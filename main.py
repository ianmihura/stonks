from game import init_game


if __name__ == "__main__":

    """Edit these variables below to adjust your game"""
    total_players = 5
    init_chips = 500
    is_playing = True
    """"""""""""""""""

    Chips, rounds = init_game(total_players, init_chips, play=is_playing)

    print("Game finished.")
    print("  Played rounds", rounds)
    print("  Resulting chips", Chips[:-1])

    for i, chips in enumerate(Chips[:-1]):
        if chips > 0:
            if i == 0:
                print(f"You won!")
            else:
                print(f"Player {i} won!")
            break
