# Candidate-position runner review — 2026-10-22

This is a read-only source review following the maintainer-confirmed
[neutral A/B reproducer](README.md). The working desktop runner remains Wine
Staging 11.19. No new runner, replacement DLL, prefix, package, or input-method
setting was installed or deployed during this review. No upstream issue was
submitted.

## Reviewed snapshots

| Source | Exact revision | Relevant observation |
| --- | --- | --- |
| [Wine 11.20 IMM32](https://github.com/wine-mirror/wine/blob/7298a818b79446bae153b8d5aa27235ab3703bf9/dlls/imm32/imm.c) | `7298a818b79446bae153b8d5aa27235ab3703bf9` | Candidate setter stores its form and sends notifications; composition setter explicitly forwards a rectangle to the host driver. |
| [Valve Wine, `proton_11.0`, IMM32](https://github.com/ValveSoftware/wine/blob/e60892cc2398b0a83c332a2078c7b85e47bdb42b/dlls/imm32/imm.c) | `e60892cc2398b0a83c332a2078c7b85e47bdb42b` | Same direct-forwarding difference at these two functions. |
| [Wine Staging 11.20 patch tree](https://github.com/wine-staging/wine-staging/tree/711f5be0b016c2730c268eb92369bf56b9ec9782) | `711f5be0b016c2730c268eb92369bf56b9ec9782` | Its recorded upstream commit is the Wine revision above. The complete 630-entry tree had no path matching `imm32`, `candidate`, or `xim`; this is a filename search, not a content audit of every patch. |

This review did not select an evidenced drop-in fix for the reproducer. It does
not establish runtime failure on either newer runner: neither was executed.
Do not describe the review as an exhaustive survey of all Proton derivatives
or assume a version upgrade will fix B. Conversely, function-level similarity
alone cannot rule out differences elsewhere in those runners.

The searchable historical
[2014 candidate-position patch](https://github.com/wine-compholio/wine-staging/blob/master/patches/winex11-CandidateWindowPos/0001-winex11.drv-Update-a-candidate-window-s-position-wit.patch)
updates the XIM spot from Win32 caret operations. It is not evidence of a current
candidate-setter bridge, a maintained binary containing one, or Hearthstone
using those caret operations. It was not copied, applied, or adopted.

## Proposed next experiment — not approved or applied

Testing a private Wine change is a new experimental scope, not routine Utopia
configuration deployment. Obtain the maintainer's choice before preparing a
patched runner or initializing another prefix. Keep the following boundaries:

1. Inspect build prerequisites, source provenance/license, disk use, and a
   bounded build plan first. Do not install missing dependencies implicitly.
   Keep downloaded source, generated code and binaries outside Git; record an
   exact upstream revision and any original patch provenance before adoption.
2. Use a separate user-space runner/build directory and a new temporary prefix.
   Do not reuse the working game prefix for build or probe experiments, change
   system Wine, or copy account and game state into the temporary prefix.
3. Review a narrow candidate-coordinate forwarding change, including candidate
   styles, context/window association, and coordinate/DPI conversion. Preserve
   composition state; do not silently replace the candidate API with a call
   that also changes the application's composition form. A sketch is not a
   validated patch.
4. Run the neutral A/B on both unmodified and modified builds in the same
   isolated setup, with matching display/input settings. B must follow the
   supplied marker and A must remain correct. Include invalid/default styles,
   exclusion-area behavior, resizing, and input-method cleanup as appropriate.
   Use coordinate-only diagnostics, not typed-content or keystroke traces.
5. A passing probe is not game acceptance. Return for separate review before
   trying any runner against Hearthstone; the working prefix can be upgraded
   by Wine merely on launch, so do not point a different build at it casually.
6. Recovery for the probe experiment is simply closing only its test window
   and leaving the isolated artifacts unused. Retain the original runner and
   game prefix unmodified. No service, driver, registry or system rollback
   should be necessary. Never stop the shared game prefix to clean up probes.

An alternative is to prepare a sanitized upstream report from the independent
reproducer and retain candidate placement as a known limitation. Publishing an
issue is a separate external action requiring the maintainer's direction; a
public repository or a reproducible bug is not authorization to post one.
