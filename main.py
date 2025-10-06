from game import init_game


def play():
    total_players = 5
    wins = [0] * total_players
    for j in range(1):
        Chips, rounds = init_game(total_players, 500)
        print("end game", Chips, rounds)
        for i, chips in enumerate(Chips[:-1]):
            if chips > 0:
                wins[i] += 1
                break

    print(wins, sum(wins))


if __name__ == "__main__":
    play()
