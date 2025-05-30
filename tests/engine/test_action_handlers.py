from unittest.mock import AsyncMock, patch

import pytest

from app.engine.action_handlers import (
    ACTION_HANDLERS,
    claim_manager,
    claim_slot,
    handle_ws_message,
    release_slot,
    start_game,
    take_turn,
    update_name,
)


@pytest.mark.parametrize(
    "player_slot,manager",
    [
        (None, "A spectator"),
        (0, "Player 0"),
    ],
)
async def test_claim_manager__succeeds_when_available(
    trivial_room, websocket, player_slot, manager
):
    CLIENT_ID = "testclient"
    trivial_room[CLIENT_ID] = websocket

    if player_slot is not None:
        trivial_room.game.players[player_slot].client_id = CLIENT_ID
    context = {
        "ws": websocket,
        "client_id": CLIENT_ID,
        "room": trivial_room,
        "data": {"action": "claim_manager"},
    }
    await claim_manager(context)
    assert trivial_room.game.manager == CLIENT_ID
    assert len(msgs := websocket.sent_messages) > 0
    assert not any("error" in msg.keys() for msg in msgs)
    print(msgs)
    assert any(f"{manager} is the manager" in msg.get("info") for msg in msgs)


async def test_claim_manager__errors_when_claimed(trivial_room, websocket):
    CLIENT_ID = "testclient"
    MANAGER = "some1else"
    trivial_room.game.manager = MANAGER
    context = {
        "ws": websocket,
        "client_id": CLIENT_ID,
        "room": trivial_room,
        "data": {"action": "claim_manager"},
    }
    await claim_manager(context)
    assert trivial_room.game.manager == MANAGER
    assert len(msgs := websocket.sent_messages) == 1
    assert msgs[0].get("error") == "Could not claim manager"


async def test_claim_slot__succeeds_when_available(trivial_room, websocket):
    CLIENT_ID = "testclient"
    SLOT_ID = 0
    context = {
        "ws": websocket,
        "client_id": CLIENT_ID,
        "room": trivial_room,
        "data": {"action": "claim_slot", "slot": SLOT_ID},
    }
    await claim_slot(context)
    assert trivial_room.game.players[SLOT_ID].client_id == CLIENT_ID


async def test_claim_slot__errors_when_claimed(trivial_room, websocket):
    OTHER_CLIENT = "some1else"
    CLIENT_ID = "testclient"
    SLOT_ID = 0
    trivial_room.game.players[SLOT_ID].client_id = OTHER_CLIENT
    context = {
        "ws": websocket,
        "client_id": CLIENT_ID,
        "room": trivial_room,
        "data": {"action": "claim_slot", "slot": SLOT_ID},
    }
    await claim_slot(context)
    assert trivial_room.game.players[SLOT_ID].client_id == OTHER_CLIENT
    assert len(msgs := websocket.sent_messages) == 1
    assert msgs[0].get("error") == f"Slot {SLOT_ID} already claimed"


@pytest.mark.parametrize(
    "game_started,num_msgs",
    [
        (False, 1),
        (True, 2),
    ],
)
async def test_release_slot__succeeds_when_held(
    trivial_room, websocket, game_started, num_msgs
):
    CLIENT_ID = "testclient"
    SLOT_ID = 0
    trivial_room.game.is_started = game_started
    trivial_room.game.players[SLOT_ID].client_id = CLIENT_ID
    trivial_room[CLIENT_ID] = websocket
    context = {
        "ws": websocket,
        "client_id": CLIENT_ID,
        "room": trivial_room,
        "data": {"action": "release_slot"},
    }
    await release_slot(context)
    assert trivial_room.game.players[SLOT_ID].client_id is None
    assert len(msgs := websocket.sent_messages) == num_msgs
    if num_msgs:
        assert not any("error" in msg.keys() for msg in msgs)


@pytest.mark.parametrize("slot_holder", ["some1else", None])
async def test_release_slot__errors_when_not_held(trivial_room, websocket, slot_holder):
    CLIENT_ID = "testclient"
    SLOT_ID = 0
    trivial_room.game.players[SLOT_ID].client_id = slot_holder
    context = {
        "ws": websocket,
        "client_id": CLIENT_ID,
        "room": trivial_room,
        "data": {"action": "release_slot"},
    }
    await release_slot(context)
    assert trivial_room.game.players[SLOT_ID].client_id == slot_holder
    assert len(msgs := websocket.sent_messages) == 1
    assert msgs[0].get("error") == "No slot associated with client"


async def test_start_game__as_manager__succeeds(trivial_room, websocket):
    CLIENT_ID = "testclient"
    trivial_room[CLIENT_ID] = websocket
    trivial_room.game.manager = CLIENT_ID
    trivial_room.game.is_started = False
    context = {
        "ws": websocket,
        "client_id": CLIENT_ID,
        "room": trivial_room,
        "data": {"action": "start_game"},
    }
    await start_game(context)
    assert trivial_room.game.is_started
    assert len(msgs := websocket.sent_messages) == 2
    assert not any("error" in msg.keys() for msg in msgs)
    assert msgs[0].get("info") == "Game started"


