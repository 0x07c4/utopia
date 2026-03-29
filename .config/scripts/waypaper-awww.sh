#!/bin/bash

set -euo pipefail

WALLPAPER="${1:-}"

if [[ -z "$WALLPAPER" || ! -f "$WALLPAPER" ]]; then
    notify-send "waypaper / awww" "壁纸路径无效: $WALLPAPER"
    exit 1
fi

ensure_awww_daemon() {
    if awww query >/dev/null 2>&1; then
        return 0
    fi

    awww-daemon >/dev/null 2>&1 &

    for _ in 1 2 3 4 5; do
        sleep 0.2
        if awww query >/dev/null 2>&1; then
            return 0
        fi
    done

    return 1
}

ensure_awww_daemon

exec awww img "$WALLPAPER" \
    --transition-duration 2 \
    --transition-type center \
    --transition-fps 60
