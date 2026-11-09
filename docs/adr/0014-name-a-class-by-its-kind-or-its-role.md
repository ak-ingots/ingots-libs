# 0014. Name a class of ingots by its kind or its role

- Status: Proposed
- Domains: design
- Date: 2026-11-09
- Deciders: Aliaksandr Karotki
- Supersedes / Superseded by: — (adds to the naming of 0007)

> In the context of **code reviewed in pull requests, without an IDE to tell
> what a name stands for**, facing **units, operations and dataclasses named
> alike, `AuthProfile` the data and `AuthProfiles` the unit**, we decided for
> **a suffix of the kind of ingots, or of the role where a class has one, and
> no suffix for plain data**, and against **a suffix of the kind on every
> class, `*Entity` among them**, to achieve **names that say what a class is in
> the diff**, accepting **a rename across the ecosystem, and a judgment of
> what is a role**.

## Context

[ADR 0007](0007-code-layout-and-naming.md) names methods by their action and
marks an incomplete class by `Base`, but says nothing of what a class is. The
packages name it as it comes: of the twenty units of ingot-auth, eighteen are
a bare plural, `AuthProfiles`, `AuthTags`, `AuthMethods`, and two take `*Unit`
because a dataclass took the bare name first, `AuthMetadataUnit`,
`AuthSignUpUnit`. An operation is a bare verb, `AuthCreateTag`, read as a
function or a command. A dataclass, `AuthProfile`, `AuthGroupInfo`, looks as an
entity does, `AuthGroup`. In a pull request the user loses what the code works
with: a class of ingots, a plain class or a dataclass (2026-11-09).

## Decision drivers

- The name tells the kind of a class in a diff, without its definition.
- A name says what the class stands for (0007), not only how it is built.
- A class does not change its name when it gains a slot.

## Considered options

1. The suffix of the kind on every class of ingots, `*Entity` too:
   `AuthNicknameMethodUnit`, `AuthTagsStorageEntity`. The kind repeats what
   the role says, `*Entity` says nothing, nearly everything being one, and a
   name changes when an entity becomes a unit.
2. The suffix of the role where a class has one, of the kind where it has
   none, a dataclass bare.
3. The dataclasses marked instead, `*Data`, `*Record`: the data is the
   minority of the code a reviewer reads, and `AuthProfiles` the unit stays
   one letter from `AuthProfile`.
4. As it is, the IDE telling: not in a pull request.

## Decision

Option 2, in every package of the ecosystem.

1. **A project, a command, an operation** takes the suffix of its kind:
   `AuthProject`, `AuthListGroupsCommand`, `AuthCreateTagOperation`.
2. **A unit, a component** takes the suffix of its role where it has one,
   `AuthStorage`, `AuthCache`, `BaseAuthMethod`, `BaseGrpcClient`,
   `FileLoader`; one that only groups others takes the suffix of its kind,
   `*Unit`, `*Component`: `AuthProfilesUnit`, `SettingsUnit`,
   `GrpcClientsUnit`. A role holds when the class gains a slot (the user,
   2026-11-09).
3. **Another entity** takes the suffix of its role, never `*Entity`:
   `AuthLengthPolicy`, `AuthGroupsGrants`, `PermissionsChecker`,
   `OperationsRunner` (the user: `*Entity` says nothing).
4. **A dataclass, an enum, a plain class** takes no suffix of ingots: a bare
   noun, `AuthProfile`, `AuthMembership`, or the suffix of its own role,
   `*Parameters`, `*Error`, `*Permissions`. No suffix of a kind means plain
   data.
5. The names of the slots stay: `op_create`, `settings`, `storage`. A class
   renamed by this keeps its prefix (`Auth`, `Grpc`) and its `Base` (0007).
6. The rename comes once, with ingots 0.33, each addon in its move (0008).

## Consequences

### Positive

- `AuthProfile` the data, `AuthProfilesUnit` the unit, `AuthCreateTagOperation`
  the operation: the kind is in the name.
- A unit that gains a slot, a method for its presets, keeps its name.

### Negative

- Every package renames: ingots its units (`Settings`, `Logging`,
  `Components`, `Operations`), each addon its units that group and all its
  operations; the applications follow.
- Longer names: `AuthListMemberGroupsOperation`.
- What is a role is a judgment: a review decides, as it does a name.

## Links

- [ADR 0007](0007-code-layout-and-naming.md): the naming this adds to.
- [operations-permissions](../design/operations-permissions/README.md): the
  design of ingots 0.33, whose release the rename rides.
