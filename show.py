"""Looping light show for the 6-block WS2812b display.

Scenes, in order, repeating forever:
  1. diagonal rainbow sweep, 2 s
  2. "Good luck Eden!" scrolling, colour flowing along the text
  3. squares zooming inward on every block, each a different colour, 3 times
  4. "Chiquititas rule!" scrolling while it blinks

STOPPING IT
  Press Ctrl-C. The display is cleared on the way out, so it will not be
  left with pixels stuck on.

  If it was started as main.py (running at power-up), Ctrl-C still works
  from `mpremote c3 repl`, because mpremote interrupts on connect.
  To stop it starting at all: `mpremote c3 fs rm :main.py`
"""

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


# --- main loop ------------------------------------------------------------
def run():
    canvas = Canvas()
    try:
        while True:
            rainbow_diagonal(canvas, 2.0)
            scroll(canvas, "Well done Eden!")
            squares_zoom(canvas, 3)
            scroll(canvas, "Chiquititas rule!", blink_ms=(180, 90))
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        # Always leave the matrix dark, however we exited.
        canvas.clear()
        canvas.show()


if __name__ == "__main__":
    print("running light show -- press Ctrl-C to stop")
    run()
