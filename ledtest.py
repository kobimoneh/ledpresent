"""WS2812b matrix bring-up test for RP2350.

6 blocks of 6x6 (36 px) on GPIO 10, 9, 7, 6, 2, 1.
Brightness is held low on purpose: 216 px at full white is ~13 A.
"""

import time

import machine
import neopixel

PINS = [10, 9, 7, 6, 2, 1]
N = 36                      # 6x6 per block
DIM = 20                    # per-channel level for single-block fills
ALL_DIM = 8                 # per-channel level when every block is lit

# One identifying colour per block, in PINS order.
TAGS = [
    ("red",     (DIM, 0, 0)),
    ("green",   (0, DIM, 0)),
    ("blue",    (0, 0, DIM)),
    ("yellow",  (DIM, DIM, 0)),
    ("cyan",    (0, DIM, DIM)),
    ("magenta", (DIM, 0, DIM)),
]

strips = [neopixel.NeoPixel(machine.Pin(p), N) for p in PINS]


def blank():
    for s in strips:
        s.fill((0, 0, 0))
        s.write()


def stage_block_id():
    """Each data line in turn, solid, with its own colour."""
    print("\n[1] BLOCK ID -- one block at a time, 1.5 s each")
    for i, (pin, (name, colour)) in enumerate(zip(PINS, TAGS)):
        blank()
        strips[i].fill(colour)
        strips[i].write()
        print("    block %d  GPIO %-2d  %s" % (i + 1, pin, name))
        time.sleep(1.5)
    blank()


def stage_walk():
    """Single pixel across all 36 of each block: proves chain length."""
    print("\n[2] PIXEL WALK -- 1 px sweeps 0..35 on each block")
    for i, pin in enumerate(PINS):
        blank()
        s = strips[i]
        for j in range(N):
            s.fill((0, 0, 0))
            s[j] = (DIM, DIM, DIM)
            s.write()
            time.sleep(0.03)
        print("    block %d  GPIO %-2d  walked %d px" % (i + 1, pin, N))
        time.sleep(0.2)
    blank()


def stage_colour_order():
    """All blocks together through R, G, B: catches GRB/RGB mix-ups."""
    print("\n[3] COLOUR ORDER -- all blocks, 1.5 s each")
    for name, colour in (("RED", (DIM, 0, 0)),
                         ("GREEN", (0, DIM, 0)),
                         ("BLUE", (0, 0, DIM))):
        for s in strips:
            s.fill(colour)
            s.write()
        print("    expect %s everywhere" % name)
        time.sleep(1.5)
    blank()


def stage_all_on():
    """Every pixel lit: shakes out power-rail sag and dead pixels."""
    print("\n[4] ALL ON -- 216 px white at level %d, 3 s" % ALL_DIM)
    for s in strips:
        s.fill((ALL_DIM, ALL_DIM, ALL_DIM))
        s.write()
    time.sleep(3)
    blank()


def run():
    print("WS2812b test: %d blocks x %d px on GPIO %s"
          % (len(PINS), N, PINS))
    stage_block_id()
    stage_walk()
    stage_colour_order()
    stage_all_on()
    print("\ndone -- all blank")


if __name__ == "__main__":
    run()
