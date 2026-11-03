# ingot-auth: the first prototypes

Status: drafts, written on 2026-10-27 before the addon was built; kept as a
snapshot, not maintained. Older than [ADR 0012](../../adr/0012-design-a-feature-before-building-it.md):
no stories, only the code.

- [facade](facade/): the logic of auth from sign-up to the authenticated
  request over a facade of the storage, with its contract tests and a memory
  backend. It hardcodes a password hashed by scrypt, against the goal of a
  core that assumes no method: the addon keeps its methods pluggable.
- [profile](profile/): the schema of the profile joined from addons and an
  application, `AuthAttributes` made dataclasses and mapped one to one onto
  the flat values a storage keeps.
