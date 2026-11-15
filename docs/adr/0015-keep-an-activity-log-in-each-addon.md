# 0015. Keep an activity log in each addon, of one shape

- Status: Proposed
- Domains: design, storage
- Date: 2026-11-15
- Deciders: Aliaksandr Karotki
- Supersedes / Superseded by: —

> In the context of **addons changing the state of their entities, each in
> a storage of its own**, facing **who changed what and when kept in the
> entities themselves, `closed_by` of a session, a history planned for the
> profile**, we decided for **an activity log in each addon that needs one,
> in its own storage, of one shape across the ecosystem**, and against **a
> generic addon of the log, and fields of the entities**, to achieve **one
> answer to who changed what, written with the change**, accepting **the
> same code repeated in the addons, kept alike by this record**.

## Context

ingot-auth 0.3.0 keeps who closed a session in the session, `closed_by`,
and its design plans a history of the profile of its own (profile.2.1):
each entity grows the fields of who changed it, each its own way (the user,
2026-11-15: "начинаем размазываться с журналированием активностей").
words-project kept an activity log instead, a record a change, `who`,
`action`, `entity_type`, `entity_id`, `description`, `when`, written by
each operation after its change, its entities keeping no `created_at`.
A generic addon of the log was weighed: the addons keep their entities in
storages of their own, MongoDB for one, SQL for another, and a log apart
from them cannot be written in the transaction of the change.

## Decision drivers

- One source of who changed what and when, not a field per entity.
- The record written with the change, in its transaction.
- Each addon free to keep it in its own storage.
- What is written checked by mypy, without a registry to manage, nor an
  assumption of the readers on what a record holds.

## Considered options

1. Fields of the entities, `created_by`, `closed_by`, a history each.
2. A generic addon of the log, one storage for all.
3. A log in each addon that needs one, of one shape.

## Decision

Option 3. An addon changing the state of its entities keeps an activity
log of its own, in a storage of its own, as its other storages are:

- **A record a change of state**: create, update, delete of an entity, and
  the other verbs of the domain where they tell more, `bind` and `unbind`
  of the entities linking others, `sign_in`, `revoke`. A read is not
  recorded.
- **Its shape**: `who`, the uid of the caller, `system` for what the code
  does by itself, with what the addon knows of the caller beside it, one
  actor, the session of the caller in ingot-auth; `action`, of an enum of
  the addon; `entity_type`, the full
  name of the unit of the entity; `entity_id`; `context`, optional;
  `run_uid`, the uid of the run of operations, not of one operation: the id
  of the request a client sent, or one a job of the server generated, in the
  background or by a schedule, every record of the run sharing it, always
  there: the code doing a thing by itself takes a new one, which its line in
  the log of the server tells (the user, 2026-11-15); `when`.
- **The context is optional, a dataclass an activity of a type of entity**,
  typed where an operation writes it, in the code of its time: the creation
  of a tag needs none, that of an attribute a little, the value of an
  attribute set for a user more. mypy checks what an operation records, no
  registry of fields to manage. The storage keeps it as a map of attributes
  and gives it back as one: a record is a fact as it was written, never
  migrated; a reader, an administration, assumes no attribute of a type of
  entity, and shows the set each record has (the user, 2026-11-15).
- **Written in the transaction of the change**; a failure to write it fails
  the change or is swallowed and logged, by a strategy the application
  declares in a slot, `strict` or `swallow`.
- **Read by a group of auditors** of the addon, by its own flag, filtered by
  who, action, entity and time.
- An entity keeps its state, not who changed it: `closed_by` of a session
  of ingot-auth goes, its history is the log.

## Consequences

### Positive

- One place to ask who changed what, in each addon, by one shape.
- No change without its record under `strict`.

### Negative

- The log is repeated in each addon that keeps one: its storage, its
  operations, its contract tests.
- A log across addons is read addon by addon.

### Open questions

- How long a log is kept, and who prunes it.
- Whether a user sees a part of the log of its own profile.

## Links

- The design of the log of ingot-auth: [docs/design/auth/activity.md](../design/auth/activity.md).
- words-project, `activity_log/`: the precedent.
