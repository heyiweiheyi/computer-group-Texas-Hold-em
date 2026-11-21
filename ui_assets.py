"""Procedural high-DPI vector cards, felt table, casino chips, and synthesized audio."""

from array import array
import math

import pygame

from texas_holdem import RANK_NAMES, SUITS
from ui_theme import (
    BG_INNER,
    BG_OUTER,
    CARD_BACK_INNER,
    CARD_BACK_NAVY,
    CARD_BORDER,
    CARD_HEIGHT,
    CARD_IVORY,
    CARD_WIDTH,
    DUAL_CARD_HEIGHT,
    DUAL_CARD_WIDTH,
    FELT_DARK,
    FELT_LIGHT,
    FELT_LINE,
    FELT_MID,
    GOLD_BRIGHT,
    GOLD_DIM,
    GOLD_MID,
    MINI_CARD_HEIGHT,
    MINI_CARD_WIDTH,
    SMALL_CARD_HEIGHT,
    SMALL_CARD_WIDTH,
    SUIT_BLACK,
    SUIT_RED,
    WOOD_DARK,
    WOOD_HIGHLIGHT,
    WOOD_MID,
    lerp,
)


# Board layout shared between table slot outlines and animated card positions
BOARD_CARD_Y = 278
BOARD_GAP = 14
BOARD_START_X = 352  # 5 cards * 88 + 4 * 14 = 496 -> centered at x=600 (352..848)


def _draw_suit_vector(surface, suit, color, box_size):
    """Draw a smooth 4x-supersampled suit icon into a square surface."""
    scale = 4
    s = box_size * scale
    hi = pygame.Surface((s, s), pygame.SRCALPHA)

    def pt(nx, ny):
        return (int(nx * s / 100), int(ny * s / 100))

    if suit == "♦":
        pygame.draw.polygon(
            hi,
            color,
            [pt(50, 8), pt(85, 50), pt(50, 92), pt(15, 50)],
        )
    elif suit == "♥":
        r = int(20.5 * s / 100)
        pygame.draw.circle(hi, color, pt(33, 35), r)
        pygame.draw.circle(hi, color, pt(67, 35), r)
        pygame.draw.polygon(
            hi,
            color,
            [pt(14, 42), pt(50, 90), pt(86, 42), pt(50, 26)],
        )
    elif suit == "♠":
        r = int(19.5 * s / 100)
        pygame.draw.polygon(
            hi,
            color,
            [pt(50, 8), pt(85, 51), pt(50, 62), pt(15, 51)],
        )
        pygame.draw.circle(hi, color, pt(33, 56), r)
        pygame.draw.circle(hi, color, pt(67, 56), r)
        pygame.draw.polygon(hi, color, [pt(50, 56), pt(36, 91), pt(64, 91)])
    elif suit == "♣":
        r = int(19 * s / 100)
        pygame.draw.circle(hi, color, pt(50, 29), r)
        pygame.draw.circle(hi, color, pt(30, 57), r)
        pygame.draw.circle(hi, color, pt(70, 57), r)
        pygame.draw.circle(hi, color, pt(50, 52), int(14 * s / 100))
        pygame.draw.polygon(hi, color, [pt(50, 54), pt(37, 91), pt(63, 91)])

    smooth = pygame.transform.smoothscale(hi, (box_size, box_size))
    surface.blit(smooth, (0, 0))


