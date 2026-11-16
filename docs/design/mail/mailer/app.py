"""
The consumers: an application sending by SMTP, a welcome mail of its own;
its tests on the mailer in memory.
"""

import typing as t

from ingots_stub import Slot
from mail_stub import (
    AiosmtplibMailer,
    Mail,
    MailConfigs,
    MailProject,
    MailSettingsUnit,
    MailSmtpTls,
    MailUnit,
    MemoryMailer,
)


class AppConfigs(MailConfigs):
    # set by the environment in production; Mailpit in development
    MAIL_FROM = "hello@shop.example"
    MAIL_SMTP_HOST = "mailpit"
    MAIL_SMTP_PORT = 1025
    MAIL_SMTP_TLS = MailSmtpTls.NONE


class AppSettingsUnit(MailSettingsUnit):
    configs = Slot(AppConfigs)


class AppMailUnit(MailUnit):
    mailer = Slot(AiosmtplibMailer)


class AppProject(MailProject):
    settings = Slot(AppSettingsUnit)
    mail = Slot(AppMailUnit)

    async def welcome(self, email: str, name: str) -> None:
        """What an operation of the application does: builds a mail, sends it."""
        mail = Mail(to=(email,), subject="Welcome", text=f"Hello, {name}!\n")
        await self.mail.mailer.send(mail)


class TestMailUnit(MailUnit):
    mailer = Slot(MemoryMailer)


class TestProject(AppProject):
    mail = Slot(TestMailUnit)  # type: ignore[assignment]


def get_memory_mailer(project: MailProject) -> MemoryMailer:
    return t.cast(MemoryMailer, project.mail.mailer)
