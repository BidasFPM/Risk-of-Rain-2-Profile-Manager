"""Main application window: sidebar, header, view router, save flow."""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from .core import (
    ACH_SUFFIX,
    APP_NAME,
    ICON_ICO,
    ICON_PNG,
    VERSION,
    Database,
    PICK_SUFFIX,
    Profile,
    discover_profiles,
    game_running,
    label_of,
    load_database,
    logbook_entries,
    profile_fingerprint,
    profile_summary,
)
from .theme import Palette
from .views.base import BaseView
from .views.category import CategoryView
from .views.dashboard import DashboardView
from .views.search import SearchView
from .views.survivors import SurvivorsView
from .views.tools import (
    BackupsView,
    CoinsDialog,
    InspectView,
    MergeView,
    PasteIDsDialog,
    run_diagnose,
    run_export_db,
    run_reset_all,
    run_status,
    run_sync_logbook,
    run_unlock_all,
    run_unlock_dlc,
)

ctk.set_appearance_mode("dark")


# =========================================================================
# Profile picker window (pre-GUI)
# =========================================================================
def _profile_picker_window(profiles: list[Path]) -> Path | None:
    picked: dict[str, Path | None] = {"path": None}

    win = ctk.CTk()
    win.title(f"{APP_NAME} — Select profile")
    win.geometry("720x520")
    win.minsize(560, 420)
    win.configure(fg_color=Palette.BG)
    win.grid_columnconfigure(0, weight=1)
    win.rowconfigure(2, weight=1)

    try:
        if ICON_PNG.is_file():
            win._picker_icon = tk.PhotoImage(file=str(ICON_PNG))
            win.iconphoto(True, win._picker_icon)
    except Exception:
        pass
    try:
        if ICON_ICO.is_file():
            win.iconbitmap(default=str(ICON_ICO))
    except Exception:
        pass

    ctk.CTkLabel(win, text="Select profile", anchor="w",
                 text_color=Palette.TEXT, font=ctk.CTkFont(size=20, weight="bold")).grid(
        row=0, column=0, sticky="w", padx=28, pady=(24, 2))
    ctk.CTkLabel(win, text="Several Steam profiles were found. Pick one.",
                 anchor="w", text_color=Palette.TEXT_MUTED,
                 font=ctk.CTkFont(size=11)).grid(row=1, column=0, sticky="w", padx=28)

    scroll = ctk.CTkScrollableFrame(win, fg_color="transparent")
    scroll.grid(row=2, column=0, sticky="nsew", padx=18, pady=(12, 18))
    scroll.grid_columnconfigure(0, weight=1)

    def choose(p: Path) -> None:
        picked["path"] = p
        win.destroy()

    for i, p in enumerate(profiles):
        card = ctk.CTkFrame(scroll, fg_color=Palette.PANEL, corner_radius=10)
        card.grid(row=i, column=0, sticky="ew", padx=6, pady=4)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text=profile_summary(p), anchor="w", text_color=Palette.TEXT,
                     font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=16, pady=(12, 0))
        ctk.CTkLabel(card, text=profile_fingerprint(p), anchor="w",
                     text_color=Palette.TEXT_MUTED,
                     font=ctk.CTkFont(size=10)).grid(row=1, column=0, sticky="w",
                                                     padx=16, pady=(0, 12))

        ctk.CTkButton(card, text="Open", width=90, height=32,
                      fg_color=Palette.ACCENT, hover_color=Palette.ACCENT_HOV,
                      text_color="#0f1115",
                      command=lambda q=p: choose(q)).grid(row=0, column=1, rowspan=2, padx=16)

    win.mainloop()
    return picked["path"]


