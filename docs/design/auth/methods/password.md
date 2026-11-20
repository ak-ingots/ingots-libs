# ingot-auth: the password

A part of [the methods](README.md). Not a method: the credential the
methods of one step share, [nickname](nickname.md), [email](email.md),
phone, each with its own identifier. The password is of the profile, one
whatever identifier the user signs in by.

It is normalized to NFKC and kept as its hash, by the strategy in the slot
`hasher` ([1.6](#password-1-6)): scrypt of the standard library with the
parameters of OWASP by default, the hash in the PHC format naming its
algorithm and its parameters. It lives in its part, `AuthPassword` of
`ingot_auth/methods/password/`, the slot `password` of the methods, its
groups of the policies included ([2.1](#password-2-1)); the methods of a
password may get a base of their own, `BaseAuthPasswordMethod`, the
identifier its hook, with the second of them, [email](email.md).

## Stories

### 1. The password

| # | Actor | Story | Needs | Status | Coverage |
|---|---|---|---|---|---|
| <a id="password-1-1"></a>1.1 | application | **A password is checked by the policies I give to it, and kept as its hash, never itself.**<br>• The group of the policies of a new password, empty unless an application gives policies to it in a subclass; a policy of the password gets the identifiers too, to refuse a password that is one. Of the password, not of a method ([2.1](#password-2-1)).<br>• A sign-in verifies against the hash; an identifier with no profile is verified against the hash of nothing all the same, so that the time of the refusal tells nothing of it ([methods.4.2](README.md#methods-4-2)). | — | Implemented | unit |
| <a id="password-1-2"></a>1.2 | end user | **I have one password, whatever identifier I sign in by.**<br>• The secret of the password is of the uid: the method finds the profile by the identifier, then the password by the profile.<br>• Example: given alice signed up by nickname with a password, and her email bound, when she signs in by her email with that password, then she is in. | [methods.2.4](README.md#methods-2-4) | Implemented | unit: the game binds no method of an email and a password |
| <a id="password-1-3"></a>1.3 | end user | **Signed up by a code or a provider, I set a password, and the identifiers I have open the sign-in by it.** | [1.2](#password-1-2), [sessions.2.2](../sessions.md#sessions-2-2) | Draft | — |
| <a id="password-1-4"></a>1.4 | end user | **I change my password, giving the old one.**<br>• The new one checked by `policies_change` ([2.2](#password-2-2)).<br>• In a session only, the old password verified at the change itself, whatever the session: the proof a change takes, as OWASP asks of a change of a password, so no fresh proof of the session is needed besides ([sessions.4.1](../sessions.md#sessions-4-1)).<br>• The other sessions of the profile are closed, this one kept, as after a stolen password the thief's are the others; the closes recorded as a revoke of the user ([activity.2.2](../activity.md#activity-2-2)).<br>• The user is told by mail, the password never in it ([sessions.3.8](../sessions.md#sessions-3-8)). | [1.2](#password-1-2), [sessions.2.2](../sessions.md#sessions-2-2) | Draft | — |
| <a id="password-1-5"></a>1.5 | end user | **A sign-in asks me to change a password too old, or one the policies of today refuse, before it opens the session.**<br>• Not to shut out: a challenge that is not of a method, of the flow, as a factor is.<br>• The new one checked by `policies_renew`, the minimum age ignored ([2.3](#password-2-3)). | [1.4](#password-1-4), [factors.1.1](factors.md#factors-1-1) | Draft | — |
| <a id="password-1-6"></a>1.6 | application | **I pick how a password is hashed, a hasher of the core, and its cost by configs, tuned to my servers; a sign-in rehashes a hash of another hasher or cost.**<br>• The slot `hasher` of `AuthPassword`, its default complete: `PasswordHasher`, scrypt with the parameters of OWASP at their highest, `N = 2 ** 17`, `r = 8`, `p = 1`, 128 MiB a hash; `Pbkdf2PasswordHasher`, PBKDF2-HMAC-SHA256 of 600 000 iterations, for where FIPS-140 is required, cheap on a GPU otherwise. Argon2id, first of OWASP, is not of the standard library: an extra, if ever asked for.<br>• The cost by configs, `AUTH_PASSWORD_SCRYPT_LOG_N`, `_R`, `_P`, `AUTH_PASSWORD_PBKDF2_ITERATIONS`, the highest by default (the user, 2026-11-20): an operator tunes them to the servers without a release, and a stand of the load sets them as it sets the floor of the timing. The guide gives the settings of OWASP of a like defence, less memory paid by more parallelism, 2¹⁴ and `p = 5` half the CPU of the default on the dev server ([the trial](#the-cost-of-a-hash)).<br>• A hash keeps its algorithm and its parameters: a hash of another hasher or cost still verifies, and a sign-in that verified it hashes the password again by those of today, in its transaction, as OWASP upgrades a work factor; `needs_rehash` of the hasher tells. One that never signs in keeps the old hash.<br>• Example: given the cost lowered to 2¹⁴ and `p = 5`, when alice, hashed by 2¹⁷, signs in, then she is in, and her hash is of 2¹⁴ after. | [1.1](#password-1-1) | Draft | unit; the cost by the load |

### 2. Its policies

| # | Actor | Story | Needs | Status | Coverage |
|---|---|---|---|---|---|
| <a id="password-2-1"></a>2.1 | application | **I give the policies of the password once, for every method it is set by, a group a point of a flow whose parameters differ.**<br>• Of the password, not of a method: the password is of the profile ([1.2](#password-1-2)), so a sign-up by nickname and one by email check it alike. The slot `preset_sign_up_password` left the nickname method for the part of the password, `ingot_auth/methods/password/` (the user, 2026-11-05: "в никнейме этому точно не место"). The policies of an identifier stay with it, `policies_sign_up_nickname`.<br>• A policy is an operation, not a check of a value alone (the user, 2026-11-11): the minimum age reads the age of the password, the history its hashes before, and an operation may run others. It raises `AuthPolicyViolationError` with its name when the value breaks it, and requires nothing of the caller, `Permissions()`, run by the flow that checked its caller. No registry of the policies, no bindings: a group is created anew on every run, as an operation is.<br>• A group a point of a flow: `policies_set`, a new password given, at a sign-up by any method of a password, at setting one ([1.3](#password-1-3)), at a change; its parameters the value and the identifiers, to refuse a password that is one of them. `policies_change` ([2.2](#password-2-2)) and `policies_renew` ([2.3](#password-2-3)) take wider parameters.<br>• A group is a `Factories` of ingots, its type given by the core, `AuthPasswordSetPolicies`: a policy takes the parts of the parameters its protocol tells, so mypy refuses the minimum age or the history in `policies_set`, whose parameters have neither, and what is checked only on a change is so by the types.<br>• The group runs together, `run_group` of ingots: the caller checked for every policy before any runs, each to its end, so that a client learns every policy broken at once; `AuthMethodInvalidError` names the field and each, in the order of the group.<br>• The groups of the core are empty, as all are; an application or a starter gives the policies in a subclass. A policy of the core is configured by the `CONFIG` of its class, a subclass replacing it: no flag `enabled` of a policy, a policy not in the group is not there.<br>• Example: given `policies_set` with a length of 12, when alice signs up by nickname, or by email, with `secret`, then `AuthMethodInvalidError` names the field `password` and the policy `length`. | [1.2](#password-1-2) | Implemented | unit |
| <a id="password-2-2"></a>2.2 | end user | **I change my password: the new one is checked as any new one, not before the minimum age since the last change, and not one of my last ones.**<br>• `policies_change`: the policies of `policies_set` first, then its own, the minimum age and the history, which read what the password keeps by the uid of its parameters. A policy of `policies_set` takes the value and the identifiers, which the parameters of a change have too, so the group of a change declares them again from those of `policies_set`, as a subclass declares a group from its base.<br>• The history keeps the hashes to the depth its config tells; a candidate is verified against each, a hash each, the depth small.<br>• A policy switched by an environment is switched by a config (the user, 2026-11-12: "конфигом!"). The core gives a group no policy; an application gives those its business asks for, and one it switches without code reads a config of its own and passes when it is off, returning before `super()._run()`, the group declared in the class all the same. A toggle of the core may come later, with the policies of the core it would switch. | [1.4](#password-1-4), [2.1](#password-2-1) | Draft | — |
| <a id="password-2-3"></a>2.3 | end user | **A sign-in asks me to renew a password the policies of today refuse, and I renew it whatever the minimum age.**<br>• Once the password verified, the sign-in checks it by `policies_set`: refused, the sign-in is not, the flow asks to renew it, as a password too old ([1.5](#password-1-5)).<br>• `policies_renew`: as a change, but the minimum age, as a forced change ignores it (the user, 2026-11-05): a policy strengthened, a user who changed the password yesterday by the old rules changes it today all the same. The history stays: no going back to a recent one.<br>• Example: given the length raised from 8 to 12, and alice's password of 10 changed an hour ago, with a minimum age of a day, when she signs in, then she is asked a new one, and the minimum age does not stop her. | [1.5](#password-1-5), [2.2](#password-2-2) | Draft | — |
| <a id="password-2-4"></a>2.4 | application | **The core gives the usual policies of a password, those of OWASP, so that I pick rather than write them.**<br>• The length, `AuthLengthPolicy` of the core: 8 at least with a second factor, 15 without, as OWASP and NIST say, a starter picking ([auth.1.3](../README.md#auth-1-3)); 64 at most at least, so that a passphrase fits, and a ceiling the hash is not flooded by, never cut silently.<br>• No rule of composition, digits, cases, symbols: OWASP and NIST advise against them, an application writes its own if its business asks.<br>• A leaked password refused, `AuthPwnedPolicy`, by the range of Pwned Passwords, k-anonymity, the first five characters of its SHA-1 sent: an extra, a call over the network, what it does when the service is down a config of its own, open by default.<br>• The strength meter is of the client. | [2.1](#password-2-1) | Draft | unit |

### 3. Its recovery

| # | Actor | Story | Needs | Status | Coverage |
|---|---|---|---|---|---|
| <a id="password-3-1"></a>3.1 | end user | **I forgot my password: a code sent to my email lets me set a new one.**<br>• The start by an identifier replies the same, at the same time, whether it is bound or not, as a sign-in does ([methods.4.2](README.md#methods-4-2)): the code by mail of the methods, of `CODE_LENGTH` digits, single use, short-lived, its answers limited by `AUTH_ATTEMPT_MAX_FAILURES`; a new code drops the old one.<br>• The requests of a profile are limited, its mailbox not flooded; a ban of the sign-in ([methods.4.3](README.md#methods-4-3)) does not close the recovery, or a ban would shut its owner out.<br>• The new password checked by `policies_set`; no sign-in after it, the user signs in as always; every session of the profile closed, every code of a recovery outstanding dropped; the user told by mail ([sessions.3.8](../sessions.md#sessions-3-8)).<br>• A profile with a second factor answers it too before the new password ([factors.1.1](factors.md#factors-1-1)), or a code of recovery ([factors.1.4](factors.md#factors-1-4)).<br>• Example: given alice with her email bound, when she asks for a recovery by it, answers the code and gives a new password, then her sessions are closed, she signs in by the new one, and a mail tells her. | [1.2](#password-1-2), [methods.2.4](README.md#methods-2-4) | Draft | — |

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
| Spoofing | The storage leaked: its hashes cracked offline. | A memory-hard hash at the minimum of OWASP at least ([1.6](#password-1-6)); a leaked password refused at its set ([2.4](#password-2-4)). |
| Spoofing | Taking a profile over by its recovery. | A code to an identifier verified as the user's; the second factor asked too; every session closed after; the user told ([3.1](#password-3-1)). |
| Denial of service | scrypt burning the CPU on a flood of sign-ins. | Of the infrastructure in front, a cloud, a balancer ([auth](../README.md#how-to-read-it)); a cost tuned to the servers ([1.6](#password-1-6)). |
| Denial of service | A password of megabytes hashed. | A ceiling of the length ([2.4](#password-2-4)). |

## The cost of a hash

A trial of the load on the dev server (Ryzen 5 5500U, its L3 of 8 MiB;
2026-11-20; a round, the host busy), a sign-in of the game against
ingot-auth 0.9.0, scrypt 2¹⁷, `p = 1`:

| scrypt | Memory | CPU a sign-in | Sign-ins a second, 8 groups |
|---|---|---|---|
| 2¹⁷, `p = 1`, the default | 128 MiB | 1.24–1.37 s | 3.3 |
| 2¹⁶, `p = 2` | 64 MiB | −10…15% | 4.0 |
| 2¹⁵, `p = 3` | 32 MiB | −42% | 5.6 |
| 2¹⁴, `p = 5` | 16 MiB | −56% | 7.4 |
| 2¹⁴, `p = 1`, below OWASP | 16 MiB | −90% | 34.4 |
| PBKDF2, 600 000 | — | −65% | 9.6 |

The settings of OWASP of a like defence cost less than their arithmetic,
`N·p`, says: a smaller table fits the caches better, by how much depending
on the server.
