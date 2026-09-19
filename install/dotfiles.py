#!/usr/bin/env python3
"""Deploy the reviewed user configuration into an installed target."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Callable

from install import bootstrap, plan, storage


class DotfilesError(RuntimeError):
    """Raised when the reviewed dotfiles deployment is unsafe or incomplete."""


# Keep this list aligned with scripts/sync-current-dotfiles.sh. Runtime state,
# credentials, and generated application data are deliberately excluded.
DEPLOY_PATHS = (
    ".zshrc",
    ".zimrc",
    ".gitconfig",
    ".ssh/config",
    ".config/Thunar",
    ".config/bottom",
    ".config/btop",
    ".config/cava",
    ".config/fastfetch",
    ".config/fish",
    ".config/fontconfig",
    ".config/environment.d/fcitx5.conf",
    ".config/fcitx5",
    ".config/gtk-3.0",
    ".config/gtk-4.0",
    ".config/kitty",
    ".config/lazygit",
    ".config/lsfg-vk",
    ".config/mimeapps.list",
    ".config/mpv",
    ".config/noctalia",
    ".config/satty",
    ".config/starship.toml",
    ".config/swayosd",
    ".config/wezterm",
    ".config/xsettingsd",
    ".config/xdg-desktop-portal",
    ".config/xfce4",
    ".config/yazi",
    ".local/bin",
    ".local/share/fcitx5/rime/default.custom.yaml",
    ".local/share/fcitx5/rime/key_bindings.custom.yaml",
    ".local/share/fcitx5/rime/rime_ice.custom.yaml",
    ".local/share/fcitx5/rime/rime_ice.dict.yaml",
    ".local/share/fcitx5/themes/catppuccin-mocha-green",
    ".local/share/icons/breeze_cursors",
    ".config/nvim",
    ".config/niri",
)

REQUIRED_PATHS = (
    ".zshrc",
    ".zimrc",
    ".config/niri/config.kdl",
    ".config/noctalia",
    ".config/nvim",
)

RIME_USER_DIR = ".local/share/fcitx5/rime"
RIME_SOURCE_PATH = f"{RIME_USER_DIR}/default.custom.yaml"
RIME_BUILD_OUTPUTS = (
    "default.yaml",
    "rime_ice.schema.yaml",
    "rime_ice.table.bin",
)


def _user_record(target: Path, username: str) -> tuple[int, int, str] | None:
    try:
        lines = (target / "etc/passwd").read_text().splitlines()
    except OSError as error:
        raise DotfilesError("cannot read the target user database") from error
    for line in lines:
        fields = line.split(":")
        if fields[0] == username and len(fields) >= 7:
            try:
                return int(fields[2]), int(fields[3]), fields[5]
            except ValueError as error:
                raise DotfilesError(f"invalid passwd entry for {username}") from error
    return None


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def build_dotfiles_plan(
    config: dict[str, Any], *, target_root: Path, source_root: Path
) -> dict[str, Any]:
    resolved = plan.load_config(plan.DEFAULT_CONFIG) if not config else config
    plan.validate_config(resolved, allow_empty_device=True)
    user = plan.require_table(resolved, "user")
    source = Path(source_root).expanduser().resolve()
    target = storage.canonical_target_root(target_root)
    if not source.is_dir():
        raise DotfilesError(f"dotfiles source root is not a directory: {source}")
    if _inside(target, source) or _inside(source, target):
        raise DotfilesError("dotfiles source and target roots must be separate")
    present = tuple(rel for rel in DEPLOY_PATHS if (source / rel).exists())
    return {
        "read_only": True,
        "source_root": os.fspath(source),
        "target_root": os.fspath(target),
        "user": user["name"],
        "paths": present,
        "required_paths": REQUIRED_PATHS,
    }


def format_dotfiles_plan(dotfiles_plan: dict[str, Any], *, dry_run: bool) -> str:
    mode = "DRY RUN" if dry_run else "APPLY REQUEST"
    lines = [
        f"UTOPIA DOTFILES STAGE — {mode}",
        "",
        f"Source: {dotfiles_plan['source_root']}",
        f"Target: {dotfiles_plan['target_root']}/home/{dotfiles_plan['user']}",
        f"Paths: {len(dotfiles_plan['paths'])}",
        "Actions:",
        "  [01] Copy the reviewed shell, desktop, input, and editor configuration",
        "  [02] Set target-user ownership; protect ~/.ssh/config",
        "  [03] Build and verify the Rime Ice user data as the target user",
        "",
    ]
    lines.append(
        "No commands were executed and no changes were made."
        if dry_run
        else "Target checks run next; no files have been copied yet."
    )
    return "\n".join(lines)


def preflight_apply(
    config: dict[str, Any],
    dotfiles_plan: dict[str, Any],
    *,
    mount_probe: bootstrap.MountProbe = bootstrap.probe_mount,
) -> tuple[int, int, Path]:
    if os.geteuid() != 0:
        raise DotfilesError("--apply must run as root from the Arch installation environment")
    target = storage.canonical_target_root(Path(dotfiles_plan["target_root"]))
    bootstrap.validate_target_mounts(
        config,
        target_root=target,
        encrypted=plan.require_table(config, "storage")["encryption"],
        mount_probe=mount_probe,
    )
    source = Path(dotfiles_plan["source_root"])
    if not source.is_dir():
        raise DotfilesError(f"dotfiles source root is missing: {source}")
    missing = [rel for rel in dotfiles_plan["required_paths"] if not (source / rel).exists()]
    if missing:
        raise DotfilesError(
            "required dotfiles are missing; initialize the repository submodule and retry: "
            + ", ".join(missing)
        )
    if not _iter_files(source / ".config/nvim"):
        raise DotfilesError(
            "the AstroNvim submodule is empty; run git submodule update --init before applying"
        )
    for rel in dotfiles_plan["paths"]:
        path = source / rel
        if path.is_symlink():
            raise DotfilesError(f"dotfiles source path must not be a symlink: {rel}")
    user = plan.require_table(config, "user")
    record = _user_record(target, user["name"])
    if record is None:
        raise DotfilesError(f"configured target user is missing: {user['name']}")
    uid, gid, home = record
    if not home.startswith("/") or ".." in Path(home).parts:
        raise DotfilesError("configured user home is not a safe absolute path")
    home_path = target / home.lstrip("/")
    try:
        home_stat = home_path.stat()
    except OSError as error:
        raise DotfilesError(f"configured user home is missing: {home}") from error
    if home_path.is_symlink() or not home_path.is_dir() or (home_stat.st_uid, home_stat.st_gid) != (uid, gid):
        raise DotfilesError(f"configured user home is not owned by {user['name']}")
    if RIME_SOURCE_PATH in dotfiles_plan["paths"]:
        if shutil.which("arch-chroot") is None:
            raise DotfilesError("required Rime deployment program is missing: arch-chroot")
        required_rime_paths = (
            "usr/bin/rime_deployer",
            "usr/share/rime-data/rime_ice.schema.yaml",
            "usr/share/rime-data/rime_ice.dict.yaml",
        )
        missing_rime_paths = [
            path for path in required_rime_paths if not (target / path).is_file()
        ]
        if missing_rime_paths:
            raise DotfilesError(
                "target Rime Ice installation is incomplete; missing: "
                + ", ".join(missing_rime_paths)
            )
    return uid, gid, home_path


def _copy_entry(source: Path, destination: Path) -> None:
    if source.is_symlink():
        raise DotfilesError(f"dotfiles source path must not be a symlink: {source}")
    if destination.is_symlink():
        raise DotfilesError(f"dotfiles target path must not be a symlink: {destination}")
    if source.is_dir():
        destination.mkdir(parents=True, exist_ok=True)
        for child in source.iterdir():
            if child.name == ".git" or child.name == "codex":
                continue
            if source.name == "gtk-4.0" and child.name in {"gtk.css", "gtk-dark.css"}:
                continue
            _copy_entry(child, destination / child.name)
        shutil.copystat(source, destination, follow_symlinks=False)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination, follow_symlinks=False)


def _chown_tree(path: Path, uid: int, gid: int) -> None:
    os.chown(path, uid, gid, follow_symlinks=False)
    if not path.is_dir():
        return
    for root, dirs, files in os.walk(path, followlinks=False):
        for name in [*dirs, *files]:
            os.chown(Path(root) / name, uid, gid, follow_symlinks=False)


RunCommand = Callable[..., subprocess.CompletedProcess[Any]]


def deploy_rime(
    dotfiles_plan: dict[str, Any],
    *,
    home: Path,
    run: RunCommand = subprocess.run,
) -> None:
    if RIME_SOURCE_PATH not in dotfiles_plan["paths"]:
        return
    target = storage.canonical_target_root(Path(dotfiles_plan["target_root"]))
    try:
        guest_home = "/" + home.relative_to(target).as_posix()
    except ValueError as error:
        raise DotfilesError("configured user home is outside the target root") from error
    rime_dir = f"{guest_home}/{RIME_USER_DIR}"
    command = [
        "arch-chroot",
        "-u",
        dotfiles_plan["user"],
        os.fspath(target),
        "env",
        f"HOME={guest_home}",
        "rime_deployer",
        "--build",
        rime_dir,
        "/usr/share/rime-data",
        f"{rime_dir}/build",
    ]
    try:
        run(command, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise DotfilesError("Rime Ice user data deployment failed") from error
    build_dir = home / RIME_USER_DIR / "build"
    missing = [name for name in RIME_BUILD_OUTPUTS if not (build_dir / name).is_file()]
    if missing:
        raise DotfilesError(
            "Rime Ice deployment did not produce: " + ", ".join(missing)
        )


def execute_dotfiles(
    dotfiles_plan: dict[str, Any],
    *,
    uid: int,
    gid: int,
    home: Path,
    run: RunCommand = subprocess.run,
) -> None:
    source = Path(dotfiles_plan["source_root"])
    for rel in dotfiles_plan["paths"]:
        destination = home / rel
        _copy_entry(source / rel, destination)
        _chown_tree(destination, uid, gid)
    ssh_dir = home / ".ssh"
    ssh_config = ssh_dir / "config"
    if ssh_dir.is_dir():
        ssh_dir.chmod(0o700)
    if ssh_config.is_file():
        ssh_config.chmod(0o600)
    deploy_rime(dotfiles_plan, home=home, run=run)


def _iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = [name for name in dirs if name not in {".git", "codex"}]
        names = [name for name in names if name not in {".git", "codex"}]
        if Path(current).name == "gtk-4.0":
            names = [name for name in names if name not in {"gtk.css", "gtk-dark.css"}]
        for name in names:
            files.append(Path(current) / name)
    return files


def audit_deployed(dotfiles_plan: dict[str, Any]) -> list[str]:
    """Compare deployed files with the source without changing either tree."""
    source = Path(dotfiles_plan["source_root"])
    target = storage.canonical_target_root(Path(dotfiles_plan["target_root"]))
    mismatches: list[str] = []
    missing = [rel for rel in dotfiles_plan["required_paths"] if not (source / rel).exists()]
    if missing:
        return ["required source configuration is missing: " + ", ".join(missing)]
    nvim = source / ".config/nvim"
    if not _iter_files(nvim):
        return ["AstroNvim submodule is empty in the source repository"]
    user_record = _user_record(target, dotfiles_plan["user"])
    if user_record is None:
        return [f"configured target user is missing: {dotfiles_plan['user']}"]
    uid, gid, home_name = user_record
    home = target / home_name.lstrip("/")
    if not home.is_dir():
        return [f"configured user home is missing: {user_record[2]}"]
    for rel in dotfiles_plan["paths"]:
        expected = source / rel
        actual = home / rel
        if expected.is_dir():
            if not actual.is_dir():
                mismatches.append(f"missing directory: {rel}")
                continue
            for source_file in _iter_files(expected):
                relative_file = source_file.relative_to(source)
                target_file = actual / source_file.relative_to(expected)
                if not target_file.is_file():
                    mismatches.append(f"missing: {relative_file}")
                    continue
                if source_file.read_bytes() != target_file.read_bytes():
                    mismatches.append(f"content differs: {relative_file}")
                if (target_file.stat().st_uid, target_file.stat().st_gid) != (uid, gid):
                    mismatches.append(f"ownership differs: {relative_file}")
        else:
            if not actual.is_file():
                mismatches.append(f"missing: {rel}")
            elif expected.read_bytes() != actual.read_bytes():
                mismatches.append(f"content differs: {rel}")
            if actual.is_file() and (actual.stat().st_uid, actual.stat().st_gid) != (uid, gid):
                mismatches.append(f"ownership differs: {rel}")
    ssh_config = home / ".ssh/config"
    if ssh_config.is_file() and stat_mode(ssh_config) != 0o600:
        mismatches.append("mode differs: .ssh/config (expected 0600)")
    return mismatches


def stat_mode(path: Path) -> int:
    return path.stat().st_mode & 0o777


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deploy reviewed Utopia user configuration.")
    parser.add_argument("config", nargs="?", type=Path, default=plan.DEFAULT_CONFIG)
    parser.add_argument("--target-root", type=Path, default=Path("/mnt"))
    parser.add_argument("--source-root", type=Path, default=plan.REPO_ROOT)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        config = plan.load_config(args.config)
        dotfiles_plan = build_dotfiles_plan(
            config, target_root=args.target_root, source_root=args.source_root
        )
        print(format_dotfiles_plan(dotfiles_plan, dry_run=not args.apply))
        if not args.apply:
            return 0
        uid, gid, home = preflight_apply(config, dotfiles_plan)
        execute_dotfiles(dotfiles_plan, uid=uid, gid=gid, home=home)
        print("Reviewed user configuration deployed and ownership verified.")
        return 0
    except (DotfilesError, bootstrap.BootstrapError, plan.PlanError, storage.StorageError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
