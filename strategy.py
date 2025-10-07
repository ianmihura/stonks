from functools import reduce
from random import random as R
import sys
from card import get_value, is_long
from position import Position, get_close_cost


class Strategy:
    player_id: int
    is_agent: bool = False
    hand: list[str] = []
    """My hand in the current round"""

    open_cards: dict[str, Position | str | None]
    """
    Return type, action taken: cards from hand to play.
    Dict mapping card (str) to either:
    - Position: existing Position (double down)
    - str: create a new position (market taker).
        format: card + "_" + other_player_id 
    - None: submit the card to the orderbook (market maker)
    """

    close_cards: dict[Position, str | None]
    """
    Return type, action taken: existing positions to close.
    Dict mapping Position to either:
    - str: Card in the player's hand
    - None: will pay cash to close the position
    """

    count: int
    """
    Current count of color seen:
    - Black +1
    - Red -1
    """

    @property
    def expects_long(self) -> bool:
        """Expect mean reversion, so I expect to be long if my count is negative"""
        return self.count < 0

    len_d: int = 52
    """Number of unknown cards (roughly len(Deck))"""

    def update_state(self, new_cards: list[str], reset=False):
        if reset:
            self.count = 0
            self.len_d = 52

        self.len_d -= len(new_cards)
        for card in new_cards:
            self.count += is_long(card) or -1

    L: float
    """
    Long bias: will tend more long than short
    - 1: Completely long
    - 0.5: No bias
    - 0: Completely short
    """

    A: float
    """
    Active bias: will tend to act on it's EV
    - 1: Always acts, as much as possible
    - 0.5: No bias
    - 0: Never acts
    """

    # G: float
    # """
    # Gullible bias: will update its EV based on other player's positions
    # - 1: Estimates every player is perfect, active, market maker
    # - 0.5: Random
    # - 0: Does not look at other positions to update its count/EV
    # """

    @property
    def C(self) -> bool:
        """
        Confidence of count is a range between [0,1]:
        - `C = 0`
            - not confident, `count=0`
        - `C = 0.001`
            - typical at the begining of a match, or after reshuffled deck.
        - `C = 0.1`
            - if I know 1/3 of the remaining cards' color
        - `C = 0.44`
            - if I know 2/3 of the remaining card's color
        - `C = 1`
            - totally confident, when `abs(count)=len_d`

        The formula is given by the notion that:
        - `abs(count)/len_d` is in the range [0,1]
        - `abs(count)` => len_d, as confidence => 1
        - `abs(count)` => 0, confidence => 0
        - Quadratics express results 'exponentially'
        - It was derived by normalizing `P[~color]` with a quadratic fn:
            - Using `~color` considering we're keeping count of cards seen
            - `P[~color | (count, len_d)] = (len_d - abs(count)) / 2*len_d`
            - Quadratic fn `2x**2` maps midpoint x=0.5 to y=0, and goes to y=1 at both ends
        """
        return (abs(self.count) / self.len_d) ** 2

    def __repr__(self):
        if self.is_agent:
            return f"S{self.player_id}(A): count:{self.count} C:{self.C:.4f}"
        else:
            return f"S{self.player_id}: count:{self.count} C:{self.C:.4f}"

    def __init__(self, player_id: int, hand: list[str], is_agent: bool, playing: bool):
        self.A = 0.5  # TODO v2. more strategy profiles
        self.L = 0.5  # TODO v2. more strategy profiles

        self.player_id = player_id
        self.update_state(hand, reset=True)
        self.is_agent = is_agent
        self.is_playing = playing
        if is_agent and playing:
            print_welcome()

    def is_active(self, threshold: float = R()) -> bool:
        """
        Returns boolean suggesting if the player should be active or no.
        Is given by the confidence of the count being above a certain threshold.

        `threshold` should be in closed range [0,1]. Random by default. Consider that

        Is also used for:
        - Should player close with cash. EV of this is the same as effectively
            loosing next market move. Efficient players only close with cash to prevent
            a streak of losses in the future (ie. if confidence is very high).
            We need an additional eagerness for this
        - Should player be a market maker. Being a taker is safer than being a maker
            (no risk of being assigned a house trade), so efficient player will always
            take if possible. We need an additional eagerness to be a market maker
        """
        # TODO fine tune threshold for auto strategies
        assert threshold >= 0 and threshold <= 1
        return threshold < self.C

    def compute_current_action(
        self,
        hand: list[str],
        Positions: list[Position],
        Chips: list[int],
        Orderbook: dict[int, list[str]],
        Blinds: int,
    ) -> bool:
        """
        Returns
        - True if it has some action to do
        - False if it passes (no action)
        """
        self.hand = hand
        self.open_cards = {}
        self.close_cards = {}

        if self.is_agent and self.is_playing:
            return ui_loop(self, Positions, Chips, Orderbook, Blinds)

        """I try to close any unreasonable positions"""
        is_closing = self.compute_close_card_actions(Positions, Chips[self.player_id])

        """Should I open new positions"""
        if not self.is_active(0.01):
            return is_closing

        """I try to act if I can"""
        is_opening = self.compute_open_card_action(Orderbook)

        return is_closing or is_opening

    def compute_close_card_actions(
        self, Positions: list[Position], chips: int
    ) -> tuple[list[str], bool]:
        """
        Returns bool is_acting, additionally:

        Modifies self.hand (removes played cards),
        so next computation (open_cards) does not take these cards into consideration
        """
        is_closing = False

        for position in Positions:
            has_player = position.has_player(self.player_id)
            if (
                has_player
                and position.is_player_long(self.player_id) != self.expects_long
            ):
                """If I expect to be long, I should close all positions that are short"""

                my_card = self.__get_closing_card()
                if my_card:
                    # TODO make sure the value of the card is valid to close the position
                    # TODO may close position with more than one card
                    self.close_cards[position] = my_card
                    self.hand.remove(my_card)
                    is_closing = True

                else:
                    if self.is_active(0.1) and chips > get_close_cost(position):
                        """We can close with cash, and we have a high enough count"""
                        self.close_cards[position] = None
                        is_closing = True

        return is_closing

    def compute_open_card_action(self, Orderbook: dict[int, list[str]]) -> bool:
        """
        Returns bool is_acting.
        We do only one open action, prefer being a market taker.
        """
        my_card = self.__get_card_match_expectation()
        if not my_card:
            """I have no card to act with"""
            return False

        """Try to find a suitable card in the orderbook"""
        if card_to_take := self.__get_card_from_orderbook(Orderbook):
            """We are a taker: less risky"""
            self.open_cards[my_card] = card_to_take
            return True

        else:
            # TODO if we have an open position on the same side:
            # we prefer to double down (if doubling down increases payoff)
            # rather than being a market maker

            if self.is_active(0.01):
                """We should be a market maker: riskier than being a taker"""
                self.open_cards[my_card] = None
                return True
            else:
                return False

    def __get_closing_card(self) -> str:
        """
        Returns card from the hand that can close a position, given an expectation.
        Prefers any card before an Ace.
        Returns empty string if no card found.
        """
        my_card = self.__get_card_match_expectation()
        if not my_card:
            """Try to find an Ace"""
            for card in self.hand:
                if get_value(card) == 1:
                    return card
        return my_card

    def __get_card_match_expectation(self) -> str:
        """Returns a card from the hand that matches the expectation, empty string otherwise"""
        for card in self.hand:
            if is_long(card) == self.expects_long:
                return card
        return ""

    def __get_card_from_orderbook(self, Orderbook: dict[int, list[str]]) -> str:
        """
        Returns a card from the Orderbook of the opposite expectation that I have,
        concatenated with "_" + other_player_id.
        Returns empty string otherwise.
        """
        for other_player_id in Orderbook:
            for card in Orderbook[other_player_id]:
                if is_long(card) != self.expects_long:
                    return card + "_" + str(other_player_id)
        return ""


