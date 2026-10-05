"""Generic category checklist view (used by all DB categories)."""
from __future__ import annotations

import customtkinter as ctk

from ..core import DLC_LABELS, dlc_of, kind_of, link_note, set_state
from ..theme import Palette
from .base import BaseView, CheckRow
from .tools import run_unlock_all


# Legacy duplicates: the game keeps an old unlock next to the current one (e.g. the original
# "Bandit" next to "Bandit2"). Only the current one is shown; toggling it also toggles the legacy one.
_HIDDEN_LEGACY = {"Characters.Bandit"}
_LEGACY_OF = {"Characters.Bandit2": ["Characters.Bandit"]}


class CategoryView(BaseView):
    def __init__(self, master, app, category: str, items=None, title: str | None = None):
        self.category = category
        self.kind = kind_of(category)
        self.title = title or category
        src = items if items is not None else app.db[category]
        self._items: list[tuple[str, str]] = [(c, l) for c, l in src if c not in _HIDDEN_LEGACY]
        self._filter = "all"          # all | missing | have
        self._search = ""
        self._dlc = "all"             # all | Base | SotV | SotS | AC
        self._row_map: dict[str, CheckRow] = {}
        super().__init__(master, app)

    def build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # --- Toolbar -----------------------------------------------------
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 6))
        bar.grid_columnconfigure(0, weight=1)

        self.search = ctk.CTkEntry(
            bar, placeholder_text="Filter this category…",
            fg_color=Palette.PANEL, border_color=Palette.BORDER,
            text_color=Palette.TEXT, height=34, corner_radius=8,
        )
        self.search.grid(row=0, column=0, sticky="ew")
        self.search.bind("<KeyRelease>", lambda e: self._on_search())

        seg = ctk.CTkSegmentedButton(
            bar, values=["All", "Missing", "Have"],
            command=self._on_filter,
            selected_color=Palette.ACCENT, selected_hover_color=Palette.ACCENT_HOV,
            unselected_color=Palette.PANEL, unselected_hover_color=Palette.PANEL_2,
            text_color=Palette.TEXT, fg_color=Palette.PANEL, height=34,
        )
        seg.grid(row=0, column=1, padx=(10, 0))
        seg.set("All")
        self._seg = seg

        present = {dlc_of(c) for c, _ in self._items}
        self._dlc_names = {"All content": "all"}
        self._dlc_names.update({f"{k} · {v}": k for k, v in DLC_LABELS.items() if k in present})
        self._dlc_menu = None
        if len(self._dlc_names) > 2:
            self._dlc_menu = ctk.CTkOptionMenu(
                bar, values=list(self._dlc_names), command=self._on_dlc, height=34, width=190,
                fg_color=Palette.PANEL, button_color=Palette.PANEL_2,
                button_hover_color=Palette.PANEL_3, text_color=Palette.TEXT,
            )
            self._dlc_menu.grid(row=0, column=4, padx=(10, 0))

        # Achievements and logbook share a single "Unlock All" button
        if self.kind == "achievement":
            ctk.CTkButton(
                bar, text="Unlock All", width=110, height=34,
                fg_color=Palette.ACCENT, hover_color=Palette.ACCENT_HOV,
                text_color="#0f1115", command=lambda: run_unlock_all(self.app),
            ).grid(row=0, column=2, padx=(10, 0))
        else:
            ctk.CTkButton(
                bar, text="Enable all", width=110, height=34,
                fg_color=Palette.PANEL, hover_color=Palette.PANEL_3,
                text_color=Palette.TEXT, command=self._select_all,
            ).grid(row=0, column=2, padx=(10, 0))

        ctk.CTkButton(
            bar, text="Clear", width=90, height=34,
            fg_color=Palette.PANEL, hover_color=Palette.PANEL_3,
            text_color=Palette.RED, command=self._clear_all,
        ).grid(row=0, column=3, padx=(6, 0))

        # --- Progress ----------------------------------------------------
        self.progress_label = ctk.CTkLabel(
            self, text="", anchor="w", text_color=Palette.TEXT_MUTED,
            font=ctk.CTkFont(size=11),
        )
        self.progress_label.grid(row=1, column=0, sticky="w", padx=28, pady=(0, 6))

        # --- Scroll list -------------------------------------------------
        self.list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.list.grid_columnconfigure(0, weight=1)

    # ------------------------------------------------------------------
    def _on_search(self) -> None:
        self._search = self.search.get().strip().lower()
        self._rebuild()

    def _on_filter(self, value: str) -> None:
        self._filter = {"All": "all", "Missing": "missing", "Have": "have"}[value]
        self._rebuild()

    def _on_dlc(self, value: str) -> None:
        self._dlc = self._dlc_names[value]
        self._rebuild()

    def _visible_items(self) -> list[tuple[str, str]]:
        out = []
        for code, label in self._items:
            if self._dlc != "all" and dlc_of(code) != self._dlc:
                continue
            state = self.profile.state(code, self.kind)
            if self._filter == "missing" and state == 2:
                continue
            if self._filter == "have" and state != 2:
                continue
            if self._search and self._search not in code.lower() and self._search not in label.lower():
                continue
            out.append((code, label))
        return out

    def _rebuild(self) -> None:
        for w in self.list.winfo_children():
            w.destroy()
        self._row_map.clear()

        items = self._visible_items()
        for i, (code, label) in enumerate(items):
            state = self.profile.state(code, self.kind)
            note = link_note(self.profile, code, self.kind) if self.kind == "unlock" else ""
            row = CheckRow(
                self.list, label=label, code=code, state=state, note=note,
                command=lambda c=code, k=self.kind: self._toggle(c, k),
            )
            row.grid(row=i, column=0, sticky="ew", padx=4, pady=1)
            self._row_map[code] = row

        self._update_progress(len(items))

    def _update_progress(self, shown: int | None = None) -> None:
        if shown is None:
            shown = len(self._row_map)
        n = self.profile.count(self._items, self.kind)
        self.progress_label.configure(
            text=f"{n}/{len(self._items)} active · showing {shown} of {len(self._items)}"
        )

    # ------------------------------------------------------------------
    def _toggle(self, code: str, kind: str) -> None:
        on = self.profile.state(code, kind) != 2
        set_state(self.profile, code, kind, on)
        for extra in _LEGACY_OF.get(code, ()):
            set_state(self.profile, extra, kind, on)
        self.app.mark_dirty()

        # Fast path: with no active filter, just update the visible row
        if self._filter == "all" and not self._search:
            row = self._row_map.get(code)
            if row is not None:
                row.set_state(self.profile.state(code, kind))
            self._update_progress()
        else:
            self._rebuild()

    def _select_all(self) -> None:
        for code, _ in self._items:
            if self._dlc == "all" or dlc_of(code) == self._dlc:
                set_state(self.profile, code, self.kind, True)
                for extra in _LEGACY_OF.get(code, ()):
                    set_state(self.profile, extra, self.kind, True)
        self.app.mark_dirty()
        self._rebuild()

    def _clear_all(self) -> None:
        if not self.app.confirm(
            f"This removes EVERYTHING in '{self.category}' (including what you already had). Continue?"
        ):
            return
        for code, _ in self._items:
            set_state(self.profile, code, self.kind, False)
            for extra in _LEGACY_OF.get(code, ()):
                set_state(self.profile, extra, self.kind, False)
        self.app.mark_dirty()
        self._rebuild()

    def on_show(self) -> None:
        self._rebuild()
