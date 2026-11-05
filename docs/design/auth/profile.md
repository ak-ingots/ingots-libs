# ingot-auth: the profile

A part of [the design of the auth](README.md). What the auth knows of a
user:

- **The profile itself**: its `uid`, what the rest of an application knows
  the user by, and the time it was created, by the sign-up.
- **Its identifiers**: a nickname, an email, a phone, an id at a provider,
  each `(kind, value)` bound to the uid, verified before it is stored ([methods.2.4](methods/README.md#methods-2-4), [2.5](methods/README.md#methods-2-5));
  **its secrets**: what verifies them, the hash of its one password
  ([password.1.2](methods/password.md#password-1-2)), a TOTP secret.
- **Its tags**: marks it has or has not, `premium`; **its attributes**:
  typed values, a birth date. Each of a registry, ids and names, the
  metadata giving the registries to the consumers.
- **Its permissions**: of [access](access.md), computed, not kept.

The client sees a part of it, the tags, the attributes and the permissions,
to build its interface ([1.3](#profile-1-3)).

## Stories

| # | Actor | Story | Needs | Status |
|---|---|---|---|---|
| <a id="profile-1-1"></a>1.1 | operator | **I register the tags and the attributes a profile may hold, each attribute with its type, and rename or delete them; the metadata gives them by their ids.**<br>• The services `Tags` and `Attrs` of `ingot_auth.profiles.tags.v1` and `ingot_auth.profiles.attrs.v1`: `Create`, `List`, `Rename`, `Delete`. | — | Implemented |
| <a id="profile-1-2"></a>1.2 | operator | **I set the tags and the values of the attributes of a profile.**<br>• The profile holds only its uid and its time today. | [1.1](#profile-1-1) | Draft |
| <a id="profile-1-3"></a>1.3 | client | **I get my profile, its tags, its attributes and my permissions, to build my interface, and learn when it changed, so that I show no button the server refuses.**<br>• The server is the truth; the profile a client holds is an aid to its interface, as the catalogue of the permissions is.<br>• The permissions are a part of the profile the client sees, as the tags and the attributes are.<br>• `AuthUserProfile.Get` gives the profile of the caller and its hash, computed once, when the profile comes into the cache with the session ([sessions.2.4](sessions.md#sessions-2-4)), and carried by `AuthCaller`.<br>• Every reply carries the hash in the metadata of its transport, under one name for all, `ingot-auth-user-profile-hash` (the user, 2026-11-03): a header in HTTP, a key of the trailing metadata in gRPC. Not an `ETag`: that is of the resource of the reply. Lowercase with hyphens, as gRPC takes no other key and HTTP does not care; no `X-` (RFC 6648). The core gives the hash, each transport puts it where it puts such things.<br>• The client compares it with its own and asks for the profile again when it differs: a permission granted shows on the next reply, and one taken away hides its button before a refusal.<br>• A refusal, `PERMISSION_DENIED` or 403, stays the safety net: the client asks again on it.<br>• Example: given alice granted `CAN_MODIFY_ITEM`, or tagged `premium`, when her client makes any call, then the reply carries a new hash, the client asks for the profile and shows the button.<br>• A push of the change, by a stream, later if ever: only for an interface that must change without any request. | [1.2](#profile-1-2), [sessions.2.2](sessions.md#sessions-2-2), [sessions.2.4](sessions.md#sessions-2-4), [access.1.1](access.md#access-1-1) | Draft |

## Flows

The profile of the caller, and its change seen on any reply:

```mermaid
sequenceDiagram
    participant Client
    participant Server as any servicer
    participant Profile as AuthUserProfile servicer
    Client->>Profile: AuthUserProfile.Get(), Bearer token
    Profile-->>Client: {tags, attrs, permissions}, hash h1
    Note over Client: builds the interface, keeps h1
    Client->>Server: a call, Bearer token
    Server-->>Client: the result, ingot-auth-user-profile-hash: h2
    Note over Client: h2 is not h1
    Client->>Profile: AuthUserProfile.Get()
    Profile-->>Client: the profile again, h2
```

## API sketch

```proto
// The package and the path by ADRs 0009 and 0011, to be named with the
// slice that brings it.
service AuthUserProfile {
  rpc Get(GetProfileRequest) returns (GetProfileResponse);
}

message GetProfileResponse {
  repeated uint32 tag_ids = 1;   // the ids of the registry of the tags
  // the values of the attributes, by their ids
  map<string, int32> permissions = 3;  // a mask per domain
  string hash = 4;
}
```

```python
profile = await user_profile.Get(GetProfileRequest(), metadata=auth)
reply, call = await shop.Buy.with_call(request, metadata=auth)
if dict(call.trailing_metadata())["ingot-auth-user-profile-hash"] != profile.hash:
    profile = await user_profile.Get(GetProfileRequest(), metadata=auth)
```

## Questions

1. <a id="profile-q1"></a>Parked. The name of the service, `AuthUserProfile`
   as said, or by the packages of the contracts, `ingot_auth.profiles.v1`,
   `Profile`? And the message of the values of the attributes, shared with
   those of a session. Hold [1.3](#profile-1-3), of slice 4.
