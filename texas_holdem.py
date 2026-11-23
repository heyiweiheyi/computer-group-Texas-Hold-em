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


AI_TIER_SETTINGS = {
    "Ultra": {"stars": 5, "noise": 0.015, "tightness": 0.04, "aggression": 1.25, "bluff": 0.04},
    "Master": {"stars": 4, "noise": 0.03, "tightness": 0.02, "aggression": 1.08, "bluff": 0.03},
    "Pro": {"stars": 3, "noise": 0.045, "tightness": 0.0, "aggression": 1.0, "bluff": 0.02},
    "Normal": {"stars": 2, "noise": 0.08, "tightness": -0.03, "aggression": 0.85, "bluff": 0.02},
    "Rookie": {"stars": 1, "noise": 0.14, "tightness": -0.07, "aggression": 0.65, "bluff": 0.05},
}

AI_ROSTER = [
    {"name": "Claude", "tier": "Ultra", "style": "GTO Shark", "tag": "Anthropic"},
    {"name": "Jtt", "tier": "Ultra", "style": "Final Boss", "tag": "Rollingwood"},
    {"name": "Gemini", "tier": "Master", "style": "Sharp Reader", "tag": "Google"},
    {"name": "Chatgpt", "tier": "Master", "style": "Balanced Ace", "tag": "Openai"},
    {"name": "Deepseek", "tier": "Master", "style": "Math Tactician", "tag": "DeepSeek"},
    {"name": "Glm", "tier": "Pro", "style": "Steady Grinder", "tag": "Zcode"},
    {"name": "Kimi", "tier": "Pro", "style": "Patient Stalker", "tag": "Moonshot"},
    {"name": "Doubao", "tier": "Pro", "style": "Tricky Caller", "tag": "ByteDance"},
    {"name": "Yuanzuo", "tier": "Normal", "style": "Casual Player", "tag": "Rollingwood"},
    {"name": "Zch", "tier": "Normal", "style": "Loose Gambler", "tag": "Rollingwood"},
    {"name": "Xrh", "tier": "Rookie", "style": "Card Tourist", "tag": "Rollingwood"},
    {"name": "Qzr", "tier": "Rookie", "style": "Chip Donor", "tag": "Rollingwood"},
]


