CARDS = [
    "As",
    "Ac",
    "Ad",
    "Ah",
    "2s",
    "2c",
    "2d",
    "2h",
    "3s",
    "3c",
    "3d",
    "3h",
    "4s",
    "4c",
    "4d",
    "4h",
    "5s",
    "5c",
    "5d",
    "5h",
    "6s",
    "6c",
    "6d",
    "6h",
    "7s",
    "7c",
    "7d",
    "7h",
    "8s",
    "8c",
    "8d",
    "8h",
    "9s",
    "9c",
    "9d",
    "9h",
    "Ts",  # T=10
    "Tc",  # T=10
    "Td",  # T=10
    "Th",  # T=10
    "Js",
    "Jc",
    "Jd",
    "Jh",
    "Qs",
    "Qc",
    "Qd",
    "Qh",
    "Ks",
    "Kc",
    "Kd",
    "Kh",
]
"""
Sorted array of cards:
- value = `CARDS[n][0]`: A-K, T=10
- suit = `CARDS[n][1]`: s:spades, c:clubs, d:diamond, h:heart
"""


def get_value(card: str) -> int:
    """Numerical value of card. Face cards are worth 10."""
    return {
        "A": 1,
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "6": 6,
        "7": 7,
        "8": 8,
        "9": 9,
        "T": 10,
        "J": 10,
        "Q": 10,
        "K": 10,
    }[card[0]]


def is_big(card: str) -> bool:
    """Is card big or small. Returns 1 if big, 0 if small."""
    return card[0] in ["7", "8", "9", "T", "J", "Q", "K"]


def is_long(card: str) -> bool:
    """Is card long or short. Returns 1 if long, 0 if short."""
    return card[1] in ["s", "c"]


def is_face(card: str) -> bool:
    """Is card a face: `J, Q, K`"""
    return card[0] in ["J", "Q", "K"]
