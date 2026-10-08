#!/usr/bin/env python3
"""PC-side control for the 6-block LED display.  Needs: pip install pyserial

The board must have ledserver.py (plus font6x6, text6x6, show) in flash:
    python -m mpremote c3 fs cp ledserver.py :ledserver.py

Each run interrupts whatever the board is doing (e.g. the light show),
starts ledserver, sends the command, and leaves the result on the LEDs.

Colours: a palette name (red, orange, azure, ...), r,g,b or #rrggbb.

  python ledctl.py ping
  python ledctl.py fill red
  python ledctl.py clear
  python ledctl.py text azure HELLO!
  python ledctl.py scroll "Good luck Eden!" --colour rainbow --speed 45
  python ledctl.py block 2 #ff8000
  python ledctl.py px 0 0 255,255,255
  python ledctl.py rect 6 1 12 4 green
  python ledctl.py rainbow 5
  python ledctl.py squares 3
  python ledctl.py scene fire 10                (comet sparkle fire rain plasma ripple rainbow)
  python ledctl.py level 30
  python ledctl.py anim plasma --fps 25         (PC-generated frames, Ctrl+C stops)
  python ledctl.py show                         (restart the built-in light show)
  python ledctl.py --port COM3 ...              (default COM3, else auto-detect)
"""
import argparse
import math
import sys
import time

import serial
from serial.tools import list_ports

W, H = 36, 6
RPI_VID = 0x2E8A


def find_port():
    ports = [p.device for p in list_ports.comports() if p.vid == RPI_VID]
    if not ports:
        sys.exit("No RP2350 found (VID 2e8a). Is another program holding it? Use --port.")
    return ports[0]


class Board:
    def __init__(self, port):
        try:
            self.s = serial.Serial(port, 115200, timeout=3)
        except serial.SerialException as e:
            sys.exit("%s\nClose Thonny / VS Code REPL / other mpremote using %s." % (e, port))

    def interrupt(self):
        self.s.write(b"\r\x03\x03")
        time.sleep(0.3)
        self.s.reset_input_buffer()
        self.s.write(b"\r")
        time.sleep(0.1)
        self.s.reset_input_buffer()

    def start_server(self):
        self.interrupt()
        self.s.write(b"import ledserver; ledserver.run()\r")
        end = time.time() + 5
        seen = []
        while time.time() < end:
            ln = self.s.readline().decode(errors="replace").strip()
            if ln == "ledserver ready":
                return
            if ln:
                seen.append(ln)
            if "ImportError" in ln or "no module named" in ln.lower():
                break
        sys.exit("ledserver did not start. Board said:\n  " + "\n  ".join(seen[-5:]) +
                 "\nCopy it to the board:  python -m mpremote c3 fs cp ledserver.py :ledserver.py")

    def cmd(self, line, timeout=3):
        self.s.timeout = timeout
        self.s.write((line + "\n").encode())
        while True:
            r = self.s.readline().decode(errors="replace").strip()
            if not r:
                raise TimeoutError("no reply to %r" % line[:40])
            if r.startswith("ok"):
                return r
            if r.startswith("err"):
                sys.exit(r)

    def start_show(self):
        self.interrupt()
        self.s.write(b"import show; show.run()\r")
        time.sleep(0.3)


def plasma(t):
    out = bytearray()
    for y in range(H):
        for x in range(W):
            v = math.sin(x / 4 + t) + math.sin((y + t) / 2) + math.sin((x + y) / 6 + t * 1.3)
            h = (v / 6 + 0.5) % 1
            r = int(127 * (1 + math.sin(2 * math.pi * h)))
            g = int(127 * (1 + math.sin(2 * math.pi * (h + 1 / 3))))
            b = int(127 * (1 + math.sin(2 * math.pi * (h + 2 / 3))))
            out += bytes((r, g, b))
    return out


