from random import shuffle
from functools import reduce

from card import *
from position import Position, flat_positions, get_value_position
from strategy import Strategy
from atests import Ok, game_card_number, players_limited_cards, test_strategy


def log():
    return
    print(Positions)
    print(Deck)
    print(Discarded)
    print(Hands)
    print(Chips)


HOUSE_INIT_CHIPS = 999_999
HOUSE_PREVENTION_CUTOFF = 500_000
CARDS_PER_PLAYER = 6

SMALL_PAYOUT = 3
MID_PAYOUT = 5
BIG_PAYOUT = 10
STONK_PAYOUT = 20

BIG_SIZE_CUTOFF = 6
MAX_POSITION_VALUE = 10

total_players = 0
current_round = 0


"""
A card is a string of 2 chars, see CARDS for examples
"""

Chips: list[int] = []
"""Stack of chips per player_id"""

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

Orderbook: list[list[str]] = []
"""List of lists of cards a player will play this round. id of list = player_id"""


def reset_all():
    global Chips, Hands, Strategies, Deck, Discarded, Positions, Orderbook
    Chips = []
    Hands = []
    Strategies = []
    Deck = CARDS.copy()
    Discarded = []
    Positions = []
    Orderbook = []


def init_game(num_players: int, init_chips: int) -> tuple[list[int], int]:
    """
    Configures a new game, with auto Strategies and one agent.
    Returns: Chips (final state), round_count.
    """
    Ok(CARDS_PER_PLAYER * (num_players + 1) <= len(CARDS), "Too many players")
    global Orderbook, total_players
    reset_all()

    total_players = num_players
    Orderbook = [[]] * total_players

    shuffle(Deck)

    """Setup players Chips, Hands and Strategies"""
    for player_id in range(num_players):
        Chips.append(init_chips)

        hand: list[str] = []
        for _ in range(CARDS_PER_PLAYER):
            hand.append(Deck.pop())
        Hands.append(hand)

        Strategies.append(Strategy(player_id, hand)) # TODO if player, init a player strategy
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
        players_limited_cards(Positions, Hands, Chips, CARDS_PER_PLAYER)
        game_card_number(Positions, Hands, Deck, Discarded)

        players_passing = [False] * total_players
        i = 0

        """Market opens: players open and close positions"""
        while reduce(lambda a, v: a + v, players_passing, 0) < total_players-1:
            """Every round a different player starts"""
            player_id: int = (i + current_round) % total_players 
            if players_passing[player_id]:
                continue

            hand = Hands[player_id]
            cs = Strategies[player_id]

            # TODO extend actions: act, pass
            # action 1: open: accept from orderbook
            # action 2: open: propose a new order
            # action 3: close existing (with card, As or money)
            # action 4: doubledown
            # action 5: open against house
            # action 6: pass
            # action 7: default open against the house if nobody else

            is_passing = cs.compute_current_action(hand.copy(), Positions, Chips)
            if is_passing:
                players_passing[player_id] = True
                continue

            new_cards = cs.open_cards + cs.close_cards
            test_strategy(new_cards, hand)

            """Opening and closing positions reveals cards"""
            [s.update_state(new_cards) for s in Strategies if s.player_id != i]

            """Implements strategy's actions"""
            [hand.remove(card) for card in new_cards]
            Orderbook[player_id] = cs.open_cards
            close_positions(cs.close_pos, cs.close_cards, player_id)

            # TODO match algo v2 - turns
            i += 1

        match_algo_v1()

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
            if p.is_house:
                Chips[p.long * p.short * -1] -= 1

        """Bankrupt players: close positions and discard hand"""
        close_pos = [p for p in Positions if Chips[p.long] <= 0 or Chips[p.short] <= 0]
        close_positions(close_pos, [], -1)
        for player_id, hand in enumerate(Hands):
            if Chips[player_id] <= 0:
                Discarded.extend(hand)
                del hand[:]

        """House prevents bankruptcy: closes all positions against itself"""
        ## Not needed as we already demand big payout every 100 rounds
        # if Chips[-1] < HOUSE_PREVENTION_CUTOFF:
        #     close_pos = [p for p in Positions if ((p.long+1) * (p.short+1)) == 0]
        #     close_positions(close_pos, [], -1)
        #     Chips[-1] = HOUSE_INIT_CHIPS

        """House takes fee to prevent long games"""
        if current_round > 100 and max(Chips[:-1]) > 30:
            for c, _ in enumerate(Chips):
                Chips[c] -= BIG_PAYOUT

    return Chips, current_round


