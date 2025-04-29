import os
import random
import string
from collections import defaultdict
from typing import List

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.websockets import WebSocketState
from pydantic import BaseModel

from app.game.base import Game
from app.game.pass_pebble import PassThePebbleGame

router = APIRouter()

# Global in-memory game storage
games = {}
connections: defaultdict = defaultdict(dict)  # { code: {player_id: websocket} }


def generate_code(length: int = 4) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


class CreateGameRequest(BaseModel):
    game_type: str
    players: List[str]


@router.post("/create-game/")
async def create_game(request: CreateGameRequest) -> dict:
    if request.game_type == "pass_the_pebble":
        game = PassThePebbleGame(request.players)
    else:
        raise HTTPException(status_code=400, detail="Unknown game type")

    code = generate_code()
    while code in games:
        code = generate_code()
    games[code] = game
    return {"code": code}


@router.post("/submit-action/{code}/{player_id}/")
async def submit_action(code: str, player_id: str, action: dict):
    if code not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[code]

    if game.is_game_over():
        return {"status": "Game already over", "final_result": game.get_final_result()}

    try:
        game.submit_action(player_id, action)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status": "Action accepted"}


@router.get("/game-state/{code}/")
async def game_state(code: str):
    if code not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[code]
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


@router.websocket("/ws/{code}/{player_id}/")
async def game_ws(websocket: WebSocket, code: str, player_id: str):
    await websocket.accept()

    if code not in games:
        await websocket.send_json({"error": "Game not found"})
        await websocket.close()
        return

    game = games[code]
    connections[code][player_id] = websocket

    try:
        # Send initial state
        await send_game_state(game, code)

        while True:
            message = await websocket.receive_json()
            try:
                game.submit_action(player_id, message)
            except ValueError as e:
                await websocket.send_json({"error": str(e)})
                continue

            # Notify all connected players of the new state
            await send_game_state(game, code)

    except WebSocketDisconnect:
        del connections[code][player_id]
        if not connections[code]:  # Cleanup if empty
            del connections[code]


async def send_game_state(game: Game, code: str):
    for pid, ws in connections[code].items():
        if ws.application_state != WebSocketState.CONNECTED:
            continue
        await ws.send_json(
            {
                "public_state": game.get_public_state(),
                "private_state": game.get_private_state(pid),
                "your_turn": game.get_current_player() == pid,
                "is_over": game.is_game_over(),
                "final_result": (
                    game.get_final_result() if game.is_game_over() else None
                ),
            }
        )
