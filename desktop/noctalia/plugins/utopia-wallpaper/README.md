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
by Noctalia and closes the panel. Source-tab shortcuts live in tooltips rather
than permanent labels, and both sources present the same goal-oriented “Set
wallpaper” action; an online selection is downloaded as an implementation
detail before it is applied.

The attached panel is 640 logical pixels tall. This keeps the footer and Apply
action away from the screen edge on 800-pixel-tall outputs after Noctalia
reserves the top bar; the thumbnail grid scrolls when filters or additional
rows need more room. Its zero minimum height lets the online filter toolbar
consume space without pushing the pagination and Apply footer out of view.
Local and Wallhaven share a stable keyed scroll node, while the online toolbar
is conditionally present and the footer keeps its own stable identity. This
avoids stale layout geometry without forcing the image surface to be recreated
on every source switch.

Local previews use ImageMagick, with FFmpeg as a fallback, to build 410×232
JPEG thumbnails asynchronously under Noctalia's persistent plugin data
directory. Cache keys include the source path, size, and modification time, so
changing an image invalidates its preview without exposing the local path in a
cache filename. Cached previews avoid decoding full-resolution wallpapers
every time the source tab changes; the first load shows lightweight
placeholders while missing thumbnails are generated. If neither thumbnailer
is available, the plugin remains functional and logs that it is falling back
to the original images. Both tools are part of Utopia's declared Arch package
intent.

For runtime validation, an already-open panel accepts `source local`,
`source online`, and `refresh` through Noctalia's plugin IPC. These events call
the same functions as the visible tabs and refresh button; they do not add a
second wallpaper workflow.
