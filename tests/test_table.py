from app.game.base import CreateGameRequest, PokerTable


def test_create_table_with_stack():
    STACK = 5000
    # TODO: anything but this
    request = CreateGameRequest(game_type="poker", stack_size=STACK)
    table = PokerTable(request)
    assert table.game_state["stack_size"] == STACK
    assert table.players == {}
