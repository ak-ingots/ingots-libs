# 0011. Mirror the packages of the gRPC contracts in their paths

- Status: Proposed
- Domains: grpc, tooling
- Date: 2026-11-02
- Deciders: Aliaksandr Karotki
- Supersedes / Superseded by: supersedes in 0009 the names of the files and the
  services, the domains of the permissions and the rewrite of the imports, the rest
  of it stands

> In the context of **addons whose subdomains nest, the attributes of the profiles
> and of the sessions**, facing **names of 0009 that collide once two subdomains have
> a part of the same name**, we decided for **the path of a file mirroring its proto
> package, the subdomains of a contrib following those of the core**, and against
> **flat files named with prefixes**, to achieve **names saying where a service
> belongs, in the shape linters of protobuf expect**, accepting **a deeper tree and a
> wider rewrite of the imports**.

## Context

[ADR 0009](0009-name-grpc-contracts-apart-from-the-layout.md) names a file
`ingot_<name>/v<N>/<service>.proto` and its package `ingot_<name>.<service>.v<N>`,
a service standing for a subdomain of the addon. ingot-auth has grouped its
registries by what they describe: the tags and the attributes under `profile`, the
attributes of the sessions under `session`. Two services are now `Attrs`, so their
files and their packages would be one. 0009 gives its domains of the permissions by
example only, `auth.tags`.

The rewrite of 0009 makes `from ingot_<name>.v<N> import` relative in one directory.
The code `protoc` generates for a file imports only its own `_pb2`, which lies next
to it, so one pattern makes the imports relative at any depth.

## Decision drivers

- A name tells where a service belongs, without a prefix repeating it.
- The proto package, its path, the domain of the permissions and the path in the code
  say the same thing.
- What linters of protobuf expect, a path mirroring the package, holds where it
  costs nothing.
- `make proto` stays one call of `protoc` and one rewrite.

## Considered options

1. The files flat in a version, named by the path joined with `_`,
   `ingot_auth/v1/profile_tags.proto`, the package `ingot_auth.profile.tags.v1`: the
   rewrite of 0009 as it is, a name repeating the path its package says.
2. The path of a file mirroring its package,
   `ingot_auth/profile/tags/v1/tags.proto` for `ingot_auth.profile.tags.v1`.
3. Flat names everywhere, `ingot_auth.profile_tags.v1` and the service `ProfileTags`:
   the hierarchy is lost, and every name repeats the prefix.

## Decision

Option 2, for every addon shipping a contract.

1. A service of the subdomain at the path `<path>` is in the package
   `ingot_<name>.<path>.v<N>`, the path joined with `.`, and in the file
   `ingot_<name>/<path>/v<N>/<service>.proto`, the path joined with `/`:
   `ingot_auth/profile/tags/v1/tags.proto`, `ingot_auth/metadata/v1/metadata.proto`.
   The file lies under the root of the contract, `proto/` of the contrib, given to
   `protoc` (`-I proto`).
2. A service is named after the last part of the path, with no `Service` suffix:
   `Tags` in `ingot_auth.profile.tags.v1`. The messages and the enums leave out what
   the package already says: `Attr` and `AttrSource` in `ingot_auth.session.attrs.v1`,
   not `SessionAttr`.
3. A set of operations has its flags in the domain named by the path joined with `.`:
   `auth.profile.tags`.
4. A contrib follows the subdomains of the core: the servicers and the bindings of the
   profiles in `contrib/transports/grpcio/profile/`, as a storage keeps its own in
   `contrib/storages/<backend>/profile/`. The root of the contract stays one.
5. `make proto` runs `protoc` over every file under the root, then rewrites
   `from ingot_<name>.<path>.v<N> import` to `from . import` in the generated `.py` and
   `.pyi` files, whatever the depth.

## Consequences

### Positive

- Two subdomains may have parts of the same name: `Attrs` of the profiles and of the
  sessions.
- The package, its path, the domain of the permissions and the path in the code read
  alike.
- The path mirrors the package, as buf asks: one negative of 0009 is gone.
- Each service has a version of its own in its path.

### Negative

- A deeper tree, with an `__init__.py` in every directory of the contrib.
- A deeper SDK: its paths are the names.
- The rewrite assumes a generated file imports nothing but its neighbours: an import
  between subdomains needs more, as an import between versions does in 0009.

### Open questions

- An import between subdomains, should one need a message of another.

## Links

- [ADR 0009](0009-name-grpc-contracts-apart-from-the-layout.md): the naming this
  supersedes in part, and why the names are apart from the layout.
