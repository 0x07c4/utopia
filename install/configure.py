#!/usr/bin/env python3
"""Preview or configure a bootstrapped Arch Linux target system."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable

from install import bootstrap, plan, render, storage


class ConfigureError(RuntimeError):
    """Raised when target configuration is unsafe or fails."""


def blkid_uuid(
    device: str,
    *,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> str:
    try:
        result = run(
            ["blkid", "--probe", "--match-tag", "UUID", "--output", "value", device],
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "LC_ALL": "C"},
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise ConfigureError(f"could not read the UUID from {device}: {error}") from error
    value = result.stdout.strip()
    if not value or "\n" in value:
        raise ConfigureError(f"blkid returned an invalid UUID for {device}")
    return value


def mapper_backing_device(root_source: str) -> str:
    resolved = Path(root_source).resolve()
    slaves = Path("/sys/class/block") / resolved.name / "slaves"
    try:
        entries = list(slaves.iterdir())
    except OSError as error:
        raise ConfigureError(f"cannot inspect the backing device for {root_source}") from error
    if len(entries) != 1:
        raise ConfigureError(f"encrypted root must have exactly one backing device: {root_source}")
    return f"/dev/{entries[0].name}"


def discover_identifiers(
    config: dict[str, Any],
    *,
    target_root: Path,
    encrypted: bool,
    mount_probe: bootstrap.MountProbe = bootstrap.probe_mount,
    uuid_probe: Callable[[str], str] = blkid_uuid,
    backing_probe: Callable[[str], str] = mapper_backing_device,
) -> dict[str, str | None]:
    sources = bootstrap.validate_target_mounts(
        config,
        target_root=target_root,
        encrypted=encrypted,
        mount_probe=mount_probe,
    )
    root_uuid = uuid_probe(sources["root_source"])
    esp_uuid = uuid_probe(sources["esp_source"])
    luks_uuid = None
    if encrypted:
        luks_uuid = uuid_probe(backing_probe(sources["root_source"]))
    try:
        return render.resolve_identifiers(
            root_uuid=root_uuid,
            esp_uuid=esp_uuid,
            luks_uuid=luks_uuid,
            encrypted=encrypted,
            placeholders=False,
        )
    except render.RenderError as error:
        raise ConfigureError(str(error)) from error


def build_configuration_plan(
    config: dict[str, Any],
    *,
    target_root: Path,
    encryption_override: bool | None,
    identifiers: dict[str, str | None] | None,
    placeholders: bool,
) -> dict[str, Any]:
    target = storage.canonical_target_root(target_root)
    storage_config = plan.require_table(config, "storage")
    encrypted = (
        encryption_override
        if encryption_override is not None
        else storage_config["encryption"]
    )
    if placeholders:
        if identifiers is not None:
            raise ConfigureError("placeholder configuration cannot use discovered UUIDs")
        root_uuid = esp_uuid = luks_uuid = None
    else:
        if identifiers is None:
            raise ConfigureError("discovered UUIDs are required without --placeholders")
        root_uuid = identifiers["root_uuid"]
        esp_uuid = identifiers["esp_uuid"]
        luks_uuid = identifiers["luks_uuid"]

    artifacts, metadata = render.build_artifacts(
        config,
        root_uuid=root_uuid,
        esp_uuid=esp_uuid,
        luks_uuid=luks_uuid,
        encryption_override=encrypted,
        placeholders=placeholders,
    )
    user = plan.require_table(config, "user")
    services = plan.require_table(config, "services")
    boot = plan.require_table(config, "boot")
    chroot = ("arch-chroot", os.fspath(target))
    group_list = ",".join(user["groups"])
    actions = [
        "Install generated configuration files atomically",
        "Install /usr/share/limine/BOOTX64.EFI at /boot/EFI/BOOT/BOOTX64.EFI",
        shlex.join((*chroot, "locale-gen")),
        (
            shlex.join(
                (
                    *chroot,
                    "useradd",
                    "--create-home",
                    "--groups",
                    group_list,
                    "--shell",
                    user["shell"],
                    user["name"],
                )
            )
            + " (usermod with the same groups and shell on retry)"
        ),
        shlex.join((*chroot, "visudo", "--check", "--file", "/etc/sudoers")),
        shlex.join((*chroot, "hwclock", "--systohc")),
        shlex.join((*chroot, "mkinitcpio", "-P")),
        shlex.join(
            (
                "systemctl",
                f"--root={target}",
                "enable",
                *services["enable_after_official"],
            )
        ),
        shlex.join((*chroot, "passwd", user["name"]))
        + " (interactive terminal input; never stored by Utopia)",
        shlex.join((*chroot, "passwd", "--lock", "root")),
    ]
    return {
        "read_only": True,
        "target_root": os.fspath(target),
        "encryption": encrypted,
        "identifiers": metadata["identifiers"],
        "artifacts": artifacts,
        "symlinks": metadata["symlinks"],
        "modes": metadata["modes"],
        "files": metadata["files"],
        "kernel": boot["kernel"],
        "user": {
            "name": user["name"],
            "shell": user["shell"],
            "groups": user["groups"],
        },
        "enable_services": services["enable_after_official"],
        "deferred_services": services["enable_after_archlinuxcn"],
        "actions": actions,
    }


def format_configuration_plan(configuration: dict[str, Any], *, dry_run: bool) -> str:
    mode = "DRY RUN" if dry_run else "APPLY REQUEST"
    identifiers = configuration["identifiers"]
    lines = [
        f"UTOPIA TARGET CONFIGURATION — {mode}",
        "",
        f"Target root: {configuration['target_root']}",
        "Encryption: " + ("LUKS2" if configuration["encryption"] else "disabled"),
        f"Btrfs UUID: {identifiers['root_uuid']}",
        f"ESP UUID: {identifiers['esp_uuid']}",
    ]
    if configuration["encryption"]:
        lines.append(f"LUKS UUID: {identifiers['luks_uuid']}")
    lines.append("Generated paths:")
    for relative_path in configuration["files"]:
        if relative_path in configuration["symlinks"]:
            lines.append(
                f"  {relative_path} -> {configuration['symlinks'][relative_path]}"
            )
        else:
            mode_value = configuration["modes"].get(relative_path, 0o644)
            lines.append(f"  {relative_path} ({mode_value:04o})")
    lines.append("Actions:")
    for index, action in enumerate(configuration["actions"], start=1):
        lines.append(f"  [{index:02d}] {action}")
    if configuration["deferred_services"]:
        lines.append(
            "Deferred until Arch Linux CN stage: "
            + ", ".join(configuration["deferred_services"])
        )
    lines.append("")
    if dry_run:
        lines.append("No commands were executed and no changes were made.")
    else:
        lines.append("Target checks run next; no configuration has been written yet.")
    return "\n".join(lines)


def safe_destination(target: Path, relative_path: str) -> Path:
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ConfigureError(f"artifact path escapes the target root: {relative_path}")
    destination = target / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        destination.parent.resolve().relative_to(target)
    except ValueError as error:
        raise ConfigureError(f"artifact parent escapes the target root: {relative_path}") from error
    return destination


def atomic_write_text(destination: Path, content: str, mode: int) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        temporary.chmod(mode)
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def atomic_symlink(destination: Path, link_target: str) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    temporary.unlink()
    try:
        temporary.symlink_to(link_target)
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def install_artifacts(configuration: dict[str, Any]) -> None:
    target = storage.canonical_target_root(Path(configuration["target_root"]))
    try:
        for relative_path, content in configuration["artifacts"].items():
            destination = safe_destination(target, relative_path)
            atomic_write_text(
                destination,
                content,
                configuration["modes"].get(relative_path, 0o644),
            )
        for relative_path, link_target in configuration["symlinks"].items():
            atomic_symlink(safe_destination(target, relative_path), link_target)

        source = target / "usr/share/limine/BOOTX64.EFI"
        destination = safe_destination(target, "boot/EFI/BOOT/BOOTX64.EFI")
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", dir=destination.parent
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            shutil.copyfile(source, temporary)
            temporary.chmod(0o755)
            os.replace(temporary, destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    except OSError as error:
        raise ConfigureError(f"could not install target configuration: {error}") from error


def preflight_apply(
    config: dict[str, Any],
    configuration: dict[str, Any],
    *,
    mount_probe: bootstrap.MountProbe = bootstrap.probe_mount,
) -> None:
    if os.geteuid() != 0:
        raise ConfigureError("--apply must run as root from the Arch installation environment")
    missing_programs = [
        program
        for program in ("arch-chroot", "blkid", "systemctl")
        if shutil.which(program) is None
    ]
    if missing_programs:
        raise ConfigureError(
            "required configuration programs are missing: " + ", ".join(missing_programs)
        )
    target = storage.canonical_target_root(Path(configuration["target_root"]))
    bootstrap.validate_target_mounts(
        config,
        target_root=target,
        encrypted=configuration["encryption"],
        mount_probe=mount_probe,
    )

    required_paths = [
        "etc/os-release",
        "etc/passwd",
        "etc/group",
        "usr/bin/bash",
        "usr/bin/hwclock",
        "usr/bin/locale-gen",
        "usr/bin/mkinitcpio",
        "usr/bin/passwd",
        "usr/bin/useradd",
        "usr/bin/usermod",
        "usr/bin/visudo",
        "usr/share/limine/BOOTX64.EFI",
        f"boot/vmlinuz-{configuration['kernel']}",
    ]
    required_paths.extend(
        f"usr/lib/systemd/system/{unit}" for unit in configuration["enable_services"]
    )
    missing_paths = [path for path in required_paths if not (target / path).exists()]
    if missing_paths:
        raise ConfigureError(
            "target package bootstrap is incomplete; missing: " + ", ".join(missing_paths)
        )
    if not (target / configuration["user"]["shell"].lstrip("/")).is_file():
        raise ConfigureError(
            f"configured user shell is missing in target: {configuration['user']['shell']}"
        )


RunCommand = Callable[..., subprocess.CompletedProcess[Any]]


def run_checked(run: RunCommand, argv: list[str]) -> None:
    try:
        run(argv, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise ConfigureError(f"target configuration command failed: {shlex.join(argv)}") from error


def target_user_exists(target: Path, username: str) -> bool:
    try:
        lines = (target / "etc/passwd").read_text().splitlines()
    except OSError as error:
        raise ConfigureError("cannot read the target user database") from error
    return any(line.partition(":")[0] == username for line in lines)


def execute_configuration(
    config: dict[str, Any],
    configuration: dict[str, Any],
    *,
    run: RunCommand = subprocess.run,
) -> None:
    target = Path(configuration["target_root"])
    user = plan.require_table(config, "user")
    chroot = ["arch-chroot", os.fspath(target)]
    run_checked(run, [*chroot, "locale-gen"])
    groups = ",".join(user["groups"])
    if target_user_exists(target, user["name"]):
        run_checked(
            run,
            [
                *chroot,
                "usermod",
                "--append",
                "--groups",
                groups,
                "--shell",
                user["shell"],
                user["name"],
            ],
        )
    else:
        run_checked(
            run,
            [
                *chroot,
                "useradd",
                "--create-home",
                "--groups",
                groups,
                "--shell",
                user["shell"],
                user["name"],
            ],
        )
    run_checked(run, [*chroot, "visudo", "--check", "--file", "/etc/sudoers"])
    run_checked(run, [*chroot, "hwclock", "--systohc"])
    run_checked(run, [*chroot, "mkinitcpio", "-P"])
    run_checked(
        run,
        [
            "systemctl",
            f"--root={target}",
            "enable",
            *configuration["enable_services"],
        ],
    )
    run_checked(run, [*chroot, "passwd", user["name"]])
    run_checked(run, [*chroot, "passwd", "--lock", "root"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Preview or configure a bootstrapped Arch Linux target."
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
    parser.add_argument(
        "--placeholders",
        action="store_true",
        help="preview deterministic UUID placeholders without a mounted target",
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.apply and args.placeholders:
            raise ConfigureError("--placeholders cannot be combined with --apply")
        config = plan.load_config(args.config)
        encryption_override = plan.parse_encryption_override(args.encryption)
        storage_config = plan.require_table(config, "storage")
        encrypted = (
            encryption_override
            if encryption_override is not None
            else storage_config["encryption"]
        )
        identifiers = None
        if not args.placeholders:
            identifiers = discover_identifiers(
                config,
                target_root=args.target_root,
                encrypted=encrypted,
            )
        configuration = build_configuration_plan(
            config,
            target_root=args.target_root,
            encryption_override=encryption_override,
            identifiers=identifiers,
            placeholders=args.placeholders,
        )
        print(format_configuration_plan(configuration, dry_run=not args.apply))
        if not args.apply:
            return 0

        preflight_apply(config, configuration)
        fresh_identifiers = discover_identifiers(
            config,
            target_root=Path(configuration["target_root"]),
            encrypted=configuration["encryption"],
        )
        if fresh_identifiers != configuration["identifiers"]:
            raise ConfigureError("target filesystem identifiers changed after review")
        print("\nPreflight passed; configuring the target system.", flush=True)
        install_artifacts(configuration)
        execute_configuration(config, configuration)
        print("Target system configuration completed; the user password was not stored.")
        return 0
    except (
        bootstrap.BootstrapError,
        plan.PlanError,
        render.RenderError,
        storage.StorageError,
        ConfigureError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
