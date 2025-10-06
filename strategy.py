from functools import reduce
from random import random as R
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
    Current count of color:
    - Black +1
    - Red -1
    """
    # TODO am i counting upside down?

    @property
    def expects_long(self) -> bool:
        return self.count > 0

    len_d: int = 52
    """Number of unknown cards (roughly len(Deck))"""
    # TODO maybe theres an error with reshuffling

    def update_state(self, new_cards: list[str], reset=False):
        if reset:
            self.count = 0

        self.len_d -= len(new_cards)
        if self.len_d < 1:
            self.len_d += 52
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

    def C(self) -> bool:
        """
        Confidence of count is a range between [0,1]:
        - 0: not confident (when count=0)
        - Higher count: progresively more confidence
        - 1: totally confident (when abs(count)=len_d)

        The formula is given by the notion that:
        - `abs(count)/len_d` is in the range [0,1]
        - `abs(count)` => len_d, confidence => 1
        - `abs(count)` => 0, confidence => 0
        - Quadratics express results 'exponentially'

        The formula was derived by normalizing `P[~color]` with a quadratic fn:
        - Using `~color` considering were keeping count of cards seen
        - `P[~color | count, len_d] = (len_d - abs(count)) / 2*len_d`
        - Quadratic fn `2x**2` maps midpoint x=0.5 to y=0, and goes to y=1 at both ends
        """
        return (abs(self.count) / self.len_d) ** 2

    def __repr__(self):
        if self.is_agent:
            return f"S{self.player_id}(A): count:{self.count} C:{self.C():.4f}"
        else:
            return f"S{self.player_id}: count:{self.count} C:{self.C():.4f}"

    def __init__(self, player_id: int, hand: list[str]):
        self.A = 0.5  # TODO v2. more strategy profiles
        self.L = 0.5  # TODO v2. more strategy profiles

        self.player_id = player_id
        self.update_state(hand, reset=True)

    def is_active(self, threshold: float = R()) -> bool:
        """
        Returns boolean suggesting if the player should be active or no.
        Is given by the confidence of the count being above a certain threshold.

        `threshold` should be in closed range [0,1]. Random by default.

        Is also used for:
        - Should player close with cash. EV of this is the same as effectively
            loosing next market move. Efficient players only close with cash to prevent
            a streak of losses in the future (ie. if confidence is very high).
            We need an additional eagerness for this
        - Should player be a market maker. Being a taker is safer than being a maker
            (no risk of being assigned a house trade), so efficient player will always
            take if possible. We need an additional eagerness to be a market maker
        """
        assert threshold >= 0 and threshold <= 1
        return threshold < self.C()

    def compute_current_action(
        self,
        hand: list[str],
        Positions: list[Position],
        Chips: list[int],
        Orderbook: dict[int, list[str]],
    ) -> bool:
        """
        Returns
        - True if it has some action to do
        - False if it passes (no action)
        """
        self.hand = hand
        self.open_cards = {}
        self.close_cards = {}

        if self.is_agent:
            is_acting = False
            import ipdb; ipdb.set_trace()
            return is_acting

        """I try to close any unreasonable positions"""
        is_closing = self.compute_close_card_actions(Positions, Chips[self.player_id])

        """Should I open new positions"""
        if not self.is_active(0.2):
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
            if has_player and position.is_player_long(self.player_id) != self.expects_long:
                """If I expect to be long, I should close all positions that are short"""

                my_card = self.__get_closing_card()
                if my_card:
                    # TODO make sure the value of the card is valid to close the position
                    # TODO may close position with more than one card
                    self.close_cards[position] = my_card
                    self.hand.remove(my_card)
                    is_closing = True

                else:
                    if self.is_active(0.8) and chips > get_close_cost(position):
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

            if self.is_active(0.5):
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
