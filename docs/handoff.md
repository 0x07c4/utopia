# Current handoff

This is the short, rolling entry point for continuing Utopia on another machine
or in a new agent session. Update it when the active baseline or immediate next
work changes. Keep durable direction in [`vision.md`](vision.md), and keep
the active product sequence in [`roadmap.md`](roadmap.md). Keep session history
in [`journal/`](journal/).

## Active pause point — 2026-10-21

- During Hearthstone downloading, the main Battle.net window exposed an
  upper-right white region while tiled at 1000x1014 logical pixels. Moving only
  that window to floating 1100x720 removed it, including after a focus cycle;
  downloading continued. A precise shared rule for app ID `battle.net.exe` and
  title `战网` now defaults the main client to floating without hard-coded
  dimensions. Both host compositions validate. The rule was deployed only to
  the desktop after backup, preserving unrelated live rules; the current
  window was adjusted without restart. Cold-start acceptance of this rule is
  pending completion of the download. This is a geometry/repaint workaround,
  not a proven DPI or driver diagnosis. Details and rollback are in the gaming
  trial document. Do not reset DPI or restart the client during downloading.

- On `cachyos-desktop`, the optional Battle.net China trial now has a reviewed
  application-launcher entry named **战网（国服）**. Its versioned script and
  desktop entry are under `desktop/gaming/`; both were installed into user data
  after timestamped backups. The script only reuses the verified traditional
  Wine 11.19 runner and existing prefix; it never installs or initializes them.
  A `--check` path validates files without starting Wine. Niri's session lacks
  `~/.local/bin` on PATH, so the desktop entry explicitly launches the script
  from that home-relative location, without changing global PATH. The white
  icon strip was addressed with prefix-local `Explorer/ShowSystray=0`, backed up
  before changing. A cold launch through the desktop entry produced a Battle.net
  window with no visible Explorer tray window. This hides the standalone Wine
  tray; it does not establish Noctalia tray integration. Use the application
  entry for reopening, and verify close/reopen behavior after authentication.
  Reopening while the client was running initially failed to activate it; the
  entry now explicitly focuses one unambiguous Battle.net window through Niri.
  A live repeat focused the same window while game download files continued to
  grow. Matching uses app ID, not prefix identity; multiple clients fall back to
  normal prefix launch. Do not claim close/reopen acceptance: closing was not
  tested during the active download to avoid interruption.
  Eight isolated launcher tests pass; current totals are 80 main tests and 67
  installer tests, with both profiles resolving. Do not infer account or actual
  Hearthstone acceptance from startup. Continue with user-controlled login/game
  installation as needed, then game rendering, input, audio, and desktop return.
  Recovery and limitations are in
  [`desktop/gaming/hearthstone-cn.md`](../desktop/gaming/hearthstone-cn.md).

- The accepted WeChat slice now has optional `wechat-bin` package intent and
  a provider/review/acceptance/recovery boundary under
  [`desktop/social/README.md`](../desktop/social/README.md). This adds no
  installation, desktop deployment, installer default, or live configuration
  change. Use this definition for future rebuild review instead of treating
  the laptop's installed client or mutable vendor download as a pinned source.

