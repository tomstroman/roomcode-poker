import random
import string
from typing import Any, Dict, List, TypedDict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.player import Player
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
active_games: Dict[str, "PokerTable"] = {}


def generate_code(length: int = 4) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


class GameState(TypedDict):
    stack_size: int
    players: Dict[str, Any]
    actions: List[Dict[str, Any]]


class PokerTable:
    def __init__(self, stack_size: int):
        self.stack_size = stack_size
        self.clients: Dict[str, WebSocket] = {}
        self.players: Dict[str, Player] = {}
        self.game_state: GameState = {
            "stack_size": stack_size,
            "players": {},  # Will be populated from Player instances
            "actions": [],
        }

    async def connect(self, websocket: WebSocket, player_id: str) -> bool:
        await websocket.accept()

        # Reject if already connected
        if player_id in self.clients:
            await websocket.close(code=1008)
            return False

        if player_id in self.players:
            self.players[player_id].reconnect()
        else:
            self.players[player_id] = Player(player_id, self.stack_size)

        self.clients[player_id] = websocket
        self.update_game_state_players()
        return True

    def disconnect(self, websocket: WebSocket) -> None:
        for pid, sock in list(self.clients.items()):
            if sock == websocket:
                self.players[pid].disconnect()
                del self.clients[pid]
                break
        self.update_game_state_players()

    def update_game_state_players(self) -> None:
        self.game_state["players"] = {
            pid: {
                "stack": p.stack,
                "status": p.status,
            }
            for pid, p in self.players.items()
        }

    async def broadcast(self, message: dict) -> None:
        for ws in self.clients.values():
            await ws.send_json(message)


@fastapi_app.post("/create-game/")
async def create_game(stack_size: int = 5000) -> dict:
    code = generate_code()
    while code in active_games:
        code = generate_code()
    active_games[code] = PokerTable(stack_size)
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
