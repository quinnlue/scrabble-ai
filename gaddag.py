import zlib
import pickle
import os


class Node:
    def __init__(self, letter=None):
        self.children = {}
        self.value = letter
        self.is_word = False


class Gaddag:
    def __init__(self, dictionary_file="dictionary.txt", gaddag_file="gaddag.pkl"):
        self.dictionary_file = dictionary_file
        self.gaddag_file = gaddag_file
        self.root = Node()

        if os.path.exists(gaddag_file):
            self.load_gaddag()
        else:
            self.build_and_save_gaddag()

    def build_and_save_gaddag(self):
        with open(self.dictionary_file, "r") as file:
            for word in file.read().splitlines():
                word = word[::-1] + "#"
                for i in range(len(word) - 1):
                    self.add_to_graph(word[i:] + word[:i][::-1])
        self.save_gaddag()

    def add_to_graph(self, word):
        node = self.root
        for letter in word:
            if letter not in node.children:
                node.children[letter] = Node(letter)
            node = node.children[letter]
        node.is_word = True
        node.children["$"] = Node("$")

    def is_valid_word(self, word):
        word = (word[::-1] + "#").upper()
        node = self.root
        for letter in word:
            if letter not in node.children:
                return False
            node = node.children[letter]
        return "$" in node.children

    def save_gaddag(self):
        with open(self.gaddag_file, "wb") as file:
            # Serialize and then compress the GADDAG structure
            serialized_data = pickle.dumps(self.root)
            compressed_data = zlib.compress(serialized_data)
            file.write(compressed_data)
        print("GADDAG saved to", self.gaddag_file)

    def load_gaddag(self):
        with open(self.gaddag_file, "rb") as file:
            compressed_data = file.read()
            # Decompress and then load the GADDAG structure
            serialized_data = zlib.decompress(compressed_data)
            self.root = pickle.loads(serialized_data)
        print("GADDAG loaded from", self.gaddag_file)


if __name__ == "__main__":
    # Create or load the GADDAG
    gaddag = Gaddag(dictionary_file="dictionary2.txt", gaddag_file="gaddag.pkl")
    print("GADDAG has been built and saved!")