- The current laptop slice is WeChat/social workflow acceptance. The maintainer
  approved and installed `wechat-bin` 4.1.13.26-1, and confirmed login, Chinese
  input, and video audio after a laptop-only ALSA `Speaker` mute/attenuation
  correction. No persistent audio policy or service was changed. Bluetooth
  headphones became the default A2DP stereo output at 38% volume; the maintainer
  confirmed normal playback and normal switching back to internal speakers
  after disconnection, without agent routing changes. A maintainer-controlled
  reboot then failed speaker restoration: the saved ALSA state has Speaker
  enabled at 0 dB, but the live switch is muted despite a successful restore
  service. This led to route investigation rather than another state save or
  a startup-unmute workaround.
  On 2026-10-18, selecting the already-available Speaker profile instead of
  the higher-priority Line profile automatically enabled the hardware Speaker
  switch and made Speaker the default output at 40%. The selection is saved
  in WirePlumber user state. The maintainer confirmed audible playback and
  working volume-slider control, then rebooted and confirmed both still work.
  Post-reboot inspection verified the Speaker profile, default Speaker route,
  unmuted hardware, and 70% desktop output. The speaker persistence check is
  accepted; no services were changed. The maintainer then repeated Bluetooth
  playback and disconnect-to-speaker switching with the corrected Speaker
  profile and confirmed both work normally. Speaker playback, desktop volume
  control, reboot restoration, and Bluetooth switch-back are now accepted.
  After opening WeChat in the post-reboot session, the maintainer confirmed
  that closing its window and clicking the tray icon restores it, and that
  image paste produces a composer preview without sending. Reopening after
  reboot required QR-code login; automatic-login support/settings have not
  been reviewed, so do not claim persistence or diagnose this alone as a bug.
  The maintainer confirmed an incoming desktop notification and successful
  activation into its corresponding conversation. The basic WeChat desktop
  integration test round is accepted: login, Chinese input, video audio, tray
  restoration, image paste, and notification arrival/activation. Do not expand
  this into calls, delivery guarantees, or automatic-login acceptance.
  Wired headphones, microphone,
  and calls are not covered by the Bluetooth playback check. See
  [the laptop acceptance record](journal/2026-10-17-laptop-wechat-and-audio.md).
  The desktop gaming continuation below is separate and must not be deployed
  to the laptop merely because it appears in this handoff.

- The maintainer deferred game-session idle inhibition and selected Hearthstone
  China as the next gaming slice. The official China Battle.net installer
  endpoint was verified, including its `Battle.net-Setup-CN.exe` redirect;
  Lutris's standard international recipe is only a reference, not a verified
  China installer. `lutris` is now declared optional. Its 46-package transaction
  failed first on stale-index 404s and then on the CachyOS `python-pycurl`
  signature; those failed transactions installed no packages. The retry with the
  preconfigured Arch `extra/python-pycurl` standard build passed normal signature
  validation and installed all 46 packages after administrator authentication.
  Lutris 0.5.22-2 and python-pycurl 7.47.0-1 pass packaged-file checks, and
  `lutris --version` succeeds. Its initial missing `python-protobuf` dependency
  has now been declared optional and installed: packaged-file validation and
  Battle.net service import using normal GTK3 initialization pass, and the
  missing-module warning is gone. The Lutris GUI opens. It still reports missing
  `vulkaninfo` for diagnostics; do not
  interpret the latter as missing Vulkan drivers. No system Wine, kernel, or
  driver package was in the transaction. A checksummed Wine Staging 11.19 WoW64
  runner is installed
  in user data and passes its version check. A new independent prefix installed
  Mono and reached the China bootstrap/Agent, but the installer stalled at its
  startup logo with high CPU use before installing the actual launcher. Only
  that prefix's processes were stopped, preserving its data. A backed-up
  process-local `locationapi` disable trial still stalled; the installer is
  already floating. A same-version, checksummed traditional Wine amd64 runner
  in a fresh separate prefix also showed the startup-logo/high-CPU behavior.
  Debug attachment exposed a WoW64 execution-access exception, but its role in
  the original stall is unproven. The installer's MD5 matches the official CDN.
  The first virtual-desktop attempt was interrupted by session locking. After
  unlock, the backed-up traditional prefix with a 1280x720 virtual desktop and
  Windows `Z:` installer path reached the complete installation configuration.
  Its bootstrap log confirmed it was waiting for user configuration; sustained
  high CPU alone is not evidence of a stall. Prefix-local Noto CJK font links
  restored Chinese text after a font copy/replacement-only attempt failed.
  The startup checkbox was disabled, client installation completed, and the
  China client reached the readable NetEase login/registration and consent page.
  The installation virtual desktop subsequently showed black margins when its
  outer window was tiled larger. Direct launch of the installed Battle.net.exe
  removed that virtual desktop and produced an independent floating login
  window. A timestamp-backed prefix-only DPI change from 96 to 192 adapted it
  to the desktop's scale-2 output; a complete 362x597 logical-pixel login window
  was verified by screenshot. Do not copy this host-specific trial DPI to the
  laptop or use the installation virtual desktop for normal client startup.
  The client remains open for the maintainer; agreement acceptance, account
  linking, and authentication must be performed by the user. Both prefixes and
  backups are retained. The manager dependency and
  GUI checks do not need repeating. Authenticated login and game compatibility are still
  unverified. The experiment's source,
  account boundary, validation stages, and recovery path are documented in
  [`desktop/gaming/hearthstone-cn.md`](../desktop/gaming/hearthstone-cn.md).

