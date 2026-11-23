"""Tests for the state-driven multi-player session, side pots, runouts, updater, and headless UI."""

import io
import os
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import pygame

from texas_holdem import (
    ComputerPlayer,
    TexasHoldemSession,
    build_side_pots,
    estimate_all_in_equities,
)
from texas_holdem_gui import PokerTableApp
from ui_updater import LOCAL_COMMIT_FILE, apply_zip_update, check_for_updates


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

        # Card-by-card reveal (1 -> 2 -> 3 -> 4 -> 5)
        for expected_len in (1, 2, 3, 4):
            session.step_reveal_board()
            self.assertEqual(len(session.game.board), expected_len)
            self.assertEqual(session.phase, "reveal_board")

        session.step_reveal_board()  # 5th card (River) -> Showdown
        self.assertEqual(len(session.game.board), 5)
        self.assertEqual(session.phase, "hand_over")
        self.assertEqual(
            session.game.players[0].chips + session.game.players[1].chips,
            200,
        )

    def test_all_in_run_it_twice_deals_run1_then_run2_one_card_at_a_time(self):
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

        # Run 1 deals 5 cards one by one while Run 2 stays at 0
        for expected_r1 in (1, 2, 3, 4, 5):
            session.step_reveal_board()
            self.assertEqual(len(session.run_boards[0]), expected_r1)
            self.assertEqual(len(session.run_boards[1]), 0)
            self.assertEqual(session.phase, "reveal_board")

        # Run 2 then deals 5 cards one by one until Showdown
        for expected_r2 in (1, 2, 3, 4):
            session.step_reveal_board()
            self.assertEqual(len(session.run_boards[1]), expected_r2)
            self.assertEqual(session.phase, "reveal_board")

        session.step_reveal_board()
        self.assertEqual(session.phase, "hand_over")
        self.assertEqual(session.run_count, 2)
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


class UpdaterTests(unittest.TestCase):
    def test_check_for_updates_detects_new_commit_for_zip_install(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, LOCAL_COMMIT_FILE), "w", encoding="utf-8") as fh:
                fh.write("1111111111111111111111111111111111111111\n")

            fake_remote = {
                "sha": "2222222222222222222222222222222222222222",
                "short_sha": "2222222",
                "message": "feat: new version",
                "date": "2026-11-23T08:00:00Z",
            }
            with patch("ui_updater.fetch_remote_latest", return_value=fake_remote):
                res = check_for_updates(tmpdir)

            self.assertTrue(res["ok"])
            self.assertTrue(res["has_update"])
            self.assertEqual(res["short_sha"], "2222222")

    def test_apply_zip_update_extracts_files_safely_and_records_sha(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("repo-main/texas_holdem_gui.py", "# updated gui\n")
            zf.writestr("repo-main/requirements.txt", "pygame-ce>=2.5.0\n")
            zf.writestr("repo-main/../evil.txt", "blocked")

        with tempfile.TemporaryDirectory() as tmpdir:
            res = apply_zip_update(tmpdir, buf.getvalue(), target_sha="abcdef1234567")
            self.assertEqual(res["updated_files"], 2)
            self.assertTrue(res["requirements_changed"])
            with open(os.path.join(tmpdir, "texas_holdem_gui.py"), "r", encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "# updated gui\n")
            with open(os.path.join(tmpdir, LOCAL_COMMIT_FILE), "r", encoding="utf-8") as fh:
                self.assertEqual(fh.read().strip(), "abcdef1234567")
            self.assertFalse(os.path.exists(os.path.join(os.path.dirname(tmpdir), "evil.txt")))


class HeadlessGuiTests(unittest.TestCase):
    def test_pygame_ui_renders_multiplayer_and_modals_headless(self):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        try:
            for count in (1, 3, 5):
                app = PokerTableApp(headless=True, num_computers=count, check_updates=False)
                app.update(0.016)
                app.render()
            app.setup_modal.visible = True
            app.render()
            app.setup_modal.visible = False
            app.update_modal.visible = True
            app.render()
            app.update_modal.visible = False
            app.rules_modal.visible = True
            app.show_log = True
            app.render()
        finally:
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
