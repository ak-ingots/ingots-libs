# ingot-auth: the email method

A part of [the methods](README.md). An email and the
[password](password.md) of the profile, of one step, as the
[nickname](nickname.md) is: the identifier is the email, normalized to NFKC,
stripped and case-folded, the same as that of the
[email_code](email-code.md) method. Not built yet.

## Stories

### 1. Signing up

| # | Actor | Story | Needs | Status |
|---|---|---|---|---|
| <a id="email-1-1"></a>1.1 | end user | **I sign up with my email and a password.**<br>• The email is checked by the group of the policies `policies_sign_up_email`, the password by that of the password, `policies_set` ([password.2.1](password.md#password-2-1)).<br>• The password proves no email, so the sign-up is of two steps: the start takes the email and the password, keeps the email and the hash of the password in the attempt and sends the code; the answer verifies the email and creates the profile ([methods.2.5](README.md#methods-2-5)). Nothing is stored before the code.<br>• The reply tells nothing of the email: a taken one answers as a free one, and its owner gets a mail "you have an account, sign in" in place of the code, as [email-code.2.1](email-code.md#email-code-2-1) tells a refusal. | [methods.3.1](README.md#methods-3-1), [methods.2.5](README.md#methods-2-5), [password.1.2](password.md#password-1-2) | Draft |

### 2. Signing in

| # | Actor | Story | Needs | Status |
|---|---|---|---|---|
| <a id="email-2-1"></a>2.1 | end user | **I sign in with my email and my password, in one step, signed up by it or having bound it.**<br>• Example: given alice signed up by nickname, her email bound ([methods.5.1](README.md#methods-5-1)), when she signs in by her email and her password, then she is in, as by her nickname.<br>• An email bound to none is verified against the hash of nothing all the same, `AuthMethodRefusedError` in both ([methods.4.2](README.md#methods-4-2)). | [methods.4.1](README.md#methods-4-1), [password.1.2](password.md#password-1-2) | Draft |

### 3. Binding

| # | Actor | Story | Needs | Status |
|---|---|---|---|---|
| <a id="email-3-1"></a>3.1 | end user | **Signed up by my nickname, I add my email to my profile, and sign in by it with my password.**<br>• The bind is that of the identifier, one for the methods of the email: verified by its code ([methods.2.5](README.md#methods-2-5)), of two steps, the same as [email-code.3.1](email-code.md#email-code-3-1), whichever service starts it.<br>• It opens a way to sign in: by the email and the password of the profile, the one the nickname has ([password.1.2](password.md#password-1-2)).<br>• With the same bind it opens the sign-in by a code to the email and the code by mail as a second factor, those of [email-code.3.1](email-code.md#email-code-3-1).<br>• Example: given alice signed up by nickname, when she binds alice@example.com and answers its code, then she signs in by alice@example.com and her password. | [methods.5.1](README.md#methods-5-1), [methods.2.5](README.md#methods-2-5), [password.1.2](password.md#password-1-2) | Draft |

## API sketch

```proto
// ingot_auth/methods/email/v1/email.proto
service Email {
  rpc SignUp(SignUpRequest) returns (SignUpResponse);
  rpc SignIn(SignInRequest) returns (SignInResponse);
}

message SignInRequest {
  string email = 1;
  string password = 2;
  // the values of the attributes of the session, by their ids
}
```

The bind of an email is by its code, of [email_code](email-code.md): one
bind for both methods, as the identifier is one.
