import zlib
import pickle
import os


class Node:
    __slots__ = ("children", "value", "is_word")

    def __init__(self, letter=None):
        self.children = {}
        self.value = letter
        self.is_word = False

    def __getstate__(self):
        return self.children, self.value, self.is_word

    def __setstate__(self, state):
        if isinstance(state, dict):
            # Older caches stored each node's instance dictionary.
            self.children = state["children"]
            self.value = state["value"]
            self.is_word = state["is_word"]
            if "$" in self.children:
                self.children["$"] = _WORD_END
        else:
            self.children, self.value, self.is_word = state


class _WordEnd(Node):
    __slots__ = ()

    def __reduce__(self):
        return "_WORD_END"


_WORD_END = _WordEnd("$")


class Gaddag:
    def __init__(
        self, dictionary_file="dictionary.txt", gaddag_file="gaddag.pkl", *,
        max_word_length=None,
    ):
        self.dictionary_file = dictionary_file
        self.gaddag_file = gaddag_file
        self.max_word_length = max_word_length
        self.root = Node()

        if os.path.exists(gaddag_file):
            self.load_gaddag()
        else:
            self.build_and_save_gaddag()

    def build_and_save_gaddag(self):
        with open(self.dictionary_file, "r") as file:
            for word in file.read().splitlines():
                if self.max_word_length is not None and len(word) > self.max_word_length:
                    continue
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
        node.children["$"] = _WORD_END

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
    # Use the importable module name in the cache.
    from gaddag import Gaddag

    Gaddag()
