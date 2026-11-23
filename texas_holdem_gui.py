"""Pygame graphical interface for 2-to-6 player Texas Hold'em with All-In Runouts."""

import os
import random
import subprocess
import sys
import time

import pygame

from texas_holdem import MAX_COMPUTERS, TexasHoldemSession
from ui_assets import (
    BOARD_CARD_Y,
    BOARD_GAP,
    BOARD_START_X,
    CardRenderer,
    SoundManager,
    build_table_surface,
    draw_chip_stack,
)
from ui_theme import (
    BADGE_ALLIN,
    BADGE_BLIND,
    BADGE_CALL,
    BADGE_CHECK,
    BADGE_FOLD,
    BADGE_RAISE,
    BTN_ALLIN,
    BTN_ALLIN_HOVER,
    BTN_CALL,
    BTN_CALL_HOVER,
    BTN_FOLD,
    BTN_FOLD_HOVER,
    BTN_NEUTRAL,
    BTN_NEUTRAL_HOVER,
    BTN_RAISE,
    BTN_RAISE_HOVER,
    CARD_WIDTH,
    DUAL_CARD_HEIGHT,
    DUAL_CARD_WIDTH,
    FELT_DARK,
    FPS,
    GOLD_BRIGHT,
    GOLD_DIM,
    GOLD_MID,
    MINI_CARD_HEIGHT,
    MINI_CARD_WIDTH,
    PANEL_BG,
    PANEL_BORDER,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    draw_text,
    ease_out_cubic,
    lerp,
)
from ui_updater import UpdateController
from ui_widgets import ActionButton, RaiseControl, RulesModal, SetupModal, UpdateModal


DECK_POS = (924, 290)
COMP_CARD_POS_1V1 = [(642, 86), (726, 86)]
HUMAN_CARD_POS = [(634, 468), (734, 468)]

# Ring-table seat layouts for 2..5 AI opponents: (seat_x, seat_y, bet_pill_center)
RING_SEAT_LAYOUTS = {
    2: [
        (140, 102, (310, 212)),
        (802, 102, (890, 212)),
    ],
    3: [
        (46, 296, (300, 396)),
        (471, 84, (766, 126)),
        (896, 296, (900, 396)),
    ],
    4: [
        (46, 398, (300, 350)),
        (74, 112, (318, 216)),
        (868, 112, (882, 216)),
        (896, 398, (900, 350)),
    ],
    5: [
        (46, 398, (300, 350)),
        (74, 112, (318, 216)),
        (471, 84, (766, 126)),
        (868, 112, (882, 216)),
        (896, 398, (900, 350)),
    ],
}


def _badge_color(summary):
    if summary.startswith("CHECK"):
        return BADGE_CHECK
    if summary.startswith("CALL"):
        return BADGE_CALL
    if summary.startswith("RAISE"):
        return BADGE_RAISE
    if summary.startswith(("FOLD", "OUT")):
        return BADGE_FOLD
    if summary.startswith("ALL-IN"):
        return BADGE_ALLIN
    return BADGE_BLIND


class FontManagerWrapper:
    """Thin convenience wrapper exposing FontPalette.get directly."""

    def __init__(self):
        from ui_theme import FontPalette

        self.palette = FontPalette()

    def get(self, size, bold=False):
        return self.palette.get(size, bold=bold)


