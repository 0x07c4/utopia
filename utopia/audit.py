"""Read-only comparison of resolved artifacts with a live home directory."""

from __future__ import annotations

from collections import Counter
import filecmp
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
from typing import Any

from utopia import workstation


class AuditError(ValueError):
    """Raised when a live artifact cannot be inspected safely."""


def _path(root: Path, relative: str) -> Path:
    return root.joinpath(*PurePosixPath(relative).parts)


def _symlink_component(root: Path, relative: str) -> str | None:
    current = root
    for part in PurePosixPath(relative).parts:
        current /= part
        if current.is_symlink():
            return current.relative_to(root).as_posix()
        if not current.exists():
            return None
    return None


def _is_excluded(relative: str, excludes: list[str]) -> bool:
    return any(
        relative == excluded or relative.startswith(f"{excluded}/")
        for excluded in excludes
    )


def _change(path: str, status_name: str) -> dict[str, str]:
    return {"path": path, "status": status_name}


def _audit_file(
    source: Path, live: Path, artifact: dict[str, Any]
) -> tuple[str, list[dict[str, str]]]:
    destination = artifact["destination"]
    if live.is_symlink():
        return "unsafe", [_change(destination, "symlink")]
    if not live.exists():
        return "missing", [_change(destination, "missing")]
    if not live.is_file():
        return "unsafe", [_change(destination, "type-mismatch")]

    changes: list[dict[str, str]] = []
    if not filecmp.cmp(source, live, shallow=False):
        changes.append(_change(destination, "modified"))
    expected_mode = artifact.get("mode")
    if expected_mode is not None:
        actual_mode = stat.S_IMODE(live.stat().st_mode)
        if actual_mode != int(expected_mode, 8):
            changes.append(_change(destination, "mode-mismatch"))
    return ("drift", changes) if changes else ("match", [])


def _walk_tree(
    root: Path, excludes: list[str]
) -> tuple[dict[str, Path], dict[str, str]]:
    files: dict[str, Path] = {}
    unsafe_paths: dict[str, str] = {}
    for directory, directory_names, file_names in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        kept_directories: list[str] = []
        for name in directory_names:
            path = directory_path / name
            relative = path.relative_to(root).as_posix()
            if _is_excluded(relative, excludes):
                continue
            if path.is_symlink():
                unsafe_paths[relative] = "symlink"
            elif name == ".git":
                unsafe_paths[relative] = "git-metadata"
            else:
                kept_directories.append(name)
        directory_names[:] = kept_directories
        for name in file_names:
            path = directory_path / name
            relative = path.relative_to(root).as_posix()
            if _is_excluded(relative, excludes):
                continue
            if path.is_symlink():
                unsafe_paths[relative] = "symlink"
            elif name == ".git":
                unsafe_paths[relative] = "git-metadata"
            elif path.is_file():
                files[relative] = path
    return files, unsafe_paths


def _audit_tree(
    source: Path, live: Path, artifact: dict[str, Any]
) -> tuple[str, list[dict[str, str]]]:
    destination = PurePosixPath(artifact["destination"])
    if live.is_symlink():
        return "unsafe", [_change(destination.as_posix(), "symlink")]
    if not live.exists():
        return "missing", [_change(destination.as_posix(), "missing")]
    if not live.is_dir():
        return "unsafe", [_change(destination.as_posix(), "type-mismatch")]

    excludes = artifact["excludes"]
    expected, expected_unsafe = _walk_tree(source, excludes)
    if expected_unsafe:
        raise AuditError(
            f"validated artifact {artifact['id']!r} unexpectedly contains unsafe paths"
        )
    actual, actual_unsafe = _walk_tree(live, excludes)
    changes = [
        _change((destination / relative).as_posix(), actual_unsafe[relative])
        for relative in sorted(actual_unsafe)
    ]
    for relative in sorted(expected.keys() - actual.keys() - actual_unsafe.keys()):
        changes.append(_change((destination / relative).as_posix(), "missing"))
    for relative in sorted(actual.keys() - expected.keys()):
        changes.append(_change((destination / relative).as_posix(), "extra"))
    for relative in sorted(expected.keys() & actual.keys()):
        if not filecmp.cmp(expected[relative], actual[relative], shallow=False):
            changes.append(_change((destination / relative).as_posix(), "modified"))

    if actual_unsafe:
        return "unsafe", changes
    return ("drift", changes) if changes else ("match", [])


