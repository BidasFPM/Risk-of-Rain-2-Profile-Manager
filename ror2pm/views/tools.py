"""Tools: coins editor, backups, inspect, merge, reports, paste IDs, export DB."""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

import customtkinter as ctk

from ..core import (
    COIN_MAX,
    DLC_LABELS,
    dlc_progress,
    DEFAULT_DB_FILE,
    Profile,
    diagnose_report,
    discover_profiles,
    game_running,
    known_codes,
    label_of,
    list_backups,
    logbook_sync_plan,
    make_backup,
    parse_ids,
    profile_fingerprint,
    profile_summary,
    status_report,
    sync_logbook,
    reset_all,
    unlock_all,
)
from ..theme import Palette
from .base import BaseView, SectionTitle


# =========================================================================
# Coins
# =========================================================================
class CoinsDialog(ctk.CTkToplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Lunar coins")
        self.geometry("420x230")
        self.configure(fg_color=Palette.BG)
        self.transient(app)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)

        current = app.profile.coins
        ctk.CTkLabel(self, text="Current balance", anchor="w",
                     text_color=Palette.TEXT_MUTED, font=ctk.CTkFont(size=11)).grid(
            row=0, column=0, sticky="w", padx=22, pady=(22, 0))
        ctk.CTkLabel(self, text=str(current) if current is not None else "not found",
                     anchor="w", text_color=Palette.TEXT,
                     font=ctk.CTkFont(size=26, weight="bold")).grid(
            row=1, column=0, sticky="w", padx=22)

        ctk.CTkLabel(self, text="New balance", anchor="w",
                     text_color=Palette.TEXT_MUTED, font=ctk.CTkFont(size=11)).grid(
            row=2, column=0, sticky="w", padx=22, pady=(14, 2))

        self.entry = ctk.CTkEntry(self, fg_color=Palette.PANEL, border_color=Palette.BORDER,
                                  text_color=Palette.TEXT, height=34, corner_radius=8,
                                  placeholder_text=f"0 – {COIN_MAX}")
        self.entry.grid(row=3, column=0, sticky="ew", padx=22)
        self.entry.focus_set()

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=4, column=0, sticky="ew", padx=22, pady=(18, 22))
        btns.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(btns, text="Cancel", fg_color=Palette.PANEL,
                      hover_color=Palette.PANEL_3, text_color=Palette.TEXT,
                      command=self.destroy).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ctk.CTkButton(btns, text="Apply", fg_color=Palette.ACCENT,
                      hover_color=Palette.ACCENT_HOV, text_color="#0f1115",
                      command=self._apply).grid(row=0, column=1, sticky="ew", padx=(5, 0))

    def _apply(self) -> None:
        raw = self.entry.get().strip()
        if not raw.isdigit() or int(raw) > COIN_MAX:
            self.app.toast(f"Invalid value (0 – {COIN_MAX}).", "err")
            return
        try:
            self.app.profile.coins = int(raw)
        except RuntimeError as exc:
            self.app.toast(str(exc), "err")
            self.destroy()
            return
        self.app.mark_dirty()
        self.app.toast(f"Coins updated to {raw}.", "ok")
        self.destroy()


# =========================================================================
# Paste IDs
# =========================================================================
class PasteIDsDialog(ctk.CTkToplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Paste unlock IDs")
        self.geometry("640x460")
        self.configure(fg_color=Palette.BG)
        self.transient(app)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        ctk.CTkLabel(self, text="Paste unlock IDs", anchor="w",
                     text_color=Palette.TEXT, font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=22, pady=(20, 2))
        ctk.CTkLabel(self,
                     text="Accepts <unlock>ID</unlock>, free text, or '-ID' to remove. Separators: space, comma, ';'.",
                     anchor="w", text_color=Palette.TEXT_MUTED,
                     font=ctk.CTkFont(size=11)).grid(row=1, column=0, sticky="w", padx=22)

        self.text = ctk.CTkTextbox(self, fg_color=Palette.PANEL, border_color=Palette.BORDER,
                                   text_color=Palette.TEXT, corner_radius=8,
                                   font=ctk.CTkFont(family="Consolas", size=12))
        self.text.grid(row=2, column=0, sticky="nsew", padx=22, pady=(10, 6))
        self.text.focus_set()

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=3, column=0, sticky="ew", padx=22, pady=(6, 20))
        btns.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(btns, text="Cancel", fg_color=Palette.PANEL,
                      hover_color=Palette.PANEL_3, text_color=Palette.TEXT,
                      command=self.destroy).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ctk.CTkButton(btns, text="Apply", fg_color=Palette.ACCENT,
                      hover_color=Palette.ACCENT_HOV, text_color="#0f1115",
                      command=self._apply).grid(row=0, column=1, sticky="ew", padx=(5, 0))

    def _apply(self) -> None:
        add, remove, invalid = parse_ids(self.text.get("1.0", "end"))
        new = [c for c in dict.fromkeys(add) if not self.app.profile.has(c)]
        for code in new:
            self.app.profile.add(code)
        gone = [c for c in remove if self.app.profile.has(c)]
        for code in gone:
            self.app.profile.remove(code)
        self.app.mark_dirty()
        self.app.toast(f"{len(new)} added · {len(gone)} removed."
                       + (f"  Ignored: {' '.join(invalid)}" if invalid else ""),
                       "warn" if invalid else "ok")
        self.destroy()


