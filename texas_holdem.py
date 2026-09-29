"""A beginner-friendly, terminal Texas Hold'em game for one player and one computer."""

from collections import Counter
from itertools import combinations
import random


# Card ranks use numbers so comparing and evaluating hands stays straightforward.
RANK_NAMES = {
    11: "J",
    12: "Q",
    13: "K",
    14: "A",
}
SUITS = ["♠", "♥", "♦", "♣"]
HAND_NAMES = [
    "High Card",
    "One Pair",
    "Two Pair",
    "Three of a Kind",
    "Straight",
    "Flush",
    "Full House",
    "Four of a Kind",
    "Straight Flush",
]


class Card:
    """One playing card, such as A♠ or 10♥."""

    def __init__(self, rank, suit):
        if rank < 2 or rank > 14:
            raise ValueError("Card rank must be between 2 and 14.")
        if suit not in SUITS:
            raise ValueError("Unknown suit.")
        self.rank = rank
        self.suit = suit

    def __str__(self):
        rank_text = RANK_NAMES.get(self.rank, str(self.rank))
        return f"{rank_text}{self.suit}"

    def __repr__(self):
        return str(self)


class Deck:
    """A shuffled 52-card deck. Cards are removed as they are dealt."""

    def __init__(self):
        self.cards = []
        for suit in SUITS:
            for rank in range(2, 15):
                self.cards.append(Card(rank, suit))
        random.shuffle(self.cards)

    def draw(self):
        if not self.cards:
            raise RuntimeError("The deck is empty.")
        return self.cards.pop()

    def burn(self):
        """Discard the top card, as in a standard Texas Hold'em deal."""
        self.draw()


def straight_high_card(ranks):
    """Return the high card of a straight, or 0 if these cards are not a straight."""
    unique_ranks = sorted(set(ranks))

    # A wheel is A-2-3-4-5. Here the ace counts as 1, so the straight is five-high.
    if unique_ranks == [2, 3, 4, 5, 14]:
        return 5

    if len(unique_ranks) == 5 and unique_ranks[-1] - unique_ranks[0] == 4:
        return unique_ranks[-1]

    return 0


def evaluate_five(cards):
    """Return a sortable score tuple for exactly five cards.

    The first number is the hand category (0 = high card, 8 = straight flush).
    Remaining numbers are tie-breakers in poker order. Comparing tuples therefore
    compares both the hand type and all of its kickers.
    """
    if len(cards) != 5:
        raise ValueError("evaluate_five requires exactly 5 cards.")

    ranks = sorted([card.rank for card in cards], reverse=True)
    counts = Counter(ranks)
    groups = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)
    is_flush = all(card.suit == cards[0].suit for card in cards)
    straight_high = straight_high_card(ranks)

    if is_flush and straight_high:
        return (8, straight_high)

    if groups[0][1] == 4:
        four_rank = groups[0][0]
        kicker = max(rank for rank in ranks if rank != four_rank)
        return (7, four_rank, kicker)

    if groups[0][1] == 3 and groups[1][1] == 2:
        return (6, groups[0][0], groups[1][0])

    if is_flush:
        return (5, *ranks)

    if straight_high:
        return (4, straight_high)

    if groups[0][1] == 3:
        three_rank = groups[0][0]
        kickers = sorted(
            [rank for rank in ranks if rank != three_rank], reverse=True
        )
        return (3, three_rank, *kickers)

    pair_ranks = sorted(
        [rank for rank, count in counts.items() if count == 2], reverse=True
    )
    if len(pair_ranks) == 2:
        kicker = max(rank for rank in ranks if rank not in pair_ranks)
        return (2, pair_ranks[0], pair_ranks[1], kicker)

    if len(pair_ranks) == 1:
        pair_rank = pair_ranks[0]
        kickers = sorted(
            [rank for rank in ranks if rank != pair_rank], reverse=True
        )
        return (1, pair_rank, *kickers)

    return (0, *ranks)


def evaluate_best_hand(cards):
    """Choose and return the best (score, five-card hand) from five to seven cards."""
    if len(cards) < 5 or len(cards) > 7:
        raise ValueError("Best-hand evaluation requires 5 to 7 cards.")

    best_score = None
    best_five = None
    for five_cards in combinations(cards, 5):
        score = evaluate_five(five_cards)
        if best_score is None or score > best_score:
            best_score = score
            best_five = list(five_cards)

    return best_score, best_five


