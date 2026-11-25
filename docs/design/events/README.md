# Events: reactions to the facts of a domain

- Status: Built
- Packages: ingots (`ingots.defaults.events`, `project.events`); its first
  consumer ingot-auth (slice 12: the change of a password and its mail)
- Date: 2026-11-24
- ADRs: [0004](../../adr/0004-static-composition-with-typed-slots.md),
  [0012](../../adr/0012-design-a-feature-before-building-it.md),
  [0015](../../adr/0015-keep-an-activity-log-in-each-addon.md),
  [0017](../../adr/0017-change-an-api-by-its-consumers.md)

## Problem

Slice 12 of the auth tells a user its password was changed. The first
draft put a strategy in a slot `notifier`: one reaction, one slot, and a
rule of the slots ingots does not have. Every next slice needs more
reactions to the same facts: the audit of an application, a cache, a push,
analytics. A reaction must never undo or fail the change it reacts to, nor
fire for a change a transaction then undoes; and the code that publishes a
fact cannot know whether it runs inside the transaction of another
operation.

## Actors

- The author of an addon: declares the events of its domains, publishes
  them, ships the subscribers of its own defaults.
- The author of an application: adds its subscribers, removes those of an
  addon, holds the events of an operation of its own.
- The author of a contrib of storages: nothing to do; the facade of the
  transactions of its addon does it.

## Domain

Three kinds of actors around a change, kept apart:

| Kind | When | May refuse the change | What it is |
|---|---|---|---|
| Pre-hook | before | yes, a veto | a policy: an operation in a group (`policies_*`) |
| Step | in the change, in its transaction | yes, its failure fails the change | the flow and its strategies: the activity log (ADR 0015), the sessions closed on a change of a password |
| Reaction | after the fact | no | a subscriber of an event |

An event is a fact in the past tense, a frozen dataclass of its domain:
`AuthPasswordChanged`. A step is a guarantee of the method, which an
application must not switch off by removing a subscriber; a reaction is
optional, may fail, and fails alone.

## Stories

| # | Actor | Story | Now or later |
|---|---|---|---|
| 1 | author of an addon | I declare an event in the unit of its domain, `ev_changed`, with the subscribers of my defaults, so that it works with no code of the application | now |
| 2 | author of an addon | I publish an event after the change is done, not awaiting its subscribers, so that the reply does not wait for a mail and a subscriber never fails my flow | now |
| 3 | author of an application | I add a subscriber of mine, or drop one of the addon, by subclassing, so that the reactions are mine, checked by mypy | now |
| 4 | author of an application | my operation runs operations of addons in one transaction; their events go when it commits and are dropped when it rolls back, so that no mail tells of what is not | now |
| 5 | author of an application | I hold the events of a block with no transaction of its own, and drop them if I decide | now |
| 6 | author of an addon | the events of a savepoint dropped with it | later: no savepoints yet |
| 7 | author of an addon | a subscriber delivered at least once, through a queue | later: the dispatcher on a queue |
| 8 | author of an addon | a subscriber that subscribes itself, declared in its own unit, to an event of another addon | later: the application wires it now |
| 9 | author of a client | a catalogue of the events of a project | later: needs a class of the slot |

## Rules and examples

- Rule: an event is published after the change it tells is done, the last
  thing of the operation, outside its transaction block.
  - Example: the change of a password writes the hash, closes the other
    sessions and records the change in its transaction; after the block,
    it publishes `AuthPasswordChanged`.
  - Question: what if an operation publishes before its last step, which
    then fails and its parent catches it? The event tells of a change not
    done: the mistake of the author of the operation, said by the docs,
    not checked at run time.
- Rule: `publish` is not awaited. Outside any hold, the subscribers start
  at once in the background; inside a hold, they wait for it.
- Rule: a hold is a scope on a stack, in a context variable: a scope nested
  in another gives its events to it when it ends; the outermost sends
  them. A hold ends sending, raising or not: a fact published is a fact.
- Rule: only the one that knows the facts are undone drops them,
  `scope.discard()`: the rollback of a transaction, or the failure of its
  commit. The facade of the transactions of an addon holds the events of
  its block, once for all its backends.
  - Example: the game changes the password, an operation of the auth, and
    the nickname in one transaction; the nickname taken, it rolls back:
    the password stays the old one and no mail goes.
  - Example: the nickname optional, the game catches the error and
    commits: the password is changed and the mail goes, the fact is true.
  - Example: a block of a hold with no transaction raises after the change
    of the password: the change is written, the mail goes.
- Rule: a subscriber runs in a context of no hold and no transaction: what
  it publishes, it holds or sends itself; what it writes, it writes in a
  transaction of its own.
- Rule: a group of operations runs by one of two strategies, by whether
  its operations decide together:
  - `run_all_in_group`, the group as a whole, `run_group` of ingots
    renamed: the caller checked for all before any runs, a refusal
    refusing all, all run together to their end, the failures raised in
    an `ExceptionGroup`. The policies: a policy skipped is a check
    bypassed.
  - `run_each_in_group`, each on its own: the caller checked for each, one
    it may not run skipped, the others run together to their end, a
    refusal and a failure logged at `WARNING`, none raised. The
    subscribers of an event: a reaction is independent of the others.
