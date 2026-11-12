# ingot-auth: the password

A part of [the methods](README.md). Not a method: the credential the
methods of one step share, [nickname](nickname.md), [email](email.md),
phone, each with its own identifier. The password is of the profile, one
whatever identifier the user signs in by.

It is normalized to NFKC and kept as its hash, by scrypt of the standard
library with the parameters of OWASP (`SCRYPT_LOG_N = 17`, `SCRYPT_R = 8`,
`SCRYPT_P = 1`); how it hashes is changed by subclassing, `_hash` and
`_verify`. It lives in its part, `AuthPassword` of
`ingot_auth/methods/password/`, the slot `password` of the methods, its
groups of the policies included ([2.1](#password-2-1)); the methods of a
password may get a base of their own, `BaseAuthPasswordMethod`, the
identifier its hook, with the second of them, [email](email.md).

## Stories

### 1. The password

| # | Actor | Story | Needs | Status |
|---|---|---|---|---|
| <a id="password-1-1"></a>1.1 | application | **A password is checked by the policies I give to it, and kept as its hash, never itself.**<br>• The group of the policies of a new password, empty unless an application gives policies to it in a subclass; a policy of the password gets the identifiers too, to refuse a password that is one. Of the password, not of a method ([2.1](#password-2-1)).<br>• A sign-in verifies against the hash; an identifier with no profile is verified against the hash of nothing all the same, so that the time of the refusal tells nothing of it ([methods.4.2](README.md#methods-4-2)). | — | Implemented |
| <a id="password-1-2"></a>1.2 | end user | **I have one password, whatever identifier I sign in by.**<br>• The secret of the password is of the uid: the method finds the profile by the identifier, then the password by the profile.<br>• Example: given alice signed up by nickname with a password, and her email bound, when she signs in by her email with that password, then she is in. | [methods.2.4](README.md#methods-2-4) | Implemented |
| <a id="password-1-3"></a>1.3 | end user | **Signed up by a code or a provider, I set a password, and the identifiers I have open the sign-in by it.** | [1.2](#password-1-2), [sessions.2.2](../sessions.md#sessions-2-2) | Draft |
| <a id="password-1-4"></a>1.4 | end user | **I change my password, giving the old one.**<br>• The new one checked by `policies_change` ([2.2](#password-2-2)). | [1.2](#password-1-2), [sessions.2.2](../sessions.md#sessions-2-2) | Draft |
| <a id="password-1-5"></a>1.5 | end user | **A sign-in asks me to change a password too old, or one the policies of today refuse, before it opens the session.**<br>• Not to shut out: a challenge that is not of a method, of the flow, as a factor is.<br>• The new one checked by `policies_renew`, the minimum age ignored ([2.3](#password-2-3)). | [1.4](#password-1-4), [factors.1.1](factors.md#factors-1-1) | Draft |

### 2. Its policies

| # | Actor | Story | Needs | Status |
|---|---|---|---|---|
| <a id="password-2-1"></a>2.1 | application | **I give the policies of the password once, for every method it is set by, a group a point of a flow whose parameters differ.**<br>• Of the password, not of a method: the password is of the profile ([1.2](#password-1-2)), so a sign-up by nickname and one by email check it alike. The slot `preset_sign_up_password` left the nickname method for the part of the password, `ingot_auth/methods/password/` (the user, 2026-11-05: "в никнейме этому точно не место"). The policies of an identifier stay with it, `policies_sign_up_nickname`.<br>• A policy is an operation, not a check of a value alone (the user, 2026-11-11): the minimum age reads the age of the password, the history its hashes before, and an operation may run others. It raises `AuthPolicyViolationError` with its name when the value breaks it, and requires nothing of the caller, `Permissions()`, run by the flow that checked its caller. No registry of the policies, no bindings: a group is created anew on every run, as an operation is.<br>• A group a point of a flow: `policies_set`, a new password given, at a sign-up by any method of a password, at setting one ([1.3](#password-1-3)), at a change; its parameters the value and the identifiers, to refuse a password that is one of them. `policies_change` ([2.2](#password-2-2)) and `policies_renew` ([2.3](#password-2-3)) take wider parameters.<br>• A group is a `Factories` of ingots, its type given by the core, `AuthPasswordSetPolicies`: a policy takes the parts of the parameters its protocol tells, so mypy refuses the minimum age or the history in `policies_set`, whose parameters have neither, and what is checked only on a change is so by the types.<br>• The group runs together, `run_group` of ingots: the caller checked for every policy before any runs, each to its end, so that a client learns every policy broken at once; `AuthMethodInvalidError` names the field and each, in the order of the group.<br>• The groups of the core are empty, as all are; an application or a starter gives the policies in a subclass. A policy of the core is configured by the `CONFIG` of its class, a subclass replacing it: no flag `enabled` of a policy, a policy not in the group is not there.<br>• Example: given `policies_set` with a length of 12, when alice signs up by nickname, or by email, with `secret`, then `AuthMethodInvalidError` names the field `password` and the policy `length`. | [1.2](#password-1-2) | Implemented |
| <a id="password-2-2"></a>2.2 | end user | **I change my password: the new one is checked as any new one, not before the minimum age since the last change, and not one of my last ones.**<br>• `policies_change`: the policies of `policies_set` first, then its own, the minimum age and the history, which read what the password keeps by the uid of its parameters. A policy of `policies_set` takes the value and the identifiers, which the parameters of a change have too, so the group of a change declares them again from those of `policies_set`, as a subclass declares a group from its base.<br>• The history keeps the hashes to the depth its config tells; a candidate is verified against each, a hash each, the depth small.<br>• A policy switched by an environment is switched by a config (the user, 2026-11-12: "конфигом!"). The core gives a group no policy; an application gives those its business asks for, and one it switches without code reads a config of its own and passes when it is off, returning before `super()._run()`, the group declared in the class all the same. A toggle of the core may come later, with the policies of the core it would switch. | [1.4](#password-1-4), [2.1](#password-2-1) | Draft |
| <a id="password-2-3"></a>2.3 | end user | **A sign-in asks me to renew a password the policies of today refuse, and I renew it whatever the minimum age.**<br>• Once the password verified, the sign-in checks it by `policies_set`: refused, the sign-in is not, the flow asks to renew it, as a password too old ([1.5](#password-1-5)).<br>• `policies_renew`: as a change, but the minimum age, as a forced change ignores it (the user, 2026-11-05): a policy strengthened, a user who changed the password yesterday by the old rules changes it today all the same. The history stays: no going back to a recent one.<br>• Example: given the length raised from 8 to 12, and alice's password of 10 changed an hour ago, with a minimum age of a day, when she signs in, then she is asked a new one, and the minimum age does not stop her. | [1.5](#password-1-5), [2.2](#password-2-2) | Draft |

## API sketch

The application (stories [2.1](#password-2-1)–[2.3](#password-2-3)), the
policies of the password, each an operation, in the groups of its part:

```python
class AppPasswordLength(AuthLengthPolicy):
    CONFIG = AuthLengthConfig(min=12)

class AppPasswordMinAge(AuthPasswordMinAgePolicy):
    CONFIG = AuthPasswordMinAgeConfig(days=1)

class AppPassword(AuthPassword):
    policies_set = AuthPasswordSetPolicies(AppPasswordLength)
    # those of set, then its own
    policies_change = AuthPasswordChangePolicies(
        *policies_set.classes, AppPasswordMinAge, AuthPasswordHistoryPolicy
    )
    # as the change, with no minimum age
    policies_renew = AuthPasswordChangePolicies(
        *policies_set.classes, AuthPasswordHistoryPolicy
    )
```

A policy of its own, of the parts its protocol tells:

```python
class HasValueAndIdentifiers(AuthHasValue, AuthHasIdentifiers, t.Protocol): ...

class AppNoIdentifierPolicy(BaseOperation[HasValueAndIdentifiers, None]):
    PERMISSIONS = Permissions()

    @t.override
    async def _run(
        self, parameters: HasValueAndIdentifiers, metadata: OperationMetadata
    ) -> None:
        if any(i in parameters.value for i in parameters.identifiers):
            raise AuthPolicyViolationError.for_policy("identifier")
```

In the core, `ingot_auth/methods/password/`: `AuthPassword`, the parameters
of its groups and their types, the hash, the policies of the minimum age
and of the history, which read what the password keeps.

## Threats

| Category | Threat | Answer |
|---|---|---|
| Spoofing | Guessing a password over many sign-ins. | A sign-in by a password is one step, no attempt, so no limit of failures: only the ban of an identifier after its failures ([methods.4.3](README.md#methods-4-3)) and a second factor stop it; a gap until then. |
| Denial of service | scrypt burning the CPU on a flood of sign-ins. | Of the infrastructure in front, a cloud, a balancer ([auth](../README.md#how-to-read-it)). |