class ComputerPlayer(Player):
    """A tiered AI opponent that weighs hand strength, pot odds, and stack commitment."""

    def __init__(self, name, chips, tier="Pro", tag=""):
        super().__init__(name, chips, is_human=False)
        self.tier = tier if tier in AI_TIER_SETTINGS else "Pro"
        self.tag = tag

    def _has_draw_bonus(self, board):
        """Return a modest bonus for flush draws on the flop or turn."""
        if len(board) not in (3, 4):
            return 0.0
        cards = self.hole_cards + board
        suit_counts = Counter(card.suit for card in cards)
        if max(suit_counts.values()) == 4:
            return 0.11 if len(board) == 3 else 0.07
        return 0.0

    def estimate_strength(self, board):
        """Return a calibrated 0-to-1 strength estimate for the computer's current hand."""
        if len(board) >= 3:
            score, _ = evaluate_best_hand(self.hole_cards + board)
            category = score[0]
            draw_bonus = self._has_draw_bonus(board)

            if category == 0:
                base = 0.08 + score[1] / 140.0
            elif category == 1:
                board_max = max(card.rank for card in board)
                pair_rank = score[1]
                # Distinguish overpair / top pair from middle or bottom pair
                if pair_rank > board_max:
                    base = 0.62 + pair_rank / 140.0
                elif pair_rank == board_max:
                    base = 0.48 + score[2] / 160.0
                else:
                    base = 0.26 + pair_rank / 140.0
            elif category == 2:
                base = 0.68 + score[1] / 140.0
            elif category == 3:
                base = 0.78 + score[1] / 140.0
            elif category == 4:
                base = 0.85
            elif category == 5:
                base = 0.89
            elif category == 6:
                base = 0.94
            else:
                base = 0.98
            return min(0.99, base + draw_bonus)

        first, second = self.hole_cards
        high_rank = max(first.rank, second.rank)
        low_rank = min(first.rank, second.rank)
        high_norm = (high_rank - 2) / 12.0
        low_norm = (low_rank - 2) / 12.0
        gap = high_rank - low_rank

        strength = 0.08 + high_norm * 0.28 + low_norm * 0.14
        if first.rank == second.rank:
            strength += 0.26 + high_norm * 0.18
        else:
            if low_rank >= 10:
                strength += 0.12
            if first.suit == second.suit:
                strength += 0.07
            if gap <= 1:
                strength += 0.05
            elif gap == 2:
                strength += 0.02
            elif gap >= 4 and high_rank < 12:
                strength -= 0.08

        return max(0.05, min(0.95, strength))

    def _pick_raise_amount(self, to_call, min_raise, pot):
        """Pick a disciplined raise increment above the current bet scaled by AI tier."""
        max_raise = max(0, self.chips - to_call)
        if max_raise < min_raise:
            return min_raise
        half_pot = max(min_raise, (pot + to_call) // 2)
        two_thirds = max(min_raise, int((pot + to_call) * 0.68))
        if self.tier == "Ultra":
            desired = random.choice([half_pot, two_thirds, min_raise])
        elif self.tier == "Master":
            desired = random.choice([min_raise, half_pot, two_thirds])
        elif self.tier == "Rookie":
            desired = min_raise
        else:
            desired = random.choice([min_raise, min_raise, half_pot])
        return max(min_raise, min(max_raise, desired))

    def choose_action(self, to_call, can_raise, min_raise, pot, board, opponent_all_in):
        """Return a tier-calibrated action using strength, pot odds, and stack pressure."""
        cfg = AI_TIER_SETTINGS.get(self.tier, AI_TIER_SETTINGS["Pro"])
        strength = self.estimate_strength(board)
        noise = cfg["noise"]
        perceived = max(0.0, min(1.0, strength + random.uniform(-noise, noise)))
        tightness = cfg["tightness"]
        aggression = cfg["aggression"]
        bluff = cfg["bluff"]

        if opponent_all_in or (to_call > 0 and to_call >= self.chips):
            if to_call == 0:
                return {"action": "check"}
            effective_call = min(to_call, self.chips)
            pot_odds = effective_call / max(1, pot + effective_call)
            stack_ratio = effective_call / max(1, self.chips)
            threshold = 0.36 + tightness + pot_odds * 0.42 + stack_ratio * 0.16
            if perceived >= threshold + 0.06:
                return {"action": "call"}
            if perceived >= threshold - 0.05 and random.random() < (0.25 if self.tier == "Ultra" else 0.34):
                return {"action": "call"}
            return {"action": "fold"}

        if to_call == 0:
            if can_raise:
                if perceived >= 0.70:
                    bet_chance = min(0.85, 0.58 * aggression)
                elif perceived >= 0.55:
                    bet_chance = min(0.60, 0.28 * aggression)
                elif perceived >= 0.44:
                    bet_chance = min(0.30, 0.10 * aggression)
                else:
                    bet_chance = bluff

                if random.random() < bet_chance:
                    return {
                        "action": "raise",
                        "amount": self._pick_raise_amount(0, min_raise, pot),
                    }
            return {"action": "check"}

        pot_odds = to_call / max(1, pot + to_call)
        stack_commit = to_call / max(1, self.chips)
        preflop_floor = (0.32 if len(board) == 0 else 0.26) + tightness
        required_strength = preflop_floor + pot_odds * 0.48 + stack_commit * 0.36

        if can_raise:
            heavy_action = stack_commit > 0.20 or to_call > min_raise * 2
            if perceived >= 0.78:
                raise_chance = min(0.75, (0.24 if heavy_action else 0.42) * aggression)
            elif perceived >= 0.65:
                raise_chance = min(0.45, (0.06 if heavy_action else 0.16) * aggression)
            elif perceived >= 0.55 and not heavy_action:
                raise_chance = min(0.25, 0.05 * aggression)
            else:
                raise_chance = (bluff * 0.5) if not heavy_action else 0.0

            if random.random() < raise_chance:
                return {
                    "action": "raise",
                    "amount": self._pick_raise_amount(to_call, min_raise, pot),
                }

        margin = perceived - required_strength
        if margin >= 0.07:
            fold_chance = 0.0
        elif margin >= -0.01:
            fold_chance = 0.35
        elif margin >= -0.08:
            fold_chance = 0.78
        else:
            fold_chance = 0.96

        if random.random() < fold_chance:
            return {"action": "fold"}
        return {"action": "call"}


MAX_COMPUTERS = 5


def build_side_pots(contributions, folded_flags):
    """Split player contributions into main and side pots with eligible contenders.

    Returns a list of dicts: [{"amount": int, "eligible": [player_index, ...]}, ...].
    Consecutive slices with identical eligible contenders are merged.
    """
    levels = sorted({amount for amount in contributions if amount > 0})
    if not levels:
        return []

    pots = []
    prev_level = 0
    for level in levels:
        slice_size = level - prev_level
        contributors = [i for i, amount in enumerate(contributions) if amount >= level]
        pot_amount = slice_size * len(contributors)
        eligible = [i for i in contributors if not folded_flags[i]]
        if pot_amount > 0 and eligible:
            if pots and pots[-1]["eligible"] == eligible:
                pots[-1]["amount"] += pot_amount
            else:
                pots.append({"amount": pot_amount, "eligible": eligible})
        prev_level = level
    return pots


def estimate_all_in_equities(players, board, contender_indices, samples=220):
    """Return win/equity percentages (0.0 to 100.0) for each contender in an all-in runout."""
    if not contender_indices:
        return {}
    if len(contender_indices) == 1:
        return {contender_indices[0]: 100.0}

    used_keys = {(card.rank, card.suit) for card in board}
    for idx in contender_indices:
        for card in players[idx].hole_cards:
            used_keys.add((card.rank, card.suit))

    remaining = [
        Card(rank, suit)
        for suit in SUITS
        for rank in range(2, 15)
        if (rank, suit) not in used_keys
    ]

    needed = max(0, 5 - len(board))
    shares = {idx: 0.0 for idx in contender_indices}
    total_trials = 0

    def score_board(full_board):
        nonlocal total_trials
        best_score = None
        winners = []
        for idx in contender_indices:
            score, _ = evaluate_best_hand(players[idx].hole_cards + full_board)
            if best_score is None or score > best_score:
                best_score = score
                winners = [idx]
            elif score == best_score:
                winners.append(idx)
        share = 1.0 / len(winners)
        for idx in winners:
            shares[idx] += share
        total_trials += 1

    if needed == 0:
        score_board(list(board))
    elif needed == 1:
        for card in remaining:
            score_board(list(board) + [card])
    else:
        trial_count = min(samples, 220)
        for _ in range(trial_count):
            drawn = random.sample(remaining, needed)
            score_board(list(board) + drawn)

    if total_trials == 0:
        equal = 100.0 / len(contender_indices)
        return {idx: equal for idx in contender_indices}

    return {idx: (shares[idx] / total_trials) * 100.0 for idx in contender_indices}


class TexasHoldemGame:
    """Manage a 2-to-6 player Texas Hold'em game (1 human + 1..5 computers)."""

    def __init__(
        self,
        starting_chips=500,
        small_blind=5,
        big_blind=10,
        num_computers=1,
        max_computers=MAX_COMPUTERS,
        opponents=None,
    ):
        if opponents is not None:
            num_computers = len(opponents)
        if num_computers < 1 or num_computers > max_computers:
            raise ValueError(f"num_computers must be between 1 and {max_computers}.")
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.max_computers = max_computers
        self.num_computers = num_computers

        self.players = [Player("You", starting_chips, is_human=True)]
        if opponents is not None:
            for profile in opponents:
                self.players.append(
                    ComputerPlayer(
                        profile["name"],
                        starting_chips,
                        tier=profile.get("tier", "Pro"),
                        tag=profile.get("tag", ""),
                    )
                )
        else:
            for i in range(1, num_computers + 1):
                name = "Computer" if num_computers == 1 else f"AI {i}"
                self.players.append(ComputerPlayer(name, starting_chips))

        n = len(self.players)
        self.button_index = random.randrange(n)
        self.deck = None
        self.board = []
        self.pot = 0
        self.round_bets = [0] * n
        self.hand_contributions = [0] * n
        self.folded = [False] * n
        self.eliminated = [False] * n

    def _active_in_match(self):
        return [i for i, elim in enumerate(self.eliminated) if not elim]

    def _contenders(self):
        return [
            i
            for i in range(len(self.players))
            if not self.eliminated[i] and not self.folded[i]
        ]

    def _next_seat(self, start_index, predicate):
        n = len(self.players)
        for offset in range(1, n + 1):
            idx = (start_index + offset) % n
            if predicate(idx):
                return idx
        return None

    def _other_player(self, player_index):
        if len(self.players) == 2:
            return 1 - player_index
        nxt = self._next_seat(
            player_index, lambda idx: not self.eliminated[idx] and not self.folded[idx]
        )
        return nxt if nxt is not None else player_index

    def _put_chips_in_pot(self, player_index, amount):
        player = self.players[player_index]
        actual_amount = player.take_bet(amount)
        self.pot += actual_amount
        self.round_bets[player_index] += actual_amount
        self.hand_contributions[player_index] += actual_amount
        return actual_amount

    def _post_blind(self, player_index, amount, blind_name):
        actual_amount = self._put_chips_in_pot(player_index, amount)
        player = self.players[player_index]
        print(f"{player.name} posts the {blind_name}: ${actual_amount}.")
        if player.chips == 0:
            print(f"{player.name} is all-in.")

    def _blind_positions(self):
        active = self._active_in_match()
        if len(active) <= 2:
            sb = self.button_index
            bb = self._next_seat(sb, lambda i: not self.eliminated[i])
            return sb, bb
        sb = self._next_seat(self.button_index, lambda i: not self.eliminated[i])
        bb = self._next_seat(sb, lambda i: not self.eliminated[i])
        return sb, bb

    def _deal_hole_cards(self):
        # Deal one card at a time clockwise starting left of the button.
        n = len(self.players)
        deal_order = []
        for offset in range(1, n + 1):
            idx = (self.button_index + offset) % n
            if not self.eliminated[idx]:
                deal_order.append(idx)
        for _ in range(2):
            for player_index in deal_order:
                self.players[player_index].hole_cards.append(self.deck.draw())

    def _show_table(self, reveal_computer=False):
        human = self.players[0]
        print("\n" + "=" * 54)
        status_parts = [f"{p.name}: ${p.chips}" for i, p in enumerate(self.players) if not self.eliminated[i]]
        print("  |  ".join(status_parts) + f"  |  Pot: ${self.pot}")
        board_text = "  ".join(f"[{card}]" for card in self.board) or "(no community cards yet)"
        print(f"Board: {board_text}")
        print(f"Your hand: [{human.hole_cards[0]}] [{human.hole_cards[1]}]")
        for i in range(1, len(self.players)):
            if self.eliminated[i]:
                continue
            comp = self.players[i]
            if reveal_computer and not self.folded[i]:
                print(f"{comp.name} hand: [{comp.hole_cards[0]}] [{comp.hole_cards[1]}]")
            elif self.folded[i]:
                print(f"{comp.name} hand: (folded)")
            else:
                print(f"{comp.name} hand: [??] [??]")
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
        can_act_others = [
            i for i in self._contenders() if i != player_index and self.players[i].chips > 0
        ]
        opponent_all_in = len(can_act_others) == 0

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

    def _refund_unmatched_bet(self, quiet=False):
        """Return any unmatched part of the current street's larger contribution."""
        if len(self.players) == 2:
            first_bet, second_bet = self.round_bets
            if first_bet == second_bet:
                return None

            higher_index = 0 if first_bet > second_bet else 1
            difference = abs(first_bet - second_bet)
            self.players[higher_index].chips += difference
            self.round_bets[higher_index] -= difference
            if self.hand_contributions[higher_index] >= difference:
                self.hand_contributions[higher_index] -= difference
            self.pot -= difference
            message = f"Uncalled bet of ${difference} returned to {self.players[higher_index].name}."
            if not quiet:
                print(message)
            return message

        contenders = self._contenders()
        if len(contenders) <= 1:
            return None
        max_bet = max(self.round_bets[i] for i in contenders)
        top_players = [i for i in contenders if self.round_bets[i] == max_bet]
        if len(top_players) != 1:
            return None

        top_idx = top_players[0]
        others_can_act = any(
            self.players[i].chips > 0 for i in contenders if i != top_idx
        )
        if others_can_act:
            return None

        second_bet = max(
            (self.round_bets[i] for i in contenders if i != top_idx),
            default=0,
        )
        difference = max_bet - second_bet
        if difference <= 0:
            return None

        self.players[top_idx].chips += difference
        self.round_bets[top_idx] -= difference
        if self.hand_contributions[top_idx] >= difference:
            self.hand_contributions[top_idx] -= difference
        self.pot -= difference
        message = f"Uncalled bet of ${difference} returned to {self.players[top_idx].name}."
        if not quiet:
            print(message)
        return message

    def _init_betting_round(self, first_actor):
        """Build the initial turn queue for a betting street."""
        contenders = self._contenders()
        if len(contenders) <= 1:
            return []

        can_act = [i for i in contenders if self.players[i].chips > 0]
        if not can_act:
            return []

        max_bet = max(self.round_bets[i] for i in contenders)
        if len(can_act) == 1:
            sole = can_act[0]
            return [sole] if self.round_bets[sole] < max_bet else []

        n = len(self.players)
        queue = []
        for offset in range(n):
            idx = (first_actor + offset) % n
            if idx in can_act:
                queue.append(idx)
        return queue

    def _next_pending_actor(self, pending):
        """Pop any player who has no legal decision left and return the next actor index or None."""
        contenders = self._contenders()
        if len(contenders) <= 1:
            pending.clear()
            return None

        max_bet = max((self.round_bets[i] for i in contenders), default=0)
        while pending:
            player_index = pending[0]
            if self.eliminated[player_index] or self.folded[player_index]:
                pending.pop(0)
                continue

            player = self.players[player_index]
            if player.chips == 0:
                pending.pop(0)
                continue

            other_can_act = any(
                i != player_index and self.players[i].chips > 0 for i in contenders
            )
            to_call = max(0, max_bet - self.round_bets[player_index])
            if not other_can_act and to_call == 0:
                pending.pop(0)
                continue

            return player_index
        return None

    def _rebuild_pending_after_raise(self, raiser_index):
        """Return clockwise queue of all other contenders who still have chips to respond."""
        n = len(self.players)
        queue = []
        for offset in range(1, n):
            idx = (raiser_index + offset) % n
            if not self.eliminated[idx] and not self.folded[idx] and self.players[idx].chips > 0:
                queue.append(idx)
        return queue

    def _apply_betting_action(self, player_index, action, min_raise, pending):
        """Apply one validated player action and return updated betting state."""
        player = self.players[player_index]
        contenders = self._contenders()
        max_bet = max((self.round_bets[i] for i in contenders), default=0)
        to_call = max(0, max_bet - self.round_bets[player_index])
        action_name = action["action"]
        logs = []
        summary = action_name.upper()

        if action_name == "fold":
            self.folded[player_index] = True
            logs.append(f"{player.name} folds.")
            remaining = self._contenders()
            if len(remaining) == 1:
                refund_msg = self._refund_unmatched_bet(quiet=True)
                if refund_msg:
                    logs.append(refund_msg)
                return {
                    "folded_winner": remaining[0],
                    "min_raise": min_raise,
                    "pending": [],
                    "logs": logs,
                    "summary": "FOLD",
                }
            return {
                "folded_winner": None,
                "min_raise": min_raise,
                "pending": pending,
                "logs": logs,
                "summary": "FOLD",
            }

        if action_name == "check":
            logs.append(f"{player.name} checks.")
            summary = "CHECK"

        elif action_name == "call":
            amount = self._put_chips_in_pot(player_index, to_call)
            if amount == to_call:
                logs.append(f"{player.name} calls ${amount}.")
                summary = f"CALL ${amount}"
            else:
                logs.append(f"{player.name} calls all-in with the remaining ${amount}.")
                summary = f"ALL-IN ${amount}"

        elif action_name == "raise":
            old_current_bet = max_bet
            target_bet = old_current_bet + action["amount"]
            amount_to_put_in = target_bet - self.round_bets[player_index]
            self._put_chips_in_pot(player_index, amount_to_put_in)
            new_current_bet = max(self.round_bets[i] for i in self._contenders())
            raise_size = new_current_bet - old_current_bet
            if raise_size >= min_raise:
                min_raise = raise_size
            if old_current_bet == 0:
                logs.append(f"{player.name} bets ${new_current_bet}.")
                summary = f"BET ${new_current_bet}"
            else:
                logs.append(f"{player.name} raises to ${new_current_bet} (+${raise_size}).")
                summary = f"RAISE ${new_current_bet}"
            if player.chips == 0:
                logs.append(f"{player.name} is all-in.")
                summary = f"ALL-IN ${new_current_bet}"
            pending = self._rebuild_pending_after_raise(player_index)

        elif action_name == "all_in":
            old_current_bet = max_bet
            amount = self._put_chips_in_pot(player_index, player.chips)
            new_current_bet = max(self.round_bets[i] for i in self._contenders())
            logs.append(f"{player.name} goes all-in for ${amount}.")
            summary = f"ALL-IN ${amount}"
            if new_current_bet > old_current_bet:
                raise_size = new_current_bet - old_current_bet
                if raise_size >= min_raise:
                    min_raise = raise_size
                pending = [
                    idx
                    for idx in self._rebuild_pending_after_raise(player_index)
                    if self.round_bets[idx] < new_current_bet
                ]

        return {
            "folded_winner": None,
            "min_raise": min_raise,
            "pending": pending,
            "logs": logs,
            "summary": summary,
        }

    def _run_betting_round(self, first_actor):
        """Run one street of betting. Return the sole remaining player if all others folded."""
        min_raise = self.big_blind
        pending = self._init_betting_round(first_actor)

        while True:
            player_index = self._next_pending_actor(pending)
            if player_index is None:
                if any(self.players[i].chips == 0 for i in self._contenders()):
                    self._refund_unmatched_bet()
                break

            pending.pop(0)
            player = self.players[player_index]
            contenders = self._contenders()
            max_bet = max((self.round_bets[i] for i in contenders), default=0)
            to_call = max(0, max_bet - self.round_bets[player_index])
            others_can_act = any(
                i != player_index and self.players[i].chips > 0 for i in contenders
            )
            can_raise = others_can_act and player.chips >= to_call + min_raise
            action = self._ask_for_action(
                player_index, to_call, can_raise, min_raise
            )
            result = self._apply_betting_action(player_index, action, min_raise, pending)
            for line in result["logs"]:
                print(line)
            if result["folded_winner"] is not None:
                return result["folded_winner"]

            min_raise = result["min_raise"]
            pending = result["pending"]

            if not pending:
                if any(self.players[i].chips == 0 for i in self._contenders()):
                    self._refund_unmatched_bet()
                break

        return None

    def _deal_flop(self, quiet=False):
        self.deck.burn()
        self.board.extend([self.deck.draw(), self.deck.draw(), self.deck.draw()])
        if not quiet:
            print("\nFlop: " + "  ".join(f"[{card}]" for card in self.board))

    def _deal_turn_or_river(self, street_name, quiet=False):
        self.deck.burn()
        self.board.append(self.deck.draw())
        if not quiet:
            print(f"\n{street_name}: [{self.board[-1]}]")

    def _award_pot(self, winner_index, quiet=False):
        winner = self.players[winner_index]
        pot_won = self.pot
        winner.chips += pot_won
        if not quiet:
            print(f"{winner.name} wins the pot of ${pot_won}.")
        self.pot = 0
        return pot_won

    def _build_active_pots(self):
        """Build side pots from hand contributions, falling back to single pot if edited directly."""
        contenders = self._contenders()
        if sum(self.hand_contributions) == self.pot and self.pot > 0:
            pots = build_side_pots(self.hand_contributions, self.folded)
            if pots:
                return pots
        return [{"amount": self.pot, "eligible": contenders}] if self.pot > 0 else []

    def _settle_pots_on_board(self, board, pots):
        """Evaluate contenders on a 5-card board and distribute pot amounts."""
        contenders = self._contenders()
        player_results = {}
        for idx in contenders:
            score, best_five = evaluate_best_hand(self.players[idx].hole_cards + board)
            player_results[idx] = {
                "score": score,
                "best_five": best_five,
                "hand_name": HAND_NAMES[score[0]],
            }

        pot_awards = []
        total_by_player = {idx: 0 for idx in range(len(self.players))}
        n = len(self.players)

        for pot_idx, pot_info in enumerate(pots):
            amount = pot_info["amount"]
            eligible = [idx for idx in pot_info["eligible"] if idx in player_results]
            if not eligible or amount <= 0:
                continue

            best_score = max(player_results[idx]["score"] for idx in eligible)
            winners = [idx for idx in eligible if player_results[idx]["score"] == best_score]

            # Order winners clockwise from button for standard odd-chip rule
            ordered_winners = []
            for offset in range(1, n + 1):
                seat = (self.button_index + offset) % n
                if seat in winners:
                    ordered_winners.append(seat)

            share = amount // len(ordered_winners)
            remainder = amount % len(ordered_winners)
            for pos, w_idx in enumerate(ordered_winners):
                gain = share + (1 if pos < remainder else 0)
                self.players[w_idx].chips += gain
                total_by_player[w_idx] += gain

            pot_awards.append(
                {
                    "pot_name": "Main Pot" if pot_idx == 0 else f"Side Pot {pot_idx}",
                    "amount": amount,
                    "winners": ordered_winners,
                    "share": share,
                }
            )

        return {
            "board": list(board),
            "player_results": player_results,
            "pot_awards": pot_awards,
            "total_by_player": total_by_player,
        }

    def _resolve_showdown(self, quiet=False):
        """Evaluate hands at showdown, award main/side pots, and return structured results."""
        refund_msg = self._refund_unmatched_bet(quiet=quiet)
        pot_total = self.pot
        pots = self._build_active_pots()
        board_res = self._settle_pots_on_board(self.board, pots)
        self.pot = 0

        # Backward-compatible list indexed by seat (None for folded/eliminated)
        results_list = [board_res["player_results"].get(i) for i in range(len(self.players))]
        main_award = board_res["pot_awards"][0] if board_res["pot_awards"] else None
        if main_award and len(main_award["winners"]) == 1:
            winner_index = main_award["winners"][0]
            half_pot = pot_total
            odd_chip = 0
        else:
            winner_index = None
            half_pot = main_award["share"] if main_award else 0
            odd_chip = pot_total % 2 if len(self._contenders()) == 2 else 0

        return {
            "refund_log": refund_msg,
            "player_results": results_list,
            "pot_awards": board_res["pot_awards"],
            "total_by_player": board_res["total_by_player"],
            "winner_index": winner_index,
            "pot_awarded": pot_total,
            "half_pot": half_pot,
            "odd_chip": odd_chip,
        }

    def _showdown(self):
        self._show_table(reveal_computer=True)
        showdown = self._resolve_showdown(quiet=True)
        if showdown["refund_log"]:
            print(showdown["refund_log"])
        for idx, (player, result) in enumerate(zip(self.players, showdown["player_results"])):
            if result is None:
                continue
            cards_text = " ".join(f"[{card}]" for card in result["best_five"])
            print(f"{player.name}: {result['hand_name']}; best five cards: {cards_text}")

        for award in showdown["pot_awards"]:
            winner_names = ", ".join(self.players[i].name for i in award["winners"])
            if len(award["winners"]) == 1:
                print(f"{winner_names} wins {award['pot_name']} of ${award['amount']}.")
            else:
                print(f"Tie for {award['pot_name']} (${award['amount']}) between {winner_names}.")

    def play_hand(self):
        """Deal and play a single hand. Returns True if everyone else folded."""
        self.deck = Deck()
        self.board = []
        self.pot = 0
        n = len(self.players)
        self.round_bets = [0] * n
        self.hand_contributions = [0] * n
        self.folded = [self.eliminated[i] for i in range(n)]
        for player in self.players:
            player.hole_cards = []

        small_blind_index, big_blind_index = self._blind_positions()
        self._deal_hole_cards()
        print("\n" + "#" * 54)
        print(
            f"Button: {self.players[self.button_index].name}; "
            f"SB: {self.players[small_blind_index].name}; BB: {self.players[big_blind_index].name}"
        )
        self._post_blind(small_blind_index, self.small_blind, "small blind")
        self._post_blind(big_blind_index, self.big_blind, "big blind")

        active_count = len(self._active_in_match())
        pre_first = small_blind_index if active_count <= 2 else self._next_seat(
            big_blind_index, lambda i: not self.eliminated[i]
        )
        folded_winner = self._run_betting_round(pre_first)
        if folded_winner is not None:
            self._award_pot(folded_winner)
            return True

        can_act = [i for i in self._contenders() if self.players[i].chips > 0]
        if len(can_act) <= 1:
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
            self.round_bets = [0] * n
            first_actor = self._next_seat(
                self.button_index,
                lambda i: not self.eliminated[i] and not self.folded[i] and self.players[i].chips > 0,
            )
            if first_actor is not None:
                folded_winner = self._run_betting_round(first_actor)
                if folded_winner is not None:
                    self._award_pot(folded_winner)
                    return True

            can_act = [i for i in self._contenders() if self.players[i].chips > 0]
            if len(can_act) <= 1:
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
        print(f"Texas Hold'em: You vs. {self.num_computers} Computer(s)")
        print(f"Starting chips: ${self.players[0].chips} each; blinds: ${self.small_blind}/${self.big_blind}")
        print("Choose an action by entering its menu number. Press Enter for the next hand or type q to quit.")

        hand_number = 1
        while self.players[0].chips > 0 and any(p.chips > 0 for p in self.players[1:]):
            print(f"\nHand {hand_number}")
            self.play_hand()
            for i, p in enumerate(self.players):
                if p.chips <= 0:
                    self.eliminated[i] = True
            if self.players[0].chips <= 0 or all(self.eliminated[1:]):
                break

            nxt_btn = self._next_seat(self.button_index, lambda i: not self.eliminated[i])
            if nxt_btn is not None:
                self.button_index = nxt_btn
            hand_number += 1

            answer = input("Press Enter for the next hand, or type q to quit: ").strip().lower()
            if answer == "q":
                break

        print("\nGame over.")
        for i, p in enumerate(self.players):
            print(f"{p.name}: ${p.chips}")


class TexasHoldemSession:
    """State-driven wrapper around TexasHoldemGame for graphical interfaces."""

    def __init__(
        self,
        starting_chips=500,
        small_blind=5,
        big_blind=10,
        num_computers=1,
        max_computers=MAX_COMPUTERS,
        opponents=None,
    ):
        self.starting_chips = starting_chips
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.max_computers = max_computers
        self.opponents = list(opponents) if opponents is not None else None
        if self.opponents is not None:
            self.num_computers = max(1, min(max_computers, len(self.opponents)))
        else:
            self.num_computers = max(1, min(max_computers, num_computers))
        self.game = None
        self.phase = "idle"
        self.street = "pre_flop"
        self.hand_number = 0
        self.min_raise = big_blind
        self.pending = []
        self.last_actions = []
        self.action_log = []
        self.winner_index = None
        self.win_reason = None
        self.showdown_result = None
        self.pot_awarded = 0
        self.equities = {}
        self.run_count = 1
        self.run_boards = []
        self.run_results = []
        self.active_run_index = 0
        self.run_start_board_len = 0
        self.runout_status = ""
        self.last_full_bet = 0
        self.acted_since_full_raise = set()
        self.refund_logs = []
        self.won_this_hand = {}
        self.start_new_match()

    def _append_log(self, message):
        self.action_log.append(message)
        if len(self.action_log) > 60:
            self.action_log = self.action_log[-60:]

    def start_new_match(
        self,
        num_computers=None,
        starting_chips=None,
        small_blind=None,
        big_blind=None,
        opponents=None,
    ):
        """Reset all chip stacks with optional updated table settings and begin hand #1."""
        if opponents is not None:
            self.opponents = list(opponents)[: self.max_computers]
            self.num_computers = max(1, min(self.max_computers, len(self.opponents)))
        elif num_computers is not None:
            self.num_computers = max(1, min(self.max_computers, int(num_computers)))
            if self.opponents is not None and len(self.opponents) != self.num_computers:
                self.opponents = None
        if starting_chips is not None:
            self.starting_chips = int(starting_chips)
        if small_blind is not None:
            self.small_blind = int(small_blind)
        if big_blind is not None:
            self.big_blind = int(big_blind)

        self.game = TexasHoldemGame(
            starting_chips=self.starting_chips,
            small_blind=self.small_blind,
            big_blind=self.big_blind,
            num_computers=self.num_computers,
            max_computers=self.max_computers,
            opponents=self.opponents,
        )
        self.hand_number = 0
        self.action_log = []
        self.start_next_hand()

    def start_next_hand(self):
        """Deal the next hand, eliminating busted players and rotating the button."""
        for i, player in enumerate(self.game.players):
            if player.chips <= 0:
                self.game.eliminated[i] = True

        if self.game.eliminated[0] or all(self.game.eliminated[1:]):
            self.phase = "match_over"
            return False

        if self.hand_number > 0:
            nxt_btn = self.game._next_seat(
                self.game.button_index, lambda i: not self.game.eliminated[i]
            )
            if nxt_btn is not None:
                self.game.button_index = nxt_btn

        self.hand_number += 1
        n = len(self.game.players)
        self.game.deck = Deck()
        self.game.board = []
        self.game.pot = 0
        self.game.round_bets = [0] * n
        self.game.hand_contributions = [0] * n
        self.game.folded = [self.game.eliminated[i] for i in range(n)]
        for player in self.game.players:
            player.hole_cards = []

        self.street = "pre_flop"
        self.min_raise = self.game.big_blind
        self.last_actions = [
            "OUT" if self.game.eliminated[i] else "" for i in range(n)
        ]
        self.winner_index = None
        self.win_reason = None
        self.showdown_result = None
        self.pot_awarded = 0
        self.equities = {}
        self.run_count = 1
        self.run_boards = []
        self.run_results = []
        self.active_run_index = 0
        self.run_start_board_len = 0
        self.runout_status = ""
        self.last_full_bet = self.game.big_blind
        self.acted_since_full_raise = set()
        self.refund_logs = []
        self.won_this_hand = {i: 0 for i in range(n)}

        self.game._deal_hole_cards()
        small_blind_index, big_blind_index = self.game._blind_positions()

        self._append_log(f"--- Hand #{self.hand_number} ---")
        sb_amount = self.game._put_chips_in_pot(small_blind_index, self.game.small_blind)
        bb_amount = self.game._put_chips_in_pot(big_blind_index, self.game.big_blind)

        self.last_actions[small_blind_index] = f"SB ${sb_amount}"
        self.last_actions[big_blind_index] = f"BB ${bb_amount}"
        self._append_log(f"{self.game.players[small_blind_index].name} posts SB ${sb_amount}.")
        self._append_log(f"{self.game.players[big_blind_index].name} posts BB ${bb_amount}.")

        active_count = len(self.game._active_in_match())
        first_actor = (
            small_blind_index
            if active_count <= 2
            else self.game._next_seat(big_blind_index, lambda i: not self.game.eliminated[i])
        )
        self.pending = self.game._init_betting_round(first_actor)
        self._advance_state()
        return True

    def _update_equities(self, board_for_calc=None):
        board = self.game.board if board_for_calc is None else board_for_calc
        contenders = self.game._contenders()
        self.equities = estimate_all_in_equities(self.game.players, board, contenders)

    def _complete_showdown(self):
        self.street = "showdown"
        if self.run_count == 2 and len(self.run_boards) == 2:
            self._complete_run_it_twice_showdown()
            return

        showdown = self.game._resolve_showdown(quiet=True)
        self.showdown_result = showdown
        self.winner_index = showdown["winner_index"]
        self.win_reason = "showdown"
        self.pot_awarded = showdown["pot_awarded"]
        self.won_this_hand = dict(showdown["total_by_player"])
        self.phase = "hand_over"
        self._update_equities(self.game.board)

        if showdown["refund_log"]:
            self.refund_logs.append(showdown["refund_log"])
            self._append_log(showdown["refund_log"])
        for idx, result in enumerate(showdown["player_results"]):
            if result is not None:
                self._append_log(f"{self.game.players[idx].name}: {result['hand_name']}")
        for award in showdown["pot_awards"]:
            winner_names = ", ".join(self.game.players[i].name for i in award["winners"])
            if len(award["winners"]) == 1:
                w_idx = award["winners"][0]
                verb = "win" if w_idx == 0 else "wins"
                self._append_log(f"{winner_names} {verb} {award['pot_name']} (${award['amount']})!")
            else:
                self._append_log(f"Split {award['pot_name']} (${award['amount']}): {winner_names}.")

    def _complete_run_it_twice_showdown(self):
        refund_msg = self.game._refund_unmatched_bet(quiet=True)
        pot_total = self.game.pot
        pots = self.game._build_active_pots()

        # Split each pot into Run 1 (gets odd chip) and Run 2
        pots_run1 = []
        pots_run2 = []
        for pot_info in pots:
            amt = pot_info["amount"]
            half1 = amt // 2 + (amt % 2)
            half2 = amt // 2
            if half1 > 0:
                pots_run1.append({"amount": half1, "eligible": pot_info["eligible"]})
            if half2 > 0:
                pots_run2.append({"amount": half2, "eligible": pot_info["eligible"]})

        res1 = self.game._settle_pots_on_board(self.run_boards[0], pots_run1)
        res2 = self.game._settle_pots_on_board(self.run_boards[1], pots_run2)
        self.game.pot = 0

        total_by_player = {
            i: res1["total_by_player"][i] + res2["total_by_player"][i]
            for i in range(len(self.game.players))
        }
        top_gain = max(total_by_player.values(), default=0)
        top_players = [i for i, g in total_by_player.items() if g == top_gain and g > 0]

        self.run_results = [res1, res2]
        contenders = self.game._contenders()
        eq1 = estimate_all_in_equities(self.game.players, self.run_boards[0], contenders)
        eq2 = estimate_all_in_equities(self.game.players, self.run_boards[1], contenders)
        self.equities = {
            idx: 0.5 * (eq1.get(idx, 0.0) + eq2.get(idx, 0.0)) for idx in contenders
        }
        self.winner_index = top_players[0] if len(top_players) == 1 else None
        self.win_reason = "showdown"
        self.pot_awarded = pot_total
        self.won_this_hand = dict(total_by_player)
        self.phase = "hand_over"
        self.showdown_result = {
            "refund_log": refund_msg,
            "player_results": [res1["player_results"].get(i) for i in range(len(self.game.players))],
            "pot_awards": res1["pot_awards"] + res2["pot_awards"],
            "total_by_player": total_by_player,
            "winner_index": self.winner_index,
            "pot_awarded": pot_total,
            "run_it_twice": True,
            "run_results": [res1, res2],
        }

        if refund_msg:
            self.refund_logs.append(refund_msg)
            self._append_log(refund_msg)
        for run_idx, res in enumerate((res1, res2), start=1):
            for award in res["pot_awards"]:
                w_names = ", ".join(self.game.players[i].name for i in award["winners"])
                self._append_log(f"Run {run_idx} ({award['pot_name']} ${award['amount']}): {w_names}")

    def _advance_street(self):
        if self.street == "pre_flop":
            self.game._deal_flop(quiet=True)
            self.street = "flop"
            self._append_log("Flop: " + " ".join(str(card) for card in self.game.board))
        elif self.street == "flop":
            self.game._deal_turn_or_river("Turn", quiet=True)
            self.street = "turn"
            self._append_log(f"Turn: {self.game.board[-1]}")
        elif self.street == "turn":
            self.game._deal_turn_or_river("River", quiet=True)
            self.street = "river"
            self._append_log(f"River: {self.game.board[-1]}")

        n = len(self.game.players)
        self.game.round_bets = [0] * n
        self.min_raise = self.game.big_blind
        self.last_full_bet = 0
        self.acted_since_full_raise = set()
        self.last_actions = [
            "OUT" if self.game.eliminated[i] else ("FOLD" if self.game.folded[i] else "")
            for i in range(n)
        ]
        first_actor = self.game._next_seat(
            self.game.button_index,
            lambda i: not self.game.eliminated[i] and not self.game.folded[i] and self.game.players[i].chips > 0,
        )
        self.pending = self.game._init_betting_round(first_actor) if first_actor is not None else []

    def _advance_state(self):
        while True:
            actor = self.game._next_pending_actor(self.pending)
            if actor is not None:
                self.phase = "waiting_human" if actor == 0 else "computer_turn"
                return

            contenders = self.game._contenders()
            if len(contenders) == 1:
                winner = contenders[0]
                refund_msg = self.game._refund_unmatched_bet(quiet=True)
                if refund_msg:
                    self.refund_logs.append(refund_msg)
                    self._append_log(refund_msg)
                self.pot_awarded = self.game._award_pot(winner, quiet=True)
                self.won_this_hand = {i: (self.pot_awarded if i == winner else 0) for i in range(len(self.game.players))}
                self.winner_index = winner
                self.win_reason = "fold"
                self.phase = "hand_over"
                return

            if any(self.game.players[i].chips == 0 for i in contenders):
                refund_msg = self.game._refund_unmatched_bet(quiet=True)
                if refund_msg:
                    self.refund_logs.append(refund_msg)
                    self._append_log(refund_msg)

            can_act = [i for i in contenders if self.game.players[i].chips > 0]
            if len(can_act) <= 1 and len(self.game.board) < 5:
                self._update_equities(self.game.board)
                # Offer Run It Once vs Run It Twice when human is still in the all-in pot
                if not self.game.folded[0] and not self.game.eliminated[0]:
                    self.phase = "choose_run_count"
                else:
                    self.run_count = 1
                    self.phase = "reveal_board"
                return

            if self.street == "river" or len(self.game.board) == 5:
                self._complete_showdown()
                return

            self._advance_street()

    def choose_run_count(self, count):
        """Select 1 (Run Once) or 2 (Run It Twice) when all-in before the river."""
        if self.phase != "choose_run_count":
            raise RuntimeError("Not waiting for run count selection.")
        if count not in (1, 2):
            raise ValueError("Run count must be 1 or 2.")

        self.run_count = count
        self.active_run_index = 0
        self.run_start_board_len = len(self.game.board)
        if count == 2:
            self.run_boards = [list(self.game.board), list(self.game.board)]
            self.runout_status = "RUN 1 starting — dealing one card at a time..."
            self._append_log("All-in runout: Running It Twice (Run 1, then Run 2)!")
        else:
            self.run_boards = []
            self.runout_status = "All-in runout — dealing one card at a time..."
            self._append_log("All-in runout: Running Once (1x).")

        self.phase = "reveal_board"
        self._update_equities(self.game.board)

    def _deal_single_runout_card(self, target_board):
        """Burn before Flop/Turn/River when appropriate and deal 1 card into target_board."""
        current_len = len(target_board)
        if current_len in (0, 3, 4) and len(self.game.deck.cards) > 1:
            self.game.deck.burn()
        card = self.game.deck.draw()
        target_board.append(card)
        new_len = len(target_board)
        if new_len <= 3:
            self.street = "flop"
            card_tag = f"Flop {new_len}/3"
        elif new_len == 4:
            self.street = "turn"
            card_tag = "Turn"
        else:
            self.street = "river"
            card_tag = "River"
        return card, new_len, card_tag

    def _preview_board_winner_text(self, full_board):
        """Return a short summary of who wins a completed 5-card board."""
        contenders = self.game._contenders()
        best_score = None
        winners = []
        best_name = ""
        for idx in contenders:
            score, _ = evaluate_best_hand(self.game.players[idx].hole_cards + full_board)
            if best_score is None or score > best_score:
                best_score = score
                winners = [idx]
                best_name = HAND_NAMES[score[0]]
            elif score == best_score:
                winners.append(idx)
        names = ", ".join(self.game.players[i].name for i in winners)
        return f"{names} ({best_name})"

    def step_reveal_board(self):
        """Deal one card at a time during an all-in runout (Run 1 completely, then Run 2)."""
        if self.phase == "choose_run_count":
            self.choose_run_count(1)
            return

        if self.phase != "reveal_board":
            return

        if self.run_count == 2:
            if len(self.run_boards[0]) < 5:
                self.active_run_index = 0
                card, new_len, card_tag = self._deal_single_runout_card(self.run_boards[0])
                self._append_log(f"Run 1 {card_tag}: {card}")
                self.game.board = list(self.run_boards[0])
                self._update_equities(self.run_boards[0])
                if new_len == 5:
                    winner_text = self._preview_board_winner_text(self.run_boards[0])
                    self.runout_status = f"RUN 1: {winner_text}  •  Starting RUN 2..."
                else:
                    next_tag = "River" if new_len == 4 else ("Turn" if new_len == 3 else f"Flop {new_len + 1}/3")
                    self.runout_status = f"RUN 1 ({card_tag}: {card})  •  Next: {next_tag}..."
                return

            if len(self.run_boards[1]) < 5:
                self.active_run_index = 1
                card, new_len, card_tag = self._deal_single_runout_card(self.run_boards[1])
                self._append_log(f"Run 2 {card_tag}: {card}")
                self.game.board = list(self.run_boards[1])
                self._update_equities(self.run_boards[1])
                if new_len == 5:
                    self.runout_status = ""
                    self._complete_showdown()
                else:
                    next_tag = "River" if new_len == 4 else ("Turn" if new_len == 3 else f"Flop {new_len + 1}/3")
                    self.runout_status = f"RUN 2 ({card_tag}: {card})  •  Next: {next_tag}..."
                return

            self._complete_showdown()
            return

        card, new_len, card_tag = self._deal_single_runout_card(self.game.board)
        self._append_log(f"{card_tag}: {card}")
        self._update_equities(self.game.board)
        if new_len == 5:
            self.runout_status = ""
            self._complete_showdown()
        else:
            next_tag = "River" if new_len == 4 else ("Turn" if new_len == 3 else f"Flop {new_len + 1}/3")
            self.runout_status = f"{card_tag}: {card}  •  Revealing {next_tag}..."

    def get_legal_human_actions(self):
        """Return legal choices and bet bounds for the human player (WSOP/TDA rules)."""
        human = self.game.players[0]
        contenders = self.game._contenders()
        max_bet = max((self.game.round_bets[i] for i in contenders), default=0)
        human_bet = self.game.round_bets[0]
        to_call = max(0, max_bet - human_bet)
        others_can_act = any(i != 0 and self.game.players[i].chips > 0 for i in contenders)
        reopen_allowed = 0 not in self.acted_since_full_raise
        can_raise = (
            reopen_allowed
            and others_can_act
            and human.chips >= to_call + self.min_raise
        )
        max_raise = max(0, human.chips - to_call)
        min_total_bet = max_bet + self.min_raise
        max_total_bet = human_bet + human.chips
        can_all_in = (
            reopen_allowed
            and others_can_act
            and human.chips > 0
            and (to_call == 0 or human.chips > to_call)
        )
        return {
            "can_fold": to_call > 0,
            "can_check": to_call == 0,
            "to_call": to_call,
            "call_amount": min(to_call, human.chips),
            "current_bet": max_bet,
            "human_bet": human_bet,
            "is_bet": max_bet == 0,
            "can_raise": can_raise,
            "min_raise": self.min_raise,
            "max_raise": max_raise,
            "min_total_bet": min_total_bet,
            "max_total_bet": max_total_bet,
            "can_all_in": can_all_in,
            "all_in_amount": human.chips,
        }

    def _apply_action_and_advance(self, player_index, action):
        old_full_bet = self.last_full_bet
        old_min_raise = self.min_raise
        result = self.game._apply_betting_action(
            player_index, action, self.min_raise, self.pending
        )
        self.last_actions[player_index] = result["summary"]
        for line in result["logs"]:
            self._append_log(line)
            if line.startswith("Uncalled bet of"):
                self.refund_logs.append(line)

        if result["folded_winner"] is not None:
            winner = result["folded_winner"]
            self.pot_awarded = self.game._award_pot(winner, quiet=True)
            self.won_this_hand = {i: (self.pot_awarded if i == winner else 0) for i in range(len(self.game.players))}
            self.winner_index = winner
            self.win_reason = "fold"
            self.phase = "hand_over"
            winner_name = self.game.players[winner].name
            verb = "win" if winner == 0 else "wins"
            self._append_log(f"{winner_name} {verb} ${self.pot_awarded}!")
            return

        contenders = self.game._contenders()
        new_max_bet = max((self.game.round_bets[i] for i in contenders), default=0)
        # WSOP/TDA rule: only a full raise (increment >= min_raise from last_full_bet) reopens betting
        if new_max_bet - old_full_bet >= old_min_raise:
            self.min_raise = max(result["min_raise"], new_max_bet - old_full_bet)
            self.last_full_bet = new_max_bet
            self.acted_since_full_raise = {player_index}
        else:
            self.min_raise = result["min_raise"]
            self.acted_since_full_raise.add(player_index)

        self.pending = result["pending"]
        self._advance_state()

    def submit_human_action(self, action):
        """Apply a human action from the UI and advance the hand state."""
        if self.phase != "waiting_human":
            raise RuntimeError("Not waiting for human action.")

        legal = self.get_legal_human_actions()
        action_name = action.get("action")
        if action_name == "fold" and not legal["can_fold"]:
            raise ValueError("Cannot fold when there is nothing to call.")
        if action_name == "check" and not legal["can_check"]:
            raise ValueError("Cannot check when facing a bet.")
        if action_name == "call" and legal["to_call"] <= 0:
            raise ValueError("Nothing to call.")
        if action_name == "raise":
            if not legal["can_raise"]:
                raise ValueError("Raising is not allowed right now.")
            amount = int(action.get("amount", 0))
            if amount < legal["min_raise"] or amount > legal["max_raise"]:
                raise ValueError("Raise amount out of bounds.")
            action = {"action": "raise", "amount": amount}
        if action_name == "all_in" and not legal["can_all_in"]:
            raise ValueError("All-in is not allowed right now.")

        self.pending.pop(0)
        self._apply_action_and_advance(0, action)

    def step_computer_turn(self):
        """Let the next computer opponent take one action and advance the hand state."""
        if self.phase != "computer_turn":
            raise RuntimeError("Not a computer's turn.")

        comp_index = self.pending.pop(0)
        computer = self.game.players[comp_index]
        contenders = self.game._contenders()
        max_bet = max((self.game.round_bets[i] for i in contenders), default=0)
        to_call = max(0, max_bet - self.game.round_bets[comp_index])
        others_can_act = any(
            i != comp_index and self.game.players[i].chips > 0 for i in contenders
        )
        opponent_all_in = not others_can_act
        reopen_allowed = comp_index not in self.acted_since_full_raise
        can_raise = (
            reopen_allowed
            and others_can_act
            and computer.chips >= to_call + self.min_raise
        )
        action = computer.choose_action(
            to_call,
            can_raise,
            self.min_raise,
            self.game.pot,
            self.game.board,
            opponent_all_in,
        )
        self._apply_action_and_advance(comp_index, action)

    def get_human_best_hand_name(self):
        """Return a live label for the human player's current hand."""
        human = self.game.players[0]
        if self.game.eliminated[0]:
            return "Eliminated"
        if self.game.folded[0]:
            return "Folded"
        if len(human.hole_cards) < 2:
            return ""
        if len(self.game.board) >= 3:
            score, _ = evaluate_best_hand(human.hole_cards + self.game.board)
            return HAND_NAMES[score[0]]

        first, second = human.hole_cards
        if first.rank == second.rank:
            return "Pocket Pair"
        if first.suit == second.suit:
            return "Suited Hand"
        return "High Card"

    @staticmethod
    def _serialize_card(card):
        return [card.rank, card.suit]

    @classmethod
    def _serialize_player_eval(cls, res):
        if res is None:
            return None
        return {
            "score": list(res["score"]),
            "best_five": [cls._serialize_card(c) for c in res["best_five"]],
            "hand_name": res["hand_name"],
        }

    @classmethod
    def _deserialize_player_eval(cls, data, get_card):
        if data is None:
            return None
        return {
            "score": tuple(data["score"]),
            "best_five": [get_card(r, s) for r, s in data["best_five"]],
            "hand_name": data["hand_name"],
        }

    @classmethod
    def _serialize_board_result(cls, res):
        return {
            "board": [cls._serialize_card(c) for c in res["board"]],
            "player_results": {
                str(idx): cls._serialize_player_eval(val)
                for idx, val in res["player_results"].items()
            },
            "pot_awards": [
                {
                    "pot_name": a["pot_name"],
                    "amount": int(a["amount"]),
                    "winners": [int(w) for w in a["winners"]],
                    "share": int(a["share"]),
                }
                for a in res["pot_awards"]
            ],
            "total_by_player": {
                str(idx): int(amt) for idx, amt in res["total_by_player"].items()
            },
        }

    @classmethod
    def _deserialize_board_result(cls, data, get_card):
        return {
            "board": [get_card(r, s) for r, s in data["board"]],
            "player_results": {
                int(idx): cls._deserialize_player_eval(val, get_card)
                for idx, val in data["player_results"].items()
            },
            "pot_awards": [
                {
                    "pot_name": a["pot_name"],
                    "amount": int(a["amount"]),
                    "winners": [int(w) for w in a["winners"]],
                    "share": int(a["share"]),
                }
                for a in data["pot_awards"]
            ],
            "total_by_player": {
                int(idx): int(amt) for idx, amt in data["total_by_player"].items()
            },
        }

    def to_dict(self):
        """Serialize full match and hand state into a JSON-compatible dictionary."""
        players_data = []
        for p in self.game.players:
            players_data.append(
                {
                    "name": p.name,
                    "chips": int(p.chips),
                    "is_human": bool(p.is_human),
                    "tier": getattr(p, "tier", "Pro"),
                    "tag": getattr(p, "tag", ""),
                    "hole_cards": [self._serialize_card(c) for c in p.hole_cards],
                }
            )

        run_results_data = [
            self._serialize_board_result(res) for res in self.run_results
        ]

        showdown_data = None
        if self.showdown_result is not None:
            sr = self.showdown_result
            showdown_data = {
                "refund_log": sr.get("refund_log"),
                "player_results": [
                    self._serialize_player_eval(item)
                    for item in sr.get("player_results", [])
                ],
                "pot_awards": [
                    {
                        "pot_name": a["pot_name"],
                        "amount": int(a["amount"]),
                        "winners": [int(w) for w in a["winners"]],
                        "share": int(a["share"]),
                    }
                    for a in sr.get("pot_awards", [])
                ],
                "total_by_player": {
                    str(idx): int(amt)
                    for idx, amt in sr.get("total_by_player", {}).items()
                },
                "winner_index": sr.get("winner_index"),
                "pot_awarded": int(sr.get("pot_awarded", 0)),
                "half_pot": int(sr.get("half_pot", 0)),
                "odd_chip": int(sr.get("odd_chip", 0)),
                "run_it_twice": bool(sr.get("run_it_twice", False)),
            }

        return {
            "version": 1,
            "starting_chips": int(self.starting_chips),
            "small_blind": int(self.small_blind),
            "big_blind": int(self.big_blind),
            "num_computers": int(self.num_computers),
            "max_computers": int(self.max_computers),
            "opponents": [dict(p) for p in self.opponents] if self.opponents is not None else None,
            "phase": self.phase,
            "street": self.street,
            "hand_number": int(self.hand_number),
            "min_raise": int(self.min_raise),
            "last_full_bet": int(self.last_full_bet),
            "acted_since_full_raise": sorted(int(i) for i in self.acted_since_full_raise),
            "pending": [int(i) for i in self.pending],
            "last_actions": list(self.last_actions),
            "action_log": list(self.action_log),
            "winner_index": self.winner_index,
            "win_reason": self.win_reason,
            "pot_awarded": int(self.pot_awarded),
            "equities": {str(k): float(v) for k, v in self.equities.items()},
            "run_count": int(self.run_count),
            "run_boards": [
                [self._serialize_card(c) for c in b] for b in self.run_boards
            ],
            "run_results": run_results_data,
            "active_run_index": int(self.active_run_index),
            "run_start_board_len": int(self.run_start_board_len),
            "runout_status": self.runout_status,
            "refund_logs": list(self.refund_logs),
            "won_this_hand": {str(k): int(v) for k, v in self.won_this_hand.items()},
            "showdown_result": showdown_data,
            "game": {
                "button_index": int(self.game.button_index),
                "pot": int(self.game.pot),
                "round_bets": [int(x) for x in self.game.round_bets],
                "hand_contributions": [int(x) for x in self.game.hand_contributions],
                "folded": [bool(x) for x in self.game.folded],
                "eliminated": [bool(x) for x in self.game.eliminated],
                "board": [self._serialize_card(c) for c in self.game.board],
                "deck_cards": [
                    self._serialize_card(c)
                    for c in (self.game.deck.cards if self.game.deck else [])
                ],
                "players": players_data,
            },
        }

    @classmethod
    def from_dict(cls, data):
        """Restore a TexasHoldemSession from a serialized dictionary."""
        card_pool = {}

        def get_card(rank, suit):
            key = (int(rank), suit)
            if key not in card_pool:
                card_pool[key] = Card(key[0], key[1])
            return card_pool[key]

        session = cls.__new__(cls)
        session.starting_chips = int(data["starting_chips"])
        session.small_blind = int(data["small_blind"])
        session.big_blind = int(data["big_blind"])
        session.max_computers = int(data.get("max_computers", MAX_COMPUTERS))
        session.num_computers = int(data["num_computers"])
        raw_opps = data.get("opponents")
        session.opponents = [dict(p) for p in raw_opps] if raw_opps is not None else None

        gdata = data["game"]
        game = TexasHoldemGame.__new__(TexasHoldemGame)
        game.small_blind = session.small_blind
        game.big_blind = session.big_blind
        game.max_computers = session.max_computers
        game.num_computers = session.num_computers

        game.players = []
        for pdata in gdata["players"]:
            if pdata["is_human"]:
                player = Player(pdata["name"], int(pdata["chips"]), is_human=True)
            else:
                player = ComputerPlayer(
                    pdata["name"],
                    int(pdata["chips"]),
                    tier=pdata.get("tier", "Pro"),
                    tag=pdata.get("tag", ""),
                )
            player.hole_cards = [get_card(r, s) for r, s in pdata.get("hole_cards", [])]
            game.players.append(player)

        game.button_index = int(gdata["button_index"])
        game.pot = int(gdata["pot"])
        game.round_bets = [int(x) for x in gdata["round_bets"]]
        game.hand_contributions = [int(x) for x in gdata["hand_contributions"]]
        game.folded = [bool(x) for x in gdata["folded"]]
        game.eliminated = [bool(x) for x in gdata["eliminated"]]
        game.board = [get_card(r, s) for r, s in gdata.get("board", [])]

        deck = Deck.__new__(Deck)
        deck.cards = [Card(int(r), s) for r, s in gdata.get("deck_cards", [])]
        game.deck = deck

        session.game = game
        session.phase = data["phase"]
        session.street = data["street"]
        session.hand_number = int(data["hand_number"])
        session.min_raise = int(data["min_raise"])
        session.last_full_bet = int(data.get("last_full_bet", 0))
        session.acted_since_full_raise = set(
            int(i) for i in data.get("acted_since_full_raise", [])
        )
        session.pending = [int(i) for i in data.get("pending", [])]
        session.last_actions = list(data.get("last_actions", []))
        session.action_log = list(data.get("action_log", []))
        session.winner_index = data.get("winner_index")
        session.win_reason = data.get("win_reason")
        session.pot_awarded = int(data.get("pot_awarded", 0))
        session.equities = {
            int(k): float(v) for k, v in data.get("equities", {}).items()
        }
        session.run_count = int(data.get("run_count", 1))
        session.run_boards = [
            [get_card(r, s) for r, s in b] for b in data.get("run_boards", [])
        ]
        session.run_results = [
            cls._deserialize_board_result(res, get_card)
            for res in data.get("run_results", [])
        ]
        session.active_run_index = int(data.get("active_run_index", 0))
        session.run_start_board_len = int(data.get("run_start_board_len", 0))
        session.runout_status = data.get("runout_status", "")
        session.refund_logs = list(data.get("refund_logs", []))
        session.won_this_hand = {
            int(k): int(v) for k, v in data.get("won_this_hand", {}).items()
        }

        sr_data = data.get("showdown_result")
        if sr_data is None:
            session.showdown_result = None
        else:
            sr = {
                "refund_log": sr_data.get("refund_log"),
                "player_results": [
                    cls._deserialize_player_eval(item, get_card)
                    for item in sr_data.get("player_results", [])
                ],
                "pot_awards": [
                    {
                        "pot_name": a["pot_name"],
                        "amount": int(a["amount"]),
                        "winners": [int(w) for w in a["winners"]],
                        "share": int(a["share"]),
                    }
                    for a in sr_data.get("pot_awards", [])
                ],
                "total_by_player": {
                    int(k): int(v)
                    for k, v in sr_data.get("total_by_player", {}).items()
                },
                "winner_index": sr_data.get("winner_index"),
                "pot_awarded": int(sr_data.get("pot_awarded", 0)),
                "half_pot": int(sr_data.get("half_pot", 0)),
                "odd_chip": int(sr_data.get("odd_chip", 0)),
            }
            if sr_data.get("run_it_twice"):
                sr["run_it_twice"] = True
                sr["run_results"] = session.run_results
            session.showdown_result = sr

        return session


def main():
    game = TexasHoldemGame()
    try:
        game.run()
    except (EOFError, KeyboardInterrupt):
        print("\nGame interrupted. Goodbye.")


if __name__ == "__main__":
    main()

