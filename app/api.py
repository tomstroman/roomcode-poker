import os
import random
import string
from typing import List

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from app.game.pass_pebble import PassThePebbleGame

router = APIRouter()

# Global in-memory game storage
games = {}


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
