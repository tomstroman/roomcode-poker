from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import string, random
from typing import Dict, List

app = FastAPI()

# Allow local development testing from any frontend origin
app.add_middleware(
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
        self.clients: List[WebSocket] = []
        self.game_state = {
            "players": [],  # List of dicts {"id":..., "stack":...}
            "actions": [],  # Append actions here as they happen
        }

    async def broadcast(self, message: dict):
        for client in self.clients:
            await client.send_json(message)

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.clients.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.clients:
            self.clients.remove(websocket)

@app.post("/create-game/")
async def create_game(stack_size: int = 5000):
    code = generate_code()
    while code in tables:
        code = generate_code()
    tables[code] = PokerTable(stack_size)
    return {"code": code}

@app.websocket("/ws/{code}/")
async def websocket_endpoint(websocket: WebSocket, code: str):
    table = tables.get(code)
    if not table:
        await websocket.close(code=1008)  # Policy violation
        return

    await table.connect(websocket)
    try:
        await table.broadcast({"event": "player_joined"})
        while True:
            data = await websocket.receive_json()
            # You would handle different actions here
            table.game_state["actions"].append(data)
            await table.broadcast(data)
    except WebSocketDisconnect:
        table.disconnect(websocket)
        await table.broadcast({"event": "player_left"})

