from contextlib import AsyncExitStack
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from app.api import rooms
from app.main import fastapi_app as app

# The first client to connect receives messages:
# 1. welcome payload
# 2. a spectator is manager
# 3. you're the manager
# 4. slots
NUM_FIRST_CLIENT_MSG = 4
NUM_LATER_CLIENT_MSG = 2


@pytest.fixture
async def async_ws_client():
    async with AsyncClient(
        transport=ASGIWebSocketTransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_multiple_ws_clients(async_ws_client, trivial_room):
    room = trivial_room
    assert room.code not in rooms
    rooms[room.code] = room
    assert not room.items()

    async with AsyncExitStack() as stack:
        ws1 = await stack.enter_async_context(
            aconnect_ws(f"/ws/{room.code}/", async_ws_client)
        )
        ws2 = await stack.enter_async_context(
            aconnect_ws(f"/ws/{room.code}/", async_ws_client)
        )

        msg1 = await ws1.receive_json()
        msg2 = await ws2.receive_json()

        assert len(room.items()) == 2
        client_ids = list(room.keys())
        assert (c1 := msg1["client_id"]) in client_ids
        assert (c2 := msg2["client_id"]) in client_ids
        assert c1 != c2


@pytest.mark.asyncio
async def test_ws_inner_exception(async_ws_client, trivial_room, caplog):
    room = trivial_room
    assert room.code not in rooms
    rooms[room.code] = room
    assert not room.items()

    with patch("app.api.handle_ws_message", side_effect=ValueError("foo")):
        async with AsyncExitStack() as stack:
            ws = await stack.enter_async_context(
                aconnect_ws(f"/ws/{room.code}/", async_ws_client)
            )

            for _ in range(NUM_FIRST_CLIENT_MSG):
                await ws.receive_json()

            payload = {"action": "some_action"}
            await ws.send_json(payload)
            msg = await ws.receive_json()
            assert msg.get("error") == "Server error while handling your action"
        assert "Error handling WebSocket message: ValueError('foo')" in caplog.text


@pytest.mark.asyncio
async def test_ws_disconnect_releases_manager(async_ws_client, trivial_room):
    room = trivial_room
    assert room.code not in rooms
    rooms[room.code] = room
    assert not room.items()

    async with AsyncExitStack() as stack:
        ws1 = await stack.enter_async_context(
            aconnect_ws(f"/ws/{room.code}/", async_ws_client)
        )

        for _ in range(NUM_FIRST_CLIENT_MSG):
            await ws1.receive_json()

        ws2 = await stack.enter_async_context(
            aconnect_ws(f"/ws/{room.code}/", async_ws_client)
        )
        for _ in range(NUM_LATER_CLIENT_MSG):
            await ws2.receive_json()

        await ws1.close()
        msg = await ws2.receive_json()
        assert msg["info"] == "There is no manager"
