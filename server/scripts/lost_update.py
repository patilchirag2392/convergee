"""Reproduce the last-write-wins lost update against a running server.

Start the server first:  uv run uvicorn app.main:app
Then, from server/:      uv run python scripts/lost_update.py
"""

import asyncio
import json
import uuid

from websockets.asyncio.client import connect

SERVER = "ws://localhost:8000/ws"


async def receive(ws) -> dict:
    # Fail loudly after 2s instead of hanging, same lesson as pytest-timeout.
    return json.loads(await asyncio.wait_for(ws.recv(), timeout=2))


async def edit(ws, base: str, addition: str) -> str:
    """Send base + addition as the whole document; return what this client ends up showing."""
    await ws.send(json.dumps({"text": base + addition}))
    update = await receive(ws)  # the other client's whole document overwrites ours
    return update["text"]


async def main() -> None:
    url = f"{SERVER}/demo-{uuid.uuid4().hex[:8]}"

    async with connect(url) as alice, connect(url) as bob:
        base_alice = (await receive(alice))["text"]
        base_bob = (await receive(bob))["text"]
        assert base_alice == base_bob == ""

        alice_view, bob_view = await asyncio.gather(
            edit(alice, base_alice, "Alice was here. "),
            edit(bob, base_bob, "Bob was here. "),
        )

    async with connect(url) as observer:
        server_view = (await receive(observer))["text"]

    print("intended : both sentences, in some order")
    print(f"server   : {server_view!r}")
    print(f"alice    : {alice_view!r}")
    print(f"bob      : {bob_view!r}")


if __name__ == "__main__":
    asyncio.run(main())