- The active product focus has moved to gaming on `cachyos-desktop`. Steam is
  now declared optional in the shared workstation profile, with provider,
  acceptance, privacy, and recovery boundaries under
  [`desktop/gaming/README.md`](../desktop/gaming/README.md). The maintainer
  authorized installation of the distribution's multilib `steam` package.
  The first package transaction failed during retrieval because the cached
  multilib index referenced versions missing from current mirrors; pacman made
  no package changes. The two remaining downloads were retrieved, with their
  signatures, from the official Arch Linux Archive at versions matching the
  installed 64-bit libraries. Installation has been retried using that cache
  with normal pacman verification. On 2026-10-11 system authentication completed
  and the original 30-package transaction succeeded. `steam` 1.0.0.87-3 is
  installed; its packaged files validate with no missing files, and the package
  transaction lock is released. Launching Steam through Niri started its first
  upstream client download/update. The maintainer subsequently confirmed that
  Stardew Valley was installed. Its local manifest and native launcher were
  verified, and it launched through Steam with app ID `Stardew Valley`, loading
  NVIDIA OpenGL. Desktop/game focus switching and fullscreen dimensions passed;
  its own audio client had an uncorked, unmuted stream and unmuted output.
  Screenshots exposed a clipped menu in the default half-width tile. A precise
  `open-fullscreen true`
  startup rule now parses in both host compositions and was deployed to the
  desktop after a backup, preserving its unrelated live rules. Session locking
  interrupted the first restart check. After unlock, a fresh launch produced a
  complete title/menu in both window and actual-screen captures at the intended
  fullscreen size. Waiting for focus/resize animation and game redraw removed
  the misleading partial images seen in immediate transition captures; do not
  describe those as a proven persistent renderer defect. Mouse hover correctly
  highlighted the Co-op button without clicking or touching saves. Native
  startup/menu acceptance is now complete; actual gameplay and sustained idle
  acceptance remain open.
  Existing Niri Steam rules, fullscreen/escape shortcuts, Xwayland support, and
  the desktop's graphics prerequisites were inspected; no live desktop policy
  was changed by package installation; the later backed-up Stardew window-rule
  trial is described above. Start actual game acceptance with Stardew Valley.
  GTA Online
  remains in the existing Windows environment; Hearthstone/Battle.net needs a
  separate compatibility review. Do not deploy optional gaming packages to the
  laptop from the shared profile declaration alone.

- The wallpaper-driven theme workflow was merged by PR #9, and its accepted
  semantic role mapping was merged by PR #12. The desktop theme milestone is
  complete on `main`; do not reconstruct either earlier topic branch.
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
- On 2026-09-29, after reviewing the browser, cursor, screenshot, and input
  method assumptions, the laptop received the modular Niri tree and its
  `arch-laptop` display overlay. The deployment preserved the generated
  `noctalia.kdl` include, added the Fcitx startup entry, binds `Mod+B` to the
  declared Google Chrome AUR package, uses the declared Adwaita cursor, and
  saves screenshots under `~/Pictures/Screenshots`. The overlay now declares
  the observed `2560x1600@120.000` panel mode at scale 2. Niri validation and
  live reload passed; timestamped backups are under
  `~/.local/state/utopia/deployments/`. The laptop audit was 12 matching,
  4 drifted, and 1 missing artifact before the Fcitx follow-up.
