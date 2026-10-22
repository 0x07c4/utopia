# Isolated candidate-coordinate bridge experiment

This is an experimental `cachyos-desktop` probe result, not a Hearthstone fix.
The maintainer continued with the scoped experiment on 2026-10-22. Only a private
runner copy and a new temporary prefix participated in neutral tests; the
working game prefix and accounts were not used. The separately approved game
trial below used the working prefix after a verified full cold backup; the
trial failed and that prefix has since been restored and verified.
The ordinary runner and launch entry remain unchanged.
No system package, service, driver or global input setting was changed.

## Change and provenance

The original [patch](imm32-candidate-position.patch) targets Wine `wine-11.19`,
commit `455e3509b98a6919fd4ad1def4803e08c41c03b2`. The patch and its Wine context
are LGPL-2.1-or-later; see [the notice](../../../THIRD_PARTY_NOTICES.md#wine-candidate-position-experiment)
and the verbatim license under `LICENSES/`. No historical Staging patch was
adopted. Downloaded Wine source and compiled modules remain outside Git.

The change forwards only primary-list candidate anchors to the existing host
rectangle operation. For `CFS_EXCLUDE`, revision 2 approximates avoidance by
using the exclusion rectangle's lower edge. [Wine's X11 driver](https://github.com/wine-mirror/wine/blob/455e3509b98a6919fd4ad1def4803e08c41c03b2/dlls/winex11.drv/xim.c)
forwards only
`rect.left/top` as `XNSpotLocation`, discarding its extent; forwarding the full
rectangle in revision 1 therefore placed the panel over it. The lower-edge
fallback is not a full exclusion contract: screen-edge adjustment, large panels
and other host drivers may still overlap. Only this X11 environment was tested.
The change preserves notifications and return
behavior, and does not call `ImmSetCompositionWindow` or overwrite `cfCompForm`.
Secondary lists and default/unsupported styles retain the prior behavior.
This is not complete Windows IME compatibility or an upstream-accepted patch.

## Local construction

Existing Clang/LLD, Bison, Flex, Make and Wine SDK tools were sufficient. The
fixed official source archive was extracted under a fresh temporary root. The
single IMM32 PE target was built with two jobs, first unmodified, then patched
in the same build tree. The first output was saved before modifying the source.
Both outputs are standard Wine PE32+ DLLs. The build shape was:

```sh
../source/configure --enable-win64 --disable-tests --with-mingw=clang \
  --without-x --without-wayland --without-alsa --without-pulse --without-dbus \
  --without-gstreamer --without-vulkan --without-opengl
make -j2 dlls/imm32/x86_64-windows/imm32.dll
```

These options configure a **module build**, not a replacement runtime; they
change no runtime graphics driver or system audio. The working traditional
Staging 11.19 runner was copied into the temporary root without hard-linking its
DLL to the original. Only the copy's 64-bit `lib/wine/x86_64-windows/imm32.dll`
is switched between the saved outputs. The original DLL's SHA-256 is unchanged.

The new prefix contains no copied account/game data. Only this temporary prefix
received DPI 192 and the installed Noto Sans CJK font plus its Microsoft YaHei
font link for readable probe labels. Test processes clear inherited loader,
server, DLL-path overrides and `WAYLAND_DISPLAY`, retaining X11 `DISPLAY`/XIM
settings. They use `WINEARCH=win64`, `WINEDEBUG=-all`, and
`WINEDLLOVERRIDES=winemenubuilder.exe=d;mscoree,mshtml=d` to disable menu
integration and Mono/Gecko downloads.

Every command names the new temporary `WINEPREFIX`. Before module replacement,
only that prefix's Wine server is stopped and awaited, with a bounded wait.
The no-server return means already stopped; other errors/timeouts abort the
switch. Never use the game prefix or default `~/.wine`, kill an ambiguous window
PID, or replace a module while its test processes are running.

## Loaded-implementation check

Replacing a runner file alone does not prove it loaded. The probe's
`--module-check` and visual runs now fingerprint a 512-byte code region from
`ImmSetCandidateWindow` in **the probe's own address space**. Compare against
the matching export bytes from the two locally built PE files:

```sh
python desktop/gaming/diagnostics/pe-candidate-fingerprint.py \
  "$experiment_root/modules/imm32-baseline.dll" \
  "$experiment_root/modules/imm32-patched.dll"
```

Use the explicit private runner/prefix environment for `--module-check`, too.
The two builds produced distinct fingerprints, and accepted visual runs printed
the expected implementation. The verifier uses the Python standard library.
This is a region fingerprint, not a claim about function length. The initial
64-byte method distinguished baseline/revision 1 but failed to distinguish the
exclusion revision. It was expanded before accepting revision 2, with a test
for changes beyond the initial span. This is a local build discriminator, not
authentication; different compiler
output or relocations can invalidate a byte comparison.

An initial `/proc` mapping check was inconclusive. Compositor-reported Xwayland
PIDs and PE mapping names were not used as process identity or load proof.
Although the prefix retained an older DLL file, the probe's own fingerprint
matched the private runner's patched code. The ambiguous first window was
excluded; direct verification was added before the accepted runs. No game
memory, typed contents or keystrokes were inspected.

## Evidence and remaining gates

| Check | Result |
| --- | --- |
| API form contracts, unmodified module at DPI 192 | Zero failures. |
| Same contracts, modified module at DPI 192 | Zero failures. |
| Patched B in the isolated prefix | Maintainer confirmed the panel near the lower marker. |
| Reverse control: unmodified B, same prefix/settings | Maintainer confirmed return to the upper-left. |
| Patched A regression | Maintainer confirmed the panel still near the lower marker. |
| Revision 1 exclusion-area C | Maintainer confirmed near the marker but overlapping; failed. |
| Revision 2 lower-edge fallback C | Maintainer confirmed near the marker without overlap. |
| Revision 2 C width change and focus round trip | Maintainer confirmed normal after narrowing and switching away/back. |
| Revision 2 A | Maintainer confirmed near the point marker, with overlap. Point mode has no exclusion requirement. |
| Revision 2 B | Maintainer confirmed near the point marker. |
| Game trial | Failed: maintainer screenshot shows candidates still upper-left, far from the game field. No permanent deployment. |

Contracts cover point, exclusion, secondary and default candidate forms, form
readback, preserving composition state, and rejecting a null form/out-of-range
list. They do not verify visible placement or every style combination. The
separate no-window `--self-test` is only a startup check, not an IME test.

The follow-up probe adds `--exclude` (C) with a visible exclusion rectangle,
and refreshes its own anchor on size/movement/focus changes. It was rebuilt
with strict warnings and passed the hidden contracts with the patched
fingerprint at DPI 192. After the first visual failure, the revised bridge was
rebuilt and loaded only after stopping the isolated prefix; revision 1's output
was retained. Revision 2 contracts also pass, and its visible C placement was
accepted. The same C window was narrowed from 936 to 720 logical pixels;
the maintainer confirmed normal placement after narrowing and switching to a
terminal and back (recomposition was allowed). This does not establish
uninterrupted preedit retention or arbitrary screen-edge avoidance. C was
then stopped through only its isolated prefix. Revision 2 A and B were tested
in sequence with the verified revision 2 fingerprint. The maintainer confirmed
A near (but covering) its marker and B near its marker. A/B specify a point,
not an exclusion rectangle, so covering their marker is not the C failure.
All temporary probes were then stopped only through their isolated prefix;
artifacts remain. Do not repeat this completed neutral matrix without a new
change or specific regression.

The neutral results support this narrow experiment, not proof of Hearthstone's
API usage. Screen-edge/large-panel behavior, uninterrupted preedit retention
and non-X11 drivers remain outside acceptance. They are not game acceptance.

## Separately approved single game trial

The next useful evidence is one actual game-input check, not a broader neutral
test suite. The maintainer explicitly approved this plan on 2026-10-22 and
confirmed normal exit from Hearthstone and Battle.net. No prefix processes or
matching application windows remained, and a bounded prefix-scoped server wait
completed. A private timestamped full cold backup was made with metadata and
symlinks preserved, without hard links, then verified with a checksum/metadata
dry-run comparison. The game executable is inside the prefix; XDG-folder links
are links, not backups of those external folders. No external folder is an
explicit trial write target. Revision 2's module hash was rechecked and private-runner
Battle.net started against the working prefix. The maintainer launched the
game and supplied a screenshot with the candidate panel still upper-left,
far from the input field. Candidate positioning therefore failed; text
selection/commit was not separately accepted. The neutral result did not
transfer to the actual game. It remains unknown whether the game uses this
API path or loads the expected module; probe fingerprints establish neither.
No game memory, typed-content trace or conversations were inspected. The
maintainer then confirmed normal exit from both apps for recovery. After a
prefix-process/server stop check, a staged copy of the cold backup passed the
checksum/metadata comparison. The post-trial prefix was moved aside without
deletion, the staged copy restored to the exact original path, and a second
comparison passed. Cold backup and post-trial prefix are retained privately.
The ordinary runner/entry were never replaced; no game was relaunched after
recovery. Do not repeat the same failed trial without new evidence.
Do not claim that the original prefix stayed unused after this approved launch.
Local paths, backup, accounts and logs remain outside Git. On this desktop only:

1. The maintainer normally exits Hearthstone and Battle.net. Confirm no prefix
   processes remain; do not kill an active game or infer identity from the
   compositor's shared Xwayland PID.
2. Make a timestamped, permission-restricted, full cold prefix backup outside
   Git, preserving symlinks and metadata without hard links. Check free space,
   copy exit status and a no-write comparison before proceeding. A live copy
   is not a consistent backup. Inventory and any account-bearing data stay
   private. Leave the original runner and ordinary launcher unchanged.
3. Verify the private runner's revision 2 module hash and provenance. This is
   an upstream Wine 11.19 IMM32 module inside a Staging runner copy, not a full
   matched Staging rebuild; the neutral checks do not guarantee game
   compatibility. Record the exact trial runner and backup locally.
4. Use that explicit private runner/prefix for a temporary launch only after
   approval and backup. Clear inherited loader/DLL overrides, keep debug
   tracing off, and do not change registry, DPI, global input or the regular
   launcher. Wine may alter prefix state merely on startup. A probe's own-code
   fingerprint is not proof of what the game loaded; do not inspect game
   memory or enable private-input tracing to obtain that proof.
5. Have the maintainer type neutral Chinese test text in an existing game
   field, observe candidate location and confirm selection/commit, then clear
   it without sending. No match or account interaction is needed. Record only
   the result, not social screenshots or input logs. An unchanged result ends
   the trial rather than prompting speculative global changes.
6. Exit normally and return to the original runner. On failure, keep the
   post-trial prefix separately and restore the verified cold backup before
   normal launch; never overwrite or delete the only copy. Review exact paths
   before restoration. A successful test still needs separate promotion of
   any regular-launch change; this plan does not authorize permanent deploy.

## Recovery

Close only temporary probes; if normal closing is ineffective, stop only the
verified temporary prefix and wait before module replacement. Leave artifacts
unused. For neutral probes no working-game/system rollback was needed. The
approved game trial may change prefix state merely on launch; use its cold
backup/original-runner recovery above. No system change is in scope.
Do not delete prefixes, source trees, caches or game data during cleanup.
Generated files/local inventory remain outside Git. No upstream issue was posted.