def _resolve_profile(explicit: str | None) -> Path | None:
    if explicit:
        p = Path(explicit).expanduser()
        if p.is_file():
            return p
        print(f"File not found: {p}", file=sys.stderr)
        return None

    profiles = sorted(discover_profiles(), key=lambda x: x.stat().st_mtime, reverse=True)
    if not profiles:
        from tkinter import filedialog
        root = ctk.CTk()
        root.withdraw()
        result = filedialog.askopenfilename(
            title="Select the profile .xml",
            filetypes=[("RoR2 profile", "*.xml"), ("All files", "*.*")],
        )
        root.destroy()
        return Path(result) if result else None
    if len(profiles) == 1:
        return profiles[0]
    return _profile_picker_window(profiles)


# =========================================================================
# Main window
# =========================================================================
class App(ctk.CTk):
    def __init__(self, profile: Profile, db: Database, *, dry_run: bool = False):
        super().__init__()
        self.profile = profile
        self.db = db
        self.dry_run = dry_run
        self._views: dict[str, BaseView] = {}
        self._current_view: BaseView | None = None
        self._sidebar_buttons: dict[str, ctk.CTkButton] = {}
        self._toast: ctk.CTkLabel | None = None
        self._sidebar_visible = True
        self._sidebar: ctk.CTkFrame | None = None

        self.title(f"{APP_NAME} v{VERSION}")
        self._set_window_icon()
        self.geometry("1240x800")
        # low minsize so the window can be shrunk a lot
        self.minsize(640, 480)
        self.configure(fg_color=Palette.BG)

        # column 0 = sidebar (weight 0), column 1 = main (weight 1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        if game_running():
            self.after(400, lambda: self.toast(
                "Risk of Rain 2 is running. Close the game to avoid overwrites.", "warn"))

        self.show_view("dashboard")
        self._refresh_header()

    # ------------------------------------------------------------------
    def _set_window_icon(self) -> None:
        try:
            if ICON_PNG.is_file():
                self._icon_img = tk.PhotoImage(file=str(ICON_PNG))
                self.iconphoto(True, self._icon_img)
        except Exception:
            pass
        try:
            if ICON_ICO.is_file():
                self.iconbitmap(default=str(ICON_ICO))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------
    def _build_sidebar(self) -> None:
        sb = ctk.CTkFrame(self, fg_color=Palette.SIDEBAR, corner_radius=0, width=240)
        sb.grid(row=0, column=0, sticky="nsw")
        sb.grid_propagate(False)
        sb.grid_columnconfigure(0, weight=1)
        sb.grid_rowconfigure(1, weight=1)  # scrollable area fills the middle
        self._sidebar = sb

        # ---- fixed top -------------------------------------------------
        title = ctk.CTkFrame(sb, fg_color="transparent")
        title.grid(row=0, column=0, sticky="ew", padx=20, pady=(22, 10))
        ctk.CTkLabel(title, text="ROR2", anchor="w", text_color=Palette.ACCENT,
                     font=ctk.CTkFont(size=10, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(title, text="Profile Manager", anchor="w", text_color=Palette.TEXT,
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(title, text="Created by Bidas", anchor="w",
                     text_color=Palette.TEXT_MUTED,
                     font=ctk.CTkFont(size=10)).pack(anchor="w", pady=(2, 0))

        # ---- scrollable middle ------------------------------------------
        nav = ctk.CTkScrollableFrame(sb, fg_color="transparent",
                                     scrollbar_button_color=Palette.PANEL_2,
                                     scrollbar_button_hover_color=Palette.PANEL_3)
        nav.grid(row=1, column=0, sticky="nsew", padx=(6, 4), pady=(0, 6))
        nav.grid_columnconfigure(0, weight=1)

        def section(text: str) -> None:
            ctk.CTkLabel(nav, text=text.upper(), anchor="w",
                         text_color=Palette.TEXT_DIM,
                         font=ctk.CTkFont(size=10, weight="bold")).pack(
                fill="x", padx=14, pady=(14, 4))

        def nav_btn(text: str, view: str, *, muted: bool = False, cmd=None):
            btn = ctk.CTkButton(
                nav, text=f"  {text}", anchor="w", height=32, corner_radius=8,
                fg_color="transparent", hover_color=Palette.PANEL_3,
                text_color=Palette.TEXT_MUTED if muted else Palette.TEXT,
                font=ctk.CTkFont(size=12 if not muted else 11),
                command=cmd if cmd else (lambda v=view: self.show_view(v)),
            )
            btn.pack(fill="x", padx=6, pady=1)
            if view and cmd is None:
                self._sidebar_buttons[view] = btn
            return btn

        section("Home")
        nav_btn("Dashboard", "dashboard")
        nav_btn("Survivors", "survivors")
        nav_btn("Search", "search")

        section("Categories")
        if "Logbook" in self.db:
            nav_btn("Logbook", "logbook")   # single entry: Monsters, Environments and Drones
        for cat in self.db:
            if cat == "Logbook" or cat.endswith(PICK_SUFFIX):
                continue  # the logbook is handled by "Unlock All" and "Sync Logbook"
            nav_btn(cat, f"cat::{cat}")

        section("Tools")
        nav_btn("Backups", "backups")
        nav_btn("Inspect", "inspect")
        nav_btn("Merge profile", "merge")

        section("Quick actions")
        nav_btn("Unlock All", "", cmd=lambda: run_unlock_all(self))
        nav_btn("Unlock by DLC", "", cmd=lambda: run_unlock_dlc(self))
        reset_btn = nav_btn("Reset (lock everything)", "", cmd=lambda: run_reset_all(self))
        reset_btn.configure(text_color=Palette.RED)
        nav_btn("Sync Logbook", "", cmd=lambda: run_sync_logbook(self))
        nav_btn("Lunar coins", "", muted=True, cmd=lambda: CoinsDialog(self))
        nav_btn("Paste IDs", "", muted=True, cmd=lambda: PasteIDsDialog(self))
        nav_btn("Diagnostics", "", muted=True, cmd=lambda: run_diagnose(self))
        nav_btn("Report: have / missing", "", muted=True, cmd=lambda: run_status(self))
        nav_btn("Export enriched database", "", muted=True, cmd=lambda: run_export_db(self))

        # ---- fixed bottom -------------------------------------------------
        bottom = ctk.CTkFrame(sb, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="ew", padx=12, pady=12)
        bottom.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            bottom, text="Save (Ctrl+S)", height=36, corner_radius=8,
            fg_color=Palette.ACCENT, hover_color=Palette.ACCENT_HOV,
            text_color="#0f1115", font=ctk.CTkFont(size=12, weight="bold"),
            command=self.save_profile,
        ).grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            bottom, text="Exit", height=30, corner_radius=8,
            fg_color="transparent", hover_color=Palette.RED_DIM,
            text_color=Palette.TEXT_MUTED, font=ctk.CTkFont(size=11),
            command=self._on_close,
        ).grid(row=1, column=0, sticky="ew", pady=(6, 0))

        self.bind_all("<Control-s>", lambda e: self.save_profile())

    # ------------------------------------------------------------------
    def _toggle_sidebar(self) -> None:
        if self._sidebar is None:
            return
        if self._sidebar_visible:
            self._sidebar.grid_remove()
            self._sidebar_visible = False
        else:
            self._sidebar.grid()
            self._sidebar_visible = True

    # ------------------------------------------------------------------
    # Main area
    # ------------------------------------------------------------------
    def _build_main(self) -> None:
        main = ctk.CTkFrame(self, fg_color=Palette.BG, corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        # ---- header -----------------------------------------------------
        header = ctk.CTkFrame(main, fg_color=Palette.BG, height=64, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 0))
        header.grid_columnconfigure(1, weight=1)

        # toggle sidebar (hamburger)
        self._sidebar_toggle = ctk.CTkButton(
            header, text="☰", width=36, height=36, corner_radius=8,
            fg_color=Palette.PANEL, hover_color=Palette.PANEL_3,
            text_color=Palette.TEXT, font=ctk.CTkFont(size=16),
            command=self._toggle_sidebar,
        )
        self._sidebar_toggle.grid(row=0, column=0, sticky="w", padx=(0, 12))

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.grid(row=0, column=1, sticky="w")

        self.view_title = ctk.CTkLabel(left, text="", anchor="w",
                                       text_color=Palette.TEXT,
                                       font=ctk.CTkFont(size=20, weight="bold"))
        self.view_title.pack(anchor="w")

        self.view_sub = ctk.CTkLabel(left, text="", anchor="w",
                                     text_color=Palette.TEXT_MUTED,
                                     font=ctk.CTkFont(size=11))
        self.view_sub.pack(anchor="w")

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.grid(row=0, column=2, sticky="e")

        self.dirty_dot = ctk.CTkLabel(right, text="", text_color=Palette.YELLOW,
                                      font=ctk.CTkFont(size=11, weight="bold"))
        self.dirty_dot.pack(side="left", padx=(0, 12))

        ctk.CTkButton(right, text="Save", width=100, height=34, corner_radius=8,
                      fg_color=Palette.ACCENT, hover_color=Palette.ACCENT_HOV,
                      text_color="#0f1115", font=ctk.CTkFont(size=12, weight="bold"),
                      command=self.save_profile).pack(side="left")

        # ---- content ----------------------------------------------------
        self.content = ctk.CTkFrame(main, fg_color=Palette.BG, corner_radius=0)
        self.content.grid(row=1, column=0, sticky="nsew", padx=0, pady=(6, 0))
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self._content_host = self.content

    # ------------------------------------------------------------------
    # View routing
    # ------------------------------------------------------------------
    def show_view(self, name: str) -> None:
        for key, btn in self._sidebar_buttons.items():
            if key == name:
                btn.configure(fg_color=Palette.PANEL_2, text_color=Palette.TEXT)
            else:
                btn.configure(fg_color="transparent", text_color=Palette.TEXT)

        if self._current_view is not None:
            self._current_view.on_hide()
            self._current_view.grid_forget()

        view = self._views.get(name)
        if view is None:
            view = self._create_view(name)
            self._views[name] = view

        view.grid(row=0, column=0, sticky="nsew")

        self._current_view = view
        view.on_show()
        self._refresh_header()

    def _create_view(self, name: str) -> BaseView:
        if name == "dashboard":
            return DashboardView(self._content_host, self)
        if name == "survivors":
            return SurvivorsView(self._content_host, self)
        if name == "search":
            return SearchView(self._content_host, self)
        if name == "backups":
            return BackupsView(self._content_host, self)
        if name == "inspect":
            return InspectView(self._content_host, self)
        if name == "merge":
            return MergeView(self._content_host, self)
        if name == "logbook":
            return CategoryView(self._content_host, self, "Logbook",
                                items=logbook_entries(self.db), title="Logbook")
        if name.startswith("cat::"):
            category = name.split("::", 1)[1]
            return CategoryView(self._content_host, self, category)
        raise ValueError(f"Unknown view: {name}")

    def _reset_views(self) -> None:
        for v in self._views.values():
            v.destroy()
        self._views.clear()
        self._current_view = None

    # ------------------------------------------------------------------
    def _refresh_header(self) -> None:
        p = self.profile
        title = "Dashboard"
        sub = f"{p.name or p.path.name} · {p.path}"
        if self._current_view is not None:
            title = getattr(self._current_view, "title", title)

        self.view_title.configure(text=title)
        self.view_sub.configure(text=sub)

        if p.dirty:
            extra = f" · {p.stats_changed} stat changes" if p.stats_changed else ""
            if p.coins != p._coin_baseline:
                extra += " · coins changed"
            self.dirty_dot.configure(
                text=f"  ● {p.added} additions · {p.removed} removals{extra}",
                text_color=Palette.YELLOW,
            )
        else:
            self.dirty_dot.configure(text="", text_color=Palette.TEXT_MUTED)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def mark_dirty(self) -> None:
        self._refresh_header()
        if isinstance(self._current_view, DashboardView):
            self._current_view.refresh_stats()

    def toast(self, message: str, kind: str = "info") -> None:
        color = {
            "info": Palette.BLUE, "ok": Palette.GREEN,
            "warn": Palette.YELLOW, "err": Palette.RED,
        }.get(kind, Palette.BLUE)

        if self._toast is not None:
            self._toast.destroy()

        t = ctk.CTkLabel(
            self, text=f"  {message}  ", fg_color=color, text_color="#0f1115",
            corner_radius=10, font=ctk.CTkFont(size=12, weight="bold"),
        )
        t.place(relx=0.5, rely=0.965, anchor="s")
        self._toast = t
        self.after(3200, lambda: (t.destroy(), setattr(self, "_toast", None))
                   if self._toast is t else None)

    def confirm(self, message: str) -> bool:
        from tkinter import messagebox
        return messagebox.askyesno(APP_NAME, message, parent=self)

    # ------------------------------------------------------------------
    def save_profile(self) -> None:
        p = self.profile
        if not p.dirty:
            self.toast("No changes to save.", "info")
            return

        if self.dry_run:
            p.save(dry_run=True)
            self.toast("Dry run: nothing was written to disk.", "info")
            return

        if game_running():
            self.toast("Risk of Rain 2 is running! Close the game before saving.", "warn")
            if not self.confirm(
                "The game is running and will overwrite the profile when it closes.\n"
                "Save anyway?"
            ):
                return

        try:
            backup = p.save()
        except Exception as exc:
            self.toast(f"Failed to save: {exc}", "err")
            return

        self.toast(f"Saved successfully. Backup: {backup.name}", "ok")
        self.mark_dirty()
        if self._current_view is not None:
            self._current_view.on_show()

    def _on_close(self) -> None:
        if self.profile.dirty:
            answer = self.confirm(
                "There are unsaved changes.\n"
                "Save before exiting?"
            )
            if answer:
                self.save_profile()
                if self.profile.dirty:
                    return
        self.destroy()


# =========================================================================
# Entry point
# =========================================================================
def _merge_profile_into_db(db: Database, profile: Profile) -> Database:
    """Add to the DB everything the profile has that the database does not know about."""
    enriched: Database = {cat: list(items) for cat, items in db.items()}

    # Index of everything the database already knows
    known_unlocks = {
        c.lower()
        for cat, items in enriched.items()
        if not cat.endswith(ACH_SUFFIX)
        for c, _ in items
    }

    # 1) Profile achievements missing from the database
    ach_cat = next((c for c in enriched if c.endswith(ACH_SUFFIX)), None)
    if ach_cat is not None:
        known_a = {c.lower() for c, _ in enriched[ach_cat]}
        for ach in sorted(profile.achievements):
            if ach.lower() not in known_a:
                enriched[ach_cat].append((ach, label_of(ach)))
                known_a.add(ach.lower())

    # 2) Profile unlocks missing from the database, grouped by prefix
    by_prefix: dict[str, list[str]] = {}
    for code in sorted(profile.unlocks):
        if code.lower() in known_unlocks:
            continue
        prefix = code.split(".")[0] if "." in code else "other"
        by_prefix.setdefault(prefix, []).append(code)

    for prefix, codes in by_prefix.items():
        cat_name = f"Discovered: {prefix}"
        # if it already exists, just append
        if cat_name in enriched:
            existing = {c.lower() for c, _ in enriched[cat_name]}
            for c in codes:
                if c.lower() not in existing:
                    enriched[cat_name].append((c, label_of(c)))
        else:
            enriched[cat_name] = [(c, label_of(c)) for c in codes]

    return enriched


def run(profile_path: str | None = None, db_path: str | None = None,
        dry_run: bool = False) -> int:
    db = load_database(db_path)
    path = _resolve_profile(profile_path)
    if path is None:
        return 1
    try:
        profile = Profile(path)
    except Exception as exc:
        print(f"Could not read the profile: {exc}", file=sys.stderr)
        return 1

    app = App(profile, db, dry_run=dry_run)
    app.mainloop()
    return 0
