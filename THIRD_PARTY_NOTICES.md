# Third-party notices

This file records third-party material distributed by or referenced from this
repository. A license listed here applies only to the paths named in its entry.
Except for these path-scoped exclusions and material carrying its own notice,
Utopia's original material is licensed under the Apache License 2.0 in the root
`LICENSE` file.

## Starship Gruvbox Rainbow preset

- Path: `shell/starship/starship.toml`
- Project: Starship
- Upstream: <https://github.com/starship/starship>
- Preset source: `docs/public/presets/toml/gruvbox-rainbow.toml`
- Verified revision: `fca92d8dcbd5981b0160af2f7ed7a430b6475a72` (`v1.26.0`)
- License: ISC
- License copy: `LICENSES/Starship-ISC.txt`

Utopia's configuration preserves the preset's Powerline structure and module
ordering, but replaces its Gruvbox palette with Noctalia-managed semantic color
roles, retains the workstation's established module coverage, and adds a
deterministic fallback. It is modified material, not a byte-for-byte copy.

## Catppuccin for Kitty

- Path: `terminal/kitty/themes/frappe.conf`
- Project: Catppuccin for Kitty
- Upstream: <https://github.com/catppuccin/kitty>
- Verified revision: `43098316202b84d6a71f71aaf8360f102f4d3f1a`
- License: MIT
- License copy: `LICENSES/Catppuccin-Kitty-MIT.txt`

The distributed file is byte-for-byte identical to
`themes/frappe.conf` at the verified revision.

## Rime Ice

- Path: `input/rime/rime_ice.dict.yaml`
- Project: Rime Ice (雾凇拼音)
- Upstream: <https://github.com/iDvel/rime-ice>
- Verified revision: `f3c796bb008a0ccc2bcd08aac66b82036120589e`
- License: GPL-3.0-only
- License copy: `LICENSES/Rime-Ice-GPL-3.0-only.txt`

The distributed file is byte-for-byte identical to
`rime_ice.dict.yaml` at the verified revision. The other files under
`input/rime/` are Utopia-specific configuration and are not claimed to come
from this upstream revision.

## Catppuccin for Fcitx5

- Path: `input/fcitx5/themes/catppuccin-mocha-green/`
- Project: Catppuccin for Fcitx5
- Upstream: <https://github.com/catppuccin/fcitx5>
- Verified revision: `393845cf3ed0e0000bfe57fe1b9ad75748e2547f`
- License: MIT
- License copy: `LICENSES/Catppuccin-Fcitx5-MIT.txt`

The image and SVG assets are byte-for-byte identical to the upstream
`catppuccin-mocha-green` directory at the verified revision. Utopia's
`theme.conf` enables the upstream rounded-corner assets; those two uncommented
`Image` lines are the only modification. The Fcitx configuration selects this
fixed, attributed theme until a wallpaper-driven Fcitx adapter is designed.

## Neovim configuration submodule

- Gitlink path: `editor/nvim`
- Repository: <https://github.com/0x07c4/nvim-astro>
- Pinned revision: `428b7f214fc3263c51c6c9d5a5d2a79fdf816b43`
- Based on: <https://github.com/AstroNvim/template>
- Template revision reviewed: `49a7161b776f8bc6c23508819ea1ad4e7b359bee`

The submodule is a separate Git repository rather than vendored content. No
license file was present in either the pinned submodule revision or the
AstroNvim template when this inventory was performed. The submodule therefore
is not covered by Utopia's Apache-2.0 license. Its own provenance and licensing
must be resolved in that repository before treating it as redistributable
source.
