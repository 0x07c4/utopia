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
