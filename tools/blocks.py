"""Draws simplified MakeCode block pictures as static SVG files.

Run:  python3 tools/blocks.py          (writes images/blocks/<id>.<lang>.svg)
      python3 tools/blocks.py --check  (fails if the files are out of date)

Colours were sampled from a real MakeCode screenshot. The pictures are
simplified, so check each block against MakeCode before publishing.
"""
import os
import sys
from xml.sax.saxutils import escape

LANGS = ("en", "da")
OUT = os.path.join(os.path.dirname(__file__), "..", "images", "blocks")

COLOURS = {
    "basic": "#468EF7", "input": "#C329CD", "music": "#D44231", "led": "#56308C",
    "radio": "#D02C8A", "loops": "#4CA830", "logic": "#49A2A5",
    "variables": "#CA3142", "math": "#8819CB",
}
ICONS = {
    "heart": ["01010", "11111", "11111", "01110", "00100"],
    "happy": ["00000", "01010", "00000", "10001", "01110"],
}

ROW, PAD, GAP, ARM, FOOT, CHAR = 40, 12, 8, 18, 22, 10.2
INK = "#1F2A44"


def _shade(hex_colour, k):
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02X%02X%02X" % tuple(min(255, round(c * k)) for c in (r, g, b))


def _text(v, lang):
    return v[lang] if isinstance(v, dict) else v


def _parts(b, lang):
    """The parts that show in this language (an empty label is left out)."""
    return [p for p in b["parts"] if "t" not in p or _text(p["t"], lang)]


def _part_width(p, lang):
    if "t" in p:
        return len(_text(p["t"], lang)) * CHAR
    if "slot" in p:
        return max(34, len(_text(p["slot"], lang)) * CHAR + 18)
    if "drop" in p:
        return len(_text(p["drop"], lang)) * CHAR + 18 + 16
    return 54  # icon


def _header_width(b, lang):
    parts = _parts(b, lang)
    return PAD * 2 + sum(_part_width(p, lang) for p in parts) + GAP * (len(parts) - 1)


def _size(b, lang):
    head = _header_width(b, lang)
    kids = b.get("children", [])
    if not kids:
        return head, ROW
    sizes = [_size(k, lang) for k in kids]
    width = max(head, ARM + max(w for w, _ in sizes))
    return width, ROW + sum(h for _, h in sizes) + FOOT


def _draw(b, lang, x, y):
    col = COLOURS[b["cat"]]
    edge = _shade(col, 0.8)
    width, height = _size(b, lang)
    head = _header_width(b, lang)
    out = []
    style = 'fill="%s" stroke="%s" stroke-width="2"' % (col, edge)
    if b.get("children"):
        out.append('<rect x="%g" y="%g" width="%g" height="%g" rx="6" %s/>' % (x, y, ARM, height, style))
        out.append('<rect x="%g" y="%g" width="%g" height="%g" rx="6" %s/>' % (x, y + height - FOOT, width, FOOT, style))
    out.append('<rect x="%g" y="%g" width="%g" height="%g" rx="6" %s/>' % (x, y, max(head, width if b.get("children") else head), ROW, style))
    cx = x + PAD
    for p in _parts(b, lang):
        w = _part_width(p, lang)
        if "t" in p:
            out.append('<text x="%g" y="%g" font-size="17" font-weight="700" fill="#fff" font-family="Trebuchet MS, Verdana, sans-serif" textLength="%g" lengthAdjust="spacingAndGlyphs">%s</text>'
                       % (cx, y + 26, w, escape(_text(p["t"], lang))))
        elif "slot" in p:
            out.append('<rect x="%g" y="%g" width="%g" height="26" rx="13" fill="#fff"/>' % (cx, y + 7, w))
            out.append('<text x="%g" y="%g" font-size="17" text-anchor="middle" fill="%s" font-family="Trebuchet MS, Verdana, sans-serif" textLength="%g" lengthAdjust="spacingAndGlyphs">%s</text>'
                       % (cx + w / 2, y + 26, INK, w - 18, escape(_text(p["slot"], lang))))
        elif "drop" in p:
            out.append('<rect x="%g" y="%g" width="%g" height="26" rx="6" fill="%s"/>' % (cx, y + 7, w, _shade(col, 0.8)))
            out.append('<text x="%g" y="%g" font-size="17" font-weight="700" fill="#fff" font-family="Trebuchet MS, Verdana, sans-serif" textLength="%g" lengthAdjust="spacingAndGlyphs">%s</text>'
                       % (cx + 8, y + 26, w - 34, escape(_text(p["drop"], lang))))
            out.append('<path d="M%g %g l8 0 l-4 6 z" fill="#fff"/>' % (cx + w - 14, y + 17))
        else:
            out.append('<rect x="%g" y="%g" width="%g" height="30" rx="4" fill="%s"/>' % (cx, y + 5, w, _shade(col, 0.75)))
            rows = ICONS[p["icon"]]
            for r, line in enumerate(rows):
                for c, bit in enumerate(line):
                    out.append('<rect x="%g" y="%g" width="5" height="5" rx="1" fill="%s"/>'
                               % (cx + 7 + c * 8, y + 7 + r * 5 + r, "#fff" if bit == "1" else _shade(col, 1.25)))
        cx += w + GAP
    cy = y + ROW
    for k in b.get("children", []):
        frag, (_, kh) = _draw(k, lang, x + ARM, cy)
        out.append(frag)
        cy += kh
    return "".join(out), (width, height)


