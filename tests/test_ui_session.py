"""Tests for the state-driven multi-player session, side pots, runouts, updater, and headless UI."""

import io
import json
import os
import random
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import pygame

from texas_holdem import (
    AI_ROSTER,
    ComputerPlayer,
    TexasHoldemSession,
    build_side_pots,
    estimate_all_in_equities,
)
from texas_holdem_gui import PokerTableApp
from ui_saves import MAX_SAVED_MATCHES, MatchSaveManager
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

    def test_short_incomplete_all_in_does_not_reopen_raising_for_acted_player(self):
        # 3-player pot: Human bets $20, AI 1 all-in for $25 (+$5 < min_raise $20), AI 2 calls $25.
        # Action returns to Human (already acted since last full bet $20): Human can Call/Fold, NOT re-raise.
        session = TexasHoldemSession(starting_chips=200, small_blind=5, big_blind=10, num_computers=2)
        session.street = "flop"
        session.game.board = [session.game.deck.draw() for _ in range(3)]
        session.game.round_bets = [0, 0, 0]
        session.game.hand_contributions = [10, 10, 10]
        session.game.pot = 30
        session.game.players[0].chips = 200
        session.game.players[1].chips = 25
        session.game.players[2].chips = 200
        session.min_raise = 10
        session.last_full_bet = 0
        session.acted_since_full_raise = set()
        session.pending = [0, 1, 2]
        session.phase = "waiting_human"

        # Human bets $20 (min_raise becomes $20, last_full_bet = $20)
        legal_open = session.get_legal_human_actions()
        self.assertTrue(legal_open["is_bet"])
        self.assertEqual(legal_open["min_total_bet"], 10)
        session.submit_human_action({"action": "raise", "amount": 20})

        with patch.object(
            ComputerPlayer,
            "choose_action",
            side_effect=[{"action": "all_in"}, {"action": "call"}],
        ):
            session.step_computer_turn()  # AI 1 all-in for $25 (+$5 incomplete raise)
            session.step_computer_turn()  # AI 2 calls $25

        self.assertEqual(session.phase, "waiting_human")
        legal_after = session.get_legal_human_actions()
        self.assertEqual(legal_after["to_call"], 5)
        self.assertFalse(legal_after["can_raise"])
        self.assertFalse(legal_after["can_all_in"])

    def test_custom_ai_roster_names_and_tiers(self):
        by_name = {item["name"]: item for item in AI_ROSTER}
        expected_tags = {
            "Claude": "Anthropic",
            "Chatgpt": "Openai",
            "Jtt": "Rollingwood",
            "Yuanzuo": "Rollingwood",
            "Qzr": "Rollingwood",
            "Xrh": "Rollingwood",
            "Zch": "Rollingwood",
            "Deepseek": "DeepSeek",
            "Glm": "Zcode",
            "Kimi": "Moonshot",
            "Gemini": "Google",
            "Doubao": "ByteDance",
        }
        self.assertEqual(set(by_name.keys()), set(expected_tags.keys()))
        self.assertEqual(by_name["Claude"]["tier"], "Ultra")
        self.assertEqual(by_name["Jtt"]["tier"], "Ultra")
        self.assertEqual(by_name["Xrh"]["tier"], "Rookie")
        self.assertEqual(by_name["Qzr"]["tier"], "Rookie")
        for name, expected_tag in expected_tags.items():
            self.assertEqual(by_name[name]["tag"], expected_tag)

        chosen = [item for item in AI_ROSTER if item["name"] in ("Claude", "Jtt", "Xrh")]
        session = TexasHoldemSession(starting_chips=500, opponents=chosen)
        self.assertEqual(len(session.game.players), 4)
        self.assertEqual([p.name for p in session.game.players[1:]], [p["name"] for p in chosen])
        self.assertEqual([p.tier for p in session.game.players[1:]], [p["tier"] for p in chosen])
        self.assertEqual([p.tag for p in session.game.players[1:]], [p["tag"] for p in chosen])


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
            app_title = PokerTableApp(headless=True, start_screen="title", check_updates=False)
            app_title.render()
            app_title.screen_mode = "select"
            app_title.render()
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
            app.summary_modal.visible = True
            app.render()
            app.summary_modal.visible = False
            app.rules_modal.visible = True
            app.show_log = True
            app.render()
            app.rules_modal.visible = False
            app.saves_modal.visible = True
            app.render()
        finally:
            pygame.quit()


