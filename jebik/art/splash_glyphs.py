"""Monument block letters for the studio splash (art-deco, condensed, blocky).

Each glyph is a list of ``(op, polygon)`` in a unit box (height 1, y down):
``"+"`` fills, ``"-"`` cuts (counters / openings). Only the letters the
logo needs are defined.
"""
from __future__ import annotations

Poly = list[tuple[float, float]]
S = 0.19            # stroke


def rect(x0: float, y0: float, x1: float, y1: float) -> Poly:
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def octa(x0: float, y0: float, x1: float, y1: float, c: float) -> Poly:
    """Rectangle with chamfered corners."""
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1),
            (x0, y1 - c), (x0, y0 + c)]


def _h(w: float) -> list[tuple[str, Poly]]:
    return [("+", rect(0, 0, S, 1)), ("+", rect(w - S, 0, w, 1)), ("+", rect(0, .42, w, .42 + S))]


def _t(w: float) -> list[tuple[str, Poly]]:
    return [("+", rect(0, 0, w, S)), ("+", rect((w - S) / 2, 0, (w + S) / 2, 1))]


def _o(w: float) -> list[tuple[str, Poly]]:
    return [("+", octa(0, 0, w, 1, .16)), ("-", octa(S, S, w - S, 1 - S, .06))]


def _c(w: float) -> list[tuple[str, Poly]]:
    return _o(w) + [("-", rect(w - S - .01, .36, w + .01, .64))]


def _g(w: float) -> list[tuple[str, Poly]]:
    return _o(w) + [("-", rect(w - S - .01, .3, w + .01, .5)), ("+", rect(w * .5, .5, w, .5 + S * .8))]


def _a(w: float) -> list[tuple[str, Poly]]:
    return [("+", [(0, 1), (w * .3, 0), (w * .7, 0), (w, 1)]),
            ("-", [(w * .5 - .05, S + .02), (w * .5 + .05, S + .02), (w * .5 + .1, .5), (w * .5 - .1, .5)]),
            ("-", [(w * .5 - .14, .5 + S), (w * .5 + .14, .5 + S), (w - S * 1.05, 1.01), (S * 1.05, 1.01)])]


def _n(w: float) -> list[tuple[str, Poly]]:
    return [("+", rect(0, 0, S, 1)), ("+", rect(w - S, 0, w, 1)),
            ("+", [(0, 0), (S * 1.1, 0), (w, 1), (w - S * 1.1, 1)])]


def _m(w: float) -> list[tuple[str, Poly]]:
    return [("+", rect(0, 0, S, 1)), ("+", rect(w - S, 0, w, 1)),
            ("+", [(0, 0), (S * 1.05, 0), (w / 2 + S * .5, .66), (w / 2 - S * .5, .66)]),
            ("+", [(w, 0), (w - S * 1.05, 0), (w / 2 - S * .5, .66), (w / 2 + S * .5, .66)])]


def _one(w: float) -> list[tuple[str, Poly]]:
    x0 = w - S - .08
    return [("+", rect(x0, 0, x0 + S, 1)), ("+", [(x0, 0), (x0 + .02, .2), (0, .3), (0, .16)]),
            ("+", rect(.02, 1 - S * .8, w, 1))]


def _two(w: float) -> list[tuple[str, Poly]]:
    return [("+", [(0, .14), (.14, 0), (w - .14, 0), (w, .14), (w, .44), (w - S, .44), (w - S, S),
                   (S, S), (S, .26), (0, .26)]),
            ("+", [(w - S, .44), (w, .44), (w, .5), (S * 1.2, 1 - S), (0, 1 - S), (0, .92)]),
            ("+", rect(0, 1 - S, w, 1))]


GLYPHS = {"H": (_h, .62), "T": (_t, .62), "O": (_o, .64), "C": (_c, .62), "G": (_g, .64),
          "A": (_a, .72), "N": (_n, .66), "M": (_m, .82), "1": (_one, .46), "2": (_two, .62)}


def glyph(ch: str) -> tuple[list[tuple[str, Poly]], float]:
    fn, w = GLYPHS[ch]
    return fn(w), w
