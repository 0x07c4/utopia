"""Explicit Fcitx feature deployment and recovery, using the shared resolver.

Only this reviewed adapter's three home destinations are writable. Other
features remain planning-only. Generated wallpaper files are not static policy.
"""

from __future__ import annotations

import configparser
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import tomllib
from typing import Any
import uuid
import xml.etree.ElementTree as ET

from utopia import deployment


FEATURE = "fcitx-wallpaper-theme"
SELECTOR = ".config/fcitx5/conf/classicui.conf"
THEME = ".local/share/fcitx5/themes/utopia-wallpaper"
MARKER = ".config/utopia/enable-fcitx-wallpaper"
TARGETS = (SELECTOR, THEME, MARKER)
STATE = ".local/state/utopia/deployments/fcitx-wallpaper-theme"
ASSETS = {"theme.conf", "panel.svg", "highlight.svg", "arrow.png", "radio.png"}
RECORD_ID = re.compile(r"^[0-9]{8}T[0-9]{12}Z-[a-f0-9]{8}$")


def _path(home: Path, relative: str) -> Path:
    deployment._relative(relative, "deployment destination")
    current = home
    for part in Path(relative).parts:
        current /= part
        if current.is_symlink():
            raise deployment.DeploymentError(f"symlink in deployment path: {relative}")
    return current


