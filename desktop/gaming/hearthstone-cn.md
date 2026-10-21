# Hearthstone China compatibility trial

This is an experimental `cachyos-desktop` capability. It is not yet accepted as
a working Linux game. The maintainer selected the China service; the existing
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
the agent; account login and game acceptance remain unverified. Leave this
client available for the maintainer's next action. Both prefixes and their
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

The shared Niri rules now open only app ID `battle.net.exe` with exact title
`战网` floating, without imposing these desktop test dimensions. Login dialogs,
other Wine programs, and the game itself are not matched. Both host compositions
validate, but runtime acceptance is desktop-only. After a timestamped backup,
the exact rule was added to the desktop live rules while preserving unrelated
rules. Existing-window resize/refocus acceptance passed; restart acceptance is
deferred until downloading finishes. To undo, remove only that exact rule and
validate Niri, then return the existing window to tiling if desired. Do not
restore a complete old rules file over unrelated newer edits.
Do not repeat the already-passed manager dependency work, implicitly disable
session locking, or promote either runner as a working Hearthstone environment.

Do not disable
signature validation, update the system implicitly, or claim launcher/game
compatibility from the initial Wine bootstrap result.

## Acceptance and recovery

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
client rather than relying on the hidden tray. Close/minimize recovery after
authentication still needs acceptance. No global Niri rules were changed.
On 2026-10-21, desktop-entry cold startup produced a Battle.net window and zero
visible Wine Explorer windows. Eight isolated tests cover prerequisite failures,
no-start checking, argument rejection, space-containing paths, inherited runner
variables, desktop-entry startup without `~/.local/bin` on PATH, existing-window
activation, and absent/ambiguous/invalid-window fallback. During downloading,
reopening from the desktop entry focused the same existing window, without
creating another window or interrupting file growth. Closing the window was
deliberately not tested while downloads were active; its exit behavior is not
yet established. This does
not verify authenticated client behavior or Hearthstone gameplay.

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
