# 2026-09-20 — CachyOS desktop migration and Utopia direction

This journal preserves the context, decisions, and open questions from the
desktop reinstall and the following Utopia design discussion. It is a record of
the session, not a claim that every proposed architecture item is implemented.

## Machine context

The current target is an x86_64 desktop freshly reinstalled with CachyOS. Other
operating systems and disks were intentionally left outside the migration.
Relevant observed facts:

- Intel CPU and NVIDIA graphics
- a 4K display
- CachyOS `linux-cachyos` and `linux-cachyos-lts`
- Limine, mkinitcpio hooks, Btrfs/Snapper, and NVIDIA open modules
- Niri session with Noctalia

The repository was last updated from a laptop running Arch Linux with
`linux-cachyos-bore-lto`. Its installer and system sections are unfinished and
must not be treated as a final restore source for the desktop.

## Migration boundary

The desktop migration copied or merged personal configuration while preserving
the current CachyOS system design. The work deliberately avoided changes to:

- other operating systems or any disk layout;
- `/boot`, Limine entries, initramfs, kernels, and filesystems;
- LUKS, Btrfs subvolumes, Snapper, and system services;
- NVIDIA driver selection;
- the unfinished installer and raw package manifests.

A rollback snapshot of affected home configuration is stored outside Git under:

```text
~/.local/state/utopia-migration-backups/<timestamp>/
```

## Completed personal configuration migration

### Git and GitHub

- The Git remote and SSH authentication were configured and verified.
- Credentials, private keys, account identifiers, and Git author identity stay
  outside the tracked workstation model.

### Shell and terminal

- The CachyOS reinstall had set the login shell to Fish, but the established
  personal shell is Zsh.
- The login shell was restored to `/bin/zsh`.
- Utopia's `.zshrc`, `.zimrc`, Zim modules, Starship, zoxide, and Yazi workflow
  were restored.
- Headless agent sessions now guard Starship and `compdef` initialization so
  `TERM=dumb` validation stays quiet.
- Kitty is the selected terminal. Its Utopia configuration uses Zsh, Maple Mono
  NF CN at 13.5 pt, 0.8 background opacity, and the checked-in Matugen palette.
- WezTerm is not wanted on this workstation. It was briefly installed while
  inferring intent from an old configuration, then removed with its dedicated
  dependency and live configuration.

This established an important rule: an old application configuration does not
authorize package installation.

### Niri

The desktop's modular CachyOS Niri configuration was retained. Utopia behavior
was merged rather than copying the laptop's monolithic file.

Preserved desktop-specific state includes:

- the host-scoped display output, mode, and scale;
- current input behavior;
- CachyOS animation, blur, cursor, and session integration;
- current Noctalia and Steam window behavior.

Merged Utopia behavior includes:

- half-width default columns;
- HJKL and workspace navigation/move bindings;
- Kitty and Noctalia launcher bindings;
- screenshot bindings and localized screenshot path;
- Kitty, picture-in-picture, and related window rules.

`niri validate` passes.

### Noctalia

- The current Noctalia v5 configuration and polkit agent were retained.
- Utopia bar and idle configuration were merged.
- Visual settings were adapted to the current desktop, Tokyo Night baseline,
  Maple Mono, and a valid packaged fallback wallpaper.
- Current output-specific lock-screen state remains runtime state and is not
  copied into Git.

`noctalia config validate` passes.

### Input method

- Fcitx5 with Rime remains the selected input framework.
- `rime-ice-git` was installed and the Utopia Rime Ice schema, key bindings, and
  dictionary customization were deployed.
- Rime Ice is the active default schema with a page size of five.
- The missing Fcitx5 `classicui.conf` was identified and restored.
- The active candidate theme is `catppuccin-mocha-green` using Maple Mono NF CN.
- Fcitx5 was restarted and Rime reactivated after deployment.

### Editor and utilities

- AstroNvim is checked out at the repository gitlink
  `428b7f214fc3263c51c6c9d5a5d2a79fdf816b43`.
- Its lock file matches the Utopia submodule and headless Neovim starts cleanly.
- Bottom and Lazygit configuration remained independently managed. Configuration
  snapshots for Btop, Cava, Fastfetch, MPV, Satty, Yazi, LSFG-VK, and related
  visual tooling were later removed from the public product tree because their
  source provenance was not sufficiently isolated for redistribution.
