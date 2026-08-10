"""
Where an episode's output folder lives.

The folder used to be pinned to ~/Desktop/<SYM> <DATE>, which broke the audits the
moment the Desktop got tidied and the decks were filed under a subfolder. The
build still WRITES to one canonical place, but everything that reads afterwards
searches, so moving a finished episode never breaks its audit trail.

Order:
  1. $DECK_OUT/<SYM> <DATE>        — explicit override, wins outright
  2. ~/Desktop/<SYM> <DATE>        — the flat default
  3. ~/Desktop/*/<SYM> <DATE>      — one level of tidying, e.g. "Stock Analysis/"
  4. ~/Documents/*/<SYM> <DATE>
"""

import glob
import os

FOLDER = "{sym} {date}"


def _candidates(sym, date):
    name = FOLDER.format(sym=sym, date=date)
    env = os.environ.get("DECK_OUT")
    if env:
        yield os.path.join(os.path.expanduser(env), name)
    for base in ("~/Desktop", "~/Documents"):
        root = os.path.expanduser(base)
        yield os.path.join(root, name)
        yield from sorted(glob.glob(os.path.join(root, "*", name)))


# Where episodes are filed by default. $DECK_OUT still wins, but the default is
# the folder that actually holds them rather than a bare Desktop drop.
DEFAULT_OUT = "~/Desktop/Stock Analys"


def write_dir(sym, date):
    """Where a fresh build writes. Honours $DECK_OUT, else DEFAULT_OUT if it exists."""
    env = os.environ.get("DECK_OUT")
    if env:
        root = os.path.expanduser(env)
    else:
        preferred = os.path.expanduser(DEFAULT_OUT)
        root = preferred if os.path.isdir(preferred) else os.path.expanduser("~/Desktop")
    return os.path.join(root, FOLDER.format(sym=sym, date=date))


def read_dir(sym, date, die=None):
    """
    Where a built episode actually is. Prefers an existing folder that contains a
    deck; falls back to the write path so the error message names the obvious spot.
    """
    for path in _candidates(sym, date):
        if os.path.isfile(os.path.join(path, f"{sym}-{date}.html")):
            return path
    if die:
        die(f"no built deck for {sym} {date}. Looked in $DECK_OUT, ~/Desktop and one "
            f"level below it. Run: python3 scripts/build_deck.py {sym}")
    return write_dir(sym, date)
