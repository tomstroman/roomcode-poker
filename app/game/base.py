from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Optional


class Player:
    def __init__(self, slot_index: int):
        self.slot_index: int = slot_index
        self.display_name: str = f"Player {slot_index}"
        self.client_id: Optional[str] = None

    def set_display_name(self, display_name: str):
        self.display_name = display_name

    def set_client_id(self, client_id: Optional[str]):
        self.client_id = client_id


@dataclass
class Game(ABC):
    players: Dict[int, Player] = field(default_factory=dict)
    manager: Optional[str] = field(default_factory=str)
    is_started: bool = field(default_factory=bool)

    @abstractmethod
    def get_public_state(self) -> dict:
        pass  # pragma: no cover

    @abstractmethod
    def get_private_state(self, client_id: str) -> dict:
        pass  # pragma: no cover

    @abstractmethod
    def submit_action(
        self, client_id: str, action: dict, force_turn_for_client: Optional[str] = None
    ) -> None:
        pass  # pragma: no cover

    @abstractmethod
    def get_current_player(self) -> Optional[str]:
        pass  # pragma: no cover

    @abstractmethod
    def is_game_over(self) -> bool:
        pass  # pragma: no cover

    @abstractmethod
    def get_final_result(self) -> dict:
        pass  # pragma: no cover

    @abstractmethod
    def start_game(self) -> dict:
        pass  # pragma: no cover
