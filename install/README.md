# Installer configuration

`config.example.toml` is the non-secret input model for the future installer UI and unattended mode. Paths in the file are relative to the repository root.

The example reproduces the current machine's stable choices: Limine, the `linux` kernel, a 2 GiB EFI system partition, and Btrfs subvolumes for `/`, `/home`, `/var/log`, and the pacman package cache. The target disk is deliberately empty so no installer can use the example without an explicit disk selection.

Disk encryption is optional and defaults to off. Both storage modes keep the same Btrfs layout:

- Without encryption, the installer generates a root-filesystem kernel argument and uses the listed mkinitcpio hooks unchanged.
- With encryption, it installs `packages/features/disk-encryption.txt`, inserts `sd-encrypt` after `block`, and generates the matching `rd.luks.name=...=cryptroot` kernel argument.

Passwords, password hashes, recovery keys, and LUKS passphrases do not belong in this file or in Git. Interactive installs will request them separately. Unattended credentials will require a short-lived, root-only input mechanism before that mode is implemented.

The installer must validate the schema, require a non-empty whole-disk device, show the resolved partition plan, and obtain a final destructive confirmation before writing a partition table.
