#!/usr/bin/env python3
"""Configure Arch Linux CN packages and finish Noctalia Greeter setup."""

from __future__ import annotations

import argparse
import copy
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tomllib
from typing import Any, Callable

from install import bootstrap, configure, plan, storage


MANAGED_BEGIN = "# BEGIN UTOPIA ARCHLINUXCN"
MANAGED_END = "# END UTOPIA ARCHLINUXCN"
ALLOWED_REPOSITORIES = {"core", "extra", "archlinuxcn"}


class ArchLinuxCNError(RuntimeError):
    """Raised when Arch Linux CN or greeter setup is unsafe or fails."""


def build_archlinuxcn_plan(
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

    manifests, packages = plan.resolve_package_source(
        resolved,
        plan.REPO_ROOT,
        source="archlinuxcn",
        encrypted=storage_config["encryption"],
    )
    if packages.count("archlinuxcn-keyring") != 1:
        raise ArchLinuxCNError(
            "the Arch Linux CN manifest must contain archlinuxcn-keyring exactly once"
        )
    if packages.count("noctalia-greeter-git") != 1:
        raise ArchLinuxCNError(
            "the Arch Linux CN manifest must contain noctalia-greeter-git exactly once"
        )
    remaining = [package for package in packages if package != "archlinuxcn-keyring"]
    target = storage.canonical_target_root(target_root)
    package_config = plan.require_table(resolved, "packages")
    greetd = plan.require_table(resolved, "greetd")
    services = plan.require_table(resolved, "services")
    enable_services = services["enable_after_archlinuxcn"]
    if "greetd.service" not in enable_services:
        raise ArchLinuxCNError(
            "services.enable_after_archlinuxcn must contain greetd.service"
        )
    chroot = ("arch-chroot", os.fspath(target))
    keyring_command = (
        *chroot,
        "pacman",
        "--sync",
        "--refresh",
        "--needed",
        "--noconfirm",
        "archlinuxcn-keyring",
    )
    package_command = (
        *chroot,
        "pacman",
        "--sync",
        "--refresh",
        "--sysupgrade",
        "--needed",
        "--noconfirm",
        *remaining,
    )
    setup_command = (
        *chroot,
        "env",
        f"GREETER_USER={greetd['user']}",
        greetd["setup_command"],
    )
    enable_command = (
        "systemctl",
        f"--root={target}",
        "enable",
        *enable_services,
    )
    return {
        "read_only": True,
        "target_root": os.fspath(target),
        "encryption": storage_config["encryption"],
        "server": package_config["archlinuxcn_server"],
        "manifests": manifests,
        "packages": packages,
        "keyring_package": "archlinuxcn-keyring",
        "remaining_packages": remaining,
        "greetd": {
            "vt": greetd["vt"],
            "command": greetd["command"],
            "user": greetd["user"],
            "setup_command": greetd["setup_command"],
        },
        "enable_services": enable_services,
        "commands": {
            "keyring": keyring_command,
            "packages": package_command,
            "greeter_setup": setup_command,
            "enable": enable_command,
        },
    }


def format_archlinuxcn_plan(arch_plan: dict[str, Any], *, dry_run: bool) -> str:
    mode = "DRY RUN" if dry_run else "APPLY REQUEST"
    lines = [
        f"UTOPIA ARCH LINUX CN + GREETER — {mode}",
        "",
        f"Target root: {arch_plan['target_root']}",
        "Encryption: " + ("LUKS2" if arch_plan["encryption"] else "disabled"),
        f"Repository: {arch_plan['server']}",
        f"Packages: {len(arch_plan['packages'])}",
    ]
    for manifest in arch_plan["manifests"]:
        lines.append(f"  {manifest['path']} ({manifest['count']})")
    lines.extend(
        [
            "Actions:",
            "  [01] Add a managed [archlinuxcn] block without a SigLevel override",
            f"  [02] {shlex.join(arch_plan['commands']['keyring'])}",
            "  [03] Verify all explicit targets resolve from archlinuxcn",
            f"  [04] {shlex.join(arch_plan['commands']['packages'])}",
            f"  [05] {shlex.join(arch_plan['commands']['greeter_setup'])}",
            "  [06] Verify greetd config, PAM integration, executable, and state ownership",
            f"  [07] {shlex.join(arch_plan['commands']['enable'])}",
            "",
        ]
    )
    if dry_run:
        lines.append("No commands were executed and no changes were made.")
    else:
        lines.append("Target checks run next; pacman.conf has not been changed yet.")
    return "\n".join(lines)


def render_pacman_conf(existing: str, server: str) -> str:
    begin_count = existing.count(MANAGED_BEGIN)
    end_count = existing.count(MANAGED_END)
    if begin_count != end_count or begin_count > 1:
        raise ArchLinuxCNError("pacman.conf contains a malformed Utopia managed block")
    cleaned = existing
    if begin_count == 1:
        start = cleaned.index(MANAGED_BEGIN)
        try:
            end = cleaned.index(MANAGED_END, start) + len(MANAGED_END)
        except ValueError as error:
            raise ArchLinuxCNError(
                "pacman.conf contains a malformed Utopia managed block"
            ) from error
        cleaned = cleaned[:start] + cleaned[end:]
    if re.search(r"(?m)^\s*\[archlinuxcn]\s*(?:#.*)?$", cleaned):
        raise ArchLinuxCNError(
            "pacman.conf already contains an unmanaged [archlinuxcn] section"
        )
    block = "\n".join(
        [
            MANAGED_BEGIN,
            "[archlinuxcn]",
            f"Server = {server}",
            MANAGED_END,
        ]
    )
    return cleaned.rstrip() + "\n\n" + block + "\n"


def install_repository_config(arch_plan: dict[str, Any]) -> None:
    target = storage.canonical_target_root(Path(arch_plan["target_root"]))
    pacman_conf = configure.safe_destination(target, "etc/pacman.conf")
    try:
        existing = pacman_conf.read_text()
        mode = stat.S_IMODE(pacman_conf.stat().st_mode)
        updated = render_pacman_conf(existing, arch_plan["server"])
        configure.atomic_write_text(pacman_conf, updated, mode)
    except OSError as error:
        raise ArchLinuxCNError(f"could not update target pacman.conf: {error}") from error


def passwd_record(target: Path, username: str) -> tuple[int, int] | None:
    try:
        lines = (target / "etc/passwd").read_text().splitlines()
    except OSError as error:
        raise ArchLinuxCNError("cannot read the target user database") from error
    for line in lines:
        fields = line.split(":")
        if fields[0] == username and len(fields) >= 4:
            try:
                return int(fields[2]), int(fields[3])
            except ValueError as error:
                raise ArchLinuxCNError(f"invalid passwd entry for {username}") from error
    return None


def group_has_member(target: Path, group: str, username: str) -> bool:
    try:
        lines = (target / "etc/group").read_text().splitlines()
    except OSError as error:
        raise ArchLinuxCNError("cannot read the target group database") from error
    for line in lines:
        fields = line.split(":")
        if fields[0] == group and len(fields) >= 4:
            return username in fields[3].split(",")
    return False


def validate_greetd_config(target: Path, greetd: dict[str, Any]) -> None:
    path = target / "etc/greetd/config.toml"
    try:
        with path.open("rb") as config_file:
            value = tomllib.load(config_file)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ArchLinuxCNError(f"cannot read target greetd configuration: {error}") from error
    terminal = value.get("terminal", {})
    session = value.get("default_session", {})
    if (
        terminal.get("vt") != greetd["vt"]
        or session.get("command") != greetd["command"]
        or session.get("user") != greetd["user"]
    ):
        raise ArchLinuxCNError("target greetd configuration does not match the profile")


def preflight_apply(
    config: dict[str, Any],
    arch_plan: dict[str, Any],
    *,
    mount_probe: bootstrap.MountProbe = bootstrap.probe_mount,
) -> None:
    if os.geteuid() != 0:
        raise ArchLinuxCNError("--apply must run as root from the Arch installation environment")
    missing_programs = [
        program for program in ("arch-chroot", "systemctl") if shutil.which(program) is None
    ]
    if missing_programs:
        raise ArchLinuxCNError(
            "required Arch Linux CN programs are missing: " + ", ".join(missing_programs)
        )
    target = storage.canonical_target_root(Path(arch_plan["target_root"]))
    bootstrap.validate_target_mounts(
        config,
        target_root=target,
        encrypted=arch_plan["encryption"],
        mount_probe=mount_probe,
    )
    required_paths = [
        "etc/pacman.conf",
        "etc/passwd",
        "etc/group",
        "etc/greetd/config.toml",
        "etc/pam.d/greetd",
        "usr/bin/greetd",
        "usr/bin/pacman",
        "usr/bin/pacman-conf",
        "usr/bin/pacman-key",
    ]
    required_paths.extend(
        f"usr/lib/systemd/system/{unit}" for unit in arch_plan["enable_services"]
    )
    missing = [path for path in required_paths if not (target / path).exists()]
    if missing:
        raise ArchLinuxCNError(
            "configured target is incomplete; missing: " + ", ".join(missing)
        )
    main_user = plan.require_table(config, "user")["name"]
    if passwd_record(target, main_user) is None:
        raise ArchLinuxCNError(f"configured target user is missing: {main_user}")
    greeter_user = arch_plan["greetd"]["user"]
    if passwd_record(target, greeter_user) is None:
        raise ArchLinuxCNError(f"greetd system user is missing: {greeter_user}")
    if not group_has_member(target, "video", greeter_user):
        raise ArchLinuxCNError(f"greetd system user is not in the video group: {greeter_user}")
    validate_greetd_config(target, arch_plan["greetd"])
    render_pacman_conf((target / "etc/pacman.conf").read_text(), arch_plan["server"])


RunCommand = Callable[..., subprocess.CompletedProcess[Any]]


def run_checked(
    run: RunCommand,
    argv: list[str] | tuple[str, ...],
    *,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[Any]:
    try:
        return run(
            list(argv),
            check=True,
            capture_output=capture_output,
            text=capture_output,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise ArchLinuxCNError(f"command failed: {shlex.join(argv)}") from error


def verify_resolution(
    arch_plan: dict[str, Any], *, run: RunCommand = subprocess.run
) -> None:
    target = arch_plan["target_root"]
    repositories = run_checked(
        run,
        ["arch-chroot", target, "pacman-conf", "--repo-list"],
        capture_output=True,
    )
    found_repositories = set(repositories.stdout.split())
    if found_repositories != ALLOWED_REPOSITORIES:
        raise ArchLinuxCNError(
            "target pacman repositories are not exactly core, extra, and archlinuxcn: "
            + ", ".join(sorted(found_repositories))
        )

    command = [
        "arch-chroot",
        target,
        "env",
        "LC_ALL=C",
        "pacman",
        "--sync",
        "--print",
        "--print-format",
        "%r/%n",
        *arch_plan["remaining_packages"],
    ]
    result = run_checked(run, command, capture_output=True)
    explicit = set(arch_plan["remaining_packages"])
    resolved_explicit: set[str] = set()
    for line in result.stdout.splitlines():
        repository, separator, package = line.strip().partition("/")
        if not separator or repository not in ALLOWED_REPOSITORIES or not package:
            raise ArchLinuxCNError(f"unexpected package resolution record: {line!r}")
        if package in explicit:
            if repository != "archlinuxcn":
                raise ArchLinuxCNError(
                    f"explicit Arch Linux CN target resolved from {repository}: {package}"
                )
            resolved_explicit.add(package)
    missing = sorted(explicit - resolved_explicit)
    if missing:
        raise ArchLinuxCNError(
            "Arch Linux CN targets did not resolve: " + ", ".join(missing)
        )


def verify_installed_packages(
    arch_plan: dict[str, Any], *, run: RunCommand = subprocess.run
) -> None:
    result = run_checked(
        run,
        [
            "arch-chroot",
            arch_plan["target_root"],
            "pacman",
            "--query",
            "--quiet",
            *arch_plan["packages"],
        ],
        capture_output=True,
    )
    installed = set(result.stdout.split())
    missing = sorted(set(arch_plan["packages"]) - installed)
    if missing:
        raise ArchLinuxCNError(
            "Arch Linux CN packages are missing after installation: " + ", ".join(missing)
        )


def verify_greeter_setup(arch_plan: dict[str, Any]) -> None:
    target = Path(arch_plan["target_root"])
    greetd = arch_plan["greetd"]
    validate_greetd_config(target, greetd)
    required_executables = [
        "usr/bin/noctalia-greeter-apply-appearance",
        "usr/bin/noctalia-greeter-session",
        greetd["setup_command"].lstrip("/"),
    ]
    for relative_path in required_executables:
        path = target / relative_path
        if not path.is_file() or not os.access(path, os.X_OK):
            raise ArchLinuxCNError(f"Noctalia Greeter executable is missing: /{relative_path}")

    try:
        pam = (target / "etc/pam.d/greetd").read_text()
    except OSError as error:
        raise ArchLinuxCNError("cannot read target greetd PAM configuration") from error
    if not re.search(r"(?m)^session\s+required\s+pam_systemd\.so(?:\s|$)", pam):
        raise ArchLinuxCNError("Noctalia Greeter PAM systemd session integration is missing")

    record = passwd_record(target, greetd["user"])
    if record is None:
        raise ArchLinuxCNError(f"greetd system user is missing: {greetd['user']}")
    state_dir = target / "var/lib/noctalia-greeter"
    try:
        state = state_dir.stat()
    except OSError as error:
        raise ArchLinuxCNError("Noctalia Greeter state directory is missing") from error
    if not state_dir.is_dir() or (state.st_uid, state.st_gid) != record:
        raise ArchLinuxCNError(
            f"Noctalia Greeter state directory is not owned by {greetd['user']}"
        )


def execute_archlinuxcn(
    arch_plan: dict[str, Any],
    *,
    run: RunCommand = subprocess.run,
    resolution_check: Callable[[dict[str, Any]], None] = verify_resolution,
    installation_check: Callable[[dict[str, Any]], None] = verify_installed_packages,
    greeter_check: Callable[[dict[str, Any]], None] = verify_greeter_setup,
) -> None:
    install_repository_config(arch_plan)
    run_checked(run, arch_plan["commands"]["keyring"])
    resolution_check(arch_plan)
    run_checked(run, arch_plan["commands"]["packages"])
    installation_check(arch_plan)
    run_checked(run, arch_plan["commands"]["greeter_setup"])
    greeter_check(arch_plan)
    run_checked(run, arch_plan["commands"]["enable"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Configure Arch Linux CN packages and Noctalia Greeter."
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
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    try:
        config = plan.load_config(args.config)
        arch_plan = build_archlinuxcn_plan(
            config,
            target_root=args.target_root,
            encryption_override=plan.parse_encryption_override(args.encryption),
        )
        print(format_archlinuxcn_plan(arch_plan, dry_run=not args.apply))
        if not args.apply:
            return 0
        preflight_apply(config, arch_plan)
        print("\nPreflight passed; configuring Arch Linux CN and Noctalia Greeter.", flush=True)
        execute_archlinuxcn(arch_plan)
        print("Arch Linux CN packages installed and greetd enabled.")
        return 0
    except (
        bootstrap.BootstrapError,
        configure.ConfigureError,
        plan.PlanError,
        storage.StorageError,
        ArchLinuxCNError,
        OSError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
