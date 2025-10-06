from game import init_game
from tqdm import tqdm


def study():
    total_players = 5
    wins = [0] * total_players
    for j in range(100):
        Chips, rounds = init_game(total_players, 500)
        print("end game", Chips, rounds)
        for i, chips in enumerate(Chips[:-1]):
            if chips > 0:
                wins[i] += 1
                break
        if j % 100 == 0:
            tqdm.write(str(wins))
        if j % 1000 == 0:
            wins = [0] * total_players

    print(wins, sum(wins))


def play():
    while True:
        inp = input()
        match inp:
            case "a":
                pass


if __name__ == "__main__":
    # TODO execute with argparse
    study()
    # play()
