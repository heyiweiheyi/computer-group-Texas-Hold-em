"""Interactive Pygame widgets: action buttons, raise slider, and hand-ranking modal."""

import pygame

from ui_theme import (
    BTN_CALL,
    BTN_CALL_HOVER,
    BTN_DISABLED,
    BTN_FOLD,
    BTN_FOLD_HOVER,
    BTN_NEUTRAL,
    BTN_NEUTRAL_HOVER,
    BTN_RAISE,
    BTN_RAISE_HOVER,
    GOLD_BRIGHT,
    GOLD_MID,
    PANEL_BG,
    PANEL_BG_ALT,
    PANEL_BORDER,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    draw_text,
)


class ActionButton:
    """Rounded interactive button with hover highlight, press feedback, and shortcut hint."""

    def __init__(
        self,
        rect,
        label,
        bg_color,
        hover_color,
        text_color=TEXT_PRIMARY,
        shortcut="",
        radius=10,
    ):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.shortcut = shortcut
        self.radius = radius
        self.enabled = True
        self.hovered = False
        self.pressed = False

    def handle_event(self, event):
        if not self.enabled:
            self.hovered = False
            self.pressed = False
            return False

        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed = self.pressed
            self.pressed = False
            if was_pressed and self.rect.collidepoint(event.pos):
                return True
        return False

    def draw(self, surface, fonts):
        draw_rect = self.rect.move(0, 1) if (self.pressed and self.enabled) else self.rect

        if not self.enabled:
            bg = BTN_DISABLED
            border = (42, 52, 68)
            fg = TEXT_MUTED
        else:
            bg = self.hover_color if self.hovered else self.bg_color
            border = tuple(min(255, c + 36) for c in bg)
            fg = self.text_color

        # Drop shadow
        if self.enabled and not self.pressed:
            pygame.draw.rect(
                surface,
                (5, 8, 13),
                draw_rect.move(0, 3),
                border_radius=self.radius,
            )

        pygame.draw.rect(surface, bg, draw_rect, border_radius=self.radius)
        pygame.draw.rect(surface, border, draw_rect, width=1, border_radius=self.radius)

        font = fonts.get(16, bold=True)
        if self.shortcut:
            draw_text(
                surface,
                font,
                self.label,
                fg,
                (draw_rect.centerx, draw_rect.centery - 7),
                anchor="center",
            )
            sub_font = fonts.get(11, bold=False)
            sub_color = TEXT_SECONDARY if self.enabled else TEXT_MUTED
            draw_text(
                surface,
                sub_font,
                f"[{self.shortcut}]",
                sub_color,
                (draw_rect.centerx, draw_rect.centery + 11),
                anchor="center",
            )
        else:
            draw_text(surface, font, self.label, fg, draw_rect.center, anchor="center")


