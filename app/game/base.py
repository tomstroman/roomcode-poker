from typing import Any, Dict, List, TypedDict

from fastapi import WebSocket

from app.player import Player


class Game:
    """
    During transition, this class still has some poker-specific
    aspects but after abstraction work is finished, that won't
    persist.
    """

    def __init__(self):
        self.clients: Dict[str, WebSocket] = {}
        self.players: Dict[str, Player] = {}
        self.stack_size = None

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
        raise NotImplementedError

    async def broadcast(self, message: dict) -> None:
        for ws in self.clients.values():
            await ws.send_json(message)


class GameState(TypedDict):
    stack_size: int
    players: Dict[str, Any]
    actions: List[Dict[str, Any]]


class PokerTable(Game):
    def __init__(self, stack_size: int):
        super(PokerTable, self).__init__()
        self.stack_size = stack_size
        self.game_state: GameState = {
            "stack_size": stack_size,
            "players": {},  # Will be populated from Player instances
            "actions": [],
        }

    def update_game_state_players(self) -> None:
        self.game_state["players"] = {
            pid: {
                "stack": p.stack,
                "status": p.status,
            }
            for pid, p in self.players.items()
        }
