# utopia

This repository describes and versions the Utopia Linux workstation.

Utopia is expanding from a dotfiles snapshot into an open-source Linux
workstation product whose desktop, rebuild process, and system engineering are
readable by both people and agents. It is developed against real daily-use
systems while keeping personal machine data outside the product model.
The durable direction is recorded in [`docs/vision.md`](docs/vision.md), while
the CachyOS desktop migration and architecture discussion are preserved in the
[`2026-09-20 journal`](docs/journal/2026-09-20-cachyos-desktop-and-utopia-direction.md).
Agents should begin with [`AGENTS.md`](AGENTS.md).
Cross-machine and cross-session work should continue from the rolling
[`current handoff`](docs/handoff.md).
Public-repository privacy boundaries are defined in
[`docs/privacy.md`](docs/privacy.md).

The first [machine-readable workstation plan](profiles/README.md) can be
inspected without changing the system:

```sh
python -m utopia profile arch-laptop
python -m utopia profile cachyos-desktop --json
```

The output now includes shared, domain-owned home artifacts and thin host
overlays, with source provenance and safety checks. It remains a read-only plan:
capture, deployment, and installer integration are not implemented.

## Current stack

- modular niri configuration with shared behavior and host-specific output data
- Noctalia v5 for wallpaper, theme, bar, lock screen, idle, launcher, and notifications
- Zsh with Zim and Starship
- AstroNvim in the `.config/nvim` submodule
- Fcitx5 with Rime

## Configuration capture

The capture command is not implemented yet. Until it is, inspect
`python -m utopia profile <id>` and copy only explicitly reviewed artifacts,
leaving the final diff and commit to Git.

## Target packages

The package manifests under `packages/` belong to the laptop-oriented installer
prototype and are split by source:

- `arch.txt`: base system, desktop, and development packages from the official Arch repositories
- `hardware-intel-laptop.txt`: hardware support for this Intel laptop
- `features/disk-encryption.txt`: packages installed only when LUKS disk encryption is selected
- `archlinuxcn.txt`: packages from the configured archlinuxcn repository
- `aur.txt`: packages built through an AUR helper

These are curated target manifests rather than raw `pacman -Qqe` output. The general-purpose additions are selected from Omarchy's package manifest when they have a concrete role in this system. Legacy overlapping desktop components such as Alacritty, Fuzzel, Mako, and Waybar are intentionally omitted.

Btrfs is the base storage layout. LUKS disk encryption is an installer option rather than a requirement; selecting it adds the feature manifest and the matching `sd-encrypt` boot configuration.

The non-secret installer input model lives at `install/config.example.toml`. Its target disk is intentionally blank and must be selected explicitly by the installer CLI or a future UI.

The staged pipeline can be previewed with:

```sh
python -m install --device /dev/nvme0n1
```

It remains an Arch laptop WIP and does not consume the new profiles or artifact
catalog; it must not be used as a CachyOS restore path. Detailed stage behavior
and its explicit apply controls are documented in
[`install/README.md`](install/README.md).

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
state-directory ownership pass validation. The curated AUR packages can be
included by the complete installer with `--with-aur`; otherwise they remain
available as a separate later stage.

## Deliberately excluded

Runtime state, caches, credentials, generated launchers, emulator data, wallpaper binaries, and Noctalia's GUI state are not versioned. Noctalia's declarative files live under `.config/noctalia/`; runtime overrides remain in `~/.local/state/noctalia/`.
