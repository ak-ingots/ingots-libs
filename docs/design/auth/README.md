# ingot-auth: the auth

- Status: Draft; each story has its own
- Packages: ingot-auth (core, the memory contribs, the gRPC contrib);
  ingot-grpcio is read, not changed
- Date: 2026-11-03
- ADRs: 0004 (slots), 0005 and 0010 (contracts), 0007 (layout), 0009 and
  0011 (gRPC contracts), 0012 (this process)

The design of the auth as a whole, by [ADR 0012](../../adr/0012-design-a-feature-before-building-it.md):
a file a part of the domain, this one the whole, the metadata and the
slices. It lives on: a story is accepted for its slice, and marked
implemented once built; the rest waits as drafts.

## How to read it

- **A story** is a row of a table,
  `# | Actor | Story | Needs | Status | Coverage`: the story bold, then
  what it takes, the rules, the examples (given, when, then); `Needs`
  gives the stories it stands on, directly.
- **Its id** is the file and its number, `sessions.2.1`; the README of a
  directory is named by it, `auth.1.1`, `methods.4.1`. A link to a story of
  another file names the whole id, one within the file the number.
- **Its status**: `Draft`, written, not taken; `Accepted`, taken for the next
  slice; `Implemented`, in the code of `main`.
- **Its coverage**, the last column: what proves it as its actor meets it.
  A scenario of `examples/game` of ingot-auth, `test_sign_out`, run against
  the application in Docker ([the game](examples/game.md)), with the slice
  of the game that brings it while it is to come; `unit` for a story the
  unit tests and the contracts prove, of the composition, the transport,
  an author, or out of the game by its reason; `—` while not built.
- **A question** is in the file it is of, naming the stories it holds:
  those of the next slice are listed below, the others parked till their
  slice comes.
- **Floods are out of scope**: a cloud or a balancer in front takes them
  (the user, 2026-11-04), an application of ingot-auth hardly facing the
  internet on its own. The threats are those of the logic: guessing,
  enumeration, takeover; a denial of service only where the design itself
  piles things up, the sessions, the reads of the storage.