# =========================================================================
# Backups
# =========================================================================
class BackupsView(BaseView):
    title = "Backups"

    def build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        SectionTitle(self, "Local backups for this profile").grid(
            row=0, column=0, sticky="w", padx=28, pady=(22, 6))

        self.list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.list.grid_columnconfigure(0, weight=1)

    def _rebuild(self) -> None:
        for w in self.list.winfo_children():
            w.destroy()

        backups = list_backups(self.profile.path)
        if not backups:
            ctk.CTkLabel(self.list, text="No backups for this profile.",
                         text_color=Palette.TEXT_MUTED).grid(row=0, column=0, pady=20)
            return

        for i, b in enumerate(backups):
            try:
                stamp = datetime.strptime(b.name.split(".")[0], "%Y%m%d-%H%M%S")
            except ValueError:
                stamp = datetime.fromtimestamp(b.stat().st_mtime)

            card = ctk.CTkFrame(self.list, fg_color=Palette.PANEL, corner_radius=10)
            card.grid(row=i, column=0, sticky="ew", padx=6, pady=4)
            card.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(card, text=stamp.strftime("%Y-%m-%d  %H:%M:%S"), anchor="w",
                         text_color=Palette.TEXT,
                         font=ctk.CTkFont(size=12, weight="bold")).grid(
                row=0, column=0, sticky="w", padx=16, pady=(10, 0))
            ctk.CTkLabel(card, text=f"{b.stat().st_size / 1024:.0f} KB · {b.name}",
                         anchor="w", text_color=Palette.TEXT_MUTED,
                         font=ctk.CTkFont(size=10)).grid(row=1, column=0, sticky="w",
                                                          padx=16, pady=(0, 10))

            ctk.CTkButton(card, text="Restore", width=100, height=30,
                          fg_color=Palette.PANEL_3, hover_color=Palette.ACCENT,
                          text_color=Palette.TEXT,
                          command=lambda p=b: self._restore(p)).grid(
                row=0, column=1, rowspan=2, padx=16)

    def _restore(self, backup: Path) -> None:
        if game_running():
            self.app.toast("Close Risk of Rain 2 before restoring.", "warn")
            return
        if not self.app.confirm(f"Restore '{backup.name}'?\nUnsaved changes will be lost."):
            return
        try:
            make_backup(self.profile.path)
            shutil.copy2(backup, self.profile.path)
        except OSError as exc:
            self.app.toast(f"Failed to restore: {exc}", "err")
            return
        try:
            self.app.profile = Profile(self.profile.path)
        except Exception as exc:  # pragma: no cover
            self.app.toast(f"Corrupted backup: {exc}", "err")
            return
        self.app.mark_dirty()
        self.app.toast("Backup restored.", "ok")
        self._rebuild()

    def on_show(self) -> None:
        self._rebuild()


