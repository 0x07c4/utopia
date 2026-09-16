#!/usr/bin/env python3
"""Audit a mounted target after a restore or before rebooting from the ISO."""

from __future__ import annotations

import argparse
from pathlib import Path
import os
import stat
import sys
from typing import Any, Callable

from install import archlinuxcn, bootstrap, configure, dotfiles, plan, storage


class RecoveryError(RuntimeError):
    """Raised when the mounted target does not match the profile."""


def _read_target_file(target: Path, relative_path: str) -> str:
    path = target / relative_path
    try:
        return path.read_text()
    except OSError as error:
        raise RecoveryError(f"target file is missing or unreadable: {relative_path}") from error


def audit_target(
    config: dict[str, Any],
    *,
    target_root: Path,
    encrypted: bool,
    mount_probe: bootstrap.MountProbe = bootstrap.probe_mount,
    uuid_probe: Callable[[str], str] = configure.blkid_uuid,
    backing_probe: Callable[[str], str] = configure.mapper_backing_device,
    source_root: Path = plan.REPO_ROOT,
) -> dict[str, Any]:
    target = storage.canonical_target_root(target_root)
    identifiers = configure.discover_identifiers(
        config,
        target_root=target,
        encrypted=encrypted,
        mount_probe=mount_probe,
        uuid_probe=uuid_probe,
        backing_probe=backing_probe,
    )
    configuration = configure.build_configuration_plan(
        config,
        target_root=target,
        encryption_override=encrypted,
        identifiers=identifiers,
        placeholders=False,
    )
    mismatches: list[str] = []
    for relative_path, expected in configuration["artifacts"].items():
        try:
            actual = (target / relative_path).read_text()
        except OSError:
            mismatches.append(f"missing: {relative_path}")
            continue
        if actual != expected:
            mismatches.append(f"content differs: {relative_path}")
        expected_mode = configuration["modes"].get(relative_path, 0o644)
        actual_mode = stat.S_IMODE((target / relative_path).stat().st_mode)
        if actual_mode != expected_mode:
            mismatches.append(
                f"mode differs: {relative_path} ({actual_mode:04o} != {expected_mode:04o})"
            )
    for relative_path, link_target in configuration["symlinks"].items():
        path = target / relative_path
        if not path.is_symlink() or os.fspath(path.readlink()) != link_target:
            mismatches.append(f"symlink differs: {relative_path}")

    limine_source = target / "usr/share/limine/BOOTX64.EFI"
    limine_fallback = target / "boot/EFI/BOOT/BOOTX64.EFI"
    try:
        if limine_source.read_bytes() != limine_fallback.read_bytes():
            mismatches.append("Limine fallback EFI binary differs from the packaged binary")
    except OSError:
        mismatches.append("Limine fallback EFI binary is missing")

    greeter_plan = archlinuxcn.build_archlinuxcn_plan(
        config,
        target_root=target,
        encryption_override=encrypted,
    )
    try:
        archlinuxcn.verify_greeter_setup(greeter_plan)
    except archlinuxcn.ArchLinuxCNError as error:
        mismatches.append(str(error))
    dotfiles_plan = dotfiles.build_dotfiles_plan(
        config,
        target_root=target,
        source_root=source_root,
    )
    mismatches.extend(dotfiles.audit_deployed(dotfiles_plan))
    if mismatches:
        raise RecoveryError("target recovery audit failed:\n  " + "\n  ".join(mismatches))
    return {
        "target_root": os.fspath(target),
        "encryption": encrypted,
        "identifiers": identifiers,
        "files": list(configuration["files"]),
        "greeter": greeter_plan["greetd"],
        "dotfiles": list(dotfiles_plan["paths"]),
    }


def format_audit(audit: dict[str, Any]) -> str:
    identifiers = audit["identifiers"]
    lines = [
        "UTOPIA RECOVERY AUDIT — PASS",
        "",
        f"Target root: {audit['target_root']}",
        "Encryption: " + ("LUKS2" if audit["encryption"] else "disabled"),
        f"Btrfs UUID: {identifiers['root_uuid']}",
        f"ESP UUID: {identifiers['esp_uuid']}",
    ]
    if audit["encryption"]:
        lines.append(f"LUKS UUID: {identifiers['luks_uuid']}")
    lines.extend(
        [
            f"Checked generated files: {len(audit['files'])}",
            f"Checked user configuration paths: {len(audit['dotfiles'])}",
            f"Greeter: {audit['greeter']['command']} as {audit['greeter']['user']}",
            "No target files were modified.",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit a mounted Arch target after a recovery or before reboot."
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
    args = parser.parse_args(argv)

    try:
        config = plan.load_config(args.config)
        storage_config = plan.require_table(config, "storage")
        encrypted = (
            plan.parse_encryption_override(args.encryption)
            if args.encryption is not None
            else storage_config["encryption"]
        )
        assert encrypted is not None
        print(format_audit(audit_target(config, target_root=args.target_root, encrypted=encrypted)))
        return 0
    except (
        archlinuxcn.ArchLinuxCNError,
        bootstrap.BootstrapError,
        configure.ConfigureError,
        dotfiles.DotfilesError,
        plan.PlanError,
        RecoveryError,
        storage.StorageError,
        OSError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
