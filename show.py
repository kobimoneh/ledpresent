"""Looping light show for the 6-block WS2812b display.

Scenes (run() strings them together with scrolling text, repeating forever):
  rainbow_diagonal  diagonal rainbow bands sweeping across
  squares_zoom      squares zooming inward on every block, one colour each
  comet             a column bouncing end to end, leaving a rainbow tail
  sparkle           random pixels flashing up in random colours and fading
  fire              flames rising from the bottom edge
  rain              green "digital rain" drops falling with fading trails
  plasma            smooth, swirling colour field
  ripple            rings spreading out from random points

STOPPING IT
  Press Ctrl-C. The display is cleared on the way out, so it will not be
  left with pixels stuck on.

  If it was started as main.py (running at power-up), Ctrl-C still works
  from `mpremote c3 repl`, because mpremote interrupts on connect.
  To stop it starting at all: `mpremote c3 fs rm :main.py`
"""

import math
import random
import time

import machine
import neopixel

import font6x6
import text6x6

W = 36          # six blocks side by side
H = 6
FRAME_MS = 40   # target frame period; a full redraw alone costs ~25 ms


def pace(started, period_ms=FRAME_MS):
    """Sleep only the remainder of a frame, so render time is not additive."""
    remaining = period_ms - time.ticks_diff(time.ticks_ms(), started)
    if remaining > 0:
        time.sleep_ms(remaining)


def frames(canvas, seconds, period_ms=FRAME_MS):
    """Yield frame numbers for `seconds`; shows and paces after each frame."""
    deadline = time.ticks_add(time.ticks_ms(), int(seconds * 1000))
    n = 0
    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        started = time.ticks_ms()
        yield n
        canvas.show()
        pace(started, period_ms)
        n += 1


# --- the display as one 36x6 canvas ---------------------------------------
class Canvas:
    """Treats the six blocks as a single 36x6 pixel grid, x=0 at the left.

    Block ordering and within-block pixel mapping both come from text6x6, so
    this stays correct if the wiring flags there ever change.
    """

    def __init__(self):
        # text6x6.PINS is right-to-left; reverse for a left-to-right canvas.
        self.strips = [neopixel.NeoPixel(machine.Pin(p), text6x6.W * text6x6.H)
                       for p in reversed(text6x6.PINS)]
        # Precompute (strip, pixel) for every canvas coordinate. Doing this
        # once keeps the per-frame work to plain list indexing.
        self.lut = []
        for y in range(H):
            for x in range(W):
                self.lut.append((self.strips[x // text6x6.W],
                                 text6x6.index(x % text6x6.W, y)))

    def set(self, x, y, colour):
        strip, pix = self.lut[y * W + x]
        strip[pix] = colour

    def clear(self):
        for strip in self.strips:
            strip.fill((0, 0, 0))

    def show(self):
        for strip in self.strips:
            strip.write()


# --- colour ---------------------------------------------------------------
WHEEL_N = 64


def _wheel(pos):
    """Position 0-255 around the colour wheel, at full scale."""
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)


