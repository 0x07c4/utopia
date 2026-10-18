# 2026-10-17 — Laptop WeChat and audio acceptance

## Scope and accepted results

The maintainer selected WeChat as the first social-workflow slice and approved
installing the official Linux client through the reviewed `wechat-bin` AUR
recipe on `arch-laptop`. This is not an installation decision for the desktop.
No account data, chats, media, application runtime state, or package binaries
belong in the repository.

- Installed client: `wechat-bin` 4.1.13.26-1. The maintainer confirmed login and
  working Chinese input. Session persistence has not been accepted yet.
- The initial host VLC plugin-cache hook reported an empty plugin directory
  after the package transaction completed. This was reproduced separately;
  it did not mean that installation failed. No hook was disabled and no extra
  VLC plugin packages were installed to suppress it.
- During video playback, the player's library mappings showed WeChat's bundled
  VLC libraries and PulseAudio plugin. Its audio stream was uncorked and
  unmuted, routed to the laptop's analog output. This is stronger evidence than
  the stream's displayed LibVLC version string; that string alone does not
  identify the loaded library path.
- SOF firmware now loads and the ALSA card exists. The maintainer ultimately
  confirmed audible, usable video playback through the internal speakers.

## Laptop-only runtime correction

The ALSA `Speaker` control was muted and at -30 dB, while the desktop volume
control operated the exposed analog `Line Out` route. After backing up the
mixer state outside Git, `Speaker` was unmuted and raised incrementally to
0 dB. The final check also showed `Master` and `Line Out` at 0 dB and the
desktop output at 100%; the maintainer then accepted the result. No above-unity
gain was enabled. These observations do not establish the original cause of
the mute or a complete routing fix.

For this observed card, the diagnostic and manual controls are:

```sh
amixer -c 0 sget Speaker
amixer -c 0 sset Speaker unmute
amixer -c 0 sset Speaker -- 0dB
```

Card index 0 and the `Speaker` control are observations of this laptop session,
not portable settings. Identify the target card before reusing these commands.
Use the normal desktop volume slider for everyday listening; 0 dB here is not
a requirement to keep desktop playback at 100%.

The pre-change mixer snapshot is temporary and outside Git; do not assume it
survives reboot. Immediate rollback of the specific adjustment is to restore
`Speaker` to -30 dB and mute it on the verified card (this deliberately restores
the original silent state). No persistent ALSA configuration, service, driver,
kernel, or boot file was changed in this correction.

## Continuation and acceptance gates

Read-only inspection on 2026-10-17 found the distribution's
`alsa-restore.service` active (exited), with `alsactl store` configured for normal
service stop and `alsactl restore` at startup. This suggests an existing save
path, but does not prove a successful next-boot restoration. Do not add a custom
startup unmute, enable another ALSA service, or explicitly store unrelated mixer
controls as a shortcut.

The Bluetooth service and adapter were already active/powered; no Bluetooth
device was connected during the initial inspection. The maintainer subsequently
connected Bluetooth headphones. Read-only inspection confirmed that they became
the default output using the `a2dp-sink` stereo profile, unmuted at 38% volume.
The maintainer confirmed normal playback, then disconnected the headphones and
confirmed normal switching back to internal speakers. The agent did not change
the headphone volume or manually reroute a stream. The analog output had been
at 50% before this test; successful switching is based on the maintainer's
listening confirmation, not merely the default-output metadata. These checks
do not validate the wired headphone jack, microphone, or calls.

The maintainer then performed a normal reboot and reported that the correction
did not persist. Read-only checks found `Speaker` still at 0 dB but muted again.
Crucially, the saved ALSA state contained both speaker switches enabled and
volume 74 (0 dB), and the current boot's restore service reported success.
Thus this is not simply a missing saved volume: saved and live mute states
diverge. The default analog output is still the UCM `Line` route, not a
dedicated speaker route. The installed generic UCM configuration contains
speaker-off initialization and device-disable sequences; these are candidate
mechanisms, not proof of which process changed the switch or at what time.
This prompted investigation of route enumeration and UCM/session initialization
before choosing a persistent correction. No startup-unmute workaround or
additional state-save operation has been applied.

On 2026-10-18, route enumeration identified a separate available Speaker
profile, while the selected Line profile had a higher priority (10400 versus
10200). After a private temporary backup of mixer and relevant WirePlumber
selection state, the agent selected the existing
`HiFi (HDMI1, HDMI2, HDMI3, Mic1, Mic2, Speaker)` profile through `pactl`.
After asynchronous route activation, Speaker became the default output,
its hardware switch turned on without a manual unmute, and its desktop volume
was 40%. The hardware volume now follows the Speaker route rather than an
independent Line control. The selected profile reports `save=true` and appears
in WirePlumber's user profile state, with `device.restore-profile` enabled.
[WirePlumber documents restoration of manually selected profiles](https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration/settings.html).
This supports a profile-selection correction, not proof of the exact original
boot-time writer. No service was restarted or configured. To undo the
selection on the verified card, use `pactl set-card-profile <card-index>` with
the prior `HiFi (HDMI1, HDMI2, HDMI3, Line, Mic1, Mic2)` profile; this may
restore the silent behavior. Do not copy or reset all WirePlumber state.

The maintainer confirmed audible playback and responsive desktop volume after
this selection, then performed another normal reboot and confirmed the result
remained normal. Post-reboot inspection verified the Speaker profile and default
`[Out] Speaker` route, unmuted at 70% desktop volume; ALSA Speaker was enabled
at -9 dB, consistent with the selected playback level. The normal-volume and
reboot-persistence checks are accepted. No extra manual unmute or explicit
ALSA store was needed after the profile selection.

## WeChat desktop integration acceptance

After the successful reboot test, WeChat was not running and was opened through
the existing desktop session. The notification and status-notifier watcher
services owned their session-bus names. The maintainer closed the WeChat window
and confirmed that clicking its tray icon restored it. Tray/window restoration
is accepted; service ownership alone does not validate message notifications or
notification activation. No chat content or notification payload was inspected.
The maintainer subsequently confirmed that reopening after reboot required
another QR-code login. Do not describe login persistence as accepted or assume
this alone is a defect: supported automatic-login behavior and its setting have
not been reviewed. The maintainer also confirmed that pasting an image produced
a preview in the chat composer. Image-paste acceptance is complete; sending or
delivery was not tested or required. No image or clipboard content was captured.

With WeChat in the background, the maintainer confirmed that an incoming-message
desktop notification appeared, and that clicking it restored WeChat and opened
the corresponding conversation. Notification arrival and activation are
accepted by user report; the agent did not read the message or capture a
notification payload. Login, Chinese input, video playback, tray restoration,
image paste, and notification activation now have user-confirmed acceptance.
This closes the current basic desktop-integration test round, not all WeChat
features or a reproducible package/deployment implementation.

Remaining follow-ups (not blockers for this test round):

1. Repeat Bluetooth playback and disconnect-to-speaker switching with the
   corrected Speaker profile when convenient. The earlier successful Bluetooth
   checks preceded this profile change. Wired headphones remain untested.
2. Review supported automatic-login behavior separately; QR-code login after
   reboot was observed. Do not send messages or inspect private content as an
   agent. Calls and microphone behavior are still unverified and need a
   separate explicit test.

Only after these checks decide whether a reusable package declaration or
host-scoped audio policy is warranted; the current result is a documented live
acceptance and runtime correction, not a managed audio deployment feature.
