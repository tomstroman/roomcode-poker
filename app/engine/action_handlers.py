import logging

logger = logging.getLogger()


async def claim_slot(ctx: dict):
    slot = ctx["data"]["slot"]
    if ctx["room"].game.players[slot].client_id is None:
        logger.info("client_id=%s claiming slot %s", ctx["client_id"], slot)
        await ctx["room"].claim_slot(slot, ctx["client_id"])
    else:
        await ctx["ws"].send_json({"error": f"Slot {slot} already claimed"})


async def update_name(ctx: dict):
    room = ctx["room"]
    player = room.game.players[(slot := ctx["data"]["slot"])]
    if player.client_id == (client_id := ctx["client_id"]):
        logger.info(
            "client_id=%s (slot %s) updating name from %s to %s",
            client_id,
            slot,
            player.display_name,
            (name := ctx["data"]["name"]),
        )
        player.set_display_name(name)
        await room.broadcast_slots()
    else:
        await ctx["ws"].send_json({"error": f"Cannot change name for {slot=}"})


async def claim_manager(ctx: dict):
    logger.info(
        "client_id=%s attempting to claim manager", (client_id := ctx["client_id"])
    )
    if not await ctx["room"].set_manager(client_id, (websocket := ctx["ws"])):
        logger.info("client_id=%s unable to claim manager", client_id)
        await websocket.send_json({"error": "Could not claim manager"})


async def release_slot(ctx: dict):
    room = ctx["room"]
    if not await room.release_slot(ctx["client_id"]):
        await ctx["ws"].send_json({"error": "No slot associated with client"})
    elif room.game.is_started:
        await room.send_game_state()


async def start_game(ctx: dict):
    room = ctx["room"]
    if ctx["client_id"] == room.game.manager:
        try:
            room.game.start_game()
            await room.broadcast({"info": "Game started"})
            await room.send_game_state()
        except ValueError as exc:
            await ctx["ws"].send_json({"error": f"{exc}"})


async def take_turn(ctx: dict):
    room = ctx["room"]
    room.game.submit_action(ctx["client_id"], ctx["data"]["turn"])

    # Notify all connected players of the new state
    await room.send_game_state()


ACTION_HANDLERS = {
    "take_turn": take_turn,
    "claim_slot": claim_slot,
    "update_name": update_name,
    "claim_manager": claim_manager,
    "release_slot": release_slot,
    "start_game": start_game,
}


async def handle_ws_message(context: dict):
    action = context["data"].get("action")
    logger.info("client %s sent action %s", context["client_id"], action)

    if (handler := ACTION_HANDLERS.get(action)) is None:
        await context["ws"].send_json({"error": f"Unknown action: {action}"})
    else:
        await handler(context)