# =========================================================================
# Inspect
# =========================================================================
class InspectView(BaseView):
    title = "Inspect"

    def build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        SectionTitle(self, "XML file state").grid(
            row=0, column=0, sticky="w", padx=28, pady=(22, 6))

        self.body = ctk.CTkTextbox(
            self, fg_color=Palette.PANEL, border_color=Palette.BORDER,
            text_color=Palette.TEXT, corner_radius=10,
            font=ctk.CTkFont(family="Consolas", size=12),
        )
        self.body.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 20))

    def on_show(self) -> None:
        p = self.profile
        lines = [
            f"File: {p.path}",
            f"Root: <{p.root.tag}>",
            "",
            f"Coins: {p.coins}",
            f"Achievements: {len(p.achievements)}",
            f"Unlocks: {len(p.unlocks)}",
            "",
            "Unlock prefixes:",
        ]
        from collections import Counter
        groups = Counter(code.split(".")[0] for code in p.unlocks)
        for prefix, n in groups.most_common():
            lines.append(f"  {prefix:<16} {n}")
        lines += ["", "All unlocks:"]
        lines += [f"  {u}" for u in sorted(p.unlocks)]
        lines += ["", "All achievements:"]
        lines += [f"  {a}" for a in sorted(p.achievements)]

        self.body.configure(state="normal")
        self.body.delete("1.0", "end")
        self.body.insert("1.0", "\n".join(lines))
        self.body.configure(state="disabled")


# =========================================================================
# Merge from another profile
# =========================================================================
class MergeView(BaseView):
    title = "Merge from another profile"

    def build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        ctk.CTkLabel(
            self, text="Merge data from another profile",
            anchor="w", text_color=Palette.TEXT,
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=28, pady=(22, 4))

        ctk.CTkLabel(
            self,
            text="Useful with a fully unlocked profile: brings in real IDs for skins, skills, items, logbook…",
            anchor="w", text_color=Palette.TEXT_MUTED,
            font=ctk.CTkFont(size=11),
        ).grid(row=1, column=0, sticky="w", padx=28)

        self.list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list.grid(row=2, column=0, sticky="nsew", padx=18, pady=(12, 18))
        self.list.grid_columnconfigure(0, weight=1)

        self.empty = ctk.CTkLabel(self.list, text="", text_color=Palette.TEXT_MUTED)

    def _rebuild(self) -> None:
        for w in self.list.winfo_children():
            w.destroy()

        current = self.profile.path.resolve()
        candidates = [p for p in discover_profiles() if p.resolve() != current]
        if not candidates:
            ctk.CTkLabel(self.list,
                         text="No other Steam profiles were found to merge.",
                         text_color=Palette.TEXT_MUTED).grid(row=0, column=0, pady=30)
            return

        for i, p in enumerate(candidates):
            card = ctk.CTkFrame(self.list, fg_color=Palette.PANEL, corner_radius=10)
            card.grid(row=i, column=0, sticky="ew", padx=6, pady=4)
            card.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(card, text=profile_summary(p), anchor="w",
                         text_color=Palette.TEXT,
                         font=ctk.CTkFont(size=12, weight="bold")).grid(
                row=0, column=0, sticky="w", padx=16, pady=(12, 0))
            ctk.CTkLabel(card, text=profile_fingerprint(p), anchor="w",
                         text_color=Palette.TEXT_MUTED,
                         font=ctk.CTkFont(size=10)).grid(row=1, column=0, sticky="w",
                                                          padx=16, pady=(0, 12))

            btns = ctk.CTkFrame(card, fg_color="transparent")
            btns.grid(row=0, column=1, rowspan=2, padx=16)
            ctk.CTkButton(btns, text="Merge all", width=110, height=30,
                          fg_color=Palette.ACCENT, hover_color=Palette.ACCENT_HOV,
                          text_color="#0f1115",
                          command=lambda q=p: self._merge(q, "all")).pack(side="left", padx=2)
            ctk.CTkButton(btns, text="Unlocks", width=90, height=30,
                          fg_color=Palette.PANEL_3, hover_color=Palette.PANEL_2,
                          text_color=Palette.TEXT,
                          command=lambda q=p: self._merge(q, "unlocks")).pack(side="left", padx=2)
            ctk.CTkButton(btns, text="Achievements", width=110, height=30,
                          fg_color=Palette.PANEL_3, hover_color=Palette.PANEL_2,
                          text_color=Palette.TEXT,
                          command=lambda q=p: self._merge(q, "achievements")).pack(side="left", padx=2)

    def _merge(self, source: Path, mode: str) -> None:
        try:
            other = Profile(source)
        except Exception as exc:
            self.app.toast(f"Could not read the profile: {exc}", "err")
            return

        mine_u = {u.lower() for u in self.profile.unlocks}
        new_u = sorted(u for u in other.unlocks if u.lower() not in mine_u)
        new_a = [a for a in other.achievements if not self.profile.has(a, "achievement")]

        new_p = [k for k in other.pickups if not self.profile.has(k, "pickup")]

        if not new_u and not new_a and not new_p:
            self.app.toast("The current profile already contains everything the other one has.", "info")
            return

        if not self.app.confirm(
            f"Merge {len(new_u)} unlocks, {len(new_p)} logbook items/drones and {len(new_a)} achievements from:\n{source.name}?"
        ):
            return

        if mode in ("all", "unlocks"):
            for code in new_u:
                self.profile.add(code)
            for code in new_p:
                self.profile.add(code, "pickup")
        if mode in ("all", "achievements"):
            if self.profile._ach_node is None and new_a:
                self.app.toast("The profile has no <achievementsList>; achievements ignored.", "warn")
            else:
                for code in new_a:
                    self.profile.add(code, "achievement")

        self.app.mark_dirty()
        self.app.toast(f"Merge done ({len(new_u)} unlocks, {len(new_a)} achievements).", "ok")

    def on_show(self) -> None:
        self._rebuild()


