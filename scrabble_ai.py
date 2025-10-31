import numpy as np
import copy
import warnings
from scrabble import Scrabble
from solver import Solver


class GameNode:
    def __init__(self, parent, game, solver, game_state, previous_move=None):
        """Game node including game state and children

        Args:
            parent (Game Node): Parent Node
            game (Scrabble): Scrabble game object
            game_state dict["board", "letter_counts", "players", "turn"]: Current game state
        """
        self.parent = parent
        self.game = game
        self.game_state = game_state
        self.previous_move = previous_move
        self.previous_move_score = (
            self.previous_move["score"] if self.previous_move else 0
        )
        self.solver = solver
        self.children = []

    def _update_board(self, move, board, rack):
        """Updates the game state after a move is played

        Args:
            move (dict): Move to play
            board (list[list[]]): board
            rack (list[str]): Player's rack
        """
        # Play the move onto NEW BOARD
        word = move["word"]
        start_position = move["start_position"]
        is_transpose = move["is_transpose"]

        x, y = start_position
        if is_transpose:
            x, y = y, x
        for letter in word:
            if board[y][x] != 0:
                pass
            else:
                rack.remove(letter)
                board[y][x] = letter

            if is_transpose:
                y += 1
            else:
                x += 1

    def get_moves(self, isFirstMove=False, num_words=10):
        rack = self.game_state["players"][self.game_state["turn"]]["rack"]
        board = self.game_state["board"]

        # Gets top candidate moves from FindWords()
        moves = self.solver._build_all_words(
            rack=rack, board=board, first_move=isFirstMove, num_words=num_words
        )

        return moves

    def make_child(self, move):
        """Creates a child node of the current node

        Args:
            move (dict): The play made

        Notes:
            - CREATES A COPY OF THE GAME STATE
            - Updates the board, rack, and score for the new game state
            - Switches the turn
            - Draws new letters for the player
        """
        new_game_state = copy.deepcopy(self.game_state)

        board = new_game_state["board"]
        turn = new_game_state["turn"]

        player = new_game_state["players"][turn]
        rack = player["rack"]

        self._update_board(move, board, rack)

        rack += self.game.draw_letters(
            self.game.num_letters - len(rack),
            isRemoval=True,
            letter_counts=new_game_state["letter_counts"],
        )

        player["score"] += move["score"]
        new_game_state["turn"] = (turn + 1) % self.game.num_players

        new_child = GameNode(
            self, self.game, self.solver, new_game_state, previous_move=move
        )
        self.children.append(new_child)