- Rule: the subscribers run by `run_each_in_group`, by the metadata of the
  publisher; the flow that published never knows of them.
  - Example: a subscriber of the staff, a caller of no such permission: it
    is skipped, logged; the mail goes, the change is done.
  - Question: the permissions of a subscriber then gate the reactions to a
    fact, by errors in a log. A way to switch a reaction off by the
    caller? Not a good one: a subscription is the decision of the code,
    switched by subclassing; a subscriber needing other rights is a
    mistake of the configuration, which the log tells.
- Rule: the transactions of several storages are several transactions:
  the events follow the outermost hold. An operation mixing storages gets
  no atomicity, of its data nor of its events.

## API sketch

The code of each actor, in the prototype [`hold/`](hold/):

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthPasswordChanged:
    profile_uid: str
    at: datetime.datetime
    session_attrs: Mapping[str, AttrValue]


class AuthPassword(Unit):  # the addon: the event in the unit of its domain
    op_change = Factory(AuthChangePasswordOperation)
    ev_changed = Factories[BaseOperation[AuthPasswordChanged, None]](
        AuthMailPasswordChangedOperation
    )


# in the operation: the steps in the transaction, the event after it
async with storage.transaction():
    ...
self.project.events.publish(self.parent.ev_changed, event, metadata)


class GamePassword(AuthPassword):  # the application: its subscribers
    ev_changed = Factories[BaseOperation[AuthPasswordChanged, None]](
        *AuthPassword.ev_changed.classes, GameAuditOperation
    )


# the facade of the transactions of an addon, once for its backends
async with self.project.events.hold() as held:
    ...  # begin, the block, commit
    # on a rollback, or a failed commit: held.discard()
```

`ingots.defaults.events` gives `EventsUnit` (`project.events`):
`publish(subscribers, event, metadata)`, `hold() -> EventsScope`,
`EventsScope.discard()`, `join()` for a shutdown and the tests; the runner
of the operations gets `run_each_in_group`, and `run_group` becomes
`run_all_in_group`. The slot of an event is a plain
`Factories`: no class of its own until stories 8 or 9.

What is checked where:

- by mypy: a subscriber of another event in the slot, an event published
  to the subscribers of another, an event changed after it is made;
- at run time: the permissions of the subscribers, against the caller of
  the publisher; a refusal, a failure, logged.

## Threats

| Category | Threat | Answer |
|---|---|---|
| Spoofing | a mail of a change of a password that was rolled back, a phishing look-alike | a rollback drops the events of its transaction |
| Tampering | a subscriber changes the event for the next ones | an event is frozen |
| Repudiation | a reaction lost, no trace | a failure is logged with the subscriber; delivery at least once is story 7 |
| Information disclosure | a secret in an event, then in a log or a mail | an event carries no secret: the rule of the domain, said by the docs; the parameters of the operation keep theirs out of `repr` |
| Denial of service | a slow subscriber holds the reply; a subscriber flood | the subscribers run in the background; the dispatcher on a queue later |
| Elevation of privilege | a caller triggers through an event what it may not run | the caller of the publisher is checked for each subscriber; one refused is skipped |

## Pre-mortem

- The authors put steps into subscribers, the activity log say, and an
  application switches a guarantee off: the table of the three kinds goes
  into the guide of ingots, and a review of an addon checks it.
- Events published in the middle of a flow tell of changes not done: the
  rule says the last thing of an operation; the auth publishes after its
  transaction block alone.
- A process stops with subscribers running: lost reactions. `join()` in
  the shutdown of the project; story 7 for what must not be lost.
- Tasks of subscribers pile up under load: the same answer as for the
  dispatcher of the auth, a queue.

## Alternatives

- A strategy per reaction, `notifier = Slot(...)`: one reaction a slot, and
  a rule of the slots ingots does not have (`Slot(cls, base=...)`).
- Subscribers registered at run time, `subscribe()` / `unsubscribe()` in a
  phase of configuration: mutable state mypy does not see, the order
  undefined, a phase ingots does not have. Code subscribes for the life of
  the process: a declaration says it.
- The subscribers awaited by the operation, `await ev.run_group(...)`: the
  reply waits for them, a failure fails the flow, and inside the
  transaction of a parent they run before its commit.
- The activity records as the events, the log an outbox: what is
  recorded and what is told differ; each stays its own.
- The subscribers in the transaction, the activity log one of them: a
  subscriber becomes a step, its failure the failure of the change, and
  the storage would have to serialize them (a lock in MongoDB).
- A counter of the holds instead of a stack of scopes: a discard of an
  inner one would drop all, and tasks of a `gather` would share it.
- The buffer in the transaction of each storage: an event of one addon
  published in the transaction of another would have to find it.
- A package of its own, `ingot-events`: the mechanism is a unit over
  `Factories` and the runner, cross-cutting as the runner is.

## Decisions

1. The permissions of the subscribers are checked against the caller of
   the publisher (the user, 2026-11-24).
2. Two strategies to run a group: `run_all_in_group` (`run_group`
   renamed), all or none, for the policies; `run_each_in_group`, what is
   permitted, for the subscribers. Both run their operations together
   (the user, 2026-11-24).
3. The activity log and the events stay apart: a record is not an event,
   an event is not recorded by itself; each is written where its rule
   says.

## Slices

1. ingots: `EventsUnit` in `ingots.defaults`; `run_group` renamed
   `run_all_in_group` and `run_each_in_group` beside it, in the runner;
   `join()` in the shutdown of the project; a minor release, breaking by
   the rename (ADR 0017).
2. ingot-auth: onto that minor version of ingots, `run_group` replaced by
   `run_all_in_group`; the facade of the transactions holds the events;
   slice 12, the change of a password, its event and its mail.
