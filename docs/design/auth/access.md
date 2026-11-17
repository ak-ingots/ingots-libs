# ingot-auth: the access

A part of [the design of the auth](README.md). What a caller may do: the
permissions, given to the users by their groups.

## The concept

The permissions are of ingots, `ingots.defaults.operations`:

- **A domain of permissions** is a `PermissionFlags`, its flags bits of a
  mask, each kept for good, as the masks are stored and sent between
  services, bound to its unit by the slot `permissions`, a
  `PermissionsSlot`, its domain the full name of the unit
  ([the entity tree](../entity-tree/README.md)):
  `AuthSignUpPermissions(PermissionFlags)` with `CAN_SIGN_UP = 1 << 0`, of
  `auth.sign_up`.
- **`Permissions`** is a mask per domain, of a caller or required by an
  operation, built by the permissions of a unit:
  `shop = self.parent.permissions; shop(shop.flags.CAN_PAY)`.
- **A caller**, `Caller(uid, permissions, is_root)`, runs an operation; the
  anonymous one has none, the root runs any.
- **An operation** builds the permissions it requires by its hook
  `_get_permissions()`, through those of its unit, its parent; the
  `PermissionsChecker` of the project compares them with those of the caller,
  `OperationPermissionsError` if they fall short.
- **A client** gets the permissions of a contract as an aid, the enum
  `Permission` next to its service; the server checks them anyway.

What the auth adds, the users, the groups, the permissions (as
`ugp` of words-project, the precedent):

