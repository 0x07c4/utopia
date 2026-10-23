## Summary

Adding a launcher provider to an enabled local plugin leaves it unavailable
after `config-reload` until the plugin is disabled and enabled again. Compare
enabled, winning manifest contents and paths during refresh, then reconcile
manifest-only changes through the existing plugin-change callback.

Unchanged config and manifests preserve running entries. Script files retain
their existing hot-reload path. Source export/update completions also advance
the applied manifest snapshot.

## Motivation

The documented local-development workflow says manifest edits take effect on
the next config reload. The current config-equality guard skips both rescanning
and runtime reconciliation when only `plugin.toml` changes.

A minimal plugin reproduced this on 5.3.0 in a disposable nested session:
zero query callbacks after adding its provider and reloading, then one after
disable/enable. With this patch based on `98c0d16389a306f33169d70bb044f0b6082dcc8b`,
the same query produces a callback immediately after reload.

## Type of Change

- [x] Bug fix

## Testing

- Built `noctalia`, `plugin_lifecycle_test`, `plugin_manifest_test` and
  `plugin_git_export_test` with GCC 16.2.1 in a separate temporary checkout.
- `meson test -C build --no-rebuild plugin_lifecycle plugin_manifest plugin_git_export --print-errorlogs`: all three pass.
- Lifecycle checks exercise provider addition, same-size/same-mtime metadata
  edits, entry removal, manifest disappearance/recovery, unchanged reloads and
  script-only edits through the actual manager/registry.
- Restoring the original config-only early-return guard makes the lifecycle
  regression fail at the first expected manifest reconciliation; restoring
  the fix passes.
- Repeated the real-shell reproduction with the final binary in nested Niri
  26.04, independent XDG directories and a separate D-Bus session. Callback
  counts: panel-only baseline 0, manifest addition plus reload 1, re-enable 1.
- `just format` with clang-format 23.1.3; excluded an unrelated pre-existing
  formatting change from this patch.
- `clang-tidy -p build --warnings-as-errors='*' src/scripting/plugin_manager.cpp tests/plugin_lifecycle_test.cpp` and `git diff --check` pass.

## Manual Coverage

- [x] Tested on Niri

## Checklist

- [x] This PR is ready for review, or it is marked as Draft.
- [x] I read and followed the relevant guidance in `CONTRIBUTING.md`.
- [x] I ran `just format` with clang-format v22+ installed, or this PR has no code changes.
- [x] I ran the relevant build or test commands, or explained why they were not run.
- [x] I self-reviewed the changes.
- [x] I checked for new warnings or errors.
- [x] I updated user-facing documentation in [`docs/user/`](../docs/user/) when this PR changes documented behavior or configuration, or this PR does not require documentation changes.
- [x] I added or updated `assets/translations/en.json`, or this PR adds no new user-facing strings.
- [x] I did not edit non-English translation files unless this PR is explicitly for translation tooling, an import/export sync, or a maintainer-requested locale change.
- [x] I used the existing canonical names for config keys, IPC names, paths, and identifiers.

## Additional Notes

This restores the already documented reload behavior, with no new configuration
or user-facing strings. Runtime testing covers the isolated Niri setup above;
other compositors, multiple monitors and different scaling values were not tested.
