# Noctalia manifest reload: upstream report draft

Status: the reproduction below is preserved as evidence for
[PR #5014](https://github.com/noctalia-dev/noctalia/pull/5014), ready for review.
Original runtime reproduction uses packaged Noctalia 5.3.0; the candidate fix
based on upstream main was subsequently built and tested as recorded below.

Suggested title: **[BUG] Adding a launcher provider to an enabled local plugin
does not take effect after config-reload**

## Expected behavior

The [local development workflow](https://docs.noctalia.dev/noctalia/plugins/development/workflow/)
states that manifest changes are picked up on the next config reload.
Adding a launcher provider to an already enabled local plugin should make it
queryable after `noctalia msg config-reload`, without disabling the plugin.

## Minimal reproduction

Use a disposable shell session with separate XDG config/data/state/cache/runtime
directories and a separate D-Bus session. Do not run the enable/disable steps
against a normal desktop's configuration. No Utopia bindings or help code are
required. Python below is not a plugin dependency: the plugin is Luau only.

1. Put these three files in a local plugin directory beneath
   `$XDG_DATA_HOME/noctalia/plugins/reload-probe/`. The launcher script exists
   initially, but its entry is not yet declared in the manifest.

   `plugin.toml`:

   ```toml
   id = "utopia/reload-probe"
   name = "Reload Probe"
   version = "0.1.0"
   plugin_api = 33

   [[panel]]
   id = "guide"
   entry = "panel.luau"
   width = 200
   height = 100
   ```

   `panel.luau`:

   ```lua
   function onOpen()
     panel.render(ui.label({ text = "Reload Probe" }))
   end
   ```

   `launcher.luau`:

   ```lua
   function onQuery(text)
     noctalia.log("reload-probe-query-ok")
     launcher.setResults(text, {{ id = "probe", title = "Reload Probe" }})
   end
   ```

2. Start the disposable shell with this configuration in `plugins.toml`:

   ```toml
   [plugins]
   enabled = ["utopia/reload-probe"]
   ```

3. Append the following to the plugin manifest, without changing its enabled
   state or any plugin settings:

   ```toml
   [[launcher_provider]]
   id = "search"
   entry = "launcher.luau"
   prefix = "reloadprobe"
   include_in_global_search = true
   ```

4. Run `noctalia msg config-reload`, then reopen the launcher with
   `noctalia msg panel-open launcher '/reloadprobe probe'`.
   Observe that no query marker appears in the isolated shell log.
5. Run `noctalia msg plugins disable utopia/reload-probe`, then
   `noctalia msg plugins enable utopia/reload-probe`. Wait for background
   enablement to complete, close and reopen the same launcher query.
   The query marker now appears and the provider answers.

## Observed results

On 2026-10-23, this was run using a minimal nested Niri 26.04 compositor without
`--session`, with no user autostarts, independent XDG directories and D-Bus.
The test driver checked that `NIRI_SOCKET` belonged to the disposable runtime
before issuing IPC or terminating the nested compositor. The test used a fresh
plugin rather than copying any production plugin/configuration.

The final run disabled the setup wizard and clipboard history and used offline
mode. Query callbacks were counted from a fixed marker, without recording query
contents or inspecting application history. Background enablement was allowed
to complete before the positive control.

| Stage | Observed query callbacks |
| --- | ---: |
| Panel-only baseline | 0 |
| Manifest addition followed by config reload | 0 |
| Disable and re-enable, then repeat query | 1 |

The disposable shell and compositor exited. The normal desktop's IPC remained
available and its managed plugin configuration/source matched the repository
after the experiment. Niri hosted the isolated test; the changed behavior was
controlled entirely by Noctalia's plugin enablement, without a compositor reload.

## Source-level evidence and limits

Inspected versions:

- Noctalia 5.3.0: `a33122c4208a385e19c9a252e65e2751b2c44fbb`.
- Upstream main at inspection: `98c0d16389a306f33169d70bb044f0b6082dcc8b`.

In both versions,
[PluginManager::refresh](https://github.com/noctalia-dev/noctalia/blob/98c0d16389a306f33169d70bb044f0b6082dcc8b/src/scripting/plugin_manager.cpp)
returns early when the plugin configuration equals its last applied value.
The application's config-reload callback invokes
[provider/panel rebuilding only when the plugins change flag is set](https://github.com/noctalia-dev/noctalia/blob/98c0d16389a306f33169d70bb044f0b6082dcc8b/src/app/application.cpp).
An edited manifest does not itself change the enabled IDs or plugin settings.
These guards explain the observed stale registration. Unmodified latest main
was not run as a full shell; the subsequent candidate test does not establish
that separate claim.

A GitHub issue/PR search for `repo:noctalia-dev/noctalia manifest reload`
returned six results; none identified this exact reproduction. That search is
not an exhaustive duplicate audit.

## Fix validation and contribution

The candidate at `9b1278ced8a9867c3c8308d5c12e4efd0c330d73`, based on main
`98c0d16389a306f33169d70bb044f0b6082dcc8b`, was fully built. It compares enabled,
winning manifest contents/paths and reconciles changes through the existing
plugin-change callback. Unchanged config/manifests and script-only changes do
not trigger runtime reconciliation. Source export/update completions synchronize
the snapshot. The ordinary config-reload guard is preserved for unchanged data.

Lifecycle regression checks cover addition, same-size/same-mtime metadata edits,
entry removal, manifest disappearance/recovery, unchanged reloads and script-only
edits. Restoring the original early-return guard makes the check fail at the
first expected reconciliation. Restoring the fix passes; the manifest and git
export test executables also pass. Targeted clang-tidy and upstream formatting
were run, with no unrelated formatting changes included.

The final binary passed the isolated real-shell reproduction with callback
counts **0, 1, 1**, replacing the packaged version's **0, 0, 1** above. It was not
installed over the normal desktop. Build tools and missing headers were prepared
only in temporary directories; no system package was installed.

The fix is published as an open PR and is ready for review. Initial PR-template enforcement and
maintainer-intake checks succeeded; code review and merge remain outstanding.
The [MIT-attributed patch and PR description](../upstream/noctalia/README.md)
are preserved in Utopia for continuation. The separate Utopia callback
CPU-timeout fix is outside this contribution.
