#!/usr/bin/env python3
"""Run the reviewed Utopia installation stages in order."""

from __future__ import annotations

import argparse
import copy
from pathlib import Path
import sys
from typing import Any

from install import archlinuxcn, bootstrap, configure, plan, storage


class InstallerError(RuntimeError):
    """Raised when the complete installation pipeline cannot continue."""


def _resolved_config(
    config: dict[str, Any], storage_plan: dict[str, Any]
) -> dict[str, Any]:
    resolved = copy.deepcopy(config)
    storage_config = plan.require_table(resolved, "storage")
    storage_config["device"] = storage_plan["storage"]["device"]["path"]
    storage_config["encryption"] = storage_plan["storage"]["encryption"]
    return resolved


def build_install_plan(
    config: dict[str, Any],
    *,
    target_root: Path,
    device_override: str | None,
    encryption_override: bool | None,
) -> dict[str, Any]:
    storage_plan = plan.build_plan(
        config,
        plan.REPO_ROOT,
        device_override=device_override,
        encryption_override=encryption_override,
    )
    target = storage.canonical_target_root(target_root)
    resolved = _resolved_config(config, storage_plan)
    operations = storage.build_operations(storage_plan, target)
    bootstrap_plan = bootstrap.build_bootstrap_plan(
        resolved,
        target_root=target,
        encryption_override=None,
    )
    configuration_preview = configure.build_configuration_plan(
        resolved,
        target_root=target,
        encryption_override=None,
        identifiers=None,
        placeholders=True,
    )
    archlinuxcn_plan = archlinuxcn.build_archlinuxcn_plan(
        resolved,
        target_root=target,
        encryption_override=None,
    )
    return {
        "config": resolved,
        "target_root": target,
        "storage": storage_plan,
        "operations": operations,
        "bootstrap": bootstrap_plan,
        "configuration_preview": configuration_preview,
        "archlinuxcn": archlinuxcn_plan,
    }


def format_install_plan(install_plan: dict[str, Any], *, dry_run: bool) -> str:
    mode = "DRY RUN" if dry_run else "APPLY REQUEST"
    sections = [f"UTOPIA COMPLETE INSTALLATION — {mode}"]
    sections.append(storage.format_operations(install_plan["operations"], install_plan["storage"], dry_run=dry_run))
    sections.append(bootstrap.format_bootstrap_plan(install_plan["bootstrap"], dry_run=dry_run))
    sections.append(
        configure.format_configuration_plan(
            install_plan["configuration_preview"], dry_run=dry_run
        )
    )
    sections.append(
        archlinuxcn.format_archlinuxcn_plan(install_plan["archlinuxcn"], dry_run=dry_run)
    )
    sections.append(
        "AUR packages are deferred. The target remains mounted after a successful run for review."
    )
    return "\n\n".join(sections)


def _device_signature(device: dict[str, Any]) -> tuple[str, int, str]:
    return device["path"], device["size_bytes"], device["model"]


def _verify_device_identity(install_plan: dict[str, Any]) -> None:
    expected = install_plan["storage"]["storage"]["device"]
    fresh = plan.probe_whole_disk(expected["path"])
    if _device_signature(fresh) != _device_signature(expected):
        raise InstallerError("target disk identity changed after the reviewed plan")
    if fresh["active_mounts"]:
        raise InstallerError("target disk gained a mounted filesystem after the reviewed plan")


def execute_install(install_plan: dict[str, Any], *, confirmation: str | None) -> None:
    target = install_plan["target_root"]
    storage_plan = install_plan["storage"]
    operations = install_plan["operations"]
    storage.preflight_apply(
        storage_plan,
        operations,
        target,
        confirmation,
    )
    _verify_device_identity(install_plan)
    storage_config = storage_plan["storage"]
    mapper = storage_config["luks_mapper_name"] if storage_config["encryption"] else None
    storage.execute_operations(
        operations,
        device=storage_config["device"]["path"],
        target_root=target,
        mapper=mapper,
    )

    bootstrap_plan = install_plan["bootstrap"]
    bootstrap.preflight_apply(install_plan["config"], bootstrap_plan)
    bootstrap.execute_bootstrap(bootstrap_plan)

    identifiers = configure.discover_identifiers(
        install_plan["config"],
        target_root=target,
        encrypted=bootstrap_plan["encryption"],
    )
    configuration = configure.build_configuration_plan(
        install_plan["config"],
        target_root=target,
        encryption_override=None,
        identifiers=identifiers,
        placeholders=False,
    )
    configure.preflight_apply(install_plan["config"], configuration)
    if configure.discover_identifiers(
        install_plan["config"],
        target_root=target,
        encrypted=configuration["encryption"],
    ) != identifiers:
        raise InstallerError("target filesystem identifiers changed after configuration review")
    configure.install_artifacts(configuration)
    configure.execute_configuration(install_plan["config"], configuration)

    archlinuxcn_plan = install_plan["archlinuxcn"]
    archlinuxcn.preflight_apply(install_plan["config"], archlinuxcn_plan)
    archlinuxcn.execute_archlinuxcn(archlinuxcn_plan)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Preview or execute the complete Utopia Arch installation pipeline."
    )
    parser.add_argument(
        "config",
        nargs="?",
        type=Path,
        default=plan.DEFAULT_CONFIG,
        help="TOML profile (default: install/config.example.toml)",
    )
    parser.add_argument("--device", help="whole disk override; must be explicitly reviewed")
    parser.add_argument("--target-root", type=Path, default=Path("/mnt"))
    parser.add_argument(
        "--encryption",
        choices=("on", "off"),
        help="override storage.encryption for every stage",
    )
    parser.add_argument(
        "--confirm-wipe",
        metavar="DEVICE",
        help="with --apply, must exactly match the reviewed target disk",
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.confirm_wipe and not args.apply:
            raise InstallerError("--confirm-wipe is only valid together with --apply")
        config = plan.load_config(args.config)
        install_plan = build_install_plan(
            config,
            target_root=args.target_root,
            device_override=args.device,
            encryption_override=plan.parse_encryption_override(args.encryption),
        )
        print(format_install_plan(install_plan, dry_run=not args.apply))
        if not args.apply:
            return 0
        print("\nAll plans are shown above; starting destructive storage preflight.", flush=True)
        execute_install(install_plan, confirmation=args.confirm_wipe)
        print("Complete installation finished; the target remains mounted for review.")
        return 0
    except (
        archlinuxcn.ArchLinuxCNError,
        bootstrap.BootstrapError,
        configure.ConfigureError,
        InstallerError,
        plan.PlanError,
        storage.StorageError,
        OSError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
