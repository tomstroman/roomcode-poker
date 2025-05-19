from unittest.mock import patch

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from app.api import generate_code, rooms
from app.main import fastapi_app as app


@pytest.fixture(autouse=True)
def clear_rooms():
    rooms.clear()


@pytest.mark.parametrize("length", [1, 2, 3, 4, 5])
def test_generate_code__creates_codes_of_length(length):
    code = generate_code(length)
    assert len(code) == length


@pytest.mark.asyncio
async def test_create_game_success():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/create-game/", json={"game_type": "pass_the_pebble", "players": 3}
        )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "code" in data
    assert isinstance(data["code"], str)
    assert len(data["code"]) > 0


@pytest.mark.asyncio
async def test_create_game_invalid_type():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/create-game/", json={"game_type": "duke_nukem_forever", "players": 1}
        )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json().get("detail") == "Unknown game type"


@pytest.mark.asyncio
async def test_create_game_code_collision():
    # first two calls return "DUCK" and third returns "GRAY"
    with patch(
        "app.api.generate_code", side_effect=["DUCK", "DUCK", "GRAY", "DUCK"]
    ) as mocked_gencode:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response1 = await ac.post(
                "/create-game/", json={"game_type": "pass_the_pebble", "players": 2}
            )
            assert response1.status_code == status.HTTP_200_OK
            assert response1.json().get("code") == "DUCK"
            assert set(rooms.keys()) == {"DUCK"}
            assert mocked_gencode.call_count == 1

            response2 = await ac.post(
                "/create-game/", json={"game_type": "pass_the_pebble", "players": 3}
            )
            assert response2.status_code == status.HTTP_200_OK
            assert response2.json().get("code") == "GRAY"
            assert set(rooms.keys()) == {"DUCK", "GRAY"}
            assert mocked_gencode.call_count == 3
