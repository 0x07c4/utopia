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

## Target packages

The package manifests under `packages/` describe the intended rebuilt system and are split by source so a future bootstrap script can install them in the correct order:

- `arch.txt`: base system, desktop, and development packages from the official Arch repositories
- `hardware-intel-laptop.txt`: hardware support for this Intel laptop
- `features/disk-encryption.txt`: packages installed only when LUKS disk encryption is selected
- `archlinuxcn.txt`: packages from the configured archlinuxcn repository
- `aur.txt`: packages built through an AUR helper

These are curated target manifests rather than raw `pacman -Qqe` output. The general-purpose additions are selected from Omarchy's package manifest when they have a concrete role in this system. Legacy overlapping desktop components such as Alacritty, Fuzzel, Mako, and Waybar are intentionally omitted.

Btrfs is the base storage layout. LUKS disk encryption is an installer option rather than a requirement; selecting it adds the feature manifest and the matching `sd-encrypt` boot configuration.

The non-secret installer input model lives at `install/config.example.toml`. Its target disk is intentionally blank and must be selected explicitly by the installer CLI or a future UI.

The complete staged pipeline can be previewed with `python -m install --device /dev/nvme0n1` and applied only after review with `--apply --confirm-wipe /dev/nvme0n1`. Encryption remains optional; use `--encryption on` consistently for an encrypted target. Detailed stage behavior is documented in [`install/README.md`](install/README.md).

### Arch Linux CN and Noctalia Greeter stage

After the official package bootstrap and target configuration stages, preview the
Arch Linux CN transaction against the mounted target:

```sh
python -m install.archlinuxcn --target-root /mnt
```

Apply the reviewed plan as root from the Arch installation environment:

```sh
python -m install.archlinuxcn --target-root /mnt --apply
```

For an encrypted target, add `--encryption on` to both commands. The selection
must match the storage layout already mounted at `/mnt`.

This stage adds a managed `[archlinuxcn]` repository block without overriding
pacman's signature policy. It bootstraps `archlinuxcn-keyring`, verifies package
origins, performs a full system upgrade with the remaining repository packages,
runs Noctalia Greeter's upstream setup explicitly as the configured greeter user,
and enables greetd only after its PAM integration, executables, configuration, and
state-directory ownership pass validation. AUR packages remain a separate later
stage.

## Deliberately excluded

Runtime state, caches, credentials, generated launchers, emulator data, wallpaper binaries, and Noctalia's GUI state are not versioned. Noctalia's declarative files live under `.config/noctalia/`; runtime overrides remain in `~/.local/state/noctalia/`.
