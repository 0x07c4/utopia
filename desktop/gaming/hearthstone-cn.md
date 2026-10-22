# Hearthstone China compatibility trial

This is an experimental `cachyos-desktop` capability with one maintainer-confirmed
completed game session. It is not a generally validated Linux game bundle.
The maintainer selected the China service; the existing
Windows environment remains the working fallback. Game-session idle inhibition
is deferred at the maintainer's request.

## Provider and source boundary

Use the distribution's optional `lutris` package to manage a separate Wine
prefix for the China Battle.net client. The reviewed package transaction does
not include system Wine, kernel modules, or driver changes. Select and record
the managed runner before executing the Windows installer; do not silently
install a system Wine package or reuse another game's prefix.

The [official China download page](https://download.battlenet.com.cn/zh-cn/)
currently links to:

```text
https://downloader.battlenet.com.cn/download/getInstallerForGame?os=win&gameProgram=BATTLENET_APP&version=Live
```

On 2026-10-12 this endpoint resolved to the official 1.0.66
`Battle.net-Setup-CN.exe` download. Downloaded installers, runtime binaries,
prefixes, game files, and account state stay outside Git. Record installer and
runner checksums in local deployment notes, not private paths or account data
in the public repository.

The [Lutris Battle.net installer](https://lutris.net/games/battlenet/) and
[upstream troubleshooting notes](https://github.com/lutris/docs/blob/master/Battle.Net.md)
are integration references. The currently published standard installer points
at the international installer and is not a tested China recipe. Do not execute
it unchanged or vendor its YAML into Utopia. Keep any installer changes limited
to the isolated prefix; its presence is not authorization for the upstream
suggestions to edit hosts, reinstall drivers, or remove shared caches.

## Current trial evidence — 2026-10-12

The selected initial runner is
[Kron4ek Wine Staging 11.19 amd64-WoW64](https://github.com/Kron4ek/Wine-Builds/releases/tag/11.19),
listed in [Lutris's runner API](https://lutris.net/api/runners/wine).
Its release archive matched the upstream SHA-256
`c89f69cf22f6664e3791210fa3b40c6e9e6d2e27a9aaa466f5a26d9c56664a09`,
and its executable reports `wine-11.19 (Staging)`. It was installed in the user's
Lutris runner directory without installing system Wine. The China bootstrap
download was identified as a PE32 Windows program and locally checksummed.

A fresh independent prefix initialized and installed Wine Mono. A standalone
runner test reached the China bootstrap window and created the Battle.net
Agent, but the installer remained at its startup logo with sustained high CPU
use; the actual Battle.net launcher and login page were not reached. That
prefix's processes were stopped, retaining its data. This is not a working
Hearthstone configuration and does not establish the cause of the stall.

Lutris package installation first failed on stale-index 404 responses. Three
exact packages and their signatures were retrieved from the official Arch
archive, but the second transaction rejected the CachyOS optimized
`python-pycurl` package's signature. Both transactions changed no installed
packages. The retry explicitly selected the already-configured Arch
`extra/python-pycurl` standard build, retained normal signature checks and the
same 46-package boundary, and succeeded after administrator authentication.
Lutris 0.5.22-2 and python-pycurl 7.47.0-1 have no missing packaged files, and
`lutris --version` reports 0.5.22. Its diagnostics report missing optional
`python-protobuf` for Battle.net source integration and missing `vulkaninfo`;
the first diagnostic preceded the follow-up dependency installation below.
The optional `vulkaninfo` diagnostic CLI remains absent.

### Follow-up dependency and runtime checks

`python-protobuf` 36.1-1.1 is now declared optional and installed on the desktop.
Its packaged-file check passes, Python reports protobuf 7.36.1, and importing
Lutris's Battle.net service with the normal GTK3 initialization succeeds. The
missing-module warning is gone. Lutris's GUI opens successfully; this verifies
the manager and source dependency, not the Windows client or Hearthstone.

After backing up the retained WoW64 prefix, a process-local
`WINEDLLOVERRIDES=locationapi=d` trial, following the upstream installer setting,
still showed the same startup logo and high CPU. The installer is already
floating, so generic tiling is not established as the cause. Debug attachment
reported a WoW64 execution-access exception involving ntdll; attachment itself
could have contributed, so this is not a proven cause of the original stall.

A same-version traditional Staging amd64 build was separately downloaded and
matched upstream SHA-256
`f70f17f7da3e8c936193e3c089e4a85615d4c1fe3e42f4a276f4160f3601a1b5`.
Its i386 Unix modules and version check were verified. A fresh separate prefix
also reached the Agent/startup logo without installing the launcher and showed
high CPU; changing Wine execution mode alone did not solve the observed issue.
The China installer's MD5 matched its official CDN response.

A first virtual-desktop attempt was interrupted by session locking and remained
unclassified. After unlock, the backed-up traditional prefix was launched with
`wine explorer /desktop=BattleNetCN,1280x720` and the installer's Windows `Z:`
path. The complete installation configuration appeared, and the bootstrap log
confirmed it was waiting for user configuration. High CPU alone therefore does
not prove that the bootstrap is stuck. This successful combined trial does not
isolate virtual-desktop geometry from the corrected launch path as the cause.

Chinese text initially appeared as boxes. Copying the already-installed Noto
Sans CJK Regular collection into this prefix and adding a Microsoft YaHei Wine
replacement alone did not resolve it. Prefix-local `FontLink\\SystemLink`
entries for Tahoma, Arial, Segoe UI, Microsoft Sans Serif, and Microsoft YaHei,
pointing to `NotoSansCJK-Regular.ttc,Noto Sans CJK SC`, restored readable Chinese
after restarting the prefix. This follows Wine's
[font-link mechanism](https://www.winehq.org/pipermail/wine-devel/2010-February/081576.html);
no fonts or registry settings were changed for other applications.

The installer then proceeded beyond configuration after disabling its startup
checkbox and selecting Continue. The Battle.net launcher files were installed,
and the China client displayed its readable NetEase login/registration and
license/privacy-consent page. Consent and authentication were not performed by
the agent; at this installation stage, account login and game acceptance were
still unverified. Later acceptance is recorded below. Both prefixes and their
backups are retained.

The installation virtual desktop is not the accepted everyday launch method:
Niri tiling enlarged its outer window without enlarging its 1280x720 content,
leaving large black margins. After stopping only this prefix, launching the
installed `C:\\Program Files (x86)\\Battle.net\\Battle.net.exe` directly produced
an independent, floating login window without that virtual desktop. Its default
96 DPI was too small on the desktop's scale-2 output. After a timestamped registry
backup, setting this prefix's `HKCU\\Control Panel\\Desktop` `LogPixels` DWORD to
192 and restarting produced a complete, readable 362x597 logical-pixel login
window. This DPI is a `cachyos-desktop` trial setting, not shared policy or an
instruction to change laptop scaling. To undo it, stop only this prefix and
restore the backed-up registry, or restore the prior DPI value before restarting.
The screenshot check covers the login window, not the post-login launcher or game.

### Main-client geometry follow-up — 2026-10-21

The main client later appeared tiled at 1000x1014 logical pixels. Focusing it
showed a white region at the upper-right edge. Without restarting the client,
moving that same window to floating layout at 1100x720 removed the white region;
leaving and restoring focus did not reproduce it, and game download files kept
growing. Only the right edge was reviewed, not account content. This supports a
geometry/repaint workaround, not proof of a DPI or graphics-driver root cause.

A default-floating rule was briefly added and deployed after backup, but was
withdrawn from both repository and live rules after review: a successful resize
does not establish that users must keep this client floating. No permanent
Battle.net geometry rule remains. The live withdrawal preserved unrelated rules
and passed Niri validation without restarting the client.

Further same-process comparisons reviewed only the upper-right corner:

| Layout | Logical size | White region after redraw |
| --- | --- | --- |
| Tall floating | 1000x1014 | Absent |
| Restored tiling | 1000x1014 | Absent |
| Maximized column | 1888x1014 | Absent |
| Fullscreen | 1920x1080 | Absent |
| Original tiling after a focus cycle | 1000x1014 | Absent |

The client was left in ordinary 1000x1014 tiling, not forced floating or
fullscreen. These results support a transient stale-paint/resize interaction;
they do not isolate its cause or prove a permanent fix. The maintainer later
completed a game as recorded below. A subsequent normal close/reopen cycle
restored the main window through the application entry, but the upper-right
white region returned on the new tiled window. Increasing its width from 1000
to 1001 logical pixels, then restoring 1000, cleared the region without changing
layout or final size. This narrows the temporary workaround to a resize/redraw;
no resize automation or permanent floating rule has been added. Process-cold
restart and permanent rendering correctness remain separate open checks.

Subsequent diagnosis found no explicit `Client.HardwareAcceleration` setting.
The public Lutris standard recipe sets it to the string `false`, and
[its troubleshooting guide](https://github.com/lutris/docs/blob/master/Battle.Net.md)
suggests disabling acceleration for a different symptom (missing login buttons).
Neither establishes the cause of this white corner. Two further normal
close/reopen-and-focus attempts at the original 1000x1014 tiled size showed no
white corner even before any setting change or resize. No acceleration setting
was changed: the fault is intermittent, and a clean screenshot after toggling
an option would not by itself establish an improvement. Leave the working
configuration intact; use a reproducible baseline and repeated comparisons
before promoting a client-specific rendering workaround. The client remains
open in ordinary tiling.

### User-supplied resize trigger — 2026-10-22

The maintainer identified `Super+R` (`Mod+R`), not merely reopening or focusing,
as the reproduction path. Repository and live bindings both map it to Niri's
`switch-preset-column-width`. Explicitly focusing Battle.net and invoking that
same action reproduced the white upper-right area when reducing a wider column
to a narrow preset. Recorded actual window widths included 1253 and 1000 logical
pixels. Directly requesting 1000 from 1253 could render correctly, despite the
same final dimensions. Do not describe reopen-only negative tests as disproving
this trigger or describe the fault as unexplained random behavior.

Two scoped candidate trials were not promoted:

- The initial hardware-acceleration attempt was invalid: closing the window
  left Battle.net processes alive, and the running client rewrote the edited
  setting. After a prefix-only stop with no active game, setting
  `Client.HardwareAcceleration` to string `false`, cold-starting, and verifying
  that the value remained present still reproduced the white corner on the
  preset-width action. The override was then removed, with other JSON values
  preserved; its absence was verified after restarting.
- A desktop-only `min-width 1000` fragment initially looked promising, but
  removing it and cold-starting did not establish a repeatable reverse result.
  Further preset cycling also produced a black unpainted corner. There is not
  enough evidence to attribute the fault to a missing minimum-width rule. The
  fragment and its include were withdrawn; the retired fragment is in private
  backups, not active configuration or the repository.

The original DPI, hardware-acceleration default, key binding, and ordinary
tiling were restored. A one-pixel width round trip restored the observed corner
to normal again. No default-floating rule, automatic resize hook, system
scaling change, driver change, or new permanent workaround was retained.
This historical investigation continued from the preset-resize trigger with
resize/redraw event evidence, and was superseded by the fix below, merged in
PR #26. Basic gameplay and close/reopen acceptance need not be repeated. Only
cropped client-edge samples were reviewed; private runtime configuration and
screenshots remain outside Git.

### Resize compatibility fix — 2026-10-22

The later cross-layer measurements made the missing contract concrete. At one
bad narrow preset, Niri reported 618x1014 logical pixels and X11 reported
1236x2028 physical pixels, but DPI-aware Win32 inspection still reported
2000x2028 for Battle.net. Its `WM_GETMINMAXINFO` reply declares a 2000x1280
physical minimum at DPI 192. Its X11 `WM_NORMAL_HINTS` lacked `PMinSize`.
At the desktop's output scale 2, the native minimum is 1000x640 logical pixels.
This is measured client intent, not a preferred fixed layout. Upstream API
semantics are documented in
[MINMAXINFO](https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-minmaxinfo).

Two scoped pieces now bridge the compatibility gap:

1. `cachyos-desktop-battlenet.kdl` gives only the exact China main window its
   measured minimum width and height. It does **not** set a default size,
   floating, fullscreen, or global display scaling. This is an
   explicit desktop/DPI-192 opt-in, not included by either shared host profile.
   Remeasure before another host, output scale, or Wine DPI adopts it. The
   distinct-width follow-up below avoids duplicate clamped shortcut steps.
2. `battlenet-repaint.py` observes Niri main-window geometry events and coalesces
   changes for 400 ms, then asks the small Windows PE helper built from
   `battlenet-repaint.c` for a normal
   [RedrawWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-redrawwindow)
   call. That helper rechecks the exact public title and executable inside this
   Wine prefix. No input, injection, focus change, resize, or game modification
   occurs. Niri geometry is observed rather than the stale Win32 rectangle.

The launcher starts this optional adapter only if its two deployed files exist.
It neither compiles nor installs them automatically. There is one observer per
prefix, with an untracked local lock, a stop interface, and automatic exit after
45 seconds without a matching main window or on Niri IPC closure. Failed helper
startup does not prevent normal client launch. No autostart or system service
was added. Neither game nor account content is inspected or logged.

#### Explicit build and deployment

These instructions apply to the already-reviewed desktop trial, **not** an
installer or authorization for the laptop. Review destination files and save
timestamped backups before replacement. The existing runner SDK, Clang, and
Windows-target linker must be available; do not install packages implicitly.
Build **Windows PE**, never the default Unix Winelib `.exe.so` format. An early
Winelib diagnostic crashed and its dialog was closed; that program was not
deployed. The final PE helper passed its no-window self-test.

From the repository root, after the backup/review step:

```sh
data_root=${XDG_DATA_HOME:-"$HOME/.local/share"}
wine_runner="$data_root/lutris/runners/wine/wine-11.19-staging-amd64"
helper_root="$data_root/utopia/helpers"
build_dir=$(mktemp -d)
"$wine_runner/bin/winegcc" -b x86_64-windows -m64 -O2 \
  desktop/gaming/battlenet-repaint.c -o "$build_dir/battlenet-repaint.exe" -luser32
file "$build_dir/battlenet-repaint.exe"  # must report Windows PE32+, not ELF/script
WINEPREFIX="$data_root/utopia/gameprefixes/battlenet-cn-legacy" \
  "$wine_runner/bin/wine" "$build_dir/battlenet-repaint.exe" --self-test
mkdir -p "$helper_root"
install -m 644 "$build_dir/battlenet-repaint.exe" "$helper_root/battlenet-repaint.exe"
install -m 644 desktop/gaming/battlenet-repaint.py "$helper_root/battlenet-repaint.py"
install -m 755 desktop/gaming/utopia-battlenet-cn "$HOME/.local/bin/utopia-battlenet-cn"
install -m 644 desktop/gaming/cachyos-desktop-battlenet.kdl \
  "$HOME/.config/niri/utopia-battlenet.kdl"
```

Add only `include "../utopia-battlenet.kdl"` to the existing live
`~/.config/niri/cfg/rules.kdl`, preserving unrelated edits, then run
`niri validate`. Do not replace the whole rules file or copy this host-specific
fragment into the shared Niri tree. The optional adapter binary, lock, and
compiled outputs remain outside Git. Its `--limits` command can remeasure the
currently visible client's Win32 minimum and DPI without changing it.

#### Verification and recovery

The X11-event prototype passed nine consecutive preset changes. The final
Niri-event observer passed nine more. The installed desktop-entry cold start
automatically loaded the adapter; initial startup samples included transient
black corners before content settled, so startup-frame perfection is **not**
claimed. Once stable, six `Mod+R` and six `Mod+Shift+R` cycles all showed normal
right-corner rendering. Maximized-column and fullscreen checks passed, and the
window was left in ordinary tiling. No extra helper window or Wine tray appeared.
These are targeted workaround results, not a claim that Wine's upstream resize
implementation is fixed or that no frame can ever be transient during loading.
Both shared host compositions and live Niri validate. Launcher/observer tests
cover opt-in isolation, event filtering, geometry-only scheduling, close state,
per-prefix locks, and scoped stop checks. The distinct-width follow-up brings
current suite totals to 95 and 67.

To stop only the observer while leaving Battle.net and games alone:

```sh
data_root=${XDG_DATA_HOME:-"$HOME/.local/share"}
python "$data_root/utopia/helpers/battlenet-repaint.py" --stop \
  --prefix "$data_root/utopia/gameprefixes/battlenet-cn-legacy"
```

To disable it across future launches, stop it first, then move its deployed
`.py` and `.exe` files to a private backup (or restore prior versions). Remove
only the added live Niri include and its desktop fragment, then validate Niri.
The ordinary launcher still works without adapter files. Restore the backed-up
launcher if desired; keep the prefix, game, and account data. All earlier
hardware-acceleration and GDI-path trials were reverted; DPI, global shortcuts,
and graphics drivers are unchanged. The fix was merged through PR #26.

### Three distinct shortcut widths

The maintainer correctly identified a usability regression in the minimum-size
bridge: two original narrow presets clamp to the same 1000-pixel width, so every
third `Mod+R` can appear to do nothing. These are column widths, not UI zoom or
DPI steps. The desktop trial now explicitly dispatches its two existing shortcuts
through `battlenet-width.py`, since this Niri version has no window-rule-specific
preset list. Only the focused, tiled China main client at the reviewed scale-2
desktop scope uses the three valid choices: minimum 1000, Niri's 66.667%, and
Niri's 100% available width. On the current output those resolve to
1000, 1253, and 1888 logical pixels. `Mod+Shift+R` traverses the inverse cycle.
Other applications, login dialogs, floating clients, unsupported display scopes,
and failed IPC lookups use the original native preset action. Width updates
target the inspected window ID, not a potentially changed keyboard focus.

After backing up the existing helper destination and live keybinds, deploy
`battlenet-width.py` into the same `utopia/helpers` directory (mode 644). Replace
only the existing two entries **inside** live `~/.config/niri/cfg/keybinds.kdl`:

```kdl
Mod+R { spawn "sh" "-c" r#"exec python3 "${XDG_DATA_HOME:-$HOME/.local/share}/utopia/helpers/battlenet-width.py" forward"#; }
Mod+Shift+R { spawn "sh" "-c" r#"exec python3 "${XDG_DATA_HOME:-$HOME/.local/share}/utopia/helpers/battlenet-width.py" back"#; }
```

Do not add a second `binds` block or duplicate these key entries. Validate Niri.
This is an explicit desktop-only override, not a shared-keybind deployment to
the laptop. Six forward and six reverse changes through the installed dispatcher
each changed width, cycled through all three sizes, and passed cropped right-
corner rendering checks. Seven isolated dispatcher tests cover both directions,
custom widths, stable window IDs, native fallbacks, and unsupported scopes.

To undo the dispatcher, **first** restore these two original actions in the live
binds and validate Niri, then move only `battlenet-width.py` into the timestamped
backup. Otherwise those shortcuts would point at a missing script. The repaint
adapter and native-minimum fragment are independent; their recovery above does
not require removing this file. No package, DPI, focus, or game change is needed.

```kdl
Mod+R { switch-preset-column-width; }
Mod+Shift+R { switch-preset-column-width-back; }
```
Do not reset DPI, disable acceleration, or change drivers
from this evidence alone. The follow-up was merged through PR #26.
Do not repeat the already-passed manager dependency work, implicitly disable
session locking, or promote this desktop result to general runner compatibility.

Do not disable
signature validation, update the system implicitly, or claim launcher/game
compatibility from the initial Wine bootstrap result.

## Acceptance and recovery

### First actual game session — 2026-10-21

The maintainer reported completing one Hearthstone game and that it appeared
normal. This accepts the first real game session on the current desktop trial,
going beyond the earlier installer, login-page, and download checks. No account,
match, opponent, or screen content was inspected to establish this result.

Do not expand the report into separately accepted Chinese text entry, physical
audio output, repeated cold starts, close/reopen behavior, sustained performance,
or idle-lock behavior. Those were not individually reported. A successful game
does not validate the launcher rendering adapter described separately above.
Keep the existing Windows fallback and the optional, desktop-scoped trial status.

### Daily interaction acceptance — 2026-10-22

PR #26 is merged as `46c3637`. Continue from the working game and launcher,
without reinstalling, starting another match, or adding performance tooling.
The maintainer launched the game at its menu for these checks. The game window
measured 1920x1080 logical pixels. Targeted Niri game/desktop/game focus switching
passed all three checks, left geometry unchanged, and restored the original
desktop focus. No in-game input was synthesized. The running, unmuted game audio
stream had active links to a running, unmuted sink. The maintainer separately
confirmed audible game sound and normal volume adjustment. No live configuration
was changed. Active desktop Rime remains readiness evidence only.

| Boundary | Narrow check | Current evidence |
| --- | --- | --- |
| Desktop/game focus | With the game at its main menu, switch away and back; inspect compositor focus without sending game input. | Game/desktop/game IPC focus checks passed; original focus restored. |
| Fullscreen recovery | Inspect the game's current geometry; if testing the existing `Mod+Shift+F` toggle, restore the original mode afterward. | 1920x1080 logical geometry observed; toggle round trip pending. Do not copy Stardew's rule onto Hearthstone. |
| Chinese input | The maintainer selects an existing game text field, composes and commits a short neutral phrase, then clears it without sending. | Partial: Chinese text is visible in the field, but the candidate panel is far from it; anchoring fails. |
| Audio route and output | Inspect only the game's stream state, links, mute and sink state; the maintainer confirms actual sound. | Running unmuted stream/sink and active links checked; audible sound confirmed by the maintainer. |
| Volume control | The maintainer uses the normal media key or control-center slider, confirms the audible change, and restores the preferred level. | Normal volume adjustment confirmed by the maintainer; the agent changed no routing or volume. |

Do not capture friend lists, conversations, account details, or game screenshots
to establish these results. Record only sanitized outcomes. Credentials, consent,
chat sending, match entry, and subjective listening remain maintainer actions.
If the game is not running, wait for it rather than claiming these checks passed.
Game-session idle inhibition stays deferred; keep the current ten-minute lock.
Failure should first produce a reproducible symptom and a scoped diagnosis,
not a speculative DPI, driver, input-method, or audio-policy change.

#### Candidate anchoring defect

The maintainer supplied a screenshot showing an upper-left candidate panel while
the game text field was near the lower-right. Chinese text was already visible
in the field. This distinguishes working text entry from incorrect candidate
placement; do not mark the complete input path accepted. The screenshot contains
private social content and is not included or reproduced in the repository.

Read-only checks found Wine input contexts using the XIM frontend, Fcitx 5.1.23
with `UseOnTheSpot=False`, and no explicit Wine `InputStyle` or `UseXIM` registry
override in this trial prefix. These checks do not expose the negotiated XIM
style or prove which process supplied a bad rectangle. No setting was changed.

In [Wine 11.19's XIM implementation](https://github.com/wine-mirror/wine/blob/wine-11.19/dlls/winex11.drv/xim.c),
the initial spot is zero; composition-rectangle forwarding updates it only for
a position-capable input style. [Fcitx 5.1.23's XIM frontend](https://github.com/fcitx/fcitx5/blob/5.1.23/src/frontend/xim/xim.cpp)
translates supplied area/spot coordinates to screen coordinates. This makes
game/Win32 rectangle reporting and XIM coordinate delivery the next diagnostic
boundary, not proof that Fcitx, Wine, or the game is individually at fault.
The screenshot alone does not establish a scaling-factor error.

Continue with coordinate-only observations and, if needed, a separate neutral
input client on the same runner. Do not capture typed text, trace keystrokes,
inject game hooks, force a fixed screen position, or restart the input method
globally. A per-game experiment must have a backup, rollback and before/after
input check before promotion; global `UseOnTheSpot`, theme and DPI changes are
not justified by the current evidence. Keep the game and prefix intact.

### Desktop trial launch entry

The repository now provides `utopia-battlenet-cn` and its `.desktop` entry beside
this document. They reuse only the retained traditional Wine 11.19 prefix and
runner under `${XDG_DATA_HOME:-$HOME/.local/share}`; they do not download software,
create prefixes, change registry settings, or install packages. This is an
opt-in desktop trial, not a shared profile deployment or accepted game bundle.

After reviewing existing destination files and backing them up, install the
script as `~/.local/bin/utopia-battlenet-cn` (mode 755) and the desktop entry as
`~/.local/share/applications/utopia-battlenet-cn.desktop` (mode 644). Search for
**战网（国服）** in the normal application launcher. The entry uses the explicit
home-relative script location because the desktop's Niri session does not have
`~/.local/bin` on PATH; it needs no global PATH change or keyboard binding.
`~/.local/bin/utopia-battlenet-cn --check` checks prerequisites without starting
Wine. Missing prerequisites fail with a notification instead of creating a new
prefix. The launcher clears inherited runner/architecture/DLL override variables
so another game's experiment does not silently alter this trial.
When Niri and Python 3 are available, the entry first focuses a single existing
`battle.net.exe` window instead of relying on Battle.net's unreliable activation.
Window matching is by application ID, not prefix identity: if multiple Battle.net
clients are visible, it does not guess which to focus and falls back to the
configured prefix's normal launch. Missing/unavailable IPC also falls back.

The white Battle.net icon strip was Wine's standalone tray. After backing up
this prefix's registry, set `HKCU\Software\Wine\Explorer` `ShowSystray` to DWORD
0, then restart only this prefix. This disables the standalone tray window, not
all `explorer.exe` windows through a compositor rule. The setting is read by
[Wine 11.19 Explorer](https://github.com/wine-mirror/wine/blob/wine-11.19/programs/explorer/desktop.c#L881).
It is not proof of Noctalia tray integration: use the launch entry to reopen the
client rather than relying on the hidden tray. No global Niri rules were changed.
On 2026-10-21, desktop-entry cold startup produced a Battle.net window and zero
visible Wine Explorer windows. Eight isolated tests cover prerequisite failures,
no-start checking, argument rejection, space-containing paths, inherited runner
variables, desktop-entry startup without `~/.local/bin` on PATH, existing-window
activation, and absent/ambiguous/invalid-window fallback. During downloading,
reopening from the desktop entry focused the same existing window, without
creating another window or interrupting file growth. After the first accepted
game session, no game window/process or recent installation writes were present.
The agent opened the client, sent a normal window-close request, verified that
the Battle.net window disappeared without a visible Wine tray, and reopened it
from the same desktop entry. Exactly one tiled main window returned. No process
was forcibly killed and the Agent remained running; this verifies window
close/reopen recovery, not a completely cold Wine/client restart, authentication
persistence, or all minimize modes. The upper-right paint defect recurred as
recorded above. Actual gameplay is accepted separately by the maintainer report.

To undo the tray trial, restore the prior `ShowSystray` value (it was absent on
this desktop, so delete only that value) and restart only this prefix. To undo
the launch entry, remove only these two installed Utopia entry files, or restore
their timestamped backups if files existed before deployment. Keep the runner,
prefix, accounts, and game data. Registry backups remain outside Git.

Validate each boundary separately: Lutris starts, a managed runner creates a
fresh prefix, the official China installer starts, the China client reaches its
login page, and Hearthstone launches after the user logs in and installs it.
Finally validate rendering, mouse/keyboard interaction, audio, returning to the
desktop, and a real game session. A login page alone is not proof of game
compatibility. Login, authentication, account linking, real-name verification,
license acceptance, purchases, and server/account choices are user actions.
Do not inspect or publish authentication files.

If the trial fails, close only its own client and runner processes, disable its
launch entry, and preserve the isolated prefix for diagnosis or recovery.
Do not reuse or delete Steam's prefixes, Windows libraries, or unrelated Wine
environments. Removing the optional Lutris package is separate from deleting
its user data; review dependencies and never cascade-remove graphics providers.
