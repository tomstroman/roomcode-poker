import logging
import os
import random
import string
import uuid
from copy import deepcopy
from typing import Any, Callable, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.websockets import WebSocketState
from pydantic import BaseModel

from app.game.base import Game
from app.game.pass_pebble import PassThePebbleGame

router = APIRouter()

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

        if client_id == current_player_client_id:
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


rooms: Dict[str, Room] = dict()  # { code: {player_id: websocket} }


def generate_code(length: int = 4) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


class CreateGameRequest(BaseModel):
    game_type: str
    players: int


@router.post("/create-game/")
async def create_game(request: CreateGameRequest) -> dict:
    if request.game_type == "pass_the_pebble":
        game = PassThePebbleGame(request.players)
    else:
        raise HTTPException(status_code=400, detail="Unknown game type")

    code = generate_code()
    while code in rooms:
        code = generate_code()
    rooms[code] = Room(code, game)
    return {"code": code}


@router.get("/game-state/{code}/")
async def game_state(code: str):
    if code not in rooms:
        raise HTTPException(status_code=404, detail="Game not found")

    game = rooms[code].game
    return {
        "public_state": game.get_public_state(),
        "is_over": game.is_game_over(),
        "final_result": game.get_final_result() if game.is_game_over() else None,
    }


# Basic UI page
@router.get("/play/pass-the-pebble/", response_class=HTMLResponse)
async def play_pass_the_pebble(request: Request):
    file_path = os.path.join("app", "static", "pass_the_pebble.html")
    return FileResponse(file_path)


@router.websocket("/ws/{code}/")
async def game_ws(websocket: WebSocket, code: str):
    await websocket.accept()
    if (room := rooms.get(code)) is None:
        await websocket.send_json({"error": "Game room not found"})
        await websocket.close()
        return

    client_id = str(uuid.uuid4())[:8]
    logger.info("WebSocket client_id=%s connected at %s", client_id, websocket.client)
    room[client_id] = websocket

    game = room.game

    if not game.manager:
        await room.set_manager(client_id, websocket)

    await room.broadcast_slots()
    #    for conn in room.values():
    #        await conn.send_json({"num_connections": len(connections[code])})

    await websocket.send_json(
        {
            "client_id": client_id,
            **room.common_payload(),
            "my_slot": None,
        }
    )

    try:
        while True:
            try:
                data = await websocket.receive_json()
                action = data.get("action")

                if action == "claim_slot":
                    slot = data["slot"]
                    if game.players[slot].client_id is None:
                        logger.info("client_id=%s claiming slot %s", client_id, slot)
                        await room.claim_slot(slot, client_id)
                    else:
                        await websocket.send_json(
                            {"error": f"Slot {slot} already claimed"}
                        )

                elif action == "update_name":
                    player = game.players[(slot := data["slot"])]
                    if player.client_id == client_id:
                        logger.info(
                            "client_id=%s (slot %s) updating name from %s to %s",
                            client_id,
                            slot,
                            player.display_name,
                            (name := data["name"]),
                        )
                        player.set_display_name(name)
                        await room.broadcast_slots()
                    else:
                        await websocket.send_json(
                            {"error": f"Cannot change name for {slot=}"}
                        )

                elif action == "claim_manager":
                    logger.info("client_id=%s attempting to claim manager", client_id)
                    if not await room.set_manager(client_id, websocket):
                        logger.info("client_id=%s unable to claim manager", client_id)
                        await websocket.send_json({"error": "Could not claim manager"})

                elif action == "release_slot":
                    if not await room.release_slot(client_id):
                        await websocket.send_json(
                            {"error": "No slot associated with client"}
                        )
                    else:
                        await send_game_state(room)

                elif action == "start_game":
                    if client_id == game.manager:
                        try:
                            game.start_game()
                            await room.broadcast({"info": "Game started"})
                            await send_game_state(room)
                        except ValueError as exc:
                            await websocket.send_json({"error": f"{exc}"})

                elif action == "take_turn":
                    game.submit_action(client_id, data["turn"])

                    # Notify all connected players of the new state
                    await send_game_state(room)
            except Exception as exc:
                if isinstance(exc, WebSocketDisconnect):
                    raise
                logger.exception("Error handling WebSocket message: %r", exc)
                await websocket.send_json(
                    {"error": "Server error while handling your action"}
                )

    except WebSocketDisconnect:
        logger.info("client_id=%s disconnected from room %s!", client_id, room.code)
        del room[client_id]
        await room.release_slot(client_id)
        if room:
            if game.manager == client_id:
                room.release_manager()
            await room.broadcast_slots()
            await send_game_state(room)
        else:
            del room


async def send_game_state(room: Room):
    game = room.game
    for pid, ws in room.items():
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
