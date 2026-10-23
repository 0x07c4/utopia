# Utopia Shortcuts

This plugin is one part of the broader
[desktop interaction design](../../../../docs/design/desktop-interaction.md).
That document distinguishes branch goals and proposals from this first
implementation; this README describes the implemented plugin and its limits.
The [runtime validation incident record](../../../../docs/journal/2026-10-23-noctalia-plugin-runtime-validation.md)
documents the provider-registration and callback-timeout failures, the actual
regression checks, and the distinction between callback and pointer acceptance.

An independently implemented, read-only Noctalia panel for Niri bindings.
`Super+/` is the only help keybinding; the former native `Super+Shift+Esc` binding
was removed at the maintainer's request. The guide uses the shell's current
palette, fonts, native search/select controls, and a bounded scrolling surface.
It does not dispatch, execute, copy, or edit any binding.

## Interaction

- The existing bar launcher provides a mouse-accessible route: search for
  快捷键, 帮助, shortcuts or hotkeys and select the localized help result.
  Its subtitle teaches Super+/. The plugin's `/keys` provider also lists this
  result without a query. It opens this same guide through Noctalia's in-process
  panel API; it does not launch applications or execute a selected binding.
  No extra desktop file, bar icon or control-center tile is installed.
- Search by Chinese action name, native action name, or key name; multiple
  whitespace-separated terms must all match. Search is literal, not a regex.
  Known action metadata supplies synonyms, such as 文件夹 → file manager,
  粘贴 → clipboard, and 帮助 → shortcuts. It does not invent new bindings.
- Filter by application, window/layout, workspace, desktop, media/brightness,
  screenshot, session, or other. Arrow keys and Page Up/Down browse the results
  and reveal the selected row. Selection is informational, not an action.
- In All categories, a curated common-actions section comes first. Priorities
  describe action identities, not hard-coded keys, usage tracking, or private
  activity history. Category filters retain each action's actual category.
- Matching aliases share a row with every combination shown. Niri's
  `hotkey-overlay-title=null` hides an entry only in the native quick reference;
  it does not hide an active binding from this guide.
  Explicitly titled primary combinations precede hidden aliases, so the
  launcher shows Super+D before its still-working Super+Ctrl+Enter alias.
- Three or more consecutive matching digit bindings for workspace focus or
  column movement can share a range row, such as Super+1–9. All original rows
  remain in the model; any nonempty search expands them before matching, so
  workspace 5 shows its exact combination. Gaps, mismatched target numbers,
  function keys, custom titles, aliases, or differing behavior are not guessed
  into a range. The footer counts displayed entries separately from bindings.
- Ambiguous/session actions have secondary descriptions: screen-off does not
  lock the session, exiting normally requests confirmation (unless that binding
  explicitly skips it), and keyboard-inhibit control is a toggle. These notes
  survive custom titles and are searchable; they do not alter action behavior.
- Escape or the close button dismisses the panel. Ctrl+F returns to search;
  Ctrl+R or the refresh button re-reads the configuration. Each open resets the
  filters and reads again; no generated binding cache is stored.
- Within one configuration/locale generation, translated strings, search text,
  keycap trees and row views are reused in memory. Filtering does not rebuild
  every keycap or translate every row on each keystroke. Cached row clicks
  resolve their current filtered position rather than retaining an old index.
  Refresh clears these caches. This keeps callbacks within Noctalia 5.3.0's
  25 ms CPU budget; repeated timeouts otherwise disable all panel interaction,
  including category selection and closing.

The manifest uses an 820×600 logical-pixel floating panel. Noctalia clamps fixed
sizes to available output space; the results scroll inside a zero-minimum-height
container, keeping the header/search/footer available. This targets the laptop's
800-logical-pixel output, not an infinitely tall native overlay. Runtime visual
acceptance is distinct from parser/config validation.

## Data source and limits

`bindings.py` uses the Python standard library; Python is already declared in
`packages/arch.txt`. It reads `$XDG_CONFIG_HOME/niri/config.kdl` (or the normal
home-relative fallback) and resolves its active top-level includes in order.
It reads configuration, not Niri IPC window data, chat contents, clipboard,
notifications, shell history, or account state. It outputs only labels,
categories, keys, native action names for search, counts, and sanitized errors;
raw spawn command arguments and absolute source paths are not output.

