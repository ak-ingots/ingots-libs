# The place of an entity: its parent, its full name, the permissions of its unit

- Status: Accepted
- Packages: ingots (0.34.0, breaking); ingot-grpcio and ingot-auth move with
  it (ADR 0008), ingot-auth with its groups named by their full names
- Date: 2026-11-13
- ADRs: 0004 (slots), 0007 (layout and naming), 0008 (dependents), 0012
  (this process)

## Problem

An entity knows its project alone. Where it sits in the tree is found by a
search, `slots_find_path()`, and is unknown in its `__init__`; an operation
reaches its own unit by an absolute path from the project,
`self.project.auth.profiles.tags`, which breaks when an application puts
the unit elsewhere, or twice. What tells where a thing is, is given again by
hand: the domain of a set of permissions, `domain="auth.profiles.tags"`,
repeating the path of its unit, and the name of a group of ingot-auth. The
user (2026-11-13): an entity knows its parent and its full name, given by its
owner when it is created, the system attributes set before an `__init__`
that takes none, as the ingots of before did; the permissions are bound to
their unit, their domain its full name; no artificial names, a migration
being the least problem of a structure changing that much.

## Actors

- **The author of an addon or an application**: writes the units, their
  operations, their permissions, the groups of ingot-auth.
- **The author of a kind of slot**: changes how the entities of its slots
  are created.
- **The operator**: reads the domains and the groups by their full names
  (ingot-auth, `auth access groups list`).

## Stories

| # | Actor | Story | Now or later |
|---|---|---|---|
| <a id="entity-tree-1"></a>1 | author of an addon | **An entity knows its parents and its full name from its `__init__` on, which takes no argument.**<br>• Its place is its parents, from the project to the owner it was created under, weak references, and its name, that of its attribute, set by one call (the user, 2026-11-13: one list of the parents, not three or four setters); the rest follows: `project`, the first, `parent`, the last, `parents`, `name`, and `full_name`, the dotted path from the project, `shop.stock`, a cached property, built on its first use. A parent gone, `ReferenceError`, as the project now.<br>• Its owner, the slot, the factory or the factories of its attribute, creates it: `cls.__new__(cls)`, the place set, then `__init__()`, so that `__init__` has it and takes nothing; a new system attribute changes no `__init__` of the ecosystem (the user, 2026-11-13, as `create_entity` of the ingots of before).<br>• Example: given `ShopProject` with `shop = Slot(ShopUnit)`, `ShopUnit` with `stock = Slot(StockUnit)`, then `project.shop.stock.full_name == "shop.stock"`, its `parents` are `(project, project.shop)`, and `StockUnit.__init__` reads them. | now |
| <a id="entity-tree-2"></a>2 | author of a kind of slot | **I change how the entities of my slot are created, by a method of the slot.**<br>• `create_entity(parent)` of the owner, final: the place first, then its hook `_prepare_entity(entity, parent)`, what the kind of slot gives its entities, then `__init__()` (the user, 2026-11-13: a method of the owner, to customize the entities of each kind of slot). The place is set whatever the hook does.<br>• Example: given `LabelSlot` giving each entity a label from its full name, then its unit reads the label in its `__init__`. | now |
| <a id="entity-tree-3"></a>3 | author of an addon | **An operation reaches its unit by its parents, wherever the application puts the unit, twice even.**<br>• `self.parent`, narrowed by an annotation, `parent: "StockUnit"`, as `project: "ShopProject"` is; or the nearest of a kind, `self.find_parent(StockUnit)`, typed by the kind, `LookupError` if none is; mypy checks what it reads.<br>• An entity of a factory is under the owner of the factory: `stock.op_count().parent is stock`, its full name that of the factory, `shop.stock.op_count`, the same for each it creates. | now |
| <a id="entity-tree-4"></a>4 | author of an addon | **I bind the permissions of a unit to it, their domain the full name of the unit, no name given by hand, nothing to import.**<br>• `PermissionFlags` without `domain=`, and no check of the names of the domains. The flags are of the unit, nested in it or next to it, no `permissions.py` of their own (the user, 2026-11-13), and bound by a slot, `permissions = PermissionsSlot(Flags)`, as all that lives in a unit is of a slot (the user, 2026-11-13: the enum knows no domain as a plain attribute). On the class the slot, its `flags` the enum; on a unit its permissions bound, created once a unit, `flags` and `domain`, the full name of the unit, as a `Factory` gives a `BoundFactory`, called with flags for their mask, `stock.permissions(StockUnit.Flags.CAN_COUNT)`, `{"shop.stock": 1}`. The slot is `permissions` of every unit: one enum a unit, a second set of flags of a sub-unit. A unit placed twice is of two domains, `shop.stock` and `outlet`.<br>• The permissions are of the operations: a unit owning operations mixes `OperationsOwner` in, a mixin, as the operations are not the base of a unit (the user, 2026-11-13).<br>• An operation has no constant of its permissions, which it would declare and import for nothing (the user, 2026-11-13): its hook, `_get_permissions()`, abstract, builds them by the permissions of a unit it reaches, its parent narrowed, `permissions = self.parent.permissions; return permissions(permissions.flags.CAN_COUNT)`, or the nearest of a kind, `self.find_parent(StockUnit)`; `Permissions()` for none. mypy checks it all: the flag, of the enum of that unit, the unit, of the parent narrowed, and the hook itself, an operation forgetting it abstract, refused where a factory takes it; nothing is left to check when a class is created.<br>• A flag alone tells no domain: `Permissions` takes the masks by domain, as a database or another service holds them.<br>• An operation builds the permissions of its own domain only: an integration, an operation of several modules, has a flag of its own and adds the permissions of the operations of the other domains it runs, not their flags, `permissions(permissions.flags.CAN_SELL) \| self.parent.stock.op_move().get_permissions()`, so that a caller lacking them is refused before anything is done, and each domain decides its own (the user, 2026-11-13: an integration is the sum of operations of different modules). The roles across domains are of the groups.<br>• Example: given `outlet = Slot(StockUnit)` next to `shop.stock`, a caller of `{"shop.stock": CAN_COUNT}` counts the stock of the shop, and is refused the count of the outlet. | now |
| <a id="entity-tree-5"></a>5 | operator | **I read the domains of the permissions and the groups by where they are, their full names.**<br>• ingot-auth names a group by its full name, `auth.profiles.grp_managers`, no `name=`; a unit moved renames its domain and its groups, the memberships migrated by the application. | later, ingot-auth |
| <a id="entity-tree-6"></a>6 | author of an addon | **The constants of the callers deprecated in 0.33.2 are gone.**<br>• `ROOT_CALLER`, `ANONYMOUS_CALLER`: `operations.callers.ROOT`, `get_anonymous()`. | now |

