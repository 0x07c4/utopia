# Utopia Profiles

Profiles and the artifact catalog are the first machine-readable description of
how Utopia composes a workstation. They are currently read-only planning inputs
and do not deploy files or change the running system.

Resolve either current host model with:

```sh
python -m utopia profile arch-laptop
python -m utopia profile cachyos-desktop --json
```

Compare the resolved artifact plan with a live home directory without changing
either side:

```sh
python -m utopia audit arch-laptop
python -m utopia audit cachyos-desktop --json
```

The audit reports matching, drifted, missing, and unsafe artifacts. It exits
with status 1 when drift is present and status 2 for an invalid plan or invalid
home root. `--home` may point at a temporary fixture or another mounted home for
inspection; the report does not include its absolute path and does not follow
symbolic links.

## Model

A profile selects an ordered list of layers:

```text
system + hardware + workstation + host + optional experiment
```

Each layer contains:

- a stable ID and kind;
- a human-readable description;
- JSON-compatible values;
- an explicit list of values it is allowed to override.

The resolver rejects unknown keys, missing layers, duplicate IDs, incompatible
value shapes, ambiguous overrides, stale override declarations, and overlapping
package intent. Its output includes provenance for every resolved leaf value.

The workstation and its domains are the center of this model. A host layer is a
small boundary for facts that genuinely differ, such as a display connector; it
does not define a separate copy of the workstation.

Later layers do not silently win. To replace an existing value, the layer must
name its exact dotted path:

```toml
[layer]
id = "host.example"
kind = "host"
description = "Example host override."
overrides = ["workstation.terminal"]
```

An override declaration that does not replace an earlier value is also an error.
This keeps old permissions from silently authorizing unrelated future changes.

## Package intent

Application configuration and package installation are separate decisions. A
resolved `packages` table must classify every listed package into exactly one of:

- `required`: part of the intended workstation;
- `optional`: useful but not implied by deployment;
- `disabled`: explicitly not wanted even if old configuration exists.

The current workstation marks WezTerm disabled and Kitty required.

## Home artifacts

`profiles/artifacts.toml` maps reviewed repository content to paths relative to
`$HOME`. Each entry declares its owning layer and domain, source, destination,
kind, management state, capture/deploy intent, and symbolic validators. The
resolver validates the entire catalog before selecting entries for a profile.

An artifact may declare `generated_blocks` for a text file whose stable body is
managed by Utopia while a runtime integration owns a uniquely marked section.
The audit still detects edits outside the markers or missing/duplicated markers,
but ignores the generated contents between them. Starship uses this boundary so
Noctalia can refresh its palette without turning every wallpaper change into
configuration drift. Tree `excludes` similarly omit separate generated theme
files such as Kitty's `themes/noctalia.conf` and Niri's `noctalia.kdl`.

The initial catalog is intentionally descriptive. `capture = true` and
`deploy = true` state future intent; there is no command that performs either
operation yet. `python -m utopia profile ...` prints the resulting plan, while
`python -m utopia audit ...` only reads the mapped live paths and reports drift.

Git author identity is deliberately absent from the artifact catalog. A future
Git mapping should deploy only shared behavior through an include file, leaving
the name, email address, signing key, and other identity data in an untracked
host-local configuration.

Current domain-owned sources preserve home-relative deployment destinations:

```text
shell/zsh/zshrc                                    shared Zsh behavior
shell/zsh/zimrc                                    shared Zim modules
shell/starship/starship.toml                       shared prompt configuration
terminal/kitty/                                    shared terminal configuration
input/fcitx5/config/                               shared Fcitx5 configuration
input/fcitx5/environment.d/fcitx5.conf             input-method environment
input/rime/                                        reviewed Rime customizations
editor/nvim                                        pinned Neovim gitlink
development/ssh/config                             shared SSH client policy
desktop/niri/                                      shared desktop behavior
hosts/arch-laptop/desktop/niri/display.kdl        laptop output only
hosts/cachyos-desktop/desktop/niri/display.kdl    desktop output only
```

The shared Niri tree excludes `cfg/display.kdl` during capture so a host cannot
silently promote its connector into shared policy. Both rendered combinations
must pass `niri validate`.

Artifact validation rejects missing or escaping sources, symlinks, Git metadata
inside copied trees, sensitive destinations, duplicate IDs, unsafe modes, and
destination collisions without an exact `replaces` declaration. Tree mappings
are overlays: disjoint files may share a destination directory, while conflicting
files remain errors.

## Current safety boundary

Both initial system layers mark boot, filesystems, kernel, services, and storage
as `unmanaged`. This profile prototype must not be interpreted as permission to
modify those areas. Existing installer behavior remains separate until it can
consume the same resolved, tested plan.

Those fields remain within Utopia's intended system model. Here, `unmanaged`
describes current implementation maturity rather than permanent project scope.
Future versions may model architecture, firmware, boot policy, kernel fallback,
storage topology, snapshots, and recovery, but each area must earn management
through dry-run planning, validation, and tested rollback.

The JSON equivalents of the TOML contracts are documented under `schemas/`.
The standard-library resolver also validates the same structural constraints at
runtime, so profile inspection does not require third-party Python packages.
