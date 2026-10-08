"""6x6 glyph rendering across six WS2812b blocks on an RP2350.

Physical arrangement: the six blocks sit side by side, ordered RIGHT TO LEFT,
so PINS[0] is the rightmost block and PINS[-1] the leftmost. One 6x6 glyph
fits one block, giving a six-character display.

Within a block, pixel 0 is in the top right corner and rows run right to
left. The flags below express that, and cover the other common wirings.
"""

import machine
import neopixel

import font6x6

PINS = [10, 9, 7, 6, 2, 1]      # block 1..6, right to left
W = font6x6.WIDTH
H = font6x6.HEIGHT
LEVEL = 10                      # per-channel; keeps 6 blocks near ~0.5 A

# --- within-block mapping -------------------------------------------------
# Confirmed on this hardware: pixel 0 sits in the TOP RIGHT of each block and
# rows run right to left, progressive (not serpentine).
SERPENTINE = False   # True if every other row runs in reverse
FLIP_V = False       # True if pixel 0 is at the bottom, not the top
FLIP_H = True        # pixel 0 is top RIGHT, so rows run right to left

def index(x, y):
    """Map a block-local (x, y) to a strip index."""
    if FLIP_V:
        y = H - 1 - y
    if FLIP_H:
        x = W - 1 - x
    if SERPENTINE and y % 2:
        x = W - 1 - x
    return y * W + x


def draw(text, colour, quiet=False):
    """Render up to 6 characters, left to right, across the blocks.

    Any character in font6x6 works -- letters (either case), digits and
    punctuation. Unknown characters render as a hollow box. Text shorter than
    6 is padded with blanks, so leftover blocks go dark rather than stale.
    """
    if len(text) > len(PINS):
        print("    note: '%s' truncated to %d chars" % (text, len(PINS)))
    text = text[:len(PINS)]
    text += " " * (len(PINS) - len(text))   # MicroPython str has no ljust()

    missing = font6x6.unsupported(text)
    if missing:
        print("    note: no glyph for %r -- showing a box" % missing)

    # PINS is right-to-left, so reverse it to walk the display left-to-right.
    left_to_right = list(reversed(PINS))

    lit = 0
    for ch, pin in zip(text, left_to_right):
        glyph = font6x6.get(ch)
        strip = neopixel.NeoPixel(machine.Pin(pin), W * H)
        strip.fill((0, 0, 0))
        for y, row in enumerate(glyph):
            for x, cell in enumerate(row):
                if cell != ".":
                    strip[index(x, y)] = colour
                    lit += 1
        strip.write()
        if not quiet:
            print("    GPIO %-2d  '%s'" % (pin, ch))
    return lit


def clear():
    """Blank every block."""
    for pin in PINS:
        strip = neopixel.NeoPixel(machine.Pin(pin), W * H)
        strip.fill((0, 0, 0))
        strip.write()


# --- colour ---------------------------------------------------------------
# PALETTE holds hues at full 0-255 scale, which is the easy way to think about
# them. dim() scales one down to LEVEL before it ever reaches the LEDs, so the
# current stays sane. To add a colour, add one line here -- nothing else.
PALETTE = {
    "red":     (255, 0, 0),
    "green":   (0, 255, 0),
    "blue":    (0, 0, 255),
    "yellow":  (255, 255, 0),
    "cyan":    (0, 255, 255),
    "magenta": (255, 0, 255),
    "white":   (255, 255, 255),
    "orange":  (255, 110, 0),
    "amber":   (255, 190, 0),
    "lime":    (160, 255, 0),
    "teal":    (0, 255, 150),
    "azure":   (0, 150, 255),
    "purple":  (140, 0, 255),
    "violet":  (190, 0, 255),
    "pink":    (255, 70, 150),
}


def dim(colour, level=LEVEL):
    """Scale a full-brightness (r, g, b) down to a safe drive level."""
    return tuple(c * level // 255 for c in colour)


def hue(name, level=LEVEL):
    """Look a colour up by name, e.g. hue('orange') or hue('red', 120)."""
    return dim(PALETTE[name], level)


# Ready-made constants at the default LEVEL.
RED = hue("red")
GREEN = hue("green")
BLUE = hue("blue")
YELLOW = hue("yellow")
CYAN = hue("cyan")
MAGENTA = hue("magenta")
WHITE = hue("white")
ORANGE = hue("orange")
AMBER = hue("amber")
LIME = hue("lime")
TEAL = hue("teal")
AZURE = hue("azure")
PURPLE = hue("purple")
VIOLET = hue("violet")
PINK = hue("pink")


if __name__ == "__main__":
    TEXT = "HELLO!"
    COLOUR = GREEN
    print("rendering %r left to right:" % TEXT)
    n = draw(TEXT, COLOUR)
    print("%d px lit at level %d" % (n, LEVEL))
