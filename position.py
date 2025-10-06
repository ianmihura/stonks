from functools import reduce
from card import get_value, is_big, is_face, is_long


SMALL_PAYOUT = 3
MID_PAYOUT = 5
BIG_PAYOUT = 10
STONK_PAYOUT = 20

BIG_SIZE_CUTOFF = 6
MAX_POSITION_VALUE = 10


class Position:
    long: int  # index of player
    short: int  # index of player
    has_house: bool
    cards: list[str]

    def __repr__(self):
        return f"[[L:{self.long}, S:{self.short}, pos:{self.cards}]]"

    def __init__(self, long: int, short: int, cards: list[str]):
        self.long = long
        self.short = short
        self.cards = cards
        self.has_house = ((long + 1) * (short + 1)) == 0

    def has_player(self, player_id: int) -> bool:
        """
        Given a player_id, return if they for part of this position
        """
        return (self.long == player_id) or (self.short == player_id)

    def is_player_long(self, player_id: int) -> int:
        """
        Given a player_id:
        - returns 1 if player is long
        - returns 0 if player is short
        - returns -1 if player is not part of this position
        """
        if self.long == player_id:
            return 1
        elif self.short == player_id:
            return 0
        else:
            return -1


def get_player_paid(market_card: str, position: Position) -> int:
    """Given a market_card, get the id of the player getting paid"""
    if is_long(market_card):
        return position.long
    else:
        return position.short


def get_value_position(position: Position) -> int:
    """Returns the card value of the position"""
    long_sum = 0
    short_sum = 0
    for c in position.cards:
        if is_long(c):
            long_sum += get_value(c)
        else:
            short_sum += get_value(c)

    if position.has_house:
        return max(long_sum, short_sum)
    else:
        return min(long_sum, short_sum)


def flat_positions(positions: list[Position]) -> list[str]:
    """Given a list of Positions, returns the flat list of the cards"""
    return reduce(lambda a, v: v.cards + a, positions, [])


def get_close_cost(position: Position) -> int:
    """Returns the cost of closing a position"""
    if get_value_position(position) > BIG_SIZE_CUTOFF:
        return BIG_PAYOUT
    else:
        return MID_PAYOUT


def get_payout_size(position: Position, market_card: str) -> int:
    """Returns the payout size of a position, according to game's rules"""
    position_value = get_value_position(position)
    is_big_position = position_value > BIG_SIZE_CUTOFF
    is_big_market = is_big(market_card)

    if is_big_market and is_big_position:
        if position_value >= MAX_POSITION_VALUE and is_face(market_card):
            return STONK_PAYOUT
        else:
            return BIG_PAYOUT

    elif is_big_market or is_big_position:
        return MID_PAYOUT

    else:
        return SMALL_PAYOUT
