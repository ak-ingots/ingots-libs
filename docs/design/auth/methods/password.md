# ingot-auth: the password

A part of [the methods](README.md). Not a method: the credential the
methods of one step share, [nickname](nickname.md), [email](email.md),
phone, each with its own identifier. The password is of the profile, one
whatever identifier the user signs in by.

It is normalized to NFKC and kept as its hash, by scrypt of the standard
library with the parameters of OWASP (`SCRYPT_LOG_N = 17`, `SCRYPT_R = 8`,
`SCRYPT_P = 1`); how it hashes is changed by subclassing, `_hash` and
`_verify`. Today it lives in `AuthPasswordMethod`, the `nickname` method to
be; the methods of a password get a base of their own,
`BaseAuthPasswordMethod`, the identifier its hook.

## Stories

| # | Actor | Story | Needs | Status |
|---|---|---|---|---|
| <a id="password-1-1"></a>1.1 | application | **A password is checked by the policies I bind to it, and kept as its hash, never itself.**<br>• The slot `preset_sign_up_password` of a method, empty unless an application binds policies to it in a subclass; a policy of the password gets the identifier too, to refuse a password that is it.<br>• A sign-in verifies against the hash; an identifier with no profile is verified against the hash of nothing all the same, so that the time of the refusal tells nothing of it ([methods.4.2](README.md#methods-4-2)). | — | Implemented |
| <a id="password-1-2"></a>1.2 | end user | **I have one password, whatever identifier I sign in by.**<br>• The secret of the password is of the uid: the method finds the profile by the identifier, then the password by the profile.<br>• Example: given alice signed up by nickname with a password, and her email bound, when she signs in by her email with that password, then she is in.<br>• Today the secret is of `(method, subject)`, the nickname. | [methods.2.4](README.md#methods-2-4) | Draft |
| <a id="password-1-3"></a>1.3 | end user | **Signed up by a code or a provider, I set a password, and the identifiers I have open the sign-in by it.** | [1.2](#password-1-2), [sessions.2.2](../sessions.md#sessions-2-2) | Draft |
| <a id="password-1-4"></a>1.4 | end user | **I change my password, giving the old one.** | [1.2](#password-1-2), [sessions.2.2](../sessions.md#sessions-2-2) | Draft |
| <a id="password-1-5"></a>1.5 | end user | **A sign-in asks me to change a password too old before it opens the session.**<br>• Not to shut out: a challenge that is not of a method, of the flow, as a factor is. | [1.4](#password-1-4), [factors.1.1](factors.md#factors-1-1) | Draft |

## Threats

| Category | Threat | Answer |
|---|---|---|
| Spoofing | Guessing a password over many sign-ins. | A sign-in by a password is one step, no attempt, so no limit of failures: only the ban of an identifier after its failures ([methods.4.3](README.md#methods-4-3)) and a second factor stop it; a gap until then. |
| Denial of service | scrypt burning the CPU on a flood of sign-ins. | Of the infrastructure in front, a cloud, a balancer ([auth](../README.md#how-to-read-it)). |