def _home(path: Path, repo: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise deployment.DeploymentError("home must be an existing absolute directory")
    resolved = path.resolve()
    if resolved == Path("/") or resolved.is_relative_to(repo.resolve()):
        raise deployment.DeploymentError("unsafe deployment home")
    if path != resolved:
        raise deployment.DeploymentError("home path must not contain symlinks")
    return resolved


def _snapshot(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise deployment.DeploymentError("deployment target contains a symlink")
    if not path.exists():
        return {"kind": "missing"}
    mode = stat.S_IMODE(path.stat().st_mode)
    if path.is_file():
        return {"kind": "file", "mode": mode,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    if not path.is_dir():
        raise deployment.DeploymentError("unsupported deployment target type")
    entries = {}
    for child in sorted(path.iterdir()):
        entries[child.name] = _snapshot(child)
    return {"kind": "directory", "mode": mode, "entries": entries}


def _atomic(path: Path, content: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".utopia-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            os.fchmod(output.fileno(), mode)
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _save(record_path: Path, record: dict[str, Any]) -> None:
    _atomic(record_path, (json.dumps(record, indent=2, sort_keys=True) + "\n").encode())


def _records(home: Path, profile: str) -> list[tuple[Path, dict[str, Any]]]:
    root = _path(home, STATE)
    if not root.exists():
        return []
    records = []
    for directory in sorted(root.iterdir()):
        if not RECORD_ID.fullmatch(directory.name):
            continue
        path = _path(home, f"{STATE}/{directory.name}/record.json")
        if not path.exists():
            # Rendering is isolated and may fail before a transaction starts.
            continue
        try:
            record = json.loads(path.read_text())
        except (OSError, ValueError) as error:
            raise deployment.DeploymentError("invalid local deployment record") from error
        if (not isinstance(record, dict) or record.get("schema_version") != 1 or record.get("feature") != FEATURE
                or record.get("id") != directory.name
                or not isinstance(record.get("before"), dict)
                or set(record.get("before", {})) != set(TARGETS)
                or not isinstance(record.get("status"), str)
                or record.get("status") not in {
                    "prepared", "applying", "applied", "rolled-back", "rollback-failed"
                }):
            raise deployment.DeploymentError("unsupported local deployment record")
        if not isinstance(record.get("reload_session"), bool):
            raise deployment.DeploymentError("invalid reload policy in deployment record")
        for key, pattern in (("repository_commit", r"[0-9a-f]{40,64}"),
                             ("selector_source_sha256", r"[0-9a-f]{64}")):
            if not isinstance(record.get(key), str) or not re.fullmatch(pattern, record[key]):
                raise deployment.DeploymentError("invalid source identity in deployment record")
        if record["status"] == "applied" and (
            not isinstance(record.get("after"), dict) or set(record["after"]) != set(TARGETS)
        ):
            raise deployment.DeploymentError("invalid post-deployment snapshot")
        if record.get("profile") != profile:
            raise deployment.DeploymentError("deployment records belong to another host profile")
        records.append((path, record))
    return records


def _selector(content: bytes, theme: str) -> bytes:
    try:
        text = content.decode("utf-8")
    except UnicodeError as error:
        raise deployment.DeploymentError("Classic UI selector must be UTF-8") from error
    for key in ("Theme", "DarkTheme"):
        pattern = rf"(?m)^{key}=[^\r\n]*$"
        if len(re.findall(pattern, text)) != 1:
            raise deployment.DeploymentError(f"Classic UI selector needs exactly one {key}")
        text = re.sub(pattern, f"{key}={theme}", text)
    return text.encode()


def _resolved(repo: Path, profile: str, feature: str, *, require_enabled: bool = True) -> dict[str, Any]:
    plan = deployment.resolve(repo, profile, feature)
    if feature != FEATURE:
        raise deployment.DeploymentError("only the Fcitx wallpaper adapter supports deployment")
    if require_enabled and plan["activation"] != "enabled":
        raise deployment.DeploymentError("feature is not enabled for this host profile")
    if (set(plan["stages"][0]["paths"]) != set(TARGETS)
            or plan["stages"][1]["directory"] != THEME
            or plan["stages"][1]["destination"] != f"{THEME}/theme.conf"
            or plan["stages"][3]["destination"] != SELECTOR
            or plan["stages"][3]["opt_in_destination"] != MARKER
            or plan["inputs"]["dynamic_theme"] != "utopia-wallpaper"
            or plan["inputs"]["fallback_theme"] != "catppuccin-mocha-green"):
        raise deployment.DeploymentError("Fcitx deployment manifest differs from reviewed destinations")
    return plan


def preview(repo: Path, profile: str, feature: str, home: Path) -> dict[str, Any]:
    """Read live prerequisites/conflicts without creating files or rendering."""
    plan = _resolved(repo, profile, feature)
    home = _home(home, repo)
    for relative in (*TARGETS, STATE):
        _path(home, relative)
    current = {relative: _snapshot(_path(home, relative)) for relative in TARGETS}
    records = _records(home, profile)
    for _, record in records:
        if record["status"] in {"applying", "rollback-failed"}:
            raise deployment.DeploymentError(
                f"unfinished deployment {record['id']}; rollback before applying again"
            )
    if current[SELECTOR]["kind"] != "file":
        raise deployment.DeploymentError("deploy the fixed Fcitx configuration first")
    if current[THEME]["kind"] not in {"missing", "directory"}:
        raise deployment.DeploymentError("generated theme destination must be a directory")
    if current[MARKER]["kind"] not in {"missing", "file"}:
        raise deployment.DeploymentError("opt-in destination must be a file")
    baseline = repo / "input/fcitx5/config/conf/classicui.conf"
    selector = _path(home, SELECTOR).read_bytes()
    latest = next((record for _, record in reversed(records)
                   if record["status"] == "applied"), None)
    if latest:
        # Wallpaper updates own generated assets. Selector and opt-in are policy.
        for relative in (SELECTOR, MARKER):
            if current[relative] != latest["after"][relative]:
                raise deployment.DeploymentError(f"local edit since last deployment: {relative}")
        if latest["selector_source_sha256"] != hashlib.sha256(baseline.read_bytes()).hexdigest():
            raise deployment.DeploymentError("repository selector changed; review its diff before deployment")
    else:
        normalized = _selector(selector, "catppuccin-mocha-green")
        selected = re.findall(r"(?m)^(?:Theme|DarkTheme)=([^\r\n]*)$", selector.decode())
        if (any(theme not in {"catppuccin-mocha-green", "utopia-wallpaper"} for theme in selected)
                or normalized != baseline.read_bytes()):
            raise deployment.DeploymentError("unrecorded Classic UI changes; review before first deployment")
    for artifact in plan["provenance"]["required_artifacts"]:
        if artifact["id"] == "input.fcitx5-theme-catppuccin-mocha-green":
            for asset in ("arrow.png", "radio.png"):
                relative = f"{artifact['destination']}/{asset}"
                source = repo / artifact["source"] / asset
                if _snapshot(_path(home, relative)).get("sha256") != hashlib.sha256(source.read_bytes()).hexdigest():
                    raise deployment.DeploymentError(f"fixed fallback asset differs or is missing: {asset}")
    for key in ("template_source", "hook_source"):
        relative = plan["inputs"][key]
        if _snapshot(_path(home, relative)).get("sha256") != hashlib.sha256((repo / relative).read_bytes()).hexdigest():
            raise deployment.DeploymentError(f"deploy the repository Noctalia adapter first: {relative}")
    visuals = ".config/noctalia/visuals.toml"
    try:
        expected = tomllib.loads((repo / visuals).read_text())["theme"]
        actual = tomllib.loads(_path(home, visuals).read_text())["theme"]
        if (actual.get("source") != "wallpaper" or actual.get("mode") != "dark"
                or actual.get("wallpaper_scheme") != "m3-content"
                or actual["templates"]["user"]["utopia-fcitx5"] !=
                   expected["templates"]["user"]["utopia-fcitx5"]):
            raise ValueError("adapter mismatch")
    except (OSError, KeyError, ValueError) as error:
        raise deployment.DeploymentError("deploy the reviewed Noctalia wallpaper adapter settings first") from error
    return {"schema_version": 1, "profile": profile, "feature": feature,
            "dry_run": True, "plan": plan, "before": current,
            "previous_commit": latest["repository_commit"] if latest else None}


@contextmanager
def _lock(home: Path):
    root = _path(home, STATE)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = _path(home, f"{STATE}/lock")
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise deployment.DeploymentError("another Fcitx deployment is running") from error
        yield


def _run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(command, capture_output=True, timeout=60, **kwargs)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise deployment.DeploymentError(f"deployment command unavailable or timed out: {command[0]}") from error
    if result.returncode:
        raise deployment.DeploymentError(f"deployment command failed: {command[0]}")
    return result


def _render(repo: Path, plan: dict[str, Any], wallpaper: Path, staging: Path) -> Path:
    if not wallpaper.is_file():
        raise deployment.DeploymentError("wallpaper must be a readable image file")
    theme = staging / THEME
    theme.mkdir(parents=True)
    env = dict(os.environ, HOME=str(staging), XDG_CONFIG_HOME=str(staging / ".config"),
               XDG_DATA_HOME=str(staging / ".local/share"),
               XDG_CACHE_HOME=str(staging / ".cache"),
               XDG_STATE_HOME=str(staging / ".local/state"), UTOPIA_FCITX_SKIP_RELOAD="1")
    _run(["noctalia", "theme", str(wallpaper), "--scheme", "m3-content", "--dark",
          "--render", f"{repo / plan['inputs']['template_source']}:{theme / 'theme.conf'}"], env=env)
    fallback = staging / ".local/share/fcitx5/themes/catppuccin-mocha-green"
    fallback.mkdir(parents=True)
    artifact = next(a for a in plan["provenance"]["required_artifacts"]
                    if a["id"] == "input.fcitx5-theme-catppuccin-mocha-green")
    for asset in ("arrow.png", "radio.png"):
        shutil.copyfile(repo / artifact["source"] / asset, fallback / asset)
    marker = staging / MARKER
    marker.parent.mkdir(parents=True)
    marker.touch()
    _run(["bash", str(repo / plan["inputs"]["hook_source"])], env=env)
    validate_theme(theme)
    return theme


def validate_theme(theme: Path) -> None:
    if not theme.is_dir() or {p.name for p in theme.iterdir()} != ASSETS:
        raise deployment.DeploymentError("generated theme must contain exactly the five declared assets")
    _snapshot(theme)  # reject symlinks and special files before parsing
    config = configparser.ConfigParser(interpolation=None, strict=True)
    config.optionxform = str
    try:
        config.read_string((theme / "theme.conf").read_text())
        for key in ("NormalColor", "HighlightCandidateColor", "HighlightColor", "HighlightBackgroundColor"):
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", config["InputPanel"][key]):
                raise ValueError("missing or invalid candidate color")
        for section, values in config.items():
            for key, value in values.items():
                if "Color" in key and not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                    raise ValueError("invalid color")
        for section, asset in (("InputPanel/Background", "panel.svg"),
                               ("InputPanel/Highlight", "highlight.svg")):
            color = config[section]["Color"]
            if config[section]["Image"] != asset:
                raise ValueError("unexpected image")
            svg = ET.parse(theme / asset).getroot()
            if svg.find("{http://www.w3.org/2000/svg}rect").get("fill") != color:
                raise ValueError("SVG color mismatch")
        for asset in ("arrow.png", "radio.png"):
            if not (theme / asset).read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("invalid PNG")
    except (OSError, ValueError, KeyError, AttributeError, configparser.Error, ET.ParseError) as error:
        raise deployment.DeploymentError("generated Fcitx assets failed validation") from error


def _reload(plan: dict[str, Any]) -> None:
    call = plan["stages"][4]["call"]
    _run(["busctl", "--user", "call", call["bus_name"], call["object_path"],
          call["interface"], call["method"], "s", call["argument"]])


def _backup(home: Path, directory: Path) -> None:
    for relative in TARGETS:
        source = _path(home, relative)
        destination = directory / "backup" / relative
        if source.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                shutil.copytree(source, destination)
            else:
                shutil.copy2(source, destination)


def _verify_backup(home: Path, record: dict[str, Any]) -> None:
    for relative in TARGETS:
        backup = _path(home, f"{STATE}/{record['id']}/backup/{relative}")
        if _snapshot(backup) != record["before"][relative]:
            raise deployment.DeploymentError("backup integrity mismatch; recovery aborted")


def _restore(home: Path, directory: Path, record: dict[str, Any]) -> None:
    # Verify every backup before changing any target.
    _verify_backup(home, record)
    for relative in (MARKER, SELECTOR, THEME):
        target = _path(home, relative)
        backup = directory / "backup" / relative
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        if backup.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            if backup.is_dir():
                shutil.copytree(backup, target)
            else:
                _atomic(target, backup.read_bytes(), stat.S_IMODE(backup.stat().st_mode))


def apply(repo: Path, profile: str, feature: str, home: Path, wallpaper: Path,
          *, confirm_host: str, reload_session: bool = True) -> dict[str, Any]:
    if confirm_host != profile:
        raise deployment.DeploymentError("--confirm-host must match the selected profile")
    home = _home(home, repo)
    if not reload_session and home == Path.home().resolve():
        raise deployment.DeploymentError("--no-reload is only available for an isolated home")
    if reload_session and home != Path.home().resolve():
        raise deployment.DeploymentError("alternate home requires --no-reload to isolate the session")
    if home == Path.home().resolve():
        for variable, relative in (("XDG_CONFIG_HOME", ".config"),
                                   ("XDG_DATA_HOME", ".local/share"),
                                   ("XDG_STATE_HOME", ".local/state")):
            if variable in os.environ and Path(os.environ[variable]) != home / relative:
                raise deployment.DeploymentError("custom XDG roots are not supported by this adapter")
    with _lock(home):
        checked = preview(repo, profile, feature, home)
        plan = checked["plan"]
        commit = _run(["git", "-C", str(repo), "rev-parse", "HEAD"]).stdout.decode().strip()
        identifier = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:8]
        directory = _path(home, f"{STATE}/{identifier}")
        record_path = directory / "record.json"
        with tempfile.TemporaryDirectory(prefix="staging-", dir=_path(home, STATE)) as temporary:
            theme = _render(repo, plan, wallpaper, Path(temporary))
            selector_path = _path(home, SELECTOR)
            desired_selector = _selector(selector_path.read_bytes(), "utopia-wallpaper")
            desired_marker = b"# Utopia host-scoped Fcitx wallpaper opt-in.\n"
            if (checked["previous_commit"] is not None
                    and selector_path.read_bytes() == desired_selector
                    and _path(home, MARKER).is_file()
                    and _snapshot(_path(home, THEME)) == _snapshot(theme)):
                return {"status": "unchanged", "profile": profile, "feature": feature}
            if {p: _snapshot(_path(home, p)) for p in TARGETS} != checked["before"]:
                raise deployment.DeploymentError("live state changed while rendering; retry the dry-run")
            directory.mkdir(mode=0o700)
            _backup(home, directory)
            if {p: _snapshot(_path(home, p)) for p in TARGETS} != checked["before"]:
                raise deployment.DeploymentError("live state changed while backing up; retry the dry-run")
            record = {"schema_version": 1, "id": identifier, "profile": profile,
                      "feature": feature, "repository_commit": commit,
                      "wallpaper_sha256": hashlib.sha256(wallpaper.read_bytes()).hexdigest(),
                      "scheme": "m3-content", "mode": "dark",
                      "source_sha256": {
                          relative: hashlib.sha256((repo / relative).read_bytes()).hexdigest()
                          for relative in (deployment.FEATURES_PATH,
                                           plan["inputs"]["template_source"],
                                           plan["inputs"]["hook_source"])
                      },
                      "selector_source_sha256": hashlib.sha256(
                          (repo / "input/fcitx5/config/conf/classicui.conf").read_bytes()).hexdigest(),
                      "before": checked["before"], "status": "prepared",
                      "reload_session": reload_session}
            _save(record_path, record)
            record["status"] = "applying"
            _save(record_path, record)
            try:
                target = _path(home, THEME)
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    os.replace(target, directory / "replaced-theme")
                os.replace(theme, target)
                validate_theme(target)
                _atomic(selector_path, desired_selector, checked["before"][SELECTOR]["mode"])
                if not _path(home, MARKER).exists():
                    _atomic(_path(home, MARKER), desired_marker)
                if reload_session:
                    _reload(plan)
                record["after"] = {p: _snapshot(_path(home, p)) for p in TARGETS}
                record["status"] = "applied"
                _save(record_path, record)
            except BaseException:
                try:
                    _restore(home, directory, record)
                    record["status"] = "rolled-back"
                    _save(record_path, record)
                    if reload_session:
                        _reload(plan)
                except BaseException:
                    record["status"] = "rollback-failed"
                    _save(record_path, record)
                raise
        return {"status": "applied", "id": identifier, "profile": profile,
                "feature": feature, "repository_commit": commit}


def rollback(repo: Path, profile: str, identifier: str, home: Path, *,
             confirm_host: str | None = None) -> dict[str, Any]:
    if not RECORD_ID.fullmatch(identifier):
        raise deployment.DeploymentError("invalid deployment record id")
    plan = _resolved(repo, profile, FEATURE, require_enabled=False)
    home = _home(home, repo)
    records = _records(home, profile)
    selected = next(((path, record) for path, record in records
                     if record["id"] == identifier), None)
    if selected is None:
        raise deployment.DeploymentError("deployment record not found")
    path, record = selected
    if record["status"] == "rolled-back":
        return {"status": "already-rolled-back", "id": identifier}
    latest = next((r for _, r in reversed(records)
                   if r["status"] in {"applied", "applying", "rollback-failed"}), None)
    if latest is None or latest["id"] != identifier:
        raise deployment.DeploymentError("rollback must start with the latest active deployment")
    if record["status"] == "applied":
        for relative in TARGETS:
            if _snapshot(_path(home, relative)) != record["after"][relative]:
                raise deployment.DeploymentError(f"live change after deployment; rollback refused: {relative}")
    _verify_backup(home, record)
    result = {"status": "planned", "id": identifier, "paths": list(TARGETS)}
    if confirm_host is None:
        return result
    if confirm_host != profile:
        raise deployment.DeploymentError("--confirm-host must match the selected profile")
    if record["reload_session"] and home != Path.home().resolve():
        raise deployment.DeploymentError("cannot reload the session from an alternate-home record")
    with _lock(home):
        # Recheck under the lock before restoring.
        checked = rollback(repo, profile, identifier, home)
        if checked["status"] == "already-rolled-back":
            return checked
        path, record = next((p, r) for p, r in _records(home, profile) if r["id"] == identifier)
        # Persist a recoverable status before the first restoration write.
        record["status"] = "rollback-failed"
        _save(path, record)
        try:
            _restore(home, path.parent, record)
            if record["reload_session"]:
                _reload(plan)
        except deployment.DeploymentError:
            record["status"] = "rollback-failed"
            _save(path, record)
            raise
        record["status"] = "rolled-back"
        _save(path, record)
    return {"status": "rolled-back", "id": identifier}
