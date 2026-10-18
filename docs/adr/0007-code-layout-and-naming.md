# 0007. Code layout and naming

- Status: Accepted
- Date: 2026-10-18
- Deciders: Aliaksandr Karotki
- Supersedes / Superseded by: —

> In the context of **code read far more often than written, in a framework
> composed by inheritance**, facing **members in arbitrary order and names
> that collide or say nothing**, we decided for **a top-down order of class
> members and module contents, and a few naming rules** and against
> **leaving both to each author**, to achieve **code that reads the same way,
> from the general to the particular, in every repository**, accepting
> **reordering existing code once and checking part of it only in review**.

## Context

[0006](0006-design-principles.md) adopted PEP 8 and the common design
principles. PEP 8 says nothing about the order of members in a class, and
little about names beyond their case. In Ingots both matter more than usual:
a reader follows a customization through several classes of one hierarchy,
and the class and instance namespaces of projects, units and entities belong
to the user's slots and methods, so any framework name placed there can
collide with them ([0004](0004-static-composition-with-typed-slots.md)).

## Decision drivers

- Code reads like a book: from the general to the particular, the purpose
  before the details that serve it.
- The same thing is found in the same place in every class and module.
- The public interface of a class is read first.
- Framework names never collide with the user's names.
- A name says what it stands for.

## Considered options

1. No rule: each author's order and names.
2. A linter plugin's default order.
3. A written order and naming rules; the class member order configured in a
   linter, the rest checked in review.

## Decision

Option 3. `flake8-class-attributes-order` checks the class member order below
(its `class_attributes_order` setting in every repository's flake8
configuration); module order and naming are checked in review.

### Member order

From top to bottom:

1. Class attributes and slots: what the class consists of.
2. Static methods: helpers that only live in the class's namespace.
3. Class methods, including `__init_subclass__`: factories of instances and
   class-level hooks. `__init_subclass__` is written with an explicit
   `@classmethod`: it is one, and the linter then checks it as one.
4. `__init__`.
5. Properties: read-only access to attributes.
6. Other special methods (`__get__`, `__set__`, `__repr__`, `__eq__`, ...).
7. Instance methods.

Within each group, public members come first, then private ones. Overloads of
one method stay together, directly above its implementation.

### Module order

A module reads top-down as well: its docstring and `__all__`, imports, then
the main classes and functions, then the helpers they use. A function comes
before the functions it calls (the stepdown rule). Python allows it wherever a
name is only used inside a function body; what is needed at import time
(base classes, decorators, default values, class bodies) is defined first,
and only that breaks the order.

### Naming

- **Methods and functions are named by their action**: a verb, or a verb
  phrase (`get_elements()`, `list_elements()`, `check_slots()`; predicates
  `is_...()`, `has_...()`). A noun names a value, so `elements()` is either
  a property or a misnamed method. Properties and attributes are nouns.
  Special methods keep their protocol names.
- **No name mangling.** Private members take one underscore (`_cls`); two
  leading underscores only where mangling is actually needed, with a comment
  saying why.
- **Read-only attributes** are private and exposed through a property
  (`_cls` and `cls`), never as public attributes nobody may assign.
- **The `Base` prefix marks an incomplete class**, one a subclass has to
  complete. Its required methods are decorated with `@abc.abstractmethod`
  (mypy rejects instantiating the class) and raise `NotImplementedError` in
  the body; `abc.ABC` and `ABCMeta` are not used, a metaclass gets in the way
  of composition by inheritance. A complete class has no prefix.
- **Mixins prefix what they add.** A mixin adds to a class or an instance only
  what it needs, named with its own prefix followed by an action
  (`SlotsOwner._slots_get_project`, `_slot_<name>` keys). Services that work
  on a class are module functions (`check_slots(cls)`), not methods.
- **Type parameters are named after what fills them** (`EntityType`,
  `ProjectType`, `**ConstructorParams`), never `T`, `T1`, `P`.

## Consequences

### Positive

- A class is read top-down: what it is made of, how it is created, what it
  exposes, how it works; a module, from its purpose to its details.
- No framework name can shadow or be shadowed by a user's slot or method.

### Negative

- Module order and naming are kept by hand and checked in review only.
- Existing code is reordered once when a repository adopts the rule.
- One more linter plugin, configured identically in every repository.

## Links

- [0004](0004-static-composition-with-typed-slots.md): slots and composition
  by inheritance.
- [0006](0006-design-principles.md): design principles, PEP 8.
