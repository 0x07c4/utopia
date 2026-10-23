# Noctalia manifest reload candidate

This directory preserves a reviewable upstream patch independently of temporary
build directories. It is not deployed by a Utopia profile and does not replace
the installed Noctalia package.

- Upstream: <https://github.com/noctalia-dev/noctalia>.
- Base: `98c0d16389a306f33169d70bb044f0b6082dcc8b`.
- Contribution: [Noctalia PR #5014](https://github.com/noctalia-dev/noctalia/pull/5014),
  open and ready for review, commit `9b1278ced8a9867c3c8308d5c12e4efd0c330d73`.
- Patch: [`manifest-reload.patch`](manifest-reload.patch).
- License: MIT, including upstream context and these proposed contributions;
  see [`LICENSE`](LICENSE). Utopia's root Apache-2.0 default does not apply to
  the patch.
- Evidence: [isolated reproduction and report draft](../../journal/2026-10-23-noctalia-manifest-reload-report.md).

The candidate snapshots the content and source path of enabled, winning
manifests independently of config-section change flags. A manifest-only edit
reconciles plugin runtimes through the existing source-update callback. An
unchanged config/manifest pair leaves runtimes alone; script hot reload remains
owned by existing script watchers. Source export/update completions update the
applied snapshot as well.

Lifecycle regression checks cover provider addition, same-size/same-timestamp
metadata edits, entry removal, manifest disappearance/recovery, unchanged reloads
and script-only edits. They exercise the actual manager and registry rather
than a separate model of the implementation.

## Validation status

Full compilation of the shell and three related test executables succeeded.
`plugin_lifecycle`, `plugin_manifest` and `plugin_git_export` pass. Temporarily
restoring the original config-only early-return guard makes the lifecycle
regression fail at its first expected reconciliation; restoring the candidate
passes. This is a guard-level negative control, not a claim that an unmodified
latest-main shell was run.

The final binary passes the same isolated real-shell reproduction: panel-only
baseline 0 query callbacks, manifest addition plus config reload 1, disable and
re-enable 1. Original packaged 5.3.0 gave 0, 0, 1. The nested Niri and shell
exited; normal desktop configuration and installed Noctalia were preserved.

Upstream `just format` ran with clang-format 23.1.3; an unrelated formatter-only
change was excluded. Targeted clang-tidy with warnings-as-errors and diff checks
pass. Temporary Meson/Ninja/just tools and JSON/STB headers stayed outside Git;
no system package was installed. The PR's initial template and triage checks
passed; those checks are separate from the local build/runtime evidence and
do not constitute upstream review or merge. Other compositors and multi-monitor
behavior were not tested. The contribution is ready for upstream review and
has not been merged; the initial Draft state was removed after validation.

Apply to an independent upstream checkout at the base revision with
`git apply <path-to-manifest-reload.patch>`. Follow upstream `BUILDING.md` and
`CONTRIBUTING.md`. Build the shell and `plugin_lifecycle_test`, run the lifecycle
checks, and repeat the isolated reproduction with the resulting binary.
Keep real user config and session services outside the experiment.
