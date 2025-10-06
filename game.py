from math import floor
from random import shuffle
from functools import reduce

from card import *
from position import (
    BIG_PAYOUT,
    MAX_POSITION_VALUE,
    Position,
    flat_positions,
    get_close_cost,
    get_payout_size,
    get_player_paid,
    get_value_position,
)
from strategy import Strategy
from atests import Ok, game_card_number, players_limited_cards, test_strategy


def log(*args):
    if is_printing:
        print(*args)


HOUSE_INIT_CHIPS = 999_999
HOUSE_PREVENTION_CUTOFF = 500_000
CARDS_PER_PLAYER = 6

total_players = 0
current_round = 0

is_printing = True


"""
A card is a string of 2 chars, see CARDS for examples
"""

Chips: list[int] = []
"""Stack of chips per player_id"""

Blinds: int = 0
"""Pot of blinds that gets paid out if there's a stonk payout"""

Hands: list[list[str]] = []
"""Hands per player_id"""

Strategies: list[Strategy] = []
"""Strategies per player_id"""

Deck: list[str] = CARDS.copy()
"""List of cards, draw from here"""

Discarded: list[str] = []
"""List of cards, useful for reshuffling"""

Positions: list[Position] = [] * len(Chips)
"""List of positions, unordered"""

Orderbook: dict[int, list[str]] = []
"""Dict of player_id mapped to list of cards they play this round"""


def reset_all():
    global Chips, Blinds, Hands, Strategies, Deck, Discarded, Positions, Orderbook
    Chips = []
    Blinds = 0
    Hands = []
    Strategies = []
    Deck = CARDS.copy()
    Discarded = []
    Positions = []
    Orderbook = {}


def init_game(num_players: int, init_chips: int) -> tuple[list[int], int]:
    """
    Configures a new game, with auto Strategies and one agent.
    Returns: Chips (final state), round_count.
    """
    Ok(CARDS_PER_PLAYER * (num_players + 1) <= len(CARDS), "Too many players")
    global Orderbook, total_players
    reset_all()

    total_players = num_players
    Orderbook = {}

    shuffle(Deck)

    """Setup players Chips, Hands and Strategies"""
    for player_id in range(num_players):
        Chips.append(init_chips)

        hand: list[str] = []
        for _ in range(CARDS_PER_PLAYER):
            hand.append(Deck.pop())
        Hands.append(hand)

        Strategies.append(Strategy(player_id, hand))
        # TODO if player, init a player strategy
    Strategies[-1].is_agent = True

    """The house is the last chip holder, player_id=-1"""
    Chips.append(HOUSE_INIT_CHIPS)

    return gameloop()


def gameloop() -> tuple[list[int], int]:
    """
    Plays automatically until a winner is found.
    Returns: Chips (final state), round_count.
    """
    global Orderbook, Deck, Discarded, current_round
    current_round = 0

    while is_playing():
        current_round += 1
        game_card_number(Positions, Hands, Deck, Discarded)

        # TODO broke players dont pay blinds
        pay_blind()

        """Market opens: players open and close positions"""
        for i in range(total_players):
            """Every round a different player starts"""
            player_id: int = (i + current_round) % total_players
            if Chips[player_id] <= 0:
                continue

            hand = Hands[player_id]
            cs = Strategies[player_id]

            if not cs.compute_current_action(hand.copy(), Positions, Chips, Orderbook, Blinds):
                continue

            f_open = list(cs.open_cards.keys())
            f_close = [cs.close_cards[c] for c in cs.close_cards if cs.close_cards[c]]
            new_cards = f_open + f_close
            test_strategy(new_cards, hand)

            """Opening and closing positions reveals cards"""
            [s.update_state(new_cards) for s in Strategies if s.player_id != player_id]

            """Implements strategy's actions"""
            [hand.remove(card) for card in new_cards]

            for my_card in cs.open_cards:
                if type(cs.open_cards[my_card]) == Position:
                    """Double down: WIP"""
                    # TODO double down
                    pass
                elif type(cs.open_cards[my_card]) == str:
                    """Market taker"""
                    active_card__id = my_card + "_" + str(player_id)
                    create_position(active_card__id, cs.open_cards[my_card])
                else:
                    """Market maker"""
                    if Orderbook.get(player_id):
                        Orderbook[player_id].append(my_card)
                    else:
                        Orderbook[player_id] = [my_card]
            
            for my_position in cs.close_cards:
                my_card = cs.close_cards[my_position]
                if type(my_card) == str:
                    close_positions(my_position, my_card, player_id)
                    # TODO may close position with more than one card
                else:
                    close_positions(my_position, None, player_id)
                    Chips[player_id] -= get_close_cost(my_position)

            """Makes sure we didnt break anything"""
            players_limited_cards(Positions, Hands, Chips, Orderbook, CARDS_PER_PLAYER)

        """Match rest of orderbook with house"""
        match_algo_house()

        """Market closes: market moves, update state of strategies"""
        if len(Deck) == 0:
            Deck = Discarded.copy()
            shuffle(Deck)
            market_card = Deck.pop()
            Discarded = [market_card]

            cards = flat_positions(Positions)
            cards.append(market_card)
            [s.update_state(cards + Hands[s.player_id], reset=True) for s in Strategies]
        else:
            market_card = Deck.pop()
            Discarded.append(market_card)
            [s.update_state([market_card]) for s in Strategies]
        
        log("Market card", market_card)

        """Payout positions"""
        for p in Positions:
            payout = get_payout_size(p, market_card)

            if is_long(market_card):
                Chips[p.long] += payout
                Chips[p.short] -= payout
            else:
                Chips[p.long] -= payout
                Chips[p.short] += payout

            """Pays the house its due"""
            if p.has_house:
                Chips[p.long * p.short * -1] -= 1

        payout_blinds(market_card)

        """Bankrupt players: close positions"""
        for position in Positions:
            if Chips[position.long] <= 0 or Chips[position.short] <= 0:
                close_positions(position, None, -1)

        """Bankrupt players: discard hand"""
        for player_id, hand in enumerate(Hands):
            if Chips[player_id] <= 0:
                Discarded.extend(hand)
                del hand[:]

    return Chips, current_round


