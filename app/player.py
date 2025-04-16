# app/player.py

class Player:
    def __init__(self, player_id: str, stack: int):
        self.player_id = player_id
        self.stack = stack
        self.status = "connected"

    def disconnect(self):
        self.status = "disconnected"

    def reconnect(self):
        self.status = "connected"

    def is_connected(self):
        return self.status == "connected"

    # Placeholder for future methods
    def bet(self, amount):
        if amount > self.stack:
            raise ValueError("Insufficient chips")
        self.stack -= amount
        return amount

