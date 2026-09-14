# utopia

This repository versions the active desktop and shell configuration for the Arch Linux workstation.

## Current stack

- niri with the single active `.config/niri/config.kdl`
- Noctalia v5 for wallpaper, theme, bar, lock screen, idle, launcher, and notifications
- Zsh with Zim and Starship
- AstroNvim in the `.config/nvim` submodule
- Fcitx5 with Rime

## Syncing the live home

Run the sync script from the repository root:

```sh
./scripts/sync-current-dotfiles.sh
```

The script copies selected files from `$HOME`, updates the AstroNvim gitlink when its commit changes, and leaves the final review and commit to Git. Use `DRY_RUN=1` to preview changes.

## Deliberately excluded

Runtime state, caches, credentials, generated launchers, emulator data, wallpaper binaries, and Noctalia's GUI state are not versioned. Noctalia's declarative files live under `.config/noctalia/`; runtime overrides remain in `~/.local/state/noctalia/`.
