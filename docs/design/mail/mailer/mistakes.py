"""The lines mypy refuses: what a consumer cannot get wrong."""

import typing as t

from mail_stub import AiosmtplibMailer, BaseMailer, Mail, MailUnit


async def send(unit: MailUnit) -> None:
    Mail(to="al@b.c", subject="Hi", text="")  # error: addresses a tuple
    Mail(to=("al@b.c",), subject="Hi")  # error: no text
    Mail(("al@b.c",), "Hi", "")  # error: by keywords
    unit.mailer.send(Mail(to=("al@b.c",), subject="Hi", text=""))  # error: not awaited


class Mailer(BaseMailer):
    async def send(self, mail: Mail) -> None:  # error: send is final
        pass

    @t.override
    async def _send(self, mail: Mail, sender: str) -> None:
        pass


class SmtpMailer(AiosmtplibMailer):
    @t.override
    def _get_port(self) -> str:  # error: a port an int
        return "587"
