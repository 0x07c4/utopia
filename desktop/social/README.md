# Social workflow baseline

WeChat is an optional Utopia workstation application, declared as `wechat-bin`.
The first accepted integration target is `arch-laptop`. Optional intent is not
an instruction to install it on the desktop or include it in installer defaults.
No WeChat account or runtime configuration is deployed by Utopia.

## Provider and provenance

The selected provider is Tencent's official proprietary Linux client, repackaged
by the community-maintained [wechat-bin AUR recipe](https://aur.archlinux.org/packages/wechat-bin).
The AUR recipe is not a distribution-signed or Tencent-maintained Arch package.
Do not substitute the separate `wechat` enhancement wrapper, Wine, or another
provider without a new review. Utopia redistributes neither the client nor the
recipe; the proprietary software is not covered by Utopia's Apache license.

The installation reviewed for this laptop used:

- AUR revision `28516c2f7fc79deb6ab529c8c2eedcf5cf5034fc` from
  `https://aur.archlinux.org/wechat-bin.git`;
- the x86_64 Debian payload from Tencent's
  [Linux download endpoint](https://dldir1v6.qq.com/weixin/Universal/Linux/WeChatLinux_x86_64.deb),
  reporting version 4.1.13.26;
- payload SHA-256
  `a0db8caeee8d1e6cfe0aa5ce58710270f8d74a90ff4920f53a3fc22aa0956fe9`;
- a local recipe adjustment pinning that version and checksum before repacking;
  installed package `wechat-bin` 4.1.13.26-1.

These are historical audit inputs, not a claim about the newest client or a
guarantee that this mutable download still serves those bytes. The reviewed
recipe uses a dynamic version function and skips upstream checksums. For a
future rebuild, review the current full recipe, source host, payload version,
checksum, dependencies, and package contents again. Record the reviewed inputs
outside private runtime data; do not run an unreviewed AUR helper command or
reuse this checksum for a different payload. Other architectures are untested.

The recipe declares `libvlc` as a dependency. Initial installation completed but
the host VLC cache-generation hook failed on an empty host plugin directory.
The client later played video using its bundled VLC libraries. Do not disable
package hooks, install a complete VLC stack, or assume either dependency failure
or media compatibility from that warning alone. Inspect the actual transaction
and playback independently. Do not partially refresh package databases or
silently upgrade the base system to resolve dependency retrieval failures.

## Desktop behavior and acceptance

Use the packaged desktop entry or the existing application launcher. No new
global shortcut, autostart, environment override, or window rule was needed for
the accepted laptop session. Authentication and consent remain user actions.

The maintainer accepted login, Chinese input, video audio, closing/restoring via
the tray, image-paste preview without sending, and incoming desktop notifications
with activation into the corresponding conversation. The laptop's Speaker
profile correction also passed volume-control, reboot-restoration, Bluetooth
playback, and disconnect-to-speaker checks. This is laptop evidence, not a
portable audio workaround or desktop acceptance. The
[acceptance journal](../../docs/journal/2026-10-17-laptop-wechat-and-audio.md)
records the diagnostic history and recovery boundary.

Reopening after reboot required QR-code login. Supported automatic-login
behavior/settings remain unreviewed; neither persistence nor a client defect is
claimed. Calls, microphone, wired headphones, and message/file delivery are not
accepted by these checks. Do not inspect chats, accounts, clipboard contents,
or notification payloads for automated tests, or send messages on the user's
behalf. User-reported previews and notification activation are sufficient for
the selected acceptance gates.

## Recovery

Close WeChat and, only if the user wants to uninstall it, remove the selected
package with `sudo pacman -R wechat-bin`. Review dependencies separately; do not
cascade removals or remove shared audio libraries. Preserve account and runtime
data unless their deletion is separately authorized. No system services or
hardware settings need reverting for this package-intent declaration. Undoing
the laptop's separate audio profile selection is documented in the journal and
may restore its original silent behavior; it is not part of uninstalling WeChat.
