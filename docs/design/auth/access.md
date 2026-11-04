# ingot-auth: the access

A part of [the design of the auth](README.md). What a caller may do: the
permissions, of the users and, later, of the groups.

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

What the auth adds: the permissions of a signed-in caller, from its profile
([1.1](#access-1-1)). A user is a profile ([profile](profile.md)); the
groups and the grants that give the permissions to profiles are the access
subdomain, to come, and the permissions on an object, of a profile on a
record, are parked in [object-permissions](../object-permissions/).

## Stories

| # | Actor | Story | Needs | Status |
|---|---|---|---|---|
| <a id="access-1-1"></a>1.1 | application | **I decide what a signed-in caller may do, in one place, until the access subdomain decides it.**<br>• The permissions are of the strategy of the permissions, the slot `permissions` of the sessions, from the uid: `AuthFixedPermissions`, the same for every profile, of a ClassVar the application sets ([Q1](#access-q1)), until the access subdomain brings one of its own, of the groups and the grants.<br>• Computed when a session comes into the cache, kept with it ([sessions.2.4](sessions.md#sessions-2-4)).<br>• Example: given `AppPermissions` with `ShopPermissions.CAN_BUY`, when alice signs in, then her caller may buy, as may any other. | — | Draft |
| <a id="access-1-2"></a>1.2 | operator | **I switch a method off for one user or a cohort, the sign-in by nickname of a leaked account, the bind for guests.**<br>• By the permissions of the method, `CAN_SIGN_IN` and `CAN_BIND` ([methods.1.3](methods/README.md#methods-1-3)), taken from the profile.<br>• `AuthFixedPermissions` gives all the same set: switching off for one user waits for the access subdomain. | [1.1](#access-1-1); the access subdomain | Draft |

## API sketch

The application (story [1.1](#access-1-1)), the permissions of every
signed-in caller, in the slot `permissions` of
[the sessions](sessions.md#api-sketch):

```python
class AppPermissions(AuthFixedPermissions):
    PERMISSIONS = Permissions(
        AuthNicknamePermissions.CAN_SIGN_IN | AuthNicknamePermissions.CAN_BIND,
        AuthEmailCodePermissions.CAN_SIGN_IN,
        AuthSessionsPermissions.CAN_SIGN_OUT
        | AuthSessionsPermissions.CAN_LIST_OWN
        | AuthSessionsPermissions.CAN_REVOKE_OWN,
        ShopPermissions.CAN_BUY,
    )
```

In the core, `ingot_auth/session/sessions/permissions.py`: the base of the
strategy, taking the uid and giving `Permissions`, and
`AuthFixedPermissions`.

## Questions

1. <a id="access-q1"></a>The permissions of a signed-in caller:
   `AuthFixedPermissions` of a ClassVar until the access subdomain. Or of a
   config? Holds [1.1](#access-1-1), of slice 2.
