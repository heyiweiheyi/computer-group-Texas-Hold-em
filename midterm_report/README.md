# Midterm Demo: Early Framework

This is an intentionally small first-stage prototype for a Python Texas Hold'em project. It creates a standard 52-card deck, shuffles it, and deals two private cards to each player.

## Run

Open a terminal in this folder and run:

```bash
py -3 texas_holdem_midterm.py
```

The current program demonstrates these parts only:

- `Card` stores a card's rank and suit.
- `Deck` builds 52 cards, shuffles them, and deals cards.
- `Player` stores a name and two private cards.
- `TexasHoldemGame` connects the first dealing steps and displays the result.

Betting, blinds, community cards, hand evaluation, pot settlement, and computer strategy are planned next steps and are not implemented in this prototype.

See the parent folder's `README.md` for the complete game version and tests.