def match_algo_v1():
    """Matching algorithm v1: naive, first find, first serve, everyone else with house"""
    global Orderbook

    for i, _ in enumerate(Orderbook):
        player_id: int = (i + current_round) % total_players
        player_cards = Orderbook[player_id]

        c = 0
        is_matched = False
        while c < len(player_cards):
            card = player_cards[c]
            is_player_long = is_long(card)

            for m, _ in enumerate(Orderbook):
                m_player_id: int = (m + current_round + 1) % total_players
                m_player_cards = Orderbook[m_player_id]

                if m_player_id == player_id:
                    continue
                for m_card in m_player_cards:

                    if is_player_long != is_long(m_card):
                        if is_player_long:
                            position = Position(player_id, m_player_id, [m_card, card])
                        else:
                            position = Position(m_player_id, player_id, [m_card, card])
                        Positions.append(position)
                        is_matched = True
                        player_cards.remove(card)
                        m_player_cards.remove(m_card)
                        break
                if is_matched:
                    break
            if is_matched:
                break
            else:
                c += 1

    """Match rest of orderbook with the house"""
    for player_id, player_cards in enumerate(Orderbook):
        for card in player_cards:
            if is_long(card):
                position = Position(player_id, -1, [card])
            else:
                position = Position(-1, player_id, [card])
            Positions.append(position)

    Orderbook = [[]] * total_players


def close_positions(
    close_pos: list[Position], close_cards: list[str], close_player_id: int
):
    """
    Closes the position with the card, discards all cards and deals new cards to palyers.
    Will throw an error if it cant close the position with the given cards.

    TODO consider not asserting, for more resilient code, against bad programmed strategies.
    """
    global Positions, Discarded, Deck

    if close_player_id >= 0:
        """Verifying we can close positions. Will throw an error if it cant"""
        Ok(
            len(close_cards) == len(close_pos),
            "Strategy Error: close cards and pos not of the same length",
        )
        Ok(
            len([p for p in close_pos if not p.has_player(close_player_id)]) == 0,
            "Strategy Error: cant close this position",
        )

        __close_cards = close_cards.copy()
        close_cards.sort(key=get_value)
        close_pos.sort(key=get_value_position)
        for p in close_pos:
            for c in close_cards:
                """looking for the first card.value >= pos.value"""
                is_value_ok = get_value(c) >= get_value_position(p)
                is_color_ok = is_long(c) != p.is_player_long(close_player_id)
                if c[0] == "A" or (is_value_ok and is_color_ok):
                    __close_cards.remove(c)
                    break
        #     else:
        #         Ok(False, f"Strategy Error: {close_player_id} cant close position {p} with {close_cards}")
        # Ok(len(__close_cards) == 0, f"Strategy Error: cards {__close_cards} cant close any position in {close_pos}")

    Positions = [p for p in Positions if p not in close_pos]
    Discarded.extend(flat_positions(close_pos) + close_cards)

    """Deals cards to players: 2 cards to one forcing the close, one card to the other"""
    did_reshuffle = False
    for pos in close_pos:
        for player_id in [p for p in [close_player_id, pos.long, pos.short] if p != -1]:
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
        cards = Hands[player_id] + flat_positions(Positions)
        [s.update_state(cards, reset=True) for s in Strategies]


def is_playing() -> bool:
    """
    Will play until there's only one chipholder left, excluding the house (id=-1)
    """
    return reduce(lambda a, v: (v > 0) + a, Chips[:-1], 0) > 1


def get_payout_size(position: Position, market_card: str) -> int:
    """According to game's rules"""
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
