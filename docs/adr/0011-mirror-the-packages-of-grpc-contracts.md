# 0011. Mirror the packages of the gRPC contracts in their paths

- Status: Proposed
- Domains: grpc, tooling
- Date: 2026-11-02
- Deciders: Aliaksandr Karotki
- Supersedes / Superseded by: supersedes in 0009 the names of the files and the
  services, their place under the contrib, the domains of the permissions and the
  rewrite of the imports, the rest of it stands

> In the context of **addons whose subdomains nest, the attributes of the profiles
> and of the sessions**, facing **names of 0009 that collide once two subdomains have
> a part of the same name**, we decided for **the path of a file mirroring its proto
> package, the file and its generated code in the package of the addon, at that
> path**, and against **flat files named with prefixes, and a contract under the
> contrib with its imports rewritten**, to achieve **names saying where a service
> belongs, imported as `protoc` writes them, in the shape linters of protobuf
> expect**, accepting **a deeper tree, and modules in the tree of the core that need
> the extra of the transport**.

## Context

[ADR 0009](0009-name-grpc-contracts-apart-from-the-layout.md) names a file
`ingot_<name>/v<N>/<service>.proto` and its package `ingot_<name>.<service>.v<N>`,
a service standing for a subdomain of the addon. ingot-auth has grouped its
registries by what they describe: the tags and the attributes under `profile`, the
attributes of the sessions under `session`. Two services are now `Attrs`, so their
files and their packages would be one. 0009 gives its domains of the permissions by
example only, `auth.tags`.

The Python code `protoc` generates imports by the proto package,
`from ingot_auth.sign_in.v1 import sign_in_pb2`: it takes the root given to `-I` for
a root of the imports, and has no option of a prefix, as Go has `go_package`. 0009
puts the contract under `proto/` of the contrib, so the generated code lies
elsewhere than its imports say, and rewrites them to `from . import`.

That rewrite covers the neighbours alone. A first version of this record kept the
contract under the contrib and the rewrite at any depth; then the contract of a
method had to hold the result of a flow, a message of another subdomain
(ingot-auth, 2026-11-09): its import, made relative, points to the wrong package,
left absolute, to `ingot_auth.sign_in.v1`, a package no wheel had. A second rewrite
would fix it, and the next case a third: the layout is wrong, not the rewrite (the
user: "пора остановиться и прошлую идею признать неудачной").

## Decision drivers

- A name tells where a service belongs, without a prefix repeating it.
- The proto package, its path, the domain of the permissions and the path in the code
  say the same thing.
- What linters of protobuf expect, a path mirroring the package, holds where it
  costs nothing.
- The generated code is imported as `protoc` writes it: no rewrite, an import
  between subdomains as any other.

## Considered options

1. The files flat in a version, named by the path joined with `_`,
   `ingot_auth/v1/profile_tags.proto`, the package `ingot_auth.profile.tags.v1`: the
   rewrite of 0009 as it is, a name repeating the path its package says.
2. The path of a file mirroring its package,
   `ingot_auth/profile/tags/v1/tags.proto` for `ingot_auth.profile.tags.v1`.
3. Flat names everywhere, `ingot_auth.profile_tags.v1` and the service `ProfileTags`:
   the hierarchy is lost, and every name repeats the prefix.

Where the files of option 2 lie:

- Under `proto/` of the contrib, as 0009 has it, the imports rewritten to
  `from . import`: the first version of this record. The rewrite takes the
  neighbours alone; an import between subdomains needs another (Context).
- In the package of the addon, at the path of their proto package: no rewrite.
- Under the contrib, the wheel mapping them to that path at its build: the tree
  and the wheel would differ, against 0003, and `uv_build` maps nothing.

## Decision

Option 2, its files in the package of the addon, for every addon shipping a
contract.

1. A service of the subdomain at the path `<path>` is in the package
   `ingot_<name>.<path>.v<N>`, the path joined with `.`, and in the file
   `ingot_<name>/<path>/v<N>/<service>.proto`, the path joined with `/`:
   `ingot_auth/profile/tags/v1/tags.proto`, `ingot_auth/metadata/v1/metadata.proto`.
   The file lies at that path in the package of the addon, next to the subdomain it
   serves: the root given to `protoc` is the root of the repository (`-I .`), and
   its generated code lies next to it, where its imports point. The module
   `ingot_auth.profiles.tags.v1` is the contract, by the name a client of an SDK
   imports too.
2. A service is named after the last part of the path, with no `Service` suffix:
   `Tags` in `ingot_auth.profile.tags.v1`. The messages and the enums leave out what
   the package already says: `Attr` and `AttrSource` in `ingot_auth.session.attrs.v1`,
   not `SessionAttr`.
3. A set of operations has its flags in the domain named by the path joined with `.`:
   `auth.profile.tags`.
4. A contrib follows the subdomains of the core: the servicers and the bindings of the
   profiles in `contrib/transports/grpcio/profile/`, as a storage keeps its own in
   `contrib/storages/<backend>/profile/`. The contract is not of the contrib: the
   servicers import it from the tree of the core.
5. `make proto` runs `protoc` over every `.proto` of the package, `-I .`, its
   output into `.`, and nothing after it. The core imports no module of a
   contract: they need protobuf, of the extra of the transport, as the contrib
   does. The tools of the package, the formatter, the linters, the coverage and
   the docs, leave the generated files out by their names, `*_pb2*.py*`.

## Consequences

### Positive

- Two subdomains may have parts of the same name: `Attrs` of the profiles and of the
  sessions.
- The package, its path, the domain of the permissions and the path in the code read
  alike.
- The path mirrors the package, as buf asks: one negative of 0009 is gone.
- No rewrite: the generated code imports as `protoc` writes it, a message of
  another subdomain as one of its own; the module of a contract has the name of
  the contract.
- Each service has a version of its own in its path.

### Negative

- A deeper tree, with an `__init__.py` in every directory of a contract.
- A deeper SDK: its paths are the names.
- The tree of the core holds modules that need the extra of the transport: one
  importing `ingot_auth.sign_in.v1` without it fails, as one importing the contrib
  does.

## Links

- [ADR 0009](0009-name-grpc-contracts-apart-from-the-layout.md): the naming this
  supersedes in part, and why the names are apart from the layout.
