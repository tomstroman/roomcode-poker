import logging
from copy import deepcopy
from typing import Any, Callable, Dict, Optional

from fastapi import WebSocket
from fastapi.websockets import WebSocketState

from app.game.base import Game

logger = logging.getLogger()


class Room(dict):
    def __init__(self, code: str, game: Game, *args, **kwargs):
        super(Room, self).__init__(*args, **kwargs)
        self.code: str = code
        self.game: Game = game

    async def broadcast(self, message: Dict[str, Any]):
        for conn in self.values():
            await conn.send_json(message)

    async def broadcast_connections(self):
        num_conn = len(self)
        await self.broadcast(
            {
                "num_connections": num_conn,
                "available_slots": self.slot_availability(),
            }
        )

    def slot_availability(self) -> Dict[int, bool]:
        return {
            slot_id: player.client_id is None
            for slot_id, player in self.game.players.items()
        }

    def slots_by_client(self) -> Dict[str, int]:
        return {
            player.client_id: slot_id
            for slot_id, player in self.game.players.items()
            if player.client_id is not None
        }

    def player_names(self) -> Dict[int, Optional[str]]:
        return {
            slot_id: (player.display_name if player.client_id is not None else None)
            for slot_id, player in self.game.players.items()
        }

    def common_payload(self):
        return {
            "num_connections": len(self),
            "available_slots": self.slot_availability(),
            "names": self.player_names(),
        }

    async def broadcast_personalized(
        self, common: Dict[str, Any], personal: Dict[str, Callable]
    ):
        for client_id, conn in self.items():
            message = deepcopy(common)
            for key, lookup in personal.items():
                message[key] = lookup(client_id)
            await conn.send_json(message)

    async def broadcast_slots(self):
        personal = {
            "my_slot": lambda x: self.slots_by_client().get(x),
        }
        await self.broadcast_personalized(self.common_payload(), personal)

    async def claim_slot(self, slot_id: int, client_id: str) -> None:
        self.game.players[slot_id].set_client_id(client_id)
        await self.broadcast_slots()

    async def release_slot(self, client_id: str) -> bool:
        slots_by_client = self.slots_by_client()
        if (client_slot := slots_by_client.get(client_id)) is None:
            return False

        current_player_client_id = self.game.get_current_player()

        self.game.players[client_slot].set_client_id(None)

        if self.game.is_started and client_id == current_player_client_id:
            logger.info("current player released slot! Taking 'pass' action.")
            self.game.submit_action(
                client_id,
                {"action": "pass"},
                force_turn_for_client=current_player_client_id,
            )

        await self.broadcast_slots()
        return True

    async def set_manager(self, client_id: str, conn: WebSocket) -> bool:
        if self.game.manager is None:
            self.game.manager = client_id
            if (client_slot := self.slots_by_client().get(client_id)) is None:
                manager = "A spectator"
            else:
                manager = f"Player {client_slot}"
            await self.broadcast({"info": f"{manager} is the manager now"})
            await conn.send_json({"info": "You are the manager"})
            return True
        return False

    async def release_manager(self):
        self.game.manager = None
        await self.broadcast({"info": "There is no manager"})

    async def send_game_state(self):
        game = self.game
        for pid, ws in self.items():
            if ws.application_state != WebSocketState.CONNECTED:
                continue
            await ws.send_json(
                {
                    "public_state": game.get_public_state(),
                    "private_state": game.get_private_state(pid),
                    "your_turn": game.get_current_player() == pid,
                    "is_over": game.is_game_over(),
                    "final_result": (
                        game.get_final_result() if game.is_game_over() else None
                    ),
                }
            )
