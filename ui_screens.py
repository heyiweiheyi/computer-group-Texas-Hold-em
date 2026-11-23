"""Title cover screen and 12-AI opponent selection screen for Texas Hold'em."""

import math
import random

import pygame

from texas_holdem import AI_ROSTER, AI_TIER_SETTINGS, Card
from ui_assets import draw_chip_stack
from ui_theme import (
    BG_OUTER,
    BTN_CALL,
    BTN_CALL_HOVER,
    BTN_NEUTRAL,
    BTN_NEUTRAL_HOVER,
    BTN_RAISE,
    BTN_RAISE_HOVER,
    GOLD_BRIGHT,
    GOLD_DIM,
    GOLD_MID,
    PANEL_BG,
    PANEL_BG_ALT,
    PANEL_BORDER,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TIER_COLORS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    draw_text,
)
from ui_widgets import ActionButton


class TitleScreen:
    """Casino cover screen shown on launch before selecting opponents."""

    ROYAL_CARDS = [
        Card(10, "♠"),
        Card(11, "♠"),
        Card(12, "♠"),
        Card(13, "♠"),
        Card(14, "♠"),
    ]

    def __init__(self):
        self.btn_start = ActionButton(
            ((WINDOW_WIDTH - 270) // 2, 514, 270, 58),
            "START GAME",
            BTN_CALL,
            BTN_CALL_HOVER,
            shortcut="Enter",
            radius=14,
        )
        self.btn_saves = ActionButton(
            (610, 514, 246, 56),
            "SAVED GAMES (0/3)",
            BTN_RAISE,
            BTN_RAISE_HOVER,
            radius=14,
        )
        self.btn_rules = ActionButton(
            (WINDOW_WIDTH - 196, 18, 86, 34),
            "Rules ?",
            BTN_NEUTRAL,
            BTN_NEUTRAL_HOVER,
            radius=9,
        )
        self.btn_update = ActionButton(
            (WINDOW_WIDTH - 306, 18, 100, 34),
            "Update",
            BTN_NEUTRAL,
            BTN_NEUTRAL_HOVER,
            radius=9,
        )
        self._rotated_cache = {}

    def _layout_buttons(self, saves_count):
        if saves_count > 0:
            self.btn_start.rect = pygame.Rect(344, 514, 246, 56)
            self.btn_saves.rect = pygame.Rect(610, 514, 246, 56)
            self.btn_saves.label = f"SAVED GAMES ({saves_count}/3)"
        else:
            self.btn_start.rect = pygame.Rect((WINDOW_WIDTH - 270) // 2, 514, 270, 58)

    def _get_fanned_card(self, card_renderer, idx, angle):
        key = (idx, angle)
        if key not in self._rotated_cache:
            card = self.ROYAL_CARDS[idx]
            surf = card_renderer._face_cache[(card.rank, card.suit, (88, 126))]
            self._rotated_cache[key] = pygame.transform.rotozoom(surf, angle, 1.08)
        return self._rotated_cache[key]

    def handle_event(self, event, saves_count=0):
        """Return 'start', 'saves', 'rules', 'update', or None."""
        self._layout_buttons(saves_count)
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            return "start"
        if self.btn_start.handle_event(event):
            return "start"
        if saves_count > 0 and self.btn_saves.handle_event(event):
            return "saves"
        if self.btn_rules.handle_event(event):
            return "rules"
        if self.btn_update.handle_event(event):
            return "update"
        return None

    def draw(self, surface, fonts, table_surface, card_renderer, upd_state, now, saves_count=0):
        self._layout_buttons(saves_count)
        surface.blit(table_surface, (0, 0))

        # Deep atmospheric vignette over the table
        veil = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        veil.fill((8, 13, 20, 178))
        surface.blit(veil, (0, 0))

        # Center framed casino showcase card
        hero = pygame.Rect(210, 92, 780, 548)
        hero_bg = pygame.Surface((hero.width, hero.height), pygame.SRCALPHA)
        pygame.draw.rect(hero_bg, (14, 22, 32, 226), hero_bg.get_rect(), border_radius=24)
        pygame.draw.rect(hero_bg, (*GOLD_MID, 210), hero_bg.get_rect(), width=2, border_radius=24)
        pygame.draw.rect(
            hero_bg,
            (*GOLD_DIM, 110),
            hero_bg.get_rect().inflate(-16, -16),
            width=1,
            border_radius=18,
        )
        surface.blit(hero_bg, hero.topleft)

        # Fanned Royal Flush centerpiece with subtle floating motion
        bob = math.sin(now * 1.7) * 4.0
        angles = [18, 9, 0, -9, -18]
        offsets_x = [-118, -60, 0, 60, 118]
        offsets_y = [20, 6, 0, 6, 20]
        for idx in range(5):
            rot = self._get_fanned_card(card_renderer, idx, angles[idx])
            rect = rot.get_rect(center=(WINDOW_WIDTH // 2 + offsets_x[idx], int(238 + offsets_y[idx] + bob)))
            surface.blit(rot, rect)

        # Decorative chip stacks flanking the fan
        draw_chip_stack(surface, 344, 286, 500)
        draw_chip_stack(surface, 374, 296, 125)
        draw_chip_stack(surface, 856, 286, 500)
        draw_chip_stack(surface, 826, 296, 125)

        draw_text(
            surface,
            fonts.get(13, bold=True),
            "COMPUTER GROUP   •   NO-LIMIT POKER ARENA",
            GOLD_MID,
            (WINDOW_WIDTH // 2, 352),
            anchor="center",
        )
        draw_text(
            surface,
            fonts.get(46, bold=True),
            "TEXAS HOLD'EM",
            GOLD_BRIGHT,
            (WINDOW_WIDTH // 2, 404),
            anchor="center",
        )
        draw_text(
            surface,
            fonts.get(15, bold=False),
            "2–6 Players  •  12 Tiered AI Opponents  •  Side Pots & Run It Twice",
            TEXT_SECONDARY,
            (WINDOW_WIDTH // 2, 456),
            anchor="center",
        )

        self.btn_start.draw(surface, fonts)
        if saves_count > 0:
            self.btn_saves.draw(surface, fonts)

        hint_txt = (
            "Start a new table or resume one of your saved unfinished matches"
            if saves_count > 0
            else "Click START GAME or press Enter to pick your table size and AI rivals"
        )
        draw_text(
            surface,
            fonts.get(12, bold=False),
            hint_txt,
            TEXT_MUTED,
            (WINDOW_WIDTH // 2, 604),
            anchor="center",
        )

        # Top-right Update & Rules buttons
        notify = upd_state["has_update"] or upd_state["restart_required"]
        if upd_state["restart_required"]:
            self.btn_update.label = "Restart!"
            self.btn_update.bg_color = BTN_CALL
            self.btn_update.hover_color = BTN_CALL_HOVER
        elif upd_state["has_update"]:
            self.btn_update.label = "Update !"
            self.btn_update.bg_color = BTN_CALL
            self.btn_update.hover_color = BTN_CALL_HOVER
        else:
            self.btn_update.label = "Update"
            self.btn_update.bg_color = BTN_NEUTRAL
            self.btn_update.hover_color = BTN_NEUTRAL_HOVER

        self.btn_update.draw(surface, fonts)
        self.btn_rules.draw(surface, fonts)

        if notify:
            dot = (self.btn_update.rect.right - 3, self.btn_update.rect.top + 3)
            pygame.draw.circle(surface, (238, 68, 68), dot, 6)
            pygame.draw.circle(surface, TEXT_PRIMARY, dot, 6, width=1)
            toast = pygame.Rect(24, 22, 348, 26)
            pygame.draw.rect(surface, (16, 42, 34), toast, border_radius=13)
            pygame.draw.rect(surface, GOLD_BRIGHT, toast, width=1, border_radius=13)
            draw_text(
                surface,
                fonts.get(11, bold=True),
                f"New update ({upd_state['short_sha']}) on GitHub! Click 'Update !'",
                GOLD_BRIGHT,
                toast.center,
                anchor="center",
            )


class OpponentSelectScreen:
    """Interactive roster screen to choose table size (2-6P), stakes, and specific AI opponents."""

    CHIP_OPTIONS = [300, 500, 1000]
    BLIND_OPTIONS = [(5, 10), (10, 20), (25, 50)]
    TIER_ORDER = ["Ultra", "Master", "Pro", "Normal", "Rookie"]

    def __init__(self, max_computers=5):
        self.max_computers = max_computers
        self.num_computers = 3
        self.starting_chips = 500
        self.blinds = (5, 10)
        self.selected_names = [AI_ROSTER[0]["name"], AI_ROSTER[2]["name"], AI_ROSTER[5]["name"]]
        self.hovered_card_idx = -1
        self.can_resume = False
        self.active_cfg = None
        self.active_hand_number = 0

        # Header Saves button
        self.btn_saves = ActionButton((544, 18, 134, 30), "Saved (0/3)", BTN_NEUTRAL, BTN_NEUTRAL_HOVER, radius=8)

        # Configuration bar controls
        self.size_buttons = []
        for count in range(1, max_computers + 1):
            btn = ActionButton(
                (148 + (count - 1) * 92, 98, 84, 34),
                f"{count + 1}P ({count} AI)",
                BTN_NEUTRAL,
                BTN_NEUTRAL_HOVER,
                radius=8,
            )
            self.size_buttons.append((count, btn))

        self.chip_buttons = []
        for idx, amount in enumerate(self.CHIP_OPTIONS):
            btn = ActionButton(
                (670 + idx * 72, 98, 66, 34),
                f"${amount}",
                BTN_NEUTRAL,
                BTN_NEUTRAL_HOVER,
                radius=8,
            )
            self.chip_buttons.append((amount, btn))

        self.blind_buttons = []
        for idx, (sb, bb) in enumerate(self.BLIND_OPTIONS):
            btn = ActionButton(
                (944 + idx * 70, 98, 64, 34),
                f"{sb}/{bb}",
                BTN_NEUTRAL,
                BTN_NEUTRAL_HOVER,
                radius=8,
            )
            self.blind_buttons.append(((sb, bb), btn))

        # 4x3 Roster card rects
        self.card_rects = []
        for idx in range(len(AI_ROSTER)):
            col = idx % 4
            row = idx // 4
            x = 42 + col * 284
            y = 172 + row * 150
            self.card_rects.append(pygame.Rect(x, y, 264, 134))

        # Bottom action buttons
        self.btn_back = ActionButton((42, 672, 128, 46), "Back", BTN_NEUTRAL, BTN_NEUTRAL_HOVER, radius=10)
        self.btn_random = ActionButton((764, 672, 160, 46), "Random Pick", BTN_NEUTRAL, BTN_NEUTRAL_HOVER, radius=10)
        self.btn_deal = ActionButton((942, 672, 216, 46), "Deal Cards!", BTN_CALL, BTN_CALL_HOVER, shortcut="Enter", radius=10)

    def sync_from_session(self, session, can_resume=False, active_cfg=None):
        self.can_resume = bool(can_resume)
        self.active_cfg = dict(active_cfg) if active_cfg else None
        self.active_hand_number = int(session.hand_number) if session else 0
        self.num_computers = session.num_computers
        self.starting_chips = session.starting_chips
        self.blinds = (session.small_blind, session.big_blind)

        roster_names = {entry["name"] for entry in AI_ROSTER}
        if session.opponents:
            names = [p["name"] for p in session.opponents if p.get("name") in roster_names]
        else:
            names = [p.name for p in session.game.players[1:] if p.name in roster_names]

        if len(names) == self.num_computers:
            self.selected_names = names
        else:
            self.selected_names = names[: self.num_computers]
            while len(self.selected_names) < self.num_computers:
                for entry in AI_ROSTER:
                    if entry["name"] not in self.selected_names:
                        self.selected_names.append(entry["name"])
                        break

    def is_unchanged_from_active(self):
        if not self.can_resume or not self.active_cfg:
            return False
        active_names = self.active_cfg.get("selected_names", [])
        return (
            self.num_computers == self.active_cfg.get("num_computers")
            and self.starting_chips == self.active_cfg.get("starting_chips")
            and self.blinds == (self.active_cfg.get("small_blind"), self.active_cfg.get("big_blind"))
            and len(self.selected_names) == len(active_names)
            and set(self.selected_names) == set(active_names)
        )

    def _sync_dynamic_buttons(self, saves_count=0):
        if self.can_resume:
            self.btn_back.rect = pygame.Rect(42, 672, 168, 46)
            self.btn_back.label = "Back to Table"
        else:
            self.btn_back.rect = pygame.Rect(42, 672, 128, 46)
            self.btn_back.label = "Back"

        self.btn_saves.label = f"Saved ({saves_count}/3)"
        if saves_count > 0:
            self.btn_saves.bg_color = BTN_RAISE
            self.btn_saves.hover_color = BTN_RAISE_HOVER
        else:
            self.btn_saves.bg_color = BTN_NEUTRAL
            self.btn_saves.hover_color = BTN_NEUTRAL_HOVER

        chosen_count = len(self.selected_names)
        ready = chosen_count == self.num_computers
        self.btn_deal.enabled = ready
        if not ready:
            self.btn_deal.label = f"Pick {self.num_computers - chosen_count} More"
            self.btn_deal.bg_color = BTN_CALL
            self.btn_deal.hover_color = BTN_CALL_HOVER
        elif self.is_unchanged_from_active():
            self.btn_deal.label = "Resume Match"
            self.btn_deal.bg_color = BTN_CALL
            self.btn_deal.hover_color = BTN_CALL_HOVER
        elif self.can_resume:
            self.btn_deal.label = "Start New Match"
            self.btn_deal.bg_color = BTN_RAISE
            self.btn_deal.hover_color = BTN_RAISE_HOVER
        else:
            self.btn_deal.label = "Deal Cards!"
            self.btn_deal.bg_color = BTN_CALL
            self.btn_deal.hover_color = BTN_CALL_HOVER

    def _toggle_ai(self, name):
        if name in self.selected_names:
            self.selected_names.remove(name)
        else:
            if len(self.selected_names) >= self.num_computers:
                self.selected_names.pop(0)
            self.selected_names.append(name)

    def _random_pick(self):
        chosen = random.sample(AI_ROSTER, self.num_computers)
        self.selected_names = [item["name"] for item in chosen]

    def _build_payload(self):
        by_name = {entry["name"]: entry for entry in AI_ROSTER}
        opponents = [dict(by_name[name]) for name in self.selected_names if name in by_name]
        return {
            "opponents": opponents,
            "num_computers": len(opponents),
            "starting_chips": self.starting_chips,
            "small_blind": self.blinds[0],
            "big_blind": self.blinds[1],
        }

    def handle_event(self, event, saves_count=0):
        """Return ('back', None), ('resume', None), ('saves', None), ('start', payload), or (None, None)."""
        self._sync_dynamic_buttons(saves_count)
        if event.type == pygame.MOUSEMOTION:
            self.hovered_card_idx = -1
            for idx, rect in enumerate(self.card_rects):
                if rect.collidepoint(event.pos):
                    self.hovered_card_idx = idx
                    break

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return ("resume", None) if self.can_resume else ("back", None)
            if event.key in (pygame.K_RETURN, pygame.K_SPACE) and len(self.selected_names) == self.num_computers:
                if self.is_unchanged_from_active():
                    return ("resume", None)
                return ("start", self._build_payload())

        if self.btn_saves.handle_event(event):
            return ("saves", None)

        for count, btn in self.size_buttons:
            if btn.handle_event(event):
                self.num_computers = count
                if len(self.selected_names) > count:
                    self.selected_names = self.selected_names[:count]
                return (None, None)

        for amount, btn in self.chip_buttons:
            if btn.handle_event(event):
                self.starting_chips = amount
                return (None, None)

        for blinds, btn in self.blind_buttons:
            if btn.handle_event(event):
                self.blinds = blinds
                return (None, None)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for idx, rect in enumerate(self.card_rects):
                if rect.collidepoint(event.pos):
                    self._toggle_ai(AI_ROSTER[idx]["name"])
                    return (None, None)

        if self.btn_back.handle_event(event):
            return ("resume", None) if self.can_resume else ("back", None)
        if self.btn_random.handle_event(event):
            self._random_pick()
            return (None, None)

        ready = len(self.selected_names) == self.num_computers
        self.btn_deal.enabled = ready
        if self.btn_deal.handle_event(event) and ready:
            if self.is_unchanged_from_active():
                return ("resume", None)
            return ("start", self._build_payload())

        return (None, None)

    @staticmethod
    def _initials(name):
        if len(name) <= 3:
            return name.upper()
        return name[:2].upper()

    def draw(self, surface, fonts, saves_count=0):
        self._sync_dynamic_buttons(saves_count)
        surface.fill(BG_OUTER)

        # Header
        draw_text(
            surface,
            fonts.get(26, bold=True),
            "Choose Your Opponents",
            GOLD_BRIGHT,
            (42, 22),
        )
        draw_text(
            surface,
            fonts.get(13, bold=False),
            "Pick table size and select matching AI rivals — each tier has distinct strength & playstyle",
            TEXT_SECONDARY,
            (42, 54),
        )

        self.btn_saves.draw(surface, fonts)

        # Strength tier legend top-right
        lx = 694
        for tier in self.TIER_ORDER:
            tc = TIER_COLORS[tier]
            pill = pygame.Rect(lx, 26, 86, 26)
            pygame.draw.rect(surface, tc["bg"], pill, border_radius=8)
            pygame.draw.rect(surface, tc["border"], pill, width=1, border_radius=8)
            draw_text(surface, fonts.get(11, bold=True), tier.upper(), tc["text"], pill.center, anchor="center")
            lx += 94

        # Settings bar
        cfg_bar = pygame.Rect(42, 84, WINDOW_WIDTH - 84, 62)
        pygame.draw.rect(surface, PANEL_BG, cfg_bar, border_radius=12)
        pygame.draw.rect(surface, PANEL_BORDER, cfg_bar, width=1, border_radius=12)

        draw_text(surface, fonts.get(13, bold=True), "Table Size", TEXT_SECONDARY, (60, 115), anchor="midleft")
        for count, btn in self.size_buttons:
            is_sel = count == self.num_computers
            btn.bg_color = BTN_RAISE if is_sel else BTN_NEUTRAL
            btn.hover_color = BTN_RAISE_HOVER if is_sel else BTN_NEUTRAL_HOVER
            btn.draw(surface, fonts)

        draw_text(surface, fonts.get(13, bold=True), "Chips", TEXT_SECONDARY, (622, 115), anchor="midleft")
        for amount, btn in self.chip_buttons:
            is_sel = amount == self.starting_chips
            btn.bg_color = BTN_RAISE if is_sel else BTN_NEUTRAL
            btn.hover_color = BTN_RAISE_HOVER if is_sel else BTN_NEUTRAL_HOVER
            btn.draw(surface, fonts)

        draw_text(surface, fonts.get(13, bold=True), "Blinds", TEXT_SECONDARY, (894, 115), anchor="midleft")
        for blinds, btn in self.blind_buttons:
            is_sel = blinds == self.blinds
            btn.bg_color = BTN_RAISE if is_sel else BTN_NEUTRAL
            btn.hover_color = BTN_RAISE_HOVER if is_sel else BTN_NEUTRAL_HOVER
            btn.draw(surface, fonts)

        # 12 AI Cards (4x3 grid)
        for idx, profile in enumerate(AI_ROSTER):
            rect = self.card_rects[idx]
            name = profile["name"]
            tier = profile["tier"]
            style = profile["style"]
            tc = TIER_COLORS[tier]
            stars = AI_TIER_SETTINGS[tier]["stars"]
            selected = name in self.selected_names
            hovered = idx == self.hovered_card_idx

            if selected:
                pygame.draw.rect(surface, tc["border"], rect.inflate(6, 6), width=2, border_radius=15)
                bg = tc["card_bg"]
                border_col = tc["border"]
                border_w = 2
            else:
                bg = PANEL_BG_ALT if hovered else PANEL_BG
                border_col = tc["accent"] if hovered else PANEL_BORDER
                border_w = 1

            pygame.draw.rect(surface, bg, rect, border_radius=12)
            pygame.draw.rect(surface, border_col, rect, width=border_w, border_radius=12)

            # Left tier color stripe
            stripe = pygame.Rect(rect.left + 2, rect.top + 12, 5, rect.height - 24)
            pygame.draw.rect(surface, tc["accent"], stripe, border_radius=3)

            # Avatar circle
            av_center = (rect.left + 44, rect.top + 46)
            pygame.draw.circle(surface, tc["bg"], av_center, 22)
            pygame.draw.circle(surface, tc["border"], av_center, 22, width=2)
            draw_text(
                surface,
                fonts.get(14, bold=True),
                self._initials(name),
                tc["text"],
                av_center,
                anchor="center",
            )

            # Name, style subtitle, and organization/team tag pill
            draw_text(surface, fonts.get(18, bold=True), name, TEXT_PRIMARY, (rect.left + 78, rect.top + 14))
            draw_text(surface, fonts.get(11, bold=False), style, TEXT_SECONDARY, (rect.left + 78, rect.top + 38))

            tag_text = profile.get("tag", "")
            if tag_text:
                tag_font = fonts.get(10, bold=True)
                tw = tag_font.size(tag_text)[0]
                tag_pill = pygame.Rect(rect.left + 78, rect.top + 57, tw + 22, 20)
                is_rw = tag_text == "Rollingwood"
                tag_bg = (36, 48, 34) if is_rw else (24, 34, 50)
                tag_border = (118, 186, 108) if is_rw else PANEL_BORDER
                tag_fg = (188, 238, 174) if is_rw else (186, 204, 228)
                pygame.draw.rect(surface, tag_bg, tag_pill, border_radius=6)
                pygame.draw.rect(surface, tag_border, tag_pill, width=1, border_radius=6)
                pygame.draw.circle(surface, tag_border, (tag_pill.left + 7, tag_pill.centery), 2)
                draw_text(surface, tag_font, tag_text, tag_fg, (tag_pill.left + 13, tag_pill.centery), anchor="midleft")

            # Seat number pill if selected
            if selected:
                seat_num = self.selected_names.index(name) + 1
                sel_pill = pygame.Rect(rect.right - 66, rect.top + 12, 54, 24)
                pygame.draw.rect(surface, tc["bg"], sel_pill, border_radius=7)
                pygame.draw.rect(surface, tc["border"], sel_pill, width=1, border_radius=7)
                draw_text(surface, fonts.get(11, bold=True), f"AI #{seat_num}", tc["text"], sel_pill.center, anchor="center")

            # Tier badge + 5-bar strength meter at bottom of card
            tier_pill = pygame.Rect(rect.left + 20, rect.bottom - 40, 82, 24)
            pygame.draw.rect(surface, tc["bg"], tier_pill, border_radius=7)
            pygame.draw.rect(surface, tc["border"], tier_pill, width=1, border_radius=7)
            draw_text(surface, fonts.get(11, bold=True), tier.upper(), tc["text"], tier_pill.center, anchor="center")

            # 5 strength segments
            bar_x = rect.left + 114
            bar_y = rect.bottom - 33
            for seg in range(5):
                seg_rect = pygame.Rect(bar_x + seg * 26, bar_y, 20, 10)
                filled = seg < stars
                pygame.draw.rect(
                    surface,
                    tc["border"] if filled else (34, 42, 56),
                    seg_rect,
                    border_radius=3,
                )

        # Bottom action bar
        dock = pygame.Rect(0, 648, WINDOW_WIDTH, WINDOW_HEIGHT - 648)
        pygame.draw.rect(surface, PANEL_BG, dock)
        pygame.draw.line(surface, PANEL_BORDER, (0, 648), (WINDOW_WIDTH, 648), 1)

        chosen_count = len(self.selected_names)
        ready = chosen_count == self.num_computers
        if ready:
            if self.is_unchanged_from_active():
                status_text = f"Unchanged lineup — Resume Match (Hand #{self.active_hand_number})"
                status_col = (72, 206, 146)
            elif self.can_resume:
                status_text = "Lineup changed — Start New Match (current match auto-saved)"
                status_col = GOLD_BRIGHT
            else:
                names_preview = ", ".join(self.selected_names)
                status_text = f"Selected {chosen_count}/{self.num_computers} AI: {names_preview}"
                status_col = (72, 206, 146)
        else:
            needed = self.num_computers - chosen_count
            status_text = f"Selected {chosen_count}/{self.num_computers} AI  —  Pick {needed} more"
            status_col = GOLD_BRIGHT

        status_x = self.btn_back.rect.right + 18
        draw_text(surface, fonts.get(13, bold=True), status_text, status_col, (status_x, 695), anchor="midleft")

        self.btn_back.draw(surface, fonts)
        self.btn_random.draw(surface, fonts)
        self.btn_deal.draw(surface, fonts)
