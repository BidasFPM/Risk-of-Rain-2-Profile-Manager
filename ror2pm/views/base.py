"""Shared GUI components used by all views."""
from __future__ import annotations

import customtkinter as ctk

from ..theme import Palette


class BaseView(ctk.CTkFrame):
    """Every view inherits from this. `app` is the main window."""

    title = "View"

    def __init__(self, master, app):
        super().__init__(master, fg_color=Palette.BG, corner_radius=0)
        self.app = app
        self.build()

    @property
    def profile(self):
        """Always the App's current profile (avoids stale references)."""
        return self.app.profile

    def build(self) -> None:  # pragma: no cover - overridden
        ...

    def on_show(self) -> None:
        """Called each time the view becomes visible."""

    def on_hide(self) -> None:
        """Called when the view is replaced."""


class CheckRow(ctk.CTkFrame):
    """A clickable row with a status icon, label, ID and optional note."""

    def __init__(self, master, *, label: str, code: str = "", state: int,
                 note: str = "", command=None):
        super().__init__(master, fg_color="transparent", corner_radius=6, height=34)
        self.pack_propagate(False)
        self._command = command

        self._icon = ctk.CTkLabel(
            self, text=self._icon_text(state), width=22,
            text_color=self._icon_color(state),
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self._icon.pack(side="left", padx=(8, 0))

        self._label = ctk.CTkLabel(
            self, text=label, anchor="w",
            text_color=Palette.TEXT if state else Palette.TEXT_MUTED,
            font=ctk.CTkFont(size=12),
        )
        self._label.pack(side="left", padx=(4, 0), fill="x", expand=True)

        self._note = None
        if note:
            self._note = ctk.CTkLabel(self, text=note, text_color=Palette.TEXT_DIM,
                                      font=ctk.CTkFont(size=10))
            self._note.pack(side="right", padx=(0, 10))

        self._code = None
        if code:
            self._code = ctk.CTkLabel(self, text=code, text_color=Palette.TEXT_DIM,
                                      font=ctk.CTkFont(family="Consolas", size=10))
            self._code.pack(side="right", padx=(0, 10))

        for w in (self, self._icon, self._label, self._code, self._note):
            if w is None:
                continue
            w.bind("<Button-1>", self._clicked)
            w.bind("<Enter>", self._hover_in)
            w.bind("<Leave>", self._hover_out)

    @staticmethod
    def _icon_text(state: int) -> str:
        return {2: "✓", 1: "◐", 0: "○"}[state]

    @staticmethod
    def _icon_color(state: int) -> str:
        return {2: Palette.GREEN, 1: Palette.YELLOW, 0: Palette.BORDER}[state]

    def set_state(self, state: int) -> None:
        """Update the state without recreating the widget (optimization)."""
        self._icon.configure(text=self._icon_text(state),
                             text_color=self._icon_color(state))
        self._label.configure(
            text_color=Palette.TEXT if state else Palette.TEXT_MUTED,
        )

    def _clicked(self, _event=None):
        if self._command:
            self._command()

    def _hover_in(self, _event=None):
        self.configure(fg_color=Palette.PANEL_2)

    def _hover_out(self, _event=None):
        self.configure(fg_color="transparent")


class SectionTitle(ctk.CTkLabel):
    def __init__(self, master, text: str, **kw):
        super().__init__(master, text=text, anchor="w",
                         text_color=Palette.TEXT_MUTED,
                         font=ctk.CTkFont(size=11, weight="bold"), **kw)


class ProgressBar(ctk.CTkFrame):
    """Thin responsive bar — expands with its parent (grid sticky='ew')."""

    def __init__(self, master, height: int = 6, **kw):
        super().__init__(
            master, fg_color=Palette.PANEL_3,
            corner_radius=height // 2,
            width=1, height=height, **kw,
        )
        self._fill = ctk.CTkFrame(
            self, fg_color=Palette.ACCENT, corner_radius=height // 2,
        )
        self._fill.place(x=0, y=0, relheight=1, relwidth=0)

    def set(self, ratio: float) -> None:
        ratio = max(0.0, min(1.0, float(ratio)))
        self._fill.place_configure(relwidth=ratio)
