# Utopia Wallpaper Center

This Utopia-owned Noctalia plugin presents local wallpapers and online
Wallhaven discovery as one keyboard-first workflow. It stores downloaded image
files in the configured home-relative wallpaper directory and runtime thumbnail
cache in Noctalia's plugin data directory; neither belongs in Git.

The online page uses Wallhaven's public API directly. Its neutral default is
all categories, SFW content, newest first, with no aspect-ratio or resolution
restriction. Search, all seven API sort modes, sort direction, toplist period,
category, purity, aspect ratio, resolution, and direct page entry remain
explicit controls instead of hidden request policy. Wallhaven's 24-result API
page size is not presented as the size of the whole result set.

An optional API key can be entered through Noctalia's plugin settings for
higher rate limits and NSFW access. No key is tracked by Utopia. The
implementation was written independently against Noctalia's public plugin API.
No code or assets from the MIT-licensed official `noctalia/wallhaven` plugin
are bundled; that plugin was used only as a behavioral and API-integration
reference:

- <https://docs.noctalia.dev/noctalia/plugins/development/declarative-ui/>
- <https://github.com/noctalia-dev/official-plugins/tree/main/wallhaven>
- <https://wallhaven.cc/help/api>

Keyboard controls inside the panel are `Ctrl+1`/`Ctrl+2` for source tabs,
arrow keys for selection, `Enter` to apply or submit the focused search/filter,
`PageUp`/`PageDown` for pages, `Ctrl+L` for online search, and `Ctrl+R` to
refresh. The online page number is directly editable. `Escape` remains owned
by Noctalia and closes the panel.

For runtime validation, an already-open panel accepts `source local`,
`source online`, and `refresh` through Noctalia's plugin IPC. These events call
the same functions as the visible tabs and refresh button; they do not add a
second wallpaper workflow.
