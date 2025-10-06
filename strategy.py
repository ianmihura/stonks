from random import random as R
from card import is_long
from position import Position


class Strategy:
    player_id: int
    is_agent: bool = False

    open_cards: list[str]
    close_cards: list[str]
    close_pos: list[Position]
    """Return type of action"""

    count: int
    """
    Current count of color:
    - Black +1
    - Red -1
    """

    len_d: int = 52
    """Number of unknown cards (roughly len(D))"""

    def update_state(self, new_cards: list[str], reset=False):
        if reset:
            self.count = 0

        self.len_d -= len(new_cards)
        if self.len_d <= 0:
            self.len_d = 52

        for card in new_cards:
            self.count += is_long(card) or -1

    L: float
    """
    Long bias: will tend more long than short
    - 1: Completely long
    - 0.5: Random (indiferent)
    - 0: Completely short
    """

    A: float
    """
    Active bias: will tend to act on it's EV
    - 1: Always acts, as much as possible
    - 0.5: Random
    - 0: Never acts
    """

    M: float
    """
    Market maker bias: will be first to propose trades to the orderbook, rather than taking from existing trades
    - 1: Always proposes their trades (market maker)
    - 0.5: Random
    - 0: Always takes from existing trades in orderbook (market taker)
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
            return f"Strategy: {self.player_id} (agent), L:{self.L}, M:{self.M}, A:{self.A}, G:{self.G}"
        else:
            return f"S{self.player_id}"

    def __init__(self, player_id: int, hand: list[str]):
        self.L = 0.5
        self.A = 0.5
        self.M = 0.5
        # TODO v2. other default strategies, beyond perfect counters

        self.player_id = player_id
        self.update_state(hand, reset=True)

    # def is_long(self) -> bool:
    #     return self.EV > self.L
    #     return R() > self.L # Random player

    def is_active(self) -> bool:
        # TODO is there a self.A that beats the non agent?
        if self.is_agent:
            return R() < (self.A + self.C()) / 2
        else:
            return R() < self.C() # optimum

    def is_maker(self) -> bool:
        # TODO v2. maker vs taker
        return 1

    def compute_current_action(
        self, hand: list[str], Positions: list[Position], Chips: list[int]
    ) -> bool:
        """
        Returns true if the player passes and there is no further action
        """
        self.open_cards = []
        self.close_cards = []
        self.close_pos = []

        if self.is_agent:
            import ipdb; ipdb.set_trace()
            return

        """Should I act"""
        expects_long = self.count > 0
        if not self.is_active():
            return

        # TODO: v2. given my EV, chips and market

        """Can I act"""
        for p in Positions:
            if p.has_player(self.player_id) and (
                p.is_player_long(self.player_id) != expects_long
            ):
                for c in hand:
                    if p.is_player_long(self.player_id) != is_long(c):
                        self.close_pos = [p]
                        self.close_cards = [c]
                        hand.remove(c)
                        break  # TODO not breaking correctly

        # TODO close with money if cant close with cards, or any Ace

        self.open_cards = [c for c in hand if is_long(c) == expects_long][:1]
