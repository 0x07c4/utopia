#!/usr/bin/env python3
"""Preview or install official Arch packages into a mounted target root."""

from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from typing import Any, Callable

from install import plan, storage


class BootstrapError(RuntimeError):
    """Raised when the official package bootstrap is unsafe or fails."""


OFFICIAL_PACMAN_CONFIG = Path(__file__).with_name("pacman.official.conf")
OFFICIAL_REPOSITORIES = {"core", "extra"}


def build_bootstrap_plan(
    config: dict[str, Any],
    *,
    target_root: Path,
    encryption_override: bool | None,
) -> dict[str, Any]:
    resolved = copy.deepcopy(config)
    storage_config = plan.require_table(resolved, "storage")
    if encryption_override is not None:
        storage_config["encryption"] = encryption_override
    plan.validate_config(resolved, allow_empty_device=True)
    plan.validate_all_manifests(resolved, plan.REPO_ROOT)

    encrypted = storage_config["encryption"]
    official_manifests, official_packages = plan.resolve_package_source(
        resolved, plan.REPO_ROOT, source="official", encrypted=encrypted
    )
    deferred: dict[str, dict[str, Any]] = {}
    for source in ("archlinuxcn", "aur"):
        manifests, packages = plan.resolve_package_source(
            resolved, plan.REPO_ROOT, source=source, encrypted=encrypted
        )
        deferred[source] = {
            "manifests": manifests,
            "packages": packages,
            "total": len(packages),
        }

    target = storage.canonical_target_root(target_root)
    command = (
        "pacstrap",
        "-C",
        os.fspath(OFFICIAL_PACMAN_CONFIG),
        "-K",
        os.fspath(target),
        *official_packages,
    )
    return {
        "read_only": True,
        "target_root": os.fspath(target),
        "encryption": encrypted,
        "official": {
            "manifests": official_manifests,
            "packages": official_packages,
            "total": len(official_packages),
        },
        "deferred": deferred,
        "command": command,
    }


def format_bootstrap_plan(bootstrap_plan: dict[str, Any], *, dry_run: bool) -> str:
    mode = "DRY RUN" if dry_run else "APPLY REQUEST"
    official = bootstrap_plan["official"]
    lines = [
        f"UTOPIA OFFICIAL PACKAGE BOOTSTRAP — {mode}",
        "",
        f"Target root: {bootstrap_plan['target_root']}",
        "Encryption: " + ("LUKS2" if bootstrap_plan["encryption"] else "disabled"),
        f"Official packages: {official['total']}",
    ]
    for manifest in official["manifests"]:
        lines.append(f"  {manifest['path']} ({manifest['count']})")
    lines.append("Deferred package sources:")
    for source, details in bootstrap_plan["deferred"].items():
        lines.append(f"  {source}: {details['total']}")
    lines.extend(
        [
            "",
            "Command:",
            f"  {shlex.join(bootstrap_plan['command'])}",
            "",
        ]
    )
    if dry_run:
        lines.append("No commands were executed and no changes were made.")
    else:
        lines.append("Mount and privilege checks run next; pacstrap has not run yet.")
    return "\n".join(lines)


