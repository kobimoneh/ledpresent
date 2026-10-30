"""Halloween light show for the 6-block WS2812b display.

Scenes, looping forever:
  pumpkins     jack-o'-lanterns on every block, candle-flickering
  creep_scroll "Happy Halloween!" scrolling, guttering like a candle
  bats         bats flapping, each block out of phase with its neighbours
  lightning    white strobes with dark, uneven gaps
  ghosts       a ghost drifting across all six blocks, bobbing and fading
  eyes         pairs of eyes opening and blinking in the dark
  cauldron     green witch-fire rising from the bottom edge
  skulls       skulls pulsing slowly

Built on show.py: Canvas, frames(), scale(), bitmap() and pace() all come
from there, so the wiring and brightness rules stay in one place.

STOPPING IT
  Press Ctrl-C. The display is cleared on the way out.

RUNNING IT
  python -m mpremote c3 mount . exec "import halloween; halloween.run()"
  python -m mpremote c3 run halloween.py
"""

import math
import random
import time

import show

# --- palette (full scale; scale() dims to LEVEL on the way out) ----------
ORANGE = (255, 85, 0)
PUMPKIN_FLESH = (255, 70, 0)
CANDLE = (255, 200, 40)
STEM = (60, 180, 30)
WHITE = (255, 255, 255)
BONE = (235, 235, 210)
PURPLE = (140, 0, 255)
BLOOD = (255, 20, 20)
EYE = (255, 40, 0)

# Characters used in the sprite art below.
INK = {
    "O": PUMPKIN_FLESH,
    "Y": CANDLE,
    "G": STEM,
    "W": WHITE,
    "B": BONE,
    "P": PURPLE,
    "R": BLOOD,
    "E": EYE,
}

# --- sprites, 6x6 each ----------------------------------------------------
# '.' is transparent. 'K' marks the carved features: drawn dark by default,
# swapped to 'Y' when the candle inside flares.
PUMPKIN = ("..GG..",
           ".OOOO.",
           "OKOOKO",
           "OOOOOO",
           "OKKKKO",
           ".OOOO.")

GHOST = ("..WW..",
         ".WWWW.",
         "WKWWKW",
         "WWWWWW",
         "WWWWWW",
         "W.W.W.")

BAT_UP = ("PP..PP",
          "PPPPPP",
          ".PPPP.",
          "..PP..",
          "......",
          "......")

BAT_DOWN = ("......",
            "..PP..",
            "PPPPPP",
            "PPPPPP",
            ".P..P.",
            "......")

SKULL = (".BBBB.",
         "BBBBBB",
         "BKBBKB",
         "BBBBBB",
         ".BBBB.",
         ".B.B.B")

EYES = ("......",
        "......",
        "EE..EE",
        "EE..EE",
        "......",
        "......")


def sprite(canvas, art, x0, bright=255, swap=None, y0=0):
    """Blit 6x6 art at canvas column x0, clipped to the canvas.

    swap remaps art characters, e.g. {"K": "Y"} to light the carved features.
    Characters not in INK (notably 'K' and '.') are left dark.
    """
    for y, row in enumerate(art):
        cy = y + y0
        if not 0 <= cy < show.H:
            continue
        for x, ch in enumerate(row):
            cx = x0 + x
            if ch == "." or not 0 <= cx < show.W:
                continue
            if swap:
                ch = swap.get(ch, ch)
            colour = INK.get(ch)
            if colour:
                canvas.set(cx, cy, show.scale(colour, bright))


BLOCKS = show.W // 6          # six blocks of six columns


# --- scenes ---------------------------------------------------------------
def pumpkins(canvas, seconds=5.0):
    """A jack-o'-lantern per block, each flickering on its own candle."""
    lit = [random.getrandbits(1) for _ in range(BLOCKS)]
    for n in show.frames(canvas, seconds):
        canvas.clear()
        for b in range(BLOCKS):
            # Occasionally the candle flares and the carved features glow.
            if n % 7 == 0 and random.randint(0, 99) < 30:
                lit[b] ^= 1
            bright = random.randint(165, 255)
            sprite(canvas, PUMPKIN, b * 6, bright,
                   {"K": "Y"} if lit[b] else None)


