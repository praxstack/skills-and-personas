"""The film kit: everything a scene needs, re-exported so scenes.py can say `from kit import *`.

    timing   TIMING, L, TOTAL, lines_in()              the voice clock (timing.json)
    film     FilmScene                                 base class: until(), beat(), play_until(), cam(), hud(), captions
    style    palette, fonts, SIZE, px(), fs(), Z        one place for the look
    text     T, H, Mono, Rich, Formula                  text without LaTeX (superscripts via Rich)
    backdrop backdrop_png, dot_grid                     depth: painted background + world grid
    fx       glow, halo, soft_shadow, ripple, pulse, roll, conceal/unconceal (hide without breaking groups)
    graph    WGraph, Token, fly, reject, auto_layout    the persistent subject, the travelling token, illegal moves
    cards    chapter_tag, title_block, lower_third, think_ring   (+ FilmScene.chapter_card / .question)
    decoder  InputDecoder                               raw input text whose entries fly into the subject
    table    ArrayRow, DPTable, INF                     DP rows that fill cell by cell
    ladder   Ladder                                     complexity ladder with the pick marked
    code     CodePanel                                  syntax-coloured code, active line, chunked reveal
    callout  burst, pop                                 comic bursts
"""
from .style import *  # noqa: F401,F403
from .timing import TIMING, L, LINES, TOTAL, FPS, CHAPTERS, CHAPTER_NAMES, lines_in, bounds  # noqa: F401
from .text import T, H, Mono, Rich, Formula, wrap_lines  # noqa: F401
from .backdrop import backdrop_png, dot_grid  # noqa: F401
from .fx import glow, halo, soft_shadow, disc_shadow, ripple, pulse, roll, straight_path, conceal, unconceal  # noqa: F401
from .film import FilmScene, list_segments  # noqa: F401
from .graph import WGraph, Token, fly, reject, auto_layout, plane_shape  # noqa: F401
from .cards import chapter_tag, title_block, lower_third, think_ring  # noqa: F401
from .decoder import InputDecoder  # noqa: F401
from .table import ArrayRow, DPTable, INF, show  # noqa: F401
from .ladder import Ladder  # noqa: F401
from .code import CodePanel, FilmCodeStyle  # noqa: F401
from .callout import burst, pop, starburst  # noqa: F401
