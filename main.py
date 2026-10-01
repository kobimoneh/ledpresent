"""Runs automatically at power-up.

MicroPython executes main.py on boot, so copying this to the board is what
makes the display work with no laptop attached:

    python -m mpremote c3 fs cp show.py :show.py
    python -m mpremote c3 fs cp main.py :main.py

It is deliberately just a wrapper around show.run() rather than a copy of the
show itself, so editing show.py is enough -- there is no second copy to keep
in step.

To stop it running at boot:  python -m mpremote c3 fs rm :main.py
To interrupt a running show:  Ctrl-C (see the README)
"""

import show

# show.py's own banner lives under `if __name__ == "__main__"`, which does not
# fire on import -- so print it here to make a boot-time start visible.
print("main.py: running light show -- press Ctrl-C to stop")
show.run()