async def test_start_game__as_manager__already_started_error(trivial_room, websocket):
    CLIENT_ID = "testclient"
    trivial_room[CLIENT_ID] = websocket
    trivial_room.game.manager = CLIENT_ID
    trivial_room.game.is_started = True
    context = {
        "ws": websocket,
        "client_id": CLIENT_ID,
        "room": trivial_room,
        "data": {"action": "start_game"},
    }
    await start_game(context)
    assert trivial_room.game.is_started
    assert len(msgs := websocket.sent_messages) == 1
    assert msgs[0].get("error") == "Game already started"


async def test_start_game__errors_when_not_manager(trivial_room, websocket):
    CLIENT_ID = "testclient"
    MANAGER = "some1else"
    trivial_room.game.manager = MANAGER
    context = {
        "ws": websocket,
        "client_id": CLIENT_ID,
        "room": trivial_room,
        "data": {"action": "start_game"},
    }
    await start_game(context)
    assert not trivial_room.game.is_started
    assert len(msgs := websocket.sent_messages) == 1
    assert msgs[0].get("error") == "Only the manager can start the game"


async def test_start_game__errors_on_exception(trivial_room, websocket):
    CLIENT_ID = "testclient"
    trivial_room[CLIENT_ID] = websocket
    trivial_room.game.manager = CLIENT_ID
    trivial_room.game.is_started = False
    context = {
        "ws": websocket,
        "client_id": CLIENT_ID,
        "room": trivial_room,
        "data": {"action": "start_game"},
    }
    with patch(
        "tests.conftest.TrivialGame.start_game",
        side_effect=ValueError("game not ready"),
    ):
        await start_game(context)
        assert not trivial_room.game.is_started
    assert len(msgs := websocket.sent_messages) == 1
    assert msgs[0].get("error") == "game not ready"


async def test_take_turn__sends_state(trivial_room, websocket):
    CLIENT_ID = "testclient"
    trivial_room[CLIENT_ID] = websocket
    trivial_room.game.manager = CLIENT_ID
    context = {
        "ws": websocket,
        "client_id": CLIENT_ID,
        "room": trivial_room,
        "data": {"action": "take_turn", "turn": "pass"},
    }
    with patch("tests.conftest.TrivialGame.submit_action") as mock_take_turn:
        await take_turn(context)
        assert mock_take_turn.call_count == 1
    assert len(msgs := websocket.sent_messages) == 1
    assert "error" not in msgs[0].keys()


async def test_update_player__succeeds_for_own_slot(trivial_room, websocket):
    CLIENT_ID = "testclient"
    SLOT_ID = 0
    trivial_room.game.players[SLOT_ID].client_id = CLIENT_ID
    OLD_NAME = trivial_room.game.players[SLOT_ID].display_name
    NEW_NAME = "Test Client"
    assert NEW_NAME != OLD_NAME
    trivial_room[CLIENT_ID] = websocket
    context = {
        "ws": websocket,
        "client_id": CLIENT_ID,
        "room": trivial_room,
        "data": {"action": "update_name", "slot": SLOT_ID, "name": NEW_NAME},
    }
    await update_name(context)
    assert trivial_room.game.players[SLOT_ID].display_name == NEW_NAME
    assert len(msgs := websocket.sent_messages) == 1
    assert "error" not in msgs[0].keys()


@pytest.mark.parametrize("slot_holder", ["some1else", None])
async def test_update_player__fails_for_other_slot(
    trivial_room, websocket, slot_holder
):
    CLIENT_ID = "testclient"
    SLOT_ID = 0
    trivial_room.game.players[SLOT_ID].client_id = slot_holder
    OLD_NAME = trivial_room.game.players[SLOT_ID].display_name
    NEW_NAME = "Test Client"
    trivial_room[CLIENT_ID] = websocket
    context = {
        "ws": websocket,
        "client_id": CLIENT_ID,
        "room": trivial_room,
        "data": {"action": "update_name", "slot": SLOT_ID, "name": NEW_NAME},
    }
    await update_name(context)
    assert trivial_room.game.players[SLOT_ID].display_name == OLD_NAME
    assert len(msgs := websocket.sent_messages) == 1
    assert msgs[0].get("error") == f"Cannot change name for slot={SLOT_ID}"


@pytest.mark.parametrize("action", ACTION_HANDLERS.keys())
async def test_handle_ws_message__routes_known_actions(trivial_room, websocket, action):
    CLIENT_ID = "testclient"
    context = {
        "ws": websocket,
        "client_id": CLIENT_ID,
        "room": trivial_room,
        "data": {"action": action},  # with handler patched, other keys unnecessary
    }

    mock_handler = AsyncMock()
    with patch.dict(
        "app.engine.action_handlers.ACTION_HANDLERS", {action: mock_handler}
    ):
        await handle_ws_message(context)
        mock_handler.assert_awaited_once_with(context)
    assert not websocket.sent_messages


async def test_handle_ws_message__errors_unknown_actions(trivial_room, websocket):
    CLIENT_ID = "testclient"
    context = {
        "ws": websocket,
        "client_id": CLIENT_ID,
        "room": trivial_room,
        "data": {"action": "reticulate_splines"},
    }

    await handle_ws_message(context)
    assert len(msgs := websocket.sent_messages) == 1
    assert msgs[0].get("error") == "Unknown action: reticulate_splines"