def render(spec, lang):
    """spec = list of top-level blocks, drawn one below the other."""
    parts, y, total_w = [], 2, 0
    for b in spec:
        frag, (w, h) = _draw(b, lang, 2, y)
        parts.append(frag)
        total_w = max(total_w, w)
        y += h + 14
    height = y - 14 + 2
    width = total_w + 4
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %g %g" width="%g" height="%g">%s</svg>\n'
            % (width, height, width, height, "".join(parts)))


# --- block specs (the Danish words are unverified: check them in Danish MakeCode)
def B(cat, *parts, children=None):
    d = {"cat": cat, "parts": list(parts)}
    if children:
        d["children"] = children
    return d


def T(en, da):
    return {"t": {"en": en, "da": da}}


SHOW_ICON = lambda name: B("basic", T("show icon", "vis ikon"), {"icon": name})
SHOW_STRING = lambda s: B("basic", T("show string", "vis streng"), {"slot": s})
SHOW_NUMBER = lambda n: B("basic", T("show number", "vis nummer"), {"slot": n})
PAUSE = lambda ms: B("basic", T("pause (ms)", "pause (ms)"), {"slot": ms})
CLEAR = B("basic", T("clear screen", "ryd skærmen"))
ON_START = lambda *kids: B("basic", T("on start", "når programmet starter"), children=list(kids))
ON_BUTTON = lambda btn, *kids: B("input", T("on button", "når der trykkes på knappen"), {"drop": btn}, T("pressed", ""), children=list(kids))

SPECS = {
    "show-number": [SHOW_NUMBER("0")],
    "show-string": [SHOW_STRING({"en": "Hello!", "da": "Hej!"})],
    "pause": [PAUSE("100")],
    "clear-screen": [CLEAR],
    "on-button": [ON_BUTTON("A")],
    "ex-hello": [ON_START(SHOW_STRING({"en": "Hello!", "da": "Hej!"}))],
    "ex-heart-gone": [ON_START(SHOW_ICON("heart"), PAUSE("2000"), CLEAR)],
    "ex-i-heart": [ON_START(SHOW_STRING({"en": "I", "da": "Jeg"}), SHOW_ICON("heart"), SHOW_STRING("micro:bit"))],
    "ex-buttons": [ON_BUTTON("A", SHOW_ICON("heart")), ON_BUTTON("B", SHOW_ICON("happy"))],
    "ex-yes-no": [ON_BUTTON("A", SHOW_STRING({"en": "yes", "da": "ja"})), ON_BUTTON("B", SHOW_STRING({"en": "no", "da": "nej"}))],
    "ex-clear": [ON_BUTTON("A+B", CLEAR)],
    "ex-show-icon": [ON_START(SHOW_ICON("heart"))],
}


def build():
    """Returns {filename: svg text}."""
    return {"%s.%s.svg" % (name, lang): render(spec, lang)
            for name, spec in SPECS.items() for lang in LANGS}


def main():
    files = build()
    os.makedirs(OUT, exist_ok=True)
    if "--check" in sys.argv:
        bad = [n for n, s in files.items()
               if not os.path.exists(os.path.join(OUT, n)) or open(os.path.join(OUT, n), encoding="utf-8").read() != s]
        if bad:
            print("Out of date, run python3 tools/blocks.py:", ", ".join(bad))
            sys.exit(1)
        print("Block pictures are up to date.")
        return
    for n, s in files.items():
        with open(os.path.join(OUT, n), "w", encoding="utf-8") as f:
            f.write(s)
    print("Wrote %d files to images/blocks/" % len(files))


if __name__ == "__main__":
    main()
