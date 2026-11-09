# ingot-auth: the access

A part of [the design of the auth](README.md). What a caller may do: the
permissions, given to the users by their groups.

## The concept

The permissions are of ingots, `ingots.defaults.operations`:

- **A domain of permissions** is a `PermissionFlags`, its flags bits of a
  mask, each kept for good, as the masks are stored and sent between
  services: `AuthSignUpPermissions(PermissionFlags, domain="auth.sign_up")`
  with `CAN_SIGN_UP = 1 << 0`.
- **`Permissions`** is a mask per domain, of a caller or required by an
  operation: `Permissions(Shop.PAY | Shop.REFUND, Stock.READ)`.
- **A caller**, `Caller(uid, permissions, is_root)`, runs an operation; the
  anonymous one has none, the root runs any.
- **An operation** declares the `PERMISSIONS` it requires; the
  `PermissionsChecker` of the project compares them with those of the caller,
  `OperationPermissionsError` if they fall short.
- **A client** gets the permissions of a contract as an aid, the enum
  `Permission` next to its service; the server checks them anyway.

What the auth adds, the users, the groups, the permissions (as
`ugp` of words-project, the precedent):

- **A user** is a profile ([profile](profile.md)), by its uid.
- **A group** is known by its name, unique, the id itself: `admins`,
  `editors`, the same in every environment, clearer to people and in the
  scripts than a number ([Q1](#access-q1)). It holds the permissions
  granted to it, a mask per domain.
- **The groups** are of the sub-unit `auth.access.groups`, which gives them
  by its API, whatever their source ([2.1](#access-2-1)). The code is one
  source: the groups an application declares as the attributes of the
  unit, with their grants, created in no storage (the user, 2026-11-09).
- **A membership** binds a user to a group, many to many: a user is a
  member of any number of groups ([Q4](#access-q4)). The memberships are
  all the storage keeps of the access.
- **The permissions of a signed-in caller** are computed from its uid
  ([1.1](#access-1-1)): those every signed-in caller gets, of the core and
  of the application, joined with those of its groups. They are of the
  caller, formed after the sign-in, not of the session, which stays a
  session ([Q3](#access-q3)).
- **The root** is the CLI: an operator joins the first administrator to
  its group there ([2.4](#access-2-4)).

The permissions on an object, of a profile on a record, are parked in
[object-permissions](../object-permissions/).

## Stories

### 1. The permissions of a caller

| # | Actor | Story | Needs | Status |
|---|---|---|---|---|
| <a id="access-1-1"></a>1.1 | application | **I get the permissions of a signed-in caller from its groups, joined with those every signed-in caller has.**<br>• The permissions are of the strategy of the permissions, the slot `permissions` of the access, from the uid: `AuthGroupsPermissions` of the core, the only one.<br>• They are of the caller, `AuthCaller(uid, session_id, permissions)`, formed after the sign-in, and again on a miss of the cache; the session holds none ([Q3](#access-q3)).<br>• Of every signed-in caller (the user, 2026-11-05): those of the methods, `CAN_SIGN_IN` and `CAN_BIND`, by their toggles, the getters of the method ([methods.1.3](methods/README.md#methods-1-3)); those of a session of its own, `CAN_SIGN_OUT`, `CAN_LIST_OWN`, `CAN_REVOKE_OWN`, given by the core; those of the application, `PERMISSIONS`, a ClassVar of its subclass, empty in the core.<br>• Of its groups: the union of the masks granted to each group it is a member of; a membership of a group no source has any more grants nothing.<br>• The caller is kept in the cache next to its session, by the same hash of the token, apart from it ([sessions.2.4](sessions.md#sessions-2-4)).<br>• Example: given `AppPermissions` with `ShopPermissions.CAN_BUY`, and alice a member of `editors`, which grants `ArticlesPermissions.CAN_PUBLISH`, when alice signs in, then her caller may buy, as may any other, and publish, as bob, not an editor, may not. | — | Draft |
| <a id="access-1-2"></a>1.2 | operator | **I switch a method off for one user or a cohort, the sign-in by nickname of a leaked account, the bind for guests.**<br>• By the permissions of the method, `CAN_SIGN_IN` and `CAN_BIND` ([methods.1.3](methods/README.md#methods-1-3)), taken from the profile.<br>• Every signed-in caller has them ([1.1](#access-1-1)): taking them off one needs a group that denies or a default group to leave ([Q2](#access-q2)). | [1.1](#access-1-1) | Draft |

### 2. The groups

What the application declares, and what an operator does with it, by the
gRPC services of `ingot_auth.access.*.v1` and by the CLI, `auth access`.

| # | Actor | Story | Needs | Status |
|---|---|---|---|---|
| <a id="access-2-1"></a>2.1 | application | **I declare the groups my application is written for, each with what it grants, in the code, reviewed with it.**<br>• The sub-unit `auth.access.groups`, `AuthGroups`, its attributes the groups, `editors = AuthGroup(Permissions(ArticlesPermissions.CAN_PUBLISH))`: the name of the attribute is the name of the group; mypy sees every flag a group grants.<br>• The code is one source of the groups, the first (the user, 2026-11-09): the unit gives the groups by its API, `get(name)`, `get_all()`, whatever their source, so that another, groups an operator creates at run time, may join it later behind the same API.<br>• A name is lowercase letters, digits and `_`, an attribute of Python; it never changes, as the scripts and the memberships name it.<br>• A group removed from the code leaves its memberships, which grant nothing; a command that prunes them comes when one asks for it.<br>• No group is active or not: a group off is a group removed ([Q5](#access-q5)).<br>• Example: given `AppGroups` with `admins` and `editors`, then `get_all()` gives the two, `get("editors")` its grants, `get("guests")` raises `AuthGroupNotFoundError`. | — | Draft |
| <a id="access-2-2"></a>2.2 | operator | **I list the groups and what each grants, to know whom to add where.**<br>• `Groups.List`, `auth access groups list`: the name and the masks of each, read only; the domain of permissions `auth.access.groups`, `CAN_READ`.<br>• A grant to a user directly is not here ([Q6](#access-q6)): a group of one if need be. | [2.1](#access-2-1) | Draft |
| <a id="access-2-3"></a>2.3 | operator | **I add a user to a group and remove it, and read the groups of a user and the members of a group.**<br>• `Members.Add(group, uid)`, `Remove`, `List(group)`, `ListGroups(uid)`, `auth access members add admins <uid>`; the domain `auth.access.members`.<br>• A group no source has is refused, `AuthGroupNotFoundError`; a uid of no profile, `AuthProfileNotFoundError`.<br>• The membership is of the access, not of the profile record ([Q7](#access-q7)). | [2.1](#access-2-1) | Draft |
| <a id="access-2-4"></a>2.4 | operator | **I make the first administrator from the command line, before any caller may grant anything.**<br>• The CLI runs as the root: `auth access members add admins <uid>`, `admins` declared by the application with the permissions of the members.<br>• Example: given `admins` granting `AuthMembersPermissions.CAN_ADD`, and alice signed up, when the operator runs the command, then alice, signed in, adds the members over gRPC. | [2.1](#access-2-1), [2.3](#access-2-3) | Draft |
| <a id="access-2-5"></a>2.5 | end user | **A group I join, or a new grant of my group, shows on my next request, without signing in again.**<br>• As [sessions.2.4](sessions.md#sessions-2-4): a change of the memberships of a user forgets its callers in the cache.<br>• The grants of the code change with a deploy only: the key of a caller in the cache holds a digest of the groups, computed once, so a deploy that changes them finds none of the old callers ([Q8](#access-q8)). | [2.1](#access-2-1), [2.3](#access-2-3), [sessions.2.4](sessions.md#sessions-2-4) | Draft |

### 3. The catalogue

| # | Actor | Story | Needs | Status |
|---|---|---|---|---|
| <a id="access-3-1"></a>3.1 | operator | **I see every permission the server knows, by domain and name, to grant them by name rather than by bits.**<br>• The domains are of the whole application; ingots has no registry of them, the enum `Permission` of each contract is the catalogue of a client ([Q9](#access-q9)). | [2.2](#access-2-2) | Draft |

## API sketch

The application (stories [1.1](#access-1-1), [2.1](#access-2-1)): the
groups and the permissions of every signed-in caller, in the access:

```python
class AppGroups(AuthGroups):
    admins = AuthGroup(Permissions(AuthMembersPermissions.CAN_ADD))
    editors = AuthGroup(Permissions(ArticlesPermissions.CAN_PUBLISH))

class AppPermissions(AuthGroupsPermissions):
    # those of every signed-in caller; the groups add their own
    PERMISSIONS = Permissions(ShopPermissions.CAN_BUY)

class AppAccess(AuthAccess):
    groups = Slot(AppGroups)
    permissions = Slot(AppPermissions)

class AppAuth(AuthUnit):
    access = Slot(AppAccess)
```

The operator (stories [2.2](#access-2-2)–[2.4](#access-2-4)), by the CLI:

```console
$ python -m app auth access groups list
$ python -m app auth access members add admins 0f6c…
```

In the core, `ingot_auth/access/`: the unit `AuthAccess`; its `groups/`,
`AuthGroups` and `AuthGroup`, the API of the groups and their operations;
its `members/`, the memberships, their operations and permissions; the
strategy, `AuthGroupsPermissions`, taking the uid and giving `Permissions`.
The storage `storage.access.members`, in memory first.

## Questions

1. <a id="access-q1"></a>Answered: a group is known by its name, unique,
   the id itself, no number: clearer to people and in the scripts, the
   same in every environment (the user, 2026-11-08); in the code, the name
   of its attribute (the user, 2026-11-09).
2. <a id="access-q2"></a>Parked. Taking `CAN_SIGN_IN` of a method off one
   user: a group that denies, its bits taken off the rest, or the base set
   moved into a default group every sign-up joins, left to switch off?
   Holds [1.2](#access-1-2), later.
3. <a id="access-q3"></a>Answered: the session stays a session; the
   permissions of a signed-in user are of the caller, formed after the
   sign-in (the user, 2026-11-08). The strategy is of the access, one,
   `AuthGroupsPermissions`; no `AuthFixedPermissions`.
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
