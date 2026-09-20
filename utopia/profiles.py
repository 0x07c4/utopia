"""Resolve layered Utopia workstation profiles with source provenance."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
import tomllib
from typing import Any, Iterator


REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
LAYER_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")
VALUE_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")
VALUE_PATH_PATTERN = re.compile(
    r"^[a-z][a-z0-9_-]*(?:\.[a-z][a-z0-9_-]*)*$"
)
PACKAGE_PATTERN = re.compile(r"^[a-z0-9@._+:-]+$")
LAYER_KINDS = {"system", "hardware", "workstation", "host", "experiment"}
PACKAGE_INTENTS = ("required", "optional", "disabled")


class ProfileError(ValueError):
    """Raised when a profile cannot be resolved safely and unambiguously."""


@dataclass(frozen=True)
class Layer:
    identifier: str
    kind: str
    description: str
    overrides: tuple[str, ...]
    values: dict[str, Any]
    source: Path


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as source:
            result = tomllib.load(source)
    except FileNotFoundError as error:
        raise ProfileError(f"profile input does not exist: {path}") from error
    except tomllib.TOMLDecodeError as error:
        raise ProfileError(f"invalid TOML in {path}: {error}") from error
    if not isinstance(result, dict):
        raise ProfileError(f"TOML root must be a table: {path}")
    return result


def _check_keys(
    table: dict[str, Any], *, allowed: set[str], required: set[str], context: str
) -> None:
    missing = required.difference(table)
    unknown = set(table).difference(allowed)
    if missing:
        raise ProfileError(f"{context} is missing: {', '.join(sorted(missing))}")
    if unknown:
        raise ProfileError(f"{context} has unknown keys: {', '.join(sorted(unknown))}")


def _string(table: dict[str, Any], key: str, context: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value:
        raise ProfileError(f"{context}.{key} must be a non-empty string")
    return value


def _string_list(table: dict[str, Any], key: str, context: str) -> list[str]:
    value = table.get(key)
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ProfileError(f"{context}.{key} must be a list of non-empty strings")
    if len(value) != len(set(value)):
        raise ProfileError(f"{context}.{key} contains duplicates")
    return value


def _relative(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as error:
        raise ProfileError(f"profile input escapes the repository: {path}") from error


def _validate_value(value: Any, path: str) -> None:
    if isinstance(value, dict):
        if not value:
            raise ProfileError(f"{path} must not be an empty table")
        for key, child in value.items():
            if not isinstance(key, str) or not VALUE_KEY_PATTERN.fullmatch(key):
                raise ProfileError(f"{path} contains an unsupported key: {key!r}")
            _validate_value(child, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _validate_value(child, f"{path}[{index}]")
        return
    if type(value) not in (str, int, float, bool):
        raise ProfileError(f"{path} is not JSON-compatible")
    if isinstance(value, str) and not value:
        raise ProfileError(f"{path} must not be an empty string")
    if isinstance(value, float) and not math.isfinite(value):
        raise ProfileError(f"{path} must be a finite number")


def _flatten(values: dict[str, Any], prefix: tuple[str, ...] = ()) -> Iterator[tuple[str, Any]]:
    for key in sorted(values):
        value = values[key]
        path = (*prefix, key)
        if isinstance(value, dict):
            yield from _flatten(value, path)
        else:
            yield ".".join(path), value


def _set_nested(target: dict[str, Any], dotted_path: str, value: Any) -> None:
    parts = dotted_path.split(".")
    parent = target
    for part in parts[:-1]:
        existing = parent.setdefault(part, {})
        if not isinstance(existing, dict):
            raise ProfileError(f"incompatible value shape at {dotted_path}")
        parent = existing
    parent[parts[-1]] = deepcopy(value)


def _parse_layer(path: Path, repo_root: Path) -> Layer:
    data = _load_toml(path)
    _check_keys(
        data,
        allowed={"schema_version", "layer", "values"},
        required={"schema_version", "layer", "values"},
        context=_relative(path, repo_root),
    )
    if data["schema_version"] != 1:
        raise ProfileError(f"{_relative(path, repo_root)} schema_version must be 1")
    metadata = data["layer"]
    values = data["values"]
    if not isinstance(metadata, dict):
        raise ProfileError(f"{_relative(path, repo_root)}.layer must be a table")
    if not isinstance(values, dict) or not values:
        raise ProfileError(f"{_relative(path, repo_root)}.values must be a non-empty table")
    _check_keys(
        metadata,
        allowed={"id", "kind", "description", "overrides"},
        required={"id", "kind", "description", "overrides"},
        context=f"{_relative(path, repo_root)}.layer",
    )
    identifier = _string(metadata, "id", "layer")
    if not LAYER_ID_PATTERN.fullmatch(identifier):
        raise ProfileError(f"invalid layer id: {identifier!r}")
    kind = _string(metadata, "kind", "layer")
    if kind not in LAYER_KINDS:
        raise ProfileError(f"layer {identifier!r} has unsupported kind: {kind!r}")
    description = _string(metadata, "description", "layer")
    overrides = _string_list(metadata, "overrides", "layer")
    for override in overrides:
        if not VALUE_PATH_PATTERN.fullmatch(override):
            raise ProfileError(f"layer {identifier!r} has invalid override: {override!r}")
    _validate_value(values, "values")
    return Layer(
        identifier=identifier,
        kind=kind,
        description=description,
        overrides=tuple(overrides),
        values=values,
        source=path,
    )


def load_layer_index(repo_root: Path) -> dict[str, Layer]:
    layers_root = repo_root / "profiles/layers"
    if not layers_root.is_dir():
        raise ProfileError(f"layer directory does not exist: {layers_root}")
    result: dict[str, Layer] = {}
    for path in sorted(layers_root.rglob("*.toml")):
        layer = _parse_layer(path, repo_root)
        if layer.identifier in result:
            first = _relative(result[layer.identifier].source, repo_root)
            second = _relative(path, repo_root)
            raise ProfileError(
                f"duplicate layer id {layer.identifier!r}: {first}, {second}"
            )
        result[layer.identifier] = layer
    return result


def _load_profile(repo_root: Path, profile_id: str) -> tuple[str, str, list[str], Path]:
    if not PROFILE_ID_PATTERN.fullmatch(profile_id):
        raise ProfileError(f"invalid profile id: {profile_id!r}")
    path = repo_root / "profiles" / f"{profile_id}.toml"
    data = _load_toml(path)
    _check_keys(
        data,
        allowed={"schema_version", "profile"},
        required={"schema_version", "profile"},
        context=_relative(path, repo_root),
    )
    if data["schema_version"] != 1:
        raise ProfileError(f"{_relative(path, repo_root)} schema_version must be 1")
    metadata = data["profile"]
    if not isinstance(metadata, dict):
        raise ProfileError(f"{_relative(path, repo_root)}.profile must be a table")
    _check_keys(
        metadata,
        allowed={"id", "description", "layers"},
        required={"id", "description", "layers"},
        context=f"{_relative(path, repo_root)}.profile",
    )
    identifier = _string(metadata, "id", "profile")
    if identifier != profile_id:
        raise ProfileError(
            f"profile id {identifier!r} does not match file name {profile_id!r}"
        )
    description = _string(metadata, "description", "profile")
    layers = _string_list(metadata, "layers", "profile")
    if not layers:
        raise ProfileError(f"profile {profile_id!r} must select at least one layer")
    if not all(LAYER_ID_PATTERN.fullmatch(layer) for layer in layers):
        raise ProfileError(f"profile {profile_id!r} contains an invalid layer id")
    return identifier, description, layers, path


def _validate_package_intent(values: dict[str, Any]) -> None:
    packages = values.get("packages")
    if packages is None:
        return
    if not isinstance(packages, dict):
        raise ProfileError("values.packages must be a table")
    if set(packages) != set(PACKAGE_INTENTS):
        raise ProfileError(
            "values.packages must define required, optional, and disabled"
        )
    seen: dict[str, str] = {}
    for intent in PACKAGE_INTENTS:
        package_list = packages[intent]
        if not isinstance(package_list, list) or not all(
            isinstance(package, str) and PACKAGE_PATTERN.fullmatch(package)
            for package in package_list
        ):
            raise ProfileError(f"values.packages.{intent} contains an invalid package")
        if len(package_list) != len(set(package_list)):
            raise ProfileError(f"values.packages.{intent} contains duplicates")
        for package in package_list:
            previous = seen.get(package)
            if previous:
                raise ProfileError(
                    f"package {package!r} appears in both {previous} and {intent}"
                )
            seen[package] = intent


def resolve_profile(repo_root: Path, profile_id: str) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    identifier, description, requested_layers, profile_path = _load_profile(
        repo_root, profile_id
    )
    layer_index = load_layer_index(repo_root)
    missing = [layer for layer in requested_layers if layer not in layer_index]
    if missing:
        raise ProfileError(
            f"profile {profile_id!r} references unknown layers: {', '.join(missing)}"
        )

    values: dict[str, Any] = {}
    provenance: dict[str, dict[str, str]] = {}
    resolved_layers: list[dict[str, str]] = []
    existing_paths: set[str] = set()

    for layer_id in requested_layers:
        layer = layer_index[layer_id]
        used_overrides: set[str] = set()
        for dotted_path, value in _flatten(layer.values):
            prefix_conflicts = [
                prior
                for prior in existing_paths
                if prior != dotted_path
                and (
                    prior.startswith(f"{dotted_path}.")
                    or dotted_path.startswith(f"{prior}.")
                )
            ]
            if prefix_conflicts:
                raise ProfileError(
                    f"layer {layer.identifier!r} changes the shape of {dotted_path!r}; "
                    f"conflicts with {prefix_conflicts[0]!r}"
                )
            if dotted_path in existing_paths:
                if dotted_path not in layer.overrides:
                    owner = provenance[dotted_path]["layer"]
                    raise ProfileError(
                        f"layer {layer.identifier!r} overrides {dotted_path!r} from "
                        f"{owner!r} without declaring it"
                    )
                used_overrides.add(dotted_path)
            _set_nested(values, dotted_path, value)
            existing_paths.add(dotted_path)
            provenance[dotted_path] = {
                "layer": layer.identifier,
                "kind": layer.kind,
                "source": _relative(layer.source, repo_root),
            }
        unused_overrides = set(layer.overrides).difference(used_overrides)
        if unused_overrides:
            raise ProfileError(
                f"layer {layer.identifier!r} declares unused overrides: "
                + ", ".join(sorted(unused_overrides))
            )
        resolved_layers.append(
            {
                "id": layer.identifier,
                "kind": layer.kind,
                "description": layer.description,
                "source": _relative(layer.source, repo_root),
            }
        )

    _validate_package_intent(values)
    return {
        "schema_version": 1,
        "profile": identifier,
        "description": description,
        "source": _relative(profile_path, repo_root),
        "layers": resolved_layers,
        "values": values,
        "provenance": dict(sorted(provenance.items())),
    }


def format_profile(result: dict[str, Any]) -> str:
    lines = [
        f"UTOPIA PROFILE — {result['profile']}",
        "",
        result["description"],
        "",
        "Layers:",
    ]
    for index, layer in enumerate(result["layers"], start=1):
        lines.append(
            f"  [{index:02d}] {layer['id']} ({layer['kind']}) — {layer['source']}"
        )
    lines.extend(("", "Resolved values:"))
    flattened = dict(_flatten(result["values"]))
    for path in sorted(flattened):
        value = json.dumps(flattened[path], ensure_ascii=False, sort_keys=True)
        owner = result["provenance"][path]["layer"]
        lines.append(f"  {path} = {value}  <- {owner}")
    return "\n".join(lines)
