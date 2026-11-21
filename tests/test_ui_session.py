"""Tests for the state-driven multi-player session, side pots, runouts, and headless UI."""

import os
import unittest
from unittest.mock import patch

import pygame

from texas_holdem import (
    ComputerPlayer,
    TexasHoldemSession,
    build_side_pots,
    estimate_all_in_equities,
)
from texas_holdem_gui import PokerTableApp


class SidePotAndEquityTests(unittest.TestCase):
    def test_build_side_pots_splits_unequal_all_ins_and_skips_folded(self):
        # P0 all-in 50, P1 all-in 120, P2 folded after 80, P3 called 120
        contributions = [50, 120, 80, 120]
        folded = [False, False, True, False]
        pots = build_side_pots(contributions, folded)
        self.assertEqual(
            pots,
            [
                {"amount": 200, "eligible": [0, 1, 3]},
                {"amount": 170, "eligible": [1, 3]},
            ],
        )
        self.assertEqual(sum(p["amount"] for p in pots), sum(contributions))

    def test_estimate_all_in_equities_sums_to_100(self):
        session = TexasHoldemSession(starting_chips=500, num_computers=2)
        equities = estimate_all_in_equities(
            session.game.players,
            [],
            [0, 1, 2],
            samples=80,
        )
        self.assertEqual(set(equities.keys()), {0, 1, 2})
        self.assertAlmostEqual(sum(equities.values()), 100.0, places=2)


class TexasHoldemSessionTests(unittest.TestCase):
    def test_initial_hand_posts_blinds_and_preserves_total_chips(self):
        session = TexasHoldemSession(starting_chips=500, small_blind=5, big_blind=10)
        total = (
            session.game.players[0].chips
            + session.game.players[1].chips
            + session.game.pot
        )
        self.assertEqual(total, 1000)
        self.assertEqual(session.hand_number, 1)
        self.assertEqual(session.game.pot, 15)
        self.assertIn(session.phase, ("waiting_human", "computer_turn"))

    def test_max_computers_cap_is_enforced(self):
        with self.assertRaises(ValueError):
            from texas_holdem import TexasHoldemGame

            TexasHoldemGame(num_computers=6, max_computers=5)

    def test_multi_computer_six_player_hand_conserves_chips(self):
        session = TexasHoldemSession(
            starting_chips=200, small_blind=5, big_blind=10, num_computers=5
        )
        self.assertEqual(len(session.game.players), 6)

        def passive_ai(self, to_call, can_raise, min_raise, pot, board, opponent_all_in):
            return {"action": "call"} if to_call > 0 else {"action": "check"}

        with patch.object(ComputerPlayer, "choose_action", passive_ai):
            steps = 0
            while session.phase != "hand_over" and steps < 120:
                if session.phase == "waiting_human":
                    legal = session.get_legal_human_actions()
                    action = {"action": "check"} if legal["can_check"] else {"action": "call"}
                    session.submit_human_action(action)
                elif session.phase == "computer_turn":
                    session.step_computer_turn()
                elif session.phase == "choose_run_count":
                    session.choose_run_count(1)
                elif session.phase == "reveal_board":
                    session.step_reveal_board()
                steps += 1

        self.assertEqual(session.phase, "hand_over")
        self.assertEqual(session.game.pot, 0)
        self.assertEqual(sum(p.chips for p in session.game.players), 1200)

    def test_all_in_run_once_steps_through_streets(self):
        session = TexasHoldemSession(starting_chips=100, small_blind=5, big_blind=10)

        def always_call(self, to_call, can_raise, min_raise, pot, board, opponent_all_in):
            return {"action": "call"} if to_call > 0 else {"action": "check"}

        with patch.object(ComputerPlayer, "choose_action", always_call):
            if session.phase == "computer_turn":
                session.step_computer_turn()
            self.assertEqual(session.phase, "waiting_human")
            session.submit_human_action({"action": "all_in"})
            while session.phase == "computer_turn":
                session.step_computer_turn()

        self.assertEqual(session.phase, "choose_run_count")
        self.assertAlmostEqual(sum(session.equities.values()), 100.0, places=2)
        session.choose_run_count(1)
        self.assertEqual(session.phase, "reveal_board")

        session.step_reveal_board()  # Flop
        self.assertEqual(len(session.game.board), 3)
        self.assertEqual(session.phase, "reveal_board")
        session.step_reveal_board()  # Turn
        self.assertEqual(len(session.game.board), 4)
        self.assertEqual(session.phase, "reveal_board")
        session.step_reveal_board()  # River -> Showdown
        self.assertEqual(len(session.game.board), 5)
        self.assertEqual(session.phase, "hand_over")
        self.assertEqual(
            session.game.players[0].chips + session.game.players[1].chips,
            200,
        )

    def test_all_in_run_it_twice_splits_boards_and_conserves_chips(self):
        session = TexasHoldemSession(
            starting_chips=150, small_blind=5, big_blind=10, num_computers=3
        )

        with patch.object(
            ComputerPlayer,
            "choose_action",
            lambda *args, **kwargs: {"action": "all_in"},
        ):
            steps = 0
            while session.phase in ("waiting_human", "computer_turn") and steps < 30:
                if session.phase == "waiting_human":
                    legal = session.get_legal_human_actions()
                    if legal["can_all_in"]:
                        session.submit_human_action({"action": "all_in"})
                    elif legal["to_call"] > 0:
                        session.submit_human_action({"action": "call"})
                    else:
                        session.submit_human_action({"action": "check"})
                else:
                    session.step_computer_turn()
                steps += 1

        self.assertEqual(session.phase, "choose_run_count")
        session.choose_run_count(2)
        self.assertEqual(session.phase, "reveal_board")

        while session.phase == "reveal_board":
            session.step_reveal_board()

        self.assertEqual(session.phase, "hand_over")
        self.assertEqual(session.run_count, 2)
        self.assertEqual(len(session.run_boards), 2)
        self.assertEqual(len(session.run_boards[0]), 5)
        self.assertEqual(len(session.run_boards[1]), 5)
        self.assertEqual(session.game.pot, 0)
        self.assertEqual(sum(p.chips for p in session.game.players), 600)

    def test_button_rotates_on_next_hand(self):
        session = TexasHoldemSession(starting_chips=200, small_blind=5, big_blind=10)
        first_button = session.game.button_index
        if session.phase == "computer_turn":
            with patch.object(
                ComputerPlayer,
                "choose_action",
                lambda *args, **kwargs: {"action": "fold"},
            ):
                session.step_computer_turn()
        else:
            legal = session.get_legal_human_actions()
            session.submit_human_action({"action": "fold"} if legal["can_fold"] else {"action": "all_in"})
            while session.phase != "hand_over":
                if session.phase == "computer_turn":
                    session.step_computer_turn()
                elif session.phase == "waiting_human":
                    session.submit_human_action({"action": "fold"})
                elif session.phase == "choose_run_count":
                    session.choose_run_count(1)
                elif session.phase == "reveal_board":
                    session.step_reveal_board()

        self.assertEqual(session.phase, "hand_over")
        started = session.start_next_hand()
        if started:
            self.assertEqual(session.game.button_index, 1 - first_button)


class HeadlessGuiTests(unittest.TestCase):
    def test_pygame_ui_renders_multiplayer_and_modals_headless(self):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        try:
            for count in (1, 3, 5):
                app = PokerTableApp(headless=True, num_computers=count)
                app.update(0.016)
                app.render()
            app.setup_modal.visible = True
            app.render()
            app.setup_modal.visible = False
            app.rules_modal.visible = True
            app.show_log = True
            app.render()
        finally:
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