## Rules and examples

- The full name is the path of the slots from the project, dotted: `shop`,
  `shop.stock`, `shop.stock.op_count`.
  - Example: a unit class in two slots, two entities, two full names.
- An entity of a factory, or of factories of several classes, takes the full
  name of the slot: the class tells apart those of factories.
- The place is of the owner: an entity made otherwise, by hand in a test,
  has none.
  - Question: a helper of `ingots.testing` creating an entity under a
    parent, for the tests that build one alone?

## API sketch

The addon (stories [1](#entity-tree-1), [3](#entity-tree-3),
[4](#entity-tree-4)), as the prototype `place/` writes it:

```python
class AuditOperation(BaseOperation[None, str]):
    """Of a sub-unit of no permissions: of those of the stock above it."""

    @t.override
    def _get_permissions(self) -> Permissions:
        permissions = self.find_parent(StockUnit).permissions
        return permissions(permissions.flags.CAN_COUNT)


class StockAuditUnit(Unit):
    op_audit = Factory(AuditOperation)


class CountOperation(BaseOperation[None, str]):
    parent: "StockUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        permissions = self.parent.permissions
        return permissions(permissions.flags.CAN_COUNT)

    @t.override
    async def _run(self, parameters: None, metadata: OperationMetadata) -> str:
        return f"{self.parent.full_name}: {self.parent.count}"


class MoveOperation(BaseOperation[int, int]):
    parent: "StockUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        permissions = self.parent.permissions
        return permissions(permissions.flags.CAN_MOVE)


class StockUnit(OperationsOwner, Unit):
    class Flags(PermissionFlags):
        CAN_COUNT = 1 << 0
        CAN_MOVE = 1 << 1

    permissions = PermissionsSlot(Flags)

    op_count = Factory(CountOperation)
    op_move = Factory(MoveOperation)

    audit = Slot(StockAuditUnit)

    def __init__(self) -> None:
        super().__init__()
        self.count = 10
        self.opened_at = self.full_name  # known already


class SellOperation(BaseOperation[int, int]):
    """An integration: its flag, and what the move of the stock requires."""

    parent: "ShopUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        permissions = self.parent.permissions
        move = self.parent.stock.op_move()
        return permissions(permissions.flags.CAN_SELL) | move.get_permissions()


class ShopUnit(OperationsOwner, Unit):
    class Flags(PermissionFlags):
        CAN_SELL = 1 << 0

    permissions = PermissionsSlot(Flags)

    op_sell = Factory(SellOperation)

    stock = Slot(StockUnit)


class ShopProject(Project):
    shop = Slot(ShopUnit)
    outlet = Slot(StockUnit)  # a domain of its own, "outlet"
```

A kind of slot (story [2](#entity-tree-2)):

```python
class LabelSlot[EntityType: LabelledUnit](Slot[EntityType]):
    @t.override
    def _prepare_entity(self, entity: EntityType, parent: SlotsOwner) -> None:
        entity.label = f"#{entity.full_name}"
```

What is checked where: mypy, the parent narrowed and what it reads, the
flags a unit's permissions take, the hook of the permissions of an
operation, an `__init__` taking the project refused; the run, the masks by
domain as now. An operation runs another with the metadata it was given,
as its caller, or with metadata of another caller, `operations.callers.ROOT`
for a step trusted: the caller is of the metadata, as now.

## Pre-mortem

- An `__init__` of an addon still takes the project: mypy refuses
  `super().__init__(project)`, the release notes say how to move.
- An operation of a unit placed twice was given the permissions of one
  place by a group: the group builds them from the unit it means, by its
  full name; ingot-auth moves its groups with the release.
- `entity.__init__()` called by the owner surprises a reader: one place,
  `create_entity()`, documented, as the ingots of before did.

## Alternatives

- **The project and the parent alone**: the parents above are walked
  `parent.parent…`; the list gives each at once, and `find_parent()`.
- **The place in the constructor**, `Entity(project, *, parent, name)`: every
  `__init__(self, project)` of the ecosystem changes, and again with each
  new system attribute.
- **Setters called after `__init__`**: `__init__` would not know its place.
- **A setter an attribute, the project, the parent, the name**: one call
  with the list of the parents gives them all, and every ancestor besides.
- **Public `set_project()`, `set_parent()`**, as the ingots of before: anyone
  could move an entity after its creation; the package sets the place, the
  entity shows it.
- **A name given by hand to the domains and the groups**, as now: it repeats
  the place and drifts from it.
- **The enum nested in the unit**, `class PERMISSIONS(PermissionFlags)`: an
  enum of the module, bound by its slot, is imported by the groups and the
  tests as now.
- **A constant of the flags of an operation**, `PERMISSIONS =
  StockPermissions.CAN_COUNT`, the mask built by the nearest owner: a
  constant to declare and an enum to import, mypy unable to tie them to the
  place, a check when the class of the unit is created making up for it;
  the hook by the parent is checked by mypy whole.
- **The enum a plain attribute of the unit**, `PERMISSIONS = StockPermissions`,
  the mask built by the mixin: the enum knows no domain where it is; a slot
  binds it, the unit then giving the bound permissions of its domain.

## Open questions

1. Answered: `OperationsOwner`, a mixin of a unit owning operations, not
   its base, the permissions being of the operations (the user,
   2026-11-13); the flags of the unit bound by the slot `permissions`,
   `PermissionsSlot[...]`, generic in them, so that mypy checks them.
2. Answered: an operation under a sub-unit of no permissions builds those
   of the unit it means, `self.find_parent(StockUnit)`, by the list of the
   parents (the user, 2026-11-13).
3. Answered where: the contract enum `Permission` of a gRPC service names
   the flags, and the client learns the domain of a unit from the
   application now, by its full name; how, is found when ingot-grpcio, then
   ingot-auth move, slice 4 (the user, 2026-11-13).

## Slices

1. ingots: the constants of the callers removed (story [6](#entity-tree-6)).
2. ingots: the owner creates its entities, their parent and full name
   (stories [1](#entity-tree-1)–[3](#entity-tree-3)); `__init__` of the
   entities of ingots without the project.
3. ingots: the permissions bound to their unit (story [4](#entity-tree-4));
   release 0.34.0.
4. ingot-grpcio moves, then ingot-auth: its `__init__`, its permissions in
   its units, its groups by their full names (story [5](#entity-tree-5)).
