#!/usr/bin/env python3
"""Preview or execute the destructive storage preparation phase."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time
from typing import Any, Callable, Sequence

from install import plan


EFI_SYSTEM_GUID = "C12A7328-F81F-11D2-BA4B-00A0C93EC93B"
LINUX_FILESYSTEM_GUID = "0FC63DAF-8483-4772-8E79-3D69D8477DE4"
LINUX_LUKS_GUID = "CA7D7CCB-63ED-4C53-861C-1742536059CC"
PROTECTED_TARGET_ROOTS = tuple(
    Path(path)
    for path in ("/boot", "/dev", "/etc", "/home", "/proc", "/run", "/sys", "/usr", "/var")
)


class StorageError(RuntimeError):
    """Raised when storage preparation is unsafe or fails."""


@dataclass(frozen=True)
class Operation:
    description: str
    argv: tuple[str, ...]
    stdin: str | None = None
    interactive: bool = False
    effect: str | None = None


def canonical_target_root(value: Path) -> Path:
    target = value.expanduser().resolve()
    if not target.is_absolute():
        raise StorageError("target root must be an absolute path")
    if target == Path("/"):
        raise StorageError("refusing to use live system root as target root")
    for protected in PROTECTED_TARGET_ROOTS:
        if target == protected or protected in target.parents:
            raise StorageError(f"refusing to use live system path as target root: {target}")
    return target


def partition_path(device: str, number: int) -> str:
    suffix = f"p{number}" if Path(device).name[-1].isdigit() else str(number)
    return f"{device}{suffix}"


def partition_script(esp_size_mib: int, *, encrypted: bool) -> str:
    root_type = LINUX_LUKS_GUID if encrypted else LINUX_FILESYSTEM_GUID
    return "\n".join(
        [
            "label: gpt",
            "unit: sectors",
            "",
            f'size={esp_size_mib}MiB, type={EFI_SYSTEM_GUID}, name="EFI System"',
            f'type={root_type}, name="Arch Linux"',
            "",
        ]
    )


def build_operations(
    install_plan: dict[str, Any], target_root: Path
) -> list[Operation]:
    target = canonical_target_root(target_root)
    storage = install_plan["storage"]
    device = storage["device"]["path"]
    esp = partition_path(device, 1)
    root_partition = partition_path(device, 2)
    encrypted = storage["encryption"]
    mapper = storage["luks_mapper_name"]
    root_device = f"/dev/mapper/{mapper}" if encrypted else root_partition
    table = partition_script(storage["esp_size_mib"], encrypted=encrypted)

    minimum_size = (storage["esp_size_mib"] + 1024) * 1024 * 1024
    size = storage["device"]["size_bytes"]
    if size and size < minimum_size:
        raise StorageError("target disk is too small for the configured storage layout")

    operations = [
        Operation("Erase filesystem signatures", ("wipefs", "--all", "--force", device)),
        Operation(
            "Create the GPT partition table",
            (
                "sfdisk",
                "--lock=yes",
                "--wipe",
                "always",
                "--wipe-partitions",
                "always",
                device,
            ),
            stdin=table,
        ),
        Operation("Wait for partition devices", ("udevadm", "settle")),
        Operation("Format the EFI system partition", ("mkfs.fat", "-F", "32", "-n", "EFI", esp)),
    ]
    if encrypted:
        operations.extend(
            [
                Operation(
                    "Create the LUKS2 container (cryptsetup prompts on the terminal)",
                    ("cryptsetup", "luksFormat", "--type", "luks2", root_partition),
                    interactive=True,
                ),
                Operation(
                    "Open the LUKS2 container (cryptsetup prompts on the terminal)",
                    ("cryptsetup", "open", root_partition, mapper),
                    interactive=True,
                    effect="mapper-open",
                ),
            ]
        )

    operations.extend(
        [
            Operation(
                "Create the Btrfs filesystem",
                ("mkfs.btrfs", "--force", "--label", storage["btrfs_label"], root_device),
            ),
            Operation("Create the target directory", ("mkdir", "--parents", os.fspath(target))),
            Operation(
                "Mount the Btrfs top level",
                ("mount", "--types", "btrfs", root_device, os.fspath(target)),
                effect="target-mounted",
            ),
        ]
    )
    for subvolume in storage["subvolumes"]:
        operations.append(
            Operation(
                f"Create Btrfs subvolume {subvolume['name']}",
                ("btrfs", "subvolume", "create", os.fspath(target / subvolume["name"])),
            )
        )
    operations.append(
        Operation(
            "Unmount the Btrfs top level",
            ("umount", os.fspath(target)),
            effect="target-unmounted",
        )
    )

    mount_options = ",".join(storage["mount_options"])
    subvolumes = sorted(
        storage["subvolumes"], key=lambda item: len(Path(item["mountpoint"]).parts)
    )
    root_subvolume = next(item for item in subvolumes if item["mountpoint"] == "/")
    operations.append(
        Operation(
            "Mount the Btrfs root subvolume",
            (
                "mount",
                "--types",
                "btrfs",
                "--options",
                f"{mount_options},subvol=/{root_subvolume['name']}",
                root_device,
                os.fspath(target),
            ),
            effect="target-mounted",
        )
    )
    for subvolume in subvolumes:
        if subvolume["mountpoint"] == "/":
            continue
        destination = target / subvolume["mountpoint"].lstrip("/")
        operations.extend(
            [
                Operation(
                    f"Create mountpoint {subvolume['mountpoint']}",
                    ("mkdir", "--parents", os.fspath(destination)),
                ),
                Operation(
                    f"Mount Btrfs subvolume {subvolume['name']}",
                    (
                        "mount",
                        "--types",
                        "btrfs",
                        "--options",
                        f"{mount_options},subvol=/{subvolume['name']}",
                        root_device,
                        os.fspath(destination),
                    ),
                ),
            ]
        )
    boot = target / "boot"
    operations.extend(
        [
            Operation("Create the ESP mountpoint", ("mkdir", "--parents", os.fspath(boot))),
            Operation("Mount the EFI system partition", ("mount", esp, os.fspath(boot))),
        ]
    )
    return operations


def format_operations(
    operations: Sequence[Operation],
    install_plan: dict[str, Any],
    *,
    dry_run: bool = True,
) -> str:
    storage = install_plan["storage"]
    device = storage["device"]
    model = f" — {device['model']}" if device["model"] else ""
    encryption = "LUKS2" if storage["encryption"] else "disabled"
    lines = [
        "UTOPIA STORAGE OPERATIONS — " + ("DRY RUN" if dry_run else "APPLY REQUEST"),
        "",
        f"Target: {device['path']} ({plan.human_size(device['size_bytes'])}){model}",
        f"Encryption: {encryption}",
    ]
    if device["active_mounts"]:
        lines.append("WARNING: apply will refuse while these filesystems are mounted:")
        for mount in device["active_mounts"]:
            lines.append(f"  {mount['path']} -> {mount['mountpoint']}")
    lines.append("")
    for index, operation in enumerate(operations, start=1):
        lines.append(f"[{index:02d}] {operation.description}")
        lines.append(f"     {shlex.join(operation.argv)}")
        if operation.stdin is not None:
            lines.append("     stdin:")
            lines.extend(f"       {line}" for line in operation.stdin.rstrip().splitlines())
        if operation.interactive:
            lines.append("     input: direct terminal prompt; never stored by Utopia")
    lines.extend(["", f"Execution confirmation must exactly equal: {device['path']}"])
    if dry_run:
        lines.append("No commands were executed and no changes were made.")
    else:
        lines.append("Preflight checks run next; no storage command has run yet.")
    return "\n".join(lines)


def required_programs(operations: Sequence[Operation]) -> list[str]:
    return sorted({operation.argv[0] for operation in operations})


def mounted_below(target: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["findmnt", "--raw", "--noheadings", "--output", "TARGET"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise StorageError("findmnt is required to inspect the target root") from error
    mounted: list[str] = []
    for line in result.stdout.splitlines():
        try:
            mountpoint = Path(line).resolve()
            mountpoint.relative_to(target)
        except (ValueError, OSError):
            continue
        mounted.append(os.fspath(mountpoint))
    return sorted(set(mounted))


def preflight_apply(
    install_plan: dict[str, Any],
    operations: Sequence[Operation],
    target_root: Path,
    confirmation: str | None,
) -> None:
    device = install_plan["storage"]["device"]
    canonical_device = device["path"]
    if confirmation != canonical_device:
        raise StorageError(
            f"--confirm-wipe must exactly match the canonical target {canonical_device}"
        )
    if os.geteuid() != 0:
        raise StorageError("--apply must run as root from the Arch installation environment")
    if device["active_mounts"]:
        mounts = ", ".join(
            f"{item['path']} at {item['mountpoint']}" for item in device["active_mounts"]
        )
        raise StorageError(f"target disk still has mounted filesystems: {mounts}")

    target = canonical_target_root(target_root)
    existing_mounts = mounted_below(target)
    if existing_mounts:
        raise StorageError("target root already contains mounts: " + ", ".join(existing_mounts))
    if target.exists() and any(target.iterdir()):
        raise StorageError(f"target root is not empty: {target}")

    missing = [program for program in required_programs(operations) if shutil.which(program) is None]
    if missing:
        raise StorageError("required installer programs are missing: " + ", ".join(missing))

    if install_plan["storage"]["encryption"]:
        mapper = install_plan["storage"]["luks_mapper_name"]
        if Path(f"/dev/mapper/{mapper}").exists():
            raise StorageError(f"LUKS mapper is already open: {mapper}")


def wait_for_partitions(device: str, *, timeout: float = 10.0) -> None:
    expected = [Path(partition_path(device, number)) for number in (1, 2)]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if all(path.exists() for path in expected):
            return
        time.sleep(0.1)
    raise StorageError(
        "partition devices did not appear: " + ", ".join(os.fspath(path) for path in expected)
    )


RunCommand = Callable[..., subprocess.CompletedProcess[str]]


def cleanup_failed_apply(target: Path, mapper: str | None, *, mounted: bool) -> None:
    if mounted:
        subprocess.run(
            ["umount", "--recursive", os.fspath(target)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    if mapper:
        subprocess.run(
            ["cryptsetup", "close", mapper],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def execute_operations(
    operations: Sequence[Operation],
    *,
    device: str,
    target_root: Path,
    mapper: str | None,
    run: RunCommand = subprocess.run,
    wait: Callable[..., None] = wait_for_partitions,
) -> None:
    mounted = False
    mapper_open = False
    try:
        for index, operation in enumerate(operations, start=1):
            print(f"[{index:02d}/{len(operations):02d}] {operation.description}", flush=True)
            run(
                list(operation.argv),
                input=operation.stdin,
                text=True,
                check=True,
            )
            if operation.argv[:2] == ("udevadm", "settle"):
                wait(device)
            if operation.effect == "mapper-open":
                mapper_open = True
            elif operation.effect == "target-mounted":
                mounted = True
            elif operation.effect == "target-unmounted":
                mounted = False
    except (OSError, subprocess.CalledProcessError, KeyboardInterrupt) as error:
        cleanup_failed_apply(
            canonical_target_root(target_root), mapper if mapper_open else None, mounted=mounted
        )
        if isinstance(error, KeyboardInterrupt):
            raise StorageError("storage preparation interrupted; created mounts were cleaned up") from error
        raise StorageError(f"storage operation failed: {error}") from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Preview or execute Utopia's destructive storage preparation phase."
    )
    parser.add_argument(
        "config",
        nargs="?",
        type=Path,
        default=plan.DEFAULT_CONFIG,
        help="TOML profile (default: install/config.example.toml)",
    )
    parser.add_argument("--device", required=True, help="whole disk to erase")
    parser.add_argument(
        "--encryption",
        choices=("on", "off"),
        help="override storage.encryption",
    )
    parser.add_argument("--target-root", type=Path, default=Path("/mnt"))
    parser.add_argument("--apply", action="store_true", help="execute destructive operations")
    parser.add_argument(
        "--confirm-wipe",
        metavar="DEVICE",
        help="with --apply, must exactly match the canonical target disk",
    )
    args = parser.parse_args(argv)

    try:
        if args.confirm_wipe and not args.apply:
            raise StorageError("--confirm-wipe is only valid together with --apply")
        config = plan.load_config(args.config)
        install_plan = plan.build_plan(
            config,
            plan.REPO_ROOT,
            device_override=args.device,
            encryption_override=plan.parse_encryption_override(args.encryption),
        )
        target = canonical_target_root(args.target_root)
        operations = build_operations(install_plan, target)
        print(format_operations(operations, install_plan, dry_run=not args.apply))
        if not args.apply:
            return 0

        preflight_apply(install_plan, operations, target, args.confirm_wipe)
        fresh_device = plan.probe_whole_disk(install_plan["storage"]["device"]["path"])
        original_device = install_plan["storage"]["device"]
        if (
            fresh_device["path"],
            fresh_device["size_bytes"],
            fresh_device["model"],
        ) != (
            original_device["path"],
            original_device["size_bytes"],
            original_device["model"],
        ):
            raise StorageError("target disk identity changed after confirmation")
        if fresh_device["active_mounts"]:
            raise StorageError("target disk gained a mounted filesystem after confirmation")

        encrypted = install_plan["storage"]["encryption"]
        mapper = install_plan["storage"]["luks_mapper_name"] if encrypted else None
        print("\nDestructive confirmation accepted; preparing storage.", flush=True)
        execute_operations(
            operations,
            device=original_device["path"],
            target_root=target,
            mapper=mapper,
        )
        print(f"Storage is ready and mounted at {target}.")
        return 0
    except (plan.PlanError, StorageError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
