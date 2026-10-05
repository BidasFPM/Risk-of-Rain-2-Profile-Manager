"""Dashboard: category progress and quick actions."""
from __future__ import annotations

import customtkinter as ctk

from ..core import DLC_LABELS, dlc_progress, kind_of
from ..theme import Palette
from .base import BaseView, ProgressBar, SectionTitle


class DashboardView(BaseView):
    title = "Dashboard"

    def build(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        # --- Hero / profile card -----------------------------------------
        hero = ctk.CTkFrame(self, fg_color=Palette.PANEL, corner_radius=14)
        hero.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 12))
        hero.grid_columnconfigure(0, weight=1)

        self.profile_name = ctk.CTkLabel(
            hero, text="", anchor="w",
            text_color=Palette.TEXT, font=ctk.CTkFont(size=22, weight="bold"),
        )
        self.profile_name.grid(row=0, column=0, sticky="w", padx=22, pady=(18, 0))

        self.profile_path = ctk.CTkLabel(
            hero, text="", anchor="w",
            text_color=Palette.TEXT_MUTED, font=ctk.CTkFont(size=11),
        )
        self.profile_path.grid(row=1, column=0, sticky="w", padx=22, pady=(2, 0))

        # Stats — 2x2 grid
        stats = ctk.CTkFrame(hero, fg_color="transparent")
        stats.grid(row=2, column=0, sticky="ew", padx=22, pady=(14, 18))
        for i in range(2):
            stats.grid_columnconfigure(i, weight=1, uniform="stat")
        for i in range(2):
            stats.grid_rowconfigure(i, weight=1, uniform="stat_row")

        self._stat_labels = []
        for idx, label in enumerate(("Unlocks", "Achievements", "Coins", "Progress")):
            r, c = divmod(idx, 2)
            box = ctk.CTkFrame(stats, fg_color=Palette.PANEL_2, corner_radius=10)
            box.grid(row=r, column=c, sticky="nsew",
                     padx=(0 if c == 0 else 6, 0), pady=(0 if r == 0 else 6, 0))
            box.grid_columnconfigure(0, weight=1)
            val = ctk.CTkLabel(box, text="—", text_color=Palette.TEXT,
                               font=ctk.CTkFont(size=18, weight="bold"))
            val.grid(row=0, column=0, padx=14, pady=(10, 0), sticky="w")
            cap = ctk.CTkLabel(box, text=label, text_color=Palette.TEXT_MUTED,
                               font=ctk.CTkFont(size=10))
            cap.grid(row=1, column=0, padx=14, pady=(0, 10), sticky="w")
            self._stat_labels.append(val)

        # --- DLC progress ------------------------------------------------
        SectionTitle(self, "Progress by DLC").grid(
            row=1, column=0, sticky="w", padx=28, pady=(12, 6))
        self.dlc_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.dlc_frame.grid(row=2, column=0, sticky="ew", padx=24)
        self.dlc_frame.grid_columnconfigure(0, weight=1)
        self._dlc_widgets: dict[str, tuple[ctk.CTkLabel, ProgressBar]] = {}

        # --- Categories grid ---------------------------------------------
        SectionTitle(self, "Progress by category").grid(
            row=3, column=0, sticky="w", padx=28, pady=(12, 6))

        self.cats_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.cats_frame.grid(row=4, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.cats_frame.grid_columnconfigure(0, weight=1)

        self.rowconfigure(4, weight=1)
        self._cat_widgets: list[tuple[str, ctk.CTkLabel, ProgressBar]] = []
        self._built_db_keys: tuple[str, ...] = ()

    # ------------------------------------------------------------------
    def _build_categories(self) -> None:
        db_keys = tuple(self.app.db.keys())

        # Fast path: layout already exists and the database is unchanged → only update values
        if self._cat_widgets and db_keys == self._built_db_keys:
            for cat, label, bar in self._cat_widgets:
                items = self.app.db[cat]
                n = self.profile.count(items, kind_of(cat))
                label.configure(text=f"{n}/{len(items)}")
                bar.set(n / max(len(items), 1))
            return

        # Full rebuild
        for w in self.cats_frame.winfo_children():
            w.destroy()
        self._cat_widgets.clear()

        for i, (cat, items) in enumerate(self.app.db.items()):
            kind = kind_of(cat)
            n = self.profile.count(items, kind)
            total = len(items)

            card = ctk.CTkFrame(self.cats_frame, fg_color=Palette.PANEL, corner_radius=10)
            card.grid(row=i, column=0, sticky="ew", padx=6, pady=4)
            card.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(card, text=cat, anchor="w", text_color=Palette.TEXT,
                         font=ctk.CTkFont(size=13, weight="bold")).grid(
                row=0, column=0, sticky="w", padx=16, pady=(12, 2))

            val = ctk.CTkLabel(card, text=f"{n}/{total}", text_color=Palette.TEXT_MUTED,
                               font=ctk.CTkFont(size=11))
            val.grid(row=0, column=1, sticky="e", padx=16, pady=(12, 2))

            bar = ProgressBar(card, height=6)
            bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 14))
            bar.set(n / max(total, 1))

            self._cat_widgets.append((cat, val, bar))

        self._built_db_keys = db_keys

    # ------------------------------------------------------------------
    def _build_dlc(self) -> None:
        prog = dlc_progress(self.profile, self.app.db)
        if set(prog) != set(self._dlc_widgets):
            for w in self.dlc_frame.winfo_children():
                w.destroy()
            self._dlc_widgets.clear()
            for i, key in enumerate(prog):
                card = ctk.CTkFrame(self.dlc_frame, fg_color=Palette.PANEL, corner_radius=10)
                card.grid(row=i, column=0, sticky="ew", pady=3)
                card.grid_columnconfigure(0, weight=1)
                ctk.CTkLabel(card, text=DLC_LABELS.get(key, key), anchor="w", text_color=Palette.TEXT,
                             font=ctk.CTkFont(size=13, weight="bold")).grid(
                    row=0, column=0, sticky="w", padx=16, pady=(10, 2))
                val = ctk.CTkLabel(card, text="", text_color=Palette.TEXT_MUTED,
                                   font=ctk.CTkFont(size=11))
                val.grid(row=0, column=1, sticky="e", padx=16, pady=(10, 2))
                bar = ProgressBar(card, height=6)
                bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 12))
                self._dlc_widgets[key] = (val, bar)
        for key, (have, total) in prog.items():
            val, bar = self._dlc_widgets[key]
            val.configure(text=f"{have}/{total}")
            bar.set(have / max(total, 1))

    def refresh_stats(self) -> None:
        p = self.profile
        total = sum(len(v) for v in self.app.db.values())
        done = sum(p.count(v, kind_of(c)) for c, v in self.app.db.items())
        coins = p.coins
        self._stat_labels[0].configure(text=str(len(p.unlocks)))
        self._stat_labels[1].configure(text=str(len(p.achievements)))
        self._stat_labels[2].configure(text="—" if coins is None else str(coins))
        self._stat_labels[3].configure(text=f"{int(100 * done / max(total, 1))}%")

    def on_show(self) -> None:
        p = self.profile
        self.profile_name.configure(text=p.name or p.path.name)
        self.profile_path.configure(text=str(p.path))
        self.refresh_stats()
        self._build_dlc()
        self._build_categories()
