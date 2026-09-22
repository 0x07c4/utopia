"""Command-line entry point for Utopia planning tools."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from utopia import artifacts, audit, profiles, workstation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m utopia")
    subcommands = parser.add_subparsers(dest="command", required=True)
    profile = subcommands.add_parser("profile", help="resolve a workstation profile")
    profile.add_argument("profile_id")
    profile.add_argument("--json", action="store_true", dest="as_json")
    profile.add_argument(
        "--repo-root", type=Path, default=profiles.REPO_ROOT, help=argparse.SUPPRESS
    )
    audit_command = subcommands.add_parser(
        "audit", help="compare resolved artifacts with a live home directory"
    )
    audit_command.add_argument("profile_id")
    audit_command.add_argument("--json", action="store_true", dest="as_json")
    audit_command.add_argument("--home", type=Path, default=Path.home())
    audit_command.add_argument(
        "--repo-root", type=Path, default=profiles.REPO_ROOT, help=argparse.SUPPRESS
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "profile":
            result = workstation.resolve(args.repo_root, args.profile_id)
            if args.as_json:
                print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
            else:
                print(workstation.format_plan(result))
            return 0
        if args.command == "audit":
            result = audit.audit_home(args.repo_root, args.profile_id, args.home)
            if args.as_json:
                print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
            else:
                print(audit.format_audit(result))
            return 1 if audit.has_drift(result) else 0
    except (profiles.ProfileError, artifacts.ArtifactError, audit.AuditError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