class ScrabbleAI:
    def __init__(self, game: Scrabble = Scrabble()):
        """Scrabble AI solver using Monte Carlo Tree Search

        Args:
            game (Scrabble, optional): Scrabble game object. Defaults to Scrabble().
        """
        self.game = game
        self.solver = Solver(game=game)

        game_state = {
            "board": game.board,
            "letter_counts": game.letter_counts,
            "players": game.players,
            "turn": game.current_player,
        }
        self.root = GameNode(
            None, game=self.game, solver=self.solver, game_state=game_state
        )

    def find_best_move(
        self,
        is_first_move=False,
        max_depth=3,
        width=10,
        num_words_explored=[3, 2, 1],
        random_opponent_rack: bool = True,
    ):
        """_summary_

        Args:
            is_first_move (bool, optional): If is the first move of the game. Defaults to False.
            max_depth (int, optional): Depth to explore game tree. Defaults to 10.
            width (int, optional): Number of random trials to run for each Node. Defaults to 3.
            num_words_explored (list[int], optional): Number of top words to explore at each node. Defaults to [3, 2, 1].
            random_opponent_rack (bool, optional): If false, simulations use the opponent's actual rack. Defaults to True.

        Notes:
            - The number of words explored should be the same as the max_depth
            - For best use, hyperparameters should follow the following properties:
                - num_words_explored should be generally decreasing
                    - num_words_explored[0] is the most important to keep large
                - width should be quite large, as it is the main source of randomness
                - a max_depth > 4 doesn't has very diminishing returns
                - random_opponent_rack: False, is akin to getting the true EV of a position

        Returns:
            list[dict]: List of best moves and their expected values
        """

        if max_depth != len(num_words_explored):

            if len(num_words_explored) > max_depth:
                num_words_explored = num_words_explored[:max_depth]
                warnings.warn(
                    f"num_words_explore should have length {max_depth}. Trimming extra values. New num_words_explored = {num_words_explored}",
                    UserWarning,
                )
            else:
                num_words_explored += [num_words_explored[-1]] * (
                    max_depth - len(num_words_explored)
                )
                warnings.warn(
                    f"num_words_explore should have length {max_depth}. Broadcasting empty values. New num_words_explored = {num_words_explored}",
                    UserWarning,
                )

        # Explore the tree to populate children
        self.explore_tree(
            is_first_move=is_first_move,
            max_depth=max_depth,
            width=width,
            num_words_explored=num_words_explored,
            random_opponent_rack=random_opponent_rack,
        )

        # Precompute EV values for all children
        best_moves = [
            {"move": move.previous_move, "ev": self._get_ev(move)}
            for move in self.root.children
        ]

        # Sort the moves by EV in descending order
        best_moves.sort(key=lambda x: x["ev"], reverse=True)

        return best_moves

    def _scale(self, x):
        # Min-max normalization
        min_val = np.min(x)
        max_val = np.max(x)
        range_val = max_val - min_val
        epsilon = 1e-10
        return (x - min_val) / (range_val + epsilon)

    def set_state(self, game_state):
        self.root = GameNode(
            None, game=self.game, game_state=game_state, solver=self.solver
        )

    def _softmax(self, x, temperature=1):
        """Internal softmax function with temperature parameter"""
        e_x = np.exp((x - np.max(x)) / temperature)
        return e_x / e_x.sum()

    def _get_ev(self, node):
        """Internal function to recursively approximate the expected value of a move

        Is essentially a MCTS simulation step

        Args:
            node GameNode: current node

        Returns:
            np.float64: the expected value of a move
        """

        # recursive base case
        if not node.children:
            return node.previous_move_score

        # Get the expected value of the children
        values = [self._get_ev(child) for child in node.children]
        scaled_values = self._scale(values)
        probs = self._softmax(scaled_values, temperature=1)
        child_ev = np.dot(probs, values)

        # The move_ev is the difference between the score of the move you play, and the EV of the child nodes' moves
        move_ev = node.previous_move_score - child_ev
        return move_ev

    def explore_tree(
        self,
        is_first_move: bool,
        max_depth: int,
        random_opponent_rack: bool,
        num_words_explored: list[int],
        width: int,
    ):
        """Wrapper function to explore the game tree

        Args:
            *** SEE ScrabbleAI.find_best_move ***

        Notes:
            - There is almost no reason to include previously calculated EVs in the tree
            - After playing a move and getting a new rack, the game tree has shrunk by a factor of about 4 digits
        """

        def _explore(node, num_words_explored: int, current_depth: int):
            if current_depth >= max_depth:
                return

            candidate_words = node.get_moves(
                num_words=num_words_explored[current_depth]
            )

            # Explore each move and make it a child node
            for move in candidate_words:
                node.make_child(move)
                _explore(
                    node.children[-1],
                    num_words_explored=num_words_explored,
                    current_depth=current_depth + 1,
                )  # Recursively explore child node

        # Clear children from previous exploration
        self.root.children = []
        candidate_words = self.root.get_moves(
            isFirstMove=is_first_move, num_words=num_words_explored[0]
        )

        for move in candidate_words:
            self.root.make_child(move)

        # Width denotes the number of random trials ran for each node
        for i in range(width):
            for child in self.root.children:

                if random_opponent_rack:
                    child.game_state["players"][1]["rack"] = self.game.draw_letters(
                        self.game.num_letters,
                        isRemoval=True,
                        letter_counts=child.game_state["letter_counts"],
                    )
                else:
                    child.game_state["players"][1]["rack"] = self.game.players[1][
                        "rack"
                    ]
                _explore(child, num_words_explored, 1)

        return candidate_words
