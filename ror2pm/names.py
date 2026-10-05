"""Hand-written readable names (monsters, drones, artifacts, survivors...).

Item, equipment and environment names come from names_data.py (R2Wiki).
Anything that is neither here nor in names_data.py is identified automatically
from the code itself (see identify.py) and marked as 'derived'.
"""
from __future__ import annotations

# Internal survivor code -> in-game name (used in skills, skins, Eclipse, achievements)
SURVIVOR_NAMES: dict[str, str] = {
    "Commando": "Commando", "Huntress": "Huntress", "Bandit": "Bandit", "Bandit2": "Bandit",
    "Toolbot": "MUL-T", "Engi": "Engineer", "Engineer": "Engineer", "Mage": "Artificer",
    "Merc": "Mercenary", "Mercenary": "Mercenary", "Treebot": "REX", "Loader": "Loader",
    "Croco": "Acrid", "Captain": "Captain", "Railgunner": "Railgunner", "RailGunner": "Railgunner",
    "VoidSurvivor": "Void Fiend", "Seeker": "Seeker", "FalseSon": "False Son", "Chef": "CHEF",
    "DroneTech": "Operator", "Drifter": "Drifter", "Heretic": "Heretic",
}

MONSTER_NAMES: dict[str, str] = {
    "BeetleBody": "Beetle", "BeetleGuardBody": "Beetle Guard", "BeetleQueenBody": "Beetle Queen",
    "BellBody": "Brass Contraption", "BisonBody": "Bighorn Bison", "BrotherBody": "Mithrix",
    "ClayBossBody": "Clay Dunestrider", "ClayBruiserBody": "Clay Templar",
    "ClayGrenadierBody": "Clay Apothecary", "ElectricWormBody": "Overloading Worm",
    "GolemBody": "Stone Golem", "GravekeeperBody": "Grovetender", "GreaterWispBody": "Greater Wisp",
    "HermitCrabBody": "Hermit Crab", "ImpBody": "Imp", "ImpBossBody": "Imp Overlord",
    "JellyfishBody": "Jellyfish", "LemurianBody": "Lemurian", "LemurianBruiserBody": "Elder Lemurian",
    "LunarGolem": "Lunar Chimera (Golem)", "LunarWisp": "Lunar Chimera (Wisp)",
    "LunarExploder": "Lunar Chimera (Exploder)", "MagmaWormBody": "Magma Worm",
    "MiniMushroom": "Mini Mushrum", "Nullifier": "Void Reaver", "Parent": "Parent",
    "RoboBallBossBody": "Solus Control Unit", "RoboBallMiniBody": "Solus Probe", "Scav": "Scavenger",
    "SuperRoboBallBossBody": "Alloy Worship Unit", "TitanBody": "Stone Titan", "TitanGoldBody": "Aurelionite",
    "VagrantBody": "Wandering Vagrant", "VultureBody": "Alloy Vulture", "WispBody": "Lesser Wisp",
    "GrandparentBody": "Grandparent", "FlyingVerminBody": "Blind Pest", "VerminBody": "Blind Vermin",
    "GupBody": "Gup", "VoidInfestorBody": "Void Infestor", "VoidJailerBody": "Void Jailer",
    "VoidBarnacleBody": "Void Barnacle", "MegaConstructBody": "Xi Construct",
    "MinorConstructBody": "Alpha Construct", "AcidLarva": "Larva", "VoidMegaCrab": "Void Devastator",
    "ScorchlingBody": "Scorchling", "HalcyoniteBody": "Halcyonite", "FalseSonBossBody": "False Son",
}

DRONE_NAMES: dict[str, str] = {
    "Drone1": "Gunner Drone", "Drone2": "Healing Drone", "EmergencyDrone": "Emergency Drone",
    "EquipmentDrone": "Equipment Drone", "FlameDrone": "Incinerator Drone", "MegaDrone": "TC-280 Prototype",
    "MissileDrone": "Missile Drone", "Turret1": "Gunner Turret", "BombardmentDrone": "Bombardment Drone",
    "CleanupDrone": "Cleanup Drone", "CopycatDrone": "Copycat Drone", "JailerDrone": "Jailer Drone",
    "JunkDrone": "Junk Drone", "RechargeDrone": "Recharge Drone",
}

ARTIFACT_NAMES: dict[str, str] = {
    "EliteOnly": "Honor", "Bomb": "Spite", "Command": "Command", "Enigma": "Enigma",
    "FriendlyFire": "Chaos", "Glass": "Glass", "MixEnemy": "Dissonance",
    "MonsterTeamGainsItems": "Evolution", "RandomSurvivorOnRespawn": "Metamorphosis",
    "Sacrifice": "Sacrifice", "ShadowClone": "Vengeance", "SingleMonsterType": "Kin",
    "Swarms": "Swarms", "TeamDeath": "Death", "WeakAssKnees": "Frailty", "WispOnDeath": "Soul",
    "Delusion": "Delusion", "Devotion": "Devotion", "Rebirth": "Rebirth", "Prestige": "Prestige",
}

# DLC of content that is not an item/equipment/environment (those come from names_data.py).
# Keys are the in-game names / internal codes used elsewhere in this file. Short DLC codes:
# SotV = Survivors of the Void, SotS = Seekers of the Storm, AC = Alloyed Collective.
SURVIVOR_DLC: dict[str, str] = {
    "Railgunner": "SotV", "Void Fiend": "SotV",
    "Seeker": "SotS", "False Son": "SotS", "CHEF": "SotS",
    "Drifter": "AC", "Operator": "AC",
}
MONSTER_DLC: dict[str, str] = {
    "VoidInfestorBody": "SotV", "VoidJailerBody": "SotV", "VoidBarnacleBody": "SotV",
    "VoidMegaCrab": "SotV", "Nullifier": "SotV", "MegaConstructBody": "SotV",
    "MinorConstructBody": "SotV", "AcidLarva": "SotV",
    "ScorchlingBody": "SotS", "HalcyoniteBody": "SotS", "FalseSonBossBody": "SotS",
}
ARTIFACT_DLC: dict[str, str] = {"Delusion": "SotV", "Devotion": "SotS"}

SKIN_NAMES: dict[str, str] = {"Alt1": "Mastery", "Alt2": "Grandmastery"}

# Tiers (R2Wiki) -> texto apresentado
TIER_LABELS: dict[str, str] = {
    "White": "White", "Green": "Green", "Red": "Red", "Boss": "Boss (yellow)", "Lunar": "Lunar",
    "Void White": "Void white", "Void Green": "Void green", "Void Red": "Void red",
    "Void Boss": "Void boss", "No Tier": "No tier", "Normal": "", "": "",
}
# Tier display order
TIER_ORDER: dict[str, int] = {
    "White": 0, "Green": 1, "Red": 2, "Boss": 3, "Lunar": 4,
    "Void White": 5, "Void Green": 6, "Void Red": 7, "Void Boss": 8, "No Tier": 9,
}
DLC_SHORT: dict[str, str] = {
    "No DLC": "Base", "": "Base", "Survivors of the Void": "SotV", "SOTV": "SotV",
    "Seekers of the Storm": "SotS", "SOTS": "SotS", "Alloyed Collective": "AC", "AC": "AC",
}
