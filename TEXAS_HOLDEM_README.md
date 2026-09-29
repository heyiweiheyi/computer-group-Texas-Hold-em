# Texas Hold'em Terminal Game

A two-player Texas Hold'em game written with the Python standard library. One person plays against a computer opponent. Play continues across hands until a player runs out of chips or the human player quits.

## Run the game

Requires Python 3.8 or newer. Open a terminal in this folder and run:

```bash
py -3 texas_holdem.py
```

If `python` starts Python 3 on your system, this also works:

```bash
python texas_holdem.py
```

After each hand, press Enter to continue or type `q` to quit. Each player starts with 500 chips. The small blind is 5 and the big blind is 10.

## Project files

- `texas_holdem.py` — the complete game: cards, hand evaluation, players, computer strategy, betting, and terminal interaction.
- `test_texas_holdem.py` — hand-evaluation and basic game-flow tests using Python's built-in `unittest` module.
- `midterm_report/texas_holdem_midterm.py` — a very early framework that builds and shuffles a deck, then deals two private cards to each player.
- `midterm_report/texas_holdem_midterm_report.pptx` — the midterm presentation with speaker notes.

Run the tests from this folder:

```bash
py -3 -m unittest -v test_texas_holdem.py
```

## Game rules and implementation

- Uses a standard 52-card deck, shuffled before each hand. The game follows Pre-flop, Flop, Turn, River, and Showdown, including standard burn cards.
- In heads-up play, the button is also the small blind. The button rotates after each hand.
- Supports Check, Call, Raise, Fold, and All-in. A raise amount is the extra amount added after matching the current bet.
- Evaluates all nine standard hand categories from High Card through Straight Flush. Score tuples compare the category and every kicker, including the A-2-3-4-5 wheel straight.
- Each player chooses the best five cards from two private cards and five community cards. When an all-in stack is smaller than the opponent's bet, any unmatched excess is returned.
- The computer uses hand-strength estimates and pot odds. It raises actively and sometimes calls with weaker hands to catch bluffs. This is a beginner-friendly heuristic, not a professional poker AI. The project has no graphical interface, networking, or advanced statistics.

## Python concepts to explain

- **Classes and objects:** `Card`, `Deck`, `Player`, `ComputerPlayer`, and `TexasHoldemGame`.
- **Lists and dictionaries:** store cards, hands, community cards, bets, and action choices.
- **Functions:** separate dealing, betting, hand evaluation, and pot settlement.
- **Loops and conditions:** manage betting rounds, hand evaluation, input validation, and multiple hands.
- **Standard library:** `random` for shuffling, `Counter` for counting ranks, and `itertools.combinations` to check every five-card selection from seven cards.
- **Testing:** `unittest` checks the nine hand categories, wheel straight, kickers, best-five selection, short-stack all-ins, and basic showdown flow.

For a guided walkthrough, start with `Card` and `Deck`, then read `evaluate_five` and `evaluate_best_hand`, and finally follow `TexasHoldemGame.play_hand` and `_run_betting_round`.


