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
- Profile resolution, artifact mapping, and repository-to-home audit are
  read-only. `python -m utopia audit <profile>` reports matching, drifted,
  missing, and unsafe artifacts without following symbolic links or exposing an
  absolute home path. Capture, deployment, and last-deployment-aware recovery
  are not working commands yet.
- Niri has shared domain-owned configuration plus output-only host overlays.
  Shell, terminal, input, editor, and reviewed development configuration are
  domain-owned. Several other home-relative artifacts still live at the
  repository root.
- [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) records the exact
  Catppuccin for Kitty and Rime Ice revisions and their bundled license texts.
  The Fcitx theme with unverifiable redistribution permission was removed;
  Fcitx now names its packaged default themes. The separate Neovim submodule
  still needs its own license decision.
- Utopia's original material is licensed under Apache-2.0. Third-party paths
  retain the licenses recorded in `THIRD_PARTY_NOTICES.md`, and the separate
  `editor/nvim` submodule is explicitly outside Utopia's license scope.
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

The current repository is clean and both Python suites pass (33 profile/audit
tests and 67 Arch-installer tests). Continue in this order, one focused change
at a time:

1. **Resolve the editor submodule license.** Utopia's original material is now
   Apache-2.0 and the retained third-party paths are documented. Resolve the
   separate `nvim-astro` repository's AstroNvim template provenance and license
   there before treating that submodule as redistributable source.
2. **Resolve audit drift by domain.** Run `python -m utopia audit arch-laptop`
   and `python -m utopia audit cachyos-desktop`; review shell, terminal, input,
   desktop, and monitoring separately. Do not recapture generated themes,
   absolute wallpaper paths, cache files, Rime runtime/build output, or the old
   monolithic Niri tree. Keep expected host differences in host overlays.
3. **Complete the artifact lifecycle.** Implement capture and deployment as
   dry-run-first commands using the existing resolver and validators. Add a
   last-deployment record and three-way conflict detection before either side
   can be overwritten. Preserve backups and provide rollback instructions.
4. **Unify installation with profiles.** Keep the existing Arch installer as a
   tested prototype, then make bootstrap, configuration, recovery, and package
   intent consume the same provenance-aware plan. Encryption remains optional;
   Limine and systemd+sd-encrypt remain the supported encrypted path.
5. **Rehearse the complete path in a fresh VM.** Validate plain and encrypted
   Arch installs, package source separation, Noctalia Greeter, Rime deployment,
   SSH permissions, recovery audit, and reboot behavior. Do not run an apply
   path against the current host.
6. **Release hygiene.** Add CI for both Python suites and profile validation,
   document supported profiles and unmanaged boundaries, then create a first
   versioned product release only after the VM rehearsal passes.

Run the repository checks relevant to the changed domain. The current baseline
checks are documented in `AGENTS.md`; at minimum, run both Python suites and
`git diff --check` for profile or documentation work.

## Updating this file

Keep this document free of credentials, private identity, local usernames,
absolute home paths, device identifiers, backup locations, and transient runtime
state. Record only facts needed for the next contributor or agent. Remove stale
next steps when work lands instead of accumulating a second project journal.
