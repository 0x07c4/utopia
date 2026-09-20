#!/usr/bin/env python3
"""Build and install the explicitly selected AUR packages as the target user."""

from __future__ import annotations

import argparse
import copy
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

from typing import Any, Callable

from install import bootstrap, plan, storage


class AURError(RuntimeError):
    """Raised when the AUR stage is unsafe or fails."""


def build_aur_plan(
    config: dict[str, Any],
    *,
    target_root: Path,
    encryption_override: bool | None,
    skip_review: bool,
) -> dict[str, Any]:
    resolved = copy.deepcopy(config)
    storage_config = plan.require_table(resolved, "storage")
    if encryption_override is not None:
        storage_config["encryption"] = encryption_override
    plan.validate_config(resolved, allow_empty_device=True)
    plan.validate_all_manifests(resolved, plan.REPO_ROOT)
    manifests, packages = plan.resolve_package_source(
        resolved,
        plan.REPO_ROOT,
        source="aur",
        encrypted=storage_config["encryption"],
    )
    if not packages:
        raise AURError("the AUR manifest is empty")
    user = plan.require_table(resolved, "user")
    target = storage.canonical_target_root(target_root)
    command = [
        "arch-chroot",
        "-u",
        user["name"],
        os.fspath(target),
        "env",
        f"HOME=/home/{user['name']}",
        "paru",
        "--sync",
        "--needed",
        "--noconfirm",
        "--aur",
        "--removemake",
        "--cleanafter",
    ]
    if skip_review:
        command.append("--skipreview")
    command.extend(packages)
    return {
        "read_only": True,
        "target_root": os.fspath(target),
        "encryption": storage_config["encryption"],
        "manifests": manifests,
        "packages": packages,
        "user": user["name"],
        "skip_review": skip_review,
        "command": tuple(command),
    }


def format_aur_plan(aur_plan: dict[str, Any], *, dry_run: bool) -> str:
    mode = "DRY RUN" if dry_run else "APPLY REQUEST"
    lines = [
        f"UTOPIA AUR STAGE — {mode}",
        "",
        f"Target root: {aur_plan['target_root']}",
        f"Build user: {aur_plan['user']} (never root)",
        "Encryption: " + ("LUKS2" if aur_plan["encryption"] else "disabled"),
        f"Packages: {len(aur_plan['packages'])}",
    ]
    for manifest in aur_plan["manifests"]:
        lines.append(f"  {manifest['path']} ({manifest['count']})")
    lines.extend(
        [
            "Actions:",
            f"  [01] {shlex.join(aur_plan['command'])}",
            "  [02] Verify every explicit AUR package is installed",
            "",
        ]
    )
    if aur_plan["skip_review"]:
        lines.append("PKGBUILD review is explicitly skipped by this plan.")
    else:
        lines.append("PKGBUILD review remains enabled in paru.")
    lines.append(
        "No commands were executed and no changes were made."
        if dry_run
        else "Target checks run next; no AUR command has run yet."
    )
    return "\n".join(lines)


def _user_record(target: Path, username: str) -> tuple[int, int, str] | None:
    try:
        lines = (target / "etc/passwd").read_text().splitlines()
    except OSError as error:
        raise AURError("cannot read the target user database") from error
    for line in lines:
        fields = line.split(":")
        if fields[0] == username and len(fields) >= 7:
            try:
                return int(fields[2]), int(fields[3]), fields[5]
            except ValueError as error:
                raise AURError(f"invalid passwd entry for {username}") from error
    return None


def preflight_apply(
    config: dict[str, Any],
    aur_plan: dict[str, Any],
    *,
    mount_probe: bootstrap.MountProbe = bootstrap.probe_mount,
) -> None:
    if os.geteuid() != 0:
        raise AURError("--apply must run as root from the Arch installation environment")
    if shutil.which("arch-chroot") is None:
        raise AURError("required AUR program is missing: arch-chroot")
    target = storage.canonical_target_root(Path(aur_plan["target_root"]))
    bootstrap.validate_target_mounts(
        config,
        target_root=target,
        encrypted=aur_plan["encryption"],
        mount_probe=mount_probe,
    )
    required_paths = [
        "etc/passwd",
        "usr/bin/git",
        "usr/bin/makepkg",
        "usr/bin/pacman",
        "usr/bin/paru",
    ]
    missing = [path for path in required_paths if not (target / path).exists()]
    if missing:
        raise AURError("configured target is incomplete; missing: " + ", ".join(missing))
    record = _user_record(target, aur_plan["user"])
    if record is None:
        raise AURError(f"configured target user is missing: {aur_plan['user']}")
    uid, gid, home = record
    if uid == 0:
        raise AURError("AUR builds must run as a non-root configured user")
    if not home.startswith("/") or ".." in Path(home).parts:
        raise AURError("configured user home is not a safe absolute path")
    home_path = target / home.lstrip("/")
    try:
        home_stat = home_path.stat()
    except OSError as error:
        raise AURError(f"configured user home is missing: {home}") from error
    if not home_path.is_dir() or (home_stat.st_uid, home_stat.st_gid) != (uid, gid):
        raise AURError(f"configured user home is not owned by {aur_plan['user']}")


RunCommand = Callable[..., subprocess.CompletedProcess[Any]]


def run_checked(
    run: RunCommand, argv: list[str] | tuple[str, ...], *, capture_output: bool = False
) -> subprocess.CompletedProcess[Any]:
    try:
        return run(
            list(argv),
            check=True,
            capture_output=capture_output,
            text=capture_output,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise AURError(f"command failed: {shlex.join(argv)}") from error


def verify_installed_packages(
    aur_plan: dict[str, Any], *, run: RunCommand = subprocess.run
) -> None:
    result = run_checked(
        run,
        [
            "arch-chroot",
            aur_plan["target_root"],
            "pacman",
            "--query",
            "--quiet",
            *aur_plan["packages"],
        ],
        capture_output=True,
    )
    installed = set(result.stdout.split())
    missing = sorted(set(aur_plan["packages"]) - installed)
    if missing:
        raise AURError("AUR packages are missing after installation: " + ", ".join(missing))


def execute_aur(
    aur_plan: dict[str, Any],
    *,
    run: RunCommand = subprocess.run,
    installation_check: Callable[[dict[str, Any]], None] = verify_installed_packages,
) -> None:
    run_checked(run, aur_plan["command"])
    installation_check(aur_plan)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build and install the configured AUR packages as the target user."
    )
    parser.add_argument(
        "config",
        nargs="?",
        type=Path,
        default=plan.DEFAULT_CONFIG,
        help="TOML profile (default: install/config.example.toml)",
    )
    parser.add_argument("--target-root", type=Path, default=Path("/mnt"))
    parser.add_argument(
        "--encryption",
        choices=("on", "off"),
        help="override storage.encryption; must match the mounted layout",
    )
    parser.add_argument("--skip-review", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    try:
        config = plan.load_config(args.config)
        aur_plan = build_aur_plan(
            config,
            target_root=args.target_root,
            encryption_override=plan.parse_encryption_override(args.encryption),
            skip_review=args.skip_review,
        )
        print(format_aur_plan(aur_plan, dry_run=not args.apply))
        if not args.apply:
            return 0
        preflight_apply(config, aur_plan)
        print("\nPreflight passed; building AUR packages as the target user.", flush=True)
        execute_aur(aur_plan)
        print("AUR packages installed and verified.")
        return 0
    except (
        AURError,
        bootstrap.BootstrapError,
        plan.PlanError,
        storage.StorageError,
        OSError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
