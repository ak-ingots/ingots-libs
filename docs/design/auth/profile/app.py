"""Two addons and an application joining their schemas of the profile."""

import datetime

from auth_profile import AuthAttributes, AuthProfile, ProfileRecord, Value


class LocaleAttributes(AuthAttributes):  # an addon
    locale: str = "en"


class VerifyAttributes(AuthAttributes):  # another addon
    is_email_verified: bool = False
    verified_at: datetime.datetime | None = None


class ShopAttributes(LocaleAttributes, VerifyAttributes):  # the application
    nickname: str


def run_the_scenario() -> None:
    stored = ProfileRecord(
        uid="u1",
        tags=frozenset({"beta"}),
        values={"nickname": "ann", "locale": "be", "newer_field": 7},
    )
    profile = AuthProfile.from_record(ShopAttributes, stored)
    nickname: str = profile.attributes.nickname
    assert (nickname, profile.attributes.locale) == ("ann", "be")
    assert profile.attributes.is_email_verified is False, "a default fills a gap"
    assert profile.unknown == {"newer_field": 7}, "kept for a newer version"
    assert profile.to_record().values == {
        "nickname": "ann",
        "locale": "be",
        "is_email_verified": False,
        "newer_field": 7,
    }

    wrong: tuple[dict[str, Value], ...] = (
        {"nickname": 1},
        {"nickname": "ann", "is_email_verified": 1},
    )
    for values in wrong:
        try:
            ShopAttributes.from_values(values)
        except ValueError:
            pass
        else:
            raise AssertionError(f"accepted {values}")

    for declare in (_declare_twice, _declare_a_dict):
        try:
            declare()
        except TypeError:
            pass
        else:
            raise AssertionError(f"{declare.__name__} passed")


def _declare_twice() -> None:
    class OtherLocale(AuthAttributes):
        locale: str = "de"

    class Both(LocaleAttributes, OtherLocale):
        pass


def _declare_a_dict() -> None:
    class Rich(AuthAttributes):
        address: dict[str, str]


def show_the_types(profile: AuthProfile[ShopAttributes]) -> None:
    profile.attributes.title  # error: not an attribute of the schema
    ShopAttributes(nickname=1)  # error: a str
    ShopAttributes()  # error: nickname has no default
