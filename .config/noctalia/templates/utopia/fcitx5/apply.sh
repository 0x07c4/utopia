#!/usr/bin/env bash
set -euo pipefail

# Noctalia renders theme.conf before calling this hook. Keep the generated
# directory outside Git and reuse the reviewed static icon assets from the
# fixed Catppuccin fallback theme.
config_home="${XDG_CONFIG_HOME:-${HOME}/.config}"
opt_in="$config_home/utopia/enable-fcitx-wallpaper"
if [[ ! -f "$opt_in" ]]; then
  exit 0
fi

data_home="${XDG_DATA_HOME:-${HOME}/.local/share}"
theme_dir="${data_home}/fcitx5/themes/utopia-wallpaper"
theme_file="${theme_dir}/theme.conf"
fallback_dir="${data_home}/fcitx5/themes/catppuccin-mocha-green"

if [[ ! -f "$theme_file" ]]; then
  printf 'utopia-fcitx5: rendered theme is missing: %s\n' "$theme_file" >&2
  exit 1
fi

for asset in arrow.png radio.png; do
  if [[ ! -f "$fallback_dir/$asset" ]]; then
    printf 'utopia-fcitx5: fallback asset is missing: %s\n' "$fallback_dir/$asset" >&2
    exit 1
  fi
done

section_color() {
  local section="$1"
  awk -v section="$section" '
    $0 == "[" section "]" { in_section = 1; next }
    in_section && /^\[/ { exit }
    in_section && /^Color=/ { sub(/^Color=/, ""); print; exit }
  ' "$theme_file"
}

is_hex_color() {
  [[ "$1" =~ ^#[0-9a-fA-F]{6}$ ]]
}

background_color="$(section_color 'InputPanel/Background')"
highlight_color="$(section_color 'InputPanel/Highlight')"
if ! is_hex_color "$background_color" || ! is_hex_color "$highlight_color"; then
  printf 'utopia-fcitx5: invalid generated colors: background=%s highlight=%s\n' \
    "$background_color" "$highlight_color" >&2
  exit 1
fi

mkdir -p "$theme_dir"
staging_dir="$(mktemp -d "${theme_dir}.staging.XXXXXX")"
cleanup() {
  rm -rf "$staging_dir"
}
trap cleanup EXIT

cp "$fallback_dir/arrow.png" "$staging_dir/arrow.png"
cp "$fallback_dir/radio.png" "$staging_dir/radio.png"
printf '<svg width="39" height="39" version="1.1" xmlns="http://www.w3.org/2000/svg">\n  <rect width="39" height="39" rx="8" fill="%s"/>\n</svg>\n' \
  "$background_color" >"$staging_dir/panel.svg"
printf '<svg width="39" height="39" version="1.1" xmlns="http://www.w3.org/2000/svg">\n  <rect width="39" height="39" rx="8" fill="%s"/>\n</svg>\n' \
  "$highlight_color" >"$staging_dir/highlight.svg"

for asset in arrow.png radio.png panel.svg highlight.svg; do
  mv "$staging_dir/$asset" "$theme_dir/$asset"
done

# Reload only Classic UI. If Fcitx or the session bus is unavailable, the
# generated files remain valid and will be picked up on the next start.
if busctl --user status org.fcitx.Fcitx5 >/dev/null 2>&1; then
  busctl --user call \
    org.fcitx.Fcitx5 \
    /controller \
    org.fcitx.Fcitx.Controller1 \
    ReloadAddonConfig s classicui >/dev/null
fi