- A temporary Fcitx default-theme deployment was rolled back after review
  because it was an unapproved intermediate visual choice. The existing
  Catppuccin theme was then verified against the official
  `catppuccin/fcitx5` MIT-licensed revision, recorded under `input/` with its
  license, and redeployed without changing the visual result. The timestamped
  backup is under `~/.local/state/utopia/deployments/`; the audit is now 13
  matching, 4 drifted, and 1 missing artifact. The remaining Fcitx drift is
  generated `cached_layouts` state and the separately unresolved environment
  variable policy, not the theme. A wallpaper-driven Fcitx adapter is now
  implemented in the repository as an explicit opt-in Noctalia user template.
  It renders semantic wallpaper roles into a runtime `utopia-wallpaper` theme,
  reuses the reviewed Catppuccin icon assets, validates generated colors, and
  reloads only Classic UI through `ReloadAddonConfig(classicui)`. The hook exits
  without touching runtime assets unless
  `~/.config/utopia/enable-fcitx-wallpaper` exists. Noctalia 5.2.0 config
  validation, direct template rendering, and isolated enabled/disabled hook
  tests pass. On 2026-09-30 the template was deployed to the laptop and a
  timestamp-backed temporary A/B was started; a blue-to-green wallpaper switch
  changed the generated Fcitx colors and SVG timestamps, and the maintainer
  accepted the visual result. On 2026-10-01 the same explicit experiment was
  enabled on `cachyos-desktop`; the current wallpaper generated a warm dynamic
  theme, Classic UI reloaded through session D-Bus, and the maintainer accepted
  that result too. Both hosts may keep this local opt-in, while the repository
  still keeps Catppuccin as its tracked fallback and does not silently enable
  the feature on unreviewed hosts. The upstream Noctalia Fcitx5 template
  documents the same narrower reload path. An isolated rebuild/rollback
  rehearsal also passed: stage the fixed theme first, render the dynamic theme,
  switch only after its SVG assets exist, and restore the fixed config while
  removing generated experiment state. Details and open design questions remain
  in
  [`ideas/2026-09-29-wallpaper-driven-fcitx-theme.md`](../ideas/2026-09-29-wallpaper-driven-fcitx-theme.md).
- On 2026-10-01, the accepted Fcitx experiment gained a host-scoped deployment
  boundary without touching either live home. `profiles/features.toml` and the
  host profile values now record the experimental state and artifact
  provenance; `python -m utopia plan <profile> fcitx-wallpaper-theme` emits a
  human- or JSON-readable dry-run with backup, render, generated-asset
  validation, atomic selector switch, Classic UI reload, and rollback stages.
  The plan never reads or writes the live home. A narrow Fcitx `deploy` and
  `rollback` implementation now consumes this resolver: default dry-run,
  explicit apply/host confirmation, isolated render and validation, policy
  conflict detection, timestamped backup/records, repeat detection, and recovery
  after publication failures or process interruption. Both host profiles passed
  real Noctalia render/apply/repeat/rollback rehearsals in temporary homes.
  The desktop then received the new hook after a backup and completed a live
  CLI deployment with its existing wallpaper. First adoption now establishes
  a backup and deployment record even when the manually deployed theme already
  matches. Selector, generated theme, and opt-in snapshots remained identical;
  only the hook update and local deployment records were new. Classic UI reload
  succeeded, a repeated deployment reported `unchanged`, backup integrity and
  rollback dry-run passed, Fcitx remained active, and live Noctalia validation
  passed. Actual CLI rollback was rehearsed in temporary homes only.
  Usage and limits are documented in [`profiles/README.md`](../profiles/README.md).
- On 2026-10-03, `arch-laptop` completed the same live CLI adoption from
  `f917019`. After verifying the static prerequisites, the outdated Noctalia
  hook gained the isolated-render reload guard and the stale opt-in comments
  were refreshed, with a verified timestamped backup. An isolated render with
  the current wallpaper matched all five live theme assets, including file
  modes. The first CLI deployment created its backup and record and reloaded
  Classic UI; the identical repeat reported `unchanged`. Selector, generated
  theme, and opt-in snapshots remained identical before and after adoption.
  Backup integrity and rollback preview passed, live Noctalia configuration
  validated, and Rime remained active. No wallpaper was changed and no actual
  live rollback was performed. This record's rollback would restore the
  already-enabled manual dynamic theme, not disable the experiment or select
  the fixed fallback. Both hosts have now completed CLI adoption; retain the
  host-scoped experimental policy and tracked Catppuccin fallback.
