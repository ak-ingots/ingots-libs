"""
Runs the mailer as its consumers meet it: the application sends by SMTP from
its sender, the tests read the mail in memory; a mail unfit to send is refused before the server, a server down is
a transient failure. mypy refuses the lines of ``mistakes.py``.
"""

import asyncio

from app import AppProject, TestProject, get_memory_mailer
from mail_stub import SERVER, SERVER_DOWN, Mail, MailDeliveryError, MailHeaderError


async def main() -> None:
    # the application: a welcome mail by SMTP, from MAIL_FROM, to Mailpit
    project = AppProject()
    await project.welcome("al@b.c", "Al")
    [sent] = SERVER
    assert sent["message"]["From"] == "hello@shop.example"
    assert sent["message"]["To"] == "al@b.c"
    assert (sent["hostname"], sent["port"]) == ("mailpit", 1025)
    assert sent["start_tls"] is False and sent["username"] is None

    # its tests: the mailer in memory, the mail in its order with its sender
    test = TestProject()
    await test.welcome("bo@b.c", "Bo")
    code = Mail(to=("cy@b.c",), subject="Your code", text="123456\n")
    await test.mail.mailer.send(code)
    assert [(sender, mail.to) for sender, mail in get_memory_mailer(test).get_sent()] == [
        ("hello@shop.example", ("bo@b.c",)),
        ("hello@shop.example", ("cy@b.c",)),
    ]
    assert "123456" not in repr(get_memory_mailer(test).get_sent())  # no code in logs

    # a header unfit to send: refused before any backend
    for mail in (
        Mail(to=(), subject="Hi", text=""),
        Mail(to=("al@b.c",), subject="Hi\r\nBcc: all@b.c", text=""),
        Mail(to=("al@b.c\nBcc: all@b.c",), subject="Hi", text=""),
        Mail(to=("al@b.c",), subject="Hi", text="", sender="a@b.c\nBcc: all@b.c"),
    ):
        try:
            await project.mail.mailer.send(mail)
        except MailHeaderError as error:
            print("refused:", error.name)
        else:
            raise AssertionError("a header injected")
    assert len(SERVER) == 1

    # a sender of its own, a mail of the support
    support = Mail(to=("al@b.c",), subject="Re", text="", sender="help@shop.example")
    await project.mail.mailer.send(support)
    assert SERVER[-1]["message"]["From"] == "help@shop.example"

    # a server down: the caller may send it again later
    SERVER_DOWN.append(True)
    try:
        await project.welcome("al@b.c", "Al")
    except MailDeliveryError as error:
        assert error.is_transient
    else:
        raise AssertionError("delivered to a server down")


asyncio.run(main())