# Pre-dimmed wheel, so no scaling happens inside the animation loops.
WHEEL = [text6x6.dim(_wheel(i * 256 // WHEEL_N)) for i in range(WHEEL_N)]
# Full-scale wheel, for scenes that fade colours through scale().
WHEEL_FULL = [_wheel(i * 256 // WHEEL_N) for i in range(WHEEL_N)]


def scale(colour, b):
    """Full-scale colour at brightness b (0-255), dimmed to LEVEL in one go."""
    k = b * text6x6.LEVEL
    return (colour[0] * k // 65025, colour[1] * k // 65025,
            colour[2] * k // 65025)

BLOCK_COLOURS = ("red", "orange", "yellow", "green", "azure", "violet")


# --- text bitmaps ---------------------------------------------------------
def bitmap(text):
    """Render text into H rows of glyph columns, for scrolling."""
    rows = []
    for y in range(H):
        row = ""
        for ch in text:
            row += font6x6.get(ch)[y]
        rows.append(row)
    return rows


# --- scenes ---------------------------------------------------------------
def rainbow_diagonal(canvas, seconds=2.0):
    """Hue as a function of (x + y), animated: bands sweep diagonally."""
    deadline = time.ticks_add(time.ticks_ms(), int(seconds * 1000))
    step = 0
    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        frame = time.ticks_ms()
        for y in range(H):
            for x in range(W):
                canvas.set(x, y, WHEEL[(x + y * 3 + step) % WHEEL_N])
        canvas.show()
        step += 2
        pace(frame)


def scroll(canvas, text, speed_ms=45, blink_ms=None):
    """Scroll text right-to-left once.

    Plain: colour flows along the length of the text.
    With blink_ms=(on, off): the text flashes while it scrolls, taking one
    colour per flash. Scrolling keeps advancing through the dark phases, so
    the message still travels at a steady pace.
    """
    rows = bitmap(text)
    total = len(rows[0])
    if blink_ms:
        on_frames = max(1, blink_ms[0] // speed_ms)
        period = on_frames + max(1, blink_ms[1] // speed_ms)
    step = 0
    # Start off the right edge, finish once the tail clears the left edge.
    for offset in range(-W, total + 1):
        frame = time.ticks_ms()
        canvas.clear()

        flash = None
        if blink_ms:
            if step % period >= on_frames:
                # Dark phase: show nothing, but the offset still advanced.
                canvas.show()
                step += 1
                pace(frame, speed_ms)
                continue
            flash = text6x6.hue(
                BLOCK_COLOURS[(step // period) % len(BLOCK_COLOURS)])

        for x in range(W):
            src = offset + x
            if 0 <= src < total:
                colour = flash if flash else WHEEL[(src + step) % WHEEL_N]
                for y in range(H):
                    if rows[y][src] != ".":
                        canvas.set(x, y, colour)
        canvas.show()
        step += 1
        pace(frame, speed_ms)


def squares_zoom(canvas, times=3, hold_ms=190):
    """Concentric square rings shrinking inward, one colour per block."""
    for cycle in range(times):
        for inset in range(text6x6.W // 2):          # 0 = outer edge, 2 = core
            canvas.clear()
            for block in range(len(canvas.strips)):
                name = BLOCK_COLOURS[(block + cycle) % len(BLOCK_COLOURS)]
                colour = text6x6.hue(name)
                for ly in range(text6x6.H):
                    for lx in range(text6x6.W):
                        edge = min(lx, ly,
                                   text6x6.W - 1 - lx, text6x6.H - 1 - ly)
                        if edge == inset:
                            canvas.set(block * text6x6.W + lx, ly, colour)
            canvas.show()
            time.sleep_ms(hold_ms)


def comet(canvas, seconds=4.0):
    """A full-height column bouncing end to end, leaving a fading tail.

    Each column remembers the hue it was lit with, so the tail is a rainbow.
    """
    glow = [0] * W
    hues = [0] * W
    pos, step = 0, 1
    for n in frames(canvas, seconds, 30):
        glow[pos] = 255
        hues[pos] = n % WHEEL_N
        for x in range(W):
            b = glow[x]
            colour = scale(WHEEL_FULL[hues[x]], b)
            for y in range(H):
                canvas.set(x, y, colour)
            glow[x] = b * 3 // 4
        pos += step
        if pos == 0 or pos == W - 1:
            step = -step


def sparkle(canvas, seconds=4.0, rate=3):
    """Random pixels flash up in random colours and fade out."""
    glow = bytearray(W * H)
    hues = bytearray(W * H)
    for _ in frames(canvas, seconds):
        for _ in range(rate):
            i = random.randrange(W * H)
            glow[i] = 255
            hues[i] = random.getrandbits(6) % WHEEL_N
        canvas.clear()
        i = 0
        for y in range(H):
            for x in range(W):
                b = glow[i]
                if b:
                    canvas.set(x, y, scale(WHEEL_FULL[hues[i]], b))
                    glow[i] = b * 4 // 5
                i += 1


def _heat(h):
    """Heat 0-255 to a full-scale flame colour: black, red, orange, yellow."""
    if h < 96:
        return (h * 255 // 96, 0, 0)
    if h < 192:
        return (255, (h - 96) * 200 // 96, 0)
    return (255, 200 + (h - 192) * 55 // 64, (h - 192) * 2)


FIRE = [text6x6.dim(_heat(i * 8)) for i in range(32)]


def fire(canvas, seconds=5.0):
    """Flames: the bottom row is fed random heat, which rises and cools."""
    heat = [bytearray(W) for _ in range(H)]
    for _ in frames(canvas, seconds, 50):
        base = heat[H - 1]
        for x in range(W):
            base[x] = 128 + random.getrandbits(7)
        # Each cell takes a blur of the three cells below it, minus cooling.
        for y in range(H - 1):
            row, below = heat[y], heat[y + 1]
            for x in range(W):
                s = (below[x - 1 if x else 0] + below[x] * 2 +
                     below[x + 1 if x < W - 1 else x])
                v = s // 4 - random.getrandbits(6)
                row[x] = v if v > 0 else 0
        for y in range(H):
            row = heat[y]
            for x in range(W):
                canvas.set(x, y, FIRE[row[x] >> 3])


RAIN_HEAD = (150, 255, 150)
RAIN_TAIL = (0, 255, 40)


def rain(canvas, seconds=5.0):
    """Green drops falling at different speeds, trails fading behind them."""
    glow = bytearray(W * H)
    drops = []                  # [x, y in quarter pixels, speed]
    for _ in frames(canvas, seconds):
        if random.getrandbits(1):
            drops.append([random.randrange(W), 0, 1 + random.getrandbits(1)])
        for i in range(W * H):
            glow[i] = glow[i] * 2 // 3
        alive = []
        for d in drops:
            y = d[1] >> 2
            if y < H:
                glow[y * W + d[0]] = 255
                d[1] += d[2]
                alive.append(d)
        drops = alive
        canvas.clear()
        i = 0
        for y in range(H):
            for x in range(W):
                b = glow[i]
                if b == 255:
                    canvas.set(x, y, scale(RAIN_HEAD, 255))
                elif b:
                    canvas.set(x, y, scale(RAIN_TAIL, b))
                i += 1


SIN = bytes(int(32 + 31 * math.sin(i * 2 * math.pi / 64)) for i in range(64))


def plasma(canvas, seconds=5.0):
    """Three drifting sine waves summed into a hue: a slow, liquid swirl."""
    for t in frames(canvas, seconds):
        xs = [SIN[(x * 4 + t) & 63] for x in range(W)]
        for y in range(H):
            ys = SIN[(y * 8 + t * 3) & 63]
            for x in range(W):
                v = xs[x] + ys + SIN[((x + y) * 3 - t * 2) & 63]
                canvas.set(x, y, WHEEL[(v // 2 + t) % WHEEL_N])


# Distance in quarter pixels for every (|dx|, |dy|) on the canvas.
DIST4 = [[int(4 * math.sqrt(dx * dx + dy * dy)) for dy in range(H)]
         for dx in range(W)]


def ripple(canvas, seconds=5.0, every=18):
    """Rings spreading out from random points, each a new colour, fading."""
    rings = []                  # [cx, cy, radius in quarter pixels, hue]
    for n in frames(canvas, seconds):
        if n % every == 0:
            rings.append([random.randrange(W), random.randrange(H), 0,
                          random.getrandbits(6) % WHEEL_N])
        canvas.clear()
        for ring in rings:      # oldest first, so newer rings draw on top
            cx, cy, r, hue = ring
            fade = 255 - r * 3
            colour = WHEEL_FULL[hue]
            for y in range(H):
                dy = abs(y - cy)
                for x in range(W):
                    k = abs(DIST4[abs(x - cx)][dy] - r)
                    if k < 6:
                        canvas.set(x, y, scale(colour, fade * (6 - k) // 6))
            ring[2] = r + 2
        rings = [r for r in rings if r[2] < 85]


SCENES = {
    "rainbow": rainbow_diagonal,
    "comet": comet,
    "sparkle": sparkle,
    "fire": fire,
    "rain": rain,
    "plasma": plasma,
    "ripple": ripple,
}


# --- main loop ------------------------------------------------------------
def run():
    canvas = Canvas()
    try:
        while True:
            rainbow_diagonal(canvas, 2.0)
            scroll(canvas, "Reality", blink_ms=(180, 90))
            fire(canvas, 5)
            sparkle(canvas, 5)
            comet(canvas, 5)
            rain(canvas, 5)
            plasma(canvas, 5)
            ripple(canvas, 5)
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        # Always leave the matrix dark, however we exited.
        canvas.clear()
        canvas.show()


if __name__ == "__main__":
    print("running light show -- press Ctrl-C to stop")
    run()
