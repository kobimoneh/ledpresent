"""Serial command server for the 6-block display -- runs ON THE BOARD.

The PC side is ledctl.py. It interrupts whatever is running (e.g. the light
show from main.py), starts this with `import ledserver; ledserver.run()`, and
then sends one command per line. Every reply is a line starting "ok" or "err".

Install once (font6x6, text6x6 and show must be on the board too):
    python -m mpremote c3 fs cp ledserver.py :ledserver.py

Colours are a palette name (text6x6.PALETTE), "r,g,b" or "#rrggbb", all at
full 0-255 scale; they are scaled down to `level` before reaching the LEDs.

    ping                    -> ok <W> <H> <level>
    clear
    fill <colour>
    px <x> <y> <colour>     canvas coords: x 0..35 left to right, y 0..5 top down
    rect <x> <y> <w> <h> <colour>
    block <n> <colour>      n = 0..5, left to right
    text <colour> <msg>     static, up to 6 chars, one per block
    scroll <colour|rainbow> <speed_ms> <msg>    scrolls once, replies when done
    rainbow <seconds>
    squares <times>
    scene <name> [seconds]  any show.SCENES entry: comet, fire, plasma, ...
    frame <hex>             W*H*3 bytes, rows top->bottom, x left->right, RGB
    level <0-255>           brightness ceiling (default text6x6.LEVEL)

Ctrl-C ends the server and returns to the REPL; the pixels keep their state.
"""

import sys
import binascii

import font6x6
import text6x6
import show

W, H = show.W, show.H
level = text6x6.LEVEL
canvas = None


def colour(tok):
    if tok in text6x6.PALETTE:
        c = text6x6.PALETTE[tok]
    elif tok.startswith("#") and len(tok) == 7:
        c = tuple(binascii.unhexlify(tok[1:]))
    else:
        c = tuple(int(v) for v in tok.split(","))
        if len(c) != 3:
            raise ValueError("colour: name, r,g,b or #rrggbb")
    return text6x6.dim(tuple(max(0, min(255, v)) for v in c), level)


def put_text(text, col):
    text = (text[:6] + "      ")[:6]
    canvas.clear()
    for b, ch in enumerate(text):
        for y, row in enumerate(font6x6.get(ch)):
            for x, cell in enumerate(row):
                if cell != ".":
                    canvas.set(b * 6 + x, y, col)


def scroll_one(text, col, speed_ms):
    rows = show.bitmap(text)
    total = len(rows[0])
    for offset in range(-W, total + 1):
        canvas.clear()
        for x in range(W):
            src = offset + x
            if 0 <= src < total:
                for y in range(H):
                    if rows[y][src] != ".":
                        canvas.set(x, y, col)
        canvas.show()
        show.time.sleep_ms(speed_ms)


def handle(line):
    global level
    p = line.split(None, 1)
    cmd, rest = p[0], (p[1] if len(p) > 1 else "")
    a = rest.split()

    if cmd == "ping":
        return "ok %d %d %d" % (W, H, level)
    if cmd == "level":
        level = max(0, min(255, int(a[0])))
        return "ok %d" % level
    if cmd == "clear":
        canvas.clear()
    elif cmd == "fill":
        c = colour(a[0])
        for y in range(H):
            for x in range(W):
                canvas.set(x, y, c)
    elif cmd == "px":
        canvas.set(int(a[0]), int(a[1]), colour(a[2]))
    elif cmd == "rect":
        x0, y0, w, h = (int(v) for v in a[:4])
        c = colour(a[4])
        for y in range(max(0, y0), min(H, y0 + h)):
            for x in range(max(0, x0), min(W, x0 + w)):
                canvas.set(x, y, c)
    elif cmd == "block":
        n = int(a[0])
        if not 0 <= n < 6:
            raise ValueError("block 0..5")
        c = colour(a[1])
        for y in range(H):
            for x in range(6):
                canvas.set(n * 6 + x, y, c)
    elif cmd == "text":
        c, msg = rest.split(" ", 1) if " " in rest else (rest, "")
        put_text(msg, colour(c))
    elif cmd == "scroll":
        c, spd, msg = rest.split(" ", 2)
        if c == "rainbow":
            show.scroll(canvas, msg, int(spd))
        else:
            scroll_one(msg, colour(c), int(spd))
        return "ok"
    elif cmd == "rainbow":
        show.rainbow_diagonal(canvas, float(a[0]) if a else 2.0)
        return "ok"
    elif cmd == "squares":
        show.squares_zoom(canvas, int(a[0]) if a else 3)
        return "ok"
    elif cmd == "scene":
        if a[0] not in show.SCENES:
            raise ValueError("scenes: " + " ".join(sorted(show.SCENES)))
        show.SCENES[a[0]](canvas, float(a[1]) if len(a) > 1 else 5.0)
        return "ok"
    elif cmd == "frame":
        d = binascii.unhexlify(a[0])
        if len(d) != W * H * 3:
            raise ValueError("frame needs %d bytes, got %d" % (W * H * 3, len(d)))
        i = 0
        for y in range(H):
            for x in range(W):
                canvas.set(x, y, text6x6.dim((d[i], d[i + 1], d[i + 2]), level))
                i += 3
    else:
        raise ValueError("unknown command %r" % cmd)
    canvas.show()
    return "ok"


def run():
    global canvas
    if canvas is None:
        canvas = show.Canvas()
    sys.stdout.write("ledserver ready\n")
    while True:
        try:
            line = sys.stdin.readline().strip()
        except KeyboardInterrupt:
            return
        if not line:
            continue
        try:
            r = handle(line)
        except KeyboardInterrupt:
            return
        except Exception as e:
            r = "err %s" % e
        sys.stdout.write(r + "\n")
