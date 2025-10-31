from scrabble import Scrabble
from scrabble_ai import ScrabbleAI


def simulate_game(print_board=True, display_board=False):
    # initialize game and ai
    game = Scrabble()
    ai = ScrabbleAI(game)
    print("Game and AI initialized.")
    move_idx = 0
    while True:
        #    find best move
        moves = ai.find_best_move(is_first_move=(move_idx==0), random_opponent_rack=True, max_depth=3, width=10, num_words_explored=[1, 1 ,1])

        # if no moves, game is over
        if not moves:
            break
        
        best_move = moves[0]["move"]

        # play the best move
        game.play_word(
            word=best_move["word"], score=best_move["score"], start_position=best_move["start_position"], is_transpose=best_move["is_transpose"]
        )

        # print board
        if print_board:
            game.print_board()
            print("-" * 50)

        # display board        
        if display_board:
            game.display_board()


        # update ai game state
        ai.set_state(game.get_game_state())
        
        move_idx += 1

    state = game.get_game_state()

    # print final scores
    print("Finished Running Simulation:")
    print("----------------------------")
    for player in state['players'].values():
        print(f"{player['name']}: {player['score']}")
    game.display_board()



if __name__ == "__main__":
    print("Initializing Game and AI... (may take up to a minute)")
    simulate_game(print_board=True, display_board=False)
