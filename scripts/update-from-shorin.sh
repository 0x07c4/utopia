#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SYNC_SCRIPT="$REPO_ROOT/scripts/sync-current-dotfiles.sh"

SHORIN_REMOTE="${SHORIN_REMOTE:-https://github.com/SHORiN-KiWATA/Shorin-ArchLinux-Guide.git}"
SHORIN_ROOT="${SHORIN_ROOT:-$HOME/workspace/vendor/shorin-guide}"
SHORIN_BRANCH="${SHORIN_BRANCH:-main}"
DRY_RUN="${DRY_RUN:-0}"
SKIP_FETCH="${SKIP_FETCH:-0}"

ensure_clean_vendor_repo() {
    if [[ -n "$(git -C "$SHORIN_ROOT" status --short)" ]]; then
        echo "Error: vendor repo is dirty: $SHORIN_ROOT" >&2
        echo "Clean or stash it before importing upstream changes." >&2
        exit 1
    fi
}

ensure_vendor_repo() {
    if [[ -d "$SHORIN_ROOT/.git" ]]; then
        return 0
    fi

    mkdir -p "$(dirname "$SHORIN_ROOT")"
    git clone --filter=blob:none --sparse "$SHORIN_REMOTE" "$SHORIN_ROOT"
}

ensure_vendor_branch() {
    if git -C "$SHORIN_ROOT" show-ref --verify --quiet "refs/heads/$SHORIN_BRANCH"; then
        git -C "$SHORIN_ROOT" switch "$SHORIN_BRANCH" >/dev/null
        return 0
    fi

    git -C "$SHORIN_ROOT" switch -c "$SHORIN_BRANCH" --track "origin/$SHORIN_BRANCH" >/dev/null
}

prepare_sparse_checkout() {
    git -C "$SHORIN_ROOT" sparse-checkout set dotfiles wallpapers
}

update_vendor_repo() {
    git -C "$SHORIN_ROOT" fetch --prune origin
    ensure_vendor_branch
    git -C "$SHORIN_ROOT" pull --ff-only origin "$SHORIN_BRANCH"
}

main() {
    if [[ ! -x "$SYNC_SCRIPT" ]]; then
        echo "Error: missing sync script: $SYNC_SCRIPT" >&2
        exit 1
    fi

    ensure_vendor_repo
    prepare_sparse_checkout
    ensure_clean_vendor_repo

    if [[ "$SKIP_FETCH" != "1" ]]; then
        update_vendor_repo
        ensure_clean_vendor_repo
    else
        ensure_vendor_branch
    fi

    local dotfiles_root="$SHORIN_ROOT/dotfiles"
    if [[ ! -d "$dotfiles_root" ]]; then
        echo "Error: missing dotfiles directory: $dotfiles_root" >&2
        exit 1
    fi

    SOURCE_HOME="$dotfiles_root" DRY_RUN="$DRY_RUN" "$SYNC_SCRIPT"

    local upstream_sha
    upstream_sha="$(git -C "$SHORIN_ROOT" rev-parse --short HEAD)"

    echo
    echo "Imported SHORiN upstream into utopia."
    echo "Vendor repo: $SHORIN_ROOT"
    echo "Upstream commit: $upstream_sha"
    if [[ "$DRY_RUN" == "1" ]]; then
        echo "Dry run only; utopia was not modified."
    else
        echo "Review with: git -C $REPO_ROOT status --short"
        echo "Suggested commit: chore(upstream): import shorin guide $upstream_sha"
    fi
}

main "$@"
