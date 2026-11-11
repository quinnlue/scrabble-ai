import random


class Scrabble:
    def __init__(self, num_players: int = 2, num_letters=7):
        """Initializes the Scrabble game

        Args:
            num_players (int, optional): Number of players in the game (2 <= n, n <= 4 ). Defaults to 2.
            num_letters (int, optional): Number of letters in each player's rack. Defaults to 7.

        Notes:
            Sets current player to 0
            Board is a 15x15 grid
        Raises:
            ValueError: Raises for invalid inputs (num_players, num_letters)
        """
        # GAME SETUP ---------------------------------------------------
        # Number of letters in each player's rack
        if num_letters < 1:
            raise ValueError("Number of letters must be greater than 0.")
        self.num_letters = num_letters

        if num_players < 2 or num_players > 4:
            raise ValueError("Number of players must be between 2 and 4.")
        self.num_players = num_players

        # Letter counts in the bag
        self.letter_counts = list(
            "A" * 9
            + "B" * 2
            + "C" * 2
            + "D" * 4
            + "E" * 12
            + "F" * 2
            + "G" * 3
            + "H" * 2
            + "I" * 9
            + "J" * 1
            + "K" * 1
            + "L" * 4
            + "M" * 2
            + "N" * 6
            + "O" * 8
            + "P" * 2
            + "Q" * 1
            + "R" * 6
            + "S" * 4
            + "T" * 6
            + "U" * 4
            + "V" * 2
            + "W" * 2
            + "X" * 1
            + "Y" * 2
            + "Z" * 1
        )

        # Point values of each letter
        self.letter_values = {
            "A": 1,
            "B": 3,
            "C": 3,
            "D": 2,
            "E": 1,
            "F": 4,
            "G": 2,
            "H": 4,
            "I": 1,
            "J": 8,
            "K": 5,
            "L": 1,
            "M": 3,
            "N": 1,
            "O": 1,
            "P": 3,
            "Q": 10,
            "R": 1,
            "S": 1,
            "T": 1,
            "U": 1,
            "V": 4,
            "W": 4,
            "X": 8,
            "Y": 4,
            "Z": 10,
        }

        # Bonus square logic
        self.get_bonus_value = {
            1: lambda value, multiplier: (value * 2, multiplier),
            2: lambda value, multiplier: (value * 3, multiplier),
            3: lambda value, multiplier: (value, multiplier * 2),
            4: lambda value, multiplier: (value, multiplier * 3),
            5: lambda value, multiplier: (value, multiplier * 2),
        }

        self.bonus_squares = {
            1: "double letter",
            2: "triple letter",
            3: "double word",
            4: "triple word",
        }
        self.square_colors = {
            0: "white",  # Normal square
            1: "lightblue",  # Double letter
            2: "indianred",  # Double letter
            3: "deepskyblue",  # Double word
            4: "red",  # Triple word
            5: "yellow",  # center (also double word)
        }
        self.turn = 1

        # This stores all the prior word placements (i.e. board state)
        self.board = [
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ]

        # Bonus square values
        # SEE self.bonus_squares
        self.bonuses = [
            [4, 0, 0, 1, 0, 0, 0, 4, 0, 0, 0, 1, 0, 0, 4],
            [0, 3, 0, 0, 0, 2, 0, 0, 0, 2, 0, 0, 0, 3, 0],
            [0, 0, 3, 0, 0, 0, 1, 0, 1, 0, 0, 0, 3, 0, 0],
            [1, 0, 0, 3, 0, 0, 0, 1, 0, 0, 0, 3, 0, 0, 1],
            [0, 0, 0, 0, 3, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0],
            [0, 2, 0, 0, 0, 2, 0, 0, 0, 2, 0, 0, 0, 2, 0],
            [0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0],
            [4, 0, 0, 1, 0, 0, 0, 5, 0, 0, 0, 1, 0, 0, 4],
            [0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0],
            [0, 2, 0, 0, 0, 2, 0, 0, 0, 2, 0, 0, 0, 2, 0],
            [0, 0, 0, 0, 3, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0],
            [1, 0, 0, 3, 0, 0, 0, 1, 0, 0, 0, 3, 0, 0, 1],
            [0, 0, 3, 0, 0, 0, 1, 0, 1, 0, 0, 0, 3, 0, 0],
            [0, 3, 0, 0, 0, 2, 0, 0, 0, 2, 0, 0, 0, 3, 0],
            [4, 0, 0, 1, 0, 0, 0, 4, 0, 0, 0, 1, 0, 0, 4],
        ]
        # ----------------------------------------------------------------

        self.players = {
            played_id: {
                "name": f"Player {played_id}",
                "score": 0,
                "rack": self.draw_letters(num_letters),
            }
            for played_id in range(num_players)
        }
        self.current_player = 0

    def get_game_state(self):
        """
        Returns:
            dict: The current game state. Keys: board, letter_counts, players, turn
        """
        game_state = {
            "board": self.board,
            "letter_counts": self.letter_counts,
            "players": self.players,
            "turn": self.current_player,
        }
        return game_state

    def next_player(self):
        """
        Updates self.current_player to the next player

        Returns:
            int: The new current player
        """
        self.current_player = (self.current_player + 1) % self.num_players
        return self.current_player

    def draw_letters(
        self, n: int, isRemoval: bool = True, letter_counts=None
    ) -> list[str]:
        """Draws letters from the bag

        Args:
            n (int): Number of letters to draw
            isRemoval (bool, optional): Whether to remove the drawn letters from the bag. Defaults to True
            letter_counts (list[str], optional): Dictionary of letter counts. Defaults to self.letter_counts.

        Returns:
            list[str]: List of drawn letters
        """

        # Sets default value of letter_counts pointer
        if letter_counts == None:
            letter_counts = self.letter_counts

        # Prevents drawing more letters than there are left
        n = min(n, len(letter_counts))

        letters = random.sample(letter_counts, n)

        # Removes the drawn letters from the letter_counts pointer
        if isRemoval:
            for letter in letters:
                letter_counts.remove(letter)

        return letters

    def display_board(self):
        """Displays the board using tkinter"""

        import tkinter as tk

        root = tk.Tk()

        canvas = tk.Canvas(root, width=600, height=600, bg="white")
        canvas.pack()

        cell_size = 40
        for i, row in enumerate(self.board):
            for j, tile in enumerate(row):
                x0, y0 = j * cell_size, i * cell_size
                x1, y1 = x0 + cell_size, y0 + cell_size

                # Determine the cell's background color
                if tile != 0:
                    color = "#D8B989"
                    width = 4
                else:
                    bonus = self.bonuses[i][j]
                    color = self.square_colors.get(bonus, "white")
                    width = 1

                canvas.create_rectangle(
                    x0, y0, x1, y1, fill=color, outline="black", width=width
                )

                # Draw the letter tile or bonus text
                if tile != 0:
                    canvas.create_text(
                        x0 + cell_size / 2,
                        y0 + cell_size / 2,
                        text=tile.upper(),
                        font=("Helvetica", 16, "bold"),
                        fill="white",
                    )

                    # Draw the value in the bottom-right corner
                    value = self.letter_values.get(tile.upper(), 0)
                    canvas.create_text(
                        x1 - 5,
                        y1 - 5,
                        text=str(value),
                        font=("Helvetica", 10, "bold"),
                        anchor="se",
                    )
                elif self.bonuses[i][j] != 0:
                    bonus_text = {1: "DL", 2: "TL", 3: "DW", 4: "TW", 5: "★"}.get(
                        self.bonuses[i][j], ""
                    )
                    canvas.create_text(
                        x0 + cell_size / 2,
                        y0 + cell_size / 2,
                        text=bonus_text,
                        font=("Helvetica", 10),
                        fill="black",
                    )

        root.mainloop()

    def print_board(self):
        for row in self.board:
            print(" ".join(str(cell) for cell in row))

    def play_word(
        self, word: str, score: str, start_position: tuple[int, int], is_transpose: bool
    ):
        """Updates board, draws new letters, updates score, and switches turn

        Args:
            word (str): String of the word to play
            score (str): Points scored by the word
            start_position (tuple[int,int]): Absolute position of the first letter of the word (not transposed)
            is_transpose (bool): Whether the word is transposed

        Raises:
            ValueError: Raises when an illegal move is played
        """
        x, y = start_position
        player = self.players[self.current_player]
        if is_transpose:
            x, y = y, x

        for letter in word:
            if self.board[y][x] != 0:
                pass
            else:
                if letter not in player["rack"]:
                    raise ValueError(
                        f"Attempting to play an illegal move. Letter {letter} not in player {self.current_player}'s rack."
                    )
                player["rack"].remove(letter)
                self.board[y][x] = letter

            if is_transpose:
                y += 1
            else:
                x += 1

        player["score"] += score

        num_letters_to_draw = self.num_letters - len(player["rack"])
        player["rack"] += self.draw_letters(n=num_letters_to_draw, isRemoval=True)

        self.next_player()
