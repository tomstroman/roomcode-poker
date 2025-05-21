from contextlib import AsyncExitStack

import pytest
from httpx import AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from app.api import rooms
from app.main import fastapi_app as app


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