- Starship and Kitty received small Utopia-owned or explicitly attributed
  replacement themes.
- Bottom, Cava, Lazygit, MPV, and Satty were installed while completing this
  migration. Their future package status should be classified explicitly rather
  than inferred from configuration presence.

## Configuration deliberately not copied

- GTK and xsettings generated theme state
- old XDG portal and MIME defaults
- user directory definitions
- NVIDIA settings
- legacy autostarts for unavailable or machine-specific applications
- Thunar actions with missing dependencies
- Fish runtime variables
- the old npm prefix, which conflicts with the current Codex/npm layout
- old scripts that install/remove packages or rewrite themes
- Rime user databases and generated build state
- Noctalia GUI state

These omissions should remain visible decisions, not silently forgotten files.

## Utopia direction discussed

The project should evolve from a personal dotfiles snapshot into an open-source
Linux workstation engineering product, grounded in real daily-use systems but
designed so other people can understand and adapt it.

The central idea is:

```text
Arch            → stable and transparent base
Utopia          → personal desktop and workflow
CachyOS work    → kernel, scheduler, compiler, and performance experiment layer
```

CachyOS is interesting because of its engineering: BORE, EEVDF, sched-ext,
Clang, LTO, AutoFDO, Propeller, x86-64-v3/v4, and performance methodology.
`linux-cachyos-bore-lto` is a useful entry point into scheduling, interactive
latency, LLVM/Clang, and LTO rather than merely another long package name.

Omarchy and CachyOS were distinguished as different reference projects:

```text
Omarchy  → desktop UX, workflow, and opinionated defaults
CachyOS  → kernel, compiler, CPU, and performance engineering
```

Utopia may learn from both without delegating its design to either.

## Multi-machine and repository model

The first proposal of only `common` and `hosts` was refined. The long-term
organization should be domain-oriented:

```text
desktop/
editor/
shell/
system/
kernel/
scheduler/
toolchain/
tuning/
benchmarks/
hosts/
profiles/
bootstrap/
ideas/
docs/
tests/
```

Profiles and host overlays are the composition mechanism beneath those domains,
not a competing top-level dotfiles hierarchy.

A resolved machine combines:

```text
system base
+ hardware support
+ shared Utopia workstation capabilities
+ host-specific facts and overrides
+ optional experiment
```

Long-lived desktop and laptop Git branches were rejected because shared shell,
desktop, editor, and input changes would drift. Short-lived feature branches and
focused experiment branches should merge into one `main`.

## Synchronization behavior required

The previous broad live-home synchronization script was removed rather than
carried into the new profile model.

The intended unified tool should provide commands equivalent to:

```text
audit   → compare repository, live state, and last deployment
capture → preview live changes that could return to the repository
deploy  → back up and apply a resolved profile
plan    → produce human and machine-readable actions
```

Requirements include:

- dry-run by default;
- explicit host/profile selection;
- shared resolver for capture, deploy, audit, recovery, and bootstrap;
- source provenance for every resolved value;
- declared and checked override collisions;
- no deletion propagation without an explicit prune option;
- no automatic commit or push;
- deployment state recorded outside Git;
- three-way conflict detection using the last deployed commit;
- package intent separate from configuration presence.

## Agent-readable rebuild requirement

Utopia should let a new agent reconstruct the system efficiently without relying
on conversation history. The repository now has a root `AGENTS.md` and an ideas
capture system, but the executable model remains future work.

The target design includes:

- schema-validated TOML or JSON inputs;
- human-readable and JSON plans;
- `managed`, `unmanaged`, and `experimental` scopes;
- idempotent and resumable stages;
- checkpoints and post-stage validation;
- explicit destructive review boundaries;
- sanitized inventory separate from desired state;
- documented rollback for every tuning and experiment.

## Performance research rules

- Compatibility can be checked across both machines.
- Scheduler, kernel, and compiler performance claims must compare variants on
  the same host.
- Experiments record exact kernel, configuration, compiler, governor, load,
  temperature, run count, and result distribution.
- Experimental kernels add boot entries and retain stable/LTS fallbacks.
- Git stores inputs, provenance, checksums, reports, and conclusions rather than
  large raw traces or compiled kernels.

