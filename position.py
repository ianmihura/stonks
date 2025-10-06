from functools import reduce
from card import get_value, is_long


class Position:
    long: int  # index of player
    short: int  # index of player
    is_house: bool
    cards: list[str]

    def __repr__(self):
        return f"[[L:{self.long}, S:{self.short}, pos:{self.cards}]]"

    def __init__(self, long: int, short: int, cards: list[str]):
        self.long = long
        self.short = short
        self.cards = cards
        self.is_house = ((long + 1) * (short + 1)) < 0

    def has_player(self, player_id: int) -> bool:
        """
        Given a player_id, return if they for part of this position
        """
        return (self.long == player_id) or (self.short == player_id)

    def is_player_long(self, player_id: int) -> int:
        """
        Given a player_id:
        - returns 1 if player is long party
        - returns 0 if player is short party
        - returns -1 otherwise
        """
        if self.long == player_id:
            return 1
        elif self.short == player_id:
            return 0
        else:
            return -1


def get_value_position(position: Position) -> int:
    long_sum = 0
    short_sum = 0
    for c in position.cards:
        if is_long(c):
            long_sum += get_value(c)
        else:
            short_sum += get_value(c)
    return min(long_sum, short_sum)


def flat_positions(position: list[Position]) -> list[str]:
    """Given a list of Positions, returns the flat list of the cards"""
    return reduce(lambda a, v: v.cards + a, position, [])
