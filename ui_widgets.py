"""Interactive Pygame widgets: action buttons, raise slider, and hand-ranking modal."""

import pygame

from ui_theme import (
    BTN_CALL,
    BTN_CALL_HOVER,
    BTN_DISABLED,
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

    def set_bounds(self, min_amount, max_amount, pot):
        self.min_amount = min_amount
        self.max_amount = max(min_amount, max_amount)
        self.pot = pot
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
                if key == "Min":
                    self.value = self.min_amount
                elif key == "1/2":
                    self.value = max(self.min_amount, min(self.max_amount, pot // 2))
                elif key == "Pot":
                    self.value = max(self.min_amount, min(self.max_amount, pot))
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
        lbl_text = f"+${self.value}" if self.enabled else "Raise N/A"
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