def ui_loop(
    self: Strategy,
    Positions: list[Position],
    Chips: list[int],
    Orderbook: dict[int, list[str]],
    Blinds: int,
) -> bool:
    """Helps user interact with the game, returns bool is_acting"""

    is_acting = False
    while True:
        print()
        print("Its your turn, type h for help")
        print(">")
        inp = input()
        match inp:
            case "print" | "p":
                print(f"Your count is {self.count} with confidence {self.C:.4f}")
                print()
                print("Your info:")
                print("  Hand", self.hand)
                print(
                    "  Your Positions", [p for p in Positions if p.has_player(self.player_id)]
                )
                print("  Chips", Chips[self.player_id])
                print()
                print("Other info:")
                print("  Blinds", Blinds)
                print("  All Positions", Positions)
                print("  All Chips", Chips)
                print("  Orderbook", Orderbook)

            case "review" | "r":
                print("Pending actions this turn:")
                print_open_cards()
                print_close_cards()
                print("")
                print("To clear all action type rr, or reset")

            case "reset" | "rr":
                print("Cleared all actions")
                self.open_cards = {}
                self.close_cards = {}
                is_acting = False

            case "open" | "o":
                print(">> Open a position")
                if card := get_card(self.hand):
                    flat_ob = reduce(lambda a, v: a + Orderbook[v], Orderbook, [])
                    while True:
                        print("Will you be a market maker or a taker?")
                        print("  Type 'make' to propose the card to the orderbook")
                        print(f"    the orderbook has {flat_ob} cards")
                        print("  Type 'take' to open a position with an existing card")
                        print(f"    you have {self.hand} cards")
                        print("  Type 'back' or 'b' to go back")
                        print(">")

                        inp = input()
                        if inp == "make":
                            self.open_cards[card] = None
                            is_acting = True
                            break
                        elif inp == "take":
                            other_card = get_card(flat_ob)
                            self.open_cards[card] = other_card
                            is_acting = True
                            break
                        elif inp in ["back", "b"]:
                            break
                        else:
                            continue

            case "close" | "c":
                print(">> Close a position")
                if position := get_position(Positions):
                    while True:
                        print("Will you close with chips or a cards?")
                        print("  Type 'chip' to close the position with chips")
                        print(f"    you have {Chips[self.player_id]} chips")
                        print(
                            "  Type 'card' to close the position with an existing card"
                        )
                        print(f"    you have {self.hand} cards")
                        print("  Type 'back' or 'b' to go back")
                        print(">")

                        inp = input()
                        if inp == "chip":
                            self.close_cards[position] = None
                            is_acting = True
                            break
                        elif inp == "card":
                            card = get_card(self.hand)
                            self.close_cards[position] = card
                            is_acting = True
                            break
                        elif inp in ["back", "b"]:
                            break
                        else:
                            continue

            case "ok" | "k":
                print("Finished turn")
                break

            case "quit" | "q" | "exit" | "exit()":
                print("Goodbye")
                sys.exit()

            case "welcome" | "w":
                print_welcome()

            case _:
                print()
                print("Type any of the following commands to play")
                print()
                print("Information:")
                print("  p,  print    Print the information of your state")
                print("  r,  review   Review your actions")
                print("  rr, reset    Reset all your pending action")
                print()
                print("Actions:")
                print("  c,  close    Close a position...")
                print("  o,  open     Open a position...")
                print("  ok           End your turn (review your actions before!)")
                print()

    return is_acting