def create_position(active_card__id: str, passive_card__id: str):
    """
    Creates a new Position from the given two cards,
    removes passive_card from the orderbook
    """
    [passive_card, p_player_id] = passive_card__id.split("_")
    [active_card, a_player_id] = active_card__id.split("_")
    p_player_id = int(p_player_id)
    a_player_id = int(a_player_id)

    Orderbook[p_player_id].remove(passive_card)

    if is_long(active_card):
        position = Position(a_player_id, p_player_id, [active_card, passive_card])
    else:
        position = Position(p_player_id, a_player_id, [active_card, passive_card])
    Positions.append(position)


def match_algo_house():
    """Matches remaining orderbook with the house"""
    global Orderbook

    for player_id in Orderbook:
        player_cards = Orderbook[player_id]
        for card in player_cards:
            if is_long(card):
                position = Position(player_id, -1, [card])
            else:
                position = Position(-1, player_id, [card])
            Positions.append(position)

    Orderbook = {}


def close_positions(close_pos: Position, close_card: str, close_player_id: int):
    """
    Closes the position with the card, discards all cards and deals new cards to palyers.
    Will throw an error if it cant close the position with the given cards.
    """
    global Positions, Discarded, Deck

    if close_card and close_player_id >= 0:
        """Verifying we can close the position. Will throw an error if it cant"""
        is_value_ok = get_value(close_card) >= get_value_position(close_pos)
        is_color_ok = is_long(close_card) != close_pos.is_player_long(close_player_id)
        # TODO uncoment line below
        # Ok(close_card[0] == "A" or (is_value_ok and is_color_ok), f"Strategy Error: {close_player_id} cant close position {close_pos} with {close_card}")
        Discarded.append(close_card)
    Discarded.extend(close_pos.cards)
    Positions = [p for p in Positions if p != close_pos]

    """Deals cards to players: 2 cards to one forcing the close, one card to the other"""
    did_reshuffle = False

    deals = [close_pos.long, close_pos.short]
    if close_card:
        """Deal twice to player if they closed the position with cards"""
        deals.append(close_player_id)
    for player_id in [p_id for p_id in deals if p_id != -1]:
        if len(Deck) == 0:
            Deck = Discarded.copy()
            Discarded = []
            shuffle(Deck)
            did_reshuffle = True
        card = Deck.pop()
        Hands[player_id].append(card)
        Strategies[player_id].update_state([card])

    if did_reshuffle:
        """Reshuffling resets all Strategy's state"""
        for i, strategy in enumerate(Strategies):
            strategy.update_state(Hands[i] + flat_positions(Positions), reset=True)


def is_playing() -> bool:
    """
    Will play until there's only one chipholder left, excluding the house (id=-1)
    """
    return reduce(lambda a, v: (v > 0) + a, Chips[:-1], 0) > 1


def pay_blind():
    global Blinds, Chips

    player_id = (total_players + current_round) % total_players
    Chips[player_id] -= BIG_PAYOUT
    Blinds += BIG_PAYOUT


def payout_blinds(market_card: str):
    global Blinds, Chips
    paid_players = []
    for p in Positions:
        if get_value_position(p) == MAX_POSITION_VALUE:
            paid_players.append(get_player_paid(market_card, p))

    if len(paid_players) > 0:
        for player_id in paid_players:
            Chips[player_id] += floor(Blinds / len(paid_players))
        Blinds = 0