- **A variation of behaviour** is a strategy or a policy, never a flag or a
  hook of its own: a strategy decides how something goes (the lifetime of a
  session, what happens over the limit), a policy accepts or refuses a value
  (the length of a password, as in `ingot_auth.policies`). A strategy is an
  entity in a slot, a policy an operation in a group, run together
  ([password.2.1](methods/password.md#password-2-1)); the core gives the
  usual ones, an application picks one or writes its own. No slot has a
  default: the explicit over the implicit, a little more work at the start
  for more understanding and control (the user, 2026-11-03). A starter
  ([1.3](#auth-1-3)) takes the work off.

## The parts

| File | What |
|---|---|
| [methods/](methods/README.md) | How a user proves who it is: the identifiers and the credentials, the methods, their protocols (sign-up, sign-in, bind) and toggles, the password they share, the second factors, a file each |
| [sessions.md](sessions.md) | What a sign-in opens: the token, the attributes, the work in a session, the lifetime and the limit |
| [sign-out.md](sign-out.md) | How a session ends by a user or an operator, and a block |
| [access.md](access.md) | What a caller may do: the permissions, the users and the groups |
| [profile.md](profile.md) | What the auth knows of a user: the tags, the attributes, the permissions, and the profile a client sees; its version and history; its data by the GDPR |
| [activity.md](activity.md) | What changed, by whom and when: the activity log of the auth, read by the auditors |
| [examples/game.md](examples/game.md) | The example of an application of the auth, `examples/game` of ingot-auth: the backend of a game, its scenarios proving the stories end to end, the column `Coverage` |

## The concept

Three questions, asked in turn on the way of a request:

- **Who are you? The identification.** A user is a profile, its `uid` what
  the rest of an application knows it by. A profile is found by an
  identifier bound to it: a nickname, an email, a phone, the id of a
  provider. A profile binds as many as it likes, and each opens the methods
  of its kind: an email bound, the sign-in by it with the password, or by a
  code sent to it.
- **Prove it. The authentication.** A method verifies the identifier by a
  credential ([methods](methods/README.md)): the password of the profile at
  once, a code by mail in two, a second factor after the password if the
  profile has one. Signing up binds the identifier to a new profile,
  signing in opens a session for the profile it is bound to, binding adds
  it to the profile of the caller. Then the token of the session stands for the proof on every
  request ([sessions](sessions.md)), till the session ends
  ([sign-out](sign-out.md)).
- **May you? The authorization.** The token gives a caller of ingots, its
  uid and permissions ([access](access.md)); an operation declares the
  permissions it requires and the checker of ingots compares. The client
  gets the same permissions, with the tags and the attributes of the
  profile ([profile](profile.md)), to build its interface.

## Actors

- **The end user**: signs up and in, stays signed in, signs out, sees the
  devices signed in and signs one out.
- **The developer of a client**: learns from the metadata what it can sign
  up and in by, runs the steps of a method, keeps the token, sends it with
  each call, tells "sign in again" from other errors.
- **The author of an application**: picks a starter, or the methods, the
  lifetime of the sessions and their limit, decides what a signed-in caller
  may do.
- **The author of a method**: writes its steps once, for the sign-up, the
  sign-in and the bind.
- **The author of a transport** (the gRPC contrib, an HTTP one later): reads
  the token of a request, turns it into a caller, gives the attributes of
  the transport (the IP).
- **The author of an operation** of the application: needs the uid of the
  caller, and nothing else of the auth.
- **The operator**: signs out every session of a profile, blocks a profile,
  clears the expired sessions, sees when and where a profile signed in;
  finds, creates and deletes a profile, sees its history.

## Domain

- Events: `SignedUp`, `SignInStarted`, `SignInRefused`, `SignedIn` (a
  session opened), `SessionSeen`, `SignedOut`, `SessionRevoked`,
  `SessionEvicted`, `SessionExpired`, `ProfileBlocked`.
- Commands and who gives them:
  - read the metadata, the methods among it: the client, before anything;
  - start and answer a sign-up, a sign-in, a bind: the client, for the end
    user;
  - authenticate a token: the transport, on every request;
  - sign out: the client, with the token of its session;
  - list the own sessions, revoke one of them, revoke all the others: the
    client, for the end user;
  - revoke the sessions of any profile, block a profile: the operator;
  - sweep the expired sessions: the operator, or a schedule.

The states of a session are in [sessions](sessions.md#domain), those of an
attempt in [methods](methods/README.md#domain).

## Stories

### 1. The metadata and the starters

What a client and an application see and pick before anything.

| # | Actor | Story | Needs | Status | Coverage |
|---|---|---|---|---|---|
| <a id="auth-1-1"></a>1.1 | client | **I load the metadata of the auth to learn which methods I can sign up and sign in by, so that I show the user those and no others.**<br>• The metadata of the profiles and of the sessions is there, their registries, and that of the methods with them.<br>• The metadata lists the methods in the slots of the methods of the application, whatever they are: a method of the core or one of the application's own, each by its name, the path of its slot, with the flows open by it ([methods.1.2](methods/README.md#methods-1-2)). It knows no method of the core by itself: they are a catalogue, bound by the application ([methods.1.1](methods/README.md#methods-1-1)) (the user, 2026-11-04).<br>• A method opens the flows it takes by its hooks, `_get_sign_up_enabled`, `_get_sign_in_enabled`, closed in the base: a flow it does not take is listed closed, the client needs no more (the user, 2026-11-05).<br>• Example: given the nickname method bound with its sign-up closed, and the `email_code` one not bound, a client reads `[{name: nickname, sign_up: false, sign_in: true}]`: the nickname is there, its sign-up closed for now.<br>• The client calls a method by its own typed service (`Nickname.SignIn`): the list tells only which are there. | [methods.1.1](methods/README.md#methods-1-1) | Implemented | `test_metadata` |
| <a id="auth-1-2"></a>1.2 | client | **The metadata gives the policies a method checks, the length of a password, so that I check a form before sending it.**<br>• Abandoned (the user, 2026-11-11): a policy is an operation, reading what the server keeps, the history of a password, which is not for a client, nor its config to read in place of it. A client learns every policy broken at once, from the error of the start ([password.2.1](methods/password.md#password-2-1)); a check without the flow, a dry run, if a client ever needs one. | [1.1](#auth-1-1) | Abandoned | — |
| <a id="auth-1-3"></a>1.3 | application | **I import one starter that suits me, `game` or `web`, instead of a dozen classes to pick and subclass, and override only what differs.**<br>• `contrib/starters/`, a flat list, each units an application inherits and overrides, picking the methods and the strategies, or the storage, the cache and the transport too, under an extra of its own when it needs libraries; not "presets", which ingot-auth has twice already.<br>• Its worth grows with all that is bound by hand (the user, 2026-11-04): the methods, the configs of each, their servicers, the strategies of the sessions, of the timing, of the second factor. A starter binds them once, as they go together, and the creation of the project checks it as any application.<br>• Example: given `class AppAuth(AuthWebStarter)`, the application has the sign-up by `email_code`, the sign-in by `nickname` and `email_code`, a sliding month, the oldest session evicted, overriding only the slot of the mail. | [access.1.1](access.md#access-1-1), [sessions.3.1](sessions.md#sessions-3-1), [sessions.3.3](sessions.md#sessions-3-3) | Draft | `examples/game` composed by it, game slice 5 |

## Flows

The metadata, before any sign-in: what the client shows.

```mermaid
sequenceDiagram
    actor User as end user
    participant Client
    participant Server as Metadata servicer
    Client->>Server: Metadata.GetMetadata()
    Server-->>Client: methods = [nickname: {sign_in}, email_code: {sign_up, sign_in}]
    Note over Client: the forms of the methods open, sign-in by nickname or by a code by mail
    User->>Client: picks the code by mail
```

## API sketch

The client (story [1.1](#auth-1-1)), in Python for the sketch:

```python
metadata = await auth.GetMetadata(GetMetadataRequest())
methods = {method.name: method for method in metadata.methods}
if "nickname" in methods and methods["nickname"].sign_in:
    ...  # show the form of the nickname and the password
```

The metadata of the methods, a list of those bound:

```proto
// ingot_auth/metadata/v1/metadata.proto
// whether each flow is open, closed as well when the method does not take
// it; bind comes with the bind
message Method {
  string name = 1;  // the path of its slot: nickname, email_code
  bool sign_up = 2;
  bool sign_in = 3;
}

message GetMetadataResponse {
  Profile profile = 1;
  Session session = 2;
  repeated Method methods = 3;
}
```

In the core, `ingot_auth/metadata/`: a part `methods` of `AuthMetadata`,
a tuple of `AuthMethodMetadata(name, flows)`, one a slot of the methods,
found by `slots_find_entities` of `BaseAuthMethod`.

The packages of the core, a flow a package, as `sign_up/` is (the user,
2026-11-05):

- `ingot_auth/sign_in/`: the sign-in ([methods](methods/README.md#api-sketch));
- `ingot_auth/sign_out/`: the sign-out, likely one operation,
  `op_sign_out` ([sign-out](sign-out.md#api-sketch));
- `ingot_auth/sessions/`: the sessions, their registries, their lifetime,
  their revokes, all in the unit `AuthSessions`, no package within (the
  user, 2026-11-05) ([sessions](sessions.md#api-sketch)).

A starter (story [1.3](#auth-1-3)), the strategies picked once for a kind of
application:

```python
class AppAuth(AuthWebStarter):  # email sign-up, sliding month, evict the oldest
    methods = Slot(AppMethods)  # the email_code method, its mail by the mailer
```

## Pre-mortem

Six months on, the auth failed. Why:

- Every request went to the storage: the touch, the miss of the cache. The
  touch is written once per interval, the cache holds the open sessions
  ([sessions](sessions.md)).
- A revoked token still worked: the cache was not cleared, or another
  process had its own memory cache. Forgetting follows each close; the memory
  cache is for one process only, said in its docs, `AuthRedisCache` for
  more (ingot-auth 0.6.0).
- The strategy of the permissions was too narrow. It takes the uid and
  returns `Permissions`, of the groups of the user; if it needs the
  session, it takes the record instead ([access](access.md)).
- A grant to a group made the sessions of its members stale: the
  permissions are of the caller, kept apart from the session, so a change
  forgets the callers only ([access Q8](access.md#access-q8)).
- An application tuned the configs of one strategy and bound another: the
  sessions lived as long as the defaults of the other. The docstring of each
  strategy names its configs; the rest is the care of the application.
- `AuthCaller` did not fit ingots: an operation of another addon cannot see
  the session. Only the operations of the sessions read `session_id`; the rest
  read the uid.
- Applications wanted stateless tokens for their other services. Story
  [sessions.3.6](sessions.md#sessions-3-6): an operation that checks a token,
  before any JWT.
- The sign-in of two factors did not fit the steps of a method. The flow
  owns the steps (story [factors.1.1](methods/factors.md#factors-1-1)), so a
  second factor is a next step of the flow, whatever the method.

## Questions

Of this file: none now.

Those the next slice, 4, needs answered: none now.

## OWASP

The stories checked against the cheat sheets of OWASP (2026-11-20):
[Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html),
[Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html),
[Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html),
[Forgot Password](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html),
[Multifactor Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html),
[Credential Stuffing Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Credential_Stuffing_Prevention_Cheat_Sheet.html).

| OWASP | Built | To build |
|---|---|---|
| The storage of a password | scrypt of OWASP, the PHC format, a compare in constant time | the hashers, their cost, the rehash ([password.1.6](methods/password.md#password-1-6)) |
| The strength of a password | the policies as operations, no rule of composition | the length and the leaked ones ([password.2.4](methods/password.md#password-2-4)) |
| The messages and the timing | one reply, the dummy hash, the floor ([methods.4.2](methods/README.md#methods-4-2)) | the same for the recovery and the ban |
| The throttle | the answers of an attempt limited | the ban by the identifier ([methods.4.3](methods/README.md#methods-4-3)) |
| The change of a password, the re-authentication | — | [password.1.4](methods/password.md#password-1-4), [sessions.4.1](sessions.md#sessions-4-1) |
| The recovery of a password | — | [password.3.1](methods/password.md#password-3-1) |
| The second factor | — | TOTP, the codes of recovery, the failure told ([factors](methods/factors.md)) |
| The session: its token, its expiry, the logout | 256 random bits kept hashed; idle and absolute; revoked on the server; the own sessions listed and closed; the record | — |
| The notifications | — | [sessions.3.8](sessions.md#sessions-3-8) |
| The change of an email, the federation | — | [methods.5.1](methods/README.md#methods-5-1) |

Out of the addon: the cookies, the browser, the TLS, of the client and the
transport; the CAPTCHA, the fingerprints of a device or a connection, the
reputation of an IP, of the infrastructure in front, as the floods are
([how to read it](#how-to-read-it)). Not taken: the security questions,
which OWASP and NIST reject.

## Slices

The implementation, a pull request a slice, each with its first consumer, in
the order of `Needs`: a slice takes no story before those it needs.

1. The methods move from `contrib/methods/` to `methods/`
   ([methods.1.1](methods/README.md#methods-1-1)). No story of its own: a
   move.
2. **A thin path**: [auth.1.1](#auth-1-1);
   [methods.1.1](methods/README.md#methods-1-1),
   [1.2](methods/README.md#methods-1-2), [1.3](methods/README.md#methods-1-3),
   [2.2](methods/README.md#methods-2-2), [2.4](methods/README.md#methods-2-4),
   [4.1](methods/README.md#methods-4-1), [4.2](methods/README.md#methods-4-2);
   [password.1.2](methods/password.md#password-1-2),
   [2.1](methods/password.md#password-2-1);
   [nickname.2.1](methods/nickname.md#nickname-2-1);
   [access.1.1](access.md#access-1-1),
   [2.1](access.md#access-2-1)–[2.5](access.md#access-2-5);
   [sessions.1.2](sessions.md#sessions-1-2),
   [2.1](sessions.md#sessions-2-1)–[2.4](sessions.md#sessions-2-4), and
   [3.1](sessions.md#sessions-3-1) with the fixed strategy only. The methods
   and their toggles in the metadata, the groups, their grants and members,
   the identities by identifier and the
   password of the profile, a sign-in by nickname, a session in the memory
   storage and cache, `authenticate()`, the gRPC `Nickname.SignIn`, an
   asynchronous `_get_caller`; a test signs up, signs in, calls an
   operation as the user. Built, but the answers of
   [methods.2.2](methods/README.md#methods-2-2), moved to slice 3 (the
   user, 2026-11-11).
3. [sessions.3.1](sessions.md#sessions-3-1) the sliding strategies, the
   touch, the lazy close; [sessions.1.3](sessions.md#sessions-1-3); the
   sign-in by a code by mail, [email-code.2.1](methods/email-code.md#email-code-2-1),
   its code sent in the background, [methods.2.3](methods/README.md#methods-2-3),
   its answer by `SignIn.AnswerSignIn`, with the challenge
   ([methods.2.2](methods/README.md#methods-2-2)). Built.
4. [sign-out.1.1](sign-out.md#sign-out-1-1),
   [sessions.3.2](sessions.md#sessions-3-2),
   [sign-out.1.2](sign-out.md#sign-out-1-2),
   [sessions.3.5](sessions.md#sessions-3-5),
   [profile.1.2](profile.md#profile-1-2),
   [profile.1.3](profile.md#profile-1-3): sign-out, the own sessions listed
   and revoked, the record of the sign-ins, the values of a profile, the
   profile of the caller and its hash; their gRPC services. Accepted (the
   user, 2026-11-15), the prototype [own](own/) running them: the sign-out
   open to any caller; the own sessions and the profile of the caller by
   the flags `auth.grp_signed_in` grants; the place of a session by a
   strategy deriving its attributes; the record by the command line and
   over gRPC; the hash told by the servicers of a signed-in caller. Five
   pull requests, a story or two each, in this order, then 0.3.0. Built,
   the move of `AttrValue` a pull request of its own.
5. [activity.1.1](activity.md#activity-1-1)–[1.3](activity.md#activity-1-3),
   [2.1](activity.md#activity-2-1), [2.2](activity.md#activity-2-2): the
   activity log, by [ADR 0015](../../adr/0015-keep-an-activity-log-in-each-addon.md),
   its strategy of a failure, the auditors, the changes of the core recorded,
   `closed_by` of a session gone; then 0.4.0 (the user, 2026-11-15: before
   the rest). Built, released as 0.4.0.
6. [sign-out.1.3](sign-out.md#sign-out-1-3),
   [sessions.3.4](sessions.md#sessions-3-4): the operator signs out a
   profile, sweeps, by the CLI and gRPC. Built by ingot-auth#66,
   revoke-all, and #67, the sweep, its job the caller `auth.system`;
   released as 0.5.0.
7. [sessions.3.3](sessions.md#sessions-3-3): the limit of the sessions,
   how many a config of the operator, what over it a strategy of the
   application, the prototype [limit](limit/) running it: a sign-in
   evicting the one seen longest ago in its transaction, or refused; the
   game evicting, three a player till a web example takes the sets of
   sessions ([the game](examples/game.md#slices)). Breaking, the slot
   `limit` with no default: 0.8.0. Built by ingot-auth#83.
8. [auth.1.3](#auth-1-3): the first starter, `web`, out of what the slices
   above built; the tests of the slices then bind it.
9. The MongoDB backends of the sessions, with the profiles and identities
   still waiting for theirs. No story of its own: the stories above on
   another backend.

The slices of OWASP ([below](#owasp)), taken before 8 and 9, in this
order (the user, 2026-11-20):

10. [password.1.6](methods/password.md#password-1-6): the hashers in the
    slot `hasher`, their cost by configs, the rehash at a sign-in; the
    cost of the game's stand by those configs. Breaking, the attributes
    `SCRYPT_*` of `AuthPassword` gone: a minor release.
11. [password.2.4](methods/password.md#password-2-4): the policies of
    OWASP, the length in the core, the leaked passwords an extra.
12. [sessions.4.1](sessions.md#sessions-4-1),
    [password.1.4](methods/password.md#password-1-4),
    [sessions.3.8](sessions.md#sessions-3-8): the fresh proof, the change
    of the password, its mail the first of the notifications.
13. [password.3.1](methods/password.md#password-3-1): the recovery of the
    password by a code by mail.
14. [methods.4.3](methods/README.md#methods-4-3): the ban of an identifier
    after its failures.
15. [factors.1.1](methods/factors.md#factors-1-1),
    [1.3](methods/factors.md#factors-1-3)–[1.6](methods/factors.md#factors-1-6):
    the second factor, TOTP first, the codes of recovery, the failure told,
    the change of a factor.
16. [methods.5.1](methods/README.md#methods-5-1),
    [factors.1.2](methods/factors.md#factors-1-2): the bind, the change of
    an email, the code by mail as a factor; the providers after it.

Later, each in a slice of its own once its needs are built:
[methods.2.5](methods/README.md#methods-2-5),
[3.2](methods/README.md#methods-3-2),
[5.2](methods/README.md#methods-5-2);
[password.1.3](methods/password.md#password-1-3),
[1.5](methods/password.md#password-1-5),
[2.2](methods/password.md#password-2-2), [2.3](methods/password.md#password-2-3);
[nickname.3.1](methods/nickname.md#nickname-3-1);
[email.1.1](methods/email.md#email-1-1), [2.1](methods/email.md#email-2-1),
[3.1](methods/email.md#email-3-1);
[email-code.2.2](methods/email-code.md#email-code-2-2),
[3.1](methods/email-code.md#email-code-3-1);
[access.1.2](access.md#access-1-2), [3.1](access.md#access-3-1);
[sessions.3.6](sessions.md#sessions-3-6),
[3.7](sessions.md#sessions-3-7);
[sign-out.1.4](sign-out.md#sign-out-1-4);
[profile.1.4](profile.md#profile-1-4)–[1.8](profile.md#profile-1-8),
[2.1](profile.md#profile-2-1),
[3.1](profile.md#profile-3-1)–[3.4](profile.md#profile-3-4).

## The first prototypes

Written on 2026-10-27 before the addon was built; kept as a snapshot, not
maintained. Older than ADR 0012: no stories, only the code.

- [facade](facade/): the logic of auth from sign-up to the authenticated
  request over a facade of the storage, with its contract tests and a memory
  backend. It hardcodes a password hashed by scrypt, against the goal of a
  core that assumes no method: the addon keeps its methods pluggable.
- [profile](profile/): the schema of the profile joined from addons and an
  application, `AuthAttributes` made dataclasses and mapped one to one onto
  the flat values a storage keeps.