# =========================================================================
# Reports / Export DB (quick actions)
# =========================================================================
def _reload_current_view(app) -> None:
    app.mark_dirty()
    if app._current_view is not None:
        app._current_view.on_show()


def run_unlock_all(app) -> None:
    """Single button: unlock everything (survivors, skills, skins, items, artifacts, Eclipse,
    Newt/shop, achievements and logbook)."""
    todo = unlock_all(app.profile, app.db, apply=False)
    total = sum(todo.values())
    if not total:
        app.toast("Everything is already unlocked.", "info")
        return
    if not app.confirm(
        f"Unlock All: unlock {total} entries "
        f"({todo['unlock']} unlocks, {todo['achievement']} achievements, {todo['logbook']} logbook)?"
    ):
        return
    unlock_all(app.profile, app.db)
    _reload_current_view(app)
    app.toast(f"Unlocked: {todo['unlock']} unlocks · {todo['achievement']} achievements · "
              f"{todo['logbook']} logbook.", "ok")


def run_unlock_dlc(app) -> None:
    """Unlock everything that belongs to one DLC (or the base game) in the profile."""
    DlcUnlockDialog(app)


class DlcUnlockDialog(ctk.CTkToplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Unlock by DLC")
        self.geometry("470x330")
        self.configure(fg_color=Palette.BG)
        self.transient(app)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)

        prog = dlc_progress(app.profile, app.db)
        self._choices = {f"{DLC_LABELS.get(k, k)} ({h}/{t})": k for k, (h, t) in prog.items()}

        ctk.CTkLabel(self, text="Unlock everything from one content pack", anchor="w",
                     text_color=Palette.TEXT, font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=22, pady=(22, 4))
        ctk.CTkLabel(
            self, anchor="w", justify="left", wraplength=420, text_color=Palette.TEXT_MUTED,
            font=ctk.CTkFont(size=11),
            text="Survivors, skills, skins, items, logbook and achievements of the chosen DLC are "
                 "marked as unlocked in the profile. Playing a DLC survivor or using DLC items in-game "
                 "still requires owning that DLC; this only edits your progress.",
        ).grid(row=1, column=0, sticky="w", padx=22)

        self.menu = ctk.CTkOptionMenu(
            self, values=list(self._choices), height=34, fg_color=Palette.PANEL,
            button_color=Palette.PANEL_2, button_hover_color=Palette.PANEL_3, text_color=Palette.TEXT)
        self.menu.grid(row=2, column=0, sticky="ew", padx=22, pady=(16, 0))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=3, column=0, sticky="ew", padx=22, pady=(22, 22))
        btns.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(btns, text="Cancel", fg_color=Palette.PANEL, hover_color=Palette.PANEL_3,
                      text_color=Palette.TEXT, command=self.destroy).grid(
            row=0, column=0, sticky="ew", padx=(0, 5))
        ctk.CTkButton(btns, text="Unlock", fg_color=Palette.ACCENT, hover_color=Palette.ACCENT_HOV,
                      text_color="#0f1115", command=self._apply).grid(
            row=0, column=1, sticky="ew", padx=(5, 0))

    def _apply(self) -> None:
        dlc = self._choices[self.menu.get()]
        todo = unlock_all(self.app.profile, self.app.db, apply=False, dlc=dlc)
        total = sum(todo.values())
        name = DLC_LABELS.get(dlc, dlc)
        if not total:
            self.app.toast(f"{name}: everything is already unlocked.", "info")
            self.destroy()
            return
        if not self.app.confirm(
            f"Unlock {total} entries from {name} "
            f"({todo['unlock']} unlocks, {todo['achievement']} achievements, {todo['logbook']} logbook)?"
        ):
            return
        unlock_all(self.app.profile, self.app.db, dlc=dlc)
        self.destroy()
        _reload_current_view(self.app)
        self.app.toast(f"{name}: {todo['unlock']} unlocks · {todo['achievement']} achievements · "
                       f"{todo['logbook']} logbook.", "ok")


