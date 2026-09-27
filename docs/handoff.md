# Current handoff

This is the short, rolling entry point for continuing Utopia on another machine
or in a new agent session. Update it when the active baseline or immediate next
work changes. Keep durable direction in [`vision.md`](vision.md), and keep
the active product sequence in [`roadmap.md`](roadmap.md). Keep session history
in [`journal/`](journal/).

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
- Niri and Noctalia v5 are the accepted desktop foundation. The current laptop
  runs Noctalia v5.1.0 and its live configuration validates. DMS remains a
  reference rather than a migration target; revisit it only for a reproduced
  Noctalia limitation.
- The first Desktop v0.1 theme slice makes Noctalia's wallpaper palette the
  source for Niri, Kitty, and Starship. Niri and Kitty use versioned Utopia
  templates and retain explicit static fallbacks; Noctalia owns only a marked
  Starship palette block. Generated outputs are excluded from static tree audit,
  while edits outside the Starship block still count as drift. The plumbing is
  validated with Noctalia 5.1.0 and Niri 26.04, but its visual policy has not
  completed review and it has not been deployed. The current wallpaper produces
  a predominantly olive-green Material 3 palette; that behavior was examined,
  not accepted or rejected. The repository Starship configuration did replace
  the live prompt's established Powerline layout, and that layout regression
  must not be deployed.
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

## Current product gaps

Utopia's safety and rebuild scaffolding is currently more mature than the
workstation experience it is meant to support. The repository has reliable
profile resolution, audit boundaries, and a heavily tested Arch installer, but
the distinctive product is still mostly a collection of usable domain
configurations rather than one coherent system.

- The visual system is only partially unified. The existing Noctalia templates
  prove that wallpaper-derived values can reach Niri, Kitty, and Starship, but
  they do not yet define an approved Utopia palette. Noctalia's built-in
  schemes derive a complete role set from one selected seed, so a green seed can
  make primary, secondary, tertiary, terminal, and surface roles feel uniformly
  green. This is an algorithmic property, not yet a product verdict. Compare it
  with more controlled wallpaper influence, such as stable surfaces and
  semantic colors plus several hue-separated accent candidates, contrast
  enforcement, and deterministic fallbacks. Neovim still uses Tokyo Night Moon,
  Fcitx uses its packaged theme, and GTK/Qt integration is not yet intentional.
  Generated GTK/Qt remnants at the repository root are not an intentional
  Utopia design.
- Several declared interactions are not closed product loops. Niri binds a
  browser that is absent from package intent, names a cursor theme that is not
  declared, and hard-codes a localized screenshot directory. Editor features
  reference external tools and a local model service without expressing their
  package or capability requirements.
- The laptop does not currently run the repository composition as declared.
  Its read-only audit reports 7 matching, 7 drifted, and 2 missing artifacts;
  notably, the modular Niri tree and laptop display overlay are not deployed.
  Generated theme state and caches must still remain outside Git when this is
  reconciled.
- The performance-engineering north star is almost entirely unimplemented.
  The BORE/LTO layer currently records a package name and an experimental label,
  but there are no kernel provenance records, controlled baselines, benchmark
  definitions, measurements, tuning overlays, or rollback evidence.
- The separate `nvim-astro` repository still has unresolved template licensing
  and public-history privacy issues. The maintainer explicitly deferred its
  rebuild; do not let it block product work or rewrite that remote history
  without fresh authorization.

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

The current repository is clean and both Python suites pass (36 profile/audit
tests and 67 Arch-installer tests). Continue in this order, one focused change
at a time:

1. **Evaluate Utopia's dynamic palette policy before deployment.** Treat the
   current Noctalia integration as working plumbing whose visual result still
   needs review. Compare the built-in single-seed schemes with a controlled
   multi-accent resolver; do not assume that the current green result is either
   accepted or rejected. Any alternative should select hue-separated candidates,
   reject unsuitable or near-duplicate colors, enforce text contrast, preserve
   intentional surfaces and semantic status colors, and have a versioned
   fallback. Its output must remain dynamic when the wallpaper changes; do not
   hard-code colors sampled from the current wallpaper. Test several versioned,
   redistribution-safe image fixtures and render reviewable comparisons before
   changing live files.
2. **Preserve the established Starship interaction design.** Keep the live
   Powerline structure, separators, module order, and language/tool coverage;
   only its palette should become generated. The layout is based on Starship's
   `gruvbox-rainbow` preset, so record the upstream ISC provenance and license
   before placing that implementation in Utopia. Do not retain the simplified
   repository prompt merely because it is already committed.
3. **Obtain visual approval, then reconcile one host at a time.** First show the
   same unchanged component layouts under palettes generated from several
   wallpapers. After approval, reconcile the Niri, Kitty, and Starship slice on
   the active host with timestamped backups and a reviewable diff. Do not infer
   that the laptop's wallpaper, display, or live configuration belongs on the
   desktop. Choose explicit adapters for GTK/Qt, Fcitx, and Neovim later instead
   of enabling every built-in or network-fetched template. Keep rendered colors
   and transient wallpaper paths outside Git.
4. **Close the interaction and dependency gaps exposed by that milestone.** A
   key binding, font, cursor, application, editor integration, or background
   service must either have declared intent and validation or be removed from
   the shared experience. Eliminate generated KDE/GTK snapshots and default
   application configs that do not express Utopia behavior.
5. **Use the laptop as integration evidence, not as an import source.** Review
   its drift only for the active product milestone, choose the desired behavior
   deliberately, back up live files before replacement, and never recapture
   generated themes, absolute wallpaper paths, caches, or the old monolithic
   Niri tree.
6. **Build the first real performance experiment.** On one host, compare a
   stable kernel baseline with `linux-cachyos-bore-lto` using a declared
   workload, repeated latency measurements, complete environment metadata, and
   a tested boot fallback. This should create the first useful content under
   the kernel, scheduler, tuning, and benchmark domains.
7. **Add supporting machinery only when a product slice requires it.** Capture,
   deployment, installer/profile unification, VM rehearsal, and CI remain
   important enabling work, but should be driven by a concrete desktop or
   performance capability rather than treated as Utopia's product roadmap.

Run the repository checks relevant to the changed domain. The current baseline
checks are documented in `AGENTS.md`; at minimum, run both Python suites and
`git diff --check` for profile or documentation work.

## Updating this file

Keep this document free of credentials, private identity, local usernames,
absolute home paths, device identifiers, backup locations, and transient runtime
state. Record only facts needed for the next contributor or agent. Remove stale
next steps when work lands instead of accumulating a second project journal.
