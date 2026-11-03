"""Runs the contract on the memory storage and the scenario of the app."""

import asyncio

from app import run_the_scenario
from contract import CONTRACT
from storage import MemoryAuthStorage


async def main() -> None:
    for test in CONTRACT:
        await test(MemoryAuthStorage[None]())  # type: ignore[misc]
        print("ok", test.__name__)
    await run_the_scenario()
    print("ok the scenario")


asyncio.run(main())
