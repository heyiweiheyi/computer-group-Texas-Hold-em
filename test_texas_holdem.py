"""Small standard-library tests for the poker evaluator and basic game flow."""

import contextlib
import io
import unittest
from unittest.mock import patch

from texas_holdem import (
    Card,
    ComputerPlayer,
    HAND_NAMES,
    Player,
    TexasHoldemGame,
    evaluate_best_hand,
    evaluate_five,
)


RANKS = {"T": 10, "J": 11, "Q": 12, "K": 13, "A": 14}


def cards(text):
    """Build cards from compact test text such as 'AS KH 10D 3C 2S'."""
    result = []
    for token in text.split():
        rank_text = token[:-1]
        suit = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}[token[-1]]
        rank = RANKS.get(rank_text, int(rank_text) if rank_text.isdigit() else None)
        result.append(Card(rank, suit))
    return result


class HandEvaluationTests(unittest.TestCase):
    def test_all_nine_hand_categories(self):
        examples = [
            ("AS KH QD 9C 3S", 0),
            ("AS AH KD QC 3S", 1),
            ("AS AH KD KC 3S", 2),
            ("AS AH AD KC 3S", 3),
            ("9S 8H 7D 6C 5S", 4),
            ("AS JS 8S 5S 2S", 5),
            ("AS AH AD KC KD", 6),
            ("AS AH AD AC KS", 7),
            ("9S 8S 7S 6S 5S", 8),
        ]
        for hand_text, expected_category in examples:
            with self.subTest(hand=hand_text):
                score = evaluate_five(cards(hand_text))
                self.assertEqual(score[0], expected_category)
                self.assertEqual(HAND_NAMES[score[0]], HAND_NAMES[expected_category])

    def test_wheel_straight_is_five_high(self):
        score = evaluate_five(cards("AS 2H 3D 4C 5S"))
        self.assertEqual(score, (4, 5))

    def test_pair_kicker_breaks_tie(self):
        ace_kicker = evaluate_five(cards("JS JH AD 8C 3S"))
        king_kicker = evaluate_five(cards("JS JH KD 8C 3S"))
        self.assertGreater(ace_kicker, king_kicker)

    def test_two_pair_compares_kicker_after_both_pairs(self):
        low_kicker = evaluate_five(cards("AS AH KD KC 3S"))
        queen_kicker = evaluate_five(cards("AS AH KD KC QD"))
        self.assertGreater(queen_kicker, low_kicker)

    def test_seven_cards_choose_best_five(self):
        score, best_five = evaluate_best_hand(cards("AS AH KD QC JH 10S 9D"))
        self.assertEqual(score, (4, 14))
        self.assertEqual(len(best_five), 5)

    def test_best_five_can_ignore_both_private_cards(self):
        board = cards("AS KS QS JS 10S")
        private_cards = cards("2H 3D")
        score, best_five = evaluate_best_hand(private_cards + board)
        self.assertEqual(score, (8, 14))
        self.assertEqual(set(best_five), set(board))


class ChipAndGameFlowTests(unittest.TestCase):
    def test_bet_uses_only_available_chips(self):
        player = Player("Test Player", 35)
        actual = player.take_bet(100)
        self.assertEqual(actual, 35)
        self.assertEqual(player.chips, 0)

    def test_game_pot_and_round_bet_track_short_all_in(self):
        game = TexasHoldemGame(starting_chips=100)
        game.players[0].chips = 7
        actual = game._put_chips_in_pot(0, 20)
        self.assertEqual(actual, 7)
        self.assertEqual(game.players[0].chips, 0)
        self.assertEqual(game.pot, 7)
        self.assertEqual(game.round_bets[0], 7)

    def test_unmatched_bet_is_returned(self):
        game = TexasHoldemGame(starting_chips=100)
        game.players[0].chips = 70
        game.players[1].chips = 90
        game.pot = 40
        game.round_bets = [30, 10]
        with contextlib.redirect_stdout(io.StringIO()):
            game._refund_unmatched_bet()
        self.assertEqual(game.players[0].chips, 90)
        self.assertEqual(game.pot, 20)
        self.assertEqual(game.round_bets, [10, 10])

    def test_player_can_call_an_all_in(self):
        game = TexasHoldemGame(starting_chips=100, small_blind=5, big_blind=10)
        game.players[0].chips = 95
        game.players[1].chips = 0
        game.players[0].hole_cards = cards("AS KH")
        game.players[1].hole_cards = cards("QD JC")
        game.pot = 20
        game.round_bets = [5, 15]

        with patch("builtins.input", side_effect=["2"]), contextlib.redirect_stdout(
            io.StringIO()
        ):
            folded_winner = game._run_betting_round(first_actor=0)

        self.assertIsNone(folded_winner)
        self.assertEqual(game.pot, 30)
        self.assertEqual(game.round_bets, [15, 15])
        self.assertEqual(game.players[0].chips, 85)

    def test_invalid_menu_and_raise_amount_are_reprompted(self):
        game = TexasHoldemGame(starting_chips=100)
        answers = ["x", "3", "not money", "5", "10"]
        with patch("builtins.input", side_effect=answers), contextlib.redirect_stdout(
            io.StringIO()
        ):
            action = game._human_action(
                player_index=0,
                to_call=5,
                can_raise=True,
                min_raise=10,
                opponent_all_in=False,
            )

        self.assertEqual(action, {"action": "raise", "amount": 10})

    def test_basic_hand_reaches_showdown_and_preserves_chips(self):
        game = TexasHoldemGame(starting_chips=100, small_blind=1, big_blind=2)
        game.button_index = 0

        # Human calls the small blind, then checks each post-flop street.
        scripted_inputs = ["2", "1", "1", "1"]

        def computer_check_or_call(self, to_call, can_raise, min_raise, pot, board, opponent_all_in):
            if to_call > 0:
                return {"action": "call"}
            return {"action": "check"}

        with patch("builtins.input", side_effect=scripted_inputs), patch.object(
            ComputerPlayer, "choose_action", computer_check_or_call
        ), contextlib.redirect_stdout(io.StringIO()):
            game.play_hand()

        self.assertEqual(len(game.board), 5)
        self.assertEqual(game.pot, 0)
        self.assertEqual(game.players[0].chips + game.players[1].chips, 200)

    def test_short_stack_calls_all_in_and_the_board_runs_out(self):
        game = TexasHoldemGame(starting_chips=10, small_blind=5, big_blind=10)
        game.players[0].chips = 7
        game.players[1].chips = 10
        game.button_index = 0

        # The human has only $2 left after the small blind, so this call is short.
        with patch("builtins.input", side_effect=["2"]), contextlib.redirect_stdout(
            io.StringIO()
        ):
            game.play_hand()

        self.assertEqual(len(game.board), 5)
        self.assertEqual(game.pot, 0)
        self.assertEqual(game.players[0].chips + game.players[1].chips, 17)


if __name__ == "__main__":
    unittest.main()