def bats(canvas, seconds=4.0):
    """Bats flapping, neighbouring blocks deliberately out of phase."""
    for n in show.frames(canvas, seconds):
        canvas.clear()
        for b in range(BLOCKS):
            art = BAT_UP if ((n // 4) + b) % 2 == 0 else BAT_DOWN
            sprite(canvas, art, b * 6, 235)


def skulls(canvas, seconds=4.0):
    """Skulls breathing in and out together."""
    for n in show.frames(canvas, seconds):
        canvas.clear()
        # A slow triangle wave, so the pulse has no visible seam.
        phase = n % 40
        bright = 70 + (phase if phase < 20 else 40 - phase) * 9
        for b in range(BLOCKS):
            sprite(canvas, SKULL, b * 6, bright)


def eyes(canvas, seconds=4.0):
    """Pairs of eyes in the dark, opening and blinking independently."""
    open_ = [True] * BLOCKS
    hold = [random.randint(4, 30) for _ in range(BLOCKS)]
    for _ in show.frames(canvas, seconds):
        canvas.clear()
        for b in range(BLOCKS):
            hold[b] -= 1
            if hold[b] <= 0:
                open_[b] = not open_[b]
                # Open for a good while, blink shut only briefly.
                hold[b] = (random.randint(10, 40) if open_[b]
                           else random.randint(2, 5))
            if open_[b]:
                sprite(canvas, EYES, b * 6, random.randint(170, 255))


def ghosts(canvas, seconds=6.0):
    """One ghost drifting right to left, bobbing, fading at both ends."""
    span = show.W + 6                      # off one edge to off the other
    for n in show.frames(canvas, seconds):
        canvas.clear()
        # Travel the whole span over the scene's length, at ~25 fps.
        travel = (n * span) // max(1, int(seconds * 25))
        x0 = show.W - travel
        if x0 < -6:
            x0 = -6
        bob = int(math.sin(n / 5.0) + 0.5)          # -1, 0 or 1
        # Fade in on entry and out on exit so it does not pop.
        edge = min(x0 + 6, show.W - x0, 6)
        bright = 90 + max(0, edge) * 27
        sprite(canvas, GHOST, x0, min(255, bright), y0=bob)


def lightning(canvas, times=3):
    """White strobes in pairs, with uneven darkness between."""
    for _ in range(times):
        for bright in (255, 70, 255):
            canvas.clear()
            for y in range(show.H):
                for x in range(show.W):
                    canvas.set(x, y, show.scale(WHITE, bright))
            canvas.show()
            time.sleep_ms(45)
        canvas.clear()
        canvas.show()
        time.sleep_ms(random.randint(220, 650))


def _brew(h):
    """Flame colour for heat h (0-255): deep green core to pale tips."""
    if h < 110:
        return (0, 170, 40)
    if h < 190:
        return (60, 255, 60)
    return (190, 255, 150)


def cauldron(canvas, seconds=5.0):
    """Green witch-fire licking up from the bottom row."""
    heat = [[0] * show.W for _ in range(show.H)]
    for _ in show.frames(canvas, seconds):
        # Stoke the bottom row, then let heat rise and cool as it spreads.
        bottom = heat[show.H - 1]
        for x in range(show.W):
            bottom[x] = random.randint(120, 255)
        for y in range(show.H - 1):
            below = heat[y + 1]
            row = heat[y]
            for x in range(show.W):
                left = below[x - 1] if x else below[x]
                right = below[x + 1] if x < show.W - 1 else below[x]
                avg = (below[x] + left + right) // 3
                row[x] = max(0, avg - random.randint(20, 55))
        canvas.clear()
        for y in range(show.H):
            row = heat[y]
            for x in range(show.W):
                h = row[x]
                if h > 14:
                    canvas.set(x, y, show.scale(_brew(h), h))


def creep_scroll(canvas, text, colour=ORANGE, speed_ms=45, flicker=False):
    """Scroll text once in a single colour, optionally guttering as it goes."""
    rows = show.bitmap(text)
    total = len(rows[0])
    for offset in range(-show.W, total + 1):
        started = time.ticks_ms()
        canvas.clear()
        bright = random.randint(150, 255) if flicker else 255
        lit = show.scale(colour, bright)
        for x in range(show.W):
            src = offset + x
            if 0 <= src < total:
                for y in range(show.H):
                    if rows[y][src] != ".":
                        canvas.set(x, y, lit)
        canvas.show()
        show.pace(started, speed_ms)


# --- main loop ------------------------------------------------------------
def run():
    canvas = show.Canvas()
    try:
        while True:
            pumpkins(canvas, 5.0)
            creep_scroll(canvas, "Happy Halloween!", ORANGE, flicker=True)
            bats(canvas, 4.0)
            lightning(canvas, 3)
            creep_scroll(canvas, "Scared yet?", BLOOD)
            ghosts(canvas, 6.0)
            eyes(canvas, 4.0)
            cauldron(canvas, 5.0)
            creep_scroll(canvas, "Trick or Treat, Eden!", PURPLE)
            skulls(canvas, 4.0)
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        canvas.clear()
        canvas.show()


if __name__ == "__main__":
    print("Halloween show -- press Ctrl-C to stop")
    run()
