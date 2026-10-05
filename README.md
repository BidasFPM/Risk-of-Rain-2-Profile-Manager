# RoR2 Profile Manager — v2.14

GUI application (customtkinter) to manage a Risk of Rain 2 profile: achievements, unlocks,
logbook, items, skins, artifacts, Eclipse, lunar coins and backups.
It always makes a backup before saving.

## What's new in v2.14

- **Reset (lock everything)** — new button in the sidebar under *Quick actions*. It locks
  everything again (unlocks, achievements and logbook) so you can unlock it all afresh.
  Nothing is written to disk until you press **Save** (a backup is made first), and
  **Unlock All** brings everything back. Lunar coins and real game statistics are not touched.
- The whole program is now in English.

## DLC tools

- **Unlock by DLC** (sidebar, *Quick actions*): unlocks everything from one pack (Base, Survivors of the Void,
  Seekers of the Storm, Alloyed Collective) in the profile. This edits progress only; playing DLC content
  in-game still requires owning the DLC.
- **DLC filter** in every category list; "Enable all" respects it.
- **Progress by DLC** on the Dashboard.

## Usage

```
python -m pip install -r requirements.txt
python main.py                        # detects the Steam profiles automatically
python main.py --profile "C:\path\profile.xml"
python main.py --db ror2_database.json
python main.py --dry-run              # writes nothing to disk
python main.py --export-catalog       # writes ror2_ids_catalog.csv with ALL identified IDs
```

Build the .exe (Windows):

```
python build.py            # single file, no console
python build.py --debug    # with console (see errors)
python build.py --onedir   # folder, faster startup
python build.py --clean    # clean build/ and dist/ first
```

## Project structure

```
ROR2COM_v2_14/
├── main.py                 Entry point (command-line arguments)
├── build.py                Builds the executable with PyInstaller
├── requirements.txt        Dependencies
├── README.md               This file
└── ror2pm/                 Main package
    ├── __init__.py         Exposes APP_NAME and VERSION
    ├── core.py             Logic without UI (see index below)
    ├── reference.py        ID lists extracted from a fully unlocked profile
    ├── identify.py         Identifies any ID: type, name, group, tier, DLC and name source
    ├── names.py            Hand-written names (monsters, drones, artifacts, survivors)
    ├── names_data.py       Names/tiers/DLC of items, equipment and environments (generated from the R2Wiki)
    ├── catalog.py          Catalog of all IDs (CSV) — python main.py --export-catalog
    ├── theme.py            Color palette and fonts (dark theme)
    ├── app.py              Main window, sidebar, navigation and save flow
    ├── assets/             icon.ico and icon.png
    └── views/              UI screens
        ├── base.py         Shared components (BaseView, CheckRow, ProgressBar…)
        ├── dashboard.py    Summary and progress per category
        ├── category.py     Generic checklist (one per category)
        ├── survivors.py    Survivors: skills, skins and achievements
        ├── search.py       Global search
        └── tools.py        Coins, backups, inspect, merge, reports, paste IDs, export DB, Unlock All / Reset
```

## `core.py` index

| # | Section | Contents |
|---|---------|----------|
| 1 | Identification, constants and paths | `APP_NAME`, `VERSION`, `BACKUP_ROOT`, icons |
| 2 | Embedded data | Survivors, skills, skins, artifacts, logbook, items, achievements |
| 3 | Survivor data | `ACH_LINKS`, `SURVIVOR_DATA` |
| 4 | External files and master database | `items_ids.json`, `logbook_ids.json`, `achievements_ids.json`, `MASTER_DB` |
| 5 | Utilities | IDs, Steam/profile detection, backups |
| 6 | Database | `load_database` |
| 7 | Profile | `Profile` class (XML read/write) |
| 8 | Unlock All + Reset + Sync Logbook | bulk operations (`unlock_all`, `reset_all`, `sync_logbook`) |
| 9 | Survivors | detailed entries |
| 10 | Reports | diagnostics and profile status |

## Files created at runtime (next to the program)

- `backups/` — profile backups (keeps the latest 15)
- `ror2_database.json` — exported database
- `diagnostics_*.txt` and `status_*.txt` reports
- `items_ids.json`, `logbook_ids.json`, `achievements_ids.json` — optional lists that replace the embedded ones

## How IDs are identified

Each ID has a **code** (what is stored in the profile, never changed) and an **identification**
(`ror2pm/identify.py`): type, readable name, group, tier, DLC and where the name came from.

| Type | Example ID | How it appears in the list |
|------|------------|----------------------------|
| Item | `ItemIndex.AlienHead` | Alien Head · Red |
| Equipment | `EquipmentIndex.BFG` | Preon Accumulator · Equipment |
| Monster | `Logs.BrotherBody.0` | Mithrix |
| Environment | `Logs.Stages.blackbeach` | Distant Roost |
| Survivor | `Characters.Croco` | Acrid |
| Skill / Skin | `Skills.Commando.SlideJet` | Commando · Tactical Slide |
| Eclipse | `Eclipse.Mage.4` | Artificer · Eclipse 4 |
| Newt Statue | `NewtStatue.blackbeach.0` | Distant Roost · statue 0 |
| Achievement | `ObtainArtifactBomb` | Obtain artifact Spite |

Name source (the "Name source" column in the catalog): **R2Wiki** (official), **manual**, **project
label**, **internal ID** (exists in the engine without an in-game name) or **derived from the code**
(to confirm). Items are sorted by tier. To update the item/equipment/environment list, regenerate
`names_data.py` from the R2Wiki (the "Items and Equipments Data" page).