def probe_mount(mountpoint: Path) -> dict[str, str]:
    try:
        result = subprocess.run(
            [
                "findmnt",
                "--json",
                "--mountpoint",
                os.fspath(mountpoint),
                "--output",
                "TARGET,SOURCE,FSTYPE,OPTIONS",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        filesystems = json.loads(result.stdout)["filesystems"]
    except FileNotFoundError as error:
        raise BootstrapError("findmnt is required to verify the target mounts") from error
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise BootstrapError(f"required target mount is missing: {mountpoint}") from error
    if not isinstance(filesystems, list) or len(filesystems) != 1:
        raise BootstrapError(f"target mount is ambiguous: {mountpoint}")
    mount = filesystems[0]
    if not isinstance(mount, dict):
        raise BootstrapError(f"unexpected findmnt response for {mountpoint}")
    return {key: str(mount.get(key, "")) for key in ("target", "source", "fstype", "options")}


def base_mount_source(source: str) -> str:
    return re.sub(r"\[[^]]*]$", "", source)


MountProbe = Callable[[Path], dict[str, str]]


def verify_official_resolution(
    bootstrap_plan: dict[str, Any],
    *,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> None:
    packages = bootstrap_plan["official"]["packages"]
    command = [
        "pacman",
        "--config",
        os.fspath(OFFICIAL_PACMAN_CONFIG),
        "--sync",
        "--print",
        "--print-format",
        "%r/%n",
        *packages,
    ]
    try:
        result = run(
            command,
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "LC_ALL": "C"},
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise BootstrapError(f"official package resolution failed: {error}") from error

    resolved_names: set[str] = set()
    for line in result.stdout.splitlines():
        repository, separator, package = line.strip().partition("/")
        if not separator or not repository or not package:
            raise BootstrapError(f"unexpected pacman package record: {line!r}")
        if repository not in OFFICIAL_REPOSITORIES:
            raise BootstrapError(
                f"package transaction resolved through non-official repository: {line}"
            )
        resolved_names.add(package)
    missing = sorted(set(packages) - resolved_names)
    if missing:
        raise BootstrapError(
            "official package transaction did not resolve explicit targets: "
            + ", ".join(missing)
        )


def validate_target_mounts(
    config: dict[str, Any],
    *,
    target_root: Path,
    encrypted: bool,
    mount_probe: MountProbe = probe_mount,
) -> dict[str, str]:
    target = storage.canonical_target_root(target_root)
    if not target.is_dir():
        raise BootstrapError(f"target root does not exist: {target}")

    storage_config = plan.require_table(config, "storage")
    btrfs = plan.require_table(storage_config, "btrfs")
    btrfs_sources: set[str] = set()
    root_source = ""
    for subvolume in btrfs["subvolumes"]:
        mountpoint = target / subvolume["mountpoint"].lstrip("/")
        mount = mount_probe(mountpoint)
        options = set(mount["options"].split(","))
        expected_subvolume = f"subvol=/{subvolume['name']}"
        if mount["target"] != os.fspath(mountpoint):
            raise BootstrapError(f"findmnt returned the wrong target for {mountpoint}")
        if mount["fstype"] != "btrfs" or expected_subvolume not in options:
            raise BootstrapError(
                f"target mount does not match {subvolume['name']} at {mountpoint}"
            )
        if "rw" not in options:
            raise BootstrapError(f"target mount is not writable: {mountpoint}")
        missing_options = set(btrfs["mount_options"]) - options
        if missing_options:
            raise BootstrapError(
                f"target mount lacks configured options at {mountpoint}: "
                + ", ".join(sorted(missing_options))
            )
        source = base_mount_source(mount["source"])
        btrfs_sources.add(source)
        if subvolume["mountpoint"] == "/":
            root_source = source
    if len(btrfs_sources) != 1:
        raise BootstrapError("Btrfs target subvolumes do not share one filesystem")

    mapper = storage_config["luks_mapper_name"]
    mapper_path = f"/dev/mapper/{mapper}"
    mounted_mapper = os.path.realpath(root_source) == os.path.realpath(mapper_path)
    if encrypted and not mounted_mapper:
        raise BootstrapError(f"encrypted plan requires the mounted mapper {mapper_path}")
    if not encrypted and mounted_mapper:
        raise BootstrapError("mounted target is encrypted but the package plan has encryption off")

    boot = target / "boot"
    boot_mount = mount_probe(boot)
    boot_options = set(boot_mount["options"].split(","))
    if boot_mount["target"] != os.fspath(boot) or boot_mount["fstype"] != "vfat":
        raise BootstrapError(f"EFI system partition is not mounted as vfat at {boot}")
    if "rw" not in boot_options:
        raise BootstrapError(f"EFI system partition is not writable: {boot}")
    return {
        "root_source": root_source,
        "esp_source": base_mount_source(boot_mount["source"]),
    }


def preflight_apply(
    config: dict[str, Any],
    bootstrap_plan: dict[str, Any],
    *,
    mount_probe: MountProbe = probe_mount,
    repository_check: Callable[[dict[str, Any]], None] = verify_official_resolution,
) -> None:
    if os.geteuid() != 0:
        raise BootstrapError("--apply must run as root from the Arch installation environment")
    missing_programs = [
        program for program in ("pacman", "pacstrap") if shutil.which(program) is None
    ]
    if missing_programs:
        raise BootstrapError(
            "required bootstrap programs are missing: " + ", ".join(missing_programs)
        )
    if not OFFICIAL_PACMAN_CONFIG.is_file():
        raise BootstrapError(f"official pacman configuration is missing: {OFFICIAL_PACMAN_CONFIG}")

    validate_target_mounts(
        config,
        target_root=Path(bootstrap_plan["target_root"]),
        encrypted=bootstrap_plan["encryption"],
        mount_probe=mount_probe,
    )
    repository_check(bootstrap_plan)


def execute_bootstrap(bootstrap_plan: dict[str, Any]) -> None:
    try:
        subprocess.run(list(bootstrap_plan["command"]), check=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise BootstrapError(f"pacstrap failed: {error}") from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Preview or install official Arch packages into a mounted target."
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
    parser.add_argument("--apply", action="store_true", help="run pacstrap after preflight checks")
    args = parser.parse_args(argv)

    try:
        config = plan.load_config(args.config)
        bootstrap_plan = build_bootstrap_plan(
            config,
            target_root=args.target_root,
            encryption_override=plan.parse_encryption_override(args.encryption),
        )
        print(format_bootstrap_plan(bootstrap_plan, dry_run=not args.apply))
        if not args.apply:
            return 0
        preflight_apply(config, bootstrap_plan)
        print("\nPreflight passed; installing official packages.", flush=True)
        execute_bootstrap(bootstrap_plan)
        print(f"Official package bootstrap completed under {bootstrap_plan['target_root']}.")
        return 0
    except (plan.PlanError, storage.StorageError, BootstrapError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
