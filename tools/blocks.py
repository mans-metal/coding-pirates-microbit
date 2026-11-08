"""Draws simplified MakeCode block pictures as static SVG files.

Run:  python3 tools/blocks.py          (writes images/blocks/<id>.<lang>.svg)
      python3 tools/blocks.py --check  (fails if the files are out of date)

Colours of the first nine groups were sampled from a real MakeCode screenshot;
Pins and Game are approximate. The pictures are simplified, so check each block
against MakeCode before publishing. Danish words come from the DA table below
(a missing word shows the English one, so gaps are easy to see).
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
    "pins": "#A94400", "game": "#007A4D",
}
ICONS = {
    "heart": ["01010", "11111", "11111", "01110", "00100"],
    "happy": ["00000", "01010", "00000", "10001", "01110"],
    "sad": ["00000", "01010", "00000", "01110", "10001"],
    "yes": ["00000", "00001", "00010", "10100", "01000"],
    "no": ["10001", "01010", "00100", "01010", "10001"],
}

ROW, PAD, GAP, ARM, FOOT, CHAR = 40, 12, 8, 18, 22, 10.2
ELSE_ROW = 32
INK = "#1F2A44"
FONT = "Trebuchet MS, Verdana, sans-serif"

# Danish block words. Some come from MakeCode's Danish translation feed, others
# are guesses: check every one in the Danish editor (Settings > Language > Dansk).
DA = {
    "on start": "når programmet starter",
    "forever": "for altid",
    "on button": "når der trykkes på knappen",
    "pressed": "",
    "on shake": "på ryst",
    "button A is pressed": "der trykkes på knappen A",
    "show icon": "vis ikon",
    "show string": "vis streng",
    "show number": "vis nummer",
    "pause (ms)": "pause (ms)",
    "clear screen": "ryd skærmen",
    "temperature (°C)": "temperatur (°C)",
    "light level": "lysniveau",
    "digital write pin": "digital skriv pin",
    "digital read pin": "digital læs pin",
    "analog read pin": "analog læs pin",
    "servo write pin": "servo skriv pin",
    "set pull": "sæt pull pin",
    "play tone": "afspil tone",
    "for": "i",
    "if": "hvis",        # guess
    "then": "så",        # guess
    "else": "ellers",    # guess
    "true": "sand",
    "repeat": "gentag",
    "times": "gange",
    "set": "sæt",
    "to": "til",
    "change": "ændr",
    "by": "med",
    "pick random 0 to 10": "vælg tilfældig fra 0 til 10",
    "pick random 1 to 6": "vælg tilfældig fra 1 til 6",
    "pick random 0 to 1": "vælg tilfældig fra 0 til 1",
    "pick random 0 to 4": "vælg tilfældig fra 0 til 4",
    "show leds": "vis LED'er",
    "set built-in speaker": "indstil indbygget højttaler",
    "create sprite at": "skab sprite på",
    "move by": "flyt med",
    "turn": "drej",
    "degrees": "",
    "if on edge, bounce": "hvis på kanten, spring tilbage",
    "change score by": "ændr scoren med",
}


_NARROW = set("il'.,:;!|")
_SMALL = set("jtfrI()[]- 1")
_WIDE = set("mwMW")


def _tw(text, size=17):
    """Estimated width of bold text in pixels, letter by letter (a font may differ a little)."""
    total = 0.0
    for ch in text:
        if ch in _NARROW:
            total += 4.8
        elif ch in _SMALL:
            total += 6.6 if ch != " " else 5.2
        elif ch in _WIDE:
            total += 15
        elif ch == "°":
            total += 7
        elif ch.isupper():
            total += 11
        elif ch in "=<>+":
            total += 10
        else:
            total += 9.3
    return total * size / 17


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
        return _tw(_text(p["t"], lang))
    if "slot" in p:
        return max(34, _tw(_text(p["slot"], lang)) + 18)
    if "drop" in p:
        return _tw(_text(p["drop"], lang)) + 18 + 16
    if "val" in p or "bool" in p:
        return _tw(_text(p.get("val") or p["bool"], lang), 15) + 22
    return 54  # icon


def _header_width(b, lang):
    kind = b.get("kind", "stack")
    if kind in ("reporter", "boolean"):
        return _tw(_text(b["text"], lang)) + 28
    parts = _parts(b, lang)
    return PAD * 2 + sum(_part_width(p, lang) for p in parts) + GAP * (len(parts) - 1)


def _size(b, lang):
    kind = b.get("kind", "stack")
    head = _header_width(b, lang)
    if kind in ("reporter", "boolean"):
        return head, 34
    kids, ekids = b.get("children", []), b.get("else_children")
    if not kids and ekids is None and kind != "c":
        return head, ROW
    sizes = [_size(k, lang) for k in kids] + [_size(k, lang) for k in (ekids or [])]
    width = max([head] + ([ARM + max(w for w, _ in sizes)] if sizes else []))
    height = ROW + sum(h for _, h in sizes) + FOOT
    if ekids is not None:
        height += ELSE_ROW
    return width, height


def _label(x, y, text, extra=""):
    return ('<text x="%g" y="%g" font-size="17" font-weight="700" fill="#fff" font-family="%s"%s>%s</text>'
            % (x, y, FONT, extra, escape(text)))


def _fit(w):
    return ' textLength="%g" lengthAdjust="spacing"' % w


def _hex(x, y, w, h, style):
    d = 12
    pts = [(x, y + h / 2), (x + d, y), (x + w - d, y), (x + w, y + h / 2), (x + w - d, y + h), (x + d, y + h)]
    return '<polygon points="%s" %s/>' % (" ".join("%g,%g" % p for p in pts), style)


def _draw(b, lang, x, y):
    col = COLOURS[b["cat"]]
    edge = _shade(col, 0.8)
    style = 'fill="%s" stroke="%s" stroke-width="2"' % (col, edge)
    width, height = _size(b, lang)
    kind = b.get("kind", "stack")
    out = []
    if kind == "reporter":
        out.append('<rect x="%g" y="%g" width="%g" height="%g" rx="17" %s/>' % (x, y, width, height, style))
        out.append(_label(x + 14, y + 23, _text(b["text"], lang), _fit(_tw(_text(b["text"], lang)))))
        return "".join(out), (width, height)
    if kind == "boolean":
        out.append(_hex(x, y, width, height, style))
        out.append(_label(x + 16, y + 23, _text(b["text"], lang), _fit(_tw(_text(b["text"], lang)))))
        return "".join(out), (width, height)
    head = _header_width(b, lang)
    kids, ekids = b.get("children", []), b.get("else_children")
    is_c = bool(kids) or ekids is not None or kind == "c"
    if is_c:
        out.append('<rect x="%g" y="%g" width="%g" height="%g" rx="6" %s/>' % (x, y, ARM, height, style))
        out.append('<rect x="%g" y="%g" width="%g" height="%g" rx="6" %s/>' % (x, y + height - FOOT, width, FOOT, style))
    out.append('<rect x="%g" y="%g" width="%g" height="%g" rx="6" %s/>' % (x, y, max(head, width) if is_c else head, ROW, style))
    cx = x + PAD
    for p in _parts(b, lang):
        w = _part_width(p, lang)
        if "t" in p:
            out.append(_label(cx, y + 26, _text(p["t"], lang), _fit(w)))
        elif "slot" in p:
            out.append('<rect x="%g" y="%g" width="%g" height="26" rx="13" fill="#fff"/>' % (cx, y + 7, w))
            out.append('<text x="%g" y="%g" font-size="17" text-anchor="middle" fill="%s" font-family="%s"%s>%s</text>'
                       % (cx + w / 2, y + 26, INK, FONT, _fit(_tw(_text(p["slot"], lang))), escape(_text(p["slot"], lang))))
        elif "drop" in p:
            out.append('<rect x="%g" y="%g" width="%g" height="26" rx="6" fill="%s"/>' % (cx, y + 7, w, _shade(col, 0.8)))
            out.append(_label(cx + 8, y + 26, _text(p["drop"], lang), _fit(_tw(_text(p["drop"], lang)))))
            out.append('<path d="M%g %g l8 0 l-4 6 z" fill="#fff"/>' % (cx + w - 14, y + 17))
        elif "val" in p or "bool" in p:
            pc = COLOURS[p["cat"]]
            style_p = 'fill="%s" stroke="%s" stroke-width="2"' % (pc, _shade(pc, 0.8))
            t = _text(p.get("val") or p["bool"], lang)
            if "val" in p:
                out.append('<rect x="%g" y="%g" width="%g" height="28" rx="14" %s/>' % (cx, y + 6, w, style_p))
            else:
                out.append(_hex(cx, y + 6, w, 28, style_p))
            out.append('<text x="%g" y="%g" font-size="15" font-weight="700" fill="#fff" font-family="%s"%s>%s</text>'
                       % (cx + 11, y + 25, FONT, _fit(_tw(t, 15)), escape(t)))
        else:
            out.append('<rect x="%g" y="%g" width="%g" height="30" rx="4" fill="%s"/>' % (cx, y + 5, w, _shade(col, 0.75)))
            for r, line in enumerate(ICONS[p["icon"]]):
                for c, bit in enumerate(line):
                    out.append('<rect x="%g" y="%g" width="5" height="5" rx="1" fill="%s"/>'
                               % (cx + 7 + c * 8, y + 7 + r * 5 + r, "#fff" if bit == "1" else _shade(col, 1.25)))
        cx += w + GAP
    cy = y + ROW
    for k in kids:
        frag, (_, kh) = _draw(k, lang, x + ARM, cy)
        out.append(frag)
        cy += kh
    if ekids is not None:
        out.append('<rect x="%g" y="%g" width="%g" height="%g" rx="6" %s/>' % (x, cy, width, ELSE_ROW, style))
        word = DA.get("else", "ellers") if lang == "da" else "else"
        out.append(_label(x + PAD, cy + 22, word, _fit(_tw(word))))
        cy += ELSE_ROW
        for k in ekids:
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


# ---- helpers for writing block specs
def T(en, da=None):
    """A label with its Danish wording from the DA table (English if missing)."""
    return {"t": {"en": en, "da": DA.get(en, en) if da is None else da}}


def W(en):
    """Plain bilingual text for slots and reporters."""
    return {"en": en, "da": DA.get(en, en)}


def B(cat, *parts, children=None, else_children=None, kind=None):
    d = {"cat": cat, "parts": list(parts)}
    if children:
        d["children"] = children
    if else_children is not None:
        d["else_children"] = else_children
    if kind:
        d["kind"] = kind
    return d


def R(cat, en, da=None, kind="reporter"):
    """A stand-alone reporter or condition block. `en` may be a ready bilingual text."""
    if isinstance(en, dict):
        return {"cat": cat, "kind": kind, "text": en}
    return {"cat": cat, "kind": kind, "text": {"en": en, "da": DA.get(en, en) if da is None else da}}


def val(cat, text):
    return {"val": W(text) if isinstance(text, str) else text, "cat": cat}


def cond(cat, text):
    return {"bool": W(text) if isinstance(text, str) else text, "cat": cat}


MIDDLE_C = {"en": "Middle C", "da": "Middel C"}


def J(en_label, rest=""):
    """Bilingual text: a label from the DA table followed by a language-neutral part."""
    return {"en": en_label + rest, "da": DA.get(en_label, en_label) + rest}


def arg(a):
    """A number or text becomes a white slot; a part (dict) is used as it is."""
    if isinstance(a, dict) and "en" not in a:
        return a
    return {"slot": a if isinstance(a, dict) else str(a)}


# ---- statement blocks
def ON_START(*k): return B("basic", T("on start"), children=list(k), kind="c")
def FOREVER(*k): return B("basic", T("forever"), children=list(k), kind="c")
def ON_BUTTON(btn, *k): return B("input", T("on button"), {"drop": btn}, T("pressed"), children=list(k), kind="c")
def ON_SHAKE(*k): return B("input", T("on shake"), children=list(k), kind="c")
def PAUSE(ms): return B("basic", T("pause (ms)"), arg(ms))
def SHOW_ICON(n): return B("basic", T("show icon"), {"icon": n})
def SHOW_STRING(s): return B("basic", T("show string"), arg(s))
def SHOW_NUMBER(n): return B("basic", T("show number"), arg(n))
CLEAR = B("basic", T("clear screen"))
def WRITE(pin, v): return B("pins", T("digital write pin"), {"drop": pin}, T("to"), arg(v))
def SERVO(pin, deg): return B("pins", T("servo write pin"), {"drop": pin}, T("to"), arg(deg))
def PULL(pin, d): return B("pins", T("set pull"), {"drop": pin}, T("to"), {"drop": d})
def PLAY_TONE(note, beat): return B("music", T("play tone"), {"drop": MIDDLE_C if note == "Middle C" else note}, T("for"), {"drop": beat})
def REST(beat): return B("music", T("rest for"), {"drop": beat})
def SET_VAR(name, v): return B("variables", T("set"), {"drop": name}, T("to"), arg(v))
def CHANGE_VAR(name, n): return B("variables", T("change"), {"drop": name}, T("by", "af"), arg(n))
def IF(c, *k): return B("logic", T("if"), c, T("then"), children=list(k), kind="c")
def IF_ELSE(c, k1, k2): return B("logic", T("if"), c, T("then"), children=k1, else_children=k2)
def REPEAT(n, *k): return B("loops", T("repeat"), arg(n), T("times"), children=list(k), kind="c")
SET_FOOD = B("variables", T("set"), {"drop": "food"}, T("to"), val("game", J("create sprite at", " x: 0 y: 0")))
SET_FOOD_X = B("game", {"drop": "food"}, T("set", "angiv"), {"drop": "x"}, T("to"), val("math", "pick random 0 to 4"))
SET_SPRITE = B("variables", T("set"), {"drop": "sprite"}, T("to"), val("game", J("create sprite at", " x: 2 y: 2")))
def SPRITE_MOVE(n): return B("game", {"drop": "sprite"}, T("move by"), arg(n))
def SPRITE_TURN(d, deg): return B("game", {"drop": "sprite"}, T("turn"), {"drop": {"en": d, "da": "højre" if d == "right" else d}}, T("by"), arg(deg), T("degrees"))
SPRITE_BOUNCE = B("game", {"drop": "sprite"}, T("if on edge, bounce"))
def SPRITE_CHANGE(axis, n): return B("game", {"drop": "sprite"}, T("change"), {"drop": axis}, T("by"), arg(n))
def CHANGE_SCORE(n): return B("game", T("change score by"), arg(n))
GAME_OVER = B("game", T("game over"))
SPRITE_DELETE = B("game", {"drop": "sprite"}, T("delete"))


SPECS = {
    # basic
    "on-start": [ON_START()],
    "forever": [FOREVER()],
    "show-icon": [SHOW_ICON("heart")],
    "show-string": [SHOW_STRING({"en": "Hello!", "da": "Hej!"})],
    "show-number": [SHOW_NUMBER("0")],
    "show-leds": [B("basic", T("show leds"), {"icon": "heart"})],
    "pause": [PAUSE("100")],
    "clear-screen": [CLEAR],
    # input
    "on-button": [ON_BUTTON("A")],
    "button-pressed": [R("input", "button A is pressed", kind="boolean")],
    "on-shake": [ON_SHAKE()],
    "acceleration": [R("input", "acceleration (mg) x")],
    "temperature": [R("input", "temperature (°C)")],
    "light-level": [R("input", "light level")],
    # pins
    "digital-write": [WRITE("P0", 1)],
    "digital-read": [R("pins", J("digital read pin", " P0"))],
    "analog-read": [R("pins", J("analog read pin", " P1"))],
    "servo-write": [SERVO("P1", 90)],
    "set-pull": [PULL("P0", {"en": "up", "da": "op"})],
    # music
    "play-tone": [PLAY_TONE("Middle C", "1 beat")],
    "rest": [REST("1 beat")],
    "speaker": [B("music", T("set built-in speaker"), {"drop": "on"})],
    # logic, loops, variables, math
    "if-then": [B("logic", T("if"), {"bool": W("true"), "cat": "logic"}, T("then"), kind="c")],
    "if-else": [IF_ELSE({"bool": W("true"), "cat": "logic"}, [], [])],
    "compare": [R("logic", "0 = 0", kind="boolean")],
    "repeat": [REPEAT(4)],
    "set-variable": [SET_VAR("score", 0)],
    "change-variable": [CHANGE_VAR("score", 1)],
    "variable": [R("variables", "score")],
    "pick-random": [R("math", "pick random 0 to 10")],
    # game
    "create-sprite": [SET_SPRITE],
    "sprite-move": [SPRITE_MOVE(1)],
    "sprite-turn": [SPRITE_TURN("right", 90)],
    "sprite-bounce": [SPRITE_BOUNCE],
    "sprite-change": [SPRITE_CHANGE("x", 1)],
    "sprite-touching": [R("game", "sprite is touching food", kind="boolean")],
    "change-score": [CHANGE_SCORE(1)],
    "score": [R("game", "score")],
    "game-over": [GAME_OVER],
    "sprite-delete": [SPRITE_DELETE],
    # examples used in the lessons
    "ex-show-icon": [ON_START(SHOW_ICON("heart"))],
    "ex-hello": [ON_START(SHOW_STRING({"en": "Hello!", "da": "Hej!"}))],
    "ex-heart-gone": [ON_START(SHOW_ICON("heart"), PAUSE(2000), CLEAR)],
    "ex-i-heart": [ON_START(SHOW_STRING({"en": "I", "da": "Jeg"}), SHOW_ICON("heart"), SHOW_STRING("micro:bit"))],
    "ex-buttons": [ON_BUTTON("A", SHOW_ICON("heart")), ON_BUTTON("B", SHOW_ICON("happy"))],
    "ex-yes-no": [ON_BUTTON("A", SHOW_STRING({"en": "yes", "da": "ja"})), ON_BUTTON("B", SHOW_STRING({"en": "no", "da": "nej"}))],
    "ex-clear": [ON_BUTTON("A+B", CLEAR)],
    "ex-led-on": [ON_START(WRITE("P0", 1))],
    "ex-led-blink": [FOREVER(WRITE("P0", 1), PAUSE(500), WRITE("P0", 0), PAUSE(500))],
    "ex-led-buttons": [ON_BUTTON("A", WRITE("P0", 1)), ON_BUTTON("B", WRITE("P0", 0))],
    "ex-counter": [ON_START(SET_VAR("score", 0)),
                   ON_BUTTON("A", CHANGE_VAR("score", 1), SHOW_NUMBER(val("variables", "score")))],
    "ex-reset": [ON_BUTTON("B", SET_VAR("score", 0), SHOW_NUMBER(val("variables", "score")))],
    "ex-dice": [ON_BUTTON("A", SET_VAR("dice", val("math", "pick random 1 to 6")), SHOW_NUMBER(val("variables", "dice")))],
    "ex-if-button": [FOREVER(IF_ELSE(cond("input", "button A is pressed"), [SHOW_ICON("heart")], [CLEAR]))],
    "ex-if-score": [ON_BUTTON("A", CHANGE_VAR("score", 1),
                              IF_ELSE(cond("logic", "score > 4"), [SHOW_ICON("happy")], [SHOW_ICON("sad")]))],
    "ex-magic-ball": [ON_SHAKE(SET_VAR("answer", val("math", "pick random 0 to 1")),
                               IF_ELSE(cond("logic", "answer = 0"), [SHOW_ICON("yes")], [SHOW_ICON("no")]))],
    "ex-show-value": [FOREVER(SHOW_NUMBER(val("pins", J("digital read pin", " P0"))))],
    "ex-pir": [FOREVER(IF_ELSE(cond("logic", J("digital read pin", " P0 = 1")), [SHOW_ICON("yes")], [CLEAR]))],
    "ex-pot": [FOREVER(SHOW_NUMBER(val("pins", J("analog read pin", " P1"))))],
    "ex-tilt": [FOREVER(SHOW_NUMBER(val("input", J("acceleration (mg)", " x"))))],
    "ex-tone": [ON_BUTTON("A", PLAY_TONE("Middle C", "1 beat"))],
    "ex-melody": [ON_BUTTON("A", PLAY_TONE("Middle C", "1 beat"), PLAY_TONE("D", "1 beat"), PLAY_TONE("E", "1 beat"))],
    "ex-servo": [ON_BUTTON("A", SERVO("P1", 0)), ON_BUTTON("B", SERVO("P1", 180))],
    "ex-sprite-move": [ON_START(SET_SPRITE), ON_BUTTON("A", SPRITE_CHANGE("x", -1)), ON_BUTTON("B", SPRITE_CHANGE("x", 1))],
    "ex-sprite-bounce": [ON_START(SET_SPRITE), FOREVER(SPRITE_MOVE(1), SPRITE_BOUNCE, PAUSE(500))],
    "ex-sprite-catch": [ON_START(SET_SPRITE, SET_FOOD),
                        FOREVER(IF(cond("game", "sprite is touching food"), CHANGE_SCORE(1), SET_FOOD_X))],
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
        extra = [n for n in os.listdir(OUT) if n.endswith(".svg") and n not in files]
        if bad or extra:
            print("Out of date, run python3 tools/blocks.py:", ", ".join(bad + extra))
            sys.exit(1)
        print("Block pictures are up to date.")
        return
    for n, s in files.items():
        with open(os.path.join(OUT, n), "w", encoding="utf-8") as f:
            f.write(s)
    for n in os.listdir(OUT):
        if n.endswith(".svg") and n not in files:
            os.remove(os.path.join(OUT, n))
    print("Wrote %d files to images/blocks/" % len(files))


if __name__ == "__main__":
    main()
