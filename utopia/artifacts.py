"""Load and resolve home-relative artifacts for a workstation profile."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
import re
import subprocess
import tomllib
from typing import Any

from utopia import profiles


ARTIFACT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")
DOMAIN_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")
VALIDATOR_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")
KINDS = {"file", "tree", "gitlink"}
STATES = {"managed", "unmanaged", "experimental"}
FORBIDDEN_DESTINATIONS = (
    ".config/gh",
    ".gnupg",
    ".local/share/fcitx5/rime/build",
    ".local/share/keyrings",
    ".zsh_history",
)


class ArtifactError(ValueError):
    """Raised when an artifact map is unsafe or ambiguous."""


@dataclass(frozen=True)
class Artifact:
    identifier: str
    layer: str
    domain: str
    source: str
    destination: str
    kind: str
    state: str
    capture: bool
    deploy: bool
    validators: tuple[str, ...]
    excludes: tuple[str, ...]
    mode: str | None
    replaces: str | None


def _relative(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as error:
        raise ArtifactError(f"artifact input escapes the repository: {path}") from error


def _load_toml(path: Path, repo_root: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as source:
            data = tomllib.load(source)
    except FileNotFoundError as error:
        raise ArtifactError(f"artifact map does not exist: {path}") from error
    except tomllib.TOMLDecodeError as error:
        raise ArtifactError(f"invalid TOML in {_relative(path, repo_root)}: {error}") from error
    if not isinstance(data, dict):
        raise ArtifactError("artifact map root must be a table")
    return data


def _check_keys(
    table: dict[str, Any], *, allowed: set[str], required: set[str], context: str
) -> None:
    missing = required.difference(table)
    unknown = set(table).difference(allowed)
    if missing:
        raise ArtifactError(f"{context} is missing: {', '.join(sorted(missing))}")
    if unknown:
        raise ArtifactError(
            f"{context} has unknown keys: {', '.join(sorted(unknown))}"
        )


def _string(table: dict[str, Any], key: str, context: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value:
        raise ArtifactError(f"{context}.{key} must be a non-empty string")
    return value


def _strings(table: dict[str, Any], key: str, context: str) -> tuple[str, ...]:
    value = table.get(key, [])
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ArtifactError(f"{context}.{key} must be a list of non-empty strings")
    if len(value) != len(set(value)):
        raise ArtifactError(f"{context}.{key} contains duplicates")
    return tuple(value)


def _relative_posix(value: str, context: str) -> str:
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or value in {"", "."}
        or ".." in path.parts
        or value != path.as_posix()
    ):
        raise ArtifactError(f"{context} must be a normalized relative POSIX path")
    return value


def _is_forbidden_destination(destination: str) -> bool:
    if destination == ".ssh/config":
        return False
    if destination == ".ssh" or destination.startswith(".ssh/"):
        return True
    return any(
        destination == prefix or destination.startswith(f"{prefix}/")
        for prefix in FORBIDDEN_DESTINATIONS
    )


def _validate_source(repo_root: Path, artifact: Artifact) -> None:
    relative_source = PurePosixPath(artifact.source)
    if ".git" in relative_source.parts:
        raise ArtifactError(
            f"artifact {artifact.identifier!r} cannot map Git metadata directly"
        )
    source = repo_root.joinpath(*relative_source.parts)
    current = repo_root
    for part in relative_source.parts:
        current /= part
        if current.is_symlink():
            raise ArtifactError(
                f"artifact {artifact.identifier!r} source path contains symlink "
                f"{current.relative_to(repo_root).as_posix()!r}"
            )
    if artifact.kind == "gitlink":
        try:
            completed = subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_root),
                    "ls-files",
                    "--stage",
                    "--",
                    artifact.source,
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as error:
            raise ArtifactError(
                "git is required to validate gitlink artifacts"
            ) from error
        fields = completed.stdout.partition("\t")[0].split()
        if completed.returncode != 0 or len(fields) != 3 or fields[0] != "160000":
            raise ArtifactError(
                f"artifact {artifact.identifier!r} source is not a repository gitlink"
            )
        if source.exists() and not source.is_dir():
            raise ArtifactError(
                f"artifact {artifact.identifier!r} initialized gitlink must be a directory"
            )
        if (
            source.is_dir()
            and any(source.iterdir())
            and not (source / ".git").exists()
        ):
            raise ArtifactError(
                f"artifact {artifact.identifier!r} initialized gitlink has no Git metadata"
            )
        return
    try:
        source.resolve(strict=True).relative_to(repo_root.resolve(strict=True))
    except FileNotFoundError as error:
        raise ArtifactError(
            f"artifact {artifact.identifier!r} source does not exist: {artifact.source}"
        ) from error
    except ValueError as error:
        raise ArtifactError(
            f"artifact {artifact.identifier!r} source escapes the repository"
        ) from error
    if source.is_symlink():
        raise ArtifactError(
            f"artifact {artifact.identifier!r} source must not be a symlink"
        )
    if artifact.kind == "file" and not source.is_file():
        raise ArtifactError(
            f"artifact {artifact.identifier!r} source must be a file"
        )
    if artifact.kind == "tree" and not source.is_dir():
        raise ArtifactError(
            f"artifact {artifact.identifier!r} source must be a directory"
        )
    if artifact.kind == "tree":
        entries = list(source.rglob("*"))
        symlink = next((item for item in entries if item.is_symlink()), None)
        if symlink is not None:
            raise ArtifactError(
                f"artifact {artifact.identifier!r} tree contains symlink "
                f"{symlink.relative_to(source).as_posix()!r}"
            )
        git_metadata = next(
            (
                item
                for item in entries
                if ".git" in item.relative_to(source).parts
            ),
            None,
        )
        if git_metadata is not None:
            raise ArtifactError(
                f"artifact {artifact.identifier!r} tree contains Git metadata"
            )


def _parse_artifact(
    raw: Any, *, index: int, repo_root: Path, known_layers: set[str]
) -> Artifact:
    context = f"profiles/artifacts.toml.artifacts[{index}]"
    if not isinstance(raw, dict):
        raise ArtifactError(f"{context} must be a table")
    required = {
        "id",
        "layer",
        "domain",
        "source",
        "destination",
        "kind",
        "state",
        "capture",
        "deploy",
        "validators",
    }
    _check_keys(
        raw,
        allowed=required | {"excludes", "mode", "replaces"},
        required=required,
        context=context,
    )

    identifier = _string(raw, "id", context)
    layer = _string(raw, "layer", context)
    domain = _string(raw, "domain", context)
    source = _relative_posix(_string(raw, "source", context), f"{context}.source")
    destination = _relative_posix(
        _string(raw, "destination", context), f"{context}.destination"
    )
    kind = _string(raw, "kind", context)
    state = _string(raw, "state", context)
    validators = _strings(raw, "validators", context)
    excludes = _strings(raw, "excludes", context)
    mode = raw.get("mode")
    replaces = raw.get("replaces")

    if not ARTIFACT_ID_PATTERN.fullmatch(identifier):
        raise ArtifactError(f"invalid artifact id: {identifier!r}")
    if layer not in known_layers:
        raise ArtifactError(f"artifact {identifier!r} references unknown layer {layer!r}")
    if not DOMAIN_PATTERN.fullmatch(domain):
        raise ArtifactError(f"artifact {identifier!r} has invalid domain {domain!r}")
    if kind not in KINDS:
        raise ArtifactError(f"artifact {identifier!r} has unsupported kind {kind!r}")
    if state not in STATES:
        raise ArtifactError(f"artifact {identifier!r} has unsupported state {state!r}")
    if type(raw["capture"]) is not bool or type(raw["deploy"]) is not bool:
        raise ArtifactError(f"artifact {identifier!r} capture/deploy must be booleans")
    if state == "unmanaged" and (raw["capture"] or raw["deploy"]):
        raise ArtifactError(
            f"unmanaged artifact {identifier!r} cannot enable capture or deploy"
        )
    if any(not VALIDATOR_PATTERN.fullmatch(item) for item in validators):
        raise ArtifactError(f"artifact {identifier!r} has an invalid validator id")
    if kind != "tree" and excludes:
        raise ArtifactError(
            f"artifact {identifier!r} may only exclude paths from a tree"
        )
    for exclude in excludes:
        _relative_posix(exclude, f"artifact {identifier!r} exclude")
    if mode is not None and (
        not isinstance(mode, str) or not re.fullmatch(r"0[0-7]{3}", mode)
    ):
        raise ArtifactError(f"artifact {identifier!r} has invalid mode {mode!r}")
    if mode is not None and kind != "file":
        raise ArtifactError(f"artifact {identifier!r} may only set mode for a file")
    if replaces is not None and (
        not isinstance(replaces, str)
        or not ARTIFACT_ID_PATTERN.fullmatch(replaces)
        or replaces == identifier
    ):
        raise ArtifactError(f"artifact {identifier!r} has invalid replaces value")
    if _is_forbidden_destination(destination):
        raise ArtifactError(
            f"artifact {identifier!r} targets forbidden destination {destination!r}"
        )

    artifact = Artifact(
        identifier=identifier,
        layer=layer,
        domain=domain,
        source=source,
        destination=destination,
        kind=kind,
        state=state,
        capture=raw["capture"],
        deploy=raw["deploy"],
        validators=validators,
        excludes=excludes,
        mode=mode,
        replaces=replaces,
    )
    _validate_source(repo_root, artifact)
    forbidden_target = next(
        (
            target.as_posix()
            for target in _artifact_targets(repo_root, artifact)
            if _is_forbidden_destination(target.as_posix())
        ),
        None,
    )
    if forbidden_target is not None:
        raise ArtifactError(
            f"artifact {identifier!r} contains forbidden destination "
            f"{forbidden_target!r}"
        )
    return artifact


def load_artifacts(repo_root: Path) -> tuple[list[Artifact], str]:
    """Validate the complete artifact catalog, including inactive host entries."""
    repo_root = repo_root.resolve()
    path = repo_root / "profiles/artifacts.toml"
    data = _load_toml(path, repo_root)
    _check_keys(
        data,
        allowed={"schema_version", "artifacts"},
        required={"schema_version", "artifacts"},
        context=_relative(path, repo_root),
    )
    if data["schema_version"] != 1:
        raise ArtifactError("profiles/artifacts.toml schema_version must be 1")
    raw_artifacts = data["artifacts"]
    if not isinstance(raw_artifacts, list) or not raw_artifacts:
        raise ArtifactError("profiles/artifacts.toml.artifacts must be a non-empty array")

    known_layers = set(profiles.load_layer_index(repo_root))
    artifacts = [
        _parse_artifact(
            raw, index=index, repo_root=repo_root, known_layers=known_layers
        )
        for index, raw in enumerate(raw_artifacts)
    ]
    identifiers = [artifact.identifier for artifact in artifacts]
    duplicates = sorted(
        identifier for identifier in set(identifiers) if identifiers.count(identifier) > 1
    )
    if duplicates:
        raise ArtifactError(f"duplicate artifact ids: {', '.join(duplicates)}")
    return artifacts, _relative(path, repo_root)


def _is_excluded(relative_path: str, excludes: tuple[str, ...]) -> bool:
    return any(
        relative_path == exclude or relative_path.startswith(f"{exclude}/")
        for exclude in excludes
    )


def _artifact_targets(
    repo_root: Path, artifact: Artifact
) -> set[PurePosixPath]:
    destination = PurePosixPath(artifact.destination)
    if artifact.kind == "file":
        return {destination}
    if artifact.kind == "gitlink":
        return {destination}
    source = repo_root.joinpath(*PurePosixPath(artifact.source).parts)
    targets = {
        destination / item.relative_to(source).as_posix()
        for item in source.rglob("*")
        if item.is_file()
        and not _is_excluded(item.relative_to(source).as_posix(), artifact.excludes)
    }
    return targets


def _artifacts_overlap(repo_root: Path, first: Artifact, second: Artifact) -> bool:
    first_targets = _artifact_targets(repo_root, first)
    second_targets = _artifact_targets(repo_root, second)
    return any(
        first_target == second_target
        or first_target in second_target.parents
        or second_target in first_target.parents
        for first_target in first_targets
        for second_target in second_targets
    )


def resolve_artifacts(
    repo_root: Path, selected_layers: list[str]
) -> tuple[list[dict[str, Any]], str]:
    """Resolve mappings selected by ordered profile layers without touching HOME."""
    repo_root = repo_root.resolve()
    artifacts, source = load_artifacts(repo_root)
    layer_order = {layer: index for index, layer in enumerate(selected_layers)}
    selected = [artifact for artifact in artifacts if artifact.layer in layer_order]
    catalog_order = {artifact.identifier: index for index, artifact in enumerate(artifacts)}
    selected.sort(key=lambda item: (layer_order[item.layer], catalog_order[item.identifier]))

    resolved: list[Artifact] = []
    for artifact in selected:
        collisions = [
            existing
            for existing in resolved
            if _artifacts_overlap(repo_root, existing, artifact)
        ]
        if not collisions:
            if artifact.replaces is not None:
                raise ArtifactError(
                    f"artifact {artifact.identifier!r} declares unused replacement "
                    f"{artifact.replaces!r}"
                )
            resolved.append(artifact)
            continue
        collision_ids = {existing.identifier for existing in collisions}
        if artifact.replaces is None or collision_ids != {artifact.replaces}:
            owners = ", ".join(sorted(collision_ids))
            raise ArtifactError(
                f"artifact {artifact.identifier!r} destination {artifact.destination!r} "
                f"overlaps {owners}; declare the exact replacement"
            )
        resolved = [
            existing
            for existing in resolved
            if existing.identifier != artifact.replaces
        ]
        resolved.append(artifact)

    output: list[dict[str, Any]] = []
    for artifact in resolved:
        item = asdict(artifact)
        item["id"] = item.pop("identifier")
        item["validators"] = list(artifact.validators)
        item["excludes"] = list(artifact.excludes)
        if item["mode"] is None:
            del item["mode"]
        if item["replaces"] is None:
            del item["replaces"]
        output.append(item)
    return output, source
