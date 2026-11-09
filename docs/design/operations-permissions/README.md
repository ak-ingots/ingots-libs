# The permissions of an operation, by a hook

- Status: Draft
- Packages: ingots (0.33.0, breaking); every addon with operations moves with
  it (ADR 0008), ingot-auth first
- Date: 2026-11-09
- ADRs: 0004 (slots), 0007 (layout and naming), 0008 (dependents), 0012
  (this process); a new record for the suffixes of the classes, 0014

## Problem

An operation declares the permissions it requires as a constant of its class,
`PERMISSIONS = Permissions(AuthTagsPermissions.CAN_CREATE)`, and the checker
reads it from the class. Permissions that depend on the project, on its
configs or its slots, have no place: they would change the API of every
operation of the ecosystem the day one needs them. The user proposed a
method in place of the constant, with a registry of the domains it would read
(access Q9, 2026-11-08); a prototype showed the registry adds nothing mypy
does not check already on the flags imported, and the method alone is what
the dynamic permissions need (the user, 2026-11-09). So: a hook, its default
the constant, ready before a first dynamic case.

Two things of the same release ride along: a base of the commands that run an
operation, which ingot-auth wrote twice already (the user, 2026-11-09), and
the suffixes of the classes by their kind, an ADR of its own.

## Actors

- **The author of an addon or an application**: declares the permissions of
  its operations, a constant or a hook; writes the commands running them.
- **The author of a checker**: decides otherwise whether a caller may run an
  operation, a subclass in the slot `checker`.

## Stories

| # | Actor | Story | Now or later |
|---|---|---|---|
| 1 | author of an addon | **I declare the permissions of an operation as now, a constant of its class, and they stay one instance a process, readable from the class.**<br>• `PERMISSIONS = Permissions(...)`, `Permissions()` for none; the hook gives it by default, `get_permissions()` final, `_get_permissions()` returning `self.PERMISSIONS`.<br>• Not a new `Permissions` on every run: the constant is built once (the user, 2026-11-09). | now |
| 2 | author of an addon | **I give an operation permissions by its project, overriding the hook, without changing the API of the others.**<br>• `_get_permissions()` reads `self.project`, narrowed by `project: "ShopProject"` as everywhere in ingots, computed on every run; the operation caches what it wants to.<br>• Example: given `ShopRefund` requiring `CAN_REFUND_ANY` too when the limit of the project is 0, when a clerk with `CAN_REFUND` refunds, then `OperationPermissionsError`. | now |
| 3 | author of an addon | **I learn that an operation declares no permissions when its class is created, not on its first run.**<br>• A concrete operation declares `PERMISSIONS` or overrides `_get_permissions()`; else `TypeError` once, in `__init_subclass__`, in place of the check of the checker on every run. | now |
| 4 | author of a checker | **My checker gets the permissions the operation requires, whatever their source.**<br>• The runner creates the operation, asks `get_permissions()`, and gives them to the checker: `check(operation_cls, required, metadata)`, `_is_allowed(operation_cls, required, metadata)` as now. A refused caller costs an instance, of nothing but a weak reference to the project. | now |
| 5 | author of an addon | **I write a command running an operation without the metadata, the runner and the caller again.**<br>• `BaseOperationCommand[ParametersType, ResultType]`, of `ingots.defaults.operations`: `run_operation(parameters)` final, giving the result; `_get_operation()` abstract; `_get_caller()` the root by default. No template of `_run`: the command takes the result and does what it needs with it (the user, 2026-11-09). | now |
| 6 | author of an addon | **I tell an entity of ingots from a plain class or a dataclass by its name.**<br>• The suffix of the kind, `*Project`, `*Unit`, `*Component`, `*Command`, `*Operation`; an entity by its role, `*Method`, `*Storage`, never `*Entity`; a unit with a role by the role, `*Unit` for one that only groups; a dataclass a bare noun (the user, 2026-11-09). An ADR of its own, 0014, the rename in the same release. | now |
| 7 | operator | **I list every domain and flag the server knows, to grant them by name.**<br>• A registry of the domains, the catalogue walking it, and a check at the start of the project that every domain of a constant `PERMISSIONS` is there, read from the classes; a dynamic one is the care of its operation. With access.3.1 of the auth, its consumer. | later |

## API sketch

The prototype is [hook/](hook/): `make check-prototype
P=docs/design/operations-permissions/hook`.

As now, stories 1 and 3:

```python
class ShopPay(BaseOperation[int, int]):
    PERMISSIONS = Permissions(ShopPermissions.CAN_PAY)
```

By the project, story 2:

```python
class ShopRefund(BaseOperation[int, int]):
    project: "ShopProject"

    @t.override
    def _get_permissions(self) -> Permissions:
        if self.project.settings.configs.SHOP_REFUND_LIMIT == 0:
            return Permissions(ShopPermissions.CAN_REFUND | ShopPermissions.CAN_REFUND_ANY)
        return Permissions(ShopPermissions.CAN_REFUND)
```

The base, story 1:

```python
class BaseOperation[ParametersType, ResultType](Entity):
    PERMISSIONS: t.ClassVar["Permissions"]

    @t.final
    def get_permissions(self) -> Permissions:
        return self._get_permissions()

    def _get_permissions(self) -> Permissions:
        return self.PERMISSIONS
```

A command, story 5:

```python
class AuthListGroupsCommand(BaseOperationCommand[None, tuple[AuthGroupInfo, ...]]):
    @t.override
    def _get_operation(self) -> "BoundFactory[AuthListGroups]":
        return self.project.auth.access.groups.op_list

    @t.override
    async def _run(self) -> None:
        for group in await self.run_operation(None):
            print(group.name)
```

What is checked where:

- by mypy: a flag the domain has not; a hook of the class narrowing the
  project (below);
- at the creation of a class: an operation declaring neither the constant nor
  the hook;
- at run time: the permissions of the caller against those of the operation,
  as now. A misspelled flag fails the import already.

## Rules and examples

- Rule: the hook is of the instance, not of the class. A hook of the class
  takes the project as an argument, and an operation of an addon narrows it to
  its own project: mypy refuses the narrowed argument (the prototype marks
  it), where the attribute `project` of an instance narrows as everywhere in
  ingots.

## Alternatives

- **A registry of the domains, read by the operations**,
  `self.project.operations.permissions.auth.profiles.tags.CAN_CREATE`: mypy
  refuses a missing flag or domain, but it does so already on the flags
  imported, and every operation gets a long path (the user, 2026-11-09). The
  registry stays for the catalogue, story 7.
- **The hook alone, no constant**, `_get_permissions()` returning
  `Permissions(...)`: a new instance on every run, and nothing to read from a
  class, as a check at the start would (the user, 2026-11-09).
- **A hook of the class, `get_permissions(cls, project)`**: no instance before
  the check, but its argument cannot narrow to the project of an addon; a cast
  in every operation instead.

## Open questions

1. Answered: a unit holding a role, `BaseAuthMethod`, a unit for its slots,
   or `AuthProfilesStorage`, takes the suffix of its role; `*Unit` is of a
   unit that only groups (the user, 2026-11-09). Of ADR 0014.

## Slices

1. ADR 0014, the suffixes of the classes, Proposed: what the rename follows.
2. ingots 0.33.0: the hook of the permissions, the runner asking it, the
   checker given what it requires, the check at the creation of a class,
   `BaseOperationCommand`, the classes renamed by 0014; its tests are its
   first consumer.
3. The addons, along the tree (ADR 0008), each its pull request and release:
   the renames, their operations unchanged otherwise; ingot-auth replaces its
   two bases of the commands by `BaseOperationCommand`.
