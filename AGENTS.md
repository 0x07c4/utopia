# Utopia Agent Guide

## Mission

Utopia is evolving from a personal dotfiles snapshot into a reproducible Linux
workstation project. It should describe the desktop and development workflow,
compose host-specific differences, support controlled performance experiments,
and make a rebuild understandable to both a human and an agent.

## Current machines

- `arch-laptop`: Arch Linux with `linux-cachyos-bore-lto`; this machine produced
  much of the configuration currently stored at the repository root.
- `cachyos-desktop`: CachyOS with NVIDIA graphics and a host-scoped 4K display
  overlay; this is the current migration and desktop-development machine.

Do not infer that a configuration captured on one host is safe for the other.
Display outputs, input devices, kernels, boot configuration, storage, drivers,
power management, and runtime state require an explicit host scope.

## Repository status

The current repository still stores most home-relative paths directly at its
root. Niri is the first configuration captured under domain ownership, with its
shared files under `desktop/niri/` and output-only overlays under `hosts/`.
The staged Arch installer under `install/` is work in progress and models
the laptop-oriented Arch target. It is not a CachyOS restore mechanism.

The intended architecture is domain-oriented (`desktop`, `editor`, `shell`,
`kernel`, `scheduler`, `tuning`, `benchmarks`, and `bootstrap`) with profiles
and host overlays composing those domains. Until that migration is implemented,
do not assume planned paths or commands already exist.

Read [`docs/vision.md`](docs/vision.md) for the durable project direction and
[`docs/journal/2026-09-20-cachyos-desktop-and-utopia-direction.md`](docs/journal/2026-09-20-cachyos-desktop-and-utopia-direction.md)
for the migration facts and design discussion that led to the current branch.
Read [`docs/handoff.md`](docs/handoff.md) for the current trusted baseline and
the immediate continuation path across machines or agent sessions.
Read [`docs/privacy.md`](docs/privacy.md) before capturing machine state or
publishing history.

## Safety boundaries

Boot, storage, kernel, driver, and service engineering are part of Utopia's
long-term scope. Their current `unmanaged` status is an implementation-maturity
boundary, not a permanent exclusion. Do not turn future scope into present
authorization: these domains require an explicit model, dry-run plan, fallback,
validation, and recovery path before an apply operation may manage them.

- Never run an installer `--apply` path merely to inspect or synchronize files.
- Never copy laptop display, input, boot, kernel, or hardware configuration onto
  the desktop, or desktop equivalents onto the laptop, without an explicit host
  mapping.
- Do not modify `/boot`, partition tables, filesystems, LUKS, Limine, kernels,
  initramfs, NVIDIA drivers, Snapper, or system services as part of dotfile work.
- Do not commit credentials, private keys, GitHub tokens, keyrings, shell
  history, caches, Rime user databases/build output, Noctalia runtime state, or
  generated Codex/npm launchers.
- Keep non-public personal identity, private email addresses, local account
  names, absolute personal home paths, public IP addresses, device serial
  numbers, and filesystem UUIDs out of tracked configuration and documentation.
  A deliberately published maintainer identity, project namespace, or project
  contact address is allowed. Use role-based host IDs, XDG or home-relative
  paths, and untracked local inventory for machine data.
- Treat the presence of an application configuration as evidence of prior use,
  not authorization to install that application. Package intent must be stated
  separately.
- Do not bulk-import another workstation repository. Record upstream licenses,
  provenance, and attribution before adopting third-party material; prefer a
  small independently maintained implementation of the required behavior.
- Preserve a timestamped backup before replacing live user configuration.
- Prefer dry-run, diff, validation, and a reviewable Git working tree before any
  apply step. Do not commit or push automatically unless the active task calls
  for it.

## Start every repository task here

1. Run `git status --short` and `git submodule status`.
2. Read the relevant profile or host scope when those manifests exist.
3. Inspect live and repository versions before copying either direction.
4. Keep shared policy separate from host facts and experimental settings.
5. Run the validation commands relevant to every changed domain.
6. Summarize what changed, why, validation evidence, and remaining limitations.

## Current validation commands

```sh
python -m unittest discover -s tests
python -m unittest discover -s install/tests
python -m utopia profile arch-laptop
python -m utopia profile cachyos-desktop
niri validate
noctalia config validate
zsh -n ~/.zshrc
zsh -n ~/.zimrc
nvim --headless +qa
git diff --check
git diff --check main...HEAD
```

The profile command is read-only. Its home-artifact section comes from
`profiles/artifacts.toml`; `capture` and `deploy` fields express intended future
behavior and are not executable commands yet.

Kitty can be parsed without opening a window:

```sh
kitty +runpy 'import os; from kitty.config import load_config; bad=[]; load_config(os.path.expanduser("~/.config/kitty/kitty.conf"), accumulate_bad_lines=bad); print(len(bad))'
```

When validating repository content rather than the current home, render or copy
it into a temporary home first. A successful live validation does not prove that
another host profile is valid.

## Agent-readable design requirements

Future profile and bootstrap work must provide:

- versioned TOML or JSON inputs with schemas;
- one resolver for capture, deployment, audit, recovery, and installation;
- machine-readable plan output as well as a human-readable summary;
- provenance showing which layer supplied each resolved value;
- explicit `managed`, `unmanaged`, and `experimental` scopes;
- dry-run by default and explicit confirmation for destructive boundaries;
- idempotent, resumable stages with validation after each stage;
- timestamped deployment records outside Git;
- declared package intent (`required`, `optional`, or `disabled`);
- conflict detection against the last deployed repository commit;
- rollback instructions for every tuning or experimental change.

Ideas live under `ideas/`. Capture first; promote an idea into architecture,
decision, experiment, or implementation documents only after it has enough
evidence.