class RaiseControl:
    """Draggable raise slider paired with quick-bet preset pills."""

    def __init__(self, track_rect, presets_y):
        self.track_rect = pygame.Rect(track_rect)
        self.min_amount = 10
        self.max_amount = 100
        self.value = 10
        self.pot = 0
        self.current_bet = 0
        self.to_call = 0
        self.is_bet = True
        self.enabled = False
        self.dragging = False

        pill_w = 58
        pill_h = 26
        gap = 8
        start_x = self.track_rect.x
        self.preset_buttons = [
            ("Min", ActionButton((start_x + 0 * (pill_w + gap), presets_y, pill_w, pill_h), "Min", BTN_NEUTRAL, BTN_NEUTRAL_HOVER, radius=7)),
            ("1/2", ActionButton((start_x + 1 * (pill_w + gap), presets_y, pill_w, pill_h), "1/2 Pot", BTN_NEUTRAL, BTN_NEUTRAL_HOVER, radius=7)),
            ("Pot", ActionButton((start_x + 2 * (pill_w + gap), presets_y, pill_w, pill_h), "Pot", BTN_NEUTRAL, BTN_NEUTRAL_HOVER, radius=7)),
            ("Max", ActionButton((start_x + 3 * (pill_w + gap), presets_y, pill_w, pill_h), "Max", BTN_NEUTRAL, BTN_NEUTRAL_HOVER, radius=7)),
        ]

    def set_bounds(self, min_amount, max_amount, pot, current_bet=0, to_call=0, is_bet=False, reset_to_min=False):
        self.min_amount = min_amount
        self.max_amount = max(min_amount, max_amount)
        self.pot = pot
        self.current_bet = current_bet
        self.to_call = to_call
        self.is_bet = is_bet
        if reset_to_min:
            self.value = self.min_amount
        else:
            self.value = max(self.min_amount, min(self.max_amount, self.value))

    def set_enabled(self, enabled):
        self.enabled = enabled
        if not enabled:
            self.dragging = False
        for _, btn in self.preset_buttons:
            btn.enabled = enabled

    def _set_from_mouse_x(self, mx):
        ratio = (mx - self.track_rect.left) / max(1, self.track_rect.width)
        ratio = max(0.0, min(1.0, ratio))
        raw = self.min_amount + ratio * (self.max_amount - self.min_amount)
        # Snap to increments of 5 unless near min/max
        if self.max_amount - self.min_amount >= 15:
            snapped = round(raw / 5) * 5
            if abs(raw - self.min_amount) < 3:
                snapped = self.min_amount
            elif abs(self.max_amount - raw) < 3:
                snapped = self.max_amount
            self.value = int(max(self.min_amount, min(self.max_amount, snapped)))
        else:
            self.value = int(round(raw))

    def handle_event(self, event, pot):
        if not self.enabled:
            return

        for key, btn in self.preset_buttons:
            if btn.handle_event(event):
                pot_after_call = pot + self.to_call
                if key == "Min":
                    self.value = self.min_amount
                elif key == "1/2":
                    target = self.current_bet + pot_after_call // 2
                    self.value = max(self.min_amount, min(self.max_amount, target))
                elif key == "Pot":
                    target = self.current_bet + pot_after_call
                    self.value = max(self.min_amount, min(self.max_amount, target))
                elif key == "Max":
                    self.value = self.max_amount
                return

        hit_rect = self.track_rect.inflate(14, 22)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if hit_rect.collidepoint(event.pos):
                self.dragging = True
                self._set_from_mouse_x(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_mouse_x(event.pos[0])

    def draw(self, surface, fonts):
        for _, btn in self.preset_buttons:
            btn.draw(surface, fonts)

        # Slider track
        track_bg = (34, 44, 60) if self.enabled else (26, 32, 42)
        pygame.draw.rect(surface, track_bg, self.track_rect, border_radius=4)

        span = max(1, self.max_amount - self.min_amount)
        ratio = 0.0 if self.max_amount <= self.min_amount else (self.value - self.min_amount) / span
        ratio = max(0.0, min(1.0, ratio))
        fill_w = int(self.track_rect.width * ratio)

        if self.enabled and fill_w > 0:
            fill_rect = pygame.Rect(
                self.track_rect.left,
                self.track_rect.top,
                fill_w,
                self.track_rect.height,
            )
            pygame.draw.rect(surface, GOLD_MID, fill_rect, border_radius=4)

        # Knob
        knob_x = self.track_rect.left + fill_w
        knob_y = self.track_rect.centery
        knob_col = GOLD_BRIGHT if self.enabled else TEXT_MUTED
        pygame.draw.circle(surface, (10, 14, 20), (knob_x, knob_y + 1), 10)
        pygame.draw.circle(surface, knob_col, (knob_x, knob_y), 9)
        pygame.draw.circle(surface, TEXT_PRIMARY if self.enabled else PANEL_BORDER, (knob_x, knob_y), 4)

        # Value label right of slider
        lbl_font = fonts.get(13, bold=True)
        if not self.enabled:
            lbl_text = "Raise N/A"
        elif self.is_bet:
            lbl_text = f"Bet ${self.value}"
        else:
            lbl_text = f"To ${self.value}"
        lbl_col = GOLD_BRIGHT if self.enabled else TEXT_MUTED
        draw_text(
            surface,
            lbl_font,
            lbl_text,
            lbl_col,
            (self.track_rect.right + 12, self.track_rect.centery),
            anchor="midleft",
        )


class RulesModal:
    """Overlay displaying the 9 standard Texas Hold'em hand rankings and shortcuts."""

    HAND_RANKINGS = [
        ("1. Straight Flush", "Five consecutive cards of the same suit", "9♠ 8♠ 7♠ 6♠ 5♠"),
        ("2. Four of a Kind", "Four cards of the same rank", "A♠ A♥ A♦ A♣ K♠"),
        ("3. Full House", "Three of a kind plus a pair", "A♠ A♥ A♦ K♣ K♦"),
        ("4. Flush", "Any five cards of the same suit", "A♠ J♠ 8♠ 5♠ 2♠"),
        ("5. Straight", "Five consecutive ranks (A-2-3-4-5 allowed)", "9♠ 8♥ 7♦ 6♣ 5♠"),
        ("6. Three of a Kind", "Three cards of the same rank", "K♠ K♥ K♦ 9♣ 4♠"),
        ("7. Two Pair", "Two different pairs plus one kicker", "A♠ A♥ K♦ K♣ Q♦"),
        ("8. One Pair", "Two cards of the same rank", "J♠ J♥ A♦ 8♣ 3♠"),
        ("9. High Card", "Highest card plays when no hand is made", "A♠ K♥ Q♦ 9♣ 3♠"),
    ]

    def __init__(self, window_w, window_h):
        self.visible = False
        self.modal_rect = pygame.Rect((window_w - 640) // 2, (window_h - 520) // 2, 640, 520)
        self.close_btn = ActionButton(
            (self.modal_rect.right - 98, self.modal_rect.top + 18, 78, 32),
            "Close",
            BTN_NEUTRAL,
            BTN_NEUTRAL_HOVER,
            radius=8,
        )

    def handle_event(self, event):
        if not self.visible:
            return False

        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_h):
            self.visible = False
            return True

        if self.close_btn.handle_event(event):
            self.visible = False
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.modal_rect.collidepoint(event.pos):
                self.visible = False
                return True
        return True

    def draw(self, surface, fonts):
        if not self.visible:
            return

        dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim.fill((6, 10, 16, 185))
        surface.blit(dim, (0, 0))

        pygame.draw.rect(surface, PANEL_BG, self.modal_rect, border_radius=16)
        pygame.draw.rect(surface, GOLD_MID, self.modal_rect, width=1, border_radius=16)

        title_font = fonts.get(20, bold=True)
        draw_text(
            surface,
            title_font,
            "Texas Hold'em Hand Rankings & Controls",
            GOLD_BRIGHT,
            (self.modal_rect.left + 24, self.modal_rect.top + 22),
        )
        self.close_btn.draw(surface, fonts)

        row_y = self.modal_rect.top + 70
        row_h = 39
        name_font = fonts.get(14, bold=True)
        desc_font = fonts.get(12, bold=False)
        ex_font = fonts.get(13, bold=True)

        for idx, (name, desc, example) in enumerate(self.HAND_RANKINGS):
            row_rect = pygame.Rect(self.modal_rect.left + 22, row_y + idx * row_h, self.modal_rect.width - 44, row_h - 5)
            bg = PANEL_BG_ALT if idx % 2 == 0 else (21, 29, 42)
            pygame.draw.rect(surface, bg, row_rect, border_radius=8)
            pygame.draw.rect(surface, PANEL_BORDER, row_rect, width=1, border_radius=8)

            draw_text(surface, name_font, name, TEXT_PRIMARY, (row_rect.left + 12, row_rect.centery - 7), anchor="midleft")
            draw_text(surface, desc_font, desc, TEXT_SECONDARY, (row_rect.left + 12, row_rect.centery + 9), anchor="midleft")
            draw_text(surface, ex_font, example, GOLD_BRIGHT, (row_rect.right - 12, row_rect.centery), anchor="midright")

        footer_font = fonts.get(12, bold=False)
        draw_text(
            surface,
            footer_font,
            "Shortcuts: [F] Fold  [C] Check/Call  [R] Raise  [A] All-In  [1]/[2] Runout  [Space] Next",
            TEXT_SECONDARY,
            (self.modal_rect.centerx, self.modal_rect.bottom - 22),
            anchor="center",
        )


class SetupModal:
    """Modal dialog for choosing number of computer opponents (up to max_computers) and stakes."""

    CHIP_OPTIONS = [300, 500, 1000]
    BLIND_OPTIONS = [(5, 10), (10, 20), (25, 50)]

    def __init__(self, window_w, window_h, max_computers=5):
        self.visible = False
        self.max_computers = max_computers
        self.selected_computers = 1
        self.selected_chips = 500
        self.selected_blinds = (5, 10)

        self.modal_rect = pygame.Rect((window_w - 560) // 2, (window_h - 400) // 2, 560, 400)
        left = self.modal_rect.left + 28
        self.comp_buttons = []
        for count in range(1, max_computers + 1):
            btn = ActionButton(
                (left + (count - 1) * 102, self.modal_rect.top + 108, 92, 42),
                f"{count} AI" if count > 1 else "1 AI",
                BTN_NEUTRAL,
                BTN_NEUTRAL_HOVER,
                radius=8,
            )
            self.comp_buttons.append((count, btn))

        self.chip_buttons = []
        for idx, amount in enumerate(self.CHIP_OPTIONS):
            btn = ActionButton(
                (left + idx * 124, self.modal_rect.top + 198, 112, 40),
                f"${amount}",
                BTN_NEUTRAL,
                BTN_NEUTRAL_HOVER,
                radius=8,
            )
            self.chip_buttons.append((amount, btn))

        self.blind_buttons = []
        for idx, (sb, bb) in enumerate(self.BLIND_OPTIONS):
            btn = ActionButton(
                (left + idx * 124, self.modal_rect.top + 284, 112, 40),
                f"${sb} / ${bb}",
                BTN_NEUTRAL,
                BTN_NEUTRAL_HOVER,
                radius=8,
            )
            self.blind_buttons.append(((sb, bb), btn))

        self.cancel_btn = ActionButton(
            (self.modal_rect.right - 256, self.modal_rect.bottom - 56, 104, 38),
            "Cancel",
            BTN_NEUTRAL,
            BTN_NEUTRAL_HOVER,
            radius=8,
        )
        self.start_btn = ActionButton(
            (self.modal_rect.right - 140, self.modal_rect.bottom - 56, 114, 38),
            "Start Match",
            BTN_CALL,
            BTN_CALL_HOVER,
            radius=8,
        )

    def open_with(self, num_computers, starting_chips, small_blind, big_blind):
        self.selected_computers = max(1, min(self.max_computers, num_computers))
        self.selected_chips = starting_chips
        self.selected_blinds = (small_blind, big_blind)
        self.visible = True

    def handle_event(self, event):
        """Return settings dict when user clicks Start Match, else None."""
        if not self.visible:
            return None

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.visible = False
            return None

        for count, btn in self.comp_buttons:
            if btn.handle_event(event):
                self.selected_computers = count

        for amount, btn in self.chip_buttons:
            if btn.handle_event(event):
                self.selected_chips = amount

        for blinds, btn in self.blind_buttons:
            if btn.handle_event(event):
                self.selected_blinds = blinds

        if self.cancel_btn.handle_event(event):
            self.visible = False
            return None

        if self.start_btn.handle_event(event):
            self.visible = False
            return {
                "num_computers": self.selected_computers,
                "starting_chips": self.selected_chips,
                "small_blind": self.selected_blinds[0],
                "big_blind": self.selected_blinds[1],
            }

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.modal_rect.collidepoint(event.pos):
                self.visible = False
        return None

    def draw(self, surface, fonts):
        if not self.visible:
            return

        dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim.fill((6, 10, 16, 185))
        surface.blit(dim, (0, 0))

        pygame.draw.rect(surface, PANEL_BG, self.modal_rect, border_radius=16)
        pygame.draw.rect(surface, GOLD_MID, self.modal_rect, width=1, border_radius=16)

        left = self.modal_rect.left + 28
        draw_text(
            surface,
            fonts.get(20, bold=True),
            "Table Setup",
            GOLD_BRIGHT,
            (left, self.modal_rect.top + 22),
        )
        draw_text(
            surface,
            fonts.get(12, bold=False),
            f"Configure AI opponents (max {self.max_computers} AI = {self.max_computers + 1}-player table) and stakes",
            TEXT_SECONDARY,
            (left, self.modal_rect.top + 49),
        )

        draw_text(
            surface,
            fonts.get(14, bold=True),
            f"Computer Opponents (1 ~ {self.max_computers})  —  {self.selected_computers + 1} Players Total",
            TEXT_PRIMARY,
            (left, self.modal_rect.top + 82),
        )
        for count, btn in self.comp_buttons:
            is_sel = count == self.selected_computers
            btn.bg_color = BTN_RAISE if is_sel else BTN_NEUTRAL
            btn.hover_color = BTN_RAISE_HOVER if is_sel else BTN_NEUTRAL_HOVER
            btn.draw(surface, fonts)

        draw_text(
            surface,
            fonts.get(14, bold=True),
            "Starting Chips",
            TEXT_PRIMARY,
            (left, self.modal_rect.top + 172),
        )
        for amount, btn in self.chip_buttons:
            is_sel = amount == self.selected_chips
            btn.bg_color = BTN_RAISE if is_sel else BTN_NEUTRAL
            btn.hover_color = BTN_RAISE_HOVER if is_sel else BTN_NEUTRAL_HOVER
            btn.draw(surface, fonts)

        draw_text(
            surface,
            fonts.get(14, bold=True),
            "Blinds",
            TEXT_PRIMARY,
            (left, self.modal_rect.top + 258),
        )
        for blinds, btn in self.blind_buttons:
            is_sel = blinds == self.selected_blinds
            btn.bg_color = BTN_RAISE if is_sel else BTN_NEUTRAL
            btn.hover_color = BTN_RAISE_HOVER if is_sel else BTN_NEUTRAL_HOVER
            btn.draw(surface, fonts)

        self.cancel_btn.draw(surface, fonts)
        self.start_btn.draw(surface, fonts)


class UpdateModal:
    """Modal dialog showing GitHub update status with one-click Pull/Download & Restart."""

    def __init__(self, window_w, window_h):
        self.visible = False
        self.modal_rect = pygame.Rect((window_w - 540) // 2, (window_h - 300) // 2, 540, 300)
        self.check_btn = ActionButton(
            (self.modal_rect.left + 26, self.modal_rect.bottom - 56, 134, 38),
            "Check Again",
            BTN_NEUTRAL,
            BTN_NEUTRAL_HOVER,
            radius=8,
        )
        self.action_btn = ActionButton(
            (self.modal_rect.left + 174, self.modal_rect.bottom - 56, 198, 38),
            "Update Now",
            BTN_CALL,
            BTN_CALL_HOVER,
            radius=8,
        )
        self.close_btn = ActionButton(
            (self.modal_rect.right - 126, self.modal_rect.bottom - 56, 100, 38),
            "Close",
            BTN_NEUTRAL,
            BTN_NEUTRAL_HOVER,
            radius=8,
        )

    def handle_event(self, event, state):
        """Return 'check', 'update', 'restart', or None."""
        if not self.visible:
            return None

        busy = state["status"] in ("checking", "updating")
        self.check_btn.enabled = not busy
        if state["restart_required"]:
            self.action_btn.label = "Restart Now"
            self.action_btn.enabled = True
        else:
            self.action_btn.label = "Updating..." if state["status"] == "updating" else "Update Now"
            self.action_btn.enabled = not busy

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.visible = False
            return None

        if self.check_btn.handle_event(event):
            return "check"
        if self.action_btn.handle_event(event):
            return "restart" if state["restart_required"] else "update"
        if self.close_btn.handle_event(event):
            self.visible = False
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.modal_rect.collidepoint(event.pos):
                self.visible = False
        return None

    def draw(self, surface, fonts, state):
        if not self.visible:
            return

        dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim.fill((6, 10, 16, 185))
        surface.blit(dim, (0, 0))

        pygame.draw.rect(surface, PANEL_BG, self.modal_rect, border_radius=16)
        border_col = GOLD_BRIGHT if state["has_update"] else GOLD_MID
        pygame.draw.rect(surface, border_col, self.modal_rect, width=1, border_radius=16)

        left = self.modal_rect.left + 26
        draw_text(
            surface,
            fonts.get(20, bold=True),
            "Repository Update",
            GOLD_BRIGHT,
            (left, self.modal_rect.top + 22),
        )
        draw_text(
            surface,
            fonts.get(12, bold=False),
            "GitHub: heyiweiheyi/computer-group-Texas-Hold-em (main)",
            TEXT_SECONDARY,
            (left, self.modal_rect.top + 50),
        )

        # Info box
        info_rect = pygame.Rect(left, self.modal_rect.top + 82, self.modal_rect.width - 52, 136)
        pygame.draw.rect(surface, PANEL_BG_ALT, info_rect, border_radius=10)
        pygame.draw.rect(surface, PANEL_BORDER, info_rect, width=1, border_radius=10)

        status = state["status"]
        status_map = {
            "idle": ("IDLE", TEXT_SECONDARY),
            "checking": ("CHECKING...", GOLD_BRIGHT),
            "up_to_date": ("UP TO DATE", (72, 206, 146)),
            "update_available": ("NEW UPDATE AVAILABLE!", GOLD_BRIGHT),
            "updating": ("DOWNLOADING UPDATE...", GOLD_BRIGHT),
            "updated": ("UPDATE INSTALLED!", (72, 206, 146)),
            "error": ("UPDATE CHECK / PULL ISSUE", (242, 126, 126)),
        }
        badge_text, badge_col = status_map.get(status, (status.upper(), TEXT_PRIMARY))
        draw_text(surface, fonts.get(14, bold=True), badge_text, badge_col, (info_rect.left + 16, info_rect.top + 14))

        local_short = state["local_sha"][:7] if state["local_sha"] else "ZIP copy"
        remote_short = state["short_sha"] or "—"
        draw_text(
            surface,
            fonts.get(13, bold=False),
            f"Local version:  {local_short}       Latest on GitHub:  {remote_short}",
            TEXT_PRIMARY,
            (info_rect.left + 16, info_rect.top + 44),
        )

        detail = state["detail"] or ""
        # Wrap detail cleanly into up to 2 lines
        max_chars = 58
        line1 = detail[:max_chars]
        line2 = detail[max_chars:max_chars * 2]
        if len(detail) > max_chars * 2:
            line2 = line2[:-3] + "..."
        draw_text(surface, fonts.get(12, bold=False), line1, TEXT_SECONDARY, (info_rect.left + 16, info_rect.top + 76))
        if line2:
            draw_text(surface, fonts.get(12, bold=False), line2, TEXT_SECONDARY, (info_rect.left + 16, info_rect.top + 96))

        busy = status in ("checking", "updating")
        self.check_btn.enabled = not busy
        if state["restart_required"]:
            self.action_btn.label = "Restart Now"
            self.action_btn.bg_color = BTN_RAISE
            self.action_btn.hover_color = BTN_RAISE_HOVER
            self.action_btn.enabled = True
        else:
            self.action_btn.label = "Updating..." if status == "updating" else "Update Now"
            self.action_btn.bg_color = BTN_CALL
            self.action_btn.hover_color = BTN_CALL_HOVER
            self.action_btn.enabled = not busy

        self.check_btn.draw(surface, fonts)
        self.action_btn.draw(surface, fonts)
        self.close_btn.draw(surface, fonts)


class HandSummaryModal:
    """End-of-hand settlement popup clearly breaking down Main Pot, Side Pots, and Run It Twice."""

    def __init__(self, window_w, window_h):
        self.visible = False
        self.modal_rect = pygame.Rect((window_w - 680) // 2, (window_h - 548) // 2, 680, 548)
        self.view_btn = ActionButton(
            (self.modal_rect.left + 28, self.modal_rect.bottom - 56, 152, 38),
            "View Table",
            BTN_NEUTRAL,
            BTN_NEUTRAL_HOVER,
            radius=8,
        )
        self.next_btn = ActionButton(
            (self.modal_rect.right - 216, self.modal_rect.bottom - 56, 188, 38),
            "Next Hand",
            BTN_CALL,
            BTN_CALL_HOVER,
            shortcut="Space",
            radius=8,
        )

    def handle_event(self, event):
        """Return 'next', 'close', or None."""
        if not self.visible:
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.visible = False
                return "close"
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.visible = False
                return "next"

        if self.view_btn.handle_event(event):
            self.visible = False
            return "close"
        if self.next_btn.handle_event(event):
            self.visible = False
            return "next"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.modal_rect.collidepoint(event.pos):
                self.visible = False
                return "close"
        return None

    def _build_pot_lines(self, session):
        lines = []
        players = session.game.players
        if session.win_reason == "fold" and session.winner_index is not None:
            w_name = players[session.winner_index].name
            lines.append((f"Main Pot (${session.pot_awarded})", f"{w_name} wins (all others folded)", GOLD_BRIGHT))
        elif session.run_count == 2 and session.run_results:
            for run_idx, res in enumerate(session.run_results, start=1):
                for award in res["pot_awards"]:
                    tag = f"RUN {run_idx} • {award['pot_name']} (${award['amount']})"
                    w_names = ", ".join(players[i].name for i in award["winners"])
                    first_w = award["winners"][0]
                    hand_name = res["player_results"][first_w]["hand_name"]
                    if len(award["winners"]) == 1:
                        detail = f"{w_names} wins ${award['amount']}  ({hand_name})"
                    else:
                        detail = f"{w_names} split (${award['share']} ea • {hand_name})"
                    col = GOLD_BRIGHT if 0 in award["winners"] else TEXT_PRIMARY
                    lines.append((tag, detail, col))
        elif session.showdown_result:
            for award in session.showdown_result.get("pot_awards", []):
                tag = f"{award['pot_name']} (${award['amount']})"
                w_names = ", ".join(players[i].name for i in award["winners"])
                first_w = award["winners"][0]
                hand_name = session.showdown_result["player_results"][first_w]["hand_name"]
                if len(award["winners"]) == 1:
                    detail = f"{w_names} wins ${award['amount']}  ({hand_name})"
                else:
                    detail = f"{w_names} split (${award['share']} ea • {hand_name})"
                col = GOLD_BRIGHT if 0 in award["winners"] else TEXT_PRIMARY
                lines.append((tag, detail, col))

        for msg in session.refund_logs:
            lines.append(("Uncalled Return", msg.replace("Uncalled bet of ", ""), (132, 212, 250)))
        return lines

    def draw(self, surface, fonts, session):
        if not self.visible:
            return

        dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim.fill((6, 10, 16, 175))
        surface.blit(dim, (0, 0))

        pygame.draw.rect(surface, PANEL_BG, self.modal_rect, border_radius=16)
        pygame.draw.rect(surface, GOLD_MID, self.modal_rect, width=1, border_radius=16)

        left = self.modal_rect.left + 26
        right = self.modal_rect.right - 26

        # Header
        if session.run_count == 2 and session.win_reason == "showdown":
            sub = f"Run It Twice Settlement  •  Total Awarded: ${session.pot_awarded}"
        elif session.win_reason == "fold":
            sub = f"Won by Fold  •  Pot: ${session.pot_awarded}"
        else:
            sub = f"Showdown Settlement  •  Total Awarded: ${session.pot_awarded}"

        draw_text(
            surface,
            fonts.get(20, bold=True),
            f"Hand #{session.hand_number} Summary",
            GOLD_BRIGHT,
            (left, self.modal_rect.top + 20),
        )
        draw_text(
            surface,
            fonts.get(12, bold=False),
            sub,
            TEXT_SECONDARY,
            (left, self.modal_rect.top + 47),
        )

        # Pot breakdown section
        draw_text(
            surface,
            fonts.get(13, bold=True),
            "Pot Breakdown (Main Pot & Side Pots)",
            TEXT_PRIMARY,
            (left, self.modal_rect.top + 74),
        )
        pot_lines = self._build_pot_lines(session)[:8]
        box_h = max(62, len(pot_lines) * 22 + 14)
        pot_box = pygame.Rect(left, self.modal_rect.top + 94, right - left, box_h)
        pygame.draw.rect(surface, PANEL_BG_ALT, pot_box, border_radius=10)
        pygame.draw.rect(surface, PANEL_BORDER, pot_box, width=1, border_radius=10)

        py = pot_box.top + 8
        tag_font = fonts.get(12, bold=True)
        det_font = fonts.get(12, bold=False)
        for tag, detail, col in pot_lines:
            draw_text(surface, tag_font, tag, GOLD_BRIGHT, (pot_box.left + 12, py))
            draw_text(surface, det_font, detail, col, (pot_box.left + 224, py))
            py += 22

        # Player stack & hand table
        sec_y = pot_box.bottom + 12
        draw_text(
            surface,
            fonts.get(13, bold=True),
            "Player Results & Remaining Chips",
            TEXT_PRIMARY,
            (left, sec_y),
        )

        table_y = sec_y + 20
        row_h = 25
        players = session.game.players
        active_indices = [i for i in range(len(players)) if not session.game.eliminated[i]]
        for idx_pos, p_idx in enumerate(active_indices):
            if table_y + (idx_pos + 1) * row_h > self.modal_rect.bottom - 66:
                break
            r_rect = pygame.Rect(left, table_y + idx_pos * row_h, right - left, row_h - 3)
            bg = PANEL_BG_ALT if idx_pos % 2 == 0 else (21, 29, 42)
            pygame.draw.rect(surface, bg, r_rect, border_radius=6)

            player = players[p_idx]
            won = session.won_this_hand.get(p_idx, 0)
            if session.game.folded[p_idx]:
                hand_desc = "Folded"
            elif session.showdown_result and session.showdown_result["player_results"][p_idx]:
                if session.run_count == 2 and len(session.run_results) == 2:
                    h1 = session.run_results[0]["player_results"].get(p_idx, {}).get("hand_name", "-")
                    h2 = session.run_results[1]["player_results"].get(p_idx, {}).get("hand_name", "-")
                    hand_desc = f"R1: {h1}  /  R2: {h2}"
                else:
                    hand_desc = session.showdown_result["player_results"][p_idx]["hand_name"]
            else:
                hand_desc = "Winner" if p_idx == session.winner_index else "In hand"

            name_col = GOLD_BRIGHT if p_idx == 0 else TEXT_PRIMARY
            draw_text(surface, fonts.get(12, bold=True), player.name, name_col, (r_rect.left + 10, r_rect.centery), anchor="midleft")
            draw_text(surface, fonts.get(11, bold=False), hand_desc, TEXT_SECONDARY, (r_rect.left + 112, r_rect.centery), anchor="midleft")

            won_text = f"+${won}" if won > 0 else "—"
            won_col = (72, 206, 146) if won > 0 else TEXT_MUTED
            draw_text(surface, fonts.get(12, bold=True), won_text, won_col, (r_rect.right - 120, r_rect.centery), anchor="midright")
            draw_text(surface, fonts.get(12, bold=True), f"Stack: ${player.chips}", GOLD_BRIGHT if player.chips > 0 else TEXT_MUTED, (r_rect.right - 10, r_rect.centery), anchor="midright")

        human_alive = players[0].chips > 0
        any_ai_alive = any(p.chips > 0 for p in players[1:])
        self.next_btn.label = "Next Hand" if (human_alive and any_ai_alive) else "Finish Match"
        self.view_btn.draw(surface, fonts)
        self.next_btn.draw(surface, fonts)


class SavesModal:
    """Modal dialog displaying up to 3 saved unfinished matches with Resume / Delete controls."""

    MAX_SLOTS = 3

    def __init__(self, window_w, window_h):
        self.visible = False
        self.modal_rect = pygame.Rect((window_w - 680) // 2, (window_h - 476) // 2, 680, 476)
        self.slot_rects = []
        self.resume_btns = []
        self.delete_btns = []

        left = self.modal_rect.left + 26
        slot_w = self.modal_rect.width - 52
        for idx in range(self.MAX_SLOTS):
            slot = pygame.Rect(left, self.modal_rect.top + 82 + idx * 110, slot_w, 98)
            self.slot_rects.append(slot)
            self.resume_btns.append(
                ActionButton(
                    (slot.right - 188, slot.bottom - 44, 94, 34),
                    "Resume",
                    BTN_CALL,
                    BTN_CALL_HOVER,
                    radius=8,
                )
            )
            self.delete_btns.append(
                ActionButton(
                    (slot.right - 86, slot.bottom - 44, 72, 34),
                    "Delete",
                    BTN_FOLD,
                    BTN_FOLD_HOVER,
                    radius=8,
                )
            )

        self.close_btn = ActionButton(
            (self.modal_rect.right - 134, self.modal_rect.bottom - 54, 108, 36),
            "Close",
            BTN_NEUTRAL,
            BTN_NEUTRAL_HOVER,
            radius=8,
        )

    def handle_event(self, event, saves):
        """Return ('resume', save_id), ('delete', save_id), or (None, None)."""
        if not self.visible:
            return (None, None)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.visible = False
            return (None, None)

        if self.close_btn.handle_event(event):
            self.visible = False
            return (None, None)

        for idx in range(min(self.MAX_SLOTS, len(saves))):
            save_id = saves[idx]["id"]
            if self.resume_btns[idx].handle_event(event):
                self.visible = False
                return ("resume", save_id)
            if self.delete_btns[idx].handle_event(event):
                return ("delete", save_id)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.modal_rect.collidepoint(event.pos):
                self.visible = False
        return (None, None)

    def draw(self, surface, fonts, saves, active_save_id=None):
        if not self.visible:
            return

        dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim.fill((6, 10, 16, 185))
        surface.blit(dim, (0, 0))

        pygame.draw.rect(surface, PANEL_BG, self.modal_rect, border_radius=16)
        pygame.draw.rect(surface, GOLD_MID, self.modal_rect, width=1, border_radius=16)

        left = self.modal_rect.left + 26
        draw_text(
            surface,
            fonts.get(20, bold=True),
            "Saved Matches (Unfinished)",
            GOLD_BRIGHT,
            (left, self.modal_rect.top + 20),
        )
        draw_text(
            surface,
            fonts.get(12, bold=False),
            "Automatically keeps your 3 most recent unfinished matches — click Resume to continue",
            TEXT_SECONDARY,
            (left, self.modal_rect.top + 48),
        )

        for idx in range(self.MAX_SLOTS):
            slot = self.slot_rects[idx]
            if idx < len(saves):
                entry = saves[idx]
                is_current = active_save_id is not None and entry["id"] == active_save_id
                pygame.draw.rect(surface, PANEL_BG_ALT, slot, border_radius=10)
                border_col = (72, 206, 146) if is_current else PANEL_BORDER
                pygame.draw.rect(surface, border_col, slot, width=2 if is_current else 1, border_radius=10)

                # Slot number badge
                badge = pygame.Rect(slot.left + 12, slot.top + 12, 34, 22)
                pygame.draw.rect(surface, (28, 42, 62), badge, border_radius=6)
                pygame.draw.rect(surface, GOLD_MID, badge, width=1, border_radius=6)
                draw_text(surface, fonts.get(11, bold=True), f"#{idx + 1}", GOLD_BRIGHT, badge.center, anchor="center")

                # Header line: Hand #, table size, blinds
                title_x = badge.right + 10
                title = (
                    f"Hand #{entry['hand_number']}  •  {entry['num_players']}P Table  •  "
                    f"Blinds ${entry['small_blind']}/${entry['big_blind']}"
                )
                title_rect = draw_text(surface, fonts.get(14, bold=True), title, TEXT_PRIMARY, (title_x, slot.top + 13))

                if is_current:
                    cur_pill = pygame.Rect(title_rect.right + 10, slot.top + 13, 66, 20)
                    pygame.draw.rect(surface, (20, 74, 54), cur_pill, border_radius=6)
                    pygame.draw.rect(surface, (72, 206, 146), cur_pill, width=1, border_radius=6)
                    draw_text(surface, fonts.get(10, bold=True), "ACTIVE", (176, 248, 212), cur_pill.center, anchor="center")

                # Timestamp top-right
                draw_text(
                    surface,
                    fonts.get(11, bold=False),
                    entry.get("updated_at", ""),
                    TEXT_MUTED,
                    (slot.right - 14, slot.top + 14),
                    anchor="topright",
                )

                # Chips / Pot / Street line
                street_txt = entry.get("street", "pre_flop").replace("_", "-").upper()
                chips_txt = f"Your Chips: ${entry['human_chips']}"
                chips_rect = draw_text(surface, fonts.get(13, bold=True), chips_txt, GOLD_BRIGHT, (slot.left + 14, slot.top + 44))
                pot_txt = f"   •   Pot: ${entry.get('pot', 0)}   •   {street_txt}"
                draw_text(surface, fonts.get(12, bold=False), pot_txt, TEXT_SECONDARY, (chips_rect.right, slot.top + 45))

                # Opponents list
                opps = entry.get("opponents", [])
                opp_parts = []
                for opp in opps:
                    label = opp["name"]
                    if opp.get("eliminated"):
                        label += " (OUT)"
                    opp_parts.append(label)
                rivals_text = "Rivals: " + (", ".join(opp_parts) if opp_parts else "AI")
                if len(rivals_text) > 54:
                    rivals_text = rivals_text[:51] + "..."
                draw_text(surface, fonts.get(12, bold=False), rivals_text, TEXT_SECONDARY, (slot.left + 14, slot.top + 70))

                self.resume_btns[idx].label = "Return" if is_current else "Resume"
                self.resume_btns[idx].draw(surface, fonts)
                self.delete_btns[idx].draw(surface, fonts)
            else:
                pygame.draw.rect(surface, (15, 21, 31), slot, border_radius=10)
                pygame.draw.rect(surface, (36, 46, 62), slot, width=1, border_radius=10)
                draw_text(
                    surface,
                    fonts.get(13, bold=False),
                    f"Slot #{idx + 1}  —  Empty",
                    TEXT_MUTED,
                    slot.center,
                    anchor="center",
                )

        draw_text(
            surface,
            fonts.get(11, bold=False),
            "Completed matches are automatically cleared from save slots.",
            TEXT_MUTED,
            (left, self.modal_rect.bottom - 36),
            anchor="midleft",
        )
        self.close_btn.draw(surface, fonts)
