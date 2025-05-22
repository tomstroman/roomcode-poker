import logging
import os
import random
import string
import uuid
from typing import Dict

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from app.engine.action_handlers import handle_ws_message
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

    await websocket.send_json(
        {
            "client_id": client_id,
            **room.common_payload(),
            "my_slot": None,
        }
    )

    game = room.game

    if not game.manager:
        await room.set_manager(client_id, websocket)

    await room.broadcast_slots()

    try:
        while True:
            try:
                data = await websocket.receive_json()
                context = dict(ws=websocket, room=room, client_id=client_id, data=data)
                await handle_ws_message(context)

            except Exception as exc:
                if isinstance(exc, WebSocketDisconnect):
                    raise
                elif isinstance(exc, RuntimeError) and "got 'websocket.close'" in str(
                    exc
                ):
                    raise WebSocketDisconnect

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
