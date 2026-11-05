# ingot-auth: the password

A part of [the methods](README.md). Not a method: the credential the
methods of one step share, [nickname](nickname.md), [email](email.md),
phone, each with its own identifier. The password is of the profile, one
whatever identifier the user signs in by.

It is normalized to NFKC and kept as its hash, by scrypt of the standard
library with the parameters of OWASP (`SCRYPT_LOG_N = 17`, `SCRYPT_R = 8`,
`SCRYPT_P = 1`); how it hashes is changed by subclassing, `_hash` and
`_verify`. Today it lives in `AuthNicknameMethod`; the methods of a
password get a base of their own, `BaseAuthPasswordMethod`, the identifier
its hook, and the password its part, `ingot_auth/methods/password/`, its
presets of the policies included ([2.1](#password-2-1)).

## Stories

### 1. The password

| # | Actor | Story | Needs | Status |
|---|---|---|---|---|
| <a id="password-1-1"></a>1.1 | application | **A password is checked by the policies I bind to it, and kept as its hash, never itself.**<br>• The slot `preset_sign_up_password` of a method, empty unless an application binds policies to it in a subclass; a policy of the password gets the identifier too, to refuse a password that is it. The slot leaves the method for the password ([2.1](#password-2-1)).<br>• A sign-in verifies against the hash; an identifier with no profile is verified against the hash of nothing all the same, so that the time of the refusal tells nothing of it ([methods.4.2](README.md#methods-4-2)). | — | Implemented |
| <a id="password-1-2"></a>1.2 | end user | **I have one password, whatever identifier I sign in by.**<br>• The secret of the password is of the uid: the method finds the profile by the identifier, then the password by the profile.<br>• Example: given alice signed up by nickname with a password, and her email bound, when she signs in by her email with that password, then she is in.<br>• Today the secret is of `(method, subject)`, the nickname. | [methods.2.4](README.md#methods-2-4) | Draft |
| <a id="password-1-3"></a>1.3 | end user | **Signed up by a code or a provider, I set a password, and the identifiers I have open the sign-in by it.** | [1.2](#password-1-2), [sessions.2.2](../sessions.md#sessions-2-2) | Draft |
| <a id="password-1-4"></a>1.4 | end user | **I change my password, giving the old one.**<br>• The new one checked by `preset_change` ([2.2](#password-2-2)). | [1.2](#password-1-2), [sessions.2.2](../sessions.md#sessions-2-2) | Draft |
| <a id="password-1-5"></a>1.5 | end user | **A sign-in asks me to change a password too old, or one the policies of today refuse, before it opens the session.**<br>• Not to shut out: a challenge that is not of a method, of the flow, as a factor is.<br>• The new one checked by `preset_renew`, the minimum age ignored ([2.3](#password-2-3)). | [1.4](#password-1-4), [factors.1.1](factors.md#factors-1-1) | Draft |

### 2. Its policies

| # | Actor | Story | Needs | Status |
|---|---|---|---|---|
| <a id="password-2-1"></a>2.1 | application | **I bind the policies of the password once, for every method it is set by, a preset a point of a flow whose context differs.**<br>• Of the password, not of a method: the password is of the profile ([1.2](#password-1-2)), so a sign-up by nickname and one by email check it alike. The slot `preset_sign_up_password` leaves the nickname method for the part of the password, `ingot_auth/methods/password/` (the user, 2026-11-05: "в никнейме этому точно не место"). The policies of an identifier stay with it, `preset_sign_up_nickname`.<br>• A preset a context, not an operation: `preset_set`, a new password given, at a sign-up by any method of a password, at setting one ([1.3](#password-1-3)), at a change; its context the value and the identifiers, to refuse a password that is one of them. `preset_change` ([2.2](#password-2-2)) and `preset_renew` ([2.3](#password-2-3)) take wider contexts.<br>• A policy takes the parts of a context its protocol tells: mypy refuses to bind the minimum age or the history to `preset_set`, whose context has neither, so what is checked only on a change is so by the types.<br>• The presets of the core are empty, as all are; an application or a starter binds the policies in a subclass. A policy switched by an environment reads a config of the password, `AuthPasswordConfigs`, mixed in as those of a method ([methods.1.1](README.md#methods-1-1)), in the preset of the application: no flag `enabled` of a policy, a policy unbound is not there.<br>• Example: given `preset_set` with a length of 12, when alice signs up by nickname, or by email, with `secret`, then `AuthMethodInvalidError` names the field `password`. | [1.2](#password-1-2) | Draft |
| <a id="password-2-2"></a>2.2 | end user | **I change my password: the new one is checked as any new one, not before the minimum age since the last change, and not one of my last ones.**<br>• `preset_change`: the bindings of `preset_set` first, then its own, the minimum age and the history; its context adds the time of the last change and the hashes of the passwords before. A binding of `preset_set` takes the value and the identifiers, which the context of a change has too, so they are declared once.<br>• The history keeps the hashes to the depth its config tells; a candidate is verified against each, a hash each, the depth small. | [1.4](#password-1-4), [2.1](#password-2-1) | Draft |
| <a id="password-2-3"></a>2.3 | end user | **A sign-in asks me to renew a password the policies of today refuse, and I renew it whatever the minimum age.**<br>• Once the password verified, the sign-in checks it by `preset_set`: refused, the sign-in is not, the flow asks to renew it, as a password too old ([1.5](#password-1-5)).<br>• `preset_renew`: as a change, but the minimum age, as a forced change ignores it (the user, 2026-11-05): a policy strengthened, a user who changed the password yesterday by the old rules changes it today all the same. The history stays: no going back to a recent one.<br>• Example: given the length raised from 8 to 12, and alice's password of 10 changed an hour ago, with a minimum age of a day, when she signs in, then she is asked a new one, and the minimum age does not stop her. | [1.5](#password-1-5), [2.2](#password-2-2) | Draft |

## API sketch

The application (stories [2.1](#password-2-1)–[2.3](#password-2-3)), the
presets of the password in a subclass of its part, the policies of a
password in the registry:

```python
class AppPasswordSetPreset(AuthPasswordSetPreset):
    @t.override
    def _get_bindings(self) -> dict[str, AuthPolicyBinding[AuthPasswordSetContext, t.Any]]:
        bindings = super()._get_bindings()
        bindings["length"] = AuthLengthPolicy.bind(AuthLengthConfig(min=12))
        return bindings

class AppPasswordChangePreset(AuthPasswordChangePreset):  # those of set, then its own
    @t.override
    def _get_bindings(self) -> dict[str, AuthPolicyBinding[AuthPasswordChangeContext, t.Any]]:
        bindings = super()._get_bindings()
        bindings["min_age"] = AuthPasswordMinAgePolicy.bind(AuthPasswordMinAgeConfig(days=1))
        depth = self.project.settings.configs.AUTH_PASSWORD_HISTORY
        if depth:  # switched by the environment
            bindings["history"] = AuthPasswordHistoryPolicy.bind(AuthPasswordHistoryConfig(depth=depth))
        return bindings

class AppPassword(AuthPassword):
    preset_set = Slot(AppPasswordSetPreset)
    preset_change = Slot(AppPasswordChangePreset)
    preset_renew = Slot(AppPasswordRenewPreset)  # as the change, with no min_age

class AppPolicies(AuthPolicies):
    min_age = Slot(AuthPasswordMinAgePolicy)
    history = Slot(AuthPasswordHistoryPolicy)
```

In the core, `ingot_auth/methods/password/`: `AuthPassword`, its presets
and their contexts, the hash, the policies of the minimum age and of the
history, which need what the password keeps, and `AuthPasswordConfigs`.

## Threats

| Category | Threat | Answer |
|---|---|---|
| Spoofing | Guessing a password over many sign-ins. | A sign-in by a password is one step, no attempt, so no limit of failures: only the ban of an identifier after its failures ([methods.4.3](README.md#methods-4-3)) and a second factor stop it; a gap until then. |
| Denial of service | scrypt burning the CPU on a flood of sign-ins. | Of the infrastructure in front, a cloud, a balancer ([auth](../README.md#how-to-read-it)). |
