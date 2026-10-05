"""Global search across database + current profile."""
from __future__ import annotations

import customtkinter as ctk

from ..core import kind_of, link_note, set_state
from ..theme import Palette
from .base import BaseView, CheckRow, SectionTitle


class SearchView(BaseView):
    title = "Search"

    def build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 6))
        bar.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkEntry(
            bar, placeholder_text="Search by name or ID…",
            fg_color=Palette.PANEL, border_color=Palette.BORDER,
            text_color=Palette.TEXT, height=36, corner_radius=8,
        )
        self.entry.grid(row=0, column=0, sticky="ew")
        self.entry.bind("<KeyRelease>", self._schedule_search)
        self.entry.bind("<Return>", lambda e: self._search_now())

        ctk.CTkButton(bar, text="Search", width=110, height=36,
                      fg_color=Palette.ACCENT, hover_color=Palette.ACCENT_HOV,
                      text_color="#0f1115",
                      command=self._search_now).grid(row=0, column=1, padx=(10, 0))

        self.hits_label = SectionTitle(self, "Results")
        self.hits_label.grid(row=1, column=0, sticky="w", padx=28, pady=(8, 4))

        self.list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.list.grid_columnconfigure(0, weight=1)

        self._hits: list[tuple[str, str, str]] = []
        self._debounce_id: str | None = None

    def _schedule_search(self, _event=None) -> None:
        # Debounce so we do not search on every keystroke
        if self._debounce_id is not None:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(180, self._search_now)

    def _search_now(self) -> None:
        self._debounce_id = None
        term = self.entry.get().strip().lower()
        for w in self.list.winfo_children():
            w.destroy()
        self._hits.clear()
        if not term:
            self.hits_label.configure(text="Type something to search")
            return

        for cat, items in self.app.db.items():
            kind = kind_of(cat)
            for code, label in items:
                if term in code.lower() or term in label.lower():
                    self._hits.append((code, label, kind))

        seen = {(c, k) for c, _, k in self._hits}
        for code in sorted(self.profile.unlocks):
            if term in code.lower() and (code, "unlock") not in seen:
                self._hits.append((code, code, "unlock"))
        for code in sorted(self.profile.achievements):
            if term in code.lower() and (code, "achievement") not in seen:
                self._hits.append((code, code, "achievement"))

        self.hits_label.configure(text=f"Results for \"{term}\"  ({len(self._hits)})")

        for i, (code, label, kind) in enumerate(self._hits):
            state = self.profile.state(code, kind)
            tag = "[achievement]" if kind == "achievement" else ""
            note = link_note(self.profile, code, kind) if kind == "unlock" else ""
            row = CheckRow(self.list, label=label, code=code, state=state,
                           note=(tag + " " + note).strip(),
                           command=lambda c=code, k=kind: self._toggle(c, k))
            row.grid(row=i, column=0, sticky="ew", padx=4, pady=1)

    def _toggle(self, code: str, kind: str) -> None:
        on = self.profile.state(code, kind) != 2
        set_state(self.profile, code, kind, on)
        self.app.mark_dirty()
        self._search_now()

    def on_show(self) -> None:
        self.entry.focus_set()
