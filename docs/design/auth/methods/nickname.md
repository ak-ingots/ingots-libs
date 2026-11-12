# ingot-auth: the nickname method

A part of [the methods](README.md). A nickname and the
[password](password.md) of the profile, of one step: the identifier is the
nickname, normalized to NFKC and case-folded, so that `Alice` is `alice`.

## Stories

### 1. Signing up

| # | Actor | Story | Needs | Status |
|---|---|---|---|---|
| <a id="nickname-1-1"></a>1.1 | end user | **I sign up with a nickname and a password, in one step.**<br>• The nickname is checked by the group of the policies `policies_sign_up_nickname`, the password by that of the password ([password.2.1](password.md#password-2-1)), both empty unless an application gives policies to them in a subclass.<br>• Example: given a policy of a length of 12 in the group of the password, when alice signs up with `secret`, then `AuthMethodInvalidError` names the field `password` and the policy.<br>• Example: given alice signed up, when `Alice` signs up, then `AuthIdentityConflictError`: the nickname is taken, and told ([methods.4.2](README.md#methods-4-2)). | [methods.3.1](README.md#methods-3-1), [password.1.1](password.md#password-1-1) | Implemented |

### 2. Signing in

| # | Actor | Story | Needs | Status |
|---|---|---|---|---|
| <a id="nickname-2-1"></a>2.1 | end user | **I sign in with my nickname and my password, in one step, and get the token at once, or the challenge of my second factor.**<br>• The method verifies the password of the profile of the nickname; a nickname bound to none is verified against the hash of nothing all the same, `AuthMethodRefusedError` in both.<br>• The challenge of a second factor comes with the factors ([factors.1.1](factors.md#factors-1-1)). | [methods.2.2](README.md#methods-2-2), [methods.4.1](README.md#methods-4-1), [password.1.2](password.md#password-1-2) | Implemented |

### 3. Binding

| # | Actor | Story | Needs | Status |
|---|---|---|---|---|
| <a id="nickname-3-1"></a>3.1 | end user | **Signed up by my email, a code or a provider, I add a nickname to my profile, and sign in by it with my password.**<br>• A nickname needs no verification, only to be free ([methods.2.5](README.md#methods-2-5)): the bind is of one step, and a nickname taken is told, as on a sign-up, the caller signed in already.<br>• It opens a way to sign in: by the nickname and the password of the profile, once the profile has one ([password.1.3](password.md#password-1-3)).<br>• It opens no second factor: nothing is sent to a nickname.<br>• Example: given alice signed up by `email_code`, with a password set, when she binds `alice`, then she signs in by `alice` and her password as well. | [methods.5.1](README.md#methods-5-1), [password.1.2](password.md#password-1-2) | Draft |

## Flows

The sign-in as the client sees it, the [OneStepMethod](README.md#flows) of
the nickname, with no second factor:

```mermaid
sequenceDiagram
    actor User as end user
    participant Client
    participant Server as Nickname servicer
    Note over Client: the form of the nickname and the password
    User->>Client: alice, her password
    Client->>Server: Nickname.SignIn(nickname, password, attr_values)
    alt the password is right
        Server-->>Client: SignInResult.signed_in = {token, session_id}
        Note over Client: keeps the token, signed in
    else wrong, or no such nickname
        Server-->>Client: UNAUTHENTICATED (AuthMethodRefusedError)
        Note over Client: the form again, "wrong nickname or password"
    else the profile may not sign in by nickname
        Server-->>Client: PERMISSION_DENIED (AuthMethodDeniedError)
        Note over Client: "this way is closed to you"
    end
```

## API

### Sign-up, Python: Implemented

```python
start = AuthStartSignUpParameters(
    method="nickname",
    parameters=AuthNicknameStart(nickname="alice", password="..."),
    attr_values={device_model_id: "Pixel 9"},  # the id of a client attribute
)
result = await project.operations.runner.run(
    project.auth.sign_up.op_start, start, metadata
)
assert isinstance(result, AuthSignedUp)  # one step: never a challenge
```

| Field | Of | What |
|---|---|---|
| `method` | `AuthStartSignUpParameters` | The name of the method, the path of its slot in the methods: `nickname`. |
| `parameters` | `AuthStartSignUpParameters` | `AuthNicknameStart`, below. |
| `attr_values` | `AuthStartSignUpParameters` | The values of the attributes of the session whose source is the client, by their ids ([sessions.1.1](../sessions.md#sessions-1-1)); kept in the record of the sign-up. |
| `nickname` | `AuthNicknameStart` | The identifier once normalized, NFKC and case-folded; checked by `policies_sign_up_nickname`. |
| `password` | `AuthNicknameStart` | Normalized to NFKC, never in a `repr`; checked by `policies_set` of the password ([password.2.1](password.md#password-2-1)), then hashed. |
| `uid` | `AuthSignedUp` | The new profile: 128 random bits, 32 hexadecimal digits. |

Errors: `AuthMethodNotFoundError`, no such method; `AuthItemNotFoundError`,
`AuthItemInvalidError`, a value of an attribute unknown or of another type;
`AuthMethodInvalidError(field, policies)`, policies broken;
`AuthIdentityConflictError`, the nickname taken; `OperationPermissionsError`,
no `CAN_SIGN_UP`.

### The service, gRPC: Implemented, but the bind

`Bind` comes with the bind ([3.1](#nickname-3-1)), the challenge of a
second factor with the factors ([factors.1.1](factors.md#factors-1-1)).

```proto
// ingot_auth/methods/nickname/v1/nickname.proto
service Nickname {
  rpc SignUp(SignUpRequest) returns (SignUpResponse);
  rpc SignIn(SignInRequest) returns (SignInResponse);
  rpc Bind(BindRequest) returns (BindResponse);
}

message SignUpRequest {
  string nickname = 1;
  string password = 2;
  // the values of the attributes of the session, by their ids
  repeated ingot_auth.sessions.attrs.v1.AttrValue attr_values = 3;
}

message SignInRequest {
  string nickname = 1;
  string password = 2;
  repeated ingot_auth.sessions.attrs.v1.AttrValue attr_values = 3;
}

message BindRequest {
  string nickname = 1;
}

// each response holds the result of its flow, of the core
message SignUpResponse {
  ingot_auth.sign_up.v1.SignUpResult result = 1;
}

message SignInResponse {
  ingot_auth.sign_in.v1.SignInResult result = 1;
}

message BindResponse {
  ingot_auth.bind.v1.BindResult result = 1;
}
```

```python
result = (
    await nickname.SignIn(SignInRequest(nickname="alice", password="..."))
).result
if result.HasField("challenge"):  # her second factor
    request = AnswerSignInRequest(
        attempt_id=result.challenge.attempt_id, code=code_from_the_user
    )
    result = (await sign_in.AnswerSignIn(request)).result
token = result.signed_in.token
```
