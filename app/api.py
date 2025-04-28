from typing import List

from fastapi import APIRouter, HTTPException  # , Request

from app.game.pass_pebble import PassThePebbleGame

# from fastapi.responses import HTMLResponse


router = APIRouter()

# Global in-memory game storage
games = {}


@router.post("/create-game/")
async def create_game(game_type: str, players: List[str]) -> dict:
    if game_type == "pass_the_pebble":
        game = PassThePebbleGame(players)
    else:
        raise HTTPException(status_code=400, detail="Unknown game type")

    code = "abcd"  # TODO: generate random roomcodes
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
# @router.get("/play/pass-the-pebble/", response_class=HTMLResponse)
# async def play_pass_the_pebble(request: Request):
#     return templates.TemplateResponse("pass_the_pebble.html", {"request": request})