def sweep(t):
    out = bytearray()
    col = int(t * 12) % W
    for y in range(H):
        for x in range(W):
            d = abs(x - col)
            v = max(0, 255 - d * 70)
            out += bytes((v, v // 3, 0))
    return out


SCENES = ("comet", "sparkle", "fire", "rain", "plasma", "ripple", "rainbow")
ANIMS = {"plasma": plasma, "sweep": sweep}


def main():
    ap = argparse.ArgumentParser(description="6-block LED display control")
    ap.add_argument("--port", default=None)
    sp = ap.add_subparsers(dest="c", required=True)
    sp.add_parser("ping")
    sp.add_parser("clear")
    sp.add_parser("show")
    sp.add_parser("fill").add_argument("colour")
    p = sp.add_parser("text"); p.add_argument("colour"); p.add_argument("msg")
    p = sp.add_parser("scroll"); p.add_argument("msg")
    p.add_argument("--colour", default="rainbow"); p.add_argument("--speed", type=int, default=45)
    p.add_argument("--repeat", type=int, default=1, help="0 = forever")
    p = sp.add_parser("block"); p.add_argument("n", type=int); p.add_argument("colour")
    p = sp.add_parser("px"); p.add_argument("x", type=int); p.add_argument("y", type=int); p.add_argument("colour")
    p = sp.add_parser("rect")
    for k in ("x", "y", "w", "h"):
        p.add_argument(k, type=int)
    p.add_argument("colour")
    sp.add_parser("rainbow").add_argument("seconds", type=float, nargs="?", default=3)
    sp.add_parser("squares").add_argument("times", type=int, nargs="?", default=3)
    p = sp.add_parser("scene"); p.add_argument("name", choices=SCENES)
    p.add_argument("seconds", type=float, nargs="?", default=5)
    sp.add_parser("level").add_argument("v", type=int)
    p = sp.add_parser("anim"); p.add_argument("name", choices=sorted(ANIMS))
    p.add_argument("--fps", type=float, default=25); p.add_argument("--seconds", type=float, default=0)
    a = ap.parse_args()

    port = a.port or ("COM3" if sys.platform == "win32" and "COM3" in
                      [p.device for p in list_ports.comports()] else find_port())
    b = Board(port)

    if a.c == "show":
        b.start_show()
        print("light show running")
        return

    b.start_server()
    try:
        if a.c == "ping":
            _, w, h, lvl = b.cmd("ping").split()
            print("ok  %sx%s  level=%s  port=%s" % (w, h, lvl, port))
        elif a.c == "clear":
            b.cmd("clear")
        elif a.c == "fill":
            b.cmd("fill " + a.colour)
        elif a.c == "text":
            b.cmd("text %s %s" % (a.colour, a.msg))
        elif a.c == "scroll":
            n = 0
            while a.repeat == 0 or n < a.repeat:
                t = (len(a.msg) * 6 + W) * a.speed / 1000 * 2 + 5
                b.cmd("scroll %s %d %s" % (a.colour, a.speed, a.msg), timeout=t)
                n += 1
        elif a.c == "block":
            b.cmd("block %d %s" % (a.n, a.colour))
        elif a.c == "px":
            b.cmd("px %d %d %s" % (a.x, a.y, a.colour))
        elif a.c == "rect":
            b.cmd("rect %d %d %d %d %s" % (a.x, a.y, a.w, a.h, a.colour))
        elif a.c == "rainbow":
            b.cmd("rainbow %g" % a.seconds, timeout=a.seconds + 5)
        elif a.c == "squares":
            b.cmd("squares %d" % a.times, timeout=a.times * 2 + 5)
        elif a.c == "scene":
            b.cmd("scene %s %g" % (a.name, a.seconds), timeout=a.seconds + 5)
        elif a.c == "level":
            if a.v > 60:
                print("warning: level %d -- 216 px at 255 is ~13 A at 5 V" % a.v)
            print(b.cmd("level %d" % a.v))
        elif a.c == "anim":
            f, t0, dt = ANIMS[a.name], time.time(), 1 / a.fps
            while a.seconds <= 0 or time.time() - t0 < a.seconds:
                st = time.time()
                b.cmd("frame " + f(st - t0).hex())
                time.sleep(max(0, dt - (time.time() - st)))
    except KeyboardInterrupt:
        b.cmd("clear")


if __name__ == "__main__":
    main()
