# Object permissions: an idea to come back to

Status: an idea, nothing decided, nothing built or prototyped. Written on
2026-11-01 so that the question is not researched twice. When the first operation
on one object needs it, this becomes an ADR of `ingots`, as it changes how
operations run.

**Why it can wait:** object permissions are an add-on above the ordinary ones. The
current `PERMISSIONS` of an operation stay as they are, and `OBJECT_PERMISSIONS`
would come next to them, breaking nothing.

## What we have today

`PermissionFlags` of a domain, bit masks: `Permissions` is `{domain: mask}`, on a
caller and on an operation (`ingots/defaults/operations/permissions.py`). An
operation declares `PERMISSIONS`, and `PermissionsChecker` checks them. These are the
simplest permissions: on operations and their sets. Some of those sets only coincide
with an entity, so the link "operation -> entity" is an accident, not a rule. In
ingot-auth, as of this writing only on its uncommitted branch `grpc-registry`:
`AuthTagsPermissions` (`auth.tags`), `AuthAttrsPermissions` (`auth.attrs`),
`AuthMetadataPermissions` (`auth.metadata`), one class and one domain per set of
operations; its `main` still has one `AuthPermissions` with `READ_REGISTRY` and
`MANAGE_REGISTRY`.

A mask answers "may it at all", not "may it with this tag". It cannot be multiplied
over instances: there is a mask per domain, and instances are unbounded.

## Where this stopped in words

`~/work/words-project/words` wanted to multiply "entity" permissions over the
instances of the entities, and stopped because nothing marked what is a permission on
an entity and what is one on an operation. Its flags
(the `common.py` under `operations/` of each app in `be/`) mix five kinds under one
`CAN_*`:

| Kind | Examples in words | "On which one?" |
|---|---|---|
| a pure operation | `CAN_SIGN_IN`, `CAN_SIGN_UP`, `CAN_ENTER_ADMIN`, `CAN_RESET_CONFIRMATION_PASSWORDS` | makes no sense: no object |
| an action on an entity | `CAN_MODIFY`, `CAN_DELETE`, `CAN_CHANGE_PASSWORD` | makes sense: multiplies over instances |
| an action on a collection | `CAN_CREATE`, `CAN_LIST_AUTH_PROFILES` | no instance yet, or many |
| a scope | `CAN_READ_DRAFT`, `CAN_READ_INACTIVE`, `CAN_READ_OWN_ADMIN_PROFILE`, `CAN_SUSPEND_OWN` | a filter by state or owner |
| managing access | `CAN_GRANT_PERMISSIONS`, `CAN_ADD_GROUPS` | depends; dangerous in its own way |

**The criterion:** ask "on which one?". If that makes no sense, it is a permission on
an operation. If it does, it is a permission on an entity, and only those multiply.
Even in plain CRUD only reading one object, updating and deleting multiply: creating
and listing stay on the collection. Today `CAN_READ` covers `List`, so one name hides
two meanings.

**The relation:** an operation *requires* permissions, it is not them. It is many to
many: moving a word between collections needs `CAN_MODIFY` on two instances, and
`SignIn` needs nothing of an entity. `PERMISSIONS = Permissions(...)` hides this,
since in the simple cases there is one requirement and no object.

## The scheme

From the user:

- `CAN_CRUD`: permissions for working with entities: classes, collections of objects.
- `CAN_RUD_OBJ`: permissions for working with objects. Creating does not belong here.
- Storing the latter takes a separate table: the same as ordinary permissions, plus a
  column with the object id.
- In operations: a step (or a mixin, but composition is better) goes to that table
  and looks whether the caller may change the object with id 123.

What the discussion added:

- **A step, not a mixin, and not for taste:** moving between two collections checks
  two objects, and a mixin cannot be applied twice.
- **Effective right on an object = the class mask OR the row of the object.** The class
  permission simply means "all instances", so an object right *widens* a class right.
  The alternative, where an object right only narrows, is simpler: the bit stays a gate
  at the entry. It does not cover "may edit this one object without a general right".
