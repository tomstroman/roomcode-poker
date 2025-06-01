from game.pass_pebble import PassThePebbleGame


def test_pass_pebble__init():
    game = PassThePebbleGame(1)
    assert len(game.players) == 1
