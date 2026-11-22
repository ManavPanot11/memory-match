"""
ui/theme.py
===========
Colour palette, font helpers, and shared widget-style constants for the
Memory Match Tiles game's vibrant light theme.

All colours are defined as module-level constants so every widget module can
import them without circular dependencies.

Usage
-----
    from ui.theme import apply_theme, get_font, BG_CREAM, CORAL, CARD_COLORS
    apply_theme()
    lbl = ctk.CTkLabel(master, text="Hi", font=get_font(18, "bold"))
"""

from __future__ import annotations

import logging
import os
from typing import Optional, Tuple, Union

import customtkinter as ctk

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ── Internal colour utilities (defined early for use in constants) ─────────
# ---------------------------------------------------------------------------

def _darken(hex_color: str, amount: float = 0.1) -> str:
    """Return *hex_color* darkened by *amount* (0.0–1.0)."""
    try:
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 3:
            hex_color = "".join(c * 2 for c in hex_color)
        r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = max(0, int(r * (1 - amount)))
        g = max(0, int(g * (1 - amount)))
        b = max(0, int(b * (1 - amount)))
        return f"#{r:02X}{g:02X}{b:02X}"
    except Exception:
        return hex_color


# ---------------------------------------------------------------------------
# ── Colour palette ──────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

# Background
BG_CREAM        = "#FFF8E7"   # warm cream – main window background

# Primary accents
CORAL           = "#FF6B6B"   # coral red
SUNNY_YELLOW    = "#FFD93D"   # sunny yellow
YELLOW          = SUNNY_YELLOW # alias
MINT            = "#6BCB77"   # mint green
SKY_BLUE        = "#4D96FF"   # sky blue
PURPLE          = "#9B5DE5"   # purple
PINK            = "#F15BB5"   # hot pink

# Neutral / UI support colours
WHITE           = "#FFFFFF"
OFF_WHITE       = "#FFF0CC"
LIGHT_GREY      = "#EDE8DC"
MID_GREY        = "#C5BFB0"
DARK_GREY       = "#5A5550"
ALMOST_BLACK    = "#2B2520"

# Semantic aliases
PRIMARY         = SKY_BLUE
SECONDARY       = MINT
DANGER          = CORAL
WARNING         = SUNNY_YELLOW
SUCCESS         = MINT
INFO            = SKY_BLUE

# Text
TEXT_DARK       = ALMOST_BLACK
TEXT_LIGHT      = WHITE
TEXT_MUTED      = DARK_GREY

# Card colours – one per column in the 4×6 rainbow grid
CARD_COLORS: list[str] = [
    "#FF9AA2",   # candy pink
    "#FFD166",   # candy yellow
    "#A8E6CF",   # candy mint
    "#A0C4FF",   # candy blue
    "#C9B1FF",   # candy lavender
    "#FFABAB",   # candy peach-red
]
CARD_BACK_COLORS = CARD_COLORS

# Card face / matched highlight
CARD_BACK_TEXT      = "#FFFFFF"
CARD_MATCHED_BORDER = MINT
CARD_DEFAULT_BORDER = MID_GREY

# Border radius
CORNER_RADIUS = 12

# Dictionary of semantic colors used by screen templates
COLORS: dict[str, str] = {
    "background":      BG_CREAM,
    "card":            WHITE,
    "border":          MID_GREY,
    "input_bg":        WHITE,
    "primary":         CORAL,
    "text":            TEXT_DARK,
    "text_muted":      DARK_GREY,
    "coral":           CORAL,
    "coral_hover":     _darken(CORAL, 0.12),
    "mint":            MINT,
    "mint_hover":      _darken(MINT, 0.12),
    "gold":            SUNNY_YELLOW,
    "link":            SKY_BLUE,
    "hover_link":      _darken(SKY_BLUE, 0.12),
    "error":           "#E63946",
    "success":         MINT,
    "table_header":    "#FDE68A",
    "table_odd":       "#FFFDF5",
    "table_even":      BG_CREAM,
    "table_highlight": "#FEF08A",
    "win_bg":          PURPLE,
    "win_card":        "#8246CA",
}

# ---------------------------------------------------------------------------
# ── Layout constants ────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

WINDOW_MIN_WIDTH  = 900
WINDOW_MIN_HEIGHT = 650

CARD_WIDTH   = 110
CARD_HEIGHT  = 130
GRID_ROWS    = 4
GRID_COLS    = 6

CARD_PAD_X = 6
CARD_PAD_Y = 6

# ---------------------------------------------------------------------------
# ── Font loading & presets ──────────────────────────────────────────────────
# ---------------------------------------------------------------------------

_FONT_FAMILY: str = ""

_PREFERRED_FONTS = [
    ("Fredoka",            "fonts/Fredoka_wdth_wght.ttf"),
    ("Fredoka One",        "fonts/FredokaOne-Regular.ttf"),
    ("Baloo 2",            "fonts/Baloo2-Regular.ttf"),
    ("Baloo 2",            "fonts/Baloo2-Bold.ttf"),
]