- **A user** is a profile ([profile](profile.md)), by its uid.
- **A group** is known by its name, unique, the id itself:
  `app.grp_admins`, `auth.profiles.grp_managers`, the same in every
  environment, clearer to people and in the scripts than a number
  ([Q1](#access-q1)); its full name, the path of its slot from the
  project, as the domain of the permissions of a unit is its full name, no
  name given by hand (the user, 2026-11-13). It grants permissions, a mask
  per domain.
- **The groups** are found by the sub-unit `auth.access.groups`, which
  gives them by its API, whatever their source ([2.1](#access-2-1)). The
  code is one source: each group an entity in a slot `grp_*` of a unit of
  its domain, an `AuthGroupsOwner`, found by a walk from the project down
  the owners alone, as the commands are down the units of the command line
  (the user, 2026-11-13), created in no storage.
- **What a group grants** is of its hook, `_get_permissions()`, each class
  of its MRO adding its own by `super()`: an addon, a contrib, the
  application, each grants what it needs to the same group, and the slots
  of ingots make the application declare the class that joins them.
- **`auth.grp_signed_in`**, a group of the core in the auth, has every
  signed-in caller as a member, no membership stored: it grants what every
  signed-in caller may do, a session of its own, the methods open, and what
  the others add to it ([1.1](#access-1-1)).
- **`auth.grp_anonymous`**, a group of the core in the auth, has every
  caller that tells no one as a member, none stored: it grants what anyone
  may, the anonymous caller of the project having it ([1.1](#access-1-1)).
- **A membership** binds a user to a group, many to many: a user is a
  member of any number of groups ([Q4](#access-q4)). The memberships are
  all the storage keeps of the access.
- **The permissions of a signed-in caller** are the union of what its
  groups grant, `auth.grp_signed_in` included, computed from its uid
  ([1.1](#access-1-1)). They are of the caller, formed after the sign-in,
  not of the session, which stays a session ([Q3](#access-q3)).
- **The root** is the CLI: an operator joins the first administrator to
  its group there ([2.4](#access-2-4)).

The permissions on an object, of a profile on a record, are parked in
[object-permissions](../object-permissions/).

## Stories

### 1. The permissions of a caller

| # | Actor | Story | Needs | Status | Coverage |
|---|---|---|---|---|---|
| <a id="access-1-1"></a>1.1 | application | **I get the permissions of a signed-in caller from its groups, `auth.grp_signed_in` with the others.**<br>• The permissions are of the strategy of the permissions, the slot `permissions` of the access, from the uid: `AuthGroupsGrants` of the core (`AuthGroupsPermissions` is the domain of the permissions of the groups), the union of what the groups of the user grant, `auth.grp_signed_in` first; a membership of a group no source has any more grants nothing. An application binds no other, nor subclasses it.<br>• They are of the caller, `AuthCaller(uid, session_id, permissions)`, formed after the sign-in, and again on a miss of the cache; the session holds none ([Q3](#access-q3)).<br>• `auth.grp_signed_in` of the core, `AuthSignedInGroup`, grants (the user, 2026-11-05): those of a session of its own, `CAN_SIGN_OUT`, `CAN_LIST_OWN`, `CAN_REVOKE_OWN`; those of the methods, `CAN_SIGN_IN` and `CAN_BIND`, by their toggles, the getters of the method ([methods.1.3](methods/README.md#methods-1-3)). What the application and its addons grant every signed-in caller, they add to it by its hook, no ClassVar of a list.<br>• The caller is kept in the cache next to its session, by the same hash of the token, apart from it ([sessions.2.4](sessions.md#sessions-2-4)).<br>• The anonymous caller has what the group `auth.grp_anonymous` of the core grants, `AuthAnonymousGroup`, of every caller that tells no one, none stored, as `auth.grp_signed_in` is of every signed-in user (the user, 2026-11-13: the groups are in the code already): what anyone may of the auth, as its units tell it, `get_anonymous_permissions()` of the sign-up, the sign-in, the methods and the metadata; an application grants anyone more, or less, by its class in the slot. `AuthCallersProvider` of `AuthProject` gives it to the anonymous caller of the project, `operations.callers.get_anonymous()` of ingots 0.33.2.<br>• A signed-in caller has the permissions of its groups alone, not what anyone may, `auth.grp_anonymous` not among them (the user, 2026-11-13): a user its groups do not let in uses what is open to anyone until it signs in, and is refused once it has; an operation of the groups to fix, or a ban to keep.<br>• Built so far: the strategy, `auth.grp_signed_in` granting the `CAN_SIGN_IN` of each method open, the caller; the permissions of a session of its own come with the sign-out ([sign-out.1.1](sign-out.md#sign-out-1-1)), `CAN_BIND` with the bind.<br>• Example: given the shop granting `ShopPermissions.CAN_BUY` to `auth.grp_signed_in`, and alice a member of `editors`, which grants `ArticlesPermissions.CAN_PUBLISH`, when alice signs in, then her caller may buy, as may any other, and publish, as bob, not an editor, may not. | — | Implemented | unit |
| <a id="access-1-2"></a>1.2 | operator | **I switch a method off for one user or a cohort, the sign-in by nickname of a leaked account, the bind for guests.**<br>• By the permissions of the method, `CAN_SIGN_IN` and `CAN_BIND` ([methods.1.3](methods/README.md#methods-1-3)), taken from the profile.<br>• Every signed-in caller has them ([1.1](#access-1-1)): taking them off one needs a group that denies or a default group to leave ([Q2](#access-q2)). | [1.1](#access-1-1) | Draft | — |

### 2. The groups

What the application declares, and what an operator does with it, by the
gRPC services of `ingot_auth.access.*.v1` and by the CLI, `auth access`.

| # | Actor | Story | Needs | Status | Coverage |
|---|---|---|---|---|---|
| <a id="access-2-1"></a>2.1 | application | **I declare the groups my application is written for, each with what it grants, in the code, reviewed with it, joined with what my addons grant to the same groups.**<br>• A group is an `AuthGroup` in a slot `grp_*` of a unit of its domain extending `AuthGroupsOwner`, as an operation is in a slot `op_*` of its unit (the user, 2026-11-13): the sub-unit `auth.access.groups`, `AuthGroupsUnit`, finds the groups by a walk from the project down the owners alone, a plain unit and everything in it staying out, as the command line goes down its units alone, and holds none, a group in a slot of it refused with its class; mypy sees every flag a group grants.<br>• A group grants by its hook, `_get_permissions()`, each class adding its own to `super()`; `get_permissions()`, final, gives the union. Two bases holding unrelated classes in a slot of a group make the application declare the class that extends them, refused at the creation of the class otherwise, by the slots of ingots: no grant is lost silently.<br>• The code is one source of the groups, the first (the user, 2026-11-09): the unit gives the groups by its API, `get(name)`, `get_all()`, whatever their source, so that another, groups an operator creates at run time, may join it later behind the same API.<br>• A group is named by its full name, the path of its slot from the project, dotted, `auth.profiles.grp_managers`, as the domain of the permissions of a unit is its full name (the user, 2026-11-13, [the entity tree](../entity-tree/README.md)): no name given by hand, none repeated; a group moved in the code is renamed, its memberships migrated by the application. A class in no slot is a mixin of what it grants, an addon granting to a group of the application by one.<br>• A group removed from the code leaves its memberships, which grant nothing; a command that prunes them comes when one asks for it.<br>• No group is active or not: a group off is a group removed ([Q5](#access-q5)).<br>• Example: given `AppUnit` in the slot `app` with `grp_admins` and the shop with `grp_buyers`, then `get_all()` gives the groups of the core, then `shop.grp_buyers` and `app.grp_admins`, in the order of the walk, `get("app.grp_admins")` the group, `get("admins")` raises `AuthGroupNotFoundError`. | — | Implemented | unit |
| <a id="access-2-2"></a>2.2 | operator | **I list the groups and what each grants, to know whom to add where.**<br>• `Groups.ListGroups`, `auth access groups list`: the name and the masks of each, read only; the domain of permissions `auth.access.groups`, `CAN_READ`.<br>• A grant to a user directly is not here ([Q6](#access-q6)): a group of one if need be. | [2.1](#access-2-1) | Implemented | `test_operator`, game slice 4 |
| <a id="access-2-3"></a>2.3 | operator | **I add a user to a group and remove it, and read the groups of a user and the members of a group.**<br>• `Members.AddMember(group, uid)`, `RemoveMember`, `ListMembers(group)`, `ListMemberGroups(uid)`, `auth access members add app.grp_admins <uid>`; the domain `auth.access.members`.<br>• Adding a member again keeps one membership, removing one not there is no error: a script runs them twice safely. The groups of a user list those no source has any more too, granting nothing, to be found and pruned.<br>• A group no source has is refused, `AuthGroupNotFoundError`, and so are `auth.grp_signed_in` and `auth.grp_anonymous`, which keep none; a uid of no profile, `AuthProfileNotFoundError`.<br>• The membership is of the access, not of the profile record ([Q7](#access-q7)). | [2.1](#access-2-1) | Implemented | `test_operator`, game slice 4 |
| <a id="access-2-4"></a>2.4 | operator | **I make the first administrator from the command line, before any caller may grant anything.**<br>• The CLI runs as the root: `auth access members add app.grp_admins <uid>`, `app.grp_admins` declared by the application, granting the permissions of the members.<br>• Example: given `app.grp_admins` granting `AuthMembersPermissions.CAN_ADD`, and alice signed up, when the operator runs the command, then alice, signed in, adds the members over gRPC. | [2.1](#access-2-1), [2.3](#access-2-3) | Implemented | `test_operator`, game slice 4 |
| <a id="access-2-5"></a>2.5 | end user | **A group I join, or a new grant of my group, shows on my next request, without signing in again.**<br>• As [sessions.2.4](sessions.md#sessions-2-4): a change of the memberships of a user forgets its callers in the cache.<br>• The grants of the code change with a deploy only: the key of a caller in the cache holds a digest of the groups, computed once, so a deploy that changes them finds none of the old callers ([Q8](#access-q8)): `get_digest()` of the groups, from their names and masks. | [2.1](#access-2-1), [2.3](#access-2-3), [sessions.2.4](sessions.md#sessions-2-4) | Implemented | `test_operator`, game slice 4 |
| <a id="access-2-6"></a>2.6 | operator | **I make a user a reader or a keeper of the registries of the auth by a group of the core, with no group of my own.**<br>• The core declares the groups of the work of its registries, in the units of their domains (the user, 2026-11-13): in the profiles, `auth.profiles.grp_consumers`, reading the tags and the attributes, and `auth.profiles.grp_managers`, keeping them; in the sessions, `auth.sessions.grp_consumers`, reading the attributes and the presets, `auth.sessions.grp_managers`, keeping them but the bindings, and `auth.sessions.grp_admins`, binding too. The profiles bind nothing: no admins of theirs.<br>• What they grant is of the code, as for any group; an application grants them more, or less, by its class in their slot. Granting from an administration, the grants of a group kept and changed apart from the code, is parked ([Q10](#access-q10)).<br>• Example: given alice a member of `auth.sessions.grp_managers`, then she renames a preset, and binding an attribute to it is refused, `OperationPermissionsError`. | [2.1](#access-2-1) | Implemented | `test_operator`, game slice 4 |

### 3. The catalogue

| # | Actor | Story | Needs | Status | Coverage |
|---|---|---|---|---|---|
| <a id="access-3-1"></a>3.1 | operator | **I see every permission the server knows, by domain and name, to grant them by name rather than by bits.**<br>• The domains are of the whole application; ingots has no registry of them, the enum `Permission` of each contract is the catalogue of a client ([Q9](#access-q9)). | [2.2](#access-2-2) | Draft | — |

## Data

Where each piece lives:

| What | Where | Shape |
|---|---|---|
| A group and what it grants | the code: a slot `grp_*` of a unit of its domain, an `AuthGroupsOwner` | its full name, `shop.grp_managers`; `get_permissions()`, the union of the hooks of its MRO |
| `auth.grp_signed_in` | the code: the slot `grp_signed_in` of the auth, of the core | every signed-in caller a member, none stored |
| `auth.grp_anonymous` | the code: the slot `grp_anonymous` of the auth, of the core | every caller that tells no one a member, none stored |
| The groups of the registries | the code: slots `grp_*` of the profiles and the sessions, of the core | `auth.profiles.grp_consumers`, `auth.sessions.grp_admins`, … |
| A membership | the storage: `storage.access.members` | `(group, uid)`, unique, found by the group and by the uid |
| The permissions of a caller | the cache: a caller by the hash of the token and the digest of the groups | `AuthCaller(uid, session_id, permissions)`, computed on a miss |

## API sketch

An addon grants to the groups of the core and declares its own in the unit
of its domain (story [2.1](#access-2-1)), a class in no slot the mixin of
what it grants to a group of the application:

```python
class ShopSignedInGroup(AuthSignedInGroup):
    project: "ShopProject"

    @t.override
    def _get_permissions(self) -> Permissions:
        shop = self.project.shop.permissions
        return super()._get_permissions() | shop(shop.flags.CAN_BUY)

class ShopManagersGroup(AuthGroup):  # shop.grp_managers
    parent: "ShopUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        shop = self.parent.permissions
        stock = self.parent.stock.permissions
        return (
            super()._get_permissions()
            | shop(shop.flags.CAN_REFUND)
            | stock(stock.flags.CAN_UPDATE)
        )

class ShopAdminsGroup(AuthGroup):  # in no slot: to the admins of the app
    project: "ShopProject"

    @t.override
    def _get_permissions(self) -> Permissions:
        shop = self.project.shop.permissions
        return super()._get_permissions() | shop(shop.flags.CAN_CLOSE)

class ShopUnit(AuthGroupsOwner, OperationsOwner, Unit):
    permissions = PermissionsSlot(ShopPermissions)
    stock = Slot(StockUnit)
    grp_managers = Slot(ShopManagersGroup)

class ShopAuthUnit(AuthUnit):
    grp_signed_in = Slot(ShopSignedInGroup)

class ShopProject(AuthProject):
    auth = Slot(ShopAuthUnit)
    shop = Slot(ShopUnit)
```

The application (stories [1.1](#access-1-1), [2.1](#access-2-1)) takes the
groups of its addons, the shop and the articles here, and joins what they
grant to `auth.grp_signed_in`: both hold it, so it declares the class extending
them, as the slots require; its own groups are in a unit of its own:

```python
class AppSignedInGroup(ShopSignedInGroup, ArticlesSignedInGroup):
    pass  # CAN_BUY and CAN_READ, with what the core grants

class AppAdminsGroup(ShopAdminsGroup, ArticlesAdminsGroup):  # app.grp_admins
    project: "AppProject"

    @t.override
    def _get_permissions(self) -> Permissions:
        members = self.project.auth.access.members.permissions
        return super()._get_permissions() | members(
            members.flags.CAN_ADD, members.flags.CAN_REMOVE
        )

class AppAuth(ShopAuthUnit, ArticlesAuthUnit):
    grp_signed_in = Slot(AppSignedInGroup)

class AppUnit(AuthGroupsOwner):
    grp_admins = Slot(AppAdminsGroup)

class AppProject(ShopProject, ArticlesProject):
    auth = Slot(AppAuth)
    app = Slot(AppUnit)
```

The operator (stories [2.2](#access-2-2)–[2.4](#access-2-4)), by the CLI:

```console
$ python -m app auth access groups list
$ python -m app auth access members add app.grp_admins 0f6c…
```

In the core, `ingot_auth/access/`: the unit `AuthAccess`; its `groups/`,
`AuthGroupsUnit`, the API of the groups and their operations, `AuthGroup`,
`AuthGroupsOwner` and the walk, `AuthAnonymousGroup` and
`AuthSignedInGroup`, in the slots of the auth; the groups of the registries
in `ingot_auth/profiles/groups.py` and `ingot_auth/sessions/groups.py`; its
`members/`, the memberships, their operations and permissions; the strategy,
`AuthGroupsGrants`, taking the uid and giving `Permissions`. The storage
`storage.access.members`, in memory first.

## Questions

1. <a id="access-q1"></a>Answered: a group is known by its name, unique,
   the id itself, no number: clearer to people and in the scripts, the
   same in every environment (the user, 2026-11-08); in the code, the name
   of its slot (the user, 2026-11-09), then its full name, the path of its
   slot `grp_*` in a unit of its domain from the project, as the domain of
   the permissions of a unit is its full name, no name given by hand (the
   user, 2026-11-13, [the entity tree](../entity-tree/README.md)): a group
   moved in the code is renamed, its memberships migrated by the
   application.
2. <a id="access-q2"></a>Parked. Taking `CAN_SIGN_IN` of a method off one
   user: a group that denies, its bits taken off the rest, or
   `auth.grp_signed_in` made a group of stored memberships, every sign-up
   joining it, left to switch off? Holds [1.2](#access-1-2), later.
3. <a id="access-q3"></a>Answered: the session stays a session; the
   permissions of a signed-in user are of the caller, formed after the
   sign-in (the user, 2026-11-08). The strategy is of the access, one,
   `AuthGroupsGrants`; no `AuthFixedPermissions`.
4. <a id="access-q4"></a>Answered: a membership is the binding of a user
   to a group, never the user; a user is a member of any number of groups,
   many to many (the user, 2026-11-08). A group gone takes nothing with it:
   its memberships grant nothing, pruned later
   ([2.1](#access-2-1)).
5. <a id="access-q5"></a>Answered: no `is_active` of a group (the user,
   2026-11-08).
6. <a id="access-q6"></a>Answered: grants by groups only, none to a user
   directly (the user, 2026-11-08).
7. <a id="access-q7"></a>Answered: the memberships live in the access, by
   group, not on the profile (the user, 2026-11-08).
8. <a id="access-q8"></a>Answered: not the codes of the permissions,
   kept for good (the user, 2026-11-08: changing one is a migration,
   costly and not always safe), but the callers in the cache, stale after
   a change. The grants are of the code, changed by a deploy: a digest of
   the groups in the key of a caller; the memberships, by the operations:
   the callers of the user forgotten (the user, 2026-11-09).
9. <a id="access-q9"></a>Parked here, of ingots: a registry of the domains
   of the permissions, a unit of the operations, the catalogue of the
   operator and the check that no operation requires a domain the project
   lacks (the user, 2026-11-08); a design of its own. Holds
   [3.1](#access-3-1).
10. <a id="access-q10"></a>Parked: the grants of a group from an
    administration, not from the code alone: the code giving a default, the
    storage the changes of an operator over it (the user, 2026-11-13:
    interesting, a spaceport in a sandbox for now). With it, the domains of
    the permissions found by a walk, as the groups are, in the units of
    their domains, parked too ([Q9](#access-q9)).
