"""ID catalog: lists ALL database IDs with type, name, group, tier, DLC and where they live in the profile.

Usage (without opening the GUI):
    python main.py --export-catalog            # writes ror2_ids_catalog.csv next to the program
    python main.py --export-catalog mine.csv
"""
from __future__ import annotations

import csv
from pathlib import Path

from .core import MASTER_DB, SCRIPT_DIR, SURVIVOR_LABELS, Database, _norm_kind, kind_of
from .identify import identify

DEFAULT_CATALOG_FILE = SCRIPT_DIR / "ror2_ids_catalog.csv"

COLUMNS = ["Category", "ID", "Type", "Name", "Group", "Tier", "DLC", "Stored in profile at", "Name source"]

_WHERE = {
    "achievement": "<achievementsList>",
    "unlock": "<unlock>",
    "pickup": "<discoveredPickups>",
    "statlog": "logbook statistic (stat)",
}
_SOURCE = {
    "wiki": "R2Wiki (official)",
    "manual": "in-game name (manual)",
    "base": "project label",
    "internal": "internal ID with no in-game name",
    "derived": "derived from the code (to confirm)",
}


def build_catalog(db: Database | None = None) -> list[list[str]]:
    """One row per (category, ID), ordered by category in database order."""
    db = db if db is not None else MASTER_DB
    rows: list[list[str]] = []
    for category, items in db.items():
        base_kind = kind_of(category)
        for code, _label in items:
            who = identify(code, SURVIVOR_LABELS)
            where = _WHERE[_norm_kind(code, base_kind)]
            rows.append([category, code, who.kind, who.label if who.kind not in ("Item", "Equipment") else who.name,
                         who.group, who.tier, who.dlc, where, _SOURCE.get(who.source, who.source)])
    return rows


def export_catalog(path: Path | str | None = None, db: Database | None = None) -> Path:
    """Write the catalog as CSV (UTF-8 with BOM and ';' separator, opens directly in Excel)."""
    out = Path(path) if path else DEFAULT_CATALOG_FILE
    with out.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow(COLUMNS)
        writer.writerows(build_catalog(db))
    return out
