# ingot-mail: the mail and its mailers

- Status: Draft
- Packages: ingot-mail
- Date: 2026-11-16
- ADRs: 0004, 0005, 0007, 0010, 0014

## Problem

An application sends mail, a welcome, a code of the sign-in, and its tests
read what it sent; a demo app sends nothing for real yet. ingot-mail gives
the interface of a mail and its mailer, one for the whole project, and its
first backend, SMTP on aiosmtplib; the other backends, the HTTP APIs of the
providers, come later beside it. It is an addon for sending mail, not for
another addon: its API is that of the mail, and it assumes nothing of how
other addons use it, which is theirs to design.

## Actors

- The author of an application: declares the mailer, configures it by the
  environment, sends a mail from an operation, reads it in the tests.
- The author of a backend: implements a mailer, runs the contract.
- An operator: sets the server of SMTP and its credentials.

## Domain

- Events: `MailSent`, the server took it; `MailRefused`, unfit to send, a
  header broken; `MailNotDelivered`, the server did not take it, transient
  or not.
- Commands: `send` of the mailer, by the code of the application. Nothing is kept: a mail sent is the server's.

## Stories

| # | Actor | Story | Now or later |
|---|---|---|---|
| 1 | author of an application | **I send a mail from an operation.**<br>• `await self.project.mail.mailer.send(Mail(to=(...,), subject=..., text=...))`; the sender is that of the mail, `sender`, else `MAIL_FROM`, by the hook `_get_sender(mail)` of the mailer.<br>• `Mail` of `ingot_mail.mail`, a frozen dataclass by keywords, plain text; its addresses and its text out of the `repr`, as it may hold a code. | now |
| 2 | author of an application | **I declare the mailer of SMTP and configure it by the environment.**<br>• `pip install "ingot-mail[aiosmtplib]"`, `mailer = Slot(AiosmtplibMailer)` in a subclass of `MailUnit`, from `ingot_mail.contrib.aiosmtplib`; the slot of the core is abstract.<br>• `MAIL_SMTP_HOST`, `_PORT`, `_USER`, `_PASSWORD` (`SecureStrConfig`), `_TLS` (`NONE`, `STARTTLS`, `TLS`, by default `STARTTLS`), `_TIMEOUT`; in the core `MailConfigs`, as the configs of the environment belong to the infrastructure addon and import nothing of the extra.<br>• A connection a mail: connect, secure, log in, send, quit. A subclass reads other configs by the hooks `_get_host()` and the rest, as the clients of ingot-pymongo. | now |
| 3 | author of an application | **My tests read what was sent.**<br>• `MemoryMailer` of `ingot_mail.contrib.memory`, no extra: `get_sent()`, the sender and the mail in their order. `python -m ingot_mail` runs with it. | now |
| 4 | author of a backend | **I prove my mailer by the contract.**<br>• `MailerContract` of `ingot_mail.testing.contracts`, its hook `get_delivered()` reading back what was delivered: a mail as sent, of any letters, several addresses, every one of several mails, from `MAIL_FROM`, a header unfit refused. The memory mailer runs it in the unit tests, aiosmtplib against Mailpit in `make integration`, reading its HTTP API. | now |
| 5 | author of an application | **I tell a failure to retry from one to give up.**<br>• `MailDeliveryError.is_transient`: no connection, a timeout, a reply 4xx, transient; 5xx, permanent. The retry is the caller's. A backend wraps the errors of its library: a caller imports none. | now |
| 6 | operator | I send a test mail from the command line, to check the configs: `mail send-test <to>`. | later |
| 7 | author of an application | A mail of HTML, a reply-to, copies, attachments: fields of `Mail` with defaults, added without a break. | later |
| 8 | author of an application | A backend of an HTTP API, Postmark, SES, ...: a contrib under its extra, the contract the same. | later |
| 9 | author of an application | A connection kept between the mails, a pool: the mailer a component, opened on start. | later |

## Rules and examples

- Rule: a mail unfit to send is refused by `send()` of the base, final,
  before any backend: no address, or a line break in the sender, an address or
  the subject, `MailHeaderError` naming the header.
  - Example: given a subject `"Hi\r\nBcc: all@b.c"`, when it is sent, then
    `MailHeaderError("subject")`, and the server sees nothing.
- Rule: the sender is the mail's, `sender`, when it tells one, else the
  mailer's, `MAIL_FROM`; a subclass of the mailer changes the choice by
  `_get_sender(mail)`.
  - Example: `MAIL_FROM = "hello@shop.example"`; a welcome tells no sender
    and is from it, a reply of the support tells `help@shop.example`.
- Rule: a failure of delivery is `MailDeliveryError`, the error of the
  library its cause.
  - Example: the server is down, `is_transient` is true; it refuses the
    address with a 550, false.