def _run_git(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            arguments,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        raise AuditError("git is required to audit gitlink artifacts") from error


def _expected_gitlink_commit(repo_root: Path, source: str) -> str:
    completed = _run_git(
        ["git", "-C", str(repo_root), "ls-files", "--stage", "--", source]
    )
    fields = completed.stdout.partition("\t")[0].split()
    if completed.returncode != 0 or len(fields) != 3 or fields[0] != "160000":
        raise AuditError(f"artifact source {source!r} is no longer a gitlink")
    return fields[1]


def _audit_gitlink(
    repo_root: Path, live: Path, artifact: dict[str, Any]
) -> tuple[str, list[dict[str, str]], dict[str, str]]:
    destination = artifact["destination"]
    if live.is_symlink():
        return "unsafe", [_change(destination, "symlink")], {}
    if not live.exists():
        return "missing", [_change(destination, "missing")], {}
    if not live.is_dir():
        return "unsafe", [_change(destination, "type-mismatch")], {}

    expected = _expected_gitlink_commit(repo_root, artifact["source"])
    head = _run_git(["git", "-C", str(live), "rev-parse", "HEAD"])
    if head.returncode != 0:
        return "unsafe", [_change(destination, "not-a-git-worktree")], {}
    actual = head.stdout.strip()
    worktree = _run_git(
        ["git", "-C", str(live), "status", "--porcelain", "--untracked-files=all"]
    )
    if worktree.returncode != 0:
        return "unsafe", [_change(destination, "git-status-failed")], {}

    changes: list[dict[str, str]] = []
    if actual != expected:
        changes.append(_change(destination, "commit-mismatch"))
    if worktree.stdout:
        changes.append(_change(destination, "worktree-modified"))
    commits = {"expected_commit": expected, "actual_commit": actual}
    status_name = "drift" if changes else "match"
    return status_name, changes, commits


def audit_home(repo_root: Path, profile_id: str, home_root: Path) -> dict[str, Any]:
    """Compare a resolved profile with HOME without changing either tree."""
    repo_root = repo_root.resolve()
    if home_root.is_symlink() or not home_root.is_dir():
        raise AuditError("audit home must be an existing, non-symlink directory")
    home_root = home_root.resolve()
    plan = workstation.resolve(repo_root, profile_id)
    results: list[dict[str, Any]] = []

    for artifact in plan["artifacts"]:
        source = _path(repo_root, artifact["source"])
        live = _path(home_root, artifact["destination"])
        metadata: dict[str, str] = {}
        symlink = _symlink_component(home_root, artifact["destination"])
        if symlink is not None:
            status_name = "unsafe"
            changes = [_change(symlink, "symlink")]
        elif artifact["kind"] == "file":
            status_name, changes = _audit_file(source, live, artifact)
        elif artifact["kind"] == "tree":
            status_name, changes = _audit_tree(source, live, artifact)
        else:
            status_name, changes, metadata = _audit_gitlink(
                repo_root, live, artifact
            )
        results.append(
            {
                "id": artifact["id"],
                "domain": artifact["domain"],
                "destination": artifact["destination"],
                "kind": artifact["kind"],
                "status": status_name,
                "changes": changes,
                **metadata,
            }
        )

    counts = Counter(item["status"] for item in results)
    summary = {
        status_name: counts[status_name]
        for status_name in ("match", "drift", "missing", "unsafe")
    }
    summary["total"] = len(results)
    return {
        "schema_version": 1,
        "profile": profile_id,
        "artifacts": results,
        "summary": summary,
    }


def format_audit(result: dict[str, Any]) -> str:
    """Format a privacy-conscious human-readable audit report."""
    lines = [f"Home artifact audit: {result['profile']}"]
    for artifact in result["artifacts"]:
        line = f"  {artifact['status']:<7} {artifact['id']}"
        changes = artifact["changes"]
        if changes:
            preview = ", ".join(
                f"{item['status']}:{item['path']}" for item in changes[:3]
            )
            if len(changes) > 3:
                preview += f", +{len(changes) - 3} more"
            line += f" ({preview})"
        lines.append(line)
    summary = result["summary"]
    lines.extend(
        (
            "",
            "Summary: "
            + ", ".join(
                f"{name}={summary[name]}"
                for name in ("match", "drift", "missing", "unsafe")
            ),
            "Read-only audit: no repository or home files were changed.",
        )
    )
    return "\n".join(lines)


def has_drift(result: dict[str, Any]) -> bool:
    return any(
        result["summary"][status_name]
        for status_name in ("drift", "missing", "unsafe")
    )
