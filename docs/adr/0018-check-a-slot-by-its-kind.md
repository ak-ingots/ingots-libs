# 0018. Check a slot declared again by its kind, an inherited one by its join

- Status: Proposed
- Domains: design
- Date: 2026-11-25
- Deciders: Aliaksandr Karotki
- Supersedes / Superseded by: — (refines a rule of [0004](0004-static-composition-with-typed-slots.md))

> In the context of **a slot a subclass declares again, or inherits from bases
> holding different classes in it**, facing **the check of 0004 refusing at
> class creation what mypy accepts: a slot whose annotation widens its
> contract, `notifier: Slot[Notifier] = Slot(MailNotifier)`, replaced by a
> sibling**, we decided for **a slot declared again checked for its kind
> alone, the class it holds left to mypy, and a slot inherited from bases
> holding different classes still checked to hold a class extending all of
> them**, and against **the check of 0004 kept whole, and no check at all**,
> to achieve **the types as the one contract of a slot declared, and a join
> of siblings caught where mypy misses it**, accepting **a class held that
> mypy alone checks**.

## Context

[ADR 0004](0004-static-composition-with-typed-slots.md) rejects slot conflicts
when the class is created: a slot must hold a subclass of what every direct
base holds in it, and mypy rejects the same. It does not: a slot is covariant,
and an annotation may type it wider than its default,

```python
class Unit(SlotsOwner):
    notifier: Slot[Notifier] = Slot(MailNotifier)

class AppUnit(Unit):
    notifier = Slot(SmsNotifier)  # mypy: fine; 0004: refused
```

so the check refused code the types accept, and an application could not
replace a default by a sibling of its contract.

Dropping the check lost one case mypy does not see: two bases holding
siblings in one slot, both keeping the wider annotation, and a subclass
declaring nothing. It inherits the slot of the first base, the second's
class gone unseen.

## Decision

Two checks at class creation (ingots 0.37.0):

- A slot declared again in a subclass is of the kind of the slot of each
  base, a `Slot` for a `Slot`, `Factories` for `Factories`; the class it
  holds is mypy's to check against the annotation of the base.
- A slot a subclass inherits, declaring none, from bases holding different
  classes in it holds a subclass of the class of each base; else the
  subclass declares it, with a join class, as 0004 says.

The rest of 0004 stands.

## Consequences

- An annotation widens the contract of a slot; an application replaces a
  default by any class of it.
- A slot declared again with a class out of its contract passes the runtime
  check: mypy alone refuses it.
- The other checks at class creation were reviewed against the types and
  kept: what they check, a place, a name, a value, the types do not express.
