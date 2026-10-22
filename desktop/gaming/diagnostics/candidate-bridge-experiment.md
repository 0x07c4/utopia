# Isolated candidate-coordinate bridge experiment

This is an experimental `cachyos-desktop` probe result, not a Hearthstone fix.
The maintainer continued with the scoped experiment on 2026-10-22. Only a private
runner copy and a new temporary prefix participate; the working game runner,
prefix, accounts, saves and launch entry are not modified or used for tests.
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
| Revision 2 A/B regressions | Not accepted yet. |
| Hearthstone with this experiment | Not attempted or authorized. |

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
then stopped through only its isolated prefix; revision 2 A is open for visual
confirmation. Earlier A/B acceptance applies to revision 1, not automatically
to the new module.

B/reverse control and the accepted A regression support revision 1 in the
neutral reproducer, not proof of Hearthstone's API usage. Before a game trial,
separately review the remaining regressions,
runner provenance, full prefix backup/recovery, and module verification without
private-input tracing. Do not point a different build at the working game
prefix, which Wine may modify merely on startup.

## Recovery

Close only temporary probes; if normal closing is ineffective, stop only the
verified temporary prefix and wait before module replacement. Leave artifacts
unused. No working-game/system rollback is needed because neither changed.
Do not delete prefixes, source trees, caches or game data during cleanup.
Generated files/local inventory remain outside Git. No upstream issue was posted.
