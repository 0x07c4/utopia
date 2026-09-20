# Public repository privacy boundary

Utopia is designed as a public open-source product. Public files and Git history
must contain only the information needed to understand, build, validate, and use
the product.

## Keep out of Git

- personal names, private email addresses, phone numbers, and physical addresses;
- local usernames, absolute personal home paths, and private account identifiers;
- credentials, tokens, private keys, keyrings, and authentication output;
- public IP addresses, private network topology, device serial numbers, disk
  UUIDs, filesystem keys, and recovery material;
- timestamped backup locations, command history, recently used files, caches,
  generated databases, and application runtime state;
- exact hardware details when a reusable capability description is sufficient.

Use neutral example values such as `utopia`, all-zero test UUIDs, role-based host
IDs, paths relative to `$HOME`, XDG directories, and placeholders such as
`<timestamp>`. Secrets and personal identity belong in ignored local files or an
external secret manager.

## Information that may be public

An intentionally published maintainer name, project namespace, and project
contact address may appear in Git metadata or project documentation. Treat that
as public project identity rather than machine configuration. Prefer a dedicated
contact address when practical, and do not copy it into deployed dotfiles.

Configuration may contain a technical host fact when it is required to produce
correct behavior and has no reusable substitute. Examples include a display
connector in a narrow host overlay or an instruction-set capability used to
select binaries. Record the minimum fact, explain why it is needed, and avoid
combining it with identity or unique device identifiers.

Repository remotes and dependency locations may identify the public project
namespace. Canonical dependency URLs are allowed when they improve reliable
cloning and provenance. Do not treat a public project namespace as private
identity, and do not repeat it where it has no technical purpose.

## Before publishing

Review the complete diff and scan the resulting tree for email addresses,
absolute home paths, account names, IP addresses, UUIDs, serial numbers, and
unexpected machine details. Review commit author metadata as well as file
content. Use a GitHub-provided `noreply` address for public commits.

If private data was already pushed, deleting it in a later commit is not enough:
it remains in reachable history. Prepare a sanitized replacement, rotate any
exposed secret, and rewrite the affected history only after reviewing the scope
and coordinating the force-push.
