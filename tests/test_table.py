from app.main import PokerTable


def test_create_table_with_stack():
    STACK = 5000
    table = PokerTable(STACK)
    assert table.game_state["stack_size"] == STACK
    assert table.players == {}
