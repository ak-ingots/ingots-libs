# 0013. Name the RPCs after their operations

- Status: Proposed
- Domains: grpc
- Date: 2026-11-09
- Deciders: Aliaksandr Karotki
- Supersedes / Superseded by: supersedes in 0009 the names of the RPCs, its
  requests and responses keeping theirs; the rest of 0009 and 0011 stands

> In the context of **the gRPC contracts of the addons**, facing **RPCs named by a
> bare verb, `Tags.Create`, whose messages, `CreateTagRequest`, are named apart from
> them**, we decided for **an RPC named after its operation, a verb then its subject,
> as Google AIP names methods, the messages after the RPC**, and against **bare
> verbs, and messages named by the bare verb**, to achieve **names a reader of a
> client and a linter of protobuf both take as they are**, accepting **a rename of
> the RPCs of the contracts already there, breaking their clients**.

## Context

[ADR 0009](0009-name-grpc-contracts-apart-from-the-layout.md) gives every RPC a
request and a response of its own, `<Rpc><Subject>Request` and
`<Rpc><Subject>Response`, and the RPC the verb alone: `rpc Create(CreateTagRequest)`
in the service `Tags`. The name of a message is not that of its RPC, which neither
the API design guide of Google ([AIP-131](https://google.aip.dev/131) and the
following) nor the linters of protobuf expect: AIP names a method by its verb and
its subject, `ListBooks(ListBooksRequest)`; the rules `RPC_REQUEST_STANDARD_NAME` and
`RPC_RESPONSE_STANDARD_NAME` of [Buf](https://buf.build/docs/lint/rules/), its set
`STANDARD`, ask for `<Rpc>Request` or `<Service><Rpc>Request`. A client reads
`tags.Create(...)`, where the subject is of the variable, not of the call.

ingot-auth alone has contracts so far, pre-alpha: seven services, none consumed
outside the ecosystem. A rename costs one pull request now, more with every addon.

AIP is more than its names: resources named by paths, standard methods with
`parent`, `page_token`, `update_mask`, checked by its own `api-linter`. The
operations of an addon are what they are, `Rename`, `Bind`, `AddMember`, not the
standard methods of a resource. Buf `STANDARD` checks names and layout only, from
the style guides of Google and Uber, and is the linter of protobuf most in use;
0011 already follows it in mirroring the packages in the paths.

## Decision drivers

- The name of a call says what it does, without the variable it is called on.
- The names are those of a known guide, not of our own.
- A linter may check them later without a rename: Buf `STANDARD` passes.
- The design of the operations stays free of a resource model they do not have.

## Considered options

1. As 0009: the RPC the verb, `Create`, the messages `<Rpc><Subject>Request`.
2. The RPC the verb and its subject, `CreateTag`, the messages named after it,
   `CreateTagRequest`: the names of AIP.
3. The RPC the verb, the messages named after it, `CreateRequest`: Buf passes, but
   the messages lose their subject, and an SDK holds a hundred `ListRequest`.

## Decision

Option 2, for every addon shipping a contract.

1. An RPC is named after its operation, a verb then its subject, the subject singular
   for one item and plural for a list, as AIP names methods: `CreateTag`, `ListTags`,
   `RenameTag`, `BindAttr`, `ListBindings`, `GetMetadata`, `AddMember`,
   `ListMemberGroups`. The service stays named after its subdomain, with no
   `Service` suffix (0009, 0011).
2. Its request and its response are named after it, `<Rpc>Request` and
   `<Rpc>Response`, each its own, empty ones too, as in 0009. An RPC being its verb
   and its subject, the messages named by 0009 keep their names.
3. The names are kept those Buf `STANDARD` passes, but for `SERVICE_SUFFIX`, which
   the services leave out by 0009: a contract does not need a rename the day an
   addon runs `buf lint`.
4. Of AIP, the names alone are taken: not its resource names, its standard methods
   and their fields, nor its `api-linter`.
5. A contract renamed by this breaks its clients: the addon says so in a news
   fragment of its own, and renames all of its RPCs in one release.
6. An addon shipping a contract lints it: `buf.yaml` names its root and
   `STANDARD` but for `SERVICE_SUFFIX`, `make proto-lint` runs `$(BUF) lint`
   in `make lint`, `BUF ?= buf`. The version of Buf is the ecosystem's, one
   for every addon: the action `setup-buf` of this repository puts it on the
   PATH in CI, `make buf` here into `.cache/`, which `make check` passes on.

## Consequences

### Positive

- A call reads as the operation: `members.AddMember(...)`.
- A request is found by the name of its RPC, in the code and in an SDK.
- The contracts pass the naming rules of Buf `STANDARD` before any addon runs it.

### Negative

- The name of an RPC repeats the subject its service often says:
  `Tags.CreateTag`.
- The RPCs of ingot-auth are renamed, the methods of its servicers and the calls of
  its clients with them.
- A developer of an addon alone, without this repository, installs Buf on
  their own, of the version pinned here.

## Links

- [ADR 0009](0009-name-grpc-contracts-apart-from-the-layout.md): the names of the
  messages kept, those of the RPCs superseded.
- [ADR 0011](0011-mirror-the-packages-of-grpc-contracts.md): the packages and the
  services, unchanged.
- [AIP-131](https://google.aip.dev/131) and the following: the names of the methods.
- [Buf lint rules](https://buf.build/docs/lint/rules/): `STANDARD`.