def build_table_surface(width, height, fonts):
    """Pre-render the 2x supersampled poker table background and card slots."""
    scale = 2
    sw, sh = width * scale, height * scale
    hi = pygame.Surface((sw, sh))
    hi.fill(BG_OUTER)

    # Subtle ambient background glow
    glow = pygame.Surface((sw, sh), pygame.SRCALPHA)
    for step in range(18, 0, -1):
        t = step / 18.0
        alpha = int(18 * (1.0 - t))
        rx = int(sw * (0.42 + t * 0.45))
        ry = int(sh * (0.36 + t * 0.42))
        rect = pygame.Rect((sw - rx) // 2, (sh - ry) // 2 - 20, rx, ry)
        pygame.draw.ellipse(glow, (*BG_INNER, alpha), rect)
    hi.blit(glow, (0, 0))

    # Outer table geometry in 2x space
    table_rect = pygame.Rect(88 * scale, 70 * scale, 1024 * scale, 536 * scale)
    rail_radius = 250 * scale

    # Drop shadow under the table
    shadow_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
    for i in range(6):
        expand = (6 - i) * 7 * scale
        s_rect = table_rect.inflate(expand, expand).move(0, 12 * scale)
        pygame.draw.rect(
            shadow_surf,
            (0, 0, 0, 26),
            s_rect,
            border_radius=rail_radius + expand // 2,
        )
    hi.blit(shadow_surf, (0, 0))

    # Mahogany wood rail with highlight bevel
    pygame.draw.rect(hi, WOOD_DARK, table_rect, border_radius=rail_radius)
    bevel_rect = table_rect.inflate(-8 * scale, -8 * scale)
    pygame.draw.rect(hi, WOOD_MID, bevel_rect, border_radius=rail_radius - 4 * scale)
    highlight_rect = table_rect.inflate(-16 * scale, -16 * scale)
    pygame.draw.rect(
        hi,
        WOOD_HIGHLIGHT,
        highlight_rect,
        width=3 * scale,
        border_radius=rail_radius - 8 * scale,
    )

    # Brass trim ring
    brass_rect = table_rect.inflate(-42 * scale, -42 * scale)
    pygame.draw.rect(
        hi,
        GOLD_MID,
        brass_rect,
        border_radius=rail_radius - 21 * scale,
    )

    # Emerald felt surface with soft radial spotlight
    felt_rect = table_rect.inflate(-50 * scale, -50 * scale)
    felt_radius = rail_radius - 25 * scale
    pygame.draw.rect(hi, FELT_DARK, felt_rect, border_radius=felt_radius)

    for step in range(14, 0, -1):
        ratio = step / 14.0
        col = (
            int(lerp(FELT_LIGHT[0], FELT_MID[0], ratio)),
            int(lerp(FELT_LIGHT[1], FELT_MID[1], ratio)),
            int(lerp(FELT_LIGHT[2], FELT_MID[2], ratio)),
        )
        inner = felt_rect.inflate(
            -int(felt_rect.width * 0.45 * (1.0 - ratio)),
            -int(felt_rect.height * 0.45 * (1.0 - ratio)),
        )
        pygame.draw.rect(
            hi,
            col,
            inner,
            border_radius=max(20, int(felt_radius * ratio)),
        )

    # Inner betting line on felt
    bet_line_rect = felt_rect.inflate(-58 * scale, -58 * scale)
    pygame.draw.rect(
        hi,
        FELT_LINE,
        bet_line_rect,
        width=2 * scale,
        border_radius=max(20, felt_radius - 29 * scale),
    )

    # Subtle felt watermark
    wm_font = fonts.get(12 * scale, bold=True)
    wm_surf = wm_font.render("TEXAS HOLD'EM   •   CASINO TABLE", True, GOLD_DIM)
    wm_surf.set_alpha(95)
    wm_rect = wm_surf.get_rect(center=(width * scale // 2, 263 * scale))
    hi.blit(wm_surf, wm_rect)

    # 5 recessed community card slots
    slot_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
    for idx in range(5):
        sx = (BOARD_START_X + idx * (CARD_WIDTH + BOARD_GAP)) * scale
        sy = BOARD_CARD_Y * scale
        s_rect = pygame.Rect(sx, sy, CARD_WIDTH * scale, CARD_HEIGHT * scale)
        pygame.draw.rect(
            slot_surf,
            (5, 32, 23, 140),
            s_rect,
            border_radius=9 * scale,
        )
        pygame.draw.rect(
            slot_surf,
            (*FELT_LINE, 165),
            s_rect,
            width=2 * scale,
            border_radius=9 * scale,
        )
    hi.blit(slot_surf, (0, 0))

    return pygame.transform.smoothscale(hi, (width, height))


class CardRenderer:
    """Pre-renders crisp 2x-supersampled playing cards and highlight halos."""

    def __init__(self, fonts):
        self.fonts = fonts
        self._suit_cache = {}
        self._face_cache = {}
        self._back_cache = {}
        self._glow_cache = {}
        self._shadow_cache = {}

        for size in (
            (CARD_WIDTH, CARD_HEIGHT),
            (SMALL_CARD_WIDTH, SMALL_CARD_HEIGHT),
            (MINI_CARD_WIDTH, MINI_CARD_HEIGHT),
            (DUAL_CARD_WIDTH, DUAL_CARD_HEIGHT),
        ):
            self._build_size_cache(size)

    def _get_suit_icon(self, suit, color, icon_size):
        key = (suit, color, icon_size)
        if key not in self._suit_cache:
            surf = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
            _draw_suit_vector(surf, suit, color, icon_size)
            self._suit_cache[key] = surf
        return self._suit_cache[key]

    def _build_size_cache(self, size):
        w, h = size
        scale = 2
        sw, sh = w * scale, h * scale
        radius = max(7, int(w * 0.1))

        # Drop shadow
        shadow = pygame.Surface((sw + 16, sh + 16), pygame.SRCALPHA)
        pygame.draw.rect(
            shadow,
            (0, 0, 0, 95),
            pygame.Rect(8, 12, sw, sh),
            border_radius=radius * scale,
        )
        self._shadow_cache[size] = pygame.transform.smoothscale(shadow, (w + 8, h + 8))

        # Winning highlight halo
        glow = pygame.Surface((sw + 24, sh + 24), pygame.SRCALPHA)
        for i in range(4):
            pad = (4 - i) * 3
            alpha = 48 + i * 35
            pygame.draw.rect(
                glow,
                (*GOLD_BRIGHT, alpha),
                pygame.Rect(12 - pad, 12 - pad, sw + pad * 2, sh + pad * 2),
                width=4,
                border_radius=(radius + 4) * scale,
            )
        self._glow_cache[size] = pygame.transform.smoothscale(glow, (w + 12, h + 12))

        # Card back
        back_hi = pygame.Surface((sw, sh), pygame.SRCALPHA)
        pygame.draw.rect(back_hi, CARD_IVORY, pygame.Rect(0, 0, sw, sh), border_radius=radius * scale)
        inner_rect = pygame.Rect(6 * scale, 6 * scale, sw - 12 * scale, sh - 12 * scale)
        pygame.draw.rect(
            back_hi,
            CARD_BACK_NAVY,
            inner_rect,
            border_radius=(radius - 2) * scale,
        )
        pygame.draw.rect(
            back_hi,
            GOLD_MID,
            inner_rect.inflate(-6 * scale, -6 * scale),
            width=2 * scale,
            border_radius=(radius - 3) * scale,
        )
        # Subtle geometric lattice inside back
        lattice = pygame.Surface((sw, sh), pygame.SRCALPHA)
        step = 14 * scale
        for x in range(12 * scale, sw - 10 * scale, step):
            for y in range(12 * scale, sh - 10 * scale, step):
                pts = [
                    (x, y - 4 * scale),
                    (x + 4 * scale, y),
                    (x, y + 4 * scale),
                    (x - 4 * scale, y),
                ]
                pygame.draw.polygon(lattice, (*CARD_BACK_INNER, 180), pts)
        back_hi.blit(lattice, (0, 0))
        # Center gold medallion on card back
        cx, cy = sw // 2, sh // 2
        pygame.draw.circle(back_hi, CARD_BACK_NAVY, (cx, cy), 14 * scale)
        pygame.draw.circle(back_hi, GOLD_MID, (cx, cy), 14 * scale, width=2 * scale)
        pygame.draw.circle(back_hi, GOLD_BRIGHT, (cx, cy), 6 * scale)
        self._back_cache[size] = pygame.transform.smoothscale(back_hi, (w, h))

        # All 52 card faces
        for suit in SUITS:
            for rank in range(2, 15):
                self._face_cache[(rank, suit, size)] = self._render_card_face(
                    rank, suit, w, h, radius
                )

    def _render_card_face(self, rank, suit, w, h, radius):
        scale = 2
        sw, sh = w * scale, h * scale
        hi = pygame.Surface((sw, sh), pygame.SRCALPHA)

        pygame.draw.rect(hi, CARD_IVORY, pygame.Rect(0, 0, sw, sh), border_radius=radius * scale)
        pygame.draw.rect(
            hi,
            CARD_BORDER,
            pygame.Rect(0, 0, sw, sh),
            width=max(2, scale),
            border_radius=radius * scale,
        )

        is_red = suit in ("♥", "♦")
        color = SUIT_RED if is_red else SUIT_BLACK
        rank_label = RANK_NAMES.get(rank, str(rank))

        corner_font = self.fonts.get(int(w * 0.22 * scale), bold=True)
        rank_surf = corner_font.render(rank_label, True, color)
        pad_x = int(w * 0.10 * scale)
        pad_y = int(h * 0.06 * scale)
        hi.blit(rank_surf, (pad_x, pad_y))

        small_suit_size = int(w * 0.19 * scale)
        small_suit = self._get_suit_icon(suit, color, small_suit_size)
        suit_x = pad_x + max(0, (rank_surf.get_width() - small_suit_size) // 2)
        suit_y = pad_y + rank_surf.get_height() - 2
        hi.blit(small_suit, (suit_x, suit_y))

        # Mirrored bottom-right corner index
        br_rank = pygame.transform.rotate(rank_surf, 180)
        br_suit = pygame.transform.rotate(small_suit, 180)
        hi.blit(br_rank, (sw - pad_x - br_rank.get_width(), sh - pad_y - br_rank.get_height()))
        br_suit_x = sw - pad_x - br_rank.get_width() + max(0, (br_rank.get_width() - small_suit_size) // 2)
        br_suit_y = sh - pad_y - br_rank.get_height() - small_suit_size + 2
        hi.blit(br_suit, (br_suit_x, br_suit_y))

        # Royal court subtle frame for J, Q, K, A
        if rank >= 11:
            frame_rect = pygame.Rect(
                int(sw * 0.27),
                int(sh * 0.24),
                int(sw * 0.46),
                int(sh * 0.52),
            )
            tint = (232, 214, 214) if is_red else (222, 226, 234)
            pygame.draw.rect(hi, tint, frame_rect, width=2 * scale, border_radius=6 * scale)

        # Center suit emblem
        center_size = int(w * 0.44 * scale)
        center_suit = self._get_suit_icon(suit, color, center_size)
        hi.blit(
            center_suit,
            ((sw - center_size) // 2, (sh - center_size) // 2 + (2 if rank >= 11 else 0)),
        )

        if rank == 14:
            badge_font = self.fonts.get(int(w * 0.17 * scale), bold=True)
            badge_surf = badge_font.render(rank_label, True, CARD_IVORY)
            b_rect = badge_surf.get_rect(center=(sw // 2, sh // 2 + 2))
            hi.blit(badge_surf, b_rect)

        return pygame.transform.smoothscale(hi, (w, h))

    def draw_card(
        self,
        surface,
        card,
        pos,
        face_up=True,
        small=False,
        card_size=None,
        highlighted=False,
        dimmed=False,
    ):
        """Draw a card (or card back) at pos with optional winning glow or dim overlay."""
        if card_size is not None:
            size = card_size
        else:
            size = (SMALL_CARD_WIDTH, SMALL_CARD_HEIGHT) if small else (CARD_WIDTH, CARD_HEIGHT)
        x, y = int(pos[0]), int(pos[1])

        if highlighted:
            glow = self._glow_cache[size]
            surface.blit(glow, (x - 6, y - 6))
        else:
            shadow = self._shadow_cache[size]
            surface.blit(shadow, (x - 2, y - 1))

        if face_up and card is not None:
            card_surf = self._face_cache[(card.rank, card.suit, size)]
        else:
            card_surf = self._back_cache[size]

        surface.blit(card_surf, (x, y))

        if dimmed:
            dim = pygame.Surface(size, pygame.SRCALPHA)
            dim.fill((10, 14, 20, 95))
            surface.blit(dim, (x, y))


def draw_chip_stack(surface, center_x, center_y, amount):
    """Draw a compact visual stack of casino chips proportional to amount."""
    if amount <= 0:
        return

    denominations = [
        (100, (36, 40, 48), GOLD_BRIGHT),
        (25, (28, 138, 92), (236, 240, 238)),
        (5, (192, 48, 58), (242, 238, 228)),
        (1, (232, 230, 224), (72, 108, 178)),
    ]

    chips = []
    remaining = amount
    for value, body_col, stripe_col in denominations:
        count = min(4, remaining // value)
        remaining %= value
        for _ in range(count):
            chips.append((body_col, stripe_col))
        if len(chips) >= 7:
            break

    if not chips:
        chips.append(((232, 230, 224), (72, 108, 178)))
    chips = chips[:7]

    chip_w, chip_h = 26, 10
    for idx, (body_col, stripe_col) in enumerate(chips):
        cy = center_y - idx * 4
        rect = pygame.Rect(center_x - chip_w // 2, cy - chip_h // 2, chip_w, chip_h)
        pygame.draw.ellipse(surface, (0, 0, 0, 110), rect.move(0, 2))
        pygame.draw.ellipse(surface, body_col, rect)
        pygame.draw.ellipse(surface, stripe_col, rect, width=2)
        inner = rect.inflate(-10, -4)
        pygame.draw.ellipse(surface, stripe_col, inner, width=1)


class SoundManager:
    """Generates and plays lightweight procedural casino sound effects."""

    def __init__(self):
        self.available = False
        self.muted = False
        self.sounds = {}
        self._init_mixer()

    def _init_mixer(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self.available = True
            self.sounds["card"] = self._make_card_sound()
            self.sounds["chip"] = self._make_chip_sound()
            self.sounds["check"] = self._make_check_sound()
            self.sounds["win"] = self._make_win_sound()
            self.sounds["fold"] = self._make_fold_sound()
        except pygame.error:
            self.available = False

    @staticmethod
    def _build_pcm(samples):
        buf = array("h", (max(-32767, min(32767, int(s * 32767))) for s in samples))
        return pygame.mixer.Sound(buffer=buf)

    def _make_card_sound(self):
        sr = 22050
        n = int(sr * 0.065)
        samples = []
        for i in range(n):
            t = i / sr
            env = math.exp(-t * 58)
            wave = (math.sin(2 * math.pi * 420 * t) * 0.4 + math.sin(2 * math.pi * 1150 * t) * 0.25)
            samples.append(wave * env * 0.18)
        return self._build_pcm(samples)

    def _make_chip_sound(self):
        sr = 22050
        n = int(sr * 0.09)
        samples = []
        for i in range(n):
            t = i / sr
            env = math.exp(-t * 42)
            wave = math.sin(2 * math.pi * 2450 * t) * 0.55 + math.sin(2 * math.pi * 3820 * t) * 0.45
            samples.append(wave * env * 0.16)
        return self._build_pcm(samples)

    def _make_check_sound(self):
        sr = 22050
        n = int(sr * 0.07)
        samples = []
        for i in range(n):
            t = i / sr
            env = math.exp(-t * 60)
            wave = math.sin(2 * math.pi * 190 * t)
            samples.append(wave * env * 0.22)
        return self._build_pcm(samples)

    def _make_win_sound(self):
        sr = 22050
        notes = [523.25, 659.25, 783.99, 1046.5]
        samples = []
        total = int(sr * 0.42)
        for i in range(total):
            t = i / sr
            val = 0.0
            for idx, freq in enumerate(notes):
                start = idx * 0.065
                if t >= start:
                    dt = t - start
                    val += math.sin(2 * math.pi * freq * dt) * math.exp(-dt * 9.5) * 0.22
            samples.append(val)
        return self._build_pcm(samples)

    def _make_fold_sound(self):
        sr = 22050
        n = int(sr * 0.14)
        samples = []
        for i in range(n):
            t = i / sr
            freq = 360 - 180 * (i / n)
            env = math.exp(-t * 22)
            samples.append(math.sin(2 * math.pi * freq * t) * env * 0.15)
        return self._build_pcm(samples)

    def toggle_mute(self):
        self.muted = not self.muted
        return self.muted

    def play(self, name):
        if self.available and not self.muted and name in self.sounds:
            self.sounds[name].play()
