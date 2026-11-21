# Texas Hold'em Poker Game

A 2-to-6 player (1 human vs. 1–5 computer opponents) Texas Hold'em game written in Python, featuring both a **Pygame graphical interface** (`texas_holdem_gui.py`) and a **terminal version** (`texas_holdem.py`). Play continues across hands until the human player is eliminated, all computer opponents bust out, or the player quits.

## Run the Graphical UI (Recommended)

Requires Python 3.8+ and `pygame-ce` (listed in `requirements.txt`):

```bash
py -3 -m pip install -r requirements.txt
py -3 texas_holdem_gui.py
```

UI features & shortcuts:
- **Multi-AI Ring Table (1–5 AI, up to 6 players):** Click `Table: N AI` in the top bar to set the number of computer opponents (capped at 5 AI), starting chips, and blinds, with automatic `D`/`SB`/`BB` rotation, player elimination, and main/side-pot settlement
- **All-In Runout ("跑马"):** Automatic hole-card reveal, live win-equity percentages (`WIN %`) updated at every street, and choice between **Run Once (`[1]`)** and **Run It Twice (`[2]`)** dual-board split
- Interactive action buttons (`Fold [F]`, `Check / Call [C]`, `Raise [R]`, `All-In [A]`, `Next Hand [Space]`)
- Raise slider with `Min`, `1/2 Pot`, `Pot`, and `Max` presets
- Smooth card dealing animations, winning 5-card showdown highlights, live best-hand indicator, toggleable action log (`[L]`), hand rankings guide (`[H]`), and synthesized sound effects (`[M]` to mute)

## Run the Terminal Version

Open a terminal in this folder and run:

```bash
py -3 texas_holdem.py
```

If `python` starts Python 3 on your system, this also works:

```bash
python texas_holdem.py
```

After each hand, press Enter to continue or type `q` to quit. Each player starts with 500 chips. The small blind is 5 and the big blind is 10.

## Project files

- `texas_holdem.py` — core game rules, cards, hand evaluator, computer strategy, terminal game (`TexasHoldemGame`), and state-driven UI engine (`TexasHoldemSession`).
- `texas_holdem_gui.py` — Pygame desktop interface, animations, HUD, and event loop.
- `ui_theme.py` — color palette, typography loader, and smoothing helpers.
- `ui_assets.py` — 2x supersampled felt table, vector playing cards, chip stacks, and synthesized sound effects.
- `ui_widgets.py` — reusable buttons, raise slider with presets, hand-ranking modal, and multi-AI table setup modal.
- `requirements.txt` — Python dependency (`pygame-ce`) for the graphical interface.
- `test_texas_holdem.py` and `tests/test_ui_session.py` — `unittest` suites covering hand evaluation, game flow, side pots, `TexasHoldemSession`, and headless UI rendering.
- `midterm_report/texas_holdem_midterm.py` — a very early framework that builds and shuffles a deck, then deals two private cards to each player.
- `midterm_report/texas_holdem_midterm_report.pptx` — the midterm presentation with speaker notes.

Run all tests from this folder:

```bash
py -3 -m unittest -v test_texas_holdem.py tests/test_ui_session.py
```

Or with `pytest` (as used by GitHub Actions CI):

```bash
py -3 -m pytest -q
```

## Game rules and implementation

- Uses a standard 52-card deck, shuffled before each hand. The game follows Pre-flop, Flop, Turn, River, and Showdown, including standard burn cards.
- In heads-up play (2 players), the button is also the small blind. In 3-to-6 player games, `D` (button), `SB`, and `BB` are distinct seats rotating clockwise, skipping eliminated players.
- Supports Check, Call, Raise, Fold, and All-in. A raise amount is the extra amount added after matching the current bet.
- Evaluates all nine standard hand categories from High Card through Straight Flush. Score tuples compare the category and every kicker, including the A-2-3-4-5 wheel straight.
- Each player chooses the best five cards from two private cards and five community cards. Multi-way unequal all-ins are split into main and side pots (`build_side_pots`), and unmatched bets are returned.
- In the graphical UI, an all-in before the river triggers live equity calculation (`estimate_all_in_equities`) and lets the player choose **Run Once** or **Run It Twice** (`run_count = 2`).
- The computer uses hand-strength estimates and pot odds. It raises actively and sometimes calls with weaker hands to catch bluffs. This is a beginner-friendly heuristic, not a professional poker AI. The project has no networking or advanced statistics.

## Python concepts to explain

- **Classes and objects:** `Card`, `Deck`, `Player`, `ComputerPlayer`, and `TexasHoldemGame`.
- **Lists and dictionaries:** store cards, hands, community cards, bets, and action choices.
- **Functions:** separate dealing, betting, hand evaluation, and pot settlement.
- **Loops and conditions:** manage betting rounds, hand evaluation, input validation, and multiple hands.
- **Standard library:** `random` for shuffling, `Counter` for counting ranks, and `itertools.combinations` to check every five-card selection from seven cards.
- **Testing:** `unittest` checks the nine hand categories, wheel straight, kickers, best-five selection, short-stack all-ins, and basic showdown flow.

For a guided walkthrough, start with `Card` and `Deck`, then read `evaluate_five` and `evaluate_best_hand`, and finally follow `TexasHoldemGame.play_hand` and `_run_betting_round`.


