#!/usr/bin/env python3
"""Entry point for the RoR2 Profile Manager GUI."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RoR2 Profile Manager (GUI)")
    parser.add_argument("--profile", help="Direct path to the profile .xml file")
    parser.add_argument("--db", help="JSON file with the database")
    parser.add_argument("--dry-run", action="store_true", help="Do not write anything to disk")
    parser.add_argument("--export-catalog", nargs="?", const="", metavar="FILE",
                        help="Export the catalog of all IDs (CSV) and exit, without opening the GUI")
    args = parser.parse_args(argv)
    if args.export_catalog is not None:
        from ror2pm.catalog import export_catalog  # does not need the GUI
        print(f"Catalog saved to: {export_catalog(args.export_catalog or None)}")
        return 0
    from ror2pm.app import run
    return run(profile_path=args.profile, db_path=args.db, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())