def run_reset_all(app) -> None:
    """Reset: lock EVERYTHING again (unlocks, achievements and logbook) so it can be unlocked afresh.

    Nothing is written to disk until the user presses Save, and Save always makes a backup first.
    """
    todo = reset_all(app.profile, app.db, apply=False)
    total = sum(todo.values())
    if not total:
        app.toast("Everything is already locked.", "info")
        return
    if not app.confirm(
        f"RESET: lock EVERYTHING in this profile?\n\n"
        f"This removes {todo['unlock']} unlocks, {todo['achievement']} achievements and "
        f"{todo['logbook']} logbook entries.\n"
        "ALL game statistics (kills, deaths, gold, stages...) are set to 0, because\n"
        "challenges and logbook entries are driven by them.\n"
        "Lunar coins are not touched.\n\n"
        "Nothing is written until you press Save (a backup is made first), "
        "and you can unlock everything again with Unlock All."
    ):
        return
    reset_all(app.profile, app.db)
    _reload_current_view(app)
    app.toast(f"Reset: locked {todo['unlock']} unlocks · {todo['achievement']} achievements · "
              f"{todo['logbook']} logbook. Press Save to apply.", "warn")


def run_sync_logbook(app) -> None:
    """Align the logbook with what the profile really has unlocked."""
    add, remove = logbook_sync_plan(app.profile, app.db)
    if not add and not remove:
        app.toast("The logbook is already in sync with your unlocks.", "ok")
        return
    if not app.confirm(f"Sync Logbook: add {len(add)} and remove {len(remove)} entries "
                       "to reflect what you really have unlocked?"):
        return
    sync_logbook(app.profile, add, remove)
    _reload_current_view(app)
    app.toast(f"Logbook synced: +{len(add)} · -{len(remove)}.", "ok")


def run_diagnose(app) -> None:
    try:
        path = diagnose_report(app.profile)
    except Exception as exc:
        app.toast(f"Failed to generate diagnostics: {exc}", "err")
        return
    app.toast(f"Diagnostics saved: {path.name}", "ok")


def run_status(app) -> None:
    try:
        path = status_report(app.profile, app.db)
    except Exception as exc:
        app.toast(f"Failed to generate status report: {exc}", "err")
        return
    app.toast(f"Status report saved: {path.name}", "ok")


def run_export_db(app) -> None:
    db = app.db
    extra_u = sorted(u for u in app.profile.unlocks if u.lower() not in known_codes(db, "unlock"))
    extra_a = sorted(a for a in app.profile.achievements if a.lower() not in known_codes(db, "achievement"))
    if not extra_u and not extra_a:
        app.toast("The database already knows everything the profile has.", "info")
        return
    if not app.confirm(f"Export {len(extra_u)} discovered unlocks and {len(extra_a)} discovered achievements "
                       f"to {DEFAULT_DB_FILE.name}?"):
        return
    out: dict[str, list[list[str]]] = {cat: [[c, d] for c, d in items] for cat, items in db.items()}
    by_prefix: dict[str, list[str]] = {}
    for code in extra_u:
        by_prefix.setdefault(code.split(".")[0], []).append(code)
    for prefix, codes in sorted(by_prefix.items()):
        out[f"Discovered: {prefix}"] = [[c, label_of(c)] for c in codes]
    if extra_a:
        out["Discovered achievements [achievements]"] = [[a, label_of(a)] for a in extra_a]
    try:
        if DEFAULT_DB_FILE.exists():
            bak = DEFAULT_DB_FILE.with_name(f"{DEFAULT_DB_FILE.stem}.{datetime.now():%Y%m%d-%H%M%S}.bak")
            shutil.copy2(DEFAULT_DB_FILE, bak)
        DEFAULT_DB_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        app.toast(f"Failed to write: {exc}", "err")
        return
    app.toast(f"Database exported to {DEFAULT_DB_FILE.name}.", "ok")
