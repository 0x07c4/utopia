# IME coordinate reproducer

`ime-coordinate-probe.c` is an original, independent Windows test application,
not a game adapter. It owns only its own window and input context. It does not
attach to games, read their memory, inject hooks, synthesize input, install a
service, or change registry, input-method, scaling, or theme settings.

It draws a lower-window marker at one-fifth of client width and three-quarters
of client height, then reports that position through one of two Windows APIs:

| Mode | Position API and style | Desktop observation on Wine Staging 11.19 |
| --- | --- | --- |
| A: `--composition` | `ImmSetCompositionWindow`, `CFS_POINT` | Candidate panel appeared beside the lower marker. |
| B: `--candidate` | `ImmSetCandidateWindow`, `CFS_CANDIDATEPOS` | Candidate panel remained near the upper-left instead. |

The maintainer supplied both visual results on `cachyos-desktop` on 2026-10-22.
Both API calls returned success. Both runs logged the same client/screen anchor
of `(374, 1521)` and DPI 192 under the existing Wine/XIM/Fcitx environment. Each
mode ran in a new test process, with A closed before B started. The application
logs only API status and its own coordinates/DPI, never composed or committed
text. It deliberately discards text, so it does **not** test text commit.

This isolates a candidate-only positioning failure in a neutral application;
it is not proof that Hearthstone calls only that API. It is not a general
failure of theme rendering or proof that every Wine application mispositions
its candidates. The game remains unchanged and its input positioning is not
accepted as fixed.

## Explicit local build and run

These commands reuse the already-reviewed desktop runner, SDK and retained
prefix described in [the trial](../hearthstone-cn.md). They do not authorize
installing missing tools, creating a prefix, or deployment to another host.
Use an existing Windows-target compiler/linker. Build into a fresh temporary
directory; no executable belongs in Git or the deployed helper directory.

```sh
data_root=${XDG_DATA_HOME:-"$HOME/.local/share"}
wine_runner="$data_root/lutris/runners/wine/wine-11.19-staging-amd64"
trial_prefix="$data_root/utopia/gameprefixes/battlenet-cn-legacy"
test -f "$trial_prefix/system.reg" || exit 1
build_dir=$(mktemp -d)
"$wine_runner/bin/winegcc" -b x86_64-windows -m64 -Wall -Wextra -Werror -O2 \
  desktop/gaming/diagnostics/ime-coordinate-probe.c \
  -o "$build_dir/ime-coordinate-probe.exe" -limm32 -luser32 -lgdi32
file "$build_dir/ime-coordinate-probe.exe"  # must report Windows PE32+
```

Clear inherited runner overrides and keep Wine debug traces off; ordinary IME
debug output can include private input. Run the no-window self-test first:

```sh
env -u WINEARCH -u WINEDLLOVERRIDES -u WINELOADER -u WINESERVER \
  WINEDEBUG=-all WINEPREFIX="$trial_prefix" \
  "$wine_runner/bin/wine" "$build_dir/ime-coordinate-probe.exe" --self-test
```

Then run A, click only its test window, activate Chinese input and type a neutral
test phrase such as `nihao`. Leave the candidate panel open to observe its
position relative to the marker. Close **only the probe window** before running
B. Use the same output, runner, prefix and input-method settings for both.

```sh
env -u WINEARCH -u WINEDLLOVERRIDES -u WINELOADER -u WINESERVER \
  WINEDEBUG=-all WINEPREFIX="$trial_prefix" \
  "$wine_runner/bin/wine" "$build_dir/ime-coordinate-probe.exe" --composition

# After closing A:
env -u WINEARCH -u WINEDLLOVERRIDES -u WINELOADER -u WINESERVER \
  WINEDEBUG=-all WINEPREFIX="$trial_prefix" \
  "$wine_runner/bin/wine" "$build_dir/ime-coordinate-probe.exe" --candidate
```

Esc closes the probe (an input method may consume the first Esc to cancel its
composition); the compositor close action also works. Do not kill the prefix
or Wine server: games and the launcher may still be running. No configuration
rollback is needed because the probe changes none. Keep binaries, screenshots
and local logs outside Git.

## Interpretation boundary

[Microsoft documents candidate positioning](https://learn.microsoft.com/en-us/windows/win32/api/imm/nf-imm-immsetcandidatewindow)
separately from [composition positioning](https://learn.microsoft.com/en-us/windows/win32/api/imm/nf-imm-immsetcompositionwindow).
In [Wine 11.19 IMM32](https://github.com/wine-mirror/wine/blob/wine-11.19/dlls/imm32/imm.c),
the composition path explicitly forwards a rectangle to the host driver; the
candidate setter stores its form and sends notifications without that same
forwarding call. The neutral results are consistent with that asymmetry in the
reviewed runner; they do not identify Hearthstone's actual API calls or prove a
fix in a different Wine release. Do not substitute a new runner, patched DLL or
global Fcitx setting on the strength of this comparison alone. A candidate fix
must first pass this reproducer and then a scoped game-input check, with the
existing runner/prefix kept recoverable.

The [runner source review](runner-review.md) records the exact newer Wine,
Valve and Staging snapshots examined next. It does not select a verified fix or
authorize replacing the working runner; a separate experiment needs review.

The subsequently selected [isolated bridge experiment](candidate-bridge-experiment.md)
has its own patch, license, private-prefix boundary and remaining acceptance
gates. It is not installed in the game environment. The probe also supports
`--contract-test` (hidden own-window form/state checks) and `--module-check`
(own candidate-function fingerprint). Visual runs print that fingerprint too;
neither mode reads game state or text.

## Isolated visual regression modes

For the private runner/new-prefix experiment only, `--exclude` opens C and
reports a `CFS_EXCLUDE` rectangle at the lower marker. The panel should be near
that rectangle without overlapping it, not merely somewhere outside it. This
follows the [candidate form contract](https://learn.microsoft.com/en-us/windows/win32/api/imm/ns-imm-candidateform).
The rectangle is 360 by 96 client pixels; point modes keep their existing
marker and API behavior. C logs only the same own-window status/coordinates.

Visual modes refresh their anchor on window size, movement and focus changes,
as well as composition events. This models an application updating its own
layout; it does not establish that a game performs those updates. Test each
size/focus transition with a visible candidate panel, and distinguish API
success from visible acceptance. Use only the isolated environment described
in the experiment, not the working game prefix, for these patched runs.