class Player:
    """A player's name, chip stack, and two private cards."""

    def __init__(self, name, chips, is_human=False):
        self.name = name
        self.chips = chips
        self.is_human = is_human
        self.hole_cards = []

    def take_bet(self, amount):
        """Move up to amount chips from this stack into the pot."""
        actual_amount = min(amount, self.chips)
        self.chips -= actual_amount
        return actual_amount


class ComputerPlayer(Player):
    """A simple opponent that makes decisions from hand strength and pot odds."""

    def __init__(self, name, chips):
        super().__init__(name, chips, is_human=False)

    def estimate_strength(self, board):
        """Return a rough 0-to-1 strength estimate for the computer's current hand."""
        if len(board) >= 3:
            score, _ = evaluate_best_hand(self.hole_cards + board)
            category = score[0]
            # Hand category is the main signal. A small kicker adjustment breaks ties.
            return min(0.99, 0.18 + category * 0.095 + score[1] / 300)

        first, second = self.hole_cards
        high_rank = max(first.rank, second.rank)
        low_rank = min(first.rank, second.rank)
        strength = 0.22 + (high_rank - 2) * 0.018 + (low_rank - 2) * 0.008
        if first.rank == second.rank:
            strength += 0.24
        if first.suit == second.suit:
            strength += 0.06
        if high_rank - low_rank <= 2:
            strength += 0.04
        return min(0.85, strength)

    def choose_action(self, to_call, can_raise, min_raise, pot, board, opponent_all_in):
        """Return a small action dictionary used by the game's betting round."""
        strength = self.estimate_strength(board)

        if opponent_all_in:
            if to_call == 0:
                return {"action": "check"}
            pot_odds = to_call / max(1, pot + to_call)
            # Be cautious against an all-in, but sometimes call with a bluff catcher.
            if strength < 0.18:
                fold_chance = 0.75 if pot_odds > 0.30 else 0.35
            elif strength < 0.26:
                fold_chance = 0.55 if pot_odds > 0.35 else 0.20
            elif strength < 0.34:
                fold_chance = 0.35 if pot_odds > 0.45 else 0.12
            else:
                fold_chance = 0.0

            if random.random() < fold_chance:
                return {"action": "fold"}
            return {"action": "call"}

        if to_call == 0:
            if can_raise:
                # Raise more often with a promising hand, and occasionally bluff.
                if strength >= 0.58:
                    raise_chance = 0.62
                elif strength >= 0.40:
                    raise_chance = 0.32
                elif strength >= 0.30:
                    raise_chance = 0.10
                else:
                    raise_chance = 0.03

                if random.random() < raise_chance:
                    return {"action": "raise", "amount": min_raise}
            return {"action": "check"}

        pot_odds = to_call / max(1, pot + to_call)
        if can_raise:
            # Strong hands and some draws now raise more readily when facing a bet.
            if strength >= 0.58:
                raise_chance = 0.55
            elif strength >= 0.45:
                raise_chance = 0.30
            elif strength >= 0.34:
                raise_chance = 0.14
            elif strength >= 0.28:
                raise_chance = 0.04
            else:
                raise_chance = 0.01

            if random.random() < raise_chance:
                return {"action": "raise", "amount": min_raise}

        # Against a normal bet, occasionally pay to catch a bluff with a weaker hand.
        if strength < 0.18:
            fold_chance = 0.60 if pot_odds > 0.30 else 0.25
        elif strength < 0.26:
            fold_chance = 0.35 if pot_odds > 0.35 else 0.10
        elif strength < 0.34:
            fold_chance = 0.20 if pot_odds > 0.45 else 0.05
        else:
            fold_chance = 0.0

        if random.random() < fold_chance:
            return {"action": "fold"}
        return {"action": "call"}


