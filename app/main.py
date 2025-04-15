from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import string, random
from typing import Dict, List

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

# Store all active tables in memory
tables: Dict[str, "PokerTable"] = {}

def generate_code(length=4):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

class PokerTable:
    def __init__(self, stack_size: int):
        self.stack_size = stack_size
        self.clients: dict[str, WebSocket] = {}  # Now mapping player_id -> websocket
        self.game_state = {
            "players": {},
            "actions": [],
            # other game state data here
        }

    async def connect(self, websocket: WebSocket, player_id: str):
        await websocket.accept()
        self.clients[player_id] = websocket
        self.game_state["players"][player_id] = {
            "stack": self.stack_size,
            "status": "connected"
        }

    def disconnect(self, websocket: WebSocket):
        # Remove by matching the WebSocket object
        player_id = next((pid for pid, ws in self.clients.items() if ws == websocket), None)
        if player_id:
            self.clients.pop(player_id, None)
            if player_id in self.game_state["players"]:
                self.game_state["players"][player_id]["status"] = "disconnected"

    async def broadcast(self, message: dict):
        for client in self.clients.values():
            await client.send_json(message)


@fastapi_app.post("/create-game/")
async def create_game(stack_size: int = 5000):
    code = generate_code()
    while code in tables:
        code = generate_code()
    tables[code] = PokerTable(stack_size)
    return {"code": code}

@fastapi_app.websocket("/ws/{code}/{player_id}/")
async def websocket_endpoint(websocket: WebSocket, code: str, player_id: str):
    table = tables.get(code)
    if not table:
        await websocket.close(code=1008)  # Policy violation
        return

    await table.connect(websocket, player_id)
    try:
        await table.broadcast({"event": "player_joined", "player_id": player_id})
        while True:
            data = await websocket.receive_json()
            table.game_state["actions"].append(data)
            await table.broadcast(data)
    except WebSocketDisconnect:
        table.disconnect(websocket)
        await table.broadcast({"event": "player_left", "player_id": player_id})


@fastapi_app.get("/ws-test/", response_class=HTMLResponse)
async def websocket_test_page():
    return ws_test_html