class SaveAndResumeTests(unittest.TestCase):
    def test_session_serialization_roundtrip_mid_hand_and_run_it_twice(self):
        random.seed(2026)
        opponents = [AI_ROSTER[0], AI_ROSTER[1], AI_ROSTER[10]]
        session = TexasHoldemSession(
            starting_chips=500,
            small_blind=5,
            big_blind=10,
            opponents=opponents,
        )
        while session.phase == "computer_turn":
            session.step_computer_turn()

        raw_json = json.dumps(session.to_dict(), ensure_ascii=False)
        restored = TexasHoldemSession.from_dict(json.loads(raw_json))

        self.assertEqual(restored.hand_number, session.hand_number)
        self.assertEqual(restored.phase, session.phase)
        self.assertEqual(restored.street, session.street)
        self.assertEqual(restored.game.pot, session.game.pot)
        self.assertEqual(
            [p.name for p in restored.game.players],
            [p.name for p in session.game.players],
        )
        self.assertEqual(
            [p.chips for p in restored.game.players],
            [p.chips for p in session.game.players],
        )
        self.assertEqual(
            [(c.rank, c.suit) for c in restored.game.players[0].hole_cards],
            [(c.rank, c.suit) for c in session.game.players[0].hole_cards],
        )
        self.assertEqual(restored.game.players[1].tier, "Ultra")
        self.assertEqual(restored.game.players[1].tag, "Anthropic")
        self.assertEqual(len(restored.game.deck.cards), len(session.game.deck.cards))

        # Now force an all-in Run It Twice showdown and verify Card identity after reload
        session.game.players[0].chips = 120
        session.game.players[1].chips = 120
        session.game.players[2].chips = 0
        session.game.players[3].chips = 0
        session.game.folded = [False, False, True, True]
        session.game.eliminated = [False, False, True, True]
        session.game.round_bets = [0, 0, 0, 0]
        session.game.hand_contributions = [0, 0, 0, 0]
        session.game.pot = 0
        session.game.board = []
        session.street = "pre_flop"
        session.pending = [0, 1]
        session.phase = "waiting_human"
        session.submit_human_action({"action": "all_in"})
        if session.phase == "computer_turn":
            session._apply_action_and_advance(1, {"action": "call"})
        self.assertEqual(session.phase, "choose_run_count")
        session.choose_run_count(2)
        while session.phase == "reveal_board":
            session.step_reveal_board()
        self.assertEqual(session.phase, "hand_over")

        rit_restored = TexasHoldemSession.from_dict(json.loads(json.dumps(session.to_dict())))
        self.assertEqual(rit_restored.run_count, 2)
        self.assertEqual(len(rit_restored.run_boards), 2)
        self.assertEqual(len(rit_restored.run_results), 2)
        # Card objects in best_five must share identity with hole_cards / run_boards for UI highlight
        r1_pool = set(rit_restored.run_boards[0])
        for p in rit_restored.game.players[:2]:
            r1_pool.update(p.hole_cards)
        for p_res in rit_restored.run_results[0]["player_results"].values():
            for card in p_res["best_five"]:
                self.assertIn(card, r1_pool)

    def test_save_manager_keeps_three_unfinished_matches_and_clears_finished(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = MatchSaveManager(tmpdir, persist=True)
            ids = []
            for idx in range(4):
                s = TexasHoldemSession(
                    starting_chips=500 + idx * 100,
                    opponents=[AI_ROSTER[idx], AI_ROSTER[idx + 1]],
                )
                s.hand_number = idx + 1
                sid = mgr.save_match(None, s)
                ids.append(sid)

            # Only the 3 most recent unfinished matches are retained
            saves = mgr.list_saves()
            self.assertEqual(len(saves), MAX_SAVED_MATCHES)
            self.assertEqual([item["id"] for item in saves], [ids[3], ids[2], ids[1]])

            # Reload from disk into a fresh manager
            mgr2 = MatchSaveManager(tmpdir, persist=True)
            self.assertEqual(mgr2.count(), 3)
            loaded = mgr2.load_session(ids[2])
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.hand_number, 3)

            # Updating an existing slot does not duplicate and moves it to slot #1
            loaded.hand_number = 7
            mgr2.save_match(ids[2], loaded)
            self.assertEqual(mgr2.count(), 3)
            self.assertEqual(mgr2.list_saves()[0]["id"], ids[2])
            self.assertEqual(mgr2.list_saves()[0]["hand_number"], 7)

            # Finishing a match automatically deletes its save slot
            loaded.phase = "match_over"
            mgr2.save_match(ids[2], loaded)
            self.assertEqual(mgr2.count(), 2)
            self.assertNotIn(ids[2], [item["id"] for item in mgr2.list_saves()])

    def test_opponent_select_returns_to_table_when_unchanged_and_saves_on_change(self):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                app = PokerTableApp(
                    headless=True,
                    start_screen="title",
                    check_updates=False,
                    save_dir=tmpdir,
                )
                self.assertEqual(app.save_manager.count(), 0)

                # Start a 4P match with Claude, Jtt, Xrh
                initial_opps = [AI_ROSTER[0], AI_ROSTER[1], AI_ROSTER[10]]
                app._start_fresh_match(
                    {
                        "opponents": initial_opps,
                        "num_computers": 3,
                        "starting_chips": 500,
                        "small_blind": 5,
                        "big_blind": 10,
                    },
                    new_slot=True,
                )
                first_save_id = app.active_save_id
                first_hand_cards = [(c.rank, c.suit) for c in app.session.game.players[0].hole_cards]
                self.assertEqual(app.save_manager.count(), 1)

                # Click Table: 3 AI to enter opponent selection mid-match
                app.select_screen.sync_from_session(
                    app.session,
                    can_resume=True,
                    active_cfg=app._current_match_config(),
                )
                app.screen_mode = "select"
                self.assertTrue(app.select_screen.can_resume)
                self.assertTrue(app.select_screen.is_unchanged_from_active())

                # Pressing Enter when unchanged resumes the exact same match without resetting
                app.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}))
                self.assertEqual(app.screen_mode, "table")
                self.assertEqual(app.active_save_id, first_save_id)
                self.assertEqual(
                    [(c.rank, c.suit) for c in app.session.game.players[0].hole_cards],
                    first_hand_cards,
                )

                # Go back to select, toggle Claude off & back on -> still unchanged -> resumes
                app.select_screen.sync_from_session(
                    app.session,
                    can_resume=True,
                    active_cfg=app._current_match_config(),
                )
                app.screen_mode = "select"
                app.select_screen._toggle_ai("Claude")
                app.select_screen._toggle_ai("Claude")
                self.assertTrue(app.select_screen.is_unchanged_from_active())

                # Now swap Xrh -> Qzr, then press ESC (Back to Table) -> cancels change & returns
                app.select_screen._toggle_ai("Xrh")
                app.select_screen._toggle_ai("Qzr")
                self.assertFalse(app.select_screen.is_unchanged_from_active())
                app.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE}))
                self.assertEqual(app.screen_mode, "table")
                self.assertEqual(app.active_save_id, first_save_id)
                self.assertIn("Xrh", [p.name for p in app.session.game.players])

                # Swap Xrh -> Qzr and confirm Start New Match -> archives old match & starts new one
                app.select_screen.sync_from_session(
                    app.session,
                    can_resume=True,
                    active_cfg=app._current_match_config(),
                )
                app.screen_mode = "select"
                app.select_screen._toggle_ai("Xrh")
                app.select_screen._toggle_ai("Qzr")
                app.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}))
                self.assertEqual(app.screen_mode, "table")
                self.assertNotEqual(app.active_save_id, first_save_id)
                self.assertIn("Qzr", [p.name for p in app.session.game.players])
                self.assertEqual(app.save_manager.count(), 2)

                # Resume the first unfinished match from its save slot
                self.assertTrue(app._resume_saved_match(first_save_id))
                self.assertEqual(app.active_save_id, first_save_id)
                self.assertEqual(
                    [(c.rank, c.suit) for c in app.session.game.players[0].hole_cards],
                    first_hand_cards,
                )
            finally:
                pygame.quit()


if __name__ == "__main__":
    unittest.main()
