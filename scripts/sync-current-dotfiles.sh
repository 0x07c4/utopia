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

sync_git_ref() {
    local rel="$1"
    local src="$SOURCE_HOME/$rel"
    local dst="$REPO_ROOT/$rel"

    [[ -e "$src/.git" || -f "$src/.git" ]] || return 0
    local src_head
    src_head="$(git -C "$src" rev-parse HEAD)"

    if [[ ! -e "$dst/.git" && ! -f "$dst/.git" ]]; then
        if [[ "$DRY_RUN" == "1" ]]; then
            echo "[DRY RUN] git -C $REPO_ROOT update-index --add --cacheinfo 160000 $src_head $rel"
            return 0
        fi

        git -C "$REPO_ROOT" update-index --add --cacheinfo 160000 "$src_head" "$rel"
        return 0
    fi

    if [[ "$DRY_RUN" == "1" ]]; then
        echo "[DRY RUN] git -C $dst checkout $src_head"
        return 0
    fi

    git -C "$dst" checkout "$src_head"
}

sync_paths=(
  .zshrc
  .zimrc
  .gitconfig
  .ssh/config
  .config/Thunar
  .config/bottom
  .config/btop
  .config/cava
  .config/fastfetch
  .config/fish
  .config/fontconfig
  .config/environment.d/fcitx5.conf
  .config/fcitx5
  .config/gtk-3.0
  .config/kitty
  .config/lazygit
  .config/lsfg-vk
  .config/mimeapps.list
  .config/mpv
  .config/noctalia
  .config/satty
  .config/starship.toml
  .config/swayosd
  .config/wezterm
  .config/xsettingsd
  .config/xdg-desktop-portal
  .config/xfce4
  .config/yazi
  .local/share/icons/breeze_cursors
)

for rel in "${sync_paths[@]}"; do
    sync_path "$rel"
done

# Codex is installed by npm; keep its generated launcher out of the snapshot.
sync_dir_contents_excluding ".local/bin" "codex"

sync_path ".local/share/fcitx5/rime/default.custom.yaml"
sync_path ".local/share/fcitx5/rime/key_bindings.custom.yaml"
sync_path ".local/share/fcitx5/rime/rime_ice.custom.yaml"
sync_path ".local/share/fcitx5/rime/rime_ice.dict.yaml"
sync_path ".local/share/fcitx5/themes/catppuccin-mocha-green"

sync_git_ref ".config/nvim"

# Source gtk-4.0 currently contains broken links for these theme files.
sync_dir_contents_excluding_many ".config/gtk-4.0" "gtk.css" "gtk-dark.css"

# Sync the complete current niri configuration.
sync_dir_contents ".config/niri"

echo "Sync complete."
echo "Synced the current niri configuration."
