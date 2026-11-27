# 0019. Compose by typed slots and the typed projects of the parts

- Status: Proposed
- Domains: design
- Date: 2026-11-26
- Deciders: Aliaksandr Karotki
- Supersedes / Superseded by: supersedes [0004](0004-static-composition-with-typed-slots.md),
  once accepted (its rule of the slot conflicts refined by
  [0018](0018-check-a-slot-by-its-kind.md))

> In the context of **composing an application from Ingots addons and the
> parts of an addon that need more of a project than its own**, facing
> **entities that reach that more by a `t.cast` at each use, a promise no
> one checks**, we decided for **the static composition of 0004, its types
> narrowed by annotations only, and a typed project shipped with each such
> part, which a starter or an application inherits**, and against **the
> cast at each use, a protocol of the needs of a part, and a project of a
> part that binds it**, to achieve **every entity typed down to what it
> uses with no cast, and a part whose needs a project does not meet refused
> by mypy and at the creation of its class**, accepting **a project class
> per part, and the joins of the settings in a starter or an application
> taking several**.

## Context

[0004](0004-static-composition-with-typed-slots.md) composes statically by
inheritance and typed slots, and narrows the back-reference of an entity by
an annotation, `project: "AppProject"`. An entity is typed as far as its
addon's project goes. A part that needs more, a method its configs mixed
into the project's, a contrib on another addon its project, the load its
configs, casts at each use; the application that forgets to mix the configs
in fails at run time, on the first call. The scaffolds, an addon, its parts,
a starter and two applications:
[docs/design/typed-projects](../design/typed-projects/README.md).

## Decision drivers

- The drivers of 0004 hold: types down to the deepest entity, errors at
  import or in mypy, no registration, no global state, little boilerplate.
- No cast where a class can carry the type.
- A part's needs stated once, by its author, not in the docs of every
  application.

## Considered options

1. The cast at each use, the needs of a part told by its docs.
2. A protocol of what a part needs, structural.
3. A typed project per part, typing only; a starter binds.
4. A typed project per part that binds the part too.

Option 1 checks nothing. Option 2 asks nothing of the application, and so
checks nothing of it either, and still leaves the joins to be written by
hand. Option 4 saves a class when one part is taken, but two parts binding
in one unit make the application join that unit too, down to the slot.

## Decision

The composition of 0004 stands: static, by inheritance, children in typed
slots, a subclass narrowing a slot, a join class where two bases extend one
default (as 0018 checks it), overrides cooperative. And option 3:

- A type is narrowed by an annotation in the class, never by `t.cast` at
  each use: an entity its `project` and its `parent`, a mixin too; the mixin
  of an owner of slots is a `SlotsOwner`, so that its children may narrow
  their `parent` to it. `t.cast` stays where no class carries the type: a
  value from a library or from outside, a function whose parameter cannot
  be narrowed.
- A part of an addon that needs more of a project than its addon's own, a
  method with configs, a contrib on another addon, ships the project it
  needs, in its own module: its addon's project, the others it uses, the
  settings and configs joined (`AuthNicknameProject`,
  `AuthMongoDbProject(AuthProject, MongoDbProject)`). Its entities annotate
  `project:` by it. The project types; it binds nothing.
- A starter is a project: it inherits the projects of the parts it takes,
  writes their joins, and binds the parts in their slots.
- An application inherits a starter, or the projects of the parts it takes,
  never the bare project of an addon whose parts it uses.

## Consequences

### Positive

- No cast to reach the project of a part: its configs and the other addon
  are typed for mypy and the IDE.
- A join of the settings forgotten fails in mypy and at the creation of the
  class; configs lost by settings declared again fail in mypy.
- The joins of a kind of application are written once, in its starter.

### Negative

- A project class per part, and its settings and configs joined in it.
- An application taking parts without a starter joins their settings, as it
  does today, now checked.
- The annotation is still a promise: a part bound in a project not of its
  kind is not seen until it is used.

### Open questions

- Checking the promise once, when a slot creates an entity: the project an
  instance of the class the entity annotates.
- A runner generic in its project, so that `runner.project` is typed.
- The open questions of 0004: the hooks between siblings of different
  addons, a forgotten `super()`.

## Links

- The scaffolds: [docs/design/typed-projects](../design/typed-projects/README.md).
- The concepts compared by 0004: [docs/design/extension-composition](../design/extension-composition/README.md).