class PokerTableApp:
    """Main Pygame application driving TexasHoldemSession at 60 FPS."""

    def __init__(self, headless=False, num_computers=1, check_updates=None):
        if headless:
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Texas Hold'em — Multi-Player & All-In Runout")
        if not headless and sys.platform == "win32":
            self._ensure_window_visible_windows()
        self.clock = pygame.time.Clock()

        self.app_dir = os.path.dirname(os.path.abspath(__file__))
        self.fonts = FontManagerWrapper()
        self.table_surface = build_table_surface(WINDOW_WIDTH, WINDOW_HEIGHT, self.fonts.palette)
        self.card_renderer = CardRenderer(self.fonts.palette)
        self.sounds = SoundManager()

        self.session = TexasHoldemSession(
            starting_chips=500,
            small_blind=5,
            big_blind=10,
            num_computers=num_computers,
            max_computers=MAX_COMPUTERS,
        )
        self.rules_modal = RulesModal(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setup_modal = SetupModal(WINDOW_WIDTH, WINDOW_HEIGHT, max_computers=MAX_COMPUTERS)
        self.update_modal = UpdateModal(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.updater = UpdateController(self.app_dir)
        self.update_toast_dismissed = False
        self._restart_requested = False
        self.show_log = False

        self.display_chips = [float(p.chips) for p in self.session.game.players]
        self.display_pot = float(self.session.game.pot)
        self.card_anims = {}
        self.prev_board_len = 0
        self.prev_run_lens = [0, 0]
        self.prev_pot = self.session.game.pot
        self.prev_phase = self.session.phase
        self.ai_wait_until = 0.0
        self.runout_wait_until = 0.0

        self._build_controls()
        self._trigger_new_hand_anims()
        self._sync_timers_and_controls()

        should_check = (not headless) if check_updates is None else bool(check_updates)
        if should_check:
            self.updater.check_async()

    @staticmethod
    def _ensure_window_visible_windows():
        try:
            import ctypes

            hwnd = pygame.display.get_wm_info().get("window")
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 5)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

    def _build_controls(self):
        # Top utility bar buttons
        self.btn_update = ActionButton((588, 9, 98, 30), "Update", BTN_NEUTRAL, BTN_NEUTRAL_HOVER, radius=8)
        self.btn_setup = ActionButton((694, 9, 128, 30), "Table: 1 AI", BTN_RAISE, BTN_RAISE_HOVER, radius=8)
        self.btn_log = ActionButton((830, 9, 72, 30), "Log", BTN_NEUTRAL, BTN_NEUTRAL_HOVER, radius=8)
        self.btn_sound = ActionButton((910, 9, 96, 30), "Sound: On", BTN_NEUTRAL, BTN_NEUTRAL_HOVER, radius=8)
        self.btn_rules = ActionButton((1014, 9, 80, 30), "Rules ?", BTN_NEUTRAL, BTN_NEUTRAL_HOVER, radius=8)
        self.btn_new_match = ActionButton((1102, 9, 82, 30), "Restart", BTN_NEUTRAL, BTN_NEUTRAL_HOVER, radius=8)

        # Bottom action dock
        self.btn_fold = ActionButton((28, 668, 112, 56), "Fold", BTN_FOLD, BTN_FOLD_HOVER, shortcut="F")
        self.btn_call = ActionButton((152, 668, 152, 56), "Check", BTN_CALL, BTN_CALL_HOVER, shortcut="C")
        self.raise_control = RaiseControl(pygame.Rect(336, 700, 256, 8), presets_y=658)
        self.btn_raise = ActionButton((682, 668, 154, 56), "Raise", BTN_RAISE, BTN_RAISE_HOVER, shortcut="R")
        self.btn_allin = ActionButton((852, 668, 152, 56), "All-In", BTN_ALLIN, BTN_ALLIN_HOVER, shortcut="A")
        self.btn_next = ActionButton((1020, 668, 152, 56), "Next Hand", BTN_CALL, BTN_CALL_HOVER, shortcut="Space")

        # Run Once vs Run It Twice prompt buttons (centered above felt)
        self.btn_run_once = ActionButton((424, 412, 164, 42), "Run Once (1x)", BTN_CALL, BTN_CALL_HOVER, shortcut="1", radius=10)
        self.btn_run_twice = ActionButton((612, 412, 164, 42), "Run Twice (2x)", BTN_ALLIN, BTN_ALLIN_HOVER, shortcut="2", radius=10)

    def _deck_origin(self):
        return DECK_POS if self.session.num_computers <= 2 else (600, 195)

    def _trigger_new_hand_anims(self):
        now = time.monotonic()
        origin = self._deck_origin()
        self.prev_board_len = len(self.session.game.board)
        self.prev_run_lens = [0, 0]
        self.display_chips = [float(p.chips) for p in self.session.game.players]
        self.card_anims = {}
        step = 0
        for round_idx in range(2):
            for p_idx, elim in enumerate(self.session.game.eliminated):
                if not elim:
                    self.card_anims[(p_idx, round_idx)] = (now + step * 0.05, 0.28, origin)
                    step += 1
        self.sounds.play("card")

    def _trigger_board_anims(self, old_len, new_len):
        now = time.monotonic()
        origin = self._deck_origin()
        for idx in range(old_len, new_len):
            delay = (idx - old_len) * 0.09
            self.card_anims[("board", idx)] = (now + delay, 0.36, origin)
        self.sounds.play("card")

    def _next_runout_delay(self):
        """Return suspenseful delay before flipping the next all-in runout card."""
        if self.session.run_count == 2 and len(self.session.run_boards) == 2:
            r1_len = len(self.session.run_boards[0])
            r2_len = len(self.session.run_boards[1])
            if r1_len == 5 and r2_len == self.session.run_start_board_len:
                return 2.2
            cur_len = r1_len if r1_len < 5 else r2_len
        else:
            cur_len = len(self.session.game.board)

        if cur_len == 4:
            return 2.1
        if cur_len == 3:
            return 1.65
        return 1.25

    def _sync_timers_and_controls(self):
        now = time.monotonic()
        n_ai = self.session.num_computers
        self.btn_setup.label = f"Table: {n_ai} AI"

        if self.session.phase == "computer_turn" and self.ai_wait_until <= 0.0:
            delay = random.uniform(1.2, 2.0) if n_ai == 1 else random.uniform(0.9, 1.5)
            self.ai_wait_until = now + delay
        elif self.session.phase != "computer_turn":
            self.ai_wait_until = 0.0

        if self.session.phase == "reveal_board" and self.runout_wait_until <= 0.0:
            self.runout_wait_until = now + self._next_runout_delay()
        elif self.session.phase != "reveal_board":
            self.runout_wait_until = 0.0

        is_human_turn = self.session.phase == "waiting_human"
        if is_human_turn:
            legal = self.session.get_legal_human_actions()
            self.btn_fold.enabled = legal["can_fold"]
            self.btn_call.enabled = True
            if legal["can_check"]:
                self.btn_call.label = "Check"
            elif legal["call_amount"] < legal["to_call"]:
                self.btn_call.label = f"Call ${legal['call_amount']}*"
            else:
                self.btn_call.label = f"Call ${legal['call_amount']}"

            self.raise_control.set_bounds(legal["min_raise"], legal["max_raise"], self.session.game.pot)
            self.raise_control.set_enabled(legal["can_raise"])
            self.btn_raise.enabled = legal["can_raise"]
            self.btn_allin.enabled = legal["can_all_in"]
            self.btn_allin.label = f"All-In ${legal['all_in_amount']}" if legal["can_all_in"] else "All-In"
        else:
            self.btn_fold.enabled = False
            self.btn_call.enabled = False
            self.btn_call.label = "Check / Call"
            self.raise_control.set_enabled(False)
            self.btn_raise.enabled = False
            self.btn_raise.label = "Raise"
            self.btn_allin.enabled = False
            self.btn_allin.label = "All-In"

        if self.session.phase == "hand_over":
            human_alive = self.session.game.players[0].chips > 0
            any_ai_alive = any(p.chips > 0 for p in self.session.game.players[1:])
            self.btn_next.enabled = True
            self.btn_next.label = "Next Hand" if (human_alive and any_ai_alive) else "Finish Match"
        elif self.session.phase == "match_over":
            self.btn_next.enabled = True
            self.btn_next.label = "Play Again"
        else:
            self.btn_next.enabled = False
            self.btn_next.label = "Next Hand"

    def _on_state_advanced(self, previous_phase):
        if self.session.run_count == 2 and len(self.session.run_boards) == 2:
            now = time.monotonic()
            origin = self._deck_origin()
            dealt_any = False
            for run_idx in range(2):
                new_len = len(self.session.run_boards[run_idx])
                if new_len > self.prev_run_lens[run_idx]:
                    for c_idx in range(self.prev_run_lens[run_idx], new_len):
                        self.card_anims[("run", run_idx, c_idx)] = (now, 0.36, origin)
                    self.prev_run_lens[run_idx] = new_len
                    dealt_any = True
            if dealt_any:
                self.sounds.play("card")
        else:
            new_board_len = len(self.session.game.board)
            if new_board_len > self.prev_board_len:
                self._trigger_board_anims(self.prev_board_len, new_board_len)
                self.prev_board_len = new_board_len

        if self.session.game.pot > self.prev_pot:
            self.sounds.play("chip")
        elif previous_phase in ("waiting_human", "computer_turn"):
            if "CHECK" in self.session.last_actions:
                self.sounds.play("check")

        if self.session.phase == "hand_over" and previous_phase != "hand_over":
            if self.session.winner_index in (0, None):
                self.sounds.play("win")

        self.prev_pot = self.session.game.pot
        self.prev_phase = self.session.phase
        self._sync_timers_and_controls()

    def _submit_human(self, action_dict):
        if self.session.phase != "waiting_human":
            return
        prev_phase = self.session.phase
        self.session.submit_human_action(action_dict)
        self._on_state_advanced(prev_phase)

    def _choose_run_count(self, count):
        if self.session.phase != "choose_run_count":
            return
        prev_phase = self.session.phase
        self.session.choose_run_count(count)
        if count == 2 and len(self.session.run_boards) == 2:
            self.prev_run_lens = [len(self.session.run_boards[0]), len(self.session.run_boards[1])]
        self._on_state_advanced(prev_phase)

    def _advance_next_hand_or_match(self):
        if self.session.phase == "hand_over":
            if self.session.start_next_hand():
                self.prev_pot = self.session.game.pot
                self._trigger_new_hand_anims()
            self._sync_timers_and_controls()
        elif self.session.phase == "match_over":
            self.session.start_new_match()
            self.prev_pot = self.session.game.pot
            self._trigger_new_hand_anims()
            self._sync_timers_and_controls()

    def handle_event(self, event):
        if self.update_modal.visible:
            upd_action = self.update_modal.handle_event(event, self.updater.snapshot())
            if upd_action == "check":
                self.updater.check_async()
            elif upd_action == "update":
                self.updater.update_async()
            elif upd_action == "restart":
                self._restart_requested = True
            return

        if self.setup_modal.visible:
            new_cfg = self.setup_modal.handle_event(event)
            if new_cfg is not None:
                self.session.start_new_match(**new_cfg)
                self.prev_pot = self.session.game.pot
                self._trigger_new_hand_anims()
                self._sync_timers_and_controls()
            return

        if self.rules_modal.visible:
            self.rules_modal.handle_event(event)
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_m:
                muted = self.sounds.toggle_mute()
                self.btn_sound.label = "Sound: Off" if muted else "Sound: On"
                return
            if event.key == pygame.K_h:
                self.rules_modal.visible = True
                return
            if event.key == pygame.K_l:
                self.show_log = not self.show_log
                return

            if self.session.phase == "choose_run_count":
                if event.key == pygame.K_1:
                    self._choose_run_count(1)
                    return
                if event.key == pygame.K_2:
                    self._choose_run_count(2)
                    return

            if self.session.phase == "waiting_human":
                legal = self.session.get_legal_human_actions()
                if event.key == pygame.K_f and legal["can_fold"]:
                    self._submit_human({"action": "fold"})
                    return
                if event.key == pygame.K_c:
                    self._submit_human({"action": "check" if legal["can_check"] else "call"})
                    return
                if event.key == pygame.K_r and legal["can_raise"]:
                    self._submit_human({"action": "raise", "amount": self.raise_control.value})
                    return
                if event.key == pygame.K_a and legal["can_all_in"]:
                    self._submit_human({"action": "all_in"})
                    return
            elif self.session.phase in ("hand_over", "match_over"):
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self._advance_next_hand_or_match()
                    return

        if self.btn_update.handle_event(event):
            self.update_toast_dismissed = True
            self.update_modal.visible = True
            if self.updater.snapshot()["status"] == "idle":
                self.updater.check_async()
            return
        if self.btn_setup.handle_event(event):
            self.setup_modal.open_with(
                self.session.num_computers,
                self.session.starting_chips,
                self.session.small_blind,
                self.session.big_blind,
            )
            return
        if self.btn_log.handle_event(event):
            self.show_log = not self.show_log
        elif self.btn_sound.handle_event(event):
            muted = self.sounds.toggle_mute()
            self.btn_sound.label = "Sound: Off" if muted else "Sound: On"
        elif self.btn_rules.handle_event(event):
            self.rules_modal.visible = True
        elif self.btn_new_match.handle_event(event):
            self.session.start_new_match()
            self.prev_pot = self.session.game.pot
            self._trigger_new_hand_anims()
            self._sync_timers_and_controls()

        if self.session.phase == "choose_run_count":
            if self.btn_run_once.handle_event(event):
                self._choose_run_count(1)
                return
            if self.btn_run_twice.handle_event(event):
                self._choose_run_count(2)
                return

        self.raise_control.handle_event(event, self.session.game.pot)

        if self.btn_fold.handle_event(event):
            self._submit_human({"action": "fold"})
        elif self.btn_call.handle_event(event):
            legal = self.session.get_legal_human_actions()
            self._submit_human({"action": "check" if legal["can_check"] else "call"})
        elif self.btn_raise.handle_event(event):
            self._submit_human({"action": "raise", "amount": self.raise_control.value})
        elif self.btn_allin.handle_event(event):
            self._submit_human({"action": "all_in"})
        elif self.btn_next.handle_event(event):
            self._advance_next_hand_or_match()

    def update(self, dt):
        now = time.monotonic()

        for i, player in enumerate(self.session.game.players):
            target = float(player.chips)
            self.display_chips[i] = lerp(self.display_chips[i], target, min(1.0, dt * 12.0))
        self.display_pot = lerp(self.display_pot, float(self.session.game.pot), min(1.0, dt * 14.0))

        if self.btn_raise.enabled:
            self.btn_raise.label = f"Raise +${self.raise_control.value}"

        if self.session.phase == "computer_turn" and self.ai_wait_until > 0.0 and now >= self.ai_wait_until:
            self.ai_wait_until = 0.0
            prev_phase = self.session.phase
            self.session.step_computer_turn()
            self._on_state_advanced(prev_phase)

        elif self.session.phase == "reveal_board" and self.runout_wait_until > 0.0 and now >= self.runout_wait_until:
            self.runout_wait_until = 0.0
            prev_phase = self.session.phase
            self.session.step_reveal_board()
            self._on_state_advanced(prev_phase)

    def _animated_pos(self, key, target_pos, now):
        anim = self.card_anims.get(key)
        if not anim:
            return target_pos
        start_time, duration, from_pos = anim
        if now < start_time:
            return from_pos
        progress = (now - start_time) / max(0.01, duration)
        if progress >= 1.0:
            return target_pos
        eased = ease_out_cubic(progress)
        return (
            lerp(from_pos[0], target_pos[0], eased),
            lerp(from_pos[1], target_pos[1], eased),
        )

    def _winning_cards_for_board(self, res_dict):
        if not res_dict or not res_dict.get("pot_awards"):
            return set()
        winning = set()
        for award in res_dict["pot_awards"]:
            for w_idx in award["winners"]:
                p_res = res_dict["player_results"].get(w_idx)
                if p_res:
                    winning.update(p_res["best_five"])
        return winning

    def _winning_cards_single(self):
        if self.session.win_reason != "showdown" or not self.session.showdown_result:
            return set()
        if self.session.run_count == 2 and self.session.run_results:
            combined = set()
            for res in self.session.run_results:
                combined.update(self._winning_cards_for_board(res))
            return combined
        winning = set()
        for award in self.session.showdown_result.get("pot_awards", []):
            for w_idx in award["winners"]:
                p_res = self.session.showdown_result["player_results"][w_idx]
                if p_res:
                    winning.update(p_res["best_five"])
        return winning

    def _position_badge(self, player_index):
        if self.session.game.eliminated[player_index]:
            return None
        sb_idx, bb_idx = self.session.game._blind_positions()
        if player_index == self.session.game.button_index:
            return ("D", GOLD_BRIGHT, (20, 16, 8))
        if player_index == sb_idx:
            return ("SB", (36, 134, 108), TEXT_PRIMARY)
        if player_index == bb_idx:
            return ("BB", (58, 74, 102), TEXT_PRIMARY)
        return None

    def _draw_top_bar(self, now):
        bar_rect = pygame.Rect(0, 0, WINDOW_WIDTH, 48)
        pygame.draw.rect(self.screen, PANEL_BG, bar_rect)
        pygame.draw.line(self.screen, PANEL_BORDER, (0, 48), (WINDOW_WIDTH, 48), 1)

        pygame.draw.circle(self.screen, GOLD_BRIGHT, (24, 24), 6)
        draw_text(self.screen, self.fonts.get(17, bold=True), "TEXAS HOLD'EM", TEXT_PRIMARY, (40, 24), anchor="midleft")
        n_players = self.session.num_computers + 1
        meta = f"Hand #{self.session.hand_number}  •  Blinds ${self.session.small_blind}/${self.session.big_blind}  •  {n_players}P Table"
        draw_text(self.screen, self.fonts.get(13, bold=False), meta, TEXT_SECONDARY, (194, 24), anchor="midleft")

        upd = self.updater.snapshot()
        notify = upd["has_update"] or upd["restart_required"]
        if upd["restart_required"]:
            self.btn_update.label = "Restart!"
            self.btn_update.bg_color = BTN_CALL
            self.btn_update.hover_color = BTN_CALL_HOVER
        elif upd["has_update"]:
            self.btn_update.label = "Update !"
            self.btn_update.bg_color = BTN_CALL
            self.btn_update.hover_color = BTN_CALL_HOVER
        elif upd["status"] == "updating":
            self.btn_update.label = "Updating"
            self.btn_update.bg_color = BTN_RAISE
            self.btn_update.hover_color = BTN_RAISE_HOVER
        elif upd["status"] == "checking":
            self.btn_update.label = "Checking"
            self.btn_update.bg_color = BTN_NEUTRAL
            self.btn_update.hover_color = BTN_NEUTRAL_HOVER
        else:
            self.btn_update.label = "Update"
            self.btn_update.bg_color = BTN_NEUTRAL
            self.btn_update.hover_color = BTN_NEUTRAL_HOVER

        for btn in (self.btn_update, self.btn_setup, self.btn_log, self.btn_sound, self.btn_rules, self.btn_new_match):
            btn.draw(self.screen, self.fonts.palette)

        # Pulsing red notification dot on Update button when GitHub has a new commit
        if notify:
            dot_center = (self.btn_update.rect.right - 3, self.btn_update.rect.top + 3)
            pulse = 0.5 + 0.5 * abs((now * 2.8) % 2.0 - 1.0)
            outer_r = int(7 + pulse * 3)
            halo = pygame.Surface((26, 26), pygame.SRCALPHA)
            pygame.draw.circle(halo, (238, 68, 68, int(90 * (1.0 - 0.4 * pulse))), (13, 13), outer_r)
            self.screen.blit(halo, (dot_center[0] - 13, dot_center[1] - 13))
            pygame.draw.circle(self.screen, (238, 68, 68), dot_center, 6)
            pygame.draw.circle(self.screen, TEXT_PRIMARY, dot_center, 6, width=1)

        if upd["has_update"] and not self.update_toast_dismissed and not self.update_modal.visible:
            toast = pygame.Rect(18, 54, 346, 24)
            pygame.draw.rect(self.screen, (16, 42, 34), toast, border_radius=12)
            pygame.draw.rect(self.screen, GOLD_BRIGHT, toast, width=1, border_radius=12)
            draw_text(
                self.screen,
                self.fonts.get(11, bold=True),
                f"New update ({upd['short_sha']}) on GitHub! Click 'Update !'",
                GOLD_BRIGHT,
                toast.center,
                anchor="center",
            )

    def _draw_equity_pill(self, x, y, width, player_index):
        if player_index not in self.session.equities:
            return
        pct = self.session.equities[player_index]
        max_pct = max(self.session.equities.values(), default=0.0)
        is_lead = pct >= max_pct - 0.1

        pill = pygame.Rect(x, y, width, 20)
        pygame.draw.rect(self.screen, (14, 20, 28), pill, border_radius=6)
        fill_w = max(4, int((width - 2) * min(100.0, pct) / 100.0))
        fill_col = (34, 148, 102) if is_lead else (66, 92, 132)
        pygame.draw.rect(self.screen, fill_col, pygame.Rect(x + 1, y + 1, fill_w, 18), border_radius=5)
        pygame.draw.rect(self.screen, GOLD_BRIGHT if is_lead else PANEL_BORDER, pill, width=1, border_radius=6)
        draw_text(
            self.screen,
            self.fonts.get(11, bold=True),
            f"WIN {pct:.1f}%",
            TEXT_PRIMARY,
            pill.center,
            anchor="center",
        )

    def _draw_human_panel(self, now):
        rect = pygame.Rect(348, 482, 266, 102)
        is_active = self.session.phase == "waiting_human"
        player = self.session.game.players[0]
        chips_val = int(round(self.display_chips[0]))
        last_action = self.session.last_actions[0]

        if is_active:
            pulse = 0.55 + 0.45 * abs((now * 2.2) % 2.0 - 1.0)
            glow_col = tuple(int(lerp(GOLD_DIM[i], GOLD_BRIGHT[i], pulse)) for i in range(3))
            pygame.draw.rect(self.screen, glow_col, rect.inflate(6, 6), width=2, border_radius=15)

        pygame.draw.rect(self.screen, PANEL_BG, rect, border_radius=12)
        pygame.draw.rect(self.screen, GOLD_MID if is_active else PANEL_BORDER, rect, width=1, border_radius=12)

        avatar_center = (rect.left + 30, rect.top + 32)
        pygame.draw.circle(self.screen, (28, 96, 74), avatar_center, 18)
        pygame.draw.circle(self.screen, GOLD_MID, avatar_center, 18, width=2)
        draw_text(self.screen, self.fonts.get(14, bold=True), "ME", TEXT_PRIMARY, avatar_center, anchor="center")

        draw_text(self.screen, self.fonts.get(15, bold=True), player.name, TEXT_PRIMARY, (rect.left + 58, rect.top + 13))
        draw_text(self.screen, self.fonts.get(19, bold=True), f"${chips_val}", GOLD_BRIGHT, (rect.left + 58, rect.top + 32))

        badge = self._position_badge(0)
        if badge:
            label, bg, fg = badge
            puck_center = (rect.right - 22, rect.top + 22)
            pygame.draw.circle(self.screen, bg, puck_center, 12)
            draw_text(self.screen, self.fonts.get(10, bold=True), label, fg, puck_center, anchor="center")

        tag_y = rect.bottom - 18
        if last_action:
            pill_w = min(124, max(74, len(last_action) * 8 + 18))
            pill_rect = pygame.Rect(rect.left + 14, tag_y - 11, pill_w, 22)
            pygame.draw.rect(self.screen, _badge_color(last_action), pill_rect, border_radius=6)
            draw_text(self.screen, self.fonts.get(11, bold=True), last_action, TEXT_PRIMARY, pill_rect.center, anchor="center")

        extra = self.session.get_human_best_hand_name()
        if self.session.win_reason == "showdown" and self.session.showdown_result:
            res = self.session.showdown_result["player_results"][0]
            if res:
                extra = res["hand_name"]
        if extra:
            draw_text(self.screen, self.fonts.get(12, bold=True), extra, TEXT_SECONDARY, (rect.right - 14, tag_y), anchor="midright")

        if self.session.phase in ("choose_run_count", "reveal_board", "hand_over") and 0 in self.session.equities:
            self._draw_equity_pill(rect.left, rect.bottom + 6, rect.width, 0)

    def _draw_1v1_computer(self, now, reveal_all, winning_set):
        rect = pygame.Rect(374, 94, 248, 92)
        is_active = self.session.phase == "computer_turn" and self.session.pending and self.session.pending[0] == 1
        player = self.session.game.players[1]
        chips_val = int(round(self.display_chips[1]))
        last_action = self.session.last_actions[1]

        if is_active:
            pulse = 0.55 + 0.45 * abs((now * 2.2) % 2.0 - 1.0)
            glow_col = tuple(int(lerp(GOLD_DIM[i], GOLD_BRIGHT[i], pulse)) for i in range(3))
            pygame.draw.rect(self.screen, glow_col, rect.inflate(6, 6), width=2, border_radius=15)

        pygame.draw.rect(self.screen, PANEL_BG, rect, border_radius=12)
        pygame.draw.rect(self.screen, GOLD_MID if is_active else PANEL_BORDER, rect, width=1, border_radius=12)

        avatar_center = (rect.left + 30, rect.top + 32)
        pygame.draw.circle(self.screen, (42, 68, 108), avatar_center, 18)
        pygame.draw.circle(self.screen, PANEL_BORDER, avatar_center, 18, width=2)
        draw_text(self.screen, self.fonts.get(14, bold=True), "AI", TEXT_PRIMARY, avatar_center, anchor="center")

        draw_text(self.screen, self.fonts.get(15, bold=True), player.name, TEXT_PRIMARY, (rect.left + 58, rect.top + 13))
        draw_text(self.screen, self.fonts.get(19, bold=True), f"${chips_val}", GOLD_BRIGHT, (rect.left + 58, rect.top + 32))

        badge = self._position_badge(1)
        if badge:
            label, bg, fg = badge
            puck_center = (rect.right - 22, rect.top + 22)
            pygame.draw.circle(self.screen, bg, puck_center, 12)
            draw_text(self.screen, self.fonts.get(10, bold=True), label, fg, puck_center, anchor="center")

        extra = ""
        if is_active:
            extra = "Thinking" + "." * (1 + int(now * 3) % 3)
        elif self.session.win_reason == "showdown" and self.session.showdown_result:
            res = self.session.showdown_result["player_results"][1]
            if res:
                extra = res["hand_name"]

        tag_y = rect.bottom - 18
        if last_action:
            pill_w = min(124, max(74, len(last_action) * 8 + 18))
            pill_rect = pygame.Rect(rect.left + 14, tag_y - 11, pill_w, 22)
            pygame.draw.rect(self.screen, _badge_color(last_action), pill_rect, border_radius=6)
            draw_text(self.screen, self.fonts.get(11, bold=True), last_action, TEXT_PRIMARY, pill_rect.center, anchor="center")
        if extra:
            draw_text(self.screen, self.fonts.get(12, bold=True), extra, TEXT_SECONDARY, (rect.right - 14, tag_y), anchor="midright")

        if self.session.phase in ("choose_run_count", "reveal_board", "hand_over") and 1 in self.session.equities:
            self._draw_equity_pill(rect.left, rect.top - 24, rect.width, 1)

        if self.session.phase not in ("hand_over", "match_over"):
            self._draw_bet_pill((856, 140), self.session.game.round_bets[1])

        face_up = reveal_all and not self.session.game.folded[1]
        is_showdown = self.session.win_reason == "showdown"
        for idx, card in enumerate(player.hole_cards):
            tx, ty = COMP_CARD_POS_1V1[idx]
            in_best = face_up and (card in winning_set)
            if is_showdown and in_best:
                ty += 6
            pos = self._animated_pos((1, idx), (tx, ty), now)
            self.card_renderer.draw_card(
                self.screen,
                card,
                pos,
                face_up=face_up,
                small=True,
                highlighted=(is_showdown and in_best),
                dimmed=(is_showdown and bool(winning_set) and not in_best),
            )

    def _draw_compact_ai_seat(self, player_index, seat_x, seat_y, bet_center, now, reveal_all, winning_set):
        player = self.session.game.players[player_index]
        eliminated = self.session.game.eliminated[player_index]
        folded = self.session.game.folded[player_index]
        is_active = (
            self.session.phase == "computer_turn"
            and bool(self.session.pending)
            and self.session.pending[0] == player_index
        )

        # Nameplate (142x80) + 2 mini cards (52x74) side by side
        plate = pygame.Rect(seat_x, seat_y, 142, 80)
        if is_active:
            pulse = 0.55 + 0.45 * abs((now * 2.2) % 2.0 - 1.0)
            glow_col = tuple(int(lerp(GOLD_DIM[i], GOLD_BRIGHT[i], pulse)) for i in range(3))
            pygame.draw.rect(self.screen, glow_col, plate.inflate(5, 5), width=2, border_radius=12)

        bg_col = (14, 18, 26) if (eliminated or folded) else PANEL_BG
        pygame.draw.rect(self.screen, bg_col, plate, border_radius=10)
        pygame.draw.rect(
            self.screen,
            GOLD_MID if is_active else PANEL_BORDER,
            plate,
            width=1,
            border_radius=10,
        )

        name_col = TEXT_MUTED if (eliminated or folded) else TEXT_PRIMARY
        chip_col = TEXT_MUTED if (eliminated or folded) else GOLD_BRIGHT
        draw_text(self.screen, self.fonts.get(13, bold=True), player.name, name_col, (plate.left + 10, plate.top + 8))

        chips_val = int(round(self.display_chips[player_index]))
        draw_text(self.screen, self.fonts.get(16, bold=True), f"${chips_val}", chip_col, (plate.left + 10, plate.top + 26))

        badge = self._position_badge(player_index)
        if badge:
            label, bg, fg = badge
            puck = (plate.right - 16, plate.top + 16)
            pygame.draw.circle(self.screen, bg, puck, 10)
            draw_text(self.screen, self.fonts.get(9, bold=True), label, fg, puck, anchor="center")

        action_lbl = self.session.last_actions[player_index]
        if is_active:
            action_lbl = "Thinking" + "." * (1 + int(now * 3) % 3)
        elif self.session.win_reason == "showdown" and self.session.showdown_result and not folded:
            res = self.session.showdown_result["player_results"][player_index]
            if res:
                action_lbl = res["hand_name"]

        if action_lbl:
            pill_rect = pygame.Rect(plate.left + 8, plate.bottom - 24, plate.width - 16, 18)
            pill_bg = PANEL_BORDER if is_active else _badge_color(action_lbl)
            pygame.draw.rect(self.screen, pill_bg, pill_rect, border_radius=5)
            draw_text(self.screen, self.fonts.get(10, bold=True), action_lbl, TEXT_PRIMARY, pill_rect.center, anchor="center")

        if (
            self.session.phase in ("choose_run_count", "reveal_board", "hand_over")
            and player_index in self.session.equities
            and not folded
            and not eliminated
        ):
            self._draw_equity_pill(plate.left, plate.top - 22, plate.width, player_index)

        if self.session.phase not in ("hand_over", "match_over"):
            self._draw_bet_pill(bet_center, self.session.game.round_bets[player_index])

        if not eliminated and not folded:
            face_up = reveal_all
            is_showdown = self.session.win_reason == "showdown"
            cards_x = plate.right + 6
            cards_y = plate.top + 3
            for idx, card in enumerate(player.hole_cards):
                tx = cards_x + idx * (MINI_CARD_WIDTH + 5)
                ty = cards_y
                in_best = face_up and (card in winning_set)
                if is_showdown and in_best:
                    ty -= 5
                pos = self._animated_pos((player_index, idx), (tx, ty), now)
                self.card_renderer.draw_card(
                    self.screen,
                    card,
                    pos,
                    face_up=face_up,
                    card_size=(MINI_CARD_WIDTH, MINI_CARD_HEIGHT),
                    highlighted=(is_showdown and in_best),
                    dimmed=(is_showdown and bool(winning_set) and not in_best),
                )

    def _draw_bet_pill(self, center, amount):
        if amount <= 0:
            return
        draw_chip_stack(self.screen, center[0] - 26, center[1] + 2, amount)
        pill_rect = pygame.Rect(center[0] - 10, center[1] - 12, 62, 24)
        pygame.draw.rect(self.screen, (14, 24, 20), pill_rect, border_radius=12)
        pygame.draw.rect(self.screen, GOLD_DIM, pill_rect, width=1, border_radius=12)
        draw_text(self.screen, self.fonts.get(12, bold=True), f"${amount}", GOLD_BRIGHT, pill_rect.center, anchor="center")

    def _draw_center_table(self, now):
        # Street indicator pill
        street_label = self.session.street.replace("_", "-").upper()
        if self.session.num_computers <= 2:
            street_rect = pygame.Rect(184, 326, 134, 30)
        else:
            street_rect = pygame.Rect(354, 208, 120, 30)
        pygame.draw.rect(self.screen, FELT_DARK, street_rect, border_radius=15)
        pygame.draw.rect(self.screen, GOLD_DIM, street_rect, width=1, border_radius=15)
        draw_text(self.screen, self.fonts.get(12, bold=True), street_label, GOLD_BRIGHT, street_rect.center, anchor="center")

        # Pot badge + chip stack
        if self.session.phase in ("hand_over", "match_over"):
            pot_val = self.session.pot_awarded
            pot_label = f"AWARDED  ${pot_val}"
            pot_rect = pygame.Rect(528, 206, 174, 34)
            chip_x, chip_y = 506, 224
        else:
            pot_val = int(round(self.display_pot))
            pot_label = f"POT  ${pot_val}"
            pot_rect = pygame.Rect(548, 206, 144, 34)
            chip_x, chip_y = 526, 224

        draw_chip_stack(self.screen, chip_x, chip_y, max(1, pot_val))
        pygame.draw.rect(self.screen, (12, 22, 18), pot_rect, border_radius=17)
        pygame.draw.rect(self.screen, GOLD_MID, pot_rect, width=1, border_radius=17)
        draw_text(self.screen, self.fonts.get(14, bold=True), pot_label, GOLD_BRIGHT, pot_rect.center, anchor="center")

        # Deck shoe when side wing is free
        if self.session.num_computers <= 2:
            for offset in (4, 2, 0):
                self.card_renderer.draw_card(
                    self.screen,
                    None,
                    (DECK_POS[0] + offset, DECK_POS[1] - offset),
                    face_up=False,
                    small=True,
                )

        # Dual-board Run It Twice display OR single-board display
        if self.session.run_count == 2 and self.session.run_boards:
            self._draw_dual_boards(now)
        else:
            winning_set = self._winning_cards_single()
            is_showdown = self.session.win_reason == "showdown"
            for idx, card in enumerate(self.session.game.board):
                target_x = BOARD_START_X + idx * (CARD_WIDTH + BOARD_GAP)
                target_y = BOARD_CARD_Y
                in_best = card in winning_set
                if is_showdown and in_best:
                    target_y -= 10
                pos = self._animated_pos(("board", idx), (target_x, target_y), now)
                self.card_renderer.draw_card(
                    self.screen,
                    card,
                    pos,
                    face_up=True,
                    highlighted=(is_showdown and in_best),
                    dimmed=(is_showdown and bool(winning_set) and not in_best),
                )

    def _draw_dual_boards(self, now):
        arena = pygame.Rect(344, 248, 512, 208)
        pygame.draw.rect(self.screen, (10, 36, 26), arena, border_radius=14)
        pygame.draw.rect(self.screen, GOLD_DIM, arena, width=1, border_radius=14)

        is_showdown = self.session.win_reason == "showdown"
        is_revealing = self.session.phase == "reveal_board"
        row_ys = [256, 356]
        for run_idx in range(2):
            ry = row_ys[run_idx]
            is_active_run = is_revealing and self.session.active_run_index == run_idx
            label_rect = pygame.Rect(354, ry + 32, 66, 28)
            pygame.draw.rect(self.screen, GOLD_BRIGHT if is_active_run else PANEL_BG, label_rect, border_radius=8)
            pygame.draw.rect(self.screen, GOLD_BRIGHT if is_active_run else GOLD_MID, label_rect, width=1, border_radius=8)
            draw_text(
                self.screen,
                self.fonts.get(12, bold=True),
                f"RUN {run_idx + 1}",
                (20, 16, 8) if is_active_run else GOLD_BRIGHT,
                label_rect.center,
                anchor="center",
            )

            win_set = set()
            if is_showdown and len(self.session.run_results) == 2:
                win_set = self._winning_cards_for_board(self.session.run_results[run_idx])

            board = self.session.run_boards[run_idx]
            for c_idx in range(5):
                cx = 434 + c_idx * (DUAL_CARD_WIDTH + 8)
                if c_idx < len(board):
                    card = board[c_idx]
                    in_best = card in win_set
                    target_pos = (cx, ry - (4 if (is_showdown and in_best) else 0))
                    pos = self._animated_pos(("run", run_idx, c_idx), target_pos, now)
                    self.card_renderer.draw_card(
                        self.screen,
                        card,
                        pos,
                        face_up=True,
                        card_size=(DUAL_CARD_WIDTH, DUAL_CARD_HEIGHT),
                        highlighted=(is_showdown and in_best),
                        dimmed=(is_showdown and bool(win_set) and not in_best),
                    )
                else:
                    slot_border = GOLD_MID if (is_active_run and c_idx == len(board)) else (18, 62, 46)
                    pygame.draw.rect(
                        self.screen,
                        (7, 28, 20),
                        pygame.Rect(cx, ry, DUAL_CARD_WIDTH, DUAL_CARD_HEIGHT),
                        border_radius=7,
                    )
                    pygame.draw.rect(
                        self.screen,
                        slot_border,
                        pygame.Rect(cx, ry, DUAL_CARD_WIDTH, DUAL_CARD_HEIGHT),
                        width=1,
                        border_radius=7,
                    )

    def _draw_players_and_cards(self, now):
        reveal_all = (
            self.session.win_reason == "showdown"
            or self.session.phase in ("choose_run_count", "reveal_board")
        )
        winning_set = self._winning_cards_single()
        is_showdown = self.session.win_reason == "showdown"

        # Draw Human seat
        self._draw_human_panel(now)
        if self.session.phase not in ("hand_over", "match_over"):
            self._draw_bet_pill((856, 530), self.session.game.round_bets[0])

        human = self.session.game.players[0]
        human_folded = self.session.game.folded[0] or self.session.game.eliminated[0]
        if not self.session.game.eliminated[0]:
            for idx, card in enumerate(human.hole_cards):
                tx, ty = HUMAN_CARD_POS[idx]
                in_best = card in winning_set
                if is_showdown and in_best:
                    ty -= 10
                pos = self._animated_pos((0, idx), (tx, ty), now)
                self.card_renderer.draw_card(
                    self.screen,
                    card,
                    pos,
                    face_up=True,
                    highlighted=(is_showdown and in_best),
                    dimmed=human_folded or (is_showdown and bool(winning_set) and not in_best),
                )

        # Draw AI seats
        if self.session.num_computers == 1:
            self._draw_1v1_computer(now, reveal_all, winning_set)
        else:
            layout = RING_SEAT_LAYOUTS[self.session.num_computers]
            for ai_idx in range(1, self.session.num_computers + 1):
                sx, sy, bet_center = layout[ai_idx - 1]
                self._draw_compact_ai_seat(
                    ai_idx, sx, sy, bet_center, now, reveal_all, winning_set
                )

    def _draw_runout_choice_overlay(self):
        if self.session.phase != "choose_run_count":
            return

        box = pygame.Rect(386, 368, 428, 96)
        pygame.draw.rect(self.screen, (14, 20, 30), box, border_radius=14)
        pygame.draw.rect(self.screen, GOLD_BRIGHT, box, width=2, border_radius=14)
        draw_text(
            self.screen,
            self.fonts.get(14, bold=True),
            "ALL-IN RUNOUT — CHOOSE HOW TO DEAL",
            GOLD_BRIGHT,
            (box.centerx, box.top + 22),
            anchor="center",
        )
        self.btn_run_once.draw(self.screen, self.fonts.palette)
        self.btn_run_twice.draw(self.screen, self.fonts.palette)

    def _draw_result_banner(self):
        if self.session.phase == "reveal_board" and self.session.runout_status:
            banner = pygame.Rect(618, 598, 550, 32) if self.session.run_count == 2 else pygame.Rect(336, 418, 528, 34)
            pygame.draw.rect(self.screen, (14, 20, 30), banner, border_radius=16)
            pygame.draw.rect(self.screen, GOLD_MID, banner, width=1, border_radius=16)
            draw_text(
                self.screen,
                self.fonts.get(13, bold=True),
                self.session.runout_status,
                GOLD_BRIGHT,
                banner.center,
                anchor="center",
            )
            return

        if self.session.phase not in ("hand_over", "match_over"):
            return

        if self.session.phase == "match_over":
            human_chips = self.session.game.players[0].chips
            if human_chips > 0 and all(p.chips <= 0 for p in self.session.game.players[1:]):
                msg = f"CHAMPION! YOU WON THE TABLE (${human_chips})"
                accent = GOLD_BRIGHT
            else:
                msg = "ELIMINATED — BETTER LUCK NEXT MATCH"
                accent = (240, 128, 128)
        elif self.session.run_count == 2 and self.session.run_results:
            r1 = self.session.run_results[0]["pot_awards"]
            r2 = self.session.run_results[1]["pot_awards"]
            w1 = ", ".join(self.session.game.players[i].name for i in r1[0]["winners"]) if r1 else "-"
            w2 = ", ".join(self.session.game.players[i].name for i in r2[0]["winners"]) if r2 else "-"
            msg = f"RUN 1: {w1.upper()}   •   RUN 2: {w2.upper()}"
            accent = GOLD_BRIGHT
        else:
            winner = self.session.winner_index
            pot = self.session.pot_awarded
            if self.session.win_reason == "fold":
                w_name = self.session.game.players[winner].name.upper()
                verb = "WIN" if winner == 0 else "WINS"
                msg = f"{w_name} {verb} ${pot}  •  OTHERS FOLDED"
                accent = GOLD_BRIGHT if winner == 0 else (240, 132, 132)
            elif winner is not None:
                w_name = self.session.game.players[winner].name.upper()
                hand_name = self.session.showdown_result["player_results"][winner]["hand_name"].upper()
                verb = "WIN" if winner == 0 else "WINS"
                msg = f"{w_name} {verb} ${pot}  •  {hand_name}"
                accent = GOLD_BRIGHT if winner == 0 else (240, 132, 132)
            else:
                msg = f"POT SPLIT (${pot}) — SEE LOG FOR SIDE POTS"
                accent = (132, 212, 250)

        banner_y = 460 if self.session.run_count == 2 else 418
        banner = pygame.Rect(336, banner_y, 528, 34)
        if self.session.run_count == 2:
            # Place Run It Twice banner neatly in top-of-dock/below board without hitting human panel
            banner = pygame.Rect(618, 598, 550, 32)
        pygame.draw.rect(self.screen, (14, 20, 30), banner, border_radius=16)
        pygame.draw.rect(self.screen, accent, banner, width=1, border_radius=16)
        draw_text(self.screen, self.fonts.get(14, bold=True), msg, accent, banner.center, anchor="center")

    def _draw_bottom_dock(self):
        dock_rect = pygame.Rect(0, 638, WINDOW_WIDTH, WINDOW_HEIGHT - 638)
        pygame.draw.rect(self.screen, PANEL_BG, dock_rect)
        pygame.draw.line(self.screen, PANEL_BORDER, (0, 638), (WINDOW_WIDTH, 638), 1)

        if self.session.phase == "waiting_human":
            legal = self.session.get_legal_human_actions()
            hint = "Your turn — Check or Raise" if legal["can_check"] else f"Your turn — ${legal['to_call']} to call"
            hint_col = GOLD_BRIGHT
        elif self.session.phase == "computer_turn":
            idx = self.session.pending[0] if self.session.pending else 1
            hint = f"{self.session.game.players[idx].name} is thinking..."
            hint_col = TEXT_SECONDARY
        elif self.session.phase == "choose_run_count":
            hint = "All-in! Choose Run Once [1] or Run Twice [2]"
            hint_col = GOLD_BRIGHT
        elif self.session.phase == "reveal_board":
            if self.session.run_count == 2:
                hint = f"All-in runout — RUN {self.session.active_run_index + 1} dealing..."
            else:
                hint = "All-in runout — Dealing card..."
            hint_col = GOLD_BRIGHT
        elif self.session.phase == "hand_over":
            hint = "Hand finished — Click Next Hand"
            hint_col = TEXT_SECONDARY
        else:
            hint = "Match finished — Click Play Again"
            hint_col = GOLD_BRIGHT

        draw_text(self.screen, self.fonts.get(12, bold=True), hint, hint_col, (28, 645))

        for btn in (self.btn_fold, self.btn_call, self.btn_raise, self.btn_allin, self.btn_next):
            btn.draw(self.screen, self.fonts.palette)
        self.raise_control.draw(self.screen, self.fonts.palette)

    def _draw_log_drawer(self):
        if not self.show_log:
            return

        drawer = pygame.Rect(904, 62, 280, 388)
        overlay = pygame.Surface((drawer.width, drawer.height), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (*PANEL_BG, 238), overlay.get_rect(), border_radius=12)
        pygame.draw.rect(overlay, PANEL_BORDER, overlay.get_rect(), width=1, border_radius=12)
        self.screen.blit(overlay, drawer.topleft)

        draw_text(self.screen, self.fonts.get(14, bold=True), "Action Log", GOLD_BRIGHT, (drawer.left + 14, drawer.top + 12))
        pygame.draw.line(self.screen, PANEL_BORDER, (drawer.left + 10, drawer.top + 38), (drawer.right - 10, drawer.top + 38), 1)

        lines = self.session.action_log[-14:]
        line_font = self.fonts.get(12, bold=False)
        y = drawer.top + 48
        for entry in lines:
            col = GOLD_BRIGHT if entry.startswith("---") or "win" in entry or "Run " in entry else TEXT_SECONDARY
            text = entry if len(entry) <= 36 else entry[:33] + "..."
            draw_text(self.screen, line_font, text, col, (drawer.left + 14, y))
            y += 23

    def render(self):
        now = time.monotonic()
        self.screen.blit(self.table_surface, (0, 0))
        self._draw_top_bar(now)
        self._draw_center_table(now)
        self._draw_players_and_cards(now)
        self._draw_runout_choice_overlay()
        self._draw_result_banner()
        self._draw_bottom_dock()
        self._draw_log_drawer()
        self.rules_modal.draw(self.screen, self.fonts.palette)
        self.setup_modal.draw(self.screen, self.fonts.palette)
        self.update_modal.draw(self.screen, self.fonts.palette, self.updater.snapshot())
        pygame.display.flip()

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                self.handle_event(event)
            if self._restart_requested:
                running = False
                break
            self.update(dt)
            self.render()
        pygame.quit()
        if self._restart_requested:
            subprocess.Popen([sys.executable, os.path.abspath(__file__)], cwd=self.app_dir)


def main():
    app = PokerTableApp()
    app.run()


if __name__ == "__main__":
    main()
