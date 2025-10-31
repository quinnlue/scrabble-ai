import heapq
from gaddag import Gaddag, Node
from scrabble import Scrabble


class Solver:
    def __init__(self, gaddag: Gaddag=Gaddag(), game=Scrabble()):
        """Move Generator for scrabble

        Args:
            gaddag Gaddag: gaddag data structure of the dictionary you're using
                - SEE http://blog.wouterkoolen.info/Gaddag/post.html
        """

        self.gaddag = gaddag
        self.root = gaddag.root

        # Game state
        self.game = game
        self.board = self.game.board
        self.bonus_squares = self.game.bonus_squares
        self.rack_length = self.game.num_letters

    def is_word(self, word: str) -> bool:
        """Returns whether a word is in the dictionary

        Args:
            word (str): Word to check

        Returns:
            bool: is word in the dictionary?
        """

        node = self.root

        # checks the reversed path
        # ie. if the word is "RATE", it checks "ETAR#"

        for char in word[::-1] + "#":
            if char in node.children:
                node = node.children[char]
            else:
                return False

        return "$" in node.children

    def _get_candidate_letters(self, rack: list[str], board, position: tuple[int, int]):
        """
        Gets all letters that can be placed at a certain position given vertical constraints.

        Args:
            rack (list[str]): Characters in the rack.
            board (list[list[str]]): The current board state (based on transposition).
            position (tuple[int, int]): The position to check (based on transposition).

        Yields:
            str: Valid letters that can be placed at the position.
        """
        candidates = set()
        prefix = ""
        suffix = ""
        x, y = position

        if board[y][x] != 0:
            raise ValueError("Position is already occupied")

        # Get prefix
        y_1 = y - 1
        while y_1 >= 0 and board[y_1][x] != 0:
            prefix = board[y_1][x] + prefix
            y_1 -= 1

        # Get suffix
        y_2 = y + 1
        while y_2 < len(board) and board[y_2][x] != 0:
            suffix += board[y_2][x]
            y_2 += 1

        # Return rack if there are no vertical constraints
        if not prefix + suffix:
            return set(rack)

        # Checks if any letters in rack, complete the prefix-suffix pair
        for char in set(rack):
            if self.is_word(prefix + char + suffix):
                candidates.add(char)

        return candidates

    def get_tranposed_board(self, board=None):
        """
        Returns the transpose of the board
        """
        if board is None:
            board = self.board
        return [list(row) for row in zip(*board)]

    def _build_valid_suffix(
        self,
        prefix: str,
        node: Node,
        rack: list[str],
        board,
        position: tuple[int, int],
        usedRack=False,
    ) -> set:
        """Recursively builds all valid suffixes that can be built from a prefix and a rack and a position

        Args:
            prefix (str): A valid prefix
            node (Node): Node of the current last letter of the suffix
            rack (list[str]): All of the letters available to the player
            board (_type_): Current board state
            position (tuple[int, int]): The position to check
            valid_words (_type_, optional): All valid words given a prefix. Defaults to set().

        Returns:
            list[dict]: Has keys "word", "start_position", "score"
        """
        x, y = position
        valid_words = set()

        # While x,y is occupied, check if its part of a valid suffix
        # After this loop, x,y NEVER has a letter on it (either off the board or is empty)
        while x < len(board[0]) and board[y][x] != 0:

            if board[y][x] in node.children:
                node = node.children[board[y][x]]
                prefix += board[y][x]
                x += 1
            else:
                return valid_words

        # Checks for delimeter node (denotes a valid word)
        if "$" in node.children and usedRack:
            valid_words.add(prefix)

        # Recursive base cases (x out of bounds or no more letters to place)
        if x >= len(board[0]) or len(rack) == 0:
            return valid_words

        # Try all letters in the rack that are part of a valid suffix
        candidate_letters = self._get_candidate_letters(rack, board, (x, y))
        for char in candidate_letters:
            if char in node.children:
                # Create a new rack with the letter removed
                new_rack = rack.copy()
                new_rack.remove(char)

                # `usedRack` prevents returning a word where the player doesn't play a letter.
                usedRack = True
                valid_words.update(
                    self._build_valid_suffix(
                        prefix + char,
                        node.children[char],
                        new_rack,
                        board,
                        (x + 1, y),
                        usedRack=usedRack,
                    )
                )

        return valid_words

    def score_play(
        self, word: str, starting_position: tuple[int, int], board, transposed_board
    ) -> int:
        """Calculates the point score of a play (including all secondary words)

        Args:
            word (str): HORIZONTAL Collinear and adjacent letters played on the board
            starting_position (tuple[int, int]): The coordinates of the first letter of the word
            board (list[list[]]): board (relative to the tranpose of the word)
            transposed_board (list[list[]]): transposed board (relative to the tranpose of the word)

        Returns:
            int: The total score of the play
        """

        # ----------------------------------------------
        def _score_word(word, starting_position, board) -> int:
            """Calculates the score of a word

            Args:
                word (str): String of the word to score
                starting_position (tuple(int, int)): x, y coordinates of the first letter of the word
                board (list[list[]]): board

            Returns:
                int: The score of the word
            """
            multiplier = 1
            score = 0

            x, y = starting_position

            ## Below is a check for invalid plays
            # if not self.is_word(word):
            #     raise ValueError(f"{word} is not a valid word")

            for letter in word:
                square = self.game.bonuses[y][x]
                value = self.game.letter_values[letter]
                # checks the board that is passed in
                if square != 0 and board[y][x] == 0:
                    value, multiplier = self.game.get_bonus_value[square](
                        value, multiplier
                    )
                score += value
                x += 1
            score *= multiplier
            return score

        # ----------------------------------------------

        x, y = starting_position
        total_score = 0

        # This counter is for the 7 letter "bingo". If the player uses all 7 letters, they get a 50 point bonus
        counter = 0

        # This loop calls _score_word on all the secondary words
        for char in word:
            if board[y][x] != 0:
                x += 1
                continue
            counter += 1
            if (
                (y - 1) >= 0
                and board[y - 1][x] != 0
                or (y + 1) < len(board)
                and board[y + 1][x] != 0
            ):
                secondary_word = char
                y_1 = y - 1
                y_2 = y + 1
                while y_1 >= 0 and board[y_1][x] != 0:
                    secondary_word = board[y_1][x] + secondary_word
                    y_1 -= 1
                while y_2 < len(board) and board[y_2][x] != 0:
                    secondary_word += board[y_2][x]
                    y_2 += 1

                total_score += _score_word(
                    word=secondary_word,
                    starting_position=(y_1 + 1, x),
                    board=transposed_board,
                )
            x += 1

        # Add score of the main word
        total_score += _score_word(
            word=word, starting_position=starting_position, board=board
        )
        total_score += 50 if counter >= 7 else 0

        return total_score

    def _build_valid_prefix(
        self,
        suffix: str,
        node: Node,
        rack: list[str],
        board,
        position: tuple[int, int],
        valid_words: list = None,
        usedRack: bool = False,
    ) -> list:
        """Recursively builds a list of all valid prefixes that can be built from a rack and an origin


        ---------IMPORTANT---------
        - *** ALL LOGIC IS BASED ON HORIZONTAL WORD CONSTRUCTUION
        - You should only call this on positions s.t. there is no letter to the right of it. This avoids redudant outputs
        - Call this with the tranpose of board if you want the vertical prefixes
        --------------------------
        Args:

            suffix (str): Sub-Suffix to build prefixes from.
            node (Node): Node of the current first letter of suffix (ETA`R`, for prefix "RATE").
            rack (list[str]): Characters in the rack.
            board : Current board state.
            position (tuple[int, int]): The position to check.

        Returns:
            list[dict]: _description_
        """

        x, y = position

        if valid_words is None:
            valid_words = []

        # While x,y is occupied, check if its part of a valid prefix
        # After this loop, x,y NEVER has a letter on it (either off the board or is empty)
        while x >= 0 and board[y][x] != 0:
            if board[y][x] in node.children:
                node = node.children[board[y][x]]
                suffix = board[y][x] + suffix
                x -= 1
            else:
                return valid_words

        # Checks for delimeter node (denotes a valid prefix)
        if "#" in node.children:
            # The x value of this position denotes the square to the left of the prefix
            # This square is guaranteed to be empty
            new_position = (x + len(suffix) + 1, y)
            # Get the delimeter node
            # See gaddag strcuture for more info
            new_node = node.children["#"]

            # Save the starting position of the prefix
            start_position = (x + 1, y)

            words = self._build_valid_suffix(
                prefix=suffix,
                node=new_node,
                rack=rack,
                board=board,
                position=new_position,
                usedRack=usedRack,
            )
            for word in words:
                valid_words.append({"word": word, "start_position": start_position})

        # At this point, x,y is the square we are trying to place a new letter at
        # If this is out of bounds or we have no letters in the rack, return the valid prefixes
        if x < 0 or len(rack) == 0:
            return valid_words

        candidate_letters = self._get_candidate_letters(rack, board, (x, y))
        for char in candidate_letters:
            if char in node.children:
                # `place` the letter on the board and remove it from the rack
                new_rack = rack.copy()
                new_rack.remove(char)
                new_node = node.children[char]

                # Prevents returning a word where the player doesn't play a letter.
                usedRack = True
                valid_words = self._build_valid_prefix(
                    char + suffix,
                    new_node,
                    new_rack,
                    board,
                    (x - 1, y),
                    valid_words,
                    usedRack,
                )

        return valid_words

    def _build_all_words(
        self, rack: list[str], num_words=16, board=None, first_move=False
    ) -> list[dict]:
        """_summary_

        Args:
            rack (list[str]): letters avaible to player
            board (list[list[str]], optional): current board state. Defaults to self.game.board.
            num_words (int, optional): Number of words. Defaults to 20.
            first_move (bool, optional): If this is the first move of the game. Defaults to False.

        Notes:
            - Word building is done in two steps: PREFIX -> SUFFIX


        Returns:
            list[dict]: Sorted list of words and their scores
        """

        def _get_candidate_positions(board):
            for y in range(len(board)):
                for x in range(len(board[0])):
                    square = board[y][x]

                    hasLetter = square != 0
                    isOnRightBorder = x == (len(board) - 1)
                    hasEmptySquareToRight = x + 1 < len(board) and board[y][x + 1] == 0

                    hasLetterAbove = y - 1 >= 0 and board[y - 1][x] != 0
                    hasLetterBelow = y + 1 < len(board) and board[y + 1][x] != 0

                    if (hasLetter and (isOnRightBorder or hasEmptySquareToRight)) or (
                        hasLetterAbove or hasLetterBelow
                    ):
                        if hasLetterAbove or hasLetterBelow:
                            yield (x, y)

        def _construct_words(board, transposed_board, rack, position, is_tranpose):
            """Builds all plays given a position on the board

            Args:
                board (list[list[]]): board
                transposed_board (list[list[]]): transposed board
                rack (list[str]): letters available to player
                position (tuple[int, int]): position to check
                is_tranpose (bool): is the board transposed?

            Returns:
                list[dict]: List of all valid words (each index has keys "word", "start_position", "score", "is_transpose")
            """
            valid_words = []
            x, y = position
            words = self._build_valid_prefix(
                suffix="", node=self.root, rack=rack, board=board, position=(x, y)
            )

            # adding score / starting position to the horizontal words
            for play in words:
                word = play["word"]
                start_position = play["start_position"]
                score = self.score_play(
                    word=word,
                    starting_position=start_position,
                    board=board,
                    transposed_board=transposed_board,
                )
                valid_words.append(
                    {
                        "word": word,
                        "start_position": start_position,
                        "score": score,
                        "is_transpose": is_tranpose,
                    }
                )
            # ------------------------------------------------------
            return valid_words

        # ----------------------------------------------

        # Sets default value for board
        if board is None:
            board = self.game.board

        all_words = []

        transposed_board = self.get_tranposed_board(board=board)

        if first_move:
            # Only finds horizontal words for the first move (symmetry makes vertical words redudant)
            all_words += _construct_words(board, transposed_board, rack, (7, 7), False)

        else:
            # Finds all HORIZONTAL words
            for position in _get_candidate_positions(board):
                all_words += _construct_words(
                    board, transposed_board, rack, position, False
                )

            # Finds all VERTICAL words
            for position in _get_candidate_positions(transposed_board):
                all_words += _construct_words(
                    transposed_board, board, rack, position, True
                )

        # Sorts the words by score, returns the top {num_words}
        return heapq.nlargest(num_words, all_words, key=lambda x: x["score"])