## Theme direction

Visual work should eventually have one theme source that can generate or verify
Kitty, Fcitx5, Noctalia, Satty, SwayOSD, and related palettes. This avoids a
desktop where each component accidentally uses a different visual system.

## Idea capture

Transient thoughts now have a low-friction path:

```sh
灵感 "idea text"
```

This appends to `ideas/inbox.md`. Mature ideas move into dated documents with a
status and links to later decisions or implementation. Ideas are intentionally
kept distinct from current facts and accepted architecture.

## Immediate next steps

1. Define tests for layered profile resolution before moving live files.
2. Define the minimal profile and path-mapping schema.
3. Replace duplicated Bash/Python path lists with one resolver.
4. Split Niri shared behavior from laptop and desktop output/input layers.
5. Capture the current CachyOS desktop as a baseline without importing system
   runtime state.
6. Render and validate both host profiles into temporary homes.
7. Update recovery and bootstrap to consume the same resolved plan.
8. Add inventory and benchmark schemas only after safe deployment works.

No profile migration, installer redesign, or system performance experiment is
implemented merely by this journal. It preserves the reasoning so later work can
continue without reconstructing the conversation.

## Progress note — 2026-09-21

The first read-only profile contract is now implemented on
`feat/multi-layer-profiles`:

- `profiles/arch-laptop.toml` composes Arch, Intel laptop, shared workstation,
  laptop display, and BORE/LTO experiment layers.
- `profiles/cachyos-desktop.toml` composes CachyOS, NVIDIA desktop, shared
  workstation, and desktop display layers.
- JSON schemas document profile and layer inputs.
- `python -m utopia profile <id>` resolves a human-readable plan.
- `--json` emits stable machine-readable values and provenance.
- Later layers cannot replace a value unless they declare its exact dotted path.
- Stale override declarations, duplicate layer IDs, unknown keys, unsafe value
  shapes, and overlapping package intent are rejected.
- Kitty is classified as required and WezTerm as disabled; configuration no
  longer implies installation intent.
- Boot, kernel, filesystems, storage, and services remain explicitly unmanaged.

Seven new profile tests and all 67 existing installer tests pass. This milestone
does not yet map files, capture live configuration, deploy profiles, or alter the
running system.

## Progress note — artifact map and Niri domain split

The next read-only milestone adds `profiles/artifacts.toml`. It declares the
reviewed repository source and home-relative destination for shell, terminal,
editor, desktop, input, and supporting tool configuration. The same profile
command now includes those artifacts in human-readable and JSON output, while
remaining unable to copy or delete live files.

This work also clarified that machine differences are not Utopia's focus.
Domains and shared workstation behavior remain primary; host data is limited to
facts that cannot be shared. Niri is the first concrete example:

- the current modular configuration was captured byte-for-byte under
  `desktop/niri/`;
- the current `keybinds.kdl`, including `Mod+Q` for `close-window`, was not
  edited during capture;
- only `display.kdl` lives under each host;
- the shared tree excludes that display file from future capture;
- both laptop and desktop compositions pass `niri validate` in temporary
  directories.

The artifact resolver rejects path traversal, symlinks, embedded Git metadata,
sensitive destinations, unknown layers, malformed state, and ambiguous target
collisions. It intentionally does not implement capture or deployment yet. That
next stage still needs dry-run diffs, last-deployment state, three-way conflict
detection, backups, and validator execution before it can safely touch `$HOME`.

## Scope clarification — full workstation lifecycle

The current safety boundary must not become an accidental project boundary.
Computer architecture, firmware, Limine policy and entries, kernels, initramfs,
storage, encryption, snapshots, drivers, services, and recovery all belong to
Utopia's long-term scope alongside the desktop and development environment.

They remain `unmanaged` today because the new resolver cannot yet change them
safely. This state means “model or observe without applying,” not “out of
scope.” Hardware architecture should be reusable capability data; boot policy
belongs to the system domain; concrete disks, identifiers, and boot entries are
host facts. Any transition to managed state requires a reviewable plan, machine
preconditions, a preserved boot or storage fallback, validation, and tested
recovery.

## Progress note — read-only home audit and shell ownership

