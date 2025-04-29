import os
import random
import string
import uuid
from collections import defaultdict

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
    players: int


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


@router.websocket("/ws/{code}/")
async def game_ws(websocket: WebSocket, code: str):
    await websocket.accept()
    player_id = str(uuid.uuid4())[:8]

    if (game := games.get(code)) is None:
        await websocket.send_json({"error": "Game not found"})
        await websocket.close()
        return

    if not game.creator:
        game.creator = player_id
        await websocket.send_json({"info": "You are the creator"})

    await websocket.send_json(
        {
            "player_id": player_id,
            "available_slots": [k for k, v in game.players.items() if v is None],
        }
    )
    connections[code][player_id] = websocket

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "claim_slot":
                slot = data["slot"]
                if game.players.get(slot) is None:
                    game.players[slot] = player_id
                    for conn in connections[code].values():
                        await conn.send_json(
                            {
                                "available_slots": [
                                    k for k, v in game.players.items() if v is None
                                ]
                            }
                        )
                else:
                    await websocket.send_json({"error": f"Slot {slot} already claimed"})
            elif action == "start_game":
                if player_id == game.creator:
                    # game.start_game()
                    for conn in connections[code].values():
                        await conn.send_json({"info": "Game started"})
            elif action == "take_turn":
                game.submit_action(player_id, data["turn"])

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
