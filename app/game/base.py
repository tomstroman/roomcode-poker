from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypedDict

from fastapi import WebSocket
from pydantic import BaseModel

from app.player import Player


class Game(ABC):
    @abstractmethod
    def get_public_state(self) -> dict:
        pass

    @abstractmethod
    def get_private_state(self, player_id: str) -> dict:
        pass

    @abstractmethod
    def submit_action(self, player_id: str, action: dict) -> None:
        pass

    @abstractmethod
    def get_current_player(self) -> str:
        pass

    @abstractmethod
    def is_game_over(self) -> bool:
        pass

    @abstractmethod
    def get_final_result(self) -> dict:
        pass


class CreateGameRequest(BaseModel):
    game_type: str
    # poker
    stack_size: Optional[int] = None


class GameState(TypedDict):
    stack_size: int
    players: Dict[str, Any]
    actions: List[Dict[str, Any]]


class LegacyGame:
    """
    During transition, this class still has some poker-specific
    aspects but after abstraction work is finished, that won't
    persist.
    """

    def __init__(self):
        self.clients: Dict[str, WebSocket] = {}
        self.players: Dict[str, Player] = {}
        self.stack_size = None
        self.game_state: GameState

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


class PokerTable(LegacyGame):
    def __init__(self, request: CreateGameRequest):
        super(PokerTable, self).__init__()
        if (stack_size := getattr(request, "stack_size", None)) is None:
            raise ValueError("stack_size undefined")

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
