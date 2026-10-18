# 0004. Static composition of extensions with typed slots

- Status: Accepted
- Date: 2026-10-18
- Deciders: Aliaksandr Karotki
- Supersedes / Superseded by: —

> In the context of **composing an application from Ingots addons**, facing
> **deep trees of units and entities that the application customizes at any
> level**, we decided for **static composition by plain inheritance, with
> children declared as typed slots** and against **dynamic composition of
> registered extensions and generics threaded through every level**, to
> achieve **types that mypy and the IDE see down to the deepest entity, and
> conflicts rejected at import time**, accepting **one short class per level
> of a deep customization and an explicit join class wherever two addons
> extend the same default**.

## Context

Ingots is built around PUER: a project holds units, units hold entities and
other units, a runner drives the project. Addons ship their own projects,
units and entities; an application combines several addons and customizes
their elements. Real addons reach four and more levels of nesting, and
flattening them is not an option.

The current `ingots` composes dynamically: extensions are registered at
runtime and the final classes are built with `type()`. It makes integration
one operation, but types end where the extension starts: mypy and the IDE see
the declared class, not the built one, and errors surface as runtime
`AttributeError`. `ingots` is going to be rewritten from scratch, so the
composition mechanism is decided first.

Three concepts were prototyped on one scenario (two addons, a three-level
tree, an entity customized at the bottom, settings extended by both addons):
[docs/design/extension-composition](../design/extension-composition/README.md).

## Decision drivers

- Customization at any depth of the tree.
- Types visible to mypy and the IDE everywhere, including the neighbours an
  extension uses.
- Errors at import time or in mypy, not at runtime.
- The result does not depend on the order in which extensions are registered.
- No state shared between projects: several projects live in one process.
- Little boilerplate per level.

## Considered options

1. Dynamic: extensions registered on a descriptor, the final class built by
   `type()` from the leaves (the current `ingots`).
2. Static with type parameters: the true classes of the children threaded
   down as generics through every level.
3. Static with typed slots: plain inheritance; children declared as typed
   descriptors that subclasses narrow.

Option 1 is the most concise and integrates an addon in one operation, but is
typed only within its own branch, depends on the order of a `set`, keeps
extensions in global state, and relies on every `super()` in the registration
chain. Option 2 is fully typed, but the parameters pile up level by level,
need explicit bounds everywhere, and duplicate the `*_cls` attributes without
anything checking that the two agree. See the concepts' README for details.

## Decision

Option 3: composition is static (classes are linked by inheritance at import
time) and uses the slots mechanism.

- A parent declares each child as a typed slot on the class
  (`sub_unit = Slot(Pkg1SubUnit)`); the child is created on first access and
  owned by its parent's instance. A subclass customizes a child by narrowing
  its slot to a subclass (`sub_unit = Slot(AppSubUnit)`).
- An entity's back-reference is narrowed by an annotation
  (`project: "AppProject"`), not by type parameters. An addon narrows it to
  its own project, the application to the combined one.
- Slot conflicts are rejected when the class is created: a slot must hold a
  subclass of what every direct base holds in it. mypy rejects the same.
  Where two bases hold different classes in one slot (typically a default
  such as settings extended by several addons), the combining class declares
  the slot with an explicit join class; a nested class is enough when it adds
  nothing.
- A slot cannot be assigned on an instance; it changes only through a
  subclass.
- Overrides are cooperative: a method that extends a base's behaviour calls
  `super()`. A forgotten `super()` silently cuts off the behaviour of the
  classes behind it in the MRO. This is common to all three options, since
  each extends behaviour by inheritance, and none of them detects it.

## Consequences

### Positive

- `p.pkg1_unit.sub_unit.entity` is the application's class for mypy and the
  IDE, and so are its project and settings.
- Combining addons wrongly fails at import time and in mypy, with a message
  naming the slot and the bases.
- No registration step and no global state: a class is its own composition,
  and projects do not share anything.

### Negative

- No one-operation integration: customizing an entity N levels deep takes one
  short class per level.
- Each default extended by several addons needs an explicit join class in
  every project that combines them.
- The `project` annotation is a promise mypy does not verify.

### Open questions

- Lifecycle hooks over lazily created slots, the runner and the CLI tree built
  from slots.
- Ordering of hooks between siblings that come from different addons.
- Detecting a forgotten `super()` in overrides (for example, of framework
  hooks at class creation).

## Links

- Concepts compared: [docs/design/extension-composition](../design/extension-composition/README.md).
- The current dynamic implementation: `ingots` (`ExtensionsManager`).
