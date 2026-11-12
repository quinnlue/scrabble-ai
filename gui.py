import time
from dataclasses import dataclass, field
from html import escape

import ipywidgets as w
from IPython.display import display

from scrabble import Scrabble
from scrabble_ai import ScrabbleAI


@dataclass
class SearchSettings:
    max_depth: int = 2
    width: int = 5
    num_words_explored: list = field(default_factory=lambda: [8, 4])
    random_opponent_rack: bool = True

    def words_per_ply(self):
        """num_words_explored padded / trimmed to exactly max_depth entries."""
        words = list(self.num_words_explored) or [1]
        words += [words[-1]] * (self.max_depth - len(words))
        return words[: self.max_depth]


CELL = 32

BONUS_COLOR = {
    0: "#e9e4d4",  # plain
    1: "#bfe0f2",  # double letter
    2: "#4a8bd1",  # triple letter
    3: "#f3c0c0",  # double word
    4: "#cf4444",  # triple word
    5: "#f3c0c0",  # center
}
TILE_BG, TILE_FG = "#f1dcaa", "#3a2a10"
NEW_TILE_BG = "#ffc94a"


def _tile(letter, value, size, bg=TILE_BG):
    return (
        f'<span style="display:inline-block;position:relative;width:{size}px;height:{size}px;'
        f"line-height:{size}px;text-align:center;background:{bg};color:{TILE_FG};font-weight:700;"
        f'font-size:{int(size * .55)}px;font-family:Helvetica,Arial,sans-serif;margin:1px">'
        f"{letter}"
        f'<span style="position:absolute;right:2px;bottom:1px;line-height:1;'
        f'font-size:{max(7, int(size * .26))}px;font-weight:600">{value}</span></span>'
    )


def render_board(game, new_tiles=frozenset()):
    out = [
        f'<div style="display:inline-grid;grid-template-columns:repeat(15,{CELL}px);'
        f'gap:1px;padding:1px;background:#888">'
    ]
    for y, row in enumerate(game.board):
        for x, letter in enumerate(row):
            if letter != 0:
                bg = NEW_TILE_BG if (x, y) in new_tiles else TILE_BG
                out.append(_tile(letter, game.letter_values[letter], CELL, bg).replace("margin:1px", "margin:0"))
            else:
                bg = BONUS_COLOR[game.bonuses[y][x]]
                out.append(f'<div style="width:{CELL}px;height:{CELL}px;background:{bg}"></div>')
    out.append("</div>")
    return "".join(out)


