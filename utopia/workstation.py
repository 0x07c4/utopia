"""Resolve the profile and its managed home artifacts as one read-only plan."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from utopia import artifacts, profiles


def resolve(repo_root: Path, profile_id: str) -> dict[str, Any]:
    result = profiles.resolve_profile(repo_root, profile_id)
    layer_ids = [layer["id"] for layer in result["layers"]]
    resolved_artifacts, artifact_source = artifacts.resolve_artifacts(
        repo_root, layer_ids
    )
    result["artifact_source"] = artifact_source
    result["artifacts"] = resolved_artifacts
    return result


def format_plan(result: dict[str, Any]) -> str:
    lines = [profiles.format_profile(result), "", "Home artifacts:"]
    if not result["artifacts"]:
        lines.append("  (none)")
    for artifact in result["artifacts"]:
        actions = "/".join(
            action
            for action in ("capture", "deploy")
            if artifact[action]
        ) or "observe"
        lines.append(
            f"  {artifact['id']} [{artifact['state']}; {actions}] "
            f"{artifact['source']} -> ~/{artifact['destination']} "
            f"<- {artifact['layer']}"
        )
    lines.extend(
        (
            "",
            "Planning only: no files were read from or written to HOME.",
        )
    )
    return "\n".join(lines)
