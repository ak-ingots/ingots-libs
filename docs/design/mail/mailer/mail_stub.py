"""
What ingot-mail would give: the mail, the mailer and its errors in the core,
the mailer in memory, the mailer of SMTP on aiosmtplib, its library faked by
a server that keeps what it is sent.
"""

import abc
import enum
import typing as t
from dataclasses import dataclass, field

from ingots_stub import Configs, Entity, Project, SettingsUnit, Slot, Unit

# ingot_mail/settings/configs.py


class MailSmtpTls(enum.Enum):
    """How a connection to a server of SMTP is secured."""

    NONE = enum.auto()  # a server of the tests, Mailpit
    STARTTLS = enum.auto()  # the submission port, 587
    TLS = enum.auto()  # implicit, the port 465


class MailConfigs(Configs):
    MAIL_FROM: str = "noreply@localhost"
    MAIL_SMTP_HOST: str = "localhost"
    MAIL_SMTP_PORT: int = 587
    MAIL_SMTP_USER: str = ""  # empty: no authentication
    MAIL_SMTP_PASSWORD: str = ""  # SecureStrConfig
    MAIL_SMTP_TLS: MailSmtpTls = MailSmtpTls.STARTTLS
    MAIL_SMTP_TIMEOUT: float = 30.0  # seconds


class MailSettingsUnit(SettingsUnit):
    configs = Slot(MailConfigs)


# ingot_mail/mail/data.py


@dataclass(frozen=True, slots=True, kw_only=True)
class Mail:
    """
    A mail to send, of plain text: its addresses and its text stay out of
    the ``repr``, as the text may hold a code.
    """

    to: tuple[str, ...] = field(repr=False)
    subject: str
    text: str = field(repr=False)
    sender: str | None = None  # None: the mailer's, MAIL_FROM


# ingot_mail/mail/errors.py


class MailError(Exception):
    """An error of the mail."""


class MailHeaderError(MailError, ValueError):
    """A mail refused before sending: no address, or a line break in a header."""

    @classmethod
    def create(cls, name: str) -> t.Self:
        return cls(f"a header unfit to send: {name}", name)

    @property
    def name(self) -> str:
        return t.cast(str, self.args[1])


class MailDeliveryError(MailError):
    """
    A mail the server did not take; transient when sending it again later
    may succeed: no connection, a timeout, a reply of SMTP 4xx.
    """

    @classmethod
    def create(cls, reason: str, *, is_transient: bool) -> t.Self:
        return cls(f"a mail not delivered: {reason}", reason, is_transient)

    @property
    def is_transient(self) -> bool:
        return t.cast(bool, self.args[2])


# ingot_mail/mail/mailers.py


class BaseMailer(Entity):
    """
    The mailer, the slot ``mailer`` of the mail, abstract: what a backend
    implements. Refuses a mail unfit to send before the backend sees it.
    """

    project: "MailProject"

    @t.final
    async def send(self, mail: Mail) -> None:
        """
        Delivers a mail from the sender of the mailer.

        :raises MailHeaderError: no address, a line break in a header.
        :raises MailDeliveryError: the server did not take it.
        """
        if not mail.to:
            raise MailHeaderError.create("to")
        sender = self._get_sender(mail)
        for name, value in (
            ("sender", sender),
            ("to", ", ".join(mail.to)),
            ("subject", mail.subject),
        ):
            if "\r" in value or "\n" in value:
                raise MailHeaderError.create(name)
        await self._send(mail, sender)

    def _get_sender(self, mail: Mail) -> str:
        """The address the mail is from: its own, else ``MAIL_FROM``."""
        if mail.sender is not None:
            return mail.sender
        return self.project.settings.configs.MAIL_FROM

    @abc.abstractmethod
    async def _send(self, mail: Mail, sender: str) -> None:
        raise NotImplementedError


# ingot_mail/mail/__init__.py


class MailUnit(Unit):
    """The mail of the project: the mailer, which the application declares."""

    mailer = Slot(BaseMailer)  # type: ignore[type-abstract]


# ingot_mail/project.py


class MailProject(Project):
    settings = Slot(MailSettingsUnit)
    mail = Slot(MailUnit)


# ingot_mail/contrib/memory/__init__.py


class MemoryMailer(BaseMailer):
    """Delivers nothing: keeps the mail, in its order, for the tests to read."""

    def __init__(self) -> None:
        super().__init__()
        self._sent: list[tuple[str, Mail]] = []

    @t.final
    def get_sent(self) -> tuple[tuple[str, Mail], ...]:
        """The mail sent so far with its sender, in its order."""
        return tuple(self._sent)

    @t.override
    async def _send(self, mail: Mail, sender: str) -> None:
        self._sent.append((sender, mail))


# a fake of aiosmtplib.send: the server of SMTP keeping what it takes

SERVER: list[dict[str, t.Any]] = []
SERVER_DOWN: list[bool] = []


async def aiosmtplib_send(message: dict[str, str], **options: t.Any) -> None:
    if SERVER_DOWN:
        raise ConnectionError("SMTPConnectError")
    SERVER.append({"message": message, **options})


# ingot_mail/contrib/aiosmtplib/__init__.py, the extra aiosmtplib


class AiosmtplibMailer(BaseMailer):
    """
    Sends a mail by SMTP, a connection a mail, configured by ``MAIL_SMTP_*``;
    a subclass reads other configs by the hooks.
    """

    @t.override
    async def _send(self, mail: Mail, sender: str) -> None:
        # email.message.EmailMessage in the real one
        message = {
            "From": sender,
            "To": ", ".join(mail.to),
            "Subject": mail.subject,
            "body": mail.text,
        }
        tls = self._get_tls()
        try:
            await aiosmtplib_send(
                message,
                hostname=self._get_host(),
                port=self._get_port(),
                username=self._get_user() or None,
                password=self._get_password() or None,
                use_tls=tls is MailSmtpTls.TLS,
                start_tls=tls is MailSmtpTls.STARTTLS,
                timeout=self._get_timeout(),
            )
        except ConnectionError as error:  # aiosmtplib.SMTPException
            raise MailDeliveryError.create(str(error), is_transient=True) from error

    def _get_host(self) -> str:
        return self.project.settings.configs.MAIL_SMTP_HOST

    def _get_port(self) -> int:
        return self.project.settings.configs.MAIL_SMTP_PORT

    def _get_user(self) -> str:
        return self.project.settings.configs.MAIL_SMTP_USER

    def _get_password(self) -> str:
        return self.project.settings.configs.MAIL_SMTP_PASSWORD

    def _get_tls(self) -> MailSmtpTls:
        return self.project.settings.configs.MAIL_SMTP_TLS

    def _get_timeout(self) -> float:
        return self.project.settings.configs.MAIL_SMTP_TIMEOUT