def get_card(cards: list[str]) -> str | None:
    """Prompts the user to choose a card from a list of possible cards"""
    if len(cards) == 0:
        print("You cannot do this, there's no available card")
        return

    while True:
        print("Please select a card from one of the following", cards)
        print("  (type back or b to go back)")
        print(">")
        inp = input()
        if inp in cards:
            print("selected", inp)
            return inp
        elif inp in ["back", "b"]:
            return
        else:
            print(inp, "not in list of cards, select one of the following", cards)


def get_position(Positions: list[Position]) -> Position | None:
    """Prompts user to choose a position from a list of possible positions"""
    if len(Positions) == 0:
        print("You cannot do this, there's no Position availabe")
        return

    while True:
        print("Please select a position out of the following", Positions)
        print("  By typing out the index number")
        print("  (type back or b to go back)")
        print(">")
        inp = input()
        try:
            id = int(inp)
        except:
            print("Please type a number smaller than", len(Positions))

        if id > 0 and id < len(Positions):
            print("selected", Positions[id])
            return Positions[id]
        elif inp in ["back", "b"]:
            return
        else:
            print("Please type a number smaller than", len(Positions))


def print_open_cards(open_cards: dict[str, Position | str | None]):
    print("Open Actions:")
    for acts in open_cards:
        if type(open_cards[acts]) == str:
            print(
                f"  Card {acts} opens new position against {open_cards[acts]} from orderbook"
            )
        elif type(open_cards[acts]) == Position:
            print(f"  Card {acts} will double down to {open_cards[acts]}")
        else:
            print(f"  Card {acts} opens to the orderbook")


def print_close_cards(close_cards: dict[Position, str | None]):
    print("Close Actions:")
    for acts in close_cards:
        if type(close_cards[acts]) == str:
            print(f"  Position {acts} closes with {close_cards[acts]}")
        else:
            print(f"  Position {acts} closes with {get_close_cost(acts)} chips")


def print_welcome():
    print()
    print("##################################################################")
    print()
    print("  :####:                                 ##                     ##")
    print(" :######     ##                          ##                     ##")
    print(" ##:  :#     ##                          ##                     ##")
    print(" ##        #######    .####.   ##.####   ##   ##:   :#####.     ##")
    print(" ###:      #######   .######.  #######   ##  ##:   ########     ##")
    print(" :#####:     ##      ###  ###  ###  :##  ##:##:    ##:  .:#     ##")
    print("  .#####:    ##      ##.  .##  ##    ##  ####      ##### .      ##")
    print("     :###    ##      ##    ##  ##    ##  #####     .######:     ##")
    print("       ##    ##      ##.  .##  ##    ##  ##.###       .: ##       ")
    print(" #:.  :##    ##.     ###  ###  ##    ##  ##  ##:   #:.  :##       ")
    print(" #######:    #####   .######.  ##    ##  ##  :##   ########     ##")
    print(" .#####:     .####    .####.   ##    ##  ##   ###  . ####       ##")
    print()
    print("##################################################################")
    print()
    print("You are playing Stonks! A card game inspired by poker and stock trading.")
    print()
    print("If you have any doubts regarding the rules of the game, check:")
    print("  https://github.com/ianmihura/stonks")
    print()
    print("If you find a bug, email me at")
    print("  mihura.ian@gmail.com")
    print()
    print("*                                                         ")
    print("@                                                         ")
    print("@                                                ###      ")
    print("@                                            ######       ")
    print("@                                             ####        ")
    print("@                                          ###  #         ")
    print("@                                        ###              ")
    print("@                                      ###                ")
    print("@                                    ###                  ")
    print("@                                  ###                    ")
    print("@                     ##         ###                      ")
    print("@                   ##  ###    ###                        ")
    print("@      ##          ##      ####                           ")
    print("@    #####        ##                                      ")
    print("@   ##    ##     ##                                       ")
    print("@  ##       ##  ##                                        ")
    print("@ ##          ###                                         ")
    print("@                                                         ")
    print("@                                                         ")
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    print()
