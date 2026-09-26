# Third-party notices

This file records third-party material distributed by or referenced from this
repository. A license listed here applies only to the paths named in its entry.
Except for these path-scoped exclusions and material carrying its own notice,
Utopia's original material is licensed under the Apache License 2.0 in the root
`LICENSE` file.

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

## Removed material with unresolved provenance

The former `input/fcitx5/themes/catppuccin-mocha-green/` theme named authors
but provided no license or verifiable upstream. Its image and SVG assets were
removed instead of assuming redistribution permission. Fcitx now refers to its
packaged `default` and `default-dark` themes. A future generated theme must have
an explicit Utopia-owned implementation or a recorded upstream license.
