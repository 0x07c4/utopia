# Dynamic palette evaluation

This directory evaluates wallpaper-driven color policy without changing a live
desktop. It is deliberately separate from Noctalia's deployed configuration.

`policy-v1.toml` is an **experimental candidate**, not an approved Utopia visual
identity. It keeps dark surfaces and semantic status colors stable, selects up
to three sufficiently saturated wallpaper colors, rejects near-duplicate hues,
and adjusts accents until they meet the declared contrast floor. A versioned
fallback fills any missing accent roles.

The fixtures are Utopia-owned synthetic SVG wallpapers licensed with the rest
of the project under Apache-2.0. They cover green-dominant, cool, and warm color
distributions without embedding a personal wallpaper or third-party binary.
The evaluator rasterizes them only in its output directory.

Run the review from the repository root with Noctalia 5.1 and ImageMagick
available:

```sh
python -m desktop.theme.evaluate --output /tmp/utopia-theme-review
```

When the active host uses Noctalia's packaged default wallpaper, include that
installed asset as a local-only fourth fixture:

```sh
python -m desktop.theme.evaluate \
  --include-noctalia-default \
  --output /tmp/utopia-theme-review-default
```

The evaluator records the Noctalia version, asset checksum, and MIT provenance
in the untracked report. It does not vendor the wallpaper or expose a personal
wallpaper path.

To evaluate the wallpaper currently selected on the active host, pass it as a
local-only input:

```sh
python -m desktop.theme.evaluate \
  --selected-wallpaper "$(noctalia msg wallpaper-get)" \
  --output /tmp/utopia-theme-review-selected
```

The report labels this input `local:selected-wallpaper` and records only its
checksum and local-only distribution status. It does not record the source path
or copy the image into the repository.

The command compares Noctalia's current `m3-content` behavior, its more strongly
wallpaper-driven `vibrant` scheme, and the controlled candidate. It writes
`comparison.html`, `comparison.svg`,
`report.json`, and temporary PNG fixture renders below the requested output
directory. The output directory must not already exist. Rendered palettes and
wallpaper derivatives are review artifacts and must not be committed.

The HTML review keeps one desktop scene fixed across every palette: the declared
Noctalia bar order, Niri focus treatment, Kitty window, the established
Powerline prompt stages, control-center card, and notification card. This is an
isolated rendering of the intended component structure, not a deployment or a
live-desktop screenshot.

This evaluator does not modify Noctalia settings, render configured templates,
run post-hooks, or write below `$HOME`. Approval of a visual direction is still
required before changing `.config/noctalia/visuals.toml` or deploying generated
Niri, Kitty, or Starship colors.