## API sketch

The prototype, [mailer/](mailer/), `make check-prototype P=docs/design/mail/mailer`.

```python
class AppConfigs(MailConfigs):  # or the environment: MAIL_SMTP_HOST=...
    ...


class AppMailUnit(MailUnit):
    mailer = Slot(AiosmtplibMailer)


class AppProject(MailProject):
    settings = Slot(AppSettingsUnit)
    mail = Slot(AppMailUnit)


mail = Mail(to=(email,), subject="Welcome", text=f"Hello, {name}!\n")
await self.project.mail.mailer.send(mail)
```

The layout of the package:

- `ingot_mail/mail/__init__.py`, `MailUnit`, the slot `mailer`;
  `mail/data.py`, `Mail`; `mail/mailers.py`, `BaseMailer`; `mail/errors.py`,
  `MailError`, `MailHeaderError`, `MailDeliveryError`.
- `ingot_mail/contrib/memory/`, `MemoryMailer`;
  `ingot_mail/contrib/aiosmtplib/`, `AiosmtplibMailer`, aiosmtplib imported at
  the top, the extra `aiosmtplib`.
- `ingot_mail/testing/contracts/`, `MailerContract`.

A class takes no prefix where its name tells the mail already, `Mail`,
`BaseMailer`, `MemoryMailer`; the configs and the units keep `Mail`.

Checked by mypy: the fields of a mail by keywords, a tuple of addresses,
`send` final and awaited, the types of the hooks. At run time: the headers,
by `send()`.

## Threats

| Category | Threat | Answer |
|---|---|---|
| Spoofing | A mail from an address the application does not own. | The sender is `MAIL_FROM`, set by the operator, or that of the mail, set by the code of the application, never taken from the data of a request; the server of SMTP refuses a sender its account may not use. SPF and DKIM are the domain's. |
| Tampering | A header injected by a line break in a subject or an address from a user, a `Bcc`. | Refused by `send()` of the base, before any backend; `EmailMessage` refuses it too. |
| Repudiation | A mail sent, none can tell. | The logger `ingot_mail` tells each mail sent, its message id, no address nor text. |
| Information disclosure | A code of the sign-in in a log, a password of SMTP in a listing of the configs. | The `repr` of `Mail` hides the addresses and the text; `MAIL_SMTP_PASSWORD` a `SecureStrConfig`; `STARTTLS` by default, `NONE` for a server of the tests alone. |
| Denial of service | A server of SMTP hanging holds the operation. | `MAIL_SMTP_TIMEOUT`, 30 seconds; a caller sends in the background where a reply must not wait. |
| Elevation of privilege | — | The mailer runs no operation and grants nothing. |

## Pre-mortem

- A connection a mail is slow under a burst of sign-ins, or the provider
  limits the connections: story 10, a component keeping one; the base takes
  no part of it.
- The contract of the mail read back from Mailpit differs from that from
  memory, its line endings, its encoding: the contract compares the text
  as decoded, its line endings as `\n`.
- `Mail` grows a field a backend cannot send: a field of a later story
  comes with its test in the contract, and a backend refuses what it
  cannot send by an error, not silently.

## Alternatives

- `smtplib` of the stdlib in a thread, `asyncio.to_thread`: no dependency,
  but a thread a mail, the timeouts and the reuse of a connection by hand;
  aiosmtplib is async by itself, a client of SMTP on asyncio, no wrapper.
- `ingot-smtp`, an addon a protocol: a mailer is the abstraction the code
  is written against, SMTP one of its backends; the name of an addon is
  that of its abstraction.
- `MAIL_SMTP_*` in the contrib, a class of configs the application joins:
  one class more to compose, for configs that import nothing.
- An API shaped for ingot-auth, a mail to one address: the addon serves
  the mail, not one of its consumers.
- An operation `op_send`, with its permission: nothing calls the mailer
  but the code of the application, which runs its own operations.

## Decisions

1. The extra is named after its library, `aiosmtplib`; an HTTP provider
   sharing `httpx` with another takes the name of the provider, `postmark`
   (the user, 2026-11-16).
2. `to` a tuple from the start: the API of the mail, whoever sends it (the
   user, 2026-11-16).

## Slices

1. ingot-mail: `Mail`, `BaseMailer`, the errors, `MAIL_FROM`, `MemoryMailer`,
   `MailerContract` run on it; `python -m ingot_mail` with it. First
   consumer: the contract.
2. ingot-mail: `AiosmtplibMailer` under its extra, `MAIL_SMTP_*`, Mailpit in
   `docker-compose.yml`, `make integration` and its job in CI, the contract
   against it; release 0.2.0.

The skeleton, the units alone, is released as 0.1.0 first, the name taken
on PyPI.
