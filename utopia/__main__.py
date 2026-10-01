"""Command-line entry point for Utopia planning tools."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from utopia import artifacts, audit, deployment, fcitx_deploy, profiles, workstation


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
    plan = subcommands.add_parser(
        "plan", help="resolve an explicit host-scoped deployment plan"
    )
    plan.add_argument("profile_id")
    plan.add_argument("feature_id")
    plan.add_argument("--json", action="store_true", dest="as_json")
    plan.add_argument(
        "--repo-root", type=Path, default=profiles.REPO_ROOT, help=argparse.SUPPRESS
    )
    deploy = subcommands.add_parser("deploy", help="preview or apply the Fcitx wallpaper adapter")
    deploy.add_argument("profile_id")
    deploy.add_argument("feature_id")
    deploy.add_argument("--home", type=Path, default=Path.home())
    deploy.add_argument("--wallpaper", type=Path)
    deploy.add_argument("--apply", action="store_true")
    deploy.add_argument("--confirm-host")
    deploy.add_argument("--no-reload", action="store_true", help="isolate an alternate home from session D-Bus")
    deploy.add_argument("--json", action="store_true", dest="as_json")
    deploy.add_argument("--repo-root", type=Path, default=profiles.REPO_ROOT, help=argparse.SUPPRESS)
    rollback = subcommands.add_parser("rollback", help="preview or restore one Fcitx deployment backup")
    rollback.add_argument("profile_id")
    rollback.add_argument("record_id")
    rollback.add_argument("--home", type=Path, default=Path.home())
    rollback.add_argument("--apply", action="store_true")
    rollback.add_argument("--confirm-host")
    rollback.add_argument("--json", action="store_true", dest="as_json")
    rollback.add_argument("--repo-root", type=Path, default=profiles.REPO_ROOT, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command in {"deploy", "rollback"}:
            if args.apply and args.confirm_host != args.profile_id:
                raise deployment.DeploymentError("--apply requires --confirm-host matching the profile")
            if args.command == "deploy":
                if args.apply:
                    if args.wallpaper is None:
                        raise deployment.DeploymentError("--apply requires an explicit --wallpaper")
                    result = fcitx_deploy.apply(
                        args.repo_root, args.profile_id, args.feature_id, args.home,
                        args.wallpaper, confirm_host=args.confirm_host,
                        reload_session=not args.no_reload,
                    )
                else:
                    result = fcitx_deploy.preview(args.repo_root, args.profile_id, args.feature_id, args.home)
            else:
                result = fcitx_deploy.rollback(
                    args.repo_root, args.profile_id, args.record_id, args.home,
                    confirm_host=args.confirm_host if args.apply else None,
                )
            if args.as_json:
                print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
            elif result.get("dry_run"):
                summary = deployment.format_plan(result["plan"])
                print(summary.replace("Planning only: no files were read from or written to HOME.",
                                      "Dry-run: live files were inspected; no files were changed."))
                print("Live prerequisites and policy conflicts checked; no files changed.")
            else:
                print(f"Fcitx deployment: {result['status']}")
                if "id" in result:
                    print(f"Record: {result['id']}")
            return 0
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
        if args.command == "plan":
            result = deployment.resolve(
                args.repo_root, args.profile_id, args.feature_id
            )
            if args.as_json:
                print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
            else:
                print(deployment.format_plan(result))
            return 0
    except (
        profiles.ProfileError,
        artifacts.ArtifactError,
        audit.AuditError,
        deployment.DeploymentError,
        OSError,
    ) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
