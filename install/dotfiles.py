#!/usr/bin/env python3
"""Deploy the reviewed user configuration into an installed target."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import sys
from typing import Any

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
    if not any((source / ".config/nvim").iterdir()):
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
    if not home_path.is_dir() or (home_stat.st_uid, home_stat.st_gid) != (uid, gid):
        raise DotfilesError(f"configured user home is not owned by {user['name']}")
    return uid, gid, home_path


def _copy_entry(source: Path, destination: Path) -> None:
    if source.is_symlink():
        raise DotfilesError(f"dotfiles source path must not be a symlink: {source}")
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


def execute_dotfiles(dotfiles_plan: dict[str, Any], *, uid: int, gid: int, home: Path) -> None:
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
