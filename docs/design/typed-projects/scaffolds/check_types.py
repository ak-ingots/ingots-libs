"""
Runs the scaffolds: the game signs a player up through the starter, the site
through its own composition, each entity reaching its project with no cast;
a join forgotten is refused at the creation of the class. mypy refuses the
lines the other file marks.
"""

import asyncio
import typing as t

from app import GameConfigs, GameProject, SiteConfigs, SiteProject
from auth_addon import AuthEmailCodeProject, AuthNicknameProject


async def main() -> None:
    game = GameProject()
    assert await game.game.scores.enrol("alice") == "mongodb:1"
    assert game.mongodb.client.collections == {"profiles": [{"nickname": "alice"}]}
    t.assert_type(game.settings.configs, GameConfigs)
    assert game.settings.configs.AUTH_SESSIONS_MAX == 1
    assert game.auth.methods.email_code.get_code_ttl() == 600

    site = SiteProject()
    assert await site.auth.methods.nickname.sign_up("bob") == "mongodb:1"
    t.assert_type(site.settings.configs, SiteConfigs)

    # a join forgotten, two bases holding different settings, none declared:
    # refused at the creation of the class, as mypy refuses it in the other file
    try:
        type("Forgotten", (AuthNicknameProject, AuthEmailCodeProject), {})
    except TypeError as error:
        assert "settings" in str(error)
    else:
        raise AssertionError("a join forgotten passed")


asyncio.run(main())