class TexasHoldemGame:
    """Manage a heads-up game, including dealing, betting, and awarding the pot."""

    def __init__(self, starting_chips=500, small_blind=5, big_blind=10):
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.players = [
            Player("You", starting_chips, is_human=True),
            ComputerPlayer("Computer", starting_chips),
        ]
        self.button_index = random.randrange(2)
        self.deck = None
        self.board = []
        self.pot = 0
        self.round_bets = [0, 0]

    def _other_player(self, player_index):
        return 1 - player_index

    def _put_chips_in_pot(self, player_index, amount):
        player = self.players[player_index]
        actual_amount = player.take_bet(amount)
        self.pot += actual_amount
        self.round_bets[player_index] += actual_amount
        return actual_amount

    def _post_blind(self, player_index, amount, blind_name):
        actual_amount = self._put_chips_in_pot(player_index, amount)
        player = self.players[player_index]
        print(f"{player.name} posts the {blind_name}: ${actual_amount}.")
        if player.chips == 0:
            print(f"{player.name} is all-in.")

    def _deal_hole_cards(self):
        # Deal one card at a time, starting with the button, for two rounds.
        for _ in range(2):
            for player_index in (self.button_index, self._other_player(self.button_index)):
                self.players[player_index].hole_cards.append(self.deck.draw())

    def _show_table(self, reveal_computer=False):
        human = self.players[0]
        computer = self.players[1]
        print("\n" + "=" * 54)
        print(f"You: ${human.chips:<8}  Computer: ${computer.chips:<8}  Pot: ${self.pot}")
        board_text = "  ".join(f"[{card}]" for card in self.board) or "(no community cards yet)"
        print(f"Board: {board_text}")
        print(f"Your hand: [{human.hole_cards[0]}] [{human.hole_cards[1]}]")
        if reveal_computer:
            print(f"Computer hand: [{computer.hole_cards[0]}] [{computer.hole_cards[1]}]")
        else:
            print("Computer hand: [??] [??]")
        print("=" * 54)

    def _human_action(self, player_index, to_call, can_raise, min_raise, opponent_all_in):
        player = self.players[player_index]
        choices = []

        if to_call > 0:
            choices.append(("Fold", {"action": "fold"}))
            call_amount = min(to_call, player.chips)
            call_text = f"Call ${call_amount}"
            if call_amount < to_call:
                call_text += " (short stack; this is an all-in call)"
            choices.append((call_text, {"action": "call"}))
        else:
            choices.append(("Check", {"action": "check"}))

        if can_raise and not opponent_all_in:
            choices.append((f"Raise (minimum raise: ${min_raise})", {"action": "raise"}))

        if not opponent_all_in:
            choices.append((f"All-in (${player.chips})", {"action": "all_in"}))

        print(f"\nYour turn. Pot: ${self.pot}; amount to call: ${to_call}.")
        for number, (label, _) in enumerate(choices, start=1):
            print(f"{number}. {label}")

        while True:
            answer = input("Choose an action: ").strip()
            if answer.isdigit() and 1 <= int(answer) <= len(choices):
                action = choices[int(answer) - 1][1].copy()
                break
            print("Invalid input. Enter a number from the menu.")

        if action["action"] == "raise":
            max_raise = player.chips - to_call
            while True:
                answer = input(
                    f"Enter raise amount (${min_raise} to ${max_raise}, in addition to the call): "
                ).strip()
                try:
                    raise_amount = int(answer)
                except ValueError:
                    print("Enter a whole-number amount.")
                    continue
                if min_raise <= raise_amount <= max_raise:
                    action["amount"] = raise_amount
                    break
                print(f"Amount must be between ${min_raise} and ${max_raise}.")

        return action

    def _ask_for_action(self, player_index, to_call, can_raise, min_raise):
        player = self.players[player_index]
        opponent = self.players[self._other_player(player_index)]
        opponent_all_in = opponent.chips == 0

        if player.is_human:
            self._show_table()
            return self._human_action(
                player_index, to_call, can_raise, min_raise, opponent_all_in
            )

        action = player.choose_action(
            to_call,
            can_raise,
            min_raise,
            self.pot,
            self.board,
            opponent_all_in,
        )
        return action

    def _refund_unmatched_bet(self):
        """Return any unmatched part of the current street's larger contribution."""
        first_bet, second_bet = self.round_bets
        if first_bet == second_bet:
            return

        higher_index = 0 if first_bet > second_bet else 1
        difference = abs(first_bet - second_bet)
        self.players[higher_index].chips += difference
        self.round_bets[higher_index] -= difference
        self.pot -= difference
        print(f"Uncalled bet of ${difference} returned to {self.players[higher_index].name}.")

    def _run_betting_round(self, first_actor):
        """Run one street of betting. Return the folder's opponent, if anyone folded."""
        min_raise = self.big_blind
        pending = []

        # If a blind made a player all-in before the first action, only a player
        # who still owes chips gets a chance to call or fold.
        all_in_indices = [i for i, player in enumerate(self.players) if player.chips == 0]
        if all_in_indices:
            if len(all_in_indices) == 2:
                return None
            all_in_index = all_in_indices[0]
            live_index = self._other_player(all_in_index)
            if self.round_bets[live_index] < self.round_bets[all_in_index]:
                pending = [live_index]
            else:
                return None
        else:
            pending = [first_actor, self._other_player(first_actor)]

        while pending:
            player_index = pending.pop(0)
            player = self.players[player_index]
            opponent_index = self._other_player(player_index)
            opponent = self.players[opponent_index]

            if player.chips == 0:
                continue

            to_call = max(0, self.round_bets[opponent_index] - self.round_bets[player_index])

            # Once the opponent is all-in, no raise can be called. If this player
            # already covers the all-in amount, there is no decision to make.
            if opponent.chips == 0 and to_call == 0:
                continue

            can_raise = (
                opponent.chips > 0
                and player.chips >= to_call + min_raise
            )
            action = self._ask_for_action(
                player_index, to_call, can_raise, min_raise
            )
            action_name = action["action"]

            if action_name == "fold":
                print(f"{player.name} folds.")
                self._refund_unmatched_bet()
                return opponent_index

            if action_name == "check":
                print(f"{player.name} checks.")

            elif action_name == "call":
                amount = self._put_chips_in_pot(player_index, to_call)
                if amount == to_call:
                    print(f"{player.name} calls ${amount}.")
                else:
                    print(f"{player.name} calls all-in with the remaining ${amount}.")

            elif action_name == "raise":
                old_current_bet = max(self.round_bets)
                target_bet = old_current_bet + action["amount"]
                amount_to_put_in = target_bet - self.round_bets[player_index]
                self._put_chips_in_pot(player_index, amount_to_put_in)
                new_current_bet = max(self.round_bets)
                raise_size = new_current_bet - old_current_bet
                if raise_size >= min_raise:
                    min_raise = raise_size
                print(f"{player.name} raises by ${raise_size}; total bet this street: ${new_current_bet}.")
                if player.chips == 0:
                    print(f"{player.name} is all-in.")
                # A raise gives the other player a fresh chance to respond.
                pending = [opponent_index]

            elif action_name == "all_in":
                old_current_bet = max(self.round_bets)
                amount = self._put_chips_in_pot(player_index, player.chips)
                new_current_bet = max(self.round_bets)
                print(f"{player.name} goes all-in for ${amount}.")
                if new_current_bet > old_current_bet:
                    raise_size = new_current_bet - old_current_bet
                    if raise_size >= min_raise:
                        min_raise = raise_size
                    if opponent.chips > 0 and self.round_bets[opponent_index] < new_current_bet:
                        pending = [opponent_index]

            # When everyone who can still act has responded, this street is over.
            # Any unmatched all-in excess is returned before the next street.
            if not pending:
                if any(current_player.chips == 0 for current_player in self.players):
                    self._refund_unmatched_bet()
                break

        return None

    def _deal_flop(self):
        self.deck.burn()
        self.board.extend([self.deck.draw(), self.deck.draw(), self.deck.draw()])
        print("\nFlop: " + "  ".join(f"[{card}]" for card in self.board))

    def _deal_turn_or_river(self, street_name):
        self.deck.burn()
        self.board.append(self.deck.draw())
        print(f"\n{street_name}: [{self.board[-1]}]")

    def _award_pot(self, winner_index):
        winner = self.players[winner_index]
        winner.chips += self.pot
        print(f"{winner.name} wins the pot of ${self.pot}.")
        self.pot = 0

    def _showdown(self):
        self._refund_unmatched_bet()
        self._show_table(reveal_computer=True)

        results = []
        for player in self.players:
            score, best_five = evaluate_best_hand(player.hole_cards + self.board)
            results.append((score, best_five))
            cards_text = " ".join(f"[{card}]" for card in best_five)
            print(f"{player.name}: {HAND_NAMES[score[0]]}; best five cards: {cards_text}")

        human_score = results[0][0]
        computer_score = results[1][0]
        if human_score > computer_score:
            self._award_pot(0)
        elif computer_score > human_score:
            self._award_pot(1)
        else:
            half_pot = self.pot // 2
            self.players[0].chips += half_pot
            self.players[1].chips += half_pot
            odd_chip = self.pot % 2
            if odd_chip:
                # In heads-up play, give an odd chip to the big blind (left of button).
                self.players[self._other_player(self.button_index)].chips += odd_chip
            print(f"Tie! The pot is split; each player receives ${half_pot}.")
            self.pot = 0

    def play_hand(self):
        """Deal and play a single hand. Returns True if a player folded."""
        self.deck = Deck()
        self.board = []
        self.pot = 0
        self.round_bets = [0, 0]
        for player in self.players:
            player.hole_cards = []

        small_blind_index = self.button_index
        big_blind_index = self._other_player(self.button_index)

        self._deal_hole_cards()
        print("\n" + "#" * 54)
        print(f"Button / small blind: {self.players[small_blind_index].name}; big blind: {self.players[big_blind_index].name}")
        self._post_blind(small_blind_index, self.small_blind, "small blind")
        self._post_blind(big_blind_index, self.big_blind, "big blind")

        folded_winner = self._run_betting_round(small_blind_index)
        if folded_winner is not None:
            self._award_pot(folded_winner)
            return True

        if all(player.chips == 0 for player in self.players):
            self._deal_flop()
            self._deal_turn_or_river("Turn")
            self._deal_turn_or_river("River")
            self._showdown()
            return False

        if any(player.chips == 0 for player in self.players):
            # The remaining player has matched the all-in. Deal the rest of the board.
            self._deal_flop()
            self._deal_turn_or_river("Turn")
            self._deal_turn_or_river("River")
            self._showdown()
            return False

        streets = [
            ("flop", self._deal_flop),
            ("turn", lambda: self._deal_turn_or_river("Turn")),
            ("river", lambda: self._deal_turn_or_river("River")),
        ]

        for _, deal_street in streets:
            deal_street()
            self.round_bets = [0, 0]
            first_actor = self._other_player(self.button_index)
            folded_winner = self._run_betting_round(first_actor)
            if folded_winner is not None:
                self._award_pot(folded_winner)
                return True

            if any(player.chips == 0 for player in self.players):
                # Nobody can place another wager, so finish the board automatically.
                while len(self.board) < 5:
                    if len(self.board) == 3:
                        self._deal_turn_or_river("Turn")
                    else:
                        self._deal_turn_or_river("River")
                break

        self._showdown()
        return False

    def run(self):
        print("=" * 54)
        print("Texas Hold'em: You vs. Computer")
        print(f"Starting chips: ${self.players[0].chips} each; blinds: ${self.small_blind}/${self.big_blind}")
        print("In heads-up play, the button is also the small blind. The button rotates after each hand.")
        print("A raise amount is added on top of the call. An all-in uses your entire remaining stack.")
        print("Choose an action by entering its menu number. Press Enter for the next hand or type q to quit.")

        hand_number = 1
        while self.players[0].chips > 0 and self.players[1].chips > 0:
            print(f"\nHand {hand_number}")
            self.play_hand()
            self.button_index = self._other_player(self.button_index)
            hand_number += 1

            if self.players[0].chips == 0 or self.players[1].chips == 0:
                break

            answer = input("Press Enter for the next hand, or type q to quit: ").strip().lower()
            if answer == "q":
                break

        print("\nGame over.")
        print(f"Your chips: ${self.players[0].chips}; computer chips: ${self.players[1].chips}")
        if self.players[0].chips > self.players[1].chips:
            print("You finished with more chips.")
        elif self.players[1].chips > self.players[0].chips:
            print("The computer finished with more chips.")
        else:
            print("You finished with equal chip stacks.")


def main():
    game = TexasHoldemGame()
    try:
        game.run()
    except (EOFError, KeyboardInterrupt):
        print("\nGame interrupted. Goodbye.")


if __name__ == "__main__":
    main()

