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

A backed-up Wine virtual-desktop trial was requested, but session locking
interrupted the interface check. Its result is not accepted or classified as a
failed workaround. Trial processes were stopped and both prefixes retained.
Resume after session unlock; do not repeat the already-passed manager dependency
work, implicitly disable session locking, or promote either runner as working.

Do not disable
signature validation, update the system implicitly, or claim launcher/game
compatibility from the initial Wine bootstrap result.

## Acceptance and recovery

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
