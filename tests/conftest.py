from copy import deepcopy
from typing import Any, Dict, List, Optional

import pytest
from fastapi.websockets import WebSocketState

from app.api import rooms
from app.engine.room import Room
from app.game.base import Game, Player


class TrivialGame(Game):
    def __init__(self, players: int):
        self.players: Dict[int, Player] = {i: Player(i) for i in range(players)}
        self.manager: Optional[str] = None
        self.is_started: bool = False
        self.current_index: int = 0

    def get_public_state(self) -> dict:
        return {}

    def get_private_state(self, client_id: str) -> dict:
        return {}

    def submit_action(
        self, client_id: str, action: dict, force_turn_for_client: Optional[str] = None
    ) -> None:
        pass

    def get_current_player(self) -> Optional[str]:
        return self.players[self.current_index].client_id

    def is_game_over(self) -> bool:
        return False

    def get_final_result(self) -> dict:
        return {}

    def start_game(self) -> dict:
        self.is_started = True
        return {}


@pytest.fixture
def trivial_game():
    return TrivialGame(1)


@pytest.fixture
def trivial_room(trivial_game):
    code = "ABC123"
    return Room(code, trivial_game)


@pytest.fixture(autouse=True)
def clear_rooms():
    rooms.clear()


class FakeWebSocket:
    def __init__(self):
        self.sent_messages: List[Dict[str, Any]] = []
        self.next_message: Dict[str, Any] = {"action": "claim_slot", "slot_id": 0}
        self.application_state = WebSocketState.CONNECTED

    def stage_next_message(self, message: Dict[str, Any]):
        self.next_message = deepcopy(message)

    async def send_json(self, data: Dict[str, Any]):
        self.sent_messages.append(data)

    async def receive_json(self) -> Dict[str, Any]:
        return self.next_message


@pytest.fixture
def websocket():
    return FakeWebSocket()
