"""
Runs the events as their actors meet them. The end user changes its password
on its laptop: the reply does not wait for the mail, which goes after the
commit with the audit of the game, a broken subscriber failing alone. The
game changes the password and the nickname in one transaction: the nickname
taken undoes both, and no mail tells of a change that is not; the nickname
optional, the password stays, and the mail goes. A hold of the application
keeps the events till its block ends, raising or not; a discard drops them;
a transaction in a hold sends nothing on its commit, the hold does. A
subscriber its caller may not run is skipped, logged, the others run. mypy
refuses the lines the other file marks.
"""

import asyncio
import logging

from app import (
    GameNicknameTakenError,
    GameProject,
    GameUpdateParameters,
    GuardedProject,
)
from auth_stub import (
    AuthChangePasswordParameters,
    AuthPasswordRefusedError,
    hash_password,
)
from ingots_stub import run

PASSWORDS = [f"correct horse battery staple {number}" for number in range(9)]


class Failures(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


async def main() -> None:
    failures = Failures()
    logging.getLogger("ingots").addHandler(failures)
    project = GameProject()
    auth, events, mail = project.auth, project.events, project.mail
    alice = auth.sign_up("alice", PASSWORDS[0], ["alice@example.com"])
    auth.sign_up("bob", PASSWORDS[0], [])
    phone = auth.sign_in(alice, {"device": "a phone"})
    laptop = auth.sign_in(alice, {"device": "a laptop"})
    change = auth.password.op_change
    step = iter(range(len(PASSWORDS) - 1))

    def next_change() -> AuthChangePasswordParameters:
        number = next(step)
        return AuthChangePasswordParameters(old=PASSWORDS[number], new=PASSWORDS[number + 1])

    def password_is(number: int) -> bool:
        return auth.storage.state.profiles[alice].secret == hash_password(PASSWORDS[number])

    # the change: the reply first, the mail after, the broken one alone
    await run(change, next_change(), laptop)
    assert password_is(1) and mail.sent == []
    await events.join()
    [sent] = mail.sent
    assert sent.to == "alice@example.com" and "a laptop" in sent.text
    assert project.game.audit == [f"password of {alice}"]
    assert any("GameBrokenOperation" in message for message in failures.messages)
    assert phone.session_uid and auth.storage.state.sessions[phone.session_uid].is_closed

    # one transaction of the game: the nickname taken undoes the password,
    # and no mail tells of it
    phone = auth.sign_in(alice, {"device": "a phone"})
    undone = GameUpdateParameters(password=next_change(), nickname="bob")
    try:
        await run(project.game.op_update, undone, laptop)
    except GameNicknameTakenError:
        pass
    else:
        raise AssertionError("a nickname taken was set")
    await events.join()
    assert password_is(1) and len(mail.sent) == 1
    assert phone.session_uid and not auth.storage.state.sessions[phone.session_uid].is_closed

    # the nickname optional: the password stays, the mail goes
    kept = GameUpdateParameters(
        password=AuthChangePasswordParameters(old=PASSWORDS[1], new=PASSWORDS[2]),
        nickname="bob",
        is_nickname_optional=True,
    )
    await run(project.game.op_update, kept, laptop)
    await events.join()
    assert password_is(2) and len(mail.sent) == 2

    # a wrong old password inside the transaction of the game: nothing
    wrong = GameUpdateParameters(
        password=AuthChangePasswordParameters(old="wrong", new=PASSWORDS[3]), nickname="al"
    )
    try:
        await run(project.game.op_update, wrong, laptop)
    except AuthPasswordRefusedError:
        pass
    await events.join()
    assert password_is(2) and len(mail.sent) == 2

    # a hold of the application, no transaction of its own: kept till the
    # block ends, sent then though it raises, a fact published is a fact
    try:
        async with events.hold():
            await run(
                change,
                AuthChangePasswordParameters(old=PASSWORDS[2], new=PASSWORDS[3]),
                laptop,
            )
            await events.join()
            assert len(mail.sent) == 2  # held
            raise RuntimeError("the block fails after the change")
    except RuntimeError:
        pass
    await events.join()
    assert password_is(3) and len(mail.sent) == 3

    # a discard drops what its scope holds
    async with events.hold() as held:
        await run(
            change, AuthChangePasswordParameters(old=PASSWORDS[3], new=PASSWORDS[4]), laptop
        )
        held.discard()
    await events.join()
    assert password_is(4) and len(mail.sent) == 3

    # a transaction in a hold: its commit sends nothing, the hold does
    async with events.hold():
        await run(
            change, AuthChangePasswordParameters(old=PASSWORDS[4], new=PASSWORDS[5]), laptop
        )
        await events.join()
        assert len(mail.sent) == 3
    await events.join()
    assert password_is(5) and len(mail.sent) == 4

    # a subscriber the caller may not run: skipped, logged; the mail goes
    guarded = GuardedProject()
    carol = guarded.auth.sign_up("carol", PASSWORDS[0], ["carol@example.com"])
    carols = guarded.auth.sign_in(carol, {})
    await run(
        guarded.auth.password.op_change,
        AuthChangePasswordParameters(old=PASSWORDS[0], new=PASSWORDS[1]),
        carols,
    )
    await guarded.events.join()
    assert [sent.to for sent in guarded.mail.sent] == ["carol@example.com"]
    assert any("GameStaffOperation" in message for message in failures.messages)


asyncio.run(main())
