"""Survivors: master list + detailed skills/skins/achievements."""
from __future__ import annotations

import customtkinter as ctk

from ..core import (
    SURVIVOR_DATA,
    entry_note,
    entry_state,
    set_entry,
    survivor_entries,
)
from ..theme import Palette
from .base import IconToplevel, BaseView, CheckRow, ProgressBar, SectionTitle


class SurvivorsView(BaseView):
    title = "Survivors"

    def build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        SectionTitle(self, "Skills, skins and achievements per survivor").grid(
            row=0, column=0, sticky="w", padx=28, pady=(22, 6))

        self.list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.list.grid_columnconfigure(0, weight=1)

    def _rebuild(self) -> None:
        for w in self.list.winfo_children():
            w.destroy()

        for i, data in enumerate(SURVIVOR_DATA):
            entries = survivor_entries(data, self.profile)
            complete = sum(1 for a, u, _, _ in entries
                           if entry_state(self.profile, a, u) == 2)
            total = len(entries)
            ratio = complete / max(total, 1)

            card = ctk.CTkFrame(self.list, fg_color=Palette.PANEL, corner_radius=10)
            card.grid(row=i, column=0, sticky="ew", padx=6, pady=4)
            card.grid_columnconfigure(0, weight=1)

            name = ctk.CTkLabel(card, text=data[0], anchor="w", text_color=Palette.TEXT,
                                font=ctk.CTkFont(size=14, weight="bold"))
            name.grid(row=0, column=0, sticky="w", padx=16, pady=(12, 0))

            pct = ctk.CTkLabel(card, text=f"{complete}/{total}",
                               text_color=Palette.GREEN if ratio == 1 else Palette.TEXT_MUTED,
                               font=ctk.CTkFont(size=11))
            pct.grid(row=0, column=1, sticky="e", padx=16, pady=(12, 0))

            bar = ProgressBar(card, height=6)
            bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(4, 12))
            bar.set(ratio)

            for w in (card, name, pct):
                w.bind("<Button-1>", lambda e, d=data: self._open(d))
                w.bind("<Enter>", lambda e, c=card: c.configure(fg_color=Palette.PANEL_2))
                w.bind("<Leave>", lambda e, c=card: c.configure(fg_color=Palette.PANEL))

    def _open(self, data) -> None:
        SurvivorDetail(self.app, data)

    def on_show(self) -> None:
        self._rebuild()


class SurvivorDetail(IconToplevel):
    def __init__(self, app, data):
        super().__init__(app)
        self.app = app
        self.profile = app.profile
        self.data = data
        self._row_map: dict[tuple, CheckRow] = {}
        self.title(f"RoR2 · {data[0]}")
        self.geometry("780x620")
        self.minsize(520, 420)
        self.configure(fg_color=Palette.BG)
        self.transient(app)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, fg_color=Palette.PANEL, corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text=data[0], anchor="w", text_color=Palette.TEXT,
                     font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=18, pady=(14, 0))

        self.summary = ctk.CTkLabel(header, text="", anchor="w",
                                    text_color=Palette.TEXT_MUTED,
                                    font=ctk.CTkFont(size=11))
        self.summary.grid(row=1, column=0, sticky="w", padx=18, pady=(2, 14))

        # toolbar
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 6))
        bar.grid_columnconfigure(0, weight=1)
        self.show_missing = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            bar, text="Only locked", variable=self.show_missing,
            command=self._rebuild,
            fg_color=Palette.ACCENT, hover_color=Palette.ACCENT_HOV,
            text_color=Palette.TEXT, border_color=Palette.BORDER,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(bar, text="Enable all", width=110, height=30,
                      fg_color=Palette.PANEL, hover_color=Palette.PANEL_3,
                      text_color=Palette.TEXT,
                      command=lambda: self._set_all(True)).grid(row=0, column=1, padx=(10, 0))
        ctk.CTkButton(bar, text="Clear", width=90, height=30,
                      fg_color=Palette.PANEL, hover_color=Palette.PANEL_3,
                      text_color=Palette.RED,
                      command=lambda: self._set_all(False)).grid(row=0, column=2, padx=(6, 0))

        self.list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 16))
        self.list.grid_columnconfigure(0, weight=1)

        self._rebuild()

    def _rebuild(self) -> None:
        for w in self.list.winfo_children():
            w.destroy()
        self._row_map.clear()

        all_e = survivor_entries(self.data, self.profile)
        missing_only = self.show_missing.get()
        shown = [e for e in all_e if not missing_only
                 or entry_state(self.profile, e[0], e[1]) != 2]

        self._update_summary(all_e)

        for i, (ach, unlock, label, _) in enumerate(shown):
            state = entry_state(self.profile, ach, unlock)
            note = entry_note(self.profile, ach, unlock)
            row = CheckRow(self.list, label=label, code=unlock or ach or "",
                           state=state, note=note,
                           command=lambda a=ach, u=unlock: self._toggle(a, u))
            row.grid(row=i, column=0, sticky="ew", padx=4, pady=1)
            self._row_map[(ach, unlock)] = row

    def _update_summary(self, all_e=None) -> None:
        if all_e is None:
            all_e = survivor_entries(self.data, self.profile)
        complete = sum(1 for e in all_e
                       if entry_state(self.profile, e[0], e[1]) == 2)
        self.summary.configure(
            text=f"{complete}/{len(all_e)} complete · showing {len(self._row_map)}"
        )

    def _toggle(self, ach, unlock) -> None:
        on = entry_state(self.profile, ach, unlock) != 2
        set_entry(self.profile, ach, unlock, on)
        self.app.mark_dirty()

        # Fast path: with no filter, update only the visible row
        if not self.show_missing.get():
            row = self._row_map.get((ach, unlock))
            if row is not None:
                row.set_state(entry_state(self.profile, ach, unlock))
            self._update_summary()
        else:
            self._rebuild()

    def _set_all(self, on: bool) -> None:
        if not on and not self.app.confirm("Remove EVERYTHING for this survivor?"):
            return
        for ach, unlock, _, _ in survivor_entries(self.data, self.profile):
            set_entry(self.profile, ach, unlock, on)
        self.app.mark_dirty()
        self._rebuild()
