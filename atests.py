from card import CARDS
from position import Position, flat_positions


def Ok(ok: bool, msg: str = ""):
    """Wrap basic assert in a function to turn it off when we want silent errors"""
    assert ok, msg


def players_limited_cards(
    Positions: list[Position],
    Hands: list[list[str]],
    Chips: list[int],
    CARDS_PER_PLAYER: int,
) -> bool:
    for player_id, hand in enumerate(Hands):
        if Chips[player_id] <= 0:
            continue
        num = len([c for c in hand])
        num += len(["1" for p in Positions if p.has_player(player_id)])
        if num != CARDS_PER_PLAYER:
            assert False, f"Main Error: player {player_id} has {num} cards"
    return True


def game_card_number(
    Positions: list[Position],
    Hands: list[list[str]],
    Deck: list[str],
    Discarded: list[str],
) -> bool:
    Ok(
        len(
            flat_positions(Positions) + [c for h in Hands for c in h] + Deck + Discarded
        )
        == len(CARDS),
        "Main Error: game's cards",
    )
    return True


def test_strategy(new_cards: list[str], hand: list[str]) -> bool:
    Ok(
        len([c for c in new_cards if c not in hand]) == 0,
        "Strategy Error: card(s) not in hand",
    )
    Ok(len(new_cards) <= len(hand), "Strategy Error: too many cards")
    Ok(len(new_cards) == len(set(new_cards)), "Strategy Error: repeated cards")

    return True
