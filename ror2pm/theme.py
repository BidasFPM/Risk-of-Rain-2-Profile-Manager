"""Minimalist dark theme for the RoR2 Profile Manager GUI."""
from __future__ import annotations


class Palette:
    BG          = "#0f1115"
    SIDEBAR     = "#12151b"
    PANEL       = "#171a21"
    PANEL_2     = "#1d212a"
    PANEL_3     = "#232834"
    BORDER      = "#262b36"
    TEXT        = "#e6e8ee"
    TEXT_MUTED  = "#8a90a0"
    TEXT_DIM    = "#5a6070"
    ACCENT      = "#7c5cff"
    ACCENT_HOV  = "#9277ff"
    ACCENT_DIM  = "#2f2a55"
    GREEN       = "#4ade80"
    GREEN_DIM   = "#14532d"
    RED         = "#f87171"
    RED_DIM     = "#7f1d1d"
    YELLOW      = "#fbbf24"
    YELLOW_DIM  = "#78350f"
    BLUE        = "#60a5fa"


FONT       = "Segoe UI"     # falls back automatically if missing
FONT_MONO  = "Consolas"


def size(n: int) -> tuple[str, int]:
    return (FONT, n)