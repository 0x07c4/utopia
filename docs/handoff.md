# Current handoff

This is the short, rolling entry point for continuing Utopia on another machine
or in a new agent session. Update it when the active baseline or immediate next
work changes. Keep durable direction in [`vision.md`](vision.md), and keep
the active product sequence in [`roadmap.md`](roadmap.md). Keep session history
in [`journal/`](journal/).

## Active pause point — 2026-09-29

- The wallpaper-driven theme workflow was merged by PR #9. The accepted
  follow-up role mapping is published on `work/theme-role-mapping`, based on the
  latest `main`; review and merge that focused branch instead of reconstructing
  an earlier topic branch.
- The complete theme slice was deployed to `cachyos-desktop` on 2026-09-29
  after timestamped backups. Noctalia 5.1.0 now drives generated Niri, Kitty,
  and Starship outputs with wallpaper `m3-content`; the v0.4.0 Utopia wallpaper
  plugin is enabled. Static config, generated-output parsing, plugin lint, and
  the preserved Starship body all validated. Audit improved from 10 matching
  and 7 drifted artifacts to 12 matching and 5 drifted artifacts; the remaining
  drift is unrelated or deliberately preserved runtime state.
- A blue-dominant wallpaper exposed a role-adapter defect: Noctalia's terminal
  `blue` was the Material tertiary color, so a derived pale pink dominated the
  Starship identity segment and directory listings. The accepted mapping keeps
  palette generation dynamic but gives high-frequency surfaces explicit
  `primary`, `secondary`, and primary-derived `accent` roles; tertiary remains
  a low-frequency language or magenta accent. Utopia now owns the Starship
  palette template and reuses Noctalia's marked-block applicator. The desktop
  live result was visually approved.
- The `arch-laptop` received a separately reviewed, timestamp-backed-up theme
  deployment on 2026-09-28. Noctalia, Starship, and the Utopia wallpaper plugin
  now match the repository. Kitty uses the repository configuration and
  generated palette but retains an unreferenced old `current-theme.conf`, so
  audit reports only that extra file as drift. The Utopia wallpaper plugin is
  enabled and the former official Wallhaven plugin is disabled.
- The laptop's monolithic Niri body was deliberately preserved. Deployment
  added the optional generated `noctalia.kdl` include and its rendered palette,
  then the single reviewed `Mod+Shift+Return` binding for Utopia's wallpaper
  center. A full modular-tree replacement would currently regress the working
  browser binding, select an unavailable cursor, and use a host-inappropriate
  screenshot path. The audit therefore still reports Niri drift; do not call
  that a failed theme deployment or overwrite it merely to make audit green.
- Laptop follow-up review standardized the Noctalia shell on Maple Mono NF CN
  and Simplified Chinese, preserved distinct Starship path, Git, and time
  stages, and refined the wallpaper center for the laptop's 800-logical-pixel
  output. The plugin now keeps its footer reachable, presents concise source
  and action labels, and caches local previews outside Git instead of decoding
  full-resolution wallpapers on every source switch. These changes were
  deployed with timestamped backups and reviewed in the live session.
- The laptop deployment validated Noctalia configuration and plugin lint with
  no findings, Niri, Kitty, and Starship parsing, and idempotent template
  rendering. A controlled wallpaper switch changed all three generated Niri,
  Kitty, and Starship outputs; restoring the original wallpaper restored every
  output exactly, while the Starship body remained byte-identical throughout.
- The repository tests pass with the accepted role mapping: 48 profile/audit
  tests and 67 installer tests.
  Both profiles resolve and both diff whitespace checks pass. The offline
  comparison CLI still requires ImageMagick, which is not installed on the
  laptop; its pure policy tests pass, and it was exercised on the desktop.

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
  runs Noctalia v5.2.0 and its live configuration validates. DMS remains a
  reference rather than a migration target; revisit it only for a reproduced
  Noctalia limitation.
- The first Desktop v0.1 theme slice makes Noctalia's wallpaper palette the
  source for Niri, Kitty, and Starship. All three consumers use versioned
  Utopia templates and retain explicit static fallbacks; the Starship adapter
  reuses Noctalia's applicator so generated values remain confined to one
  marked palette block. Generated outputs are excluded from static tree audit,
  while edits outside the Starship block still count as drift. The plumbing was
  initially validated with Noctalia 5.1.0 and Niri 26.04, then deployed and
  live-tested on the laptop with Noctalia 5.2.0 and on the desktop with
  Noctalia 5.1.0. The Starship configuration preserves the established
  Powerline structure, separators, module order, and language/tool coverage.
  High-frequency stages use explicit Material `primary`, `secondary`, and
  primary-derived `accent` roles; `tertiary` is deliberately low frequency.
  Kitty likewise maps ANSI blue to `primary` and magenta to `tertiary`, avoiding
  the misleading terminal-role alias that made a blue wallpaper appear pink.
  The layout's Starship `gruvbox-rainbow` origin and ISC license are recorded at
  an exact upstream revision. Isolated and live tests confirmed that template
  application changes only the palette, remains idempotent, and leaves a
  renderable prompt.
