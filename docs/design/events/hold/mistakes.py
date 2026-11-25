"""The lines mypy refuses: what the events let no one write."""

import dataclasses
import datetime
import typing as t

from auth_stub import AuthPassword, AuthPasswordChanged, AuthProject
from ingots_stub import BaseOperation, Factories, OperationMetadata, Permissions


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class NicknameChanged:
    profile_uid: str
    nickname: str


class OnNickname(BaseOperation[NicknameChanged, None]):
    @t.override
    def _get_permissions(self) -> Permissions:
        return Permissions()

    @t.override
    async def _run(self, parameters: NicknameChanged, metadata: OperationMetadata) -> None:
        pass


class WrongPassword(AuthPassword):
    ev_changed = Factories[BaseOperation[AuthPasswordChanged, None]](
        OnNickname  # error: a subscriber of another event
    )


def publish(project: AuthProject, metadata: OperationMetadata) -> None:
    nickname = NicknameChanged(profile_uid="p1", nickname="al")
    project.events.publish(project.auth.password.ev_changed, nickname, metadata)  # error: another event


def tamper(event: AuthPasswordChanged) -> None:
    event.at = datetime.datetime.now(datetime.UTC)  # error: an event is a fact
