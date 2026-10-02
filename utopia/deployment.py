"""Resolve safe, host-scoped deployment plans without touching HOME."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
import re
import tomllib
from typing import Any

from utopia import workstation


class DeploymentError(ValueError):
    """Raised when a feature deployment definition is invalid or unavailable."""


@dataclass(frozen=True)
class ReloadCall:
    bus_name: str
    object_path: str
    interface: str
    method: str
    argument: str


FEATURES_PATH = "profiles/features.toml"
FEATURE_KEYS = {
    "description",
    "state_path",
    "domain",
    "activation_state",
    "required_artifacts",
    "template_source",
    "hook_source",
    "generated_directory",
    "generated_theme",
    "selector_destination",
    "opt_in_destination",
    "fallback_theme",
    "dynamic_theme",
    "backup_destinations",
    "rollback_destinations",
    "reload",
}
RELOAD_KEYS = {"bus_name", "object_path", "interface", "method", "argument"}
STATES = {"fallback", "experimental", "managed", "unmanaged"}
FEATURE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
ARTIFACT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")
DOMAIN_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")
STATE_PATH_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*(?:\.[a-z][a-z0-9_-]*)*$")


def _relative(value: str, context: str) -> str:
    path = PurePosixPath(value)
    if (
        not value
        or path.is_absolute()
        or value in {"", "."}
        or ".." in path.parts
        or value != path.as_posix()
    ):
        raise DeploymentError(f"{context} must be a normalized relative POSIX path")
    return value


def _string(table: dict[str, Any], key: str, context: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value:
        raise DeploymentError(f"{context}.{key} must be a non-empty string")
    return value


def _strings(table: dict[str, Any], key: str, context: str) -> list[str]:
    value = table.get(key)
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise DeploymentError(f"{context}.{key} must be a list of strings")
    if len(value) != len(set(value)):
        raise DeploymentError(f"{context}.{key} contains duplicates")
    return value


def _load_features(repo_root: Path) -> dict[str, dict[str, Any]]:
    path = repo_root / FEATURES_PATH
    try:
        with path.open("rb") as source:
            data = tomllib.load(source)
    except FileNotFoundError as error:
        raise DeploymentError(f"feature definitions do not exist: {FEATURES_PATH}") from error
    except tomllib.TOMLDecodeError as error:
        raise DeploymentError(f"invalid TOML in {FEATURES_PATH}: {error}") from error
    if set(data) != {"schema_version", "features"} or data["schema_version"] != 1:
        raise DeploymentError(f"{FEATURES_PATH} must have schema_version 1 and features")
    features = data["features"]
    if not isinstance(features, dict) or not features:
        raise DeploymentError(f"{FEATURES_PATH}.features must be a non-empty table")

    parsed: dict[str, dict[str, Any]] = {}
    for feature_id, raw in features.items():
        context = f"{FEATURES_PATH}.features.{feature_id}"
        if not isinstance(feature_id, str) or not FEATURE_ID_PATTERN.fullmatch(feature_id):
            raise DeploymentError(f"{context} has an invalid id")
        if not isinstance(raw, dict):
            raise DeploymentError(f"{context} must be a table")
        unknown = set(raw).difference(FEATURE_KEYS)
        missing = FEATURE_KEYS.difference(raw)
        if unknown:
            raise DeploymentError(f"{context} has unknown keys: {', '.join(sorted(unknown))}")
        if missing:
            raise DeploymentError(f"{context} is missing: {', '.join(sorted(missing))}")
        feature = dict(raw)
        for key in ("description", "state_path", "domain", "fallback_theme", "dynamic_theme"):
            _string(feature, key, context)
        if not STATE_PATH_PATTERN.fullmatch(feature["state_path"]):
            raise DeploymentError(f"{context}.state_path has an invalid dotted path")
        activation_state = feature["activation_state"]
        if not isinstance(activation_state, str):
            raise DeploymentError(f"{context}.activation_state must be a string")
        if activation_state not in {"experimental", "managed"}:
            raise DeploymentError(f"{context}.activation_state must be experimental or managed")
        if not DOMAIN_PATTERN.fullmatch(feature["domain"]):
            raise DeploymentError(f"{context}.domain has an invalid value")
        for key in (
            "template_source",
            "hook_source",
            "generated_directory",
            "generated_theme",
            "selector_destination",
            "opt_in_destination",
        ):
            _relative(_string(feature, key, context), f"{context}.{key}")
        for key in ("backup_destinations", "rollback_destinations"):
            values = _strings(feature, key, context)
            feature[key] = [
                _relative(value, f"{context}.{key}") for value in values
            ]
        artifacts = _strings(feature, "required_artifacts", context)
        if not artifacts:
            raise DeploymentError(f"{context}.required_artifacts must not be empty")
        invalid_artifacts = [
            artifact_id
            for artifact_id in artifacts
            if not ARTIFACT_ID_PATTERN.fullmatch(artifact_id)
        ]
        if invalid_artifacts:
            raise DeploymentError(
                f"{context}.required_artifacts has invalid ids: {', '.join(invalid_artifacts)}"
            )
        feature["required_artifacts"] = artifacts
        reload_data = feature["reload"]
        if not isinstance(reload_data, dict):
            raise DeploymentError(f"{context}.reload must be a table")
        if set(reload_data) != RELOAD_KEYS:
            raise DeploymentError(f"{context}.reload must contain exactly the D-Bus call keys")
        feature["reload"] = ReloadCall(
            **{key: _string(reload_data, key, f"{context}.reload") for key in RELOAD_KEYS}
        )
        generated_directory = PurePosixPath(feature["generated_directory"])
        generated_theme = PurePosixPath(feature["generated_theme"])
        if generated_directory not in generated_theme.parents:
            raise DeploymentError(
                f"{context}.generated_theme must be inside generated_directory"
            )
        for key in ("backup_destinations", "rollback_destinations"):
            destinations = feature[key]
            for required_destination in (
                feature["selector_destination"],
                feature["generated_directory"],
                feature["opt_in_destination"],
            ):
                if required_destination not in destinations:
                    raise DeploymentError(
                        f"{context}.{key} must include {required_destination!r}"
                    )
        parsed[feature_id] = feature
    return parsed


def _value_at(values: dict[str, Any], dotted_path: str) -> Any:
    current: Any = values
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise DeploymentError(f"profile does not resolve feature state {dotted_path!r}")
        current = current[part]
    return current


def _source_exists(repo_root: Path, relative: str, *, directory: bool | None = None) -> None:
    source = repo_root / relative
    current = repo_root
    for part in PurePosixPath(relative).parts:
        current /= part
        if current.is_symlink():
            raise DeploymentError(f"feature source contains a symlink: {relative}")
    try:
        source.resolve(strict=True).relative_to(repo_root.resolve(strict=True))
    except FileNotFoundError as error:
        raise DeploymentError(f"feature source does not exist: {relative}") from error
    except ValueError as error:
        raise DeploymentError(f"feature source escapes the repository: {relative}") from error
    if directory is True and not source.is_dir():
        raise DeploymentError(f"feature source must be a directory: {relative}")
    if directory is False and not source.is_file():
        raise DeploymentError(f"feature source must be a file: {relative}")


def resolve(repo_root: Path, profile_id: str, feature_id: str) -> dict[str, Any]:
    """Return a machine-readable dry-run plan for one explicit feature."""
    repo_root = repo_root.resolve()
    features = _load_features(repo_root)
    try:
        feature = features[feature_id]
    except KeyError as error:
        raise DeploymentError(f"unknown deployment feature: {feature_id}") from error

    profile = workstation.resolve(repo_root, profile_id)
    state_path = feature["state_path"]
    state = _value_at(profile["values"], state_path)
    if not isinstance(state, str) or state not in STATES:
        raise DeploymentError(
            f"profile feature state {state_path!r} must be one of: {', '.join(sorted(STATES))}"
        )
    provenance = profile["provenance"].get(state_path)
    if not isinstance(provenance, dict):
        raise DeploymentError(f"missing provenance for feature state {state_path!r}")

    for key, directory in (
        ("template_source", False),
        ("hook_source", False),
    ):
        _source_exists(repo_root, feature[key], directory=directory)
    artifacts_by_id = {artifact["id"]: artifact for artifact in profile["artifacts"]}
    missing_artifacts = sorted(
        set(feature["required_artifacts"]).difference(artifacts_by_id)
    )
    if missing_artifacts:
        raise DeploymentError(
            f"feature {feature_id!r} requires unresolved artifacts: {', '.join(missing_artifacts)}"
        )

    active = state == feature["activation_state"]
    reload_call = asdict(feature["reload"])
    return {
        "schema_version": 1,
        "profile": profile_id,
        "feature": feature_id,
        "description": feature["description"],
        "domain": feature["domain"],
        "state": state,
        "activation_state": feature["activation_state"],
        "activation": "enabled" if active else "fallback",
        "provenance": {
            "profile_state": {
                "path": state_path,
                "value": state,
                "layer": provenance["layer"],
                "kind": provenance["kind"],
            },
            "required_artifacts": [
                {
                    "id": artifact["id"],
                    "layer": artifact["layer"],
                    "source": artifact["source"],
                    "destination": artifact["destination"],
                }
                for artifact_id in feature["required_artifacts"]
                for artifact in (artifacts_by_id[artifact_id],)
            ],
        },
        "safety": {
            "dry_run": True,
            "writes_home": False,
            "requires_confirmation": True,
            "backup_required": True,
            "fallback_theme": feature["fallback_theme"],
        },
        "inputs": {
            "template_source": feature["template_source"],
            "hook_source": feature["hook_source"],
            "fallback_theme": feature["fallback_theme"],
            "dynamic_theme": feature["dynamic_theme"],
        },
        "stages": [
            {
                "id": "backup-live-state",
                "kind": "backup",
                "mutates": False,
                "paths": feature["backup_destinations"],
            },
            {
                "id": "render-dynamic-theme",
                "kind": "render",
                "mutates": True,
                "source": feature["template_source"],
                "hook": feature["hook_source"],
                "directory": feature["generated_directory"],
                "destination": feature["generated_theme"],
                "requires": ["backup-live-state"],
            },
            {
                "id": "validate-generated-assets",
                "kind": "validate",
                "mutates": False,
                "directory": feature["generated_directory"],
                "checks": [
                    "theme.conf has valid generated hex colors",
                    "panel.svg and highlight.svg exist",
                    "arrow.png and radio.png are available from the fixed fallback",
                ],
                "requires": ["render-dynamic-theme"],
            },
            {
                "id": "switch-classicui-theme",
                "kind": "atomic-switch",
                "mutates": True,
                "destination": feature["selector_destination"],
                "opt_in_destination": feature["opt_in_destination"],
                "from": feature["fallback_theme"],
                "to": feature["dynamic_theme"],
                "requires": ["validate-generated-assets"],
            },
            {
                "id": "reload-classicui",
                "kind": "dbus-reload",
                "mutates": True,
                "call": reload_call,
                "requires": ["switch-classicui-theme"],
            },
        ],
        "rollback": {
            "trigger": "any failed stage after backup-live-state",
            "steps": [
                {
                    "id": "restore-classicui-theme",
                    "kind": "restore",
                    "destination": feature["selector_destination"],
                    "from_backup": True,
                },
                {
                    "id": "remove-or-restore-generated-theme",
                    "kind": "restore",
                    "paths": [
                        path
                        for path in feature["rollback_destinations"]
                        if path != feature["selector_destination"]
                    ],
                    "from_backup": True,
                },
                {
                    "id": "reload-classicui-fallback",
                    "kind": "dbus-reload",
                    "call": reload_call,
                },
            ],
        },
        "planning_only": True,
    }


def format_plan(result: dict[str, Any]) -> str:
    lines = [
        f"UTOPIA DEPLOYMENT PLAN — {result['profile']} / {result['feature']}",
        "",
        f"Description: {result['description']}",
        f"State: {result['state']} ({result['activation']})",
        f"State provenance: {result['provenance']['profile_state']['layer']}",
        "Safety: dry-run only; writes no files; explicit confirmation required for apply.",
        f"Fallback theme: {result['safety']['fallback_theme']}",
        "",
        "Stages:",
    ]
    for index, stage in enumerate(result["stages"], start=1):
        detail = stage["kind"]
        if "destination" in stage:
            detail += f" -> {stage['destination']}"
            if "opt_in_destination" in stage:
                detail += f"; opt-in -> {stage['opt_in_destination']}"
        elif "paths" in stage:
            detail += f" ({', '.join(stage['paths'])})"
        lines.append(f"  [{index:02d}] {stage['id']}: {detail}")
    lines.extend(
        [
            "",
            "Rollback:",
            "  restore the selector and generated theme from the timestamped backup,",
            "  then reload Classic UI through the declared session D-Bus call.",
            "",
            "Planning only: no files were read from or written to HOME.",
        ]
    )
    return "\n".join(lines)
