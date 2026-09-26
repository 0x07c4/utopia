# Utopia product roadmap

This roadmap translates the durable direction in [`vision.md`](vision.md) into
the current product sequence. It is intentionally product-first: deployment,
installation, recovery, and CI are enabling work, not the reason Utopia exists.
The rolling machine and session baseline remains in [`handoff.md`](handoff.md).

## Product definition

Utopia is an opinionated Linux workstation built on transparent system bases.
It should provide a coherent desktop and development workflow, then use that
daily workstation as a disciplined environment for Linux performance
engineering.

The two product tracks are:

1. **Utopia Desktop** — interaction, visual design, applications, input, shell,
   editor, and daily workflow.
2. **Utopia Performance** — kernels, schedulers, toolchains, reversible tuning,
   benchmarks, and measured results.

Profiles, host overlays, bootstrap, deployment, recovery, and validation serve
both tracks. They must not become a substitute for building the product.

## Current architecture decision

The current desktop foundation is:

```text
Arch or CachyOS     system base
Niri                compositor and scrolling window model
Noctalia v5         shell, palette, templates, wallpaper, panels, and services
Utopia              product policy, interaction, visual identity, and workflow
```

- Keep Niri unless a demonstrated Utopia interaction cannot be implemented on
  it. Do not replace a stable compositor merely to resemble another project.
- Use Noctalia v5 as the current shell and theme engine. Keep Utopia's curated
  configuration separate from Noctalia's GUI-managed runtime state.
- Treat DMS and Omarchy as product references, not migration targets. Revisit
  the shell choice only after a concrete Noctalia limitation is reproduced.
- Do not write a compositor or complete desktop shell while the product can be
  expressed through Niri, Noctalia configuration, templates, IPC, and plugins.
- Record the tested Noctalia version in the handoff and validate migrations
  before adopting a new major configuration shape.

## Milestone 1 — Utopia Desktop v0.1

The first milestone turns the existing configurations into one deliberate
desktop product on the Arch laptop.

### Unified visual system

Use Noctalia v5's palette and template engine as the theme source:

```text
wallpaper or fallback palette
  -> Noctalia color tokens
  -> Niri, Kitty, Starship, Fcitx, Neovim, GTK, and Qt
```

Version the Utopia-owned palette policy, templates, mappings, and deterministic
fallback. Keep the selected wallpaper path, extracted per-wallpaper colors,
rendered output, GUI overrides, and caches outside Git.

The theme must remain usable when no wallpaper exists, when palette extraction
fails, and before optional application templates have been installed.

### Interaction contract

Define and validate the complete daily path:

- terminal, browser, file manager, editor, and application launcher;
- window focus, movement, sizing, floating, full screen, and workspaces;
- control center, notifications, clipboard, screenshots, recording, and media;
- input method, session lock, idle behavior, display power, and session exit;
- laptop brightness, battery behavior, suspend policy, and external displays.

Every binding and integration must name a declared application, package,
service, or capability. Remove duplicate bindings, inactive examples, stale
window rules, generated desktop files, and default configs that add no Utopia
behavior.

### Laptop integration

Use the laptop as integration evidence, not as an automatic source of truth.
For each Desktop v0.1 domain:

1. compare repository intent with live behavior;
2. choose the desired behavior explicitly;
3. preserve a timestamped backup before replacing live configuration;
4. validate the repository composition in isolation;
5. apply only the reviewed domain and verify the daily workflow.

Do not import absolute wallpaper paths, caches, generated palettes, Noctalia
runtime state, Rime build output, or the old monolithic Niri configuration.

### Definition of done

Desktop v0.1 is complete when:

- the laptop runs the reviewed modular Niri and Noctalia composition;
- all core shortcuts launch declared and available capabilities;
- one wallpaper change updates the supported application palette coherently;
- the fallback palette produces a complete usable session;
- Fcitx, terminal, shell, editor, GTK, and Qt no longer look like unrelated
  theme snapshots;
- a short manual acceptance checklist covers login through session exit;
- remaining host differences are explicit overlays rather than copied trees.

## Milestone 2 — Performance experiment 001

After Desktop v0.1 is stable enough to serve as a daily baseline, compare the
Arch stable kernel with `linux-cachyos-bore-lto` on the same laptop.

The experiment must declare:

- exact kernel packages, versions, provenance, and relevant configuration;
- a stable boot fallback and tested rollback path;
- CPU governor, power source, thermal state, background load, and software
  versions;
- workloads for compilation throughput and interactive latency under load;
- warm-up, repetition count, raw measurement location, summary statistics, and
  tail-latency reporting;
- the boundary between BORE, compiler/LTO, and unrelated system differences.

This milestone should create the first substantive content owned by `kernel`,
`scheduler`, `tuning`, and `benchmarks`. A package name and subjective feeling
do not constitute a completed experiment.

## Later integration

Once the desktop machine is available, compose the same Utopia Desktop with its
NVIDIA and 4K host facts. Do not force it to imitate laptop power or input
behavior. Use it as the CachyOS integration baseline and later repeat controlled
experiments on that host without comparing results across different hardware.

## Enabling work policy

Add supporting machinery when a product milestone requires it:

- theme rendering may require a narrow render, preview, diff, and rollback
  command before a general deployment engine exists;
- Desktop v0.1 deployment may require backups and conflict detection for only
  the participating domains;
- performance work may require inventory and benchmark schemas before system
  installation consumes them;
- CI should protect accepted product behavior and experiment formats rather
  than merely increase test count;
- installer and recovery should consume stable product definitions instead of
  becoming a parallel source of workstation policy.

Dry runs, validation, backups, and recovery remain mandatory at destructive
boundaries even when the general lifecycle implementation is deferred.

## Explicitly deferred

The following work is not on the active product path:

- rebuilding or force-pushing the separate `nvim-astro` repository;
- migrating from Noctalia v5 to DMS without a reproduced blocker;
- writing a new compositor or complete shell;
- resolving every audit drift before selecting desired product behavior;
- broadening the Arch installer or running a release VM rehearsal before the
  workstation definition has stabilized;
- building a generic capture/deploy framework in advance of a concrete desktop
  or performance requirement.

Deferred work can return when it blocks a product milestone or the maintainer
explicitly promotes it.
