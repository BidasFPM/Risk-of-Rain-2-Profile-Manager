"""ID identification: given a code, returns name, group, tier, DLC and where the name came from.

Name sources (`source` field):
  wiki      - official R2Wiki (names_data.py): items, equipment and environments
  manual    - names.py (hand-written): monsters, drones, artifacts, survivors
  base      - label already in the project (SURVIVOR_DATA: survivors' skills/skins/achievements)
  internal  - item that exists in the game but has no visible name (internal ID); name derived from the code
  derived   - name obtained from the code itself (split CamelCase); may not match the game
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace

from . import names as N
from .names_data import EQUIP_INFO, ITEM_INFO, STAGE_INFO


@dataclass(frozen=True)
class Identity:
    code: str
    kind: str          # readable type: Item, Equipment, Monster, Environment, Skill...
    name: str
    group: str = ""    # sub-group: item tier, owning survivor, statue environment...
    tier: str = ""     # in-game tier (White, Green...) - items/equipment only
    dlc: str = "Base"
    source: str = "derived"

    @property
    def label(self) -> str:
        """Short text shown in the application list."""
        if self.kind == "Item":
            return f"{self.name} · {self.tier}" if self.tier else self.name
        if self.kind == "Equipment":
            return f"{self.name} · Equipment" + (f" ({self.tier})" if self.tier else "")
        return self.name


_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def humanize(raw: str) -> str:
    """'CompleteTeleporterWithoutInjury' -> 'Complete Teleporter Without Injury'."""
    raw = raw.removesuffix(".0")
    return _CAMEL.sub(" ", raw).replace("_", " ").strip() or raw


def _owner(raw: str) -> str:
    return N.SURVIVOR_NAMES.get(raw, humanize(raw))


def _dlc(value: str) -> str:
    return N.DLC_SHORT.get(value, value or "Base")


def _item(code: str) -> Identity:
    key = code.split(".", 1)[1]
    name, tier, dlc = ITEM_INFO.get(key, ("", "", ""))
    return Identity(code, "Item", name or humanize(key), group=N.TIER_LABELS.get(tier, tier),
                    tier=N.TIER_LABELS.get(tier, tier), dlc=_dlc(dlc),
                    source="wiki" if name else ("internal" if key in ITEM_INFO else "derived"))


def _equipment(code: str) -> Identity:
    key = code.split(".", 1)[1]
    name, tier, dlc = EQUIP_INFO.get(key, ("", "", ""))
    lunar = "Lunar" if tier == "Lunar" else ""
    return Identity(code, "Equipment", name or humanize(key), group="Equipment", tier=lunar,
                    dlc=_dlc(dlc), source="wiki" if name else "derived")


def _stage(code: str, kind: str = "Environment") -> Identity:
    base = code.rsplit(".", 1)[1]
    title, _sub, dlc = STAGE_INFO.get(base, ("", "", ""))
    return Identity(code, kind, title or humanize(base).title(), dlc=_dlc(dlc), source="wiki" if title else "derived")


def identify(code: str, survivor_labels: dict[str, str] | None = None) -> Identity:
    """Identify any known game ID. `survivor_labels` = labels from SURVIVOR_DATA.

    Items, equipment and environments carry their DLC from the R2Wiki data; everything that
    belongs to a DLC survivor / monster / artifact gets its DLC filled in here.
    """
    who = _identify(code, survivor_labels)
    if who.dlc != "Base":
        return who
    dlc = ""
    if who.kind in _SURVIVOR_KINDS:
        dlc = N.SURVIVOR_DLC.get(who.group, "")
    elif who.kind == "Monster":
        dlc = N.MONSTER_DLC.get(code.partition(".")[2].removesuffix(".0"), "")
    elif who.kind == "Artifact":
        dlc = N.ARTIFACT_DLC.get(code.partition(".")[2], "")
    return replace(who, dlc=dlc) if dlc else who


_SURVIVOR_KINDS = {"Survivor", "Survivor (logbook)", "Skill", "Skin", "Eclipse", "Achievement"}


def _identify(code: str, survivor_labels: dict[str, str] | None = None) -> Identity:
    survivor_labels = survivor_labels or {}
    head, _, rest = code.partition(".")

    if head == "ItemIndex":
        return _item(code)
    if head == "EquipmentIndex":
        return _equipment(code)
    if head == "DroneIndex":
        key = rest
        return Identity(code, "Drone", N.DRONE_NAMES.get(key, humanize(key)), source="manual" if key in N.DRONE_NAMES else "derived")
    if head == "DroneLog":
        return Identity(code, "Drone", humanize(rest) + " (logbook)")
    if head == "SurvivorLog":
        return Identity(code, "Survivor (logbook)", _owner(rest), group=_owner(rest),
                        source="manual" if rest in N.SURVIVOR_NAMES else "derived")
    if head == "Logs" and rest.startswith("Stages."):
        return _stage(code)
    if head in ("Logs", "Log"):
        key = rest.removesuffix(".0")
        if key in N.MONSTER_NAMES:
            return Identity(code, "Monster", N.MONSTER_NAMES[key], source="manual")
        return Identity(code, "Monster", humanize(key.removesuffix("Body")))
    if head == "Characters":
        return Identity(code, "Survivor", _owner(rest), group=_owner(rest),
                        source="manual" if rest in N.SURVIVOR_NAMES else "derived")
    if head in ("Skills", "Skins"):
        owner, _, key = rest.partition(".")
        who = _owner(owner)
        if code in survivor_labels:
            name = f"Skin {survivor_labels[code]}" if head == "Skins" else survivor_labels[code]
            src = "base"
        elif head == "Skins" and key in N.SKIN_NAMES:
            name, src = f"Skin {N.SKIN_NAMES[key]}", "manual"
        else:
            name, src = humanize(key), "derived"
        return Identity(code, "Skill" if head == "Skills" else "Skin", f"{who} · {name}", group=who, source=src)
    if head == "Artifacts":
        return Identity(code, "Artifact", N.ARTIFACT_NAMES.get(rest, humanize(rest)),
                        source="manual" if rest in N.ARTIFACT_NAMES else "derived")
    if head == "Eclipse":
        owner, _, level = rest.partition(".")
        who = _owner(owner)
        return Identity(code, "Eclipse", f"{who} · Eclipse {level}", group=who, source="manual" if owner in N.SURVIVOR_NAMES else "derived")
    if head == "NewtStatue":
        base, _, idx = rest.rpartition(".")
        title = STAGE_INFO.get(base, ("",))[0] or humanize(base)
        return Identity(code, "Newt Statue", f"{title} · statue {idx}", group=title,
                        source="wiki" if base in STAGE_INFO else "derived")
    if head == "Shop":
        _, _, idx = rest.rpartition(".")
        return Identity(code, "Lunar Shop", f"Lunar Shop · bonus {idx}")
    if head == "LunarCoin":
        return Identity(code, "Lunar Coin", "Lunar Coin")
    if head == "ArtifactIndex":
        return Identity(code, "Artifact", N.ARTIFACT_NAMES.get(rest, humanize(rest)),
                        source="manual" if rest in N.ARTIFACT_NAMES else "derived")
    if head == "Items":        # item unlocks (Items.X) - linked to the achievement that unlocks them
        info = ITEM_INFO.get(rest) or EQUIP_INFO.get(rest)
        return Identity(code, "Item unlock", (info[0] if info and info[0] else humanize(rest)), source="wiki" if info and info[0] else "derived")

    return achievement(code, survivor_labels)


_ART_PREFIX = "ObtainArtifact"


def achievement(code: str, survivor_labels: dict[str, str] | None = None) -> Identity:
    """Achievements (IDs without a dot). Groups by survivor or artifact when the prefix allows."""
    if survivor_labels and code in survivor_labels:
        name = survivor_labels[code]
        return Identity(code, "Achievement", name, group=name.split(" · ")[0], source="base")
    if code.startswith(_ART_PREFIX):
        art = code[len(_ART_PREFIX):]
        shown = N.ARTIFACT_NAMES.get(art, humanize(art))
        return Identity(code, "Achievement", f"Obtain artifact {shown}", group="Artifacts",
                        source="manual" if art in N.ARTIFACT_NAMES else "derived")
    owners = sorted(N.SURVIVOR_NAMES, key=len, reverse=True)
    for key in owners:
        if code.startswith(key) and len(code) > len(key) and code[len(key)].isupper():
            who = _owner(key)
            rest = humanize(code[len(key):])
            return Identity(code, "Achievement", f"{who} · {rest}", group=who)
    return Identity(code, "Achievement", humanize(code), group="General")


def label_for(code: str, survivor_labels: dict[str, str] | None = None) -> str:
    return identify(code, survivor_labels).label


def tier_sort_key(code: str) -> tuple[int, str]:
    """Sort items by tier (white, green, red, boss, lunar, void...) and then by name."""
    key = code.split(".", 1)[-1]
    name, tier, _ = ITEM_INFO.get(key, ("", "No Tier", ""))
    return (N.TIER_ORDER.get(tier, 9), (name or humanize(key)).lower())
