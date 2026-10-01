# LED matrix on RP2350

Six WS2812b blocks, 6x6 each, driven from an RP2350 running MicroPython 1.29.0.

## Hardware map

| Position | GPIO | Notes |
|---|---|---|
| leftmost | 1 | blocks are ordered **right to left** |
| | 2 | |
| | 6 | |
| | 7 | |
| | 9 | |
| rightmost | 10 | `PINS[0]` in code |

Within each block: **pixel 0 is the top-right corner**, rows run right to
left, progressive (not serpentine). Colours are plain `(r, g, b)` tuples —
the driver handles the WS2812b GRB order.

## Power

216 pixels at full white is roughly **13 A at 5 V**. Every script here caps
the per-channel level (usually 60/255, ~0.5 A). Raise it only once you know
the 5 V rail and its injection points can carry the current.

## Editing and running

Edit the `.py` files here in any editor, then push them to the board. The
board is `COM3`; `c3` is mpremote's shortcut for it.

    # run a local script on the board (nothing is stored on the board)
    python -m mpremote c3 run text6x6.py

    # one-off expression or statement
    python -m mpremote c3 exec "import machine, neopixel; neopixel.NeoPixel(machine.Pin(10), 36).write()"

    # interactive REPL -- Ctrl-] to exit, Ctrl-C to break a running loop
    python -m mpremote c3 repl

`run` is the normal edit-test loop: the file stays on your laptop, so just
save and re-run.

### Making code persist on the board

`run` leaves nothing behind. To store a file on the board's filesystem:

    python -m mpremote c3 fs cp text6x6.py :text6x6.py
    python -m mpremote c3 fs ls

A file named `main.py` runs automatically on power-up — that is how you make
the display work without a laptop attached:

    python -m mpremote c3 fs cp text6x6.py :main.py

To stop that, delete it: `python -m mpremote c3 fs rm :main.py`

### VS Code

The **MicroPico** extension gives you an integrated REPL, a "Run current file
on Pico" command, and file upload, so you never leave the editor. Install it
from the Extensions pane, then open this folder.

## Gotchas

- **Only one program can hold COM3 at a time.** If a REPL, VS Code, or another
  mpremote session is connected, the next command fails with an access error.
  Close the other one first.
- **MicroPython is not full CPython.** Some `str`/stdlib methods are missing —
  `ljust` is one, which is why `text6x6.py` pads manually.
- **LEDs latch.** They hold their last colour after a script ends, and even
  through a soft reset. Only writing new data clears them.
- **Recovering the board:** `python -m mpremote c3 bootloader` puts it back in
  BOOTSEL mode as drive `E:`, where dropping a `.uf2` reflashes firmware. Hold
  the BOOTSEL button while plugging in if it is unresponsive.

## Writing text

`font6x6.py` holds the glyph shapes; `text6x6.py` maps them onto the hardware.
Six blocks means six characters at a time.

    python -m mpremote c3 mount . exec "import text6x6 as t; t.draw('WORLD?', t.CYAN)"

Upper and lower case have separate glyphs, so `Hello!` renders as true mixed
case, not shrunken capitals. `t.clear()` blanks everything.

To change the default message, edit the bottom of `text6x6.py` and re-run it.

## Colours

Fifteen are defined in the `PALETTE` dict in `text6x6.py`:

    red     green   blue    yellow  cyan    magenta  white
    orange  amber   lime    teal    azure   purple   violet   pink

Use them either way — a module constant, or by name:

    t.draw('Hello!', t.ORANGE)
    t.draw('Hello!', t.hue('orange'))
    t.draw('Hello!', t.hue('orange', 120))   # brighter, one-off

### Adding a colour

`PALETTE` stores hues at full 0–255 scale, which is how colour pickers give
them to you. `dim()` scales a hue down to `LEVEL` before it reaches the LEDs,
so brightness and hue stay separate concerns. Adding one means adding one line:

    PALETTE["seafoam"] = (80, 255, 200)

It is then available as `t.hue('seafoam')` immediately. Add a matching
`SEAFOAM = hue("seafoam")` line below if you want a constant too.

You can also skip the palette and pass a raw tuple — but note it is *not*
scaled, so keep the values near `LEVEL` rather than at 255:

    t.draw('Hi', (60, 20, 0))        # fine
    t.draw('Hi', t.dim((255, 80, 0)))  # better -- scaled to LEVEL for you

`LEVEL` (default 60) is the brightness ceiling for everything. Raising it
raises the current draw proportionally — see **Power** above before you do.

### Editing the font

Every glyph in `font6x6.py` is six strings of six characters — `X` is lit,
`.` is dark — so they can be edited by eye. Run the module on your laptop to
check your work; it validates every glyph's geometry and previews shapes as
ASCII without touching the board:

    python font6x6.py

Unsupported characters render as a hollow box rather than failing, and both
letter cases map to the same glyph.

### mount vs cp

`mpremote run` copies only the one file you name, so a script that imports
`font6x6` needs that module resolvable on the device. Two ways:

- `mpremote c3 mount .` — exposes this folder to the board's importer. Local
  edits apply immediately, nothing is written to flash. Best while developing.
- `mpremote c3 fs cp font6x6.py :font6x6.py` — writes a real copy to the
  board. Needed for standalone operation, since a mount only exists while
  mpremote is attached. Re-copy after every edit.

`font6x6.py` is already copied onto the board.

## The light show

`show.py` loops four scenes forever (~15.9 s per cycle):