- Laptop follow-up review standardized the Noctalia shell on Maple Mono NF CN
  and Simplified Chinese, preserved distinct Starship path, Git, and time
  stages, and refined the wallpaper center for the laptop's 800-logical-pixel
  output. The plugin now keeps its footer reachable, presents concise source
  and action labels, and caches local previews outside Git instead of decoding
  full-resolution wallpapers on every source switch. These changes were
  deployed with timestamped backups and reviewed in the live session.
- On 2026-09-30, GTK3/GTK4 were tested only in an isolated temporary HOME:
  Noctalia 5.2.0 rendered both official templates for dark and light palettes,
  the official hook created one idempotent `noctalia.css` import per GTK
  version, and fake `gsettings`/`dconf` logging showed only the expected
  `prefer-dark/light` appearance calls. The test environment had no
  `adw-gtk3`, so no GTK theme name was changed; the laptop's GTK/dconf state
  was untouched. This validates the rendering boundary, not a product
  decision to enable GTK templates. The declared GTK consumer is Nautilus,
  which uses GTK4/libadwaita; no GTK3 or Qt consumer is currently declared.
  Review Nautilus visually before mapping `gtk4` to a host/profile, and do not
  enable `gtk3` or `qt` merely for symmetry.
- A reversible laptop-only GTK4/Nautilus A/B was staged and rolled back: a
  timestamped backup was created, the current wallpaper was rendered into a temporary
  `gtk-4.0/noctalia.css`, and one `gtk.css` import was added manually. A
  Nautilus window was launched through Niri for visual review. Restarting it
  after blue and green renders changed its surfaces and text, while folder
  icons stayed static Adwaita blue; existing processes did not hot-reload the
  CSS. The experiment did not enable Noctalia's GTK template or write dconf,
  and was rolled back after the comparison, with generated files retained in
  the timestamped backup. GTK4 therefore remains experimental until static
  icon behavior and the application-restart boundary are explicitly accepted.
- On 2026-09-30, the maintainer decided that GTK/Qt dynamic theming is not a
  current Utopia product gate. Keep their templates disabled and accept the
  stable, readable system fallback (dark Adwaita/default Qt) rather than
  carrying a half-integrated wallpaper adapter. Reopen this only for a
  concrete daily-workflow problem, with a named consumer, provenance, reload
  boundary, and rollback plan; the Nautilus A/B remains evidence, not a
  deployed feature.
- Before the modular Niri deployment, after PR #12, the laptop received the
  updated explicit Material role mapping on 2026-09-29, with timestamped
  backups. Noctalia now applies Utopia's
  Starship palette template and the updated Kitty blue/magenta mapping. The
  Noctalia config, generated Kitty config, Niri config, and Starship prompt
  validate; audit is back to 10 matching, 5 drifted, and 2 missing artifacts.
  The updated prompt colors were visually reviewed during the subsequent laptop
  session; the later modular deployment and Fcitx follow-up are recorded above.
- The laptop deployment validated Noctalia configuration and plugin lint with
  no findings, Niri, Kitty, and Starship parsing, and idempotent template
  rendering. A controlled wallpaper switch changed all three generated Niri,
  Kitty, and Starship outputs; restoring the original wallpaper restored every
  output exactly, while the Starship body remained byte-identical throughout.
- The repository tests pass with the accepted role mapping: 71
  profile/audit/deployment-plan tests and 67 installer tests.
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
  absolute home path. `python -m utopia plan <profile> <feature>` now resolves
  host-scoped dry-run deployment stages with provenance and rollback details.
  `deploy` and `rollback` support only the reviewed Fcitx wallpaper feature;
  general capture, artifact deployment, and installer integration remain future
  work.
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
  Starship, Catppuccin for Kitty, Catppuccin for Fcitx5, and Rime Ice revisions
  and their bundled license texts. The separate Neovim submodule still needs
  its own license decision.
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
  Fcitx has an accepted wallpaper-driven host-scoped experiment on the laptop
  and desktop with a provenance-tracked Catppuccin fallback, and GTK/Qt dynamic
  integration is intentionally deferred. Their stable system defaults are the documented
  fallback; the old root `.config/Trolltech.conf` snapshot was removed after
  confirming that the live laptop has no matching GTK/Qt configuration and no
  Utopia behavior depended on it. Keep the controlled and `vibrant` evaluator
  paths as comparison evidence and regression stress cases, not as competing
  deployment candidates.
