import logging
import os
import random
import string
import uuid
from typing import Dict

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from app.engine.action_handlers import ACTION_HANDLERS
from app.engine.room import Room
from app.game.pass_pebble import PassThePebbleGame

router = APIRouter()

logger = logging.getLogger()


rooms: Dict[str, Room] = dict()  # { code: {player_id: websocket} }


def generate_code(length: int = 4) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


class CreateGameRequest(BaseModel):
    game_type: str
    players: int


@router.post("/create-game/")
async def create_game(request: CreateGameRequest) -> dict:
    if request.game_type == "pass_the_pebble":
        game = PassThePebbleGame(request.players)
    else:
        raise HTTPException(status_code=400, detail="Unknown game type")

    code = generate_code()
    while code in rooms:
        code = generate_code()
    rooms[code] = Room(code, game)
    return {"code": code}


@router.get("/game-state/{code}/")
async def game_state(code: str):
    if code not in rooms:
        raise HTTPException(status_code=404, detail="Game not found")

    game = rooms[code].game
    return {
        "public_state": game.get_public_state(),
        "is_over": game.is_game_over(),
        "final_result": game.get_final_result() if game.is_game_over() else None,
    }


# Basic UI page
@router.get("/play/pass-the-pebble/", response_class=HTMLResponse)
async def play_pass_the_pebble(request: Request):
    file_path = os.path.join("app", "static", "pass_the_pebble.html")
    return FileResponse(file_path)


@router.websocket("/ws/{code}/")
async def game_ws(websocket: WebSocket, code: str):
    await websocket.accept()
    if (room := rooms.get(code)) is None:
        await websocket.send_json({"error": "Game room not found"})
        await websocket.close()
        return

    client_id = str(uuid.uuid4())[:8]
    logger.info("WebSocket client_id=%s connected at %s", client_id, websocket.client)
    room[client_id] = websocket

    game = room.game

    if not game.manager:
        await room.set_manager(client_id, websocket)

    await room.broadcast_slots()
    #    for conn in room.values():
    #        await conn.send_json({"num_connections": len(connections[code])})

    await websocket.send_json(
        {
            "client_id": client_id,
            **room.common_payload(),
            "my_slot": None,
        }
    )

    try:
        while True:
            try:
                data = await websocket.receive_json()
                context = dict(ws=websocket, room=room, client_id=client_id, data=data)
                action = data.get("action")
                logger.info("client %s sent action %s", client_id, action)

                if (handler := ACTION_HANDLERS.get(action)) is None:
                    await websocket.send_json({"error": f"Unknown action: {action}"})
                else:
                    await handler(context)

            except Exception as exc:
                if isinstance(exc, WebSocketDisconnect):
                    raise
                logger.exception("Error handling WebSocket message: %r", exc)
                await websocket.send_json(
                    {"error": "Server error while handling your action"}
                )

    except WebSocketDisconnect:
        logger.info("client_id=%s disconnected from room %s!", client_id, room.code)
        del room[client_id]
        await room.release_slot(client_id)
        if room:
            if game.manager == client_id:
                await room.release_manager()
            await room.broadcast_slots()
            await room.send_game_state()
        else:
            del room
