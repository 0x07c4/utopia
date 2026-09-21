# Current handoff

This is the short, rolling entry point for continuing Utopia on another machine
or in a new agent session. Update it when the active baseline or immediate next
work changes. Keep durable direction in [`vision.md`](vision.md), and keep
session history in [`journal/`](journal/).

## Trusted repository baseline

- The canonical repository is `https://github.com/0x07c4/utopia`.
- `main` was rebuilt from a reviewed product tree on 2026-09-21. Its sanitized
  root is `dd0fea9` (`Initial Utopia workstation product`).
- The replaced repository and its reachable history were deleted. Do not merge,
  rebase, cherry-pick, or force-push from a clone made before this rebuild.
- Treat an old clone only as an untrusted reference. Move it aside, clone the
  canonical repository again, and manually reimplement any useful change after
  privacy, provenance, and host-scope review.
- Public commits use the project maintainer's GitHub-provided `noreply` address.
- Shared behavior and narrow host overlays belong on one `main`. Use short-lived
  branches for focused work rather than permanent per-machine branches.

## Current implementation state

- [`AGENTS.md`](../AGENTS.md) is the required agent entry point and safety
  boundary.
- Two profiles resolve today: `arch-laptop` and `cachyos-desktop`.
- Profile resolution and artifact mapping are read-only. Capture, deployment,
  audit, and recovery are design targets, not working commands yet.
- Niri has shared domain-owned configuration plus output-only host overlays.
  Most other home-relative configuration still lives at the repository root.
- The staged installer remains an unfinished Arch laptop prototype. It is not a
  CachyOS restore path.
- Boot, storage, kernel, driver, and service management remain unmanaged until
  their models, dry runs, validation, fallback, and recovery paths exist.
- Configuration with unclear third-party provenance was removed. Reintroduce a
  behavior through a small reviewed implementation or with explicit license and
  attribution information.

## Resume on another machine

If that machine has a clone created before the history rebuild, preserve it only
for inspection and make a fresh clone:

```sh
mv "$HOME/utopia" "$HOME/utopia-before-rebuild"
gh repo clone 0x07c4/utopia "$HOME/utopia"
cd "$HOME/utopia"
git submodule update --init --recursive
git rev-list --max-parents=0 HEAD
git log --oneline --all
```

The fresh clone should report `dd0fea9` as its only root commit. Before editing,
read `AGENTS.md`, inspect the relevant profile and live configuration, then
create a short-lived topic branch:

```sh
git switch -c work/<topic>
```

Do not copy a complete live home directory or an old repository tree into this
clone. Port one owned domain at a time and review the complete diff before a
public commit.

## Immediate next work

1. Compare the laptop's live state with the resolved `arch-laptop` profile
   without applying changes.
2. Decide the first narrow feature to capture; shell, terminal, editor, input,
   or desktop behavior should remain separate from system experiments.
3. Continue the shared profile/resolver design so audit, capture, deployment,
   recovery, and bootstrap can consume one provenance-aware plan.
4. Add package intent independently of configuration presence.
5. Move remaining root-level configuration into domain ownership gradually,
   with destination mappings and validation preserved at each step.

Run the repository checks relevant to the changed domain. The current baseline
checks are documented in `AGENTS.md`; at minimum, run both Python suites and
`git diff --check` for profile or documentation work.

## Updating this file

Keep this document free of credentials, private identity, local usernames,
absolute home paths, device identifiers, backup locations, and transient runtime
state. Record only facts needed for the next contributor or agent. Remove stale
next steps when work lands instead of accumulating a second project journal.
