import pytest
from game.pass_pebble import PassThePebbleGame


def test_pass_pebble__init():
    game = PassThePebbleGame(1)
    assert len(game.players) == 1


def test_pass_pebble__public_state():
    game = PassThePebbleGame(1)
    want = {
        "current_holder_index": 0,
        "pass_count": 0,
        "is_game_over": False,
    }

    got = game.get_public_state()
    assert got == want


def test_pass_pebble__private_state__non_player():
    game = PassThePebbleGame(1)
    client_id = "foo"
    want = {
        "available_actions": {},
    }

    got = game.get_private_state(client_id)
    assert got == want


@pytest.mark.parametrize(
    "winner,want_result",
    [
        (None, {}),
        ("foo", {"winner": "foo"}),
    ],
)
def test_pass_pebble__get_final_result(winner, want_result):
    game = PassThePebbleGame(1)
    game.winner = winner

    got = game.get_final_result()
    assert got == want_result


def test_pass_pebble__start_game__no_players__exception():
    game = PassThePebbleGame(1)
    with pytest.raises(ValueError) as exc:
        game.start_game()
    assert "Cannot start game with no players" in str(exc)


def test_pass_pebble__start_game__success():
    game = PassThePebbleGame(1)
    game.players[0].client_id = "foo"
    assert not game.is_started
    game.start_game()
    assert game.is_started


@pytest.mark.parametrize("current_index", [0, 1])
@pytest.mark.parametrize("client_id", ["nobody", "foo", "bar"])
def test_pass_pebble_get_available_actions(client_id, current_index):
    my_turn_actions = {"pass": None}
    not_my_turn_actions = {}

    if (client_id == "foo" and current_index == 0) or (
        client_id == "bar" and current_index == 1
    ):
        want_actions = my_turn_actions
    else:
        want_actions = not_my_turn_actions

    game = PassThePebbleGame(2)
    game.players[0].client_id = "foo"
    game.players[1].client_id = "bar"
    game.current_index = current_index
    got_actions = game._get_available_actions(client_id)
    assert got_actions == want_actions


def test_pass_pebble__submit_action__out_of_turn__raises():
    game = PassThePebbleGame(1)
    game.players[0].client_id = "foo"
    with pytest.raises(ValueError) as exc:
        game.submit_action("bar", {"action": "pass"})
    assert "Not your turn!" in str(exc)


def test_pass_pebble__submit_action__invalid__raises():
    game = PassThePebbleGame(1)
    game.players[0].client_id = "foo"
    with pytest.raises(ValueError) as exc:
        game.submit_action("foo", {"action": "pass_out"})
    assert "Invalid action" in str(exc)


@pytest.mark.parametrize("game_size", [3, 4, 5])
@pytest.mark.parametrize(
    "players,next_index",
    [
        (["foo"], 0),
        (["foo", "bar"], 1),
        (["foo", "bar", "baz"], 1),
    ],
)
def test_pass_pebble__submit_action__pass__increments_count_and_turn(
    players, next_index, game_size
):
    game = PassThePebbleGame(game_size)
    for i, client_id in enumerate(players):
        game.players[i].client_id = client_id
    assert game.current_index == 0
    assert game.get_current_player() == "foo"
    assert game.pass_count == 0

    game.submit_action("foo", {"action": "pass"})
    assert game.current_index == next_index
    assert game.pass_count == 1


def test_pass_pebble__submit_action__detects_winner():
    PLAYER_0 = "Player 0"
    game = PassThePebbleGame(1)
    game.players[0].client_id = "foo"
    assert game.max_passes == 5
    assert game.players[0].display_name == PLAYER_0
    game.pass_count = 4
    game.submit_action("foo", {"action": "pass"})
    assert game.winner == PLAYER_0