- An offline evaluator under `desktop/theme/` now compares Noctalia's actual
  `m3-content` and `vibrant` output with an experimental controlled-dark
  policy. It uses three Utopia-owned synthetic wallpaper fixtures, keeps
  surfaces and semantic colors stable, filters image candidates by population
  and saturation, enforces hue separation and contrast, and uses a versioned
  fallback when a wallpaper cannot supply three suitable accents. Generated
  HTML, SVG, JSON, and rasterized fixtures stay outside Git. Initial simplified
  fixture review ranked the directions `controlled > vibrant > m3-content`, but
  that ranking did not survive a representative desktop layout. The evaluator
  now accepts a local-only selected wallpaper without recording its path and
  holds the declared Noctalia bar, Niri focus treatment, Kitty window, complete
  Powerline stages, control-center card, and notification card fixed across all
  palettes. On that layout the maintainer preferred both built-in schemes over
  controlled. A subsequent live Noctalia-only A/B on a saturated multicolor
  wallpaper selected `m3-content`: `vibrant` over-weighted a rose-colored region
  and lost too much of the image's cyan, white, yellow, and green balance.
  `m3-content` is therefore the leading baseline, `vibrant` remains a useful
  stress case, and controlled is no longer the deployment candidate.
  The evaluator can also reference Noctalia's installed MIT-licensed default
  wallpaper without vendoring it, recording the package version and checksum in
  local-only output. On that image the current controlled thresholds admit only
  one candidate, which cannot form a three-way hue-separated set with the
  fallback; the displayed controlled palette is therefore entirely fallback.
  Treat its appearance and its lack of wallpaper influence as separate review
  questions.
- Utopia now owns a small Noctalia plugin, `utopia/wallpaper`, that presents
  local files and Wallhaven discovery (SFW by default) as two pages of one
  wallpaper center.
  The bar and `Mod+Shift+Return` open that same panel; there is no separate
  online shortcut or mouse-only path. Inside the panel, source switching,
  selection, paging, search, and applying are keyboard-accessible. Wallhaven
  downloads enter the same home-relative `~/Pictures/Wallpapers` directory as
  the local page, while thumbnails and downloaded images remain outside Git.
  The implementation uses Noctalia's public plugin API and Wallhaven's public
  API; it bundles no code or assets from the official MIT-licensed Wallhaven
  plugin, which was used only as an API-integration reference. The managed
  plugin tree and the Noctalia/Niri entry changes were deployed to
  `cachyos-desktop` on 2026-09-27 after a timestamped backup. Noctalia loaded the
  plugin in Chinese, the unified panel opened successfully, and a live online
  request populated its isolated thumbnail cache. The online browser defaults
  to all categories, SFW, newest first, and no hidden aspect-ratio or resolution
  restriction; it exposes all Wallhaven sort modes, sort direction, toplist
  period, category, purity, ratio, resolution, and direct page controls, and
  prefers large thumbnails. This online-browser correction was deployed to the
  desktop on 2026-09-28 after a second timestamped backup. An optional API-key
  setting exists for rate limits and NSFW access, but no API key is tracked or
  currently configured. Laptop review then produced plugin v0.4.0: it uses a
  stable scroll/footer layout, a 640-pixel attached panel, and persistent local
  preview thumbnails generated asynchronously with ImageMagick or FFmpeg. The
  source path, size, and modification time invalidate the cache without putting
  a local path in its filename; missing thumbnail tools degrade to original
  images. Both tools are declared in the Arch package intent.
- [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) records the exact
  Starship, Catppuccin for Kitty, and Rime Ice revisions and their bundled
  license texts. The Fcitx theme with unverifiable redistribution permission
  was removed; Fcitx now names its packaged default themes. The separate Neovim
  submodule still needs its own license decision.
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

- The first visual slice is unified across Noctalia, Niri, Kitty, and the
  preserved Starship Powerline layout. A representative layout review and live
  A/B selected `m3-content` as the Desktop v0.1 baseline; its single-seed
  behavior is accepted, while explicit adapter roles prevent a derived tertiary
  color from dominating high-frequency UI. Neovim still uses Tokyo Night Moon,
  Fcitx uses its packaged theme, and GTK/Qt integration is not yet intentional.
  Generated GTK/Qt remnants at the repository root are not an intentional
  Utopia design. Keep the controlled and `vibrant` evaluator paths as comparison
  evidence and regression stress cases, not as competing deployment candidates.
- Several declared interactions are not closed product loops. Niri binds a
  browser that is absent from package intent, names a cursor theme that is not
  declared, and hard-codes a localized screenshot directory. Editor features
  reference external tools and a local model service without expressing their
  package or capability requirements.
- The laptop does not currently run the repository composition as declared.
  Its read-only audit reports 10 matching, 5 drifted, and 2 missing artifacts;
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

The current implementation passes both Python suites (48 profile/audit
tests and 67 Arch-installer tests). Continue in this order, one focused change
at a time:

1. **Merge the accepted explicit role mapping.** The focused
   `work/theme-role-mapping` branch is committed and published; review and merge
   it through a PR only when explicitly requested. Do not commit rendered
   palettes, the selected wallpaper, runtime state, or deployment backups. After
   merging, the desktop theme milestone is complete.
2. **Close the laptop's modular Niri gap deliberately.** Replace shared
   assumptions about Firefox, the Capitaine cursor, and a localized screenshot
   directory with declared package intent or explicit host mappings. Only then
   replace the laptop's preserved monolithic body and display overlay with the
   complete repository tree. Keep the working minimal theme include until that
   review is complete.
3. **Reconcile other visual adapters one at a time.** Do not infer that the
   laptop's wallpaper, display, or live configuration belongs on the desktop.
   Choose explicit adapters for GTK/Qt, Fcitx, and Neovim instead of enabling
   every built-in or network-fetched template.
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