The reader supports the KDL subset used by Utopia: nodes, properties, quoted
strings, raw strings, line continuation, line/nested block comments, disabled
nodes (`/-`), and relative includes, including missing optional includes.
It is not a general KDL parser or a replacement for `niri validate`. Unsupported
syntax (including property-level `/-` and type annotations), duplicate bindings,
missing required files, or include cycles fail closed with no partial results.
Includes must stay within the selected config directory, including resolved
symlinks. There are explicit size, depth, file, and binding limits. An error
shows a correction/refresh hint, not a stale/incomplete list or a hidden native
fallback. If the shell/plugin is unavailable, the help entry is unavailable;
no second help shortcut is installed.

The source is the current on-disk configuration, not proof that Niri loaded the
same revision. A custom compositor `--config` path is not inferred: use the
reader's `--config` option for offline checks; the live first version targets
the standard XDG config location. Labels for known native actions are Utopia's
Chinese descriptions; an explicit configuration title takes precedence.
Unknown custom actions are marked generic rather than displaying shell code.
This does not translate Niri's own native overlay title/default strings.

## Provenance

Design references were inspected, not imported or executed:

- Omarchy revision `967bbdd7346e6e2ff1a6af33c5d762ea784832cc`, MIT:
  [keybindings menu](https://github.com/omacom/omarchy/blob/967bbdd7346e6e2ff1a6af33c5d762ea784832cc/bin/omarchy-menu-keybindings).
  Borrowed product ideas: configuration-derived searchable help, readable
  aliases, ordering, and a shell-consistent surface. Its action execution is
  deliberately not adopted.
- Shorin guide revision `534b285e108d949e03e46fce39296ade9e1eaf1d`, CC-BY-SA-4.0:
  [feature description and fzf demonstration](https://github.com/SHORiN-KiWATA/Shorin-ArchLinux-Guide/blob/534b285e108d949e03e46fce39296ade9e1eaf1d/wiki/archlinux/ShorinNiri功能介绍.md).
  Its compact searchable/scrollable presentation is a visual reference only.
- [Noctalia declarative UI](https://docs.noctalia.dev/noctalia/plugins/development/declarative-ui/)
  and [runtime API](https://docs.noctalia.dev/noctalia/plugins/development/runtime-api/).
- [Launcher providers](https://docs.noctalia.dev/noctalia/plugins/development/entries/#launcher---launcher-provider).
  Noctalia 5.3.0 source revision `a33122c4208a385e19c9a252e65e2751b2c44fbb`
  (`src/launcher/panel_catalog.cpp`, `panel_provider.h`, `launcher_provider.h`)
  confirms that the built-in Panels provider names plugins from their manifest
  and defaults to prefixed search. The small dedicated provider supplies a
  localized global-search result without changing all panel search behavior.

No third-party code, screenshots, fonts, or icons are redistributed by this
plugin. Its code is Utopia-owned under the repository's Apache-2.0 license.

## Deployment and recovery

Lint the plugin, run the Python tests, and validate both composed Niri profiles
before deployment. Inspect the live keybindings and plugin enablement first.
Back up changed live files, install this directory under
`$XDG_DATA_HOME/noctalia/plugins/utopia-shortcuts`, enable `utopia/shortcuts`, and
only then switch the help binding. Preserve other plugins and local settings.
When adding an entry to an already enabled plugin on Noctalia 5.3.0, a
`config-reload` can discover the updated manifest without registering the new
launcher provider. Disable and re-enable only `utopia/shortcuts`, wait for the
background enable operation to finish, then reopen the launcher. Validate an
actual query; an enabled catalog row or successful IPC open is insufficient.
Do not deploy desktop-only Battle.net key dispatchers onto the laptop or replace
desktop live bindings with the shared file without a host-scoped diff.

Before disabling this plugin, remove or deliberately replace its `Super+/`
binding; do not leave an entry targeting a disabled panel. Retain the unrelated
wallpaper plugin. Restore only
reviewed files from the timestamped backup after checking subsequent edits;
validate Niri and Noctalia. No package, service, boot, or hardware changes are
part of this plugin.
