"""Theme colors, typography helpers, and vector-smoothing utilities for the Pygame UI."""

import pygame


WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 760
FPS = 60

CARD_WIDTH = 88
CARD_HEIGHT = 126
SMALL_CARD_WIDTH = 74
SMALL_CARD_HEIGHT = 106
MINI_CARD_WIDTH = 52
MINI_CARD_HEIGHT = 74
DUAL_CARD_WIDTH = 66
DUAL_CARD_HEIGHT = 94

# Midnight Casino / Velvet Lounge palette
BG_OUTER = (11, 16, 24)
BG_INNER = (19, 28, 42)

WOOD_DARK = (46, 26, 16)
WOOD_MID = (72, 42, 26)
WOOD_HIGHLIGHT = (102, 62, 38)

GOLD_BRIGHT = (242, 201, 76)
GOLD_MID = (201, 162, 77)
GOLD_DIM = (128, 102, 48)

FELT_DARK = (9, 51, 37)
FELT_MID = (14, 72, 52)
FELT_LIGHT = (21, 96, 69)
FELT_LINE = (34, 122, 91)

PANEL_BG = (18, 25, 36)
PANEL_BG_ALT = (26, 36, 51)
PANEL_BORDER = (52, 68, 92)
TEXT_PRIMARY = (244, 246, 250)
TEXT_SECONDARY = (164, 177, 198)
TEXT_MUTED = (108, 122, 145)

CARD_IVORY = (250, 248, 242)
CARD_BORDER = (214, 208, 195)
SUIT_RED = (200, 35, 51)
SUIT_BLACK = (27, 32, 40)
CARD_BACK_NAVY = (24, 42, 76)
CARD_BACK_INNER = (34, 58, 102)

BTN_FOLD = (158, 46, 56)
BTN_FOLD_HOVER = (190, 58, 70)
BTN_CALL = (24, 134, 98)
BTN_CALL_HOVER = (32, 162, 119)
BTN_RAISE = (196, 141, 34)
BTN_RAISE_HOVER = (224, 164, 44)
BTN_ALLIN = (114, 68, 178)
BTN_ALLIN_HOVER = (138, 86, 210)
BTN_NEUTRAL = (44, 56, 76)
BTN_NEUTRAL_HOVER = (62, 78, 104)
BTN_DISABLED = (32, 40, 52)

BADGE_CHECK = (42, 128, 98)
BADGE_CALL = (34, 118, 164)
BADGE_RAISE = (196, 134, 28)
BADGE_FOLD = (146, 48, 56)
BADGE_ALLIN = (128, 66, 188)
BADGE_BLIND = (64, 78, 102)

TIER_COLORS = {
    "Ultra": {
        "bg": (164, 34, 62),
        "border": (245, 197, 66),
        "text": (255, 232, 156),
        "accent": (235, 68, 98),
        "card_bg": (42, 18, 28),
    },
    "Master": {
        "bg": (106, 52, 174),
        "border": (182, 130, 252),
        "text": (238, 224, 255),
        "accent": (158, 102, 242),
        "card_bg": (28, 20, 44),
    },
    "Pro": {
        "bg": (22, 124, 90),
        "border": (74, 212, 162),
        "text": (216, 255, 238),
        "accent": (46, 186, 138),
        "card_bg": (16, 34, 30),
    },
    "Normal": {
        "bg": (34, 92, 156),
        "border": (98, 168, 244),
        "text": (218, 238, 255),
        "accent": (74, 148, 230),
        "card_bg": (18, 28, 42),
    },
    "Rookie": {
        "bg": (64, 74, 90),
        "border": (124, 138, 158),
        "text": (196, 206, 220),
        "accent": (118, 130, 150),
        "card_bg": (22, 27, 36),
    },
}


def ease_out_cubic(t):
    """Smooth deceleration curve for card and chip animations."""
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def lerp(start, end, t):
    """Linearly interpolate between start and end."""
    return start + (end - start) * t


class FontPalette:
    """Loads consistent sans-serif fonts across Windows, macOS, and Linux."""

    def __init__(self):
        self.family = self._pick_font_family()
        self._cache = {}

    @staticmethod
    def _pick_font_family():
        available = set(pygame.font.get_fonts())
        for candidate in ("segoeui", "arial", "helveticaneue", "dejavusans", "liberation"):
            if candidate in available:
                return candidate
        return None

    def get(self, size, bold=False):
        key = (size, bold)
        if key not in self._cache:
            if self.family:
                self._cache[key] = pygame.font.SysFont(self.family, size, bold=bold)
            else:
                self._cache[key] = pygame.font.Font(None, size)
        return self._cache[key]


def make_aa_rounded_rect(size, color, radius, border_color=None, border_width=0):
    """Render a 2x supersampled anti-aliased rounded rectangle surface."""
    width, height = size
    scale = 2
    surf = pygame.Surface((width * scale, height * scale), pygame.SRCALPHA)
    rect = pygame.Rect(0, 0, width * scale, height * scale)
    pygame.draw.rect(surf, color, rect, border_radius=radius * scale)
    if border_color and border_width > 0:
        pygame.draw.rect(
            surf,
            border_color,
            rect,
            width=border_width * scale,
            border_radius=radius * scale,
        )
    return pygame.transform.smoothscale(surf, (width, height))


def draw_text(surface, font, text, color, pos, anchor="topleft"):
    """Render text and blit it using any pygame.Rect anchor attribute."""
    rendered = font.render(text, True, color)
    rect = rendered.get_rect(**{anchor: pos})
    surface.blit(rendered, rect)
    return rect