class ScrabbleGUI:
    def __init__(self, game: Scrabble, ai: ScrabbleAI, settings: SearchSettings = None):
        self.game = game
        self.ai = ai
        self.settings = settings or SearchSettings()
        self._reset_game_state()

        s = self.settings
        style = {"description_width": "120px"}
        wide = w.Layout(width="330px")

        self.depth = w.IntSlider(s.max_depth, min=1, max=4, description="max_depth", style=style, layout=wide)
        self.width = w.IntSlider(s.width, min=1, max=30, description="width", style=style, layout=wide)
        self.random_rack = w.Checkbox(s.random_opponent_rack, description="random_opponent_rack", indent=False)
        self.ply_box = w.VBox()
        self._build_ply_sliders(s.words_per_ply())

        self.next_btn = w.Button(description="Next move", button_style="primary", icon="play")
        self.new_btn = w.Button(description="New game", icon="refresh")
        self.status = w.HTML()
        self.board_html = w.HTML()
        self.info_html = w.HTML(layout=w.Layout(width="360px"))

        self.depth.observe(self._on_depth, names="value")
        self.width.observe(self._sync_settings, names="value")
        self.random_rack.observe(self._sync_settings, names="value")
        self.next_btn.on_click(self.next_move)
        self.new_btn.on_click(self.new_game)

        controls = w.VBox(
            [
                w.HTML("<b>Search settings</b>"),
                self.depth,
                self.width,
                w.HTML("<span style='font-size:12px;opacity:.75'>num_words_explored (candidate words per ply)</span>"),
                self.ply_box,
                self.random_rack,
                w.HBox([self.next_btn, self.new_btn]),
                self.status,
            ],
            layout=w.Layout(width="360px"),
        )
        self.root = w.HBox(
            [self.board_html, w.VBox([controls, self.info_html], layout=w.Layout(margin="0 0 0 16px"))],
            layout=w.Layout(flex_flow="row wrap", align_items="flex-start"),
        )
        self.render()

    def _ipython_display_(self):
        display(self.root)

    def _build_ply_sliders(self, values):
        sliders = []
        for i, v in enumerate(values):
            sl = w.IntSlider(
                v, min=1, max=20, description=f"ply {i + 1}",
                style={"description_width": "120px"}, layout=w.Layout(width="330px"),
            )
            sl.observe(self._sync_settings, names="value")
            sliders.append(sl)
        self.ply_box.children = sliders

    def _on_depth(self, change):
        values = [sl.value for sl in self.ply_box.children]
        values += [values[-1]] * (change["new"] - len(values))
        self._build_ply_sliders(values[: change["new"]])
        self._sync_settings()

    def _sync_settings(self, *_):
        s = self.settings
        s.max_depth = self.depth.value
        s.width = self.width.value
        s.num_words_explored = [sl.value for sl in self.ply_box.children]
        s.random_opponent_rack = self.random_rack.value

    def _reset_game_state(self):
        self.move_num = 0
        self.consecutive_passes = 0
        self.game_over = False
        self.new_tiles = set()
        self.last_candidates = []
        self.last_mover = None
        self.last_chosen = None
        self.last_time = None
        self.history = []

    def new_game(self, _=None):
        self.game = Scrabble(num_players=self.game.num_players, num_letters=self.game.num_letters)
        self.ai = ScrabbleAI(self.game, gaddag=self.ai.solver.gaddag)
        self._reset_game_state()
        self.status.value = ""
        self.render()

    def next_move(self, _=None):
        if self.game_over:
            return
        self.next_btn.disabled = self.new_btn.disabled = True
        self.status.value = "<i>Thinking&hellip;</i>"
        try:
            self._play_turn()
            self.status.value = ""
        except Exception as e:  # show errors in the GUI instead of losing them
            self.status.value = f"<span style='color:#d33'>Error: {escape(repr(e))}</span>"
            raise
        finally:
            self.next_btn.disabled = self.game_over
            self.new_btn.disabled = False
            self.render()

    def _play_turn(self):
        game, s = self.game, self.settings
        player = game.current_player
        is_first_move = all(cell == 0 for row in game.board for cell in row)

        self.ai.set_state(game.get_game_state())
        t0 = time.time()
        moves = self.ai.find_best_move(
            is_first_move=is_first_move,
            max_depth=s.max_depth,
            width=s.width,
            num_words_explored=s.words_per_ply(),
            random_opponent_rack=s.random_opponent_rack,
        )
        self.last_time = time.time() - t0
        self.last_mover = player
        self.last_candidates = moves
        self.move_num += 1

        if not moves:
            game.next_player()
            self.new_tiles = set()
            self.last_chosen = None
            self.consecutive_passes += 1
            self.history.append((player, None))
        else:
            best = moves[0]["move"]
            before = [row[:] for row in game.board]
            game.play_word(
                word=best["word"],
                score=best["score"],
                start_position=best["start_position"],
                is_transpose=best["is_transpose"],
            )
            self.new_tiles = {
                (x, y)
                for y, row in enumerate(game.board)
                for x, cell in enumerate(row)
                if cell != before[y][x]
            }
            self.last_chosen = best
            self.consecutive_passes = 0
            self.history.append((player, best))

        out_of_tiles = not game.letter_counts and not game.players[player]["rack"]
        if out_of_tiles or self.consecutive_passes >= game.num_players:
            self.game_over = True

    def render(self):
        self.board_html.value = render_board(self.game, self.new_tiles)
        self.info_html.value = self._render_info()
        self.next_btn.disabled = self.game_over

    def _render_info(self):
        game = self.game
        muted = "opacity:.7;font-size:12px"
        parts = []

        # players
        rows = []
        for pid, p in game.players.items():
            turn = pid == game.current_player and not self.game_over
            rack = "".join(_tile(l, game.letter_values[l], 22) for l in p["rack"])
            rows.append(
                f"<tr style='{'font-weight:700' if turn else ''}'>"
                f"<td style='padding:3px 8px 3px 0'>{'&#9654; ' if turn else ''}{escape(p['name'])}</td>"
                f"<td style='padding:3px 8px;text-align:right'>{p['score']}</td>"
                f"<td style='padding:3px 0'>{rack}</td></tr>"
            )
        parts.append(f"<table style='border-collapse:collapse'>{''.join(rows)}</table>")
        parts.append(f"<div style='{muted}'>Move {self.move_num} &middot; {len(game.letter_counts)} tiles in bag</div>")

        if self.game_over:
            best = max(p["score"] for p in game.players.values())
            winners = [p["name"] for p in game.players.values() if p["score"] == best]
            parts.append(f"<div style='margin-top:8px;font-weight:700'>Game over &mdash; {escape(' & '.join(winners))} wins with {best}</div>")

        # last move + candidates the search considered
        if self.last_mover is not None:
            name = escape(game.players[self.last_mover]["name"])
            if self.last_chosen is None:
                parts.append(f"<div style='margin-top:10px'><b>{name}</b> had no legal move and passed.</div>")
            else:
                m = self.last_chosen
                parts.append(
                    f"<div style='margin-top:10px'><b>{name}</b> played <b>{m['word']}</b> "
                    f"for <b>{m['score']}</b> <span style='{muted}'>(search {self.last_time:.2f}s)</span></div>"
                )
                cand_rows = "".join(
                    f"<tr style='{'font-weight:700' if i == 0 else ''}'>"
                    f"<td style='padding:1px 10px 1px 0'>{c['move']['word']}</td>"
                    f"<td style='padding:1px 10px;text-align:right'>{c['move']['score']}</td>"
                    f"<td style='padding:1px 0 1px 10px;text-align:right'>{float(c['ev']):.1f}</td></tr>"
                    for i, c in enumerate(self.last_candidates[:8])
                )
                parts.append(
                    "<table style='border-collapse:collapse;font-size:12px;margin-top:4px'>"
                    f"<tr style='{muted}'><td>word</td>"
                    "<td style='padding:0 10px;text-align:right'>score</td><td style='text-align:right'>EV</td></tr>"
                    f"{cand_rows}</table>"
                )

        if self.history:
            lines = []
            for i, (pid, m) in reversed(list(enumerate(self.history, 1))):
                who = escape(game.players[pid]["name"])
                what = "pass" if m is None else f"{m['word']} +{m['score']}"
                lines.append(f"<div>{i}. {who}: {what}</div>")
            parts.append(
                f"<div style='margin-top:10px;{muted}'>History</div>"
                f"<div style='max-height:160px;overflow-y:auto;font-size:12px'>{''.join(lines)}</div>"
            )

        return f"<div style='font-family:Helvetica,Arial,sans-serif;font-size:13px'>{''.join(parts)}</div>"
