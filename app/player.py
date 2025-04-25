class Player:
    def __init__(self, player_id: str, stack: int) -> None:
        self.player_id = player_id
        self.stack = stack
        self.status = "connected"

    def disconnect(self) -> None:
        self.status = "disconnected"

    def reconnect(self) -> None:
        self.status = "connected"

    def is_connected(self) -> bool:
        return self.status == "connected"

    # Placeholder for future methods
    def bet(self, amount: int) -> int:
        if amount > self.stack:
            raise ValueError("Insufficient chips")
        self.stack -= amount
        return amount
