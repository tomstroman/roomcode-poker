from app.engine.action_handlers import claim_manager, claim_slot


async def test_claim_manager__succeeds_when_available(trivial_room, websocket):
    CLIENT_ID = "testclient"
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
