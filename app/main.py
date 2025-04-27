import random
import string
from typing import Dict

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.game.base import CreateGameRequest, Game, PokerTable
from app.ws_test import ws_test_html

fastapi_app = FastAPI()

# Allow local development testing from any frontend origin
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store all active games in memory
active_games: Dict[str, Game] = {}

game_types = {
    "poker": PokerTable,
}


def generate_code(length: int = 4) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


@fastapi_app.post("/create-game/")
async def create_game(request: CreateGameRequest) -> dict:
    if game_class := game_types.get(request.game_type):
        try:
            game = game_class(request)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid parameters for game")
    else:
        raise HTTPException(status_code=404, detail="Game type not recognized")

    code = generate_code()
    while code in active_games:
        code = generate_code()
    active_games[code] = game
    return {"code": code}


@fastapi_app.websocket("/ws/{code}/{player_id}/")
async def websocket_endpoint(websocket: WebSocket, code: str, player_id: str) -> None:
    game = active_games.get(code)
    if not game:
        await websocket.close(code=1008)  # Policy violation
        return

    success = await game.connect(websocket, player_id)
    if not success:
        return
    try:
        await game.broadcast({"event": "player_joined", "player_id": player_id})
        while True:
            data = await websocket.receive_json()
            game.game_state["actions"].append(data)
            await game.broadcast(data)
    except WebSocketDisconnect:
        game.disconnect(websocket)
        await game.broadcast({"event": "player_left", "player_id": player_id})


@fastapi_app.get("/ws-test/", response_class=HTMLResponse)
async def websocket_test_page() -> str:
    return ws_test_html
