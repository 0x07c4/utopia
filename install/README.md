# Installer configuration

`config.example.toml` is the non-secret input model for the future installer UI and unattended mode. Paths in the file are relative to the repository root.

The example reproduces the current machine's stable choices: Limine, the `linux` kernel, a 2 GiB EFI system partition, Btrfs subvolumes for `/`, `/home`, `/var/log`, and the pacman package cache, plus the system identity and Noctalia Greeter login path. The target disk is deliberately empty so no installer can use the example without an explicit disk selection.

Disk encryption is optional and defaults to off. Both storage modes keep the same Btrfs layout:

- Without encryption, the installer generates a root-filesystem kernel argument and uses the listed mkinitcpio hooks unchanged.
- With encryption, it installs `packages/features/disk-encryption.txt`, inserts `sd-encrypt` after `block`, and generates the matching `rd.luks.name=...=cryptroot` kernel argument.

Passwords, password hashes, recovery keys, and LUKS passphrases do not belong in this file or in Git. Interactive installs will request them separately. Unattended credentials will require a short-lived, root-only input mechanism before that mode is implemented.

The installer must validate the schema, require a non-empty whole-disk device, show the resolved partition plan, and obtain a final destructive confirmation before writing a partition table.

## Read-only plan

Validate the example and every referenced package manifest without selecting a disk:

```sh
python -m install.plan --schema-only
```

Preview the plan for a real whole-disk device. This only calls `lsblk` and does not require root:

```sh
python -m install.plan --device /dev/nvme0n1
```

Preview the encrypted branch without changing the TOML file:

```sh
python -m install.plan --device /dev/nvme0n1 --encryption on
```

Add `--json` to either mode for structured output intended for the future installer UI. A normal plan refuses an empty target disk, partitions, and mapped devices; `--schema-only` is the only mode that accepts the intentionally incomplete example.

## Staged boot configuration

Render both boot paths with deterministic placeholder UUIDs into new temporary directories:

```sh
python -m install.render --output /tmp/utopia-plain --placeholders
python -m install.render --output /tmp/utopia-luks --placeholders --encryption on
```

The renderer creates `etc/fstab`, an mkinitcpio `HOOKS` drop-in, the selected kernel preset, `boot/limine.conf`, hostname/locale/console files, the timezone symlink, and the greetd configuration that launches Noctalia Greeter. It refuses `/`, live `/etc` and `/boot` paths, as well as an output directory that already exists. Real installs must pass the filesystem UUIDs returned after formatting instead of using `--placeholders`.

The plan also lists the systemd units to enable after packages are installed. The staged renderer deliberately does not create enablement links: the execution phase will call `systemctl --root enable` so systemd applies each package's own `[Install]` rules. It also records Noctalia Greeter's packaged setup command; that upstream script prepares the greeter state directory and PAM session integration after package installation.

## Storage preparation

Preview the exact destructive operations without executing them:

```sh
python -m install.storage --device /dev/nvme0n1
python -m install.storage --device /dev/nvme0n1 --encryption on
```

The storage phase creates a GPT with a 2 GiB ESP and a remaining-space root partition, formats the optional LUKS2 container and Btrfs filesystem, creates the configured subvolumes, and mounts the result below `/mnt`. LUKS passphrases are read directly by `cryptsetup` from the terminal and are never handled by Utopia.

Execution is intentionally awkward to trigger. It must run as root from the Arch installation environment, the disk must have no mounted filesystems, `/mnt` must be empty and unmounted, and the confirmation value must exactly match the canonical disk reported by `lsblk`:

```sh
python -m install.storage \
  --device /dev/nvme0n1 \
  --apply \
  --confirm-wipe /dev/nvme0n1
```

The default remains unencrypted. Add `--encryption on` to both preview and apply commands when LUKS2 is wanted. After a successful run, the new target remains mounted for the package installation phase. If an operation fails, mounts created by this phase are removed and a mapper opened by this phase is closed.

## Official package bootstrap

Preview the official repository package transaction:

```sh
python -m install.bootstrap --target-root /mnt
python -m install.bootstrap --target-root /mnt --encryption on
```

This stage passes only `packages/arch.txt`, `packages/hardware-intel-laptop.txt`, and the conditional encryption manifest to `pacstrap -K`. It uses `install/pacman.official.conf`, which exposes only Arch's `core` and `extra` repositories, and preflights pacman's machine-readable resolution before writing the target. Arch Linux CN and AUR targets are displayed as deferred work and cannot enter this transaction.

After the storage stage has mounted every configured Btrfs subvolume and the ESP, run:

```sh
python -m install.bootstrap --target-root /mnt --apply
```

The apply preflight requires root, `pacstrap`, writable Btrfs mounts with the expected subvolume names and options, and a writable vfat ESP at `/mnt/boot`. The `--encryption` choice must match whether `/mnt` comes from `/dev/mapper/cryptroot`. A failed `pacstrap` leaves the mounted target available for inspection and a safe retry.

## Target system configuration

Preview configuration with deterministic identifiers without requiring a mounted target:

```sh
python -m install.configure --target-root /mnt --placeholders
python -m install.configure --target-root /mnt --placeholders --encryption on
```

On a bootstrapped and mounted target, omit `--placeholders` to discover the real Btrfs, ESP, and optional outer LUKS UUIDs. Apply writes the reviewed configuration atomically, installs the package-provided Limine EFI executable at the standard fallback path, generates locale and initramfs data, creates or reconciles the user, checks sudoers, and enables the services whose packages are already present:

```sh
python -m install.configure --target-root /mnt
python -m install.configure --target-root /mnt --apply
```

Use `--encryption on` for both commands when the mounted target uses LUKS2. The user password is requested by `passwd` running inside the target chroot; Utopia does not read, pass, log, or persist it. The root password is locked only after the user password succeeds. `greetd.service` remains disabled until the later Arch Linux CN stage installs and configures Noctalia Greeter.
