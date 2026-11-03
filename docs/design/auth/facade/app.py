"""
An application: its schema of the profile, and the logic of auth typed by
it from sign-up to the authenticated request.
"""

import datetime
from dataclasses import dataclass

from logic import Auth, AuthConfigs, NotAuthenticated, SignInFailed
from model import AuthProfile, SessionOrigin
from storage import IdentifierTaken, MemoryAuthStorage


@dataclass(frozen=True, slots=True, kw_only=True)
class ShopProfileData:
    nickname: str
    first_name: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class OtherData:
    title: str


PHONE = SessionOrigin(address="203.0.113.7", client="shop-ios/2.1")


class Clock:
    def __init__(self) -> None:
        self.now = datetime.datetime(2026, 10, 27, tzinfo=datetime.UTC)

    def __call__(self) -> datetime.datetime:
        return self.now


async def run_the_scenario() -> None:
    clock = Clock()
    storage = MemoryAuthStorage[ShopProfileData]()
    auth = Auth(storage, AuthConfigs(session_ttl=datetime.timedelta(hours=1)), clock=clock)

    signed_up = await auth.sign_up(ShopProfileData(nickname="ann"), "ann@example.com", "s3cret", PHONE)
    assert signed_up.token is not None, "signed in on sign-up by the configs"
    profile: AuthProfile[ShopProfileData] = await auth.authenticate(signed_up.token)
    assert profile.data.nickname == "ann"

    try:
        await auth.sign_up(ShopProfileData(nickname="ann2"), "ann@example.com", "x", PHONE)
    except IdentifierTaken:
        pass
    else:
        raise AssertionError("the login is taken")

    for login, password in (("ann@example.com", "wrong"), ("nobody@example.com", "s3cret")):
        try:
            await auth.sign_in(login, password, PHONE)
        except SignInFailed:
            pass
        else:
            raise AssertionError("signed in")

    token = await auth.sign_in("ann@example.com", "s3cret", PHONE)
    await auth.sign_out(token)
    clock.now += datetime.timedelta(hours=2)
    for gone in (token, signed_up.token):  # ended, expired
        try:
            await auth.authenticate(gone)
        except NotAuthenticated:
            pass
        else:
            raise AssertionError("authenticated")

    no_session = Auth(storage, AuthConfigs(is_sign_in_on_sign_up=False), clock=clock)
    later = await no_session.sign_up(ShopProfileData(nickname="bob"), "bob@example.com", "pw", PHONE)
    assert later.token is None


async def show_the_types(auth: Auth[ShopProfileData]) -> None:
    await auth.sign_up(OtherData(title="x"), "a", "b", PHONE)  # error: another schema
    profile = await auth.authenticate("token")
    profile.data.title  # error: not a field of the schema
