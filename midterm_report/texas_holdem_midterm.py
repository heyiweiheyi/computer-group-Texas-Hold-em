"""A very early Texas Hold'em project framework.

This version only creates and shuffles a deck, then deals two private cards
per player. Betting, community cards, hand ranking, and computer strategy are
left as future steps.
"""

import random


RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
SUITS = ["Spades", "Hearts", "Diamonds", "Clubs"]


class Card:
    """Store the rank and suit of one card."""

    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit

    def __str__(self):
        return f"{self.rank} of {self.suit}"


class Deck:
    """Create, shuffle, and deal cards from a standard 52-card deck."""

    def __init__(self):
        self.cards = []
        for suit in SUITS:
            for rank in RANKS:
                self.cards.append(Card(rank, suit))

    def shuffle(self):
        """Put the cards in a random order."""
        random.shuffle(self.cards)

    def deal_card(self):
        """Remove and return one card from the deck."""
        if not self.cards:
            raise RuntimeError("There are no cards left in the deck.")
        return self.cards.pop()


class Player:
    """Store a player's name and private cards."""

    def __init__(self, name):
        self.name = name
        self.hole_cards = []


class TexasHoldemGame:
    """Set up the first simple card-dealing demonstration."""

    def __init__(self):
        self.deck = Deck()
        self.players = [Player("You"), Player("Computer")]
        self.community_cards = []

    def deal_private_cards(self):
        """Deal two private cards to each player, one card at a time."""
        for _ in range(2):
            for player in self.players:
                player.hole_cards.append(self.deck.deal_card())

    def show_first_deal(self):
        """Display the private cards dealt so far."""
        print(f"Cards remaining in deck: {len(self.deck.cards)}")
        for player in self.players:
            print(f"{player.name}'s cards: {player.hole_cards[0]} and {player.hole_cards[1]}")
        print(f"Community cards: {self.community_cards}")

    def run(self):
        """Run the current prototype: shuffle and deal only."""
        print("Texas Hold'em - Early Framework")
        print("Current step: create a deck, shuffle it, and deal private cards.")

        self.deck.shuffle()
        self.deal_private_cards()
        self.show_first_deal()

        print("\nNext steps for the project:")
        print("- Add chips and blinds.")
        print("- Add betting actions and betting rounds.")
        print("- Deal the Flop, Turn, and River community cards.")
        print("- Compare hands and decide who wins the pot.")
        print("- Add computer-player decisions.")


def main():
    game = TexasHoldemGame()
    game.run()


if __name__ == "__main__":
    main()
