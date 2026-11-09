# 0009. Name the gRPC contracts of addons apart from their layout

- Status: Accepted
- Domains: grpc, tooling
- Date: 2026-11-01
- Deciders: Aliaksandr Karotki
- Supersedes / Superseded by: its names of the files and the services, the domains of
  the permissions and the rewrite of the imports by
  [0011](0011-mirror-the-packages-of-grpc-contracts.md); the names of the RPCs by
  [0013](0013-name-rpcs-after-their-operations.md)

> In the context of **addons shipping a gRPC contract in a contrib of
> ingot-grpcio**, facing **file names that are global in a process and that every
> consumer's SDK mirrors**, we decided for **short names of the addon's own, with
> the imports of the generated code made relative** and against **names following
> the layout of the package**, to achieve **a contract independent of where the
> addon holds it**, accepting **one patched line of generated code per file**.

## Context

This concerns the addons shipping a `.proto` contract, not the other dependents
of ingot-grpcio. An application needs none of it: it publishes no library, and
the name of a file by its path serves it well, as the README of ingot-grpcio
shows.

The name of a `.proto` file does three things. Protobuf keeps it in a registry
global to the process, so two addons with a `metadata.proto` of different content
fail on import. `grpc export` puts it into the binary consumers generate an SDK
from, and the SDK lands under that path. And `protoc` derives the Python import
from it, `_pb2_grpc.py` importing its own `_pb2.py` that way, so the name has to be
importable.

A contract belongs in the contrib of the transport, as the core assumes no
transport. A name that is its path there,
`ingot_auth/contrib/transports/grpcio/proto/metadata.proto`, is importable as
generated, but brings the layout of the addon into every SDK. A short name is not
importable inside the addon. The name is not on the wire, which carries only the
package and the service, so a rename moves the SDKs without breaking a client.

## Decision drivers

- A consumer holds the exported binary, not the addon: what it sees should not
  depend on the inside of the addon.
- Names of different addons never collide in one process.
- Exports of different servers of an addon give identical files, so they merge.
- A server shows a consumer only what it serves to that consumer.
- The generated code stays as `protoc` writes it, as far as possible.

## Considered options

1. Names by the path in the package: nothing to patch, the layout in every SDK.
2. Short names, with the imports of the generated code rewritten after `protoc`.
3. A plugin of `protoc` writing the imports: a tool to maintain for one line.
4. The contract in the root of the package: importable under a short name, but it
   puts a transport into the core.
5. Each addon chooses: consumers of several addons meet several shapes, and every
   author decides this again.

## Decision

Option 2, for every addon shipping a contract.

1. A file is named `ingot_<name>/v<N>/<service>.proto`: the prefix of the addon
   keeps it apart from other addons. It lies under `proto/` of the contrib, which is
   the root given to `protoc` (`-I proto`).
2. A file holds one service and its messages, in a proto package of its own,
   `ingot_<name>.<service>.v<N>`: the constants of an enum are scoped by the proto
   package, so two files can use the same names. A file with no services, for
   messages two services share, has a package of its own too.
3. A service stands for a set of operations, the subdomain of the addon it follows,
   most often an entity. A public view of entities is a service of its own, with its
   own copies of the messages and no import of theirs, as an import brings all the
   messages of a file into the export.
4. Permissions are on operations: a flag tells that a caller may run an operation,
   nothing else. A set of operations has its flags in a domain of its own, `auth.tags`
   and so on. Flags repeating the CRUD of an entity are a useful coincidence, neither
   a rule nor a kind of permission of their own. A service declares the flags of its
   operations next to it, in an enum `Permission` with the same names and bits,
   `PERMISSION_CAN_READ` for `CAN_READ`, and `PERMISSION_UNSPECIFIED = 0`. The export
   carries the enum, so a client knows the permissions without another call, to build
   its interface; the server checks them anyway. The flags in Python stay the source,
   and a test of the addon compares the enum with them. A public view requires a
   permission too, one its servicer gives anyone until a subclass says otherwise.
5. Every RPC has a request and a response of its own, `<Rpc><Subject>Request` and
   `<Rpc><Subject>Response`, empty ones too: a field can be added to one later without
   touching the others. A service is named after its subdomain, with no `Service`
   suffix.
6. `make proto` runs a plain `protoc`, then rewrites `from ingot_<name>.v<N> import`
   to `from . import` in the generated `.py` and `.pyi` files. An addon forgetting it
   fails on import, in `make wheel-test` at the latest.
7. Only the wheel of the addon carries the rewrite. An SDK generated from the export
   needs none, its paths being the names.

## Consequences

### Positive

- The contrib can move without touching a consumer.
- A public server exports nothing of the services it does not serve, not even
  their messages.
- Two services can evolve apart, each in its own package and version.
- A contract reads like the addon: a file per subdomain.
- A client gets the permissions in the SDK, typed.

### Negative

- Every addon with a contract carries the rewrite in its `Makefile`.
- A message of two services without a shared file exists twice, with its conversion.
- A service serves its operations whole: one public operation needs a public view.
- The enum `Permission` copies the flags, and a client learns a new one only from a
  new SDK. A mask stays a plain `uint32` by the name of its domain.
- The export does not say which RPC requires what: comments do not reach it.
- The values of the enum `Permission` are bits, so they are not dense, as the style
  guide of protobuf asks: a third permission has the value 4.
- The path does not mirror the proto package, which linters such as buf expect.
- The rewrite covers one directory: an import between versions needs more.
- A directory `ingot_<name>/` of an SDK shadows the installed addon of that name in
  one environment. Who installs the addon takes the stubs from it.

### Open questions

- With a second addon holding a contract, the rewrite may move to a command of
  ingot-grpcio.
- Whether `GrpcService` with a servicer should refuse a file of several services.
- Generating the services and the enums from the operations and the flags in Python.
- Permissions on an instance: the flags gate an operation as a whole and an enum
  names them, so they cannot tell a client what it may do with one item.

## Links

- [ADR 0003](0003-flat-layout-and-mandatory-library-build.md): the wheel test
  catching a missed rewrite.
- [ADR 0004](0004-static-composition-with-typed-slots.md): the composition the
  bindings of a contrib follow.
