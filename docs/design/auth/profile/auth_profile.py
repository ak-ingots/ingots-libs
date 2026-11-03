"""
The profile of auth: a uid, tags and the attributes of an application's
schema, a dataclass mapped one to one onto the flat values a storage keeps.
"""

import dataclasses
import datetime
import typing as t
from collections.abc import Mapping

type Value = bool | int | float | str | datetime.datetime
"""What an attribute holds: a scalar a storage indexes and a protobuf field
carries. A complex value belongs to the domain of the application."""

_VALUE_TYPES: t.Final = (bool, int, float, str, datetime.datetime)


@t.dataclass_transform(frozen_default=True, kw_only_default=True)
class AuthAttributes:
    """
    The schema of the attributes of a profile, a frozen dataclass:

        class ShopAttributes(AuthAttributes):
            nickname: str
            locale: str = "en"

    A field takes a scalar :data:`Value`, or ``None`` too; a new field takes
    a default, for the profiles stored before it. The schemas of addons join
    by inheritance, a field declared by two of them raising ``TypeError``.
    """

    @classmethod
    def __init_subclass__(cls, **kwargs: t.Any) -> None:
        super().__init_subclass__(**kwargs)
        _check_joined(cls)
        dataclasses.dataclass(frozen=True, kw_only=True)(cls)
        _check_types(cls)

    @classmethod
    def from_values(cls, values: Mapping[str, Value]) -> tuple[t.Self, dict[str, Value]]:
        """The attributes of ``values``, and the values the schema does not
        know: a newer version wrote them, they are kept as they are."""
        names = {field.name for field in dataclasses.fields(cls)}  # type: ignore[arg-type]
        known = {name: value for name, value in values.items() if name in names}
        unknown = {name: value for name, value in values.items() if name not in names}
        attributes = cls(**known)
        _check_values(attributes)
        return attributes, unknown

    def to_values(self) -> dict[str, Value]:
        return {
            field.name: getattr(self, field.name)
            for field in dataclasses.fields(self)  # type: ignore[arg-type]
            if getattr(self, field.name) is not None
        }


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ProfileRecord:
    """The profile as a storage keeps it: no schema, flat values."""

    uid: str
    tags: frozenset[str]
    values: Mapping[str, Value]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthProfile[AttributesType: AuthAttributes]:
    uid: str
    tags: frozenset[str] = frozenset()
    attributes: AttributesType
    unknown: Mapping[str, Value] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_record(
        cls, attributes_cls: type[AttributesType], record: ProfileRecord
    ) -> "AuthProfile[AttributesType]":
        attributes, unknown = attributes_cls.from_values(record.values)
        return AuthProfile(
            uid=record.uid, tags=record.tags, attributes=attributes, unknown=unknown
        )

    def to_record(self) -> ProfileRecord:
        return ProfileRecord(
            uid=self.uid,
            tags=self.tags,
            values={**self.unknown, **self.attributes.to_values()},
        )


def _check_joined(cls: type[AuthAttributes]) -> None:
    # a field is declared by one schema and its subclasses, not by two
    owners: dict[str, type] = {}
    for base in reversed(cls.__mro__[1:]):
        for name in getattr(base, "__annotations__", {}):
            owner = owners.get(name)
            if owner is not None and not issubclass(base, owner):
                raise TypeError(
                    f"{cls.__qualname__}: {owner.__qualname__} and "
                    f"{base.__qualname__} both declare the attribute {name}"
                )
            owners[name] = base


def _check_types(cls: type[AuthAttributes]) -> None:
    for name, hint in t.get_type_hints(cls).items():
        allowed = [arg for arg in t.get_args(hint) if arg is not type(None)] or [hint]
        if len(allowed) != 1 or allowed[0] not in _VALUE_TYPES:
            raise TypeError(f"{cls.__qualname__}.{name}: {hint} is not a scalar value")


def _check_values(attributes: AuthAttributes) -> None:
    hints = t.get_type_hints(type(attributes))
    for name, hint in hints.items():
        value = getattr(attributes, name)
        allowed = tuple(arg for arg in t.get_args(hint) or (hint,))
        if not any(type(value) is arg for arg in allowed):  # bool is not an int
            raise ValueError(f"{type(attributes).__qualname__}.{name}: {value!r}")
