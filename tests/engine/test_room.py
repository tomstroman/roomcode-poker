import pytest
from fastapi.websockets import WebSocketState


def test_room(trivial_room):
    room = trivial_room
    assert room.code == "ABC123"  # from fixture


@pytest.mark.parametrize(
    "ws_state,want_msg_count",
    [
        (WebSocketState.CONNECTED, 1),
        (WebSocketState.CONNECTING, 0),
        (WebSocketState.DISCONNECTED, 0),
        (WebSocketState.RESPONSE, 0),
    ],
)
async def test_send_game_state__connected_websocket_only(
    trivial_room, websocket, ws_state, want_msg_count
):
    websocket.application_state = ws_state
    trivial_room["FOO"] = websocket
    await trivial_room.send_game_state()
    msgs = websocket.sent_messages
    assert len(msgs) == want_msg_count
