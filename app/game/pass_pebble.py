from typing import Dict, Optional

from .base import Game, Player


class PassThePebbleGame(Game):
    """
    This implementation courtesy of ChatGPT.
    This game sounds terribly boring.
    Rules:
    - Two players, A and B.
    - There's a single "pebble."
    - On your turn, you must explicitly "pass" the pebble to the other player.
    - First player to reach 5 passes wins.
    """

    def __init__(self, players: int):
        self.players: Dict[int, Player] = {i: Player(i) for i in range(players)}
        self.manager: Optional[str] = None
        self.current_index = 0
        self.pass_count = 0
        self.max_passes = 5
        self.winner: Optional[str] = None

    def get_public_state(self) -> dict:
        return {
            "current_holder_index": self.current_index,
            "pass_count": self.pass_count,
            "is_game_over": self.is_game_over(),
        }

    def get_private_state(self, client_id: str) -> dict:
        return {}

    def submit_action(self, client_id: str, action: dict) -> None:
        if client_id != self.players[self.current_index].client_id:
            raise ValueError("Not your turn!")

        if action.get("action") != "pass":
            raise ValueError("Invalid action")

        self.pass_count += 1
        if self.pass_count >= self.max_passes:
            self.winner = self.players[self.current_index].display_name
        else:
            for _ in range(len(self.players)):
                self.current_index = (self.current_index + 1) % len(self.players)
                print(f"{self.current_index=}")
                if self.players[self.current_index].client_id:
                    break
            else:
                raise ValueError("No players!")

    def get_current_player(self) -> Optional[str]:
        return self.players[self.current_index].client_id

    def is_game_over(self) -> bool:
        return self.winner is not None

    def get_final_result(self) -> dict:
        if self.winner:
            return {"winner": self.winner}
        return {}

    def start_game(self) -> dict:
        return self.get_public_state()
