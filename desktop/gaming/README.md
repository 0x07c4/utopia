# Gaming baseline

Steam is an optional Utopia workstation capability. The current integration
target is `cachyos-desktop`; declaring it optional does not install it on either
host or make it an Arch-installer default. The first game acceptance target is
Stardew Valley. GTA Online remains in the existing Windows environment; Battle.net
and Hearthstone integration is now a separate
[China-client compatibility trial](hearthstone-cn.md), now with one completed
game session confirmed by the maintainer on the desktop. This is not general
Linux compatibility or full lifecycle acceptance.

## Provider and installation

Use the distribution's `steam` package from Arch's multilib repository. Review
the transaction before installing it; on the desktop, multilib, the NVIDIA
32-bit userspace libraries, and Vulkan loaders were already present. Do not
copy GPU-driver intent to another host or change its driver stack to match.

```sh
pacman -Sp --print-format '%n %v %s' steam
sudo pacman -S --needed steam
```

If a cached index references package versions that mirrors no longer retain,
do not work around 404 responses with a partial `pacman -Sy steam` upgrade.
Review the base-system update separately, or retrieve the exact matching
packages from the official Arch Linux Archive and keep normal pacman checksum
and signature verification enabled. Do not substitute newer 32-bit libraries
without checking their installed 64-bit counterparts.

Use the packaged Steam runtime initially. Steam may download its current client
on first launch. Account login, Steam Guard, license acceptance, game purchases,
and selecting downloads are user actions. No credentials are entered by an
agent or captured in Utopia. Launch through the application launcher or the
packaged Steam desktop entry; there is no additional game launcher binding yet.

Games, client updates, library manifests, account files, compatibility prefixes,
shader caches, mods, and save data remain outside Git. Start with a library in
the Linux home. Reusing a Windows library or migrating saves needs a separate
review; this slice does not mount or modify Windows volumes.

## Niri integration and acceptance

The existing Niri tree already has Steam auxiliary-window and notification
rules. Niri 25.08+ automatically integrates with xwayland-satellite 0.7+ when it
is available in PATH; avoid adding a second startup command or hard-coded
DISPLAY. See the [upstream Xwayland guide](https://github.com/niri-wm/niri/wiki/Xwayland).

The native Stardew Valley window was observed with app ID `Stardew Valley`.
Its first half-width tiled launch clipped the main menu. A narrowly matched
`open-fullscreen true` rule now starts it with the intended landscape viewport.
Both host compositions parse, and the desktop rule was deployed after a backup
while preserving unrelated live rules. Fresh-launch window captures and an
actual-screen capture, after allowing focus/resize animation and game redraw to
settle, show the complete title and menu. Early transition captures looked
partially stale; those do not establish a persistent rendering defect.
The property is documented in the
[upstream window rules](https://github.com/niri-wm/niri/wiki/Configuration:-Window-Rules#open-fullscreen).

The existing interaction entry points are:

- `Mod+Shift+F`: toggle fullscreen.
- `Mod+V`: toggle floating.
- `Mod+Tab`: return to the previous workspace.
- `Mod+Escape`: escape an application's keyboard-shortcut inhibitor.

Validate the client before changing these rules. After login and the selected
game download, check game launch, fullscreen, returning to the desktop, audio
output, and returning to the game. Verify idle/lock behavior during a sustained
session, particularly with controller input; the current ten-minute idle lock
is not treated as game-tested. Keep automatic lock policy until a scoped game
inhibitor has been verified. GameMode, MangoHud, gamescope, custom Proton builds,
and hardware tuning are not prerequisites for the first client test.

This baseline is accepted in stages: package installed, client/login screen
reachable, then an actual game session. Client startup alone does not prove
game compatibility, input, audio, frame pacing, or idle behavior.

Current desktop evidence: native game launch, NVIDIA OpenGL loading, fresh-launch
fullscreen rendering, desktop/game focus switching, and mouse hover mapping to
the Co-op menu button passed. The input check did not click buttons or create
or modify a save. The game's audio
client was linked to an uncorked, unmuted stream and an unmuted output, but this
does not certify physical speaker output. Actual gameplay remains open. Session
locking interrupted an earlier verification run; the visual check passed after
unlock. Game-session idle inhibition is explicitly deferred by the maintainer.
Keep the current lock policy while the active next slice evaluates Hearthstone
China compatibility.

## Recovery

Installing Steam itself does not replace live Niri or Noctalia configuration.
The later Stardew fullscreen-rule trial has a separate timestamped Niri rule
backup. To revert that trial, remove its exact window rule from the repository
and live configuration, or restore the reviewed rule backup after checking for
subsequent edits, then run `niri validate`. Existing windows retain their current
mode; change mode manually or relaunch the game if needed.
If the optional client is unwanted, close it and remove only the explicitly
selected package:

```sh
sudo pacman -R steam
```

Keep existing graphics providers and client/game data. Review dependencies
separately rather than cascading removals; deleting client data or saves is not
part of this recovery operation.
