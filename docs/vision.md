# Utopia Vision

Utopia is intended to become an open-source Linux workstation product rather
than remain only a personal dotfiles snapshot. Real daily-use machines provide
integration evidence, while reusable models, safe composition, and documented
extension points make the project useful beyond those machines.

## North star

> 不再追求别人替你设计好的 Linux，而是以 Arch 为底座，自己构建桌面，并把 CachyOS 当成进入真实 Linux 性能工程的入口。

The conceptual layers are:

```text
Arch            → stable and transparent system base
Utopia          → personal desktop, tools, and workflow
CachyOS work    → kernel, scheduler, compiler, and performance experiments
```

The current CachyOS desktop is useful as a complete integration reference. The
Arch laptop is useful for selecting individual CachyOS technologies without
adopting the entire distribution. Neither machine should be forced to imitate
the other before the behavior is understood.

## Areas of the project

```text
desktop/       niri, Noctalia, input, terminals, and visual themes
editor/        Neovim and development environment
shell/         Zsh, Zim, Starship, navigation, and command workflows
system/        base distributions, packages, services, and hardware support
kernel/        build descriptions, configurations, patches, and provenance
scheduler/     BORE, EEVDF, sched-ext, and related investigation
toolchain/     Clang, LTO, AutoFDO, Propeller, and architecture levels
tuning/        reversible sysctl, systemd, udev, power, and runtime changes
benchmarks/    repeatable definitions, runners, metadata, and reports
profiles/      composition of workstation capabilities for a target
hosts/         sanitized machine facts and narrowly scoped overrides
bootstrap/     planning, deployment, validation, recovery, and rebuild
ideas/         incomplete thoughts that have not become decisions
```

This is a domain map, not a requirement that every directory be created before
it has real content.

## Full-system scope

Utopia's long-term scope is the complete workstation lifecycle, from hardware
and firmware assumptions through the daily desktop and its recovery paths. It
therefore includes:

- instruction-set architecture and relevant CPU feature levels;
- firmware mode and boot-loader policy;
- kernel variants, initramfs, and scheduler experiments;
- disk topology, filesystems, encryption, snapshots, and recovery;
- drivers, services, power management, and performance tuning;
- desktop, shell, editor, input method, applications, and visual design.

These areas do not all have the same implementation maturity. `unmanaged`
means that Utopia currently records a boundary without applying changes there.
It is a present safety state, not a declaration that the area lies outside the
project. A system area can become managed only after it has a versioned model,
dry-run plan, host checks, validation, backup or fallback, and tested recovery.

Hardware architecture belongs primarily to reusable hardware capability data.
Concrete disk identifiers, display connectors, and boot entries remain host
facts. Boot policy belongs to the system domain, while a host supplies the
devices and identifiers needed to realize that policy.

## Composition model

A resolved machine is composed from independent layers:

```text
system base
+ hardware support
+ Utopia workstation capabilities
+ host-specific facts and overrides
+ optional experimental overlay
= resolved target state
```

Initial examples:

```text
arch-laptop
= Arch base
+ Intel laptop hardware
+ Utopia workstation
+ linux-cachyos-bore-lto experiment

cachyos-desktop
= CachyOS base
+ NVIDIA desktop hardware
+ Utopia workstation
+ CachyOS integration baseline
```

Shared configuration and host differences must live in the same main branch.
Long-lived laptop and desktop Git branches would make shared improvements drift.
Short-lived feature and experiment branches are appropriate.

Machine differences are a constraint on safe composition, not the subject or
organizing principle of Utopia. Domains such as desktop, shell, editor, and
performance research own the design. Host data stays narrow and only supplies
facts or overrides that cannot be shared.

## Engineering principles

### Explain before automating

Every managed setting should have a purpose, an owner, an applicable scope, and
a validation method. Performance work also needs a baseline and rollback path.

### Separate configuration from observation

- Desired state belongs in versioned manifests and configuration.
- Sanitized machine facts may be recorded as inventory.
- Public configuration uses role-based host IDs and XDG or home-relative paths.
  Private identity and exact device identifiers stay in untracked local
  inventory unless they are required for reproducible behavior. Deliberately
  published maintainer and project contact information remains public metadata,
  separate from deployable workstation configuration.
- Runtime state, caches, credentials, and generated databases do not belong in
  Git.
- The current state of a machine is not automatically the desired state.

### Separate application configuration from package intent

The presence of a configuration file does not mean that an application should
be installed. Profiles should classify packages as `required`, `optional`, or
`disabled`. WezTerm is currently disabled for the workstation and no WezTerm
configuration is tracked.

### Preserve recovery paths

Kernel, scheduler, and tuning experiments must be additive and reversible. An
experimental kernel must not replace the only bootable kernel. Stable and LTS
fallbacks remain available. Dotfile deployment backs up changed live files.

### Measure performance claims

Different hosts are useful for compatibility and integration testing, but they
cannot isolate scheduler or compiler effects. Performance comparisons must run
variants on the same host and record the kernel, build configuration, governor,
background load, temperature, number of runs, and latency distribution.

Kernel binaries, full source trees, caches, and large raw traces stay outside
Git. Utopia records reproducible inputs, provenance, checksums, summaries, and
links to external artifacts.

### Treat themes as a coherent system

Future visual work should use a shared theme source to generate or validate the
Kitty, Fcitx5, Noctalia, Satty, SwayOSD, and related palettes. Wallpaper-driven
themes should record the source wallpaper or its URL and checksum. Generated
runtime state remains excluded.

## Agent-readable rebuilds

A new agent should not need conversation history to determine what Utopia means
or what is safe to change. The repository should eventually provide:

- schema-validated TOML or JSON profiles;
- one resolver used by capture, deploy, audit, recovery, and bootstrap;
- human-readable and stable machine-readable plans;
- provenance for every resolved value;
- explicit `managed`, `unmanaged`, and `experimental` scopes;
- dry-run by default;
- idempotent and resumable stages;
- timestamped deployment state outside Git;
- three-way conflict detection using the last deployed commit;
- validation and rollback instructions for every applied layer.

`AGENTS.md` is the entry point. It summarizes current facts and safety rules,
while schemas and manifests will become the executable source of truth.

## Migration approach

The repository currently keeps most home-relative configuration at its root and
contains a laptop-oriented staged Arch installer. Migration should be gradual:

1. Preserve existing behavior and add tests around profile resolution.
2. Create the shared resolver and machine-readable profile schema.
3. Move configuration into domain ownership with explicit destination mapping.
4. Capture laptop and desktop host overlays without copying runtime state.
5. Make capture dry-run by default and detect concurrent edits.
6. Let recovery and bootstrap consume the same resolved plan.
7. Add performance experiment definitions only after the safe deployment model
   exists.

Ideas remain ideas until evidence promotes them into architecture or code.
