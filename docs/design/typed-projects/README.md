# Typed projects of the parts of an addon

- Status: Proposed
- Packages: ingots, ingot-auth, every addon with a contrib or a part that
  needs more of a project than its addon's own
- Date: 2026-11-26
- ADRs: [0019](../../adr/0019-compose-by-typed-projects.md), superseding
  [0004](../../adr/0004-static-composition-with-typed-slots.md);
  [0018](../../adr/0018-check-a-slot-by-its-kind.md)

## Problem

An entity reaches its project, its parent, through an annotation of its
class, as 0004 says, but only as far as its addon's project goes. A part
that needs more casts at each use: a method its configs, mixed into the
project's by the application as the docs ask
(`t.cast(AuthNicknameConfigs, self.project.settings.configs)`), a storage
on MongoDB the other addon (`t.cast("AuthProject", self.project).auth`),
the load its `PerfConfigs`. The cast is a promise no one checks, written at
each use; the application that forgets to mix the configs in learns it by
an `AttributeError`, at run time, on the first call.

## Actors

- The author of an addon: writes a part, a method, a contrib, and what it
  needs of a project.
- The author of a starter: joins the parts of a kind of application once.
- The author of an application: inherits a starter, or the parts it takes.

## Stories

| # | Actor | Story | Now or later |
|---|---|---|---|
| <a id="typed-projects-1"></a>1 | author of an addon | **The part I write gets a project of its own, what it needs and no more: its addon's project, the other addon's, the settings and configs joined. Its entities annotate `project:` by it and reach everything without a cast.**<br>• `AuthNicknameProject(AuthProject)`, its settings with `AuthNicknameConfigs`; `AuthMongoDbProject(AuthProject, MongoDbProject)`, the settings of both joined.<br>• The project types, it binds nothing: the slot of the method, of the storage, stays the application's choice. | now |
| <a id="typed-projects-2"></a>2 | author of a starter | **A starter is a project: it inherits the projects of the parts it takes, writes their joins once, and binds the parts.**<br>• `AuthGameProject(AuthNicknameProject, AuthEmailCodeProject, AuthMongoDbProject)`, the settings joined, the methods and the storage in their slots. | now |
| <a id="typed-projects-3"></a>3 | author of an application | **I inherit the starter, or the projects of the parts I take, not the bare project of an addon; I override only what differs.**<br>• `GameProject(AuthGameProject)`, its own configs and units.<br>• Without a starter, `SiteProject(AuthNicknameProject, AuthMongoDbProject)`, the joins mine. | now |
| <a id="typed-projects-4"></a>4 | author of an application | **A part I take whose needs my project does not meet fails before it runs: a join forgotten at the creation of the class and in mypy, configs lost in mypy.** | now |
| <a id="typed-projects-5"></a>5 | author of an application | **A part bound in a project that is not of its kind, a storage on MongoDB in a project without it, fails at the start, not at its first use.** | later, [open](#open-questions) |

## Rules and examples

- Rule: a type is narrowed by an annotation in the class, never by `t.cast`
  at each use: an entity its `project`, its `parent`; a mixin too.
  - Example: `AuthProofsOwner(SlotsOwner, Entity)` and an operation's
    `parent: AuthProofsOwner`: the parent of an entity is a `SlotsOwner`, so
    the mixin of an owner is one too, or mypy refuses the narrowing.
- Rule: a part that needs more than its addon's project ships the project it
  needs, next to it: `ingot_auth.methods.nickname.AuthNicknameProject`,
  `ingot_auth.contrib.storages.mongodb.AuthMongoDbProject`.
  - Example: the storage of MongoDB annotates `project: "AuthMongoDbProject"`
    and reads `self.project.mongodb.client` and `self.project.auth`.
- Rule: the project of a part types, it does not bind; a starter binds.
  - Question: does a part that has one obvious slot, a storage, bind it in
    its project too? Not now: two parts binding in one unit make the
    application join that unit as well, at every level down to the slot.

## API sketch

The scaffolds are in [scaffolds/](scaffolds/): `ingots_stub.py` the
framework, `mongodb_addon.py` ingot-pymongo, `auth_addon.py` ingot-auth a
section per module (the core, two methods, the storage on MongoDB, the
starter of a game), `app.py` a game on the starter and a site of its own
composition, `check_types.py` what runs, `mistakes.py` what mypy refuses.

```python
# ingot_auth/methods/nickname
class AuthNicknameSettingsUnit(AuthSettingsUnit):
    configs = Slot(AuthNicknameConfigs)


class AuthNicknameProject(AuthProject):
    settings = Slot(AuthNicknameSettingsUnit)


class AuthNicknameMethod(Entity):
    project: "AuthNicknameProject"

    async def sign_up(self, nickname: str) -> str:
        if not self.project.settings.configs.AUTH_SIGN_UP_NICKNAME_ENABLED:
            ...


# ingot_auth/contrib/storages/mongodb
class AuthMongoDbProject(AuthProject, MongoDbProject):
    settings = Slot(AuthMongoDbSettingsUnit)  # the settings of both joined


# ingot_auth/contrib/starters/game
class AuthGameProject(AuthNicknameProject, AuthEmailCodeProject, AuthMongoDbProject):
    settings = Slot(AuthGameSettingsUnit)
    auth = Slot(AuthGameUnit)  # the methods and the storage bound


# the application
class GameProject(AuthGameProject):
    settings = Slot(GameSettingsUnit)
    game = Slot(GameUnit)
```

What is checked where:

- mypy: a join forgotten (`Definition of "settings" in base class ... is
  incompatible`), the configs of a part lost by the settings declared
  again, an entity reaching what its project has not.
- At the creation of a class: a join forgotten, by the check of 0018.
- Nowhere yet: an entity bound in a project that is not of its annotation,
  story 5.

## Pre-mortem

- The joins pile up: every part redeclares the settings, so an application
  of five parts writes a join of five settings and five configs. It writes
  them today, by hand and unchecked; the starter writes them for it.
- The names collide: `AuthMongoDbProject` of the storage and that of the
  cache on MongoDB, if one comes. A project is of a part, named after it in
  its module; two parts of one infrastructure share it.
- An application inherits the bare `AuthProject` and binds a part anyway:
  the promise of the annotation is broken unseen, as with the cast. Story 5
  answers it.

## Alternatives

- **The cast at each use**, as now: the promise written again at each use,
  unchecked, and the configs mixed in by a sentence of the docs.
- **A protocol for what a part needs**, structural, no inheritance asked of
  the application: nothing checks the application against it either, the
  settings and the configs are still joined by hand, and the protocol
  repeats the slots it describes.
- **The project of a part binding it**: one class less for the application,
  but two parts binding in one unit make it join the unit as well, down to
  the slot; the starter binds instead.
- **Type parameters threaded down to the entity**: rejected by 0004 already.

## Open questions

- Story 5: the slot checks, when it creates an entity, that the project is
  of the class the entity annotates, once per entity, the hints of a class
  read once. Cheap, and the promise of 0004 becomes a check; is it worth a
  check at run time, or does the review of the composition suffice?
- `StarletteRunner.project`, a test's `runner.project`: a runner generic in
  its project, or the cast left at that boundary.

## Slices

1. ingots: `ingots.perf`, its `PerfProject` typing the configs; the first
   consumer, the load of ingot-auth.
2. ingot-auth: the projects of the methods and of the contribs, the
   examples inheriting them; the casts of the configs and of the contribs
   gone.
3. ingot-auth: the starter of the game a project, the example `game` its
   first consumer (story auth.1.3).