- Several declared interactions are not closed product loops. The laptop's
  browser, cursor, screenshot path, input-method startup, and display overlay
  are now explicit and validated; Chrome remains an AUR dependency in
  `packages/aur.txt`, while official packages stay in `packages/arch.txt`.
  The editor capability audit found that `latexmk` and the three common TeX
  engines exist, while `zathura`, `texlab`, and the LM Studio command/service do
  not; the active Neovim config still references those optional paths. Its
  Mason/LSP example files are mostly explicitly disabled. LaTeX and local AI
  now have written capability contracts: both remain optional, neither changes
  package intent yet, and each names its provider, validation, and graceful
  missing-capability path. Do not install or promise those features from config
  presence alone. Generated theme state, Mason caches, and model/runtime state
  must remain outside Git. Details are in
  [`ideas/2026-09-30-editor-capability-contracts.md`](../ideas/2026-09-30-editor-capability-contracts.md).
- The laptop now runs the repository's modular Niri composition as declared.
  Its remaining audit findings are deliberate or unrelated to this milestone;
  do not recapture the live generated theme include or runtime caches.
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

The current implementation passes both Python suites (71 profile/audit/
deployment-plan tests and 67 Arch-installer tests). Continue in this order, one
focused change at a time:

The current selected slice is the optional desktop gaming baseline: the Steam
installation and Stardew native startup/menu slice is validated on the desktop.
Game-session idle inhibition is explicitly deferred. The active next task is
the Hearthstone China compatibility trial; do not repeat Steam installation or
the resolved Stardew fullscreen/menu check. The visual and performance
follow-ups
below remain deferred while this slice is active.

1. **Keep the accepted Fcitx adapter host-scoped and opt-in for now.** The
   laptop and desktop A/B results are visually accepted, and the repository
   remains opt-in with a fixed Catppuccin fallback. The deployment boundary now
   expresses the required generate-then-switch ordering, provenance, and
   rollback as a dry-run plan. Its narrow apply/recovery implementation is
   tested in isolated homes and records backups outside Git; both hosts have
   passed live CLI adoption, identical-repeat, backup-integrity, and
   rollback-preview checks. The CLI adoption follow-up is complete, so do not
   repeat deployment or broaden the tooling without a concrete need.
   Avoid wallpaper changes during apply;
   custom XDG roots and general artifact deployment remain unsupported. Do not
   promote it to a general profile default. Reconcile GTK/Qt and Neovim only as
   separate, reviewed adapters.
2. **Choose the next core visual adapter deliberately.** GTK/Qt dynamic
   integration is deferred behind the stable system fallback; do not reopen it
   for symmetry. Neovim remains on its static Tokyo Night Moon theme. If the
   next slice targets Neovim or another core consumer, verify package and
   upstream provenance, preserve a static fallback, and validate it on the
   laptop before considering desktop deployment.
3. **Close the interaction and dependency gaps exposed by that milestone.**
   The LaTeX and local-AI capability contracts are now recorded; both remain
   optional until a concrete daily workflow selects one. The next implementation
   step is a separately reviewed capability bundle only after that choice, with
   package provenance, validation, and a graceful missing-capability path. A key
   binding, font, cursor, application, editor integration, or background service
   must have the same declared intent and validation or be removed from the shared
   experience. Eliminate generated KDE/GTK snapshots and default application
   configs that do not express Utopia behavior.
4. **Use the laptop as integration evidence, not as an import source.** Review
   its drift only for the active product milestone, choose the desired behavior
   deliberately, back up live files before replacement, and never recapture
   generated themes, absolute wallpaper paths, caches, or the old monolithic
   Niri tree.
5. **Build the first real performance experiment.** On one host, compare a
   stable kernel baseline with `linux-cachyos-bore-lto` using a declared
   workload, repeated latency measurements, complete environment metadata, and
   a tested boot fallback. This should create the first useful content under
   the kernel, scheduler, tuning, and benchmark domains.
6. **Add supporting machinery only when a product slice requires it.** Capture,
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
