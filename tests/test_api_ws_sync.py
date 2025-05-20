from starlette.testclient import TestClient

from app.api import rooms
from app.main import fastapi_app as app

client = TestClient(app)


def test_ws_room_not_found():
    assert "FOO" not in rooms
    with client.websocket_connect("/ws/FOO/") as ws:
        message = ws.receive_json()
        assert message.get("error") == "Game room not found"


def test_ws_first_client_connect(trivial_room):
    room = trivial_room
    assert room.code not in rooms
    rooms[room.code] = room
    assert not room.items()
    with client.websocket_connect(f"/ws/{room.code}/") as ws:
        message = ws.receive_json()
        assert len(room.items()) == 1
        client_id = list(room.keys())[0]
        # These details come from room.set_manager behavior - change?
        assert message.get("info") == "A spectator is the manager now"
        message = ws.receive_json()
        assert message.get("info") == "You are the manager"
        message = ws.receive_json()
        # From room.broadcast_slots()
        assert message["my_slot"] is None
        assert message["available_slots"] == {"0": True}

        message = ws.receive_json()
        assert message["client_id"] == client_id


def test_ws_second_client_connect(trivial_room):
    room = trivial_room
    assert room.code not in rooms
    rooms[room.code] = room
    assert not room.items()
    with client.websocket_connect(f"/ws/{room.code}/") as ws_1:
        _ = ws_1.receive_json()
        assert len(room.items()) == 1
        client_id_1 = list(room.keys())[0]
        with client.websocket_connect(f"/ws/{room.code}/") as ws_2:
            message = ws_2.receive_json()
            client_ids = list(room.keys())
            assert len(client_ids) == 2
            client_ids.remove(client_id_1)
            client_id_2 = client_ids[0]
            assert message.get("available_slots") == {"0": True}
            message = ws_2.receive_json()
            assert message["client_id"] == client_id_2