1. diagonal rainbow sweep, 2 s
2. `Good luck Eden!` scrolling, colour flowing along the text — 5.7 s
3. squares zooming inward on every block, each block a different colour, 3× — 1.9 s
4. `Chiquititas rule!` scrolling while it blinks — 6.3 s

Start it:

    python -m mpremote c3 run show.py

### Stopping it

**Press Ctrl-C.** The display is cleared on the way out by a `finally` block,
so it never leaves pixels stuck on — however it exits.

If it is running as `main.py` at power-up, Ctrl-C still works from
`python -m mpremote c3 repl`, because mpremote interrupts the running program
when it connects.

**Do not use `soft-reset` to stop it once `main.py` is installed.** A soft
reset re-runs `main.py`, so the show *restarts* rather than stopping. It only
works as a stop command when nothing is set to auto-start.

To stop it starting at boot, remove or rename `main.py`. Note that
`mpremote fs` has no `mv` — its commands are `cat, cp, sha256sum, ls, rm,
rmdir, touch, tree` — so renaming goes through `os.rename`:

    python -m mpremote c3 fs rm :main.py
    python -m mpremote c3 exec "import os; os.rename('main.py', 'main.bak')"

Renaming is the reversible one: `os.rename('main.bak', 'main.py')` puts it
back without re-copying.

If the board is ever wedged badly enough that mpremote cannot get in, hold
BOOTSEL while replugging: that comes up as drive `E:` and runs nothing.

### Run it at startup, without a laptop

MicroPython runs a file called `main.py` automatically at power-up. All four
modules need to be in the board's flash, since a `mount` only exists while
mpremote is attached:

    python -m mpremote c3 fs cp font6x6.py :font6x6.py
    python -m mpremote c3 fs cp text6x6.py :text6x6.py
    python -m mpremote c3 fs cp show.py :show.py
    python -m mpremote c3 fs cp main.py :main.py

All four are already installed. The show now starts on its own whenever the
board is powered from anything — a USB charger, a battery, a bench supply.
No laptop, no serial connection.

`main.py` is only a two-line wrapper (`import show; show.run()`) rather than a
copy of the show, so after editing `show.py` you only re-copy `show.py`. There
is no second copy to drift out of step.

To stop it starting at boot:

    python -m mpremote c3 fs rm :main.py

Note that `show.py`'s own banner sits under `if __name__ == "__main__"`, which
does not fire when it is imported — so `main.py` prints its own start line.
That makes a boot-time start visible on the serial console.

### Editing the show

Scene functions (`rainbow_diagonal`, `scroll`, `squares_zoom`) each take the
canvas plus timing arguments, and the order lives in `run()` — so reordering,
retiming or dropping a scene is a one-line change. Text is passed in, so
`scroll(canvas, 'Anything you like')` just works.

`scroll()` covers both text scenes. Called plainly, colour flows along the
length of the text. Given `blink_ms=(on, off)` it flashes while scrolling,
one colour per flash, with the scroll position still advancing through the
dark phases so the message travels at a steady pace:

    scroll(canvas, 'Good luck Eden!')                        # scene 2
    scroll(canvas, 'Chiquititas rule!', blink_ms=(180, 90))   # scene 4

Longer messages simply take longer — a scroll pass is
`(len(text) * 6 + 36)` columns at `speed_ms` each. Raise `speed_ms` to slow
it down, lower it to speed up.

The `Canvas` class treats all six blocks as one 36×6 grid with x=0 on the
left, which is what lets text scroll across block boundaries. It derives its
mapping from `text6x6`, so it stays correct if the wiring flags change.

A full-canvas redraw costs ~25 ms (≈40 fps ceiling), so frames are paced
against elapsed render time rather than with a fixed sleep.

### The edit loop for show.py

Edit the local file, then test it straight away without writing to flash:

    python -m mpremote c3 mount . exec "import show; show.run()"

Under `mount` the board's working directory becomes `/remote` and **your local
file takes precedence over the copy in flash** — verified, not assumed. So
edits take effect immediately and the flash copy is left alone. Ctrl-C to stop.

Catch syntax errors before involving the board at all. `show.py` cannot *run*
on a laptop (no `machine` module), but it can be compiled:

    python -m py_compile show.py

When you are happy, write it to flash so it survives a power cycle:

    python -m mpremote c3 fs cp show.py :show.py

Only `show.py` needs re-copying — `main.py` is a wrapper and does not change.

To confirm the board really has what you think it has, compare hashes:

    python -m mpremote c3 fs sha256sum :show.py
    python -c "import hashlib; print(hashlib.sha256(open('show.py','rb').read()).hexdigest())"

Mismatched hashes are the usual explanation for "I edited it but nothing
changed" — the edit never reached flash.

Useful things to change:

| Want | Where |
|---|---|
| Different messages | the `scroll(...)` calls in `run()` |
| Scene order, or drop a scene | `run()` |
| Scroll speed | `speed_ms` argument to `scroll()` |
| Blink rate | `blink_ms=(on, off)` argument |
| Overall brightness | `LEVEL` in `text6x6.py` |
| Colours used by squares/blink | `BLOCK_COLOURS` in `show.py` |

## Files

- `ledtest.py` — hardware bring-up: per-block ID, pixel walk, colour order, all-on
- `font6x6.py` — the 6x6 glyph table: A–Z, a–z, 0–9, punctuation, plus validation and ASCII preview
- `text6x6.py` — block/pixel mapping, colour palette and `draw()`; turns font glyphs into lit pixels
- `show.py` — the looping light show, plus the `Canvas` class that unifies all six blocks into one 36×6 grid
- `main.py` — two-line wrapper that MicroPython runs at power-up; calls `show.run()`