The artifact plan can now be compared with a live home using
`python -m utopia audit <profile>`. The command reports matching, drifted,
missing, and unsafe artifacts in human-readable or JSON form. It does not write
either side, reveal the absolute home path, follow symbolic links, or descend
into unexpected Git metadata. Gitlink artifacts compare the recorded commit and
live worktree state without exposing file names from that worktree.

This audit boundary deliberately precedes capture and deployment. It can reveal
generated themes, runtime caches, absolute wallpaper paths, and legacy layout
differences without treating them as content that belongs in the product.
Last-deployment records and three-way conflict detection remain prerequisites
for any command that writes files.

Shell is the second domain-owned configuration after Niri. Repository sources
now live under `shell/zsh/` and `shell/starship/`, while their destination paths
remain `.zshrc`, `.zimrc`, and `.config/starship.toml`. The move preserves file
content and does not deploy the repository version into a live home.

Kitty follows the same model under `terminal/kitty/`, with
`.config/kitty` retained only as its home destination. The reviewed Kitty
configuration and attributed Frappe theme remain unchanged. The tracked legacy
backup was removed, while `kitty.conf.bak` remains excluded from audit and any
future capture so machine-local backups do not become product inputs.

Fcitx5 and Rime sources now live under `input/`, while their XDG and Rime home
destinations remain unchanged. The move keeps the small explicit Rime
customizations separate from generated databases and build output. The existing
Catppuccin Fcitx5 theme was relocated without modification, but its metadata
does not provide a complete upstream and license record; it remains a temporary
candidate pending provenance review or replacement by Utopia's future unified
theme generator.

The Neovim gitlink now lives at `editor/nvim` while still targeting
`.config/nvim` in a live home. It retains the same pinned commit and clean
submodule worktree. The move uses Git's submodule-aware path handling so a fresh
clone continues to initialize the editor dependency through `.gitmodules`.

Reviewed development configuration now lives under `development/`. The SSH
client artifact contains only public GitHub connection policy and retains its
declared `0600` deployment mode. The unused GDB artifact, its partial
debuginfod environment policy, and an empty Lazygit artifact were removed
because they did not form complete active shared behavior. Lazygit package
intent remains an independent profile decision; debugging policy can return as
an explicit domain with network and cache behavior.

## Progress note — third-party provenance review

The retained imported files now have a path-scoped inventory in
`THIRD_PARTY_NOTICES.md`. Kitty's Frappe theme was verified byte-for-byte
against Catppuccin for Kitty revision
`43098316202b84d6a71f71aaf8360f102f4d3f1a` and retains the upstream MIT
license. `input/rime/rime_ice.dict.yaml` was verified byte-for-byte against
Rime Ice revision `f3c796bb008a0ccc2bcd08aac66b82036120589e` and retains the
upstream GPL-3.0-only license. Copies of both license texts are shipped under
`LICENSES/`.

No verifiable upstream or license was found for the temporary Catppuccin Fcitx
theme. Its two PNG files, two SVG files, and configuration were removed rather
than assuming redistribution permission. The managed Fcitx configuration now
refers to the packaged `default` and `default-dark` themes, and the separate
theme artifact was removed from the workstation plan. This is a provenance
fallback, not the final visual design; a future wallpaper-aware generator must
produce Utopia-owned output or carry an explicit upstream license.

The `editor/nvim` gitlink remains pinned to the separate `nvim-astro`
repository. Neither its pinned revision nor the reviewed AstroNvim template
revision contained a license file, so that repository's licensing remains a
separate unresolved task. Utopia's original material also remains unlicensed
until the maintainer makes a project-wide license choice; third-party licenses
must not be applied to the repository as a whole by inference.

## Progress note — Utopia project license

The maintainer selected the Apache License 2.0 for Utopia's original material.
The unmodified license text now lives at the repository root. README and the
third-party notice define the scope explicitly: Catppuccin for Kitty and Rime
Ice retain their path-scoped upstream licenses, while the `editor/nvim`
submodule remains a separate repository outside Utopia's Apache-2.0 grant.

This choice makes the reviewed Utopia implementation permissively reusable
with an explicit patent grant without attempting to relicense imported work.
The unresolved AstroNvim template provenance remains local to the separate
`nvim-astro` repository and is still the first licensing follow-up.