_FALLBACK_SYSTEM_FONTS = [
    "Comic Sans MS",
    "Arial Rounded MT Bold",
    "Arial",
]

_FONT_PRESETS: dict[str, tuple[int, str]] = {
    "title":           (26, "bold"),
    "win_title":       (28, "bold"),
    "section":         (18, "bold"),
    "label":           (13, "bold"),
    "body":            (14, "normal"),
    "button":          (15, "bold"),
    "small_button":    (12, "bold"),
    "small":           (12, "normal"),
    "link":            (13, "bold"),
    "table_header":    (14, "bold"),
    "table":           (13, "normal"),
    "stat_value":      (20, "bold"),
    "stat_value_win":  (18, "bold"),
    "record":          (16, "bold"),
}


def _fonts_dir() -> str:
    """Return the absolute path to the fonts/ directory next to this file's package."""
    import sys
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "fonts")
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "fonts")


def _load_fonts() -> str:
    """
    Attempt to load custom .ttf fonts via tkinter.font.
    Returns the resolved font-family name.
    """
    import tkinter.font as tkfont

    fonts_dir = _fonts_dir()
    loaded_family: Optional[str] = None

    for family, rel_path in _PREFERRED_FONTS:
        abs_path = os.path.join(fonts_dir, os.path.basename(rel_path))
        if os.path.isfile(abs_path):
            try:
                if hasattr(ctk, "FontManager"):
                    ctk.FontManager.load_font(abs_path)
                else:
                    import ctypes, sys
                    if sys.platform == "win32":
                        ctypes.windll.gdi32.AddFontResourceExW(abs_path, 0x10, 0)
                loaded_family = family
                logger.info("Loaded custom font: %s from %s", family, abs_path)
                break
            except Exception as exc:
                logger.debug("Could not load font %s: %s", abs_path, exc)

    if loaded_family:
        return loaded_family

    try:
        available = tkfont.families()
        for font in _FALLBACK_SYSTEM_FONTS:
            if font in available:
                logger.info("Using system font fallback: %s", font)
                return font
    except Exception:
        pass

    logger.warning("No preferred font found; using system default.")
    return "Arial"


def get_font(size_or_preset: Union[int, float, str], weight: str = "normal") -> ctk.CTkFont:
    """
    Return a :class:`ctk.CTkFont` using the application's resolved font family.

    Supports preset string names (e.g. 'title', 'body', 'button')
    or explicit point size and weight.
    """
    global _FONT_FAMILY
    if not _FONT_FAMILY:
        _FONT_FAMILY = _load_fonts()

    if isinstance(size_or_preset, str):
        if size_or_preset in _FONT_PRESETS:
            preset_size, preset_weight = _FONT_PRESETS[size_or_preset]
            return ctk.CTkFont(family=_FONT_FAMILY, size=preset_size, weight=preset_weight)
        try:
            val = int(size_or_preset)
            return ctk.CTkFont(family=_FONT_FAMILY, size=val, weight=weight)
        except ValueError:
            return ctk.CTkFont(family=_FONT_FAMILY, size=14, weight=weight)

    return ctk.CTkFont(family=_FONT_FAMILY, size=int(size_or_preset), weight=weight)


# ---------------------------------------------------------------------------
# ── Widget style dictionaries ───────────────────────────────────────────────
# ---------------------------------------------------------------------------

def button_style(
    color: str = SKY_BLUE,
    text_color: str = WHITE,
    hover_color: Optional[str] = None,
    corner_radius: int = 20,
    height: int = 40,
    font_size: int = 14,
    font_weight: str = "bold",
) -> dict:
    """Return a kwargs dict suitable for ctk.CTkButton(**button_style(...))."""
    if hover_color is None:
        hover_color = _darken(color, 0.15)
    return {
        "fg_color":      color,
        "hover_color":   hover_color,
        "text_color":    text_color,
        "corner_radius": corner_radius,
        "height":        height,
        "font":          get_font(font_size, font_weight),
        "border_width":  0,
        "cursor":        "hand2",
    }


def pill_badge_style(bg_color: str = SKY_BLUE, text_color: str = WHITE) -> dict:
    """Return a kwargs dict for the outer frame of a PillBadge."""
    return {
        "fg_color":      bg_color,
        "corner_radius": 20,
        "border_width":  0,
    }


# ---------------------------------------------------------------------------
# ── Theme application ───────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

def apply_theme() -> None:
    """
    Configure customtkinter for the vibrant light theme.
    Call once at application startup, before creating any widgets.
    """
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    global _FONT_FAMILY
    if not _FONT_FAMILY:
        _FONT_FAMILY = _load_fonts()

    logger.info("Theme applied – appearance=light, font=%s", _FONT_FAMILY)