- **The bits may be the same, with only the key changing:**

  ```
  {"auth.tags": 0b0110}        # on the class: every instance
  {("auth.tags", 7): 0b1100}   # on the instance 7
  ```

- **Separate flag classes:** `CAN_UPDATE_OBJ` means nothing in the mask of a caller,
  and `CAN_CREATE` means nothing in a row of the table. Classes such as
  `TagsPermissions` and `TagObjectsPermissions` make that mistake visible to the types.
  This competes with the same-bits sketch above; to be decided.

## The conflict with the code

`PermissionsChecker.check(operation_cls, metadata)`
(`ingots/defaults/operations/checker.py`) runs before the runner creates an instance,
on purpose ("a refused caller costs no operation"), and sees no parameters.

So with `PERMISSIONS = CAN_UPDATE` on `AuthRenameTag`, a caller holding only a row for
the object 123 is refused at the entry, and the step never runs. Such an operation
cannot declare the class permission as required: it needs "class OR object", and that
cannot be decided at the entry. For pure operations everything stays as now.

## The danger: a forgotten step

If an object operation weakens the check at the entry, and only an explicit call in
`_run` protects it, a forgotten call is an open operation with no error at all. So
declare it, as `PERMISSIONS` is declared now, instead of calling it:

```python
class AuthRenameTag(...):
    PERMISSIONS = Permissions(Tags.CAN_UPDATE)
    OBJECT_PERMISSIONS = Permissions(TagObjects.CAN_UPDATE_OBJ)

    def _get_object_ids(self, parameters) -> Iterable[ObjectId]:
        return (parameters.id,)
```

The final flow of the runner decides: the class permission is there, so no trip to the
database; it is not, so it goes to the table for each id. `OBJECT_PERMISSIONS` without
the hook fails when the class is created. The step stays composition: the check itself
lives in an entity of its own, say a slot `object_checker`, as `checker` does now.

## Concerns

- **`List` is the expensive part.** A step does not help: there is no one id to check.
  Filtering after reading breaks pagination and leaks counts, so the query has to join
  the table: the storage facade has to know of the caller. This is the boundary
  between logic and storage that ingot-auth has not drawn yet.
- **Where the table lives.** Operations are in any addon, the table is one. `ingots`
  has no storage, so the interface of the checker goes there and the implementation
  probably to ingot-auth. An addon with object rights then depends on auth only through
  an interface, which fits the slots.
- **Orphans and reused ids.** No foreign key points at an arbitrary object: rows stay
  after a delete, and a reused id hands the rights to a new object. The registries of
  ingot-auth never reuse ids, others may. Deleting an object has to clean the table.
- **`NOT_FOUND` or `PERMISSION_DENIED`.** For an object without access, the second one
  reveals that it exists. To be decided once, for the whole approach.
- **Batches.** Checking N objects must not take N queries: the hook gives ids together
  for that reason.
- **Conditions are not lists.** `_OWN` and `DRAFT` do not fit a table of ids. Expressed
  uniformly, the model grows into policies. A flag such as `CAN_UPDATE_OWN` is the
  cheap way around, as in words.

## The gRPC contract

- An enum `Permission` names the flags of a set of operations (ADR 0009), a hint for
  building an interface. A client cannot work out its rights on one object from it.
- Rights on an object travel with the data, say a field with the allowed operations in
  each item of a response. Every RPC having its own messages makes this a compatible
  change.
- The server checks anyway: a hint never replaces the check.

## Questions when it comes back

1. May an object right widen a class right? The scheme above says yes.
2. The same bits, or separate flag classes?
3. How are `_OWN` and state scopes expressed: flags, or policies?
4. Who may grant object rights, and is that itself a permission?
5. Rows for users only, or for groups too?
6. `NOT_FOUND` or `PERMISSION_DENIED`?
