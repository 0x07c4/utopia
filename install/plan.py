#!/usr/bin/env python3
"""Validate an installer profile and render a read-only installation plan."""

from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = Path(__file__).with_name("config.example.toml")
PACKAGE_PATTERN = re.compile(r"^[a-z0-9@._+:-]+$")
USERNAME_PATTERN = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
HOSTNAME_PATTERN = re.compile(
    r"^(?=.{1,253}$)[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?$"
)
MAPPER_PATTERN = re.compile(r"^[A-Za-z0-9._+-]+$")


class PlanError(ValueError):
    """Raised when a profile cannot produce a safe, unambiguous plan."""


def load_config(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as config_file:
            config = tomllib.load(config_file)
    except FileNotFoundError as error:
        raise PlanError(f"configuration file does not exist: {path}") from error
    except tomllib.TOMLDecodeError as error:
        raise PlanError(f"invalid TOML in {path}: {error}") from error

    if not isinstance(config, dict):
        raise PlanError("configuration root must be a TOML table")
    return config


def require_table(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise PlanError(f"{key} must be a TOML table")
    return value


def require_string(table: dict[str, Any], key: str, prefix: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value:
        raise PlanError(f"{prefix}.{key} must be a non-empty string")
    return value


def require_string_list(table: dict[str, Any], key: str, prefix: str) -> list[str]:
    value = table.get(key)
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise PlanError(f"{prefix}.{key} must be a list of non-empty strings")
    return value


def validate_config(config: dict[str, Any], *, allow_empty_device: bool = False) -> None:
    if config.get("schema_version") != 1:
        raise PlanError("schema_version must be 1")

    system = require_table(config, "system")
    hostname = require_string(system, "hostname", "system")
    if not HOSTNAME_PATTERN.fullmatch(hostname) or ".." in hostname:
        raise PlanError("system.hostname is not a valid hostname")
    timezone = require_string(system, "timezone", "system")
    if timezone.startswith("/") or ".." in Path(timezone).parts:
        raise PlanError("system.timezone must be a relative zoneinfo name")
    require_string(system, "locale", "system")
    require_string_list(system, "extra_locales", "system")
    require_string(system, "keymap", "system")

    user = require_table(config, "user")
    username = require_string(user, "name", "user")
    if not USERNAME_PATTERN.fullmatch(username):
        raise PlanError("user.name is not a supported Linux username")
    shell = require_string(user, "shell", "user")
    if not shell.startswith("/"):
        raise PlanError("user.shell must be an absolute path")

    storage = require_table(config, "storage")
    device = storage.get("device")
    if not isinstance(device, str):
        raise PlanError("storage.device must be a string")
    if not device and not allow_empty_device:
        raise PlanError("storage.device is empty; select a whole-disk device")
    if device and not device.startswith("/dev/"):
        raise PlanError("storage.device must be an absolute /dev path")
    if storage.get("wipe") is not True:
        raise PlanError("only the explicit whole-disk wipe layout is implemented")
    if storage.get("filesystem") != "btrfs":
        raise PlanError("storage.filesystem must be btrfs")
    esp_size = storage.get("esp_size_mib")
    if type(esp_size) is not int or not 512 <= esp_size <= 16384:
        raise PlanError("storage.esp_size_mib must be between 512 and 16384")
    if storage.get("swap") != "none":
        raise PlanError("only storage.swap = 'none' is implemented")
    if type(storage.get("encryption")) is not bool:
        raise PlanError("storage.encryption must be true or false")
    mapper = require_string(storage, "luks_mapper_name", "storage")
    if not MAPPER_PATTERN.fullmatch(mapper):
        raise PlanError("storage.luks_mapper_name contains unsupported characters")

    btrfs = require_table(storage, "btrfs")
    require_string(btrfs, "label", "storage.btrfs")
    require_string_list(btrfs, "mount_options", "storage.btrfs")
    subvolumes = btrfs.get("subvolumes")
    if not isinstance(subvolumes, list) or not subvolumes:
        raise PlanError("storage.btrfs.subvolumes must be a non-empty list")
    names: set[str] = set()
    mountpoints: set[str] = set()
    for index, subvolume in enumerate(subvolumes):
        if not isinstance(subvolume, dict):
            raise PlanError(f"storage.btrfs.subvolumes[{index}] must be a table")
        name = require_string(subvolume, "name", f"storage.btrfs.subvolumes[{index}]")
        mountpoint = require_string(
            subvolume, "mountpoint", f"storage.btrfs.subvolumes[{index}]"
        )
        if not name.startswith("@"):
            raise PlanError(f"Btrfs subvolume {name!r} must start with @")
        if not mountpoint.startswith("/"):
            raise PlanError(f"mountpoint {mountpoint!r} must be absolute")
        if name in names or mountpoint in mountpoints:
            raise PlanError("Btrfs subvolume names and mountpoints must be unique")
        names.add(name)
        mountpoints.add(mountpoint)
    if "@" not in names or "/" not in mountpoints:
        raise PlanError("the Btrfs layout must define @ mounted at /")

    boot = require_table(config, "boot")
    if boot.get("loader") != "limine":
        raise PlanError("boot.loader must be limine")
    require_string(boot, "kernel", "boot")
    if type(boot.get("fallback_initramfs")) is not bool:
        raise PlanError("boot.fallback_initramfs must be true or false")
    hooks = require_string_list(boot, "mkinitcpio_hooks", "boot")
    if len(hooks) != len(set(hooks)):
        raise PlanError("boot.mkinitcpio_hooks contains duplicates")
    for required_hook in ("base", "systemd", "block", "filesystems"):
        if required_hook not in hooks:
            raise PlanError(f"boot.mkinitcpio_hooks is missing {required_hook}")
    forbidden_hooks = {"udev", "encrypt", "sd-encrypt", "sd-sd-encrypt"}
    found_forbidden = forbidden_hooks.intersection(hooks)
    if found_forbidden:
        raise PlanError(
            "base mkinitcpio hooks must not contain encryption or udev hooks: "
            + ", ".join(sorted(found_forbidden))
        )
    if boot.get("encryption_hook") != "sd-encrypt":
        raise PlanError("boot.encryption_hook must be sd-encrypt")

    packages = require_table(config, "packages")
    require_string_list(packages, "manifests", "packages")
    require_string(packages, "encrypted_install_manifest", "packages")


def manifest_path(repo_root: Path, relative_path: str) -> Path:
    candidate = (repo_root / relative_path).resolve()
    try:
        candidate.relative_to(repo_root.resolve())
    except ValueError as error:
        raise PlanError(f"package manifest escapes the repository: {relative_path}") from error
    if not candidate.is_file():
        raise PlanError(f"package manifest does not exist: {relative_path}")
    return candidate


def read_manifest(path: Path) -> list[str]:
    packages: list[str] = []
    for line_number, raw_line in enumerate(path.read_text().splitlines(), start=1):
        package = raw_line.strip()
        if not package or package.startswith("#"):
            continue
        if not PACKAGE_PATTERN.fullmatch(package):
            raise PlanError(f"invalid package name in {path}:{line_number}: {package}")
        packages.append(package)
    if len(packages) != len(set(packages)):
        raise PlanError(f"package manifest contains duplicates: {path}")
    return packages


def resolve_manifests(
    config: dict[str, Any], repo_root: Path, *, encrypted: bool
) -> tuple[list[dict[str, Any]], list[str]]:
    package_config = require_table(config, "packages")
    relative_paths = list(package_config["manifests"])
    if encrypted:
        relative_paths.append(package_config["encrypted_install_manifest"])

    manifests: list[dict[str, Any]] = []
    all_packages: list[str] = []
    for relative_path in relative_paths:
        path = manifest_path(repo_root, relative_path)
        manifest_packages = read_manifest(path)
        manifests.append({"path": relative_path, "count": len(manifest_packages)})
        all_packages.extend(manifest_packages)

    duplicates = sorted(
        package for package in set(all_packages) if all_packages.count(package) > 1
    )
    if duplicates:
        raise PlanError("packages occur in multiple active manifests: " + ", ".join(duplicates))
    return manifests, all_packages


def validate_all_manifests(config: dict[str, Any], repo_root: Path) -> None:
    resolve_manifests(config, repo_root, encrypted=False)
    resolve_manifests(config, repo_root, encrypted=True)


def collect_mounts(node: dict[str, Any]) -> list[dict[str, str]]:
    mounted: list[dict[str, str]] = []
    mountpoints = node.get("mountpoints") or []
    for mountpoint in mountpoints:
        if mountpoint:
            mounted.append({"path": node.get("path", "?"), "mountpoint": mountpoint})
    for child in node.get("children") or []:
        mounted.extend(collect_mounts(child))
    return mounted


def probe_whole_disk(device: str) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [
                "lsblk",
                "--tree",
                "--json",
                "--bytes",
                "--output",
                "PATH,TYPE,SIZE,MODEL,MOUNTPOINTS",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        raise PlanError("lsblk is required to validate the target disk") from error
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or "device was not found"
        raise PlanError(f"cannot inspect storage.device {device}: {detail}") from error

    try:
        devices = json.loads(result.stdout)["blockdevices"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise PlanError("lsblk returned an unexpected response") from error
    resolved_requested = os.path.realpath(device)
    matches = [
        candidate
        for candidate in devices
        if os.path.realpath(candidate.get("path", "")) == resolved_requested
    ]
    if len(matches) != 1:
        raise PlanError(f"storage.device did not resolve to exactly one whole disk: {device}")
    disk = matches[0]
    if disk.get("type") != "disk":
        raise PlanError(f"storage.device must be a whole disk, not {disk.get('type')!r}")

    resolved_reported = os.path.realpath(disk.get("path", ""))
    if resolved_requested != resolved_reported:
        raise PlanError(
            f"storage.device resolved unexpectedly: {device} -> {disk.get('path')}"
        )

    return {
        "path": disk["path"],
        "size_bytes": int(disk.get("size") or 0),
        "model": (disk.get("model") or "").strip(),
        "active_mounts": collect_mounts(disk),
    }


def build_plan(
    config: dict[str, Any],
    repo_root: Path,
    *,
    device_override: str | None = None,
    encryption_override: bool | None = None,
    probe_device: bool = True,
) -> dict[str, Any]:
    resolved = copy.deepcopy(config)
    storage = require_table(resolved, "storage")
    if device_override is not None:
        storage["device"] = device_override
    if encryption_override is not None:
        storage["encryption"] = encryption_override
    validate_config(resolved)
    validate_all_manifests(resolved, repo_root)

    encrypted = storage["encryption"]
    device = storage["device"]
    if probe_device:
        device_info = probe_whole_disk(device)
    else:
        device_info = {
            "path": device,
            "size_bytes": 0,
            "model": "",
            "active_mounts": [],
        }

    boot = require_table(resolved, "boot")
    hooks = list(boot["mkinitcpio_hooks"])
    if encrypted:
        hooks.insert(hooks.index("block") + 1, boot["encryption_hook"])

    mapper = storage["luks_mapper_name"]
    root_cmdline = (
        f"rd.luks.name=<LUKS_UUID>={mapper} root=/dev/mapper/{mapper} "
        "rootflags=subvol=@ rw"
        if encrypted
        else "root=UUID=<BTRFS_UUID> rootflags=subvol=@ rw"
    )
    manifests, all_packages = resolve_manifests(
        resolved, repo_root, encrypted=encrypted
    )

    system = require_table(resolved, "system")
    user = require_table(resolved, "user")
    btrfs = require_table(storage, "btrfs")
    return {
        "read_only": True,
        "system": {
            "hostname": system["hostname"],
            "timezone": system["timezone"],
            "locale": system["locale"],
            "extra_locales": system["extra_locales"],
            "keymap": system["keymap"],
            "user": user["name"],
            "shell": user["shell"],
        },
        "storage": {
            "device": device_info,
            "wipe": True,
            "esp_size_mib": storage["esp_size_mib"],
            "root_partition": "LUKS2 containing Btrfs" if encrypted else "Btrfs",
            "encryption": encrypted,
            "luks_mapper_name": mapper if encrypted else None,
            "btrfs_label": btrfs["label"],
            "mount_options": btrfs["mount_options"],
            "subvolumes": btrfs["subvolumes"],
        },
        "boot": {
            "loader": boot["loader"],
            "kernel": boot["kernel"],
            "fallback_initramfs": boot["fallback_initramfs"],
            "mkinitcpio_hooks": hooks,
            "kernel_cmdline_template": root_cmdline,
        },
        "packages": {
            "manifests": manifests,
            "total": len(all_packages),
        },
    }


def human_size(size_bytes: int) -> str:
    if not size_bytes:
        return "unknown size"
    size = float(size_bytes)
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size_bytes} B"


def format_plan(plan: dict[str, Any]) -> str:
    system = plan["system"]
    storage = plan["storage"]
    device = storage["device"]
    boot = plan["boot"]
    packages = plan["packages"]
    encryption = "enabled (LUKS2)" if storage["encryption"] else "disabled"
    model = f" — {device['model']}" if device["model"] else ""
    lines = [
        "UTOPIA INSTALL PLAN — READ ONLY",
        "",
        f"System: {system['hostname']} / {system['timezone']} / {system['locale']}",
        f"User: {system['user']} ({system['shell']})",
        f"Target disk: {device['path']} ({human_size(device['size_bytes'])}){model}",
        "Disk action: wipe the complete target disk",
        f"Partition 1: {storage['esp_size_mib']} MiB FAT32 EFI system partition at /boot",
        f"Partition 2: remaining space, {storage['root_partition']}",
        f"Encryption: {encryption}",
        "Btrfs subvolumes:",
    ]
    for subvolume in storage["subvolumes"]:
        lines.append(f"  {subvolume['name']} -> {subvolume['mountpoint']}")
    lines.extend(
        [
            f"Mount options: {','.join(storage['mount_options'])}",
            f"Boot: {boot['loader']} with {boot['kernel']}",
            f"mkinitcpio hooks: {' '.join(boot['mkinitcpio_hooks'])}",
            f"Kernel command line: {boot['kernel_cmdline_template']}",
            f"Packages: {packages['total']} unique targets",
        ]
    )
    for manifest in packages["manifests"]:
        lines.append(f"  {manifest['path']} ({manifest['count']})")
    if device["active_mounts"]:
        lines.append("WARNING: the selected disk currently has mounted filesystems:")
        for mount in device["active_mounts"]:
            lines.append(f"  {mount['path']} -> {mount['mountpoint']}")
    lines.extend(["", "No commands were executed and no changes were made."])
    return "\n".join(lines)


def parse_encryption_override(value: str | None) -> bool | None:
    if value is None:
        return None
    return value == "on"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a Utopia profile and render a read-only install plan."
    )
    parser.add_argument(
        "config",
        nargs="?",
        type=Path,
        default=DEFAULT_CONFIG,
        help="TOML profile (default: install/config.example.toml)",
    )
    parser.add_argument("--device", help="override storage.device for this preview")
    parser.add_argument(
        "--encryption",
        choices=("on", "off"),
        help="override storage.encryption for this preview",
    )
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="validate structure and all manifest references without selecting a disk",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        if args.schema_only:
            resolved = copy.deepcopy(config)
            if args.device is not None:
                require_table(resolved, "storage")["device"] = args.device
            encryption_override = parse_encryption_override(args.encryption)
            if encryption_override is not None:
                require_table(resolved, "storage")["encryption"] = encryption_override
            validate_config(resolved, allow_empty_device=True)
            validate_all_manifests(resolved, REPO_ROOT)
            output = {
                "schema_valid": True,
                "target_disk_selected": bool(resolved["storage"]["device"]),
                "default_encryption": resolved["storage"]["encryption"],
            }
            if args.json:
                print(json.dumps(output, indent=2))
            else:
                print("Configuration schema and all manifest references are valid.")
                print(
                    "Target disk: "
                    + (resolved["storage"]["device"] or "not selected (expected in example)")
                )
                print(
                    "Encryption: "
                    + ("enabled" if resolved["storage"]["encryption"] else "disabled")
                )
            return 0

        plan = build_plan(
            config,
            REPO_ROOT,
            device_override=args.device,
            encryption_override=parse_encryption_override(args.encryption),
        )
        if args.json:
            print(json.dumps(plan, indent=2))
        else:
            print(format_plan(plan))
        return 0
    except PlanError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
