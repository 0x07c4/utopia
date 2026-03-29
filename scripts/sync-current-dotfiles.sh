#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE_HOME="${SOURCE_HOME:-$HOME}"
DRY_RUN="${DRY_RUN:-0}"

RSYNC_OPTS=(-aL --exclude .git --exclude .git/)
if [[ "$DRY_RUN" == "1" ]]; then
    RSYNC_OPTS+=(-n -v)
fi

sync_path() {
    local rel="$1"
    local src="$SOURCE_HOME/$rel"
    local dst="$REPO_ROOT/$rel"

    [[ -e "$src" || -L "$src" ]] || return 0

    mkdir -p "$(dirname "$dst")"
    rsync "${RSYNC_OPTS[@]}" "$src" "$(dirname "$dst")/"
}

sync_dir_contents() {
    local rel="$1"
    local src="$SOURCE_HOME/$rel/"
    local dst="$REPO_ROOT/$rel/"

    [[ -d "$SOURCE_HOME/$rel" || -L "$SOURCE_HOME/$rel" ]] || return 0

    mkdir -p "$dst"
    rsync "${RSYNC_OPTS[@]}" "$src" "$dst"
}

sync_dir_contents_excluding() {
    local rel="$1"
    local exclude_name="$2"
    local src="$SOURCE_HOME/$rel/"
    local dst="$REPO_ROOT/$rel/"

    [[ -d "$SOURCE_HOME/$rel" || -L "$SOURCE_HOME/$rel" ]] || return 0

    mkdir -p "$dst"
    rsync "${RSYNC_OPTS[@]}" --exclude "$exclude_name" "$src" "$dst"
}

sync_dir_contents_excluding_many() {
    local rel="$1"
    shift
    local src="$SOURCE_HOME/$rel/"
    local dst="$REPO_ROOT/$rel/"

    [[ -d "$SOURCE_HOME/$rel" || -L "$SOURCE_HOME/$rel" ]] || return 0

    mkdir -p "$dst"

    local args=()
    for pattern in "$@"; do
        args+=(--exclude "$pattern")
    done

    rsync "${RSYNC_OPTS[@]}" "${args[@]}" "$src" "$dst"
}

insert_after_anchor() {
    local file="$1"
    local anchor="$2"
    local marker="$3"
    local block="$4"

    if grep -Fq "$marker" "$file"; then
        return 0
    fi

    ANCHOR="$anchor" BLOCK="$block" perl -0pi -e '
        my $anchor = $ENV{"ANCHOR"};
        my $block = $ENV{"BLOCK"};
        s/\Q$anchor\E/$anchor . "\n" . $block/s;
    ' "$file"
}

sync_git_ref() {
    local rel="$1"
    local src="$SOURCE_HOME/$rel"
    local dst="$REPO_ROOT/$rel"

    [[ -e "$src/.git" || -f "$src/.git" ]] || return 0
    [[ -e "$dst/.git" || -f "$dst/.git" ]] || return 0

    local src_head
    src_head="$(git -C "$src" rev-parse HEAD)"

    if [[ "$DRY_RUN" == "1" ]]; then
        echo "[DRY RUN] git -C $dst checkout $src_head"
        return 0
    fi

    git -C "$dst" checkout "$src_head"
}

sync_paths=(
  .zshrc
  .gitconfig
  .config/Thunar
  .config/bottom
  .config/btop
  .config/cava
  .config/fastfetch
  .config/fish
  .config/fontconfig
  .config/fuzzel
  .config/gtk-3.0
  .config/kitty
  .config/lazygit
  .config/lsfg-vk
  .config/mako
  .config/matugen
  .config/mimeapps.list
  .config/mpv
  .config/noctalia
  .config/satty
  .config/scripts
  .config/starship.toml
  .config/swayosd
  .config/waybar
  .config/waybar-niri-Win11Like
  .config/waypaper
  .config/wezterm
  .config/xsettingsd
  .config/xdg-desktop-portal
  .config/xfce4
  .config/yazi
  .local/bin
  .local/share/icons/breeze_cursors
)

for rel in "${sync_paths[@]}"; do
    sync_path "$rel"
done

sync_git_ref ".config/nvim"
sync_git_ref ".config/nvim-lazyvim"

# Source gtk-4.0 currently contains broken links for these theme files.
sync_dir_contents_excluding_many ".config/gtk-4.0" "gtk.css" "gtk-dark.css"

# Keep utopia's fcitx5 as requested.
:

# Sync current niri auxiliary files, but preserve utopia's merged config.kdl.
sync_dir_contents_excluding ".config/niri" "config.kdl"

niri_config="$REPO_ROOT/.config/niri/config.kdl"
if [[ ! -f "$niri_config" ]]; then
    echo "Error: missing $niri_config" >&2
    exit 1
fi

startup_anchor='// This line starts waybar, a commonly used bar for Wayland compositors.
// spawn-at-startup "waybar"'
startup_block='// utopia-sync: wallpaper startup begin
spawn-at-startup "awww-daemon"
spawn-at-startup "awww-daemon" "-n" "overview"
spawn-sh-at-startup "sleep 1 && waypaper --random"
// utopia-sync: wallpaper startup end'
insert_after_anchor "$niri_config" "$startup_anchor" "// utopia-sync: wallpaper startup begin" "$startup_block"

rules_anchor='// Window rules let you adjust behavior for individual windows.
// Find more information on the wiki:
// https://yalter.github.io/niri/Configuration:-Window-Rules'
rules_block='// utopia-sync: wallpaper layer rules begin
layer-rule {
    match namespace="awww-daemonoverview"
    match namespace="swww-daemonoverview"
    place-within-backdrop true
}
// utopia-sync: wallpaper layer rules end'
insert_after_anchor "$niri_config" "$rules_anchor" "// utopia-sync: wallpaper layer rules begin" "$rules_block"

floating_anchor='window-rule {
    // This app-id regular expression will work for both:
    // - host Firefox (app-id is "firefox")
    // - Flatpak Firefox (app-id is "org.mozilla.firefox")
    match app-id=r#"firefox$"# title="^Picture-in-Picture$"
    open-floating true
}'
floating_block='
// utopia-sync: waypaper floating begin
window-rule {
    match app-id="waypaper"
    open-floating true
}
// utopia-sync: waypaper floating end'
insert_after_anchor "$niri_config" "$floating_anchor" "// utopia-sync: waypaper floating begin" "$floating_block"

binds_anchor='    Mod+T hotkey-overlay-title="Open a Terminal: kitty" { spawn "kitty"; }
    Mod+D hotkey-overlay-title="Run an Application: fuzzel" { spawn "fuzzel"; }'
binds_block='    // utopia-sync: wallpaper binds begin
    Mod+Alt+W hotkey-overlay-title="Change wallpaper: waypaper" { spawn "waypaper"; }
    Mod+F10 hotkey-overlay-title="Random wallpaper: waypaper" { spawn "waypaper" "--random"; }
    Mod+Shift+F10 hotkey-overlay-title="Random anime wallpaper" { spawn "~/.config/scripts/random-anime-wallpaper.sh"; }
    // utopia-sync: wallpaper binds end'
insert_after_anchor "$niri_config" "$binds_anchor" "// utopia-sync: wallpaper binds begin" "$binds_block"

echo "Sync complete."
echo "Kept utopia's fcitx5 untouched."
echo "Preserved utopia's niri config body and re-applied wallpaper patches idempotently."
