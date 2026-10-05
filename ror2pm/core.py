"""
Core (no GUI) of the RoR2 Profile Manager.

Module index (in order):
  1. Identification, constants and paths
  2. Embedded data (survivors, skills, skins, artifacts, logbook, items, achievements)
  3. Survivor data (SURVIVOR_DATA)
  4. Optional external files and MASTER_DB (master database)
  5. Utilities: IDs, Steam, profiles and backups
  6. Database (load_database)
  7. Profile: XML read/write (Profile class)
  8. Unlock All + Reset + Sync Logbook
  9. Survivors: detailed entries
 10. Reports (diagnostics and status)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime
from pathlib import Path

from . import reference as ref
from .identify import identify, tier_sort_key

# ---------------------------------------------------------------------------
# 1. IDENTIFICATION, CONSTANTS AND PATHS
# ---------------------------------------------------------------------------
APP_NAME = "RoR2 Profile Manager"
VERSION = "2.14"
STEAM_APP_ID = "632360"
GAME_PROCESS = "Risk of Rain 2.exe"
BACKUP_KEEP = 15
COIN_MAX = 2**31 - 1
ID_RE = re.compile(r"[A-Za-z0-9_.]+")


def _resolve_script_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _resolve_resource_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent.parent


SCRIPT_DIR = _resolve_script_dir()
RESOURCE_DIR = _resolve_resource_dir()
BACKUP_ROOT = SCRIPT_DIR / "backups"
DEFAULT_DB_FILE = SCRIPT_DIR / "ror2_database.json"

ASSETS_DIR = RESOURCE_DIR / "ror2pm" / "assets"
ICON_ICO = ASSETS_DIR / "icon.ico"
ICON_PNG = ASSETS_DIR / "icon.png"


# ---------------------------------------------------------------------------
# 2. EMBEDDED DATA - Survivors, skills, skins and artifacts
# ---------------------------------------------------------------------------
ACH_SUFFIX = "[achievements]"
_LEGACY_ACH_SUFFIX = "[conquistas]"   # databases exported by older (Portuguese) versions
PICK_SUFFIX = "[logbook]"

_CHARACTERS = {
    "Captain": "Captain", "Croco": "Acrid", "Engineer": "Engineer",
    "Loader": "Loader", "Mage": "Artificer", "Mercenary": "Mercenary", "Toolbot": "MUL-T",
    "Treebot": "REX", "VoidSurvivor": "Void Fiend", "Drifter": "Drifter", "Bandit2": "Bandit",
    "Seeker": "Seeker", "FalseSon": "False Son", "Chef": "Chef",
}
_SKILLS = """
Bandit2.Rifle Bandit2.SkullRevolver Bandit2.SerratedShivs
Captain.CaptainSupplyDropHacking Captain.CaptainSupplyDropEquipmentRestock Captain.UtilityAlt1
Commando.FireShotgunBlast Commando.SlideJet Commando.ThrowGrenade
Croco.ChainableLeap Croco.CrocoBite Croco.PassivePoisonLethal
Engi.Harpoon Engi.SpiderMine Engi.WalkerTurret
Huntress.FlurryArrow Huntress.MiniBlink Huntress.Snipe
Loader.YankHook Loader.ZapFist Loader.Thunderslam
Mage.FlyUp Mage.IceBomb Mage.LightningBolt
Merc.EvisProjectile Merc.Uppercut Merc.FocusedAssault
Toolbot.Buzzsaw Toolbot.Grenade Toolbot.SpecialAlt
Treebot.Barrage Treebot.PlantSonicBoom Treebot.SpecialAlt1
Railgunner.UtilityAlt1 Railgunner.SpecialAlt1 Railgunner.SecondaryAlt1
Drifter.Tornado Drifter.JunkCube
DroneTech.DroneHauler DroneTech.ShieldFormation DroneTech.CommandHeadbutt
Seeker.SoulSpiral Seeker.Meditate Seeker.Sojourn
FalseSon.LaserOfTheFather FalseSon.LunarSpikes FalseSon.StepOfTheBrothers
Chef.Sear Chef.Glaze Chef.Roll
""".split()
_SKIN_OWNERS = ["Captain", "Commando", "Croco", "Engi", "Huntress", "Loader", "Mage", "Merc", "Toolbot",
                "Treebot", "Bandit2", "RailGunner", "VoidSurvivor", "Seeker", "FalseSon", "Chef", "Drifter"]
_ARTIFACTS = """
Bomb Command EliteOnly Enigma FriendlyFire Glass MixEnemy MonsterTeamGainsItems RandomSurvivorOnRespawn
Sacrifice ShadowClone SingleMonsterType Swarms TeamDeath WeakAssKnees WispOnDeath Delusion Devotion Rebirth Prestige
""".split()

# ---------------------------------------------------------------------------
# LOGBOOK - Monsters (YetGamer list)
# ---------------------------------------------------------------------------
_LOGS_MONSTERS = """
BeetleBody.0 BeetleGuardBody.0 BeetleQueenBody.0 BellBody.0 BisonBody.0 BrotherBody.0 ClayBody.0
ClayBossBody.0 ClayBruiserBody.0 ElectricWormBody.0 GolemBody.0 GravekeeperBody.0 GreaterWispBody.0
HermitCrabBody.0 ImpBody.0 ImpBossBody.0 JellyfishBody.0 LemurianBody.0 LemurianBruiserBody.0
LunarGolem.0 LunarWisp.0 MagmaWormBody.0 MiniMushroom.0 Nullifier.0 Parent.0 RoboBallBossBody.0
RoboBallMiniBody.0 Scav.0 SuperRoboBallBossBody.0 TitanBody.0 TitanGoldBody.0 VagrantBody.0
VultureBody.0 WispBody.0 LunarExploder.0 GrandparentBody.0 FlyingVerminBody.0 VerminBody.0 GupBody.0
VoidInfestorBody VoidJailerBody VoidBarnacleBody MegaConstructBody MinorConstructBody ClayGrenadierBody
AcidLarva VoidMegaCrab MiniVoidRaidCrab ChildBody GeodeBody HaulerBody
""".split()

# ---------------------------------------------------------------------------
# LOGBOOK - Environments (YetGamer list)
# ---------------------------------------------------------------------------
_LOGS_STAGES = """
arena artifactworld bazaar blackbeach dampcavesimple foggyswamp frozenwall goldshores golemplains
goolake limbo moon mysteryspace shipgraveyard skymeadow wispgraveyard rootjungle moon2 ancientloft
snowyforest sulfurpools voidstage voidraid village villagenight lemuriantemple habitat habitatfall
meridian helminthroost
""".split()

# ---------------------------------------------------------------------------
# ITEMS + EQUIPMENT (expanded list from the R2Wiki GitHub + YetGamer)
# ---------------------------------------------------------------------------
_ITEMS_FULL = """
AACannon AdaptiveArmor AlienHead ArmorPlate ArmorReductionOnHit ArtifactKey
AttackSpeedAndMoveSpeed AttackSpeedOnCrit AttackSpeedPerNearbyAllyOrEnemy
AutoCastEquipment Bandolier BarrageOnBoss BarrierOnCooldown BarrierOnKill
BarrierOnOverHeal Bear BearVoid BeetleGland Behemoth BleedOnHit
BleedOnHitAndExplode BleedOnHitVoid BonusGoldPackOnKill BonusHealthBoost
BoostAllStats BoostAttackSpeed BoostDamage BoostEquipmentRecharge BoostHp
BossDamageBonus BounceNearby BurnNearby CaptainDefenseMatrix ChainLightning
ChainLightningVoid Clover CloverVoid ConvertCritChanceToCritDamage CookedSteak
CooldownOnCrit CrippleWardOnLevel CritAtLowerElevation CritDamage CritGlasses
CritGlassesVoid CritHeal Crowbar CutHp Dagger DeathMark DelayedDamage
DestructibleSpawner DroneDynamiteDisplay DroneUpgradeHidden DroneWeapons
DroneWeaponsBoost DroneWeaponsDisplay1 DroneWeaponsDisplay2 DronesDropDynamite
Duplicator ElementalRingVoid EmpowerAlways EnergizedOnEquipmentUse
EquipmentMagazine EquipmentMagazineVoid ExecuteLowHealthElite ExplodeOnDeath
ExplodeOnDeathVoid ExtraEquipment ExtraLife ExtraLifeConsumed ExtraLifeVoid
ExtraLifeVoidConsumed ExtraShrineItem ExtraStatsOnLevelUp FallBoots Feather
FireRing FireballsOnHit Firework FlatHealth FocusConvergence FragileDamageBonus
FragileDamageBonusConsumed FreeChest Ghost GhostOnKill GoldOnHit GoldOnHurt
GummyCloneIdentifier HalfAttackSpeedHalfCooldowns HalfSpeedDoubleHealth
HeadHunter HealOnCrit HealWhileSafe HealingPotion HealingPotionConsumed
HealthDecay Hoof IceRing Icicle IgniteOnKill ImmuneToDebuff
IncreaseDamageOnMultiKill IncreaseHealing IncreasePrimaryDamage Incubator
Infusion InvadingDoppelganger ItemDropChanceOnKill JumpBoost JumpDamageStrike
Junk KillEliteFrenzy KnockBackHitEnemies Knurl LaserTurbine LemurianHarness
LevelBonus LightningStrikeOnHit LowerPricedChests LowerPricedChestsConsumed
LunarBadLuck LunarDagger LunarPrimaryReplacement LunarSecondaryReplacement
LunarSpecialReplacement LunarSun LunarTrinket LunarUtilityReplacement LunarWings
MageAttunement MasterBattery MasterCore Medkit MeteorAttackOnHighDamage
MinionLeash MinorConstructOnKill Missile MissileVoid MoneyLoan MonstersOnShrineUse
MoreMissile MoveSpeedOnKill Mushroom MushroomVoid NearbyDamageBonus NovaOnHeal
NovaOnLowHealth OnLevelUpFreeUnlock OutOfCombatArmor ParentEgg Pearl
PermanentDebuffOnHit PersonalShield Phasing PhysicsProjectile Plant PlantOnHit
PlasmaCore PowerCube PowerOrbSphere PowerPyramid PrimarySkillShuriken
RandomDamageZone RandomEquipmentTrigger RandomlyLunar RegeneratingScrap
RegeneratingScrapConsumed RepeatHeal RoboBallBuddy ScrapGreen ScrapGreenSuppressed
ScrapRed ScrapRedSuppressed ScrapWhite ScrapWhiteSuppressed ScrapYellow
SecondarySkillMagazine Seed SharedSuffering ShieldBooster ShieldOnly ShinyPearl
ShockDamageAura ShockNearby SiphonOnLowHealth SkullCounter SlowOnHit SlowOnHitVoid
SpeedBoostPickup SpeedOnPickup SprintArmor SprintBonus SprintOutOfCombat SprintWisp
Squid StatsFromScrap Stew StickyBomb StrengthenBurn StunAndPierce StunChanceOnHit
Syringe TPHealingNova Talisman TeleportOnLowHealth TeleportOnLowHealthConsumed
TempestOnKill Thorns TitanGoldDuringTP TonicAffliction Tooth TransferDebuffOnHit
TreasureCache TreasureCacheVoid TriggerEnemyDebuffs UltimateMeal UtilitySkillMagazine
VoidMegaCrabItem VoidmanPassiveItem WarCryOnCombat WarCryOnMultiKill WardOnLevel
WyrmOnHit
""".split()

_LOGBOOK_EQUIPMENT = """
AffixBlue AffixGold AffixHaunted AffixPoison AffixRed AffixWhite AffixYellow
BFG Blackhole BurnNearby Cleanse CommandMissile CrippleWard CritOnUse
DeathProjectile DroneBackup Enigma FireBallDash Fruit GainArmor Gateway
GhostGun GoldGat Jetpack LifestealOnHit Lightning LunarPotion Meteor
OrbitalLaser PassiveHealing QuestVolatileBattery Recycle Saw Scanner
SoulCorruptor SoulJar TeamWarCry Tonic
""".split()

# ---------------------------------------------------------------------------
# ACHIEVEMENTS - fallback list
# ---------------------------------------------------------------------------
_ACHIEVEMENTS_FALLBACK = """
AttackSpeed AutomationActivation BeatArena BurnToDeath CaptainBuyMegaDrone CaptainClearGameMonsoon
CaptainVisitSeveralStages CompleteMainEnding CompleteMainEndingHard CarryLunarItems ChargeTeleporterWhileNearDeath
CleanupDuty CommandoClearGameMonsoon CommandoFastFirstStageClear CommandoKillOverloadingWorm
CommandoNonLunarEndurance Complete20Stages Complete30StagesCareer CompleteMultiBossShrine CompletePrismaticTrial
CompleteTeleporter CompleteTeleporterWithoutInjury CompleteThreeStages CompleteThreeStagesWithoutHealing
CompleteUnknownEnding CrocoClearGameMonsoon CrocoKillScavenger CrocoKillWeakEnemiesMilestone
CrocoTotalInfectionsMilestone DefeatSuperRoboBallBoss Die20Times Die5Times Discover10UniqueTier1 Discover5Equipment
EngiArmy EngiClearGameMonsoon EngiClearTeleporterWithZeroMonsters EngiKillBossQuick FailShrineChance FindDevilAltar
FindTimedChest FindUniqueNewtStatues FreeMage HardEliteBossKill HardHitter HuntressAllGlaiveBouncesKill
HuntressClearGameMonsoon HuntressCollectCrowbars HuntressMaintainFullHealthOnFrozenWall KillBossQuantityInRun
KillBossQuick KillElementalLemurians KillEliteMonster KillElitesMilestone KillGoldTitanInOneCycle KillTotalEnemies
LoaderBigSlam LoaderClearGameMonsoon LoaderSpeedRun LogCollector LoopOnce MageAirborneMultiKill MageClearGameMonsoon
MageFastBoss MageMultiKill MajorMultikill MaxHealingShrine MercClearGameMonsoon MercCompleteTrialWithFullHealth
MercDontTouchGround MoveSpeed MultiCombatShrine NeverBackDown RepeatFirstTeleporter RepeatedlyDuplicateItems
RescueTreebot StayAlive1 SuicideHermitCrabs ToolbotClearGameMonsoon ToolbotGuardTeleporter ToolbotKillImpBossWithBfg
TotalDronesRepaired TotalMoneyCollected TreebotClearGameMonsoon TreebotDunkClayBoss TreebotLowHealthTeleporter
UseThreePortals ObtainArtifactBomb ObtainArtifactCommand ObtainArtifactEliteOnly ObtainArtifactEnigma
ObtainArtifactFriendlyFire ObtainArtifactGlass ObtainArtifactMixEnemy ObtainArtifactMonsterTeamGainsItems
ObtainArtifactRandomSurvivorOnRespawn ObtainArtifactSacrifice ObtainArtifactShadowClone ObtainArtifactSingleMonsterType
ObtainArtifactSwarms ObtainArtifactTeamDeath ObtainArtifactWeakAssKnees ObtainArtifactWispOnDeath
Bandit2ClearGameMonsoon Bandit2ConsecutiveReset Bandit2RevolverFinale Bandit2StackSuperBleed
ToolbotBeatArenaLater MercXSkillsInYSeconds TreebotBigHeal LoaderKillLoaders CaptainSupplyDropFinale
RailgunnerDealMassiveDamage CompleteVoidEnding RailgunnerClearGameMonsoon VoidSurvivorClearGameMonsoon
RailgunnerAirborneMultiKill RailgunnerConsecutiveWeakPoints UnlockFalseSon FreeDrifter DroneTechUniqueDrones
FalseSonLaserMultiKill HuntressClearMeridianEvent SeekerClearGameMonsoon EngiClearMeridianEvent
CommandoClearMeridianEvent FalseSonClearGameMonsoon RailgunnerClearMeridianEvent Bandit2ClearMeridianEvent
MercClearMeridianEvent CrocoClearMeridianEvent CaptainClearMeridianEvent ToolbotClearMeridianEvent
VoidSurvivorClearMeridianEvent MageClearMeridianEvent LoaderClearMeridianEvent DroneTechTrickshot
ChefClearGameMonsoon DrifterJunkCubeAchievement FalseSonGrowthChallenge TreebotClearMeridianEvent
BarbecueQuantityBisonInRun RolyPolyHitFiveAirEnemies DroneTechClearGameMonsoon BurnMithrix NukeSojourn
DrifterTinkerAchievement DrifterTornadoSlamAchievement DrifterClearGameMonsoon FalseSonKillMithrixWithGoldenGal
HuntressPurge CommandoPurge DroneTechJuggleLemurian EngiPurge CrocoPurge MercPurge Bandit2Decompile ToolbotPurge
DroneTechDefeatVultureBossWhileAirborne MageDecompile CaptainDecompile LoaderDecompile TreebotDecompile
SeekerAirMultiHit SeekerPerfect20Meditation ChefMeridianEvent SeekerClearMeridianEvent ObtainArtifactRebirth
ObtainArtifactDevotion ObtainArtifactDelusion ObtainArtifactPrestige
""".split() + [f"ObtainArtifact{a}" for a in _ARTIFACTS]


# ---------------------------------------------------------------------------
# 3. SURVIVOR DATA - achievement/unlock links and SURVIVOR_DATA
# ---------------------------------------------------------------------------
ACH_LINKS: dict[str, str] = {
    "Characters.Bandit2": "CompleteThreeStages",
    "Characters.Toolbot": "RepeatFirstTeleporter",
    "Characters.Engineer": "Complete30StagesCareer",
    "Characters.Mage": "FreeMage",
    "Characters.Mercenary": "CompleteUnknownEnding",
    "Characters.Treebot": "RescueTreebot",
    "Characters.Loader": "DefeatSuperRoboBallBoss",
    "Characters.Croco": "BeatArena",
    "Characters.Captain": "CompleteMainEnding",
    "Characters.VoidSurvivor": "CompleteVoidEnding",
    "Characters.Drifter": "FreeDrifter",
    **{f"Artifacts.{a}": f"ObtainArtifact{a}" for a in _ARTIFACTS},
}

SURVIVOR_KEYS: dict[str, list[str]] = {
    "Commando": ["commando"], "Huntress": ["huntress"], "Bandit": ["bandit2", "bandit"],
    "MUL-T": ["toolbot"], "Engineer": ["engi", "engineer"], "Artificer": ["mage"],
    "Mercenary": ["merc", "mercenary"], "REX": ["treebot"], "Loader": ["loader"],
    "Acrid": ["croco"], "Captain": ["captain"], "Railgunner": ["railgunner"],
    "Void Fiend": ["voidsurvivor"], "Seeker": ["seeker"], "False Son": ["falseson"],
    "Chef": ["chef"], "Drifter": ["drifter"], "Operator": ["dronetech", "operator"],
}

ACH_PREFIXES: dict[str, list[str]] = {
    "Commando": ["commando"], "Huntress": ["huntress"], "Bandit": ["bandit2"], "MUL-T": ["toolbot"],
    "Engineer": ["engi"], "Artificer": ["mage"], "Mercenary": ["merc"], "REX": ["treebot"],
    "Loader": ["loader"], "Acrid": ["croco"], "Captain": ["captain"], "Railgunner": ["railgunner"],
    "Void Fiend": ["voidsurvivor"], "Seeker": ["seeker"], "False Son": ["falseson"],
    "Chef": ["chef"], "Drifter": ["drifter"], "Operator": ["dronetech"],
}


def _m(n: str) -> tuple[str, str, str]:
    return (f"{n}ClearGameMonsoon", "Mastery", f"Skins.{n}.Alt1")


SURVIVOR_DATA = [
    ("Commando", None, None,
     [("CommandoFastFirstStageClear", "Tactical Slide", "Skills.Commando.SlideJet"),
      ("CommandoKillOverloadingWorm", "Phase Blast", "Skills.Commando.FireShotgunBlast"),
      ("CommandoNonLunarEndurance", "Frag Grenade", "Skills.Commando.ThrowGrenade")],
     [_m("Commando"), ("CommandoClearMeridianEvent", "Meridian", None)]),
    ("Huntress", None, None,
     [("HuntressCollectCrowbars", "Flurry", "Skills.Huntress.FlurryArrow"),
      ("HuntressAllGlaiveBouncesKill", "Ballista", "Skills.Huntress.Snipe"),
      ("HuntressMaintainFullHealthOnFrozenWall", "Phase Blink", "Skills.Huntress.MiniBlink")],
     [_m("Huntress"), ("HuntressClearMeridianEvent", "Meridian", None)]),
    ("Bandit", "Characters.Bandit2", "CompleteThreeStages",
     [("Bandit2ConsecutiveReset", "Desperado", "Skills.Bandit2.SkullRevolver"),
      ("Bandit2StackSuperBleed", "Serrated Shiv", "Skills.Bandit2.SerratedShivs"),
      ("Bandit2RevolverFinale", "Blast", "Skills.Bandit2.Rifle")],
     [_m("Bandit2"), ("Bandit2ClearMeridianEvent", "Meridian", None)]),
    ("MUL-T", "Characters.Toolbot", "RepeatFirstTeleporter",
     [("ToolbotGuardTeleporter", "Scrap Launcher", "Skills.Toolbot.Grenade"),
      ("ToolbotKillImpBossWithBfg", "Power-Saw", "Skills.Toolbot.Buzzsaw"),
      ("ToolbotBeatArenaLater", "Power Mode", "Skills.Toolbot.SpecialAlt")],
     [_m("Toolbot"), ("ToolbotClearMeridianEvent", "Meridian", None)]),
    ("Engineer", "Characters.Engineer", "Complete30StagesCareer",
     [("EngiArmy", "Spider Mines", "Skills.Engi.SpiderMine"),
      ("EngiKillBossQuick", "Thermal Harpoons", "Skills.Engi.Harpoon"),
      ("EngiClearTeleporterWithZeroMonsters", "Carbonizer Turret", "Skills.Engi.WalkerTurret")],
     [_m("Engi"), ("EngiClearMeridianEvent", "Meridian", None)]),
    ("Artificer", "Characters.Mage", "FreeMage",
     [("MageMultiKill", "Plasma Bolt", "Skills.Mage.LightningBolt"),
      ("MageAirborneMultiKill", "Ion Surge", "Skills.Mage.FlyUp"),
      ("MageFastBoss", "Nano-Spear", "Skills.Mage.IceBomb")],
     [_m("Mage"), ("MageClearMeridianEvent", "Meridian", None)]),
    ("Mercenary", "Characters.Mercenary", "CompleteUnknownEnding",
     [("MercCompleteTrialWithFullHealth", "Slicing Winds", "Skills.Merc.EvisProjectile"),
      ("MercXSkillsInYSeconds", "Focused Assault", "Skills.Merc.FocusedAssault"),
      ("MercDontTouchGround", "Rising Thunder", "Skills.Merc.Uppercut")],
     [_m("Merc"), ("MercClearMeridianEvent", "Meridian", None)]),
    ("REX", "Characters.Treebot", "RescueTreebot",
     [("TreebotLowHealthTeleporter", "DIRECTIVE: Drill", None),
      ("TreebotBigHeal", "DIRECTIVE: Harvest", "Skills.Treebot.SpecialAlt1"),
      ("TreebotDunkClayBoss", "Bramble Volley", None)],
     [_m("Treebot"), ("TreebotClearMeridianEvent", "Meridian", None)]),
    ("Loader", "Characters.Loader", "DefeatSuperRoboBallBoss",
     [("LoaderSpeedRun", "Spiked Fist", "Skills.Loader.YankHook"),
      ("LoaderBigSlam", "Thunder Gauntlet", "Skills.Loader.ZapFist"),
      ("LoaderKillLoaders", "Thunderslam", "Skills.Loader.Thunderslam")],
     [_m("Loader"), ("LoaderClearMeridianEvent", "Meridian", None)]),
    ("Acrid", "Characters.Croco", "BeatArena",
     [("CrocoTotalInfectionsMilestone", "Blight", "Skills.Croco.PassivePoisonLethal"),
      ("CrocoKillScavenger", "Ravenous Bite", "Skills.Croco.CrocoBite"),
      ("CrocoKillWeakEnemiesMilestone", "Frenzied Leap", "Skills.Croco.ChainableLeap")],
     [_m("Croco"), ("CrocoClearMeridianEvent", "Meridian", None)]),
    ("Captain", "Characters.Captain", "CompleteMainEnding",
     [("CaptainVisitSeveralStages", "Beacon: Resupply", "Skills.Captain.CaptainSupplyDropEquipmentRestock"),
      ("CaptainBuyMegaDrone", "Beacon: Hacking", "Skills.Captain.CaptainSupplyDropHacking"),
      ("CaptainSupplyDropFinale", "'DIABLO' Strike", "Skills.Captain.UtilityAlt1")],
     [_m("Captain"), ("CaptainClearMeridianEvent", "Meridian", None)]),
    ("Railgunner", None, None,
     [("RailgunnerConsecutiveWeakPoints", "HH44 Marksman", None),
      ("RailgunnerDealMassiveDamage", "Cryocharge", None),
      ("RailgunnerAirborneMultiKill", "Polar Field Device", None)],
     [("RailgunnerClearGameMonsoon", "Mastery", "Skins.RailGunner.Alt1"),
      ("RailgunnerClearMeridianEvent", "Meridian", None)]),
    ("Void Fiend", "Characters.VoidSurvivor", "CompleteVoidEnding", [],
     [("VoidSurvivorClearGameMonsoon", "Mastery", "Skins.VoidSurvivor.Alt1"),
      ("VoidSurvivorClearMeridianEvent", "Meridian", None)]),
    ("Seeker", None, None,
     [("SeekerAirMultiHit", "Soul Spiral", "Skills.Seeker.SoulSpiral"),
      ("SeekerPerfect20Meditation", "Meditate", "Skills.Seeker.Meditate"),
      ("NukeSojourn", "Sojourn", "Skills.Seeker.Sojourn")],
     [("SeekerClearGameMonsoon", "Mastery", "Skins.Seeker.Alt1"),
      ("SeekerClearMeridianEvent", "Meridian", None)]),
    ("False Son", None, "UnlockFalseSon",
     [("FalseSonLaserMultiKill", "Laser of the Father", "Skills.FalseSon.LaserOfTheFather"),
      ("FalseSonKillMithrixWithGoldenGal", "Lunar Spikes", "Skills.FalseSon.LunarSpikes"),
      ("FalseSonGrowthChallenge", "Step of the Brothers", "Skills.FalseSon.StepOfTheBrothers")],
     [("FalseSonClearGameMonsoon", "Mastery", "Skins.FalseSon.Alt1"),
      ("FalseSonClearMeridianEvent", "Meridian", None)]),
    ("Chef", None, "ActivateChef",
     [("BarbecueQuantityBisonInRun", "Sear", "Skills.Chef.Sear"),
      ("BurnMithrix", "Glaze", "Skills.Chef.Glaze"),
      ("RolyPolyHitFiveAirEnemies", "Roll", "Skills.Chef.Roll")],
     [("ChefClearGameMonsoon", "Mastery", "Skins.Chef.Alt1"),
      ("ChefMeridianEvent", "Meridian", None)]),
    ("Drifter", "Characters.Drifter", "FreeDrifter",
     [("DrifterJunkCubeAchievement", "Junk Cube", "Skills.Drifter.JunkCube"),
      ("DrifterTornadoSlamAchievement", "Tornado Slam", "Skills.Drifter.Tornado"),
      ("DrifterTinkerAchievement", "Tinker", None)],
     [("DrifterClearGameMonsoon", "Mastery", "Skins.Drifter.Alt1")]),
    ("Operator", None, None,
     [("DroneTechTrickshot", "skill (Trickshot)", None),
      ("DroneTechDefeatVultureBossWhileAirborne", "skill (Vulture)", None),
      ("DroneTechJuggleLemurian", "skill (Lemurian)", None),
      ("DroneTechUniqueDrones", "skill (Drones)", None)],
     [("DroneTechClearGameMonsoon", "Mastery", None)]),
]


def _survivor_label_map() -> dict[str, str]:
    """Readable labels from SURVIVOR_DATA: unlock -> skill/skin name; achievement -> 'Survivor · name'."""
    out: dict[str, str] = {}
    for name, _s_unlock, s_ach, skills, skins in SURVIVOR_DATA:
        if s_ach:
            out[s_ach] = f"{name} · Unlock survivor (achievement)"
        for ach, label, unlock in list(skills) + list(skins):
            if unlock:
                out[unlock] = label
            if ach:
                out.setdefault(ach, f"{name} · {label} (achievement)")
    return out


SURVIVOR_LABELS = _survivor_label_map()


def label_of(code: str) -> str:
    """Readable name of any ID (item, monster, skill, achievement...)."""
    return identify(code, SURVIVOR_LABELS).label


# ---------------------------------------------------------------------------
# 4. EXTERNAL FILES (OPTIONAL) AND MASTER DATABASE
# ---------------------------------------------------------------------------
ITEMS_FILE = SCRIPT_DIR / "items_ids.json"
LOGBOOK_FILE = SCRIPT_DIR / "logbook_ids.json"
ACHIEVEMENTS_FILE = SCRIPT_DIR / "achievements_ids.json"


def _load_items() -> list[tuple[str, str]]:
    if ITEMS_FILE.is_file():
        try:
            data = json.loads(ITEMS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                out: list[tuple[str, str]] = []
                for code in data:
                    code = str(code)
                    label = code.split(".", 1)[1] if "." in code else code
                    out.append((code, label))
                return out
        except (OSError, ValueError):
            pass

    combined = list(dict.fromkeys(_ITEMS_FULL + _LOGBOOK_EQUIPMENT))
    return [(f"Items.{x}", x) for x in combined]


def _load_logbook_ids_file() -> list[tuple[str, str]]:
    if LOGBOOK_FILE.is_file():
        try:
            data = json.loads(LOGBOOK_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return _pairs([str(c) for c in data])
        except (OSError, ValueError):
            pass
    return []


def _load_achievements() -> list[tuple[str, str]]:
    known = [a for a in ref.REF_ACHIEVEMENTS if not a.startswith("MysticsItems_")]
    return [(x, x) for x in dict.fromkeys(_ACHIEVEMENTS_FALLBACK + known)]


def _pairs(codes: list[str]) -> list[tuple[str, str]]:
    return [(c, c.split(".", 1)[1] if "." in c else c) for c in dict.fromkeys(codes)]


def _logbook_ids() -> list[tuple[str, str]]:
    """Logbook (368) as in the game: survivors 19, monsters 62, environments 42, drones 21, items+equipment 228 (elite aspects included)."""
    surv = [(c, v[0]) for c, v in ref.REF_SURVIVOR_LOG.items()]
    logs = _load_logbook_ids_file() or _pairs([c for c in ref.REF_LOGS if c.startswith("Logs.")])
    hidden = set(ref.REF_HIDDEN_LOGS)
    monsters = [(c, d) for c, d in logs if not c.startswith("Logs.Stages.") and c not in hidden]
    # Solus Heart (hidden final boss) has its own entry; the real ID is "Log.SolusHeart" (no "s")
    monsters += [(c, c.split(".", 1)[1]) for c in ref.REF_LOGS if c == "Log.SolusHeart"]
    stages = [(c, d) for c, d in logs if c.startswith("Logs.Stages.")]
    drones = _pairs(ref.REF_PICK_DRONES) + [(c, c.split(".", 1)[1]) for c in ref.REF_DRONE_STAT_ONLY]
    items = _pairs([f"ItemIndex.{x.split('.', 1)[1]}" for x in ref.REF_PICK_ITEMS
                    if x.split(".", 1)[1] not in ref.REF_HIDDEN_ITEMS])
    equip = _pairs([x for x in ref.REF_PICK_EQUIP if x.split(".", 1)[1] not in ref.REF_HIDDEN_EQUIP])
    return list(dict.fromkeys(surv + monsters + stages + drones + items + equip))


# Items that really exist in the game: excludes internal IDs (Junk, *Consumed, *Helper, *Display…)
# which never enter <discoveredPickups> and would always show as "missing".
_REAL_ITEMS = {x.split(".", 1)[1] for x in ref.REF_PICK_ITEMS} - set(ref.REF_HIDDEN_ITEMS)


MASTER_DB: dict[str, list[tuple[str, str]]] = {
    "Survivors": _pairs(ref.REF_CHARACTERS),
    "Alternate skills": [(c, c.split(".", 1)[1].replace(".", " · ")) for c in ref.REF_SKILLS],
    "Skins": [(c, c.split(".", 1)[1].replace(".", " · ")) for c in ref.REF_SKINS],
    "Items": _pairs([f"ItemIndex.{x}" for x in ref.REF_ITEMS_ALL if x in _REAL_ITEMS]),
    "Artifacts": _pairs(ref.REF_ARTIFACTS),
    "Logbook": _logbook_ids(),
    "Eclipse": _pairs(ref.REF_ECLIPSE),
    "Newt statues & shop": _pairs(ref.REF_NEWT + ref.REF_SHOP),
    f"All known achievements {ACH_SUFFIX}": _load_achievements(),
}
Database = dict[str, list[tuple[str, str]]]


def _relabel(category: str, items: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Give each ID its readable name (the code never changes). Items are sorted by tier."""
    out = [(code, label_of(code)) for code, _old in items]
    if category == "Items":
        out.sort(key=lambda t: tier_sort_key(t[0]))
    return out


MASTER_DB = {cat: _relabel(cat, items) for cat, items in MASTER_DB.items()}


# ---------------------------------------------------------------------------
# 5. UTILITIES - IDs, Steam, profiles and backups
# ---------------------------------------------------------------------------
def kind_of(category: str) -> str:
    if category.endswith((ACH_SUFFIX, _LEGACY_ACH_SUFFIX)):
        return "achievement"
    return "pickup" if category.endswith(PICK_SUFFIX) else "unlock"


def parse_ids(text: str) -> tuple[list[str], list[str], list[str]]:
    text = re.sub(r"</?\w+>", " ", text)
    add: list[str] = []
    remove: list[str] = []
    invalid: list[str] = []
    for token in re.split(r"[\s,;]+", text):
        if not token:
            continue
        target = remove if token.startswith("-") else add
        code = token.lstrip("-")
        if ID_RE.fullmatch(code):
            target.append(code)
        else:
            invalid.append(token)
    return add, remove, invalid


def known_codes(db: Database, kind: str) -> set[str]:
    return {c.lower() for cat, items in db.items() if kind_of(cat) == kind for c, _ in items}


def steam_roots() -> list[Path]:
    candidates: list[Path] = []
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
                candidates.append(Path(winreg.QueryValueEx(key, "SteamPath")[0]))
        except OSError:
            pass
        candidates += [
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Steam",
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Steam",
            Path.home() / "AppData" / "Local" / "Steam",
        ]
        candidates += [Path(f"{d}:\\Steam") for d in "CDEFGH"]
    else:
        candidates += [Path.home() / ".steam" / "steam", Path.home() / ".local" / "share" / "Steam"]
    seen: set[str] = set()
    roots: list[Path] = []
    for c in candidates:
        key = str(c).lower()
        if key not in seen and (c / "userdata").is_dir():
            seen.add(key)
            roots.append(c)
    return roots


def discover_profiles() -> list[Path]:
    found: list[Path] = []
    for root in steam_roots():
        found += sorted((root / "userdata").glob(f"*/{STEAM_APP_ID}/remote/UserProfiles/*.xml"))
    return found


def profile_summary(path: Path) -> str:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return "unreadable file"
    name = (root.findtext(".//name") or "?").strip() or "?"
    unlocks = sum(1 for _ in root.iter("unlock"))
    achievements = len((root.findtext(".//achievementsList") or "").split())
    coins = (root.findtext(".//coins") or "?").strip()
    return f"'{name}' · {unlocks} unlocks · {achievements} achievements · {coins} coins"


def profile_fingerprint(path: Path) -> str:
    try:
        st = path.stat()
    except OSError:
        return ""
    when = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")
    owner = path.parents[3].name if len(path.parents) > 3 else "?"
    return f"{owner}\\{path.name} · {when} · {st.st_size / 1024:.0f} KB"


def game_running() -> bool:
    if os.name != "nt":
        return False
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {GAME_PROCESS}", "/NH"],
            capture_output=True, text=True, timeout=5,
            creationflags=flags,
        ).stdout
        return GAME_PROCESS.lower() in out.lower()
    except (OSError, subprocess.SubprocessError):
        return False


def backup_dir(profile_path: Path) -> Path:
    tag = hashlib.md5(str(profile_path.resolve()).lower().encode()).hexdigest()[:8]
    return BACKUP_ROOT / f"{profile_path.stem}_{tag}"


def list_backups(profile_path: Path) -> list[Path]:
    d = backup_dir(profile_path)
    return sorted(d.glob("*.xml.bak"), reverse=True) if d.is_dir() else []


def make_backup(profile_path: Path) -> Path:
    d = backup_dir(profile_path)
    d.mkdir(parents=True, exist_ok=True)
    dest = d / f"{datetime.now():%Y%m%d-%H%M%S}.xml.bak"
    shutil.copy2(profile_path, dest)
    for old in list_backups(profile_path)[BACKUP_KEEP:]:
        old.unlink(missing_ok=True)
    return dest


# ---------------------------------------------------------------------------
# 6. DATABASE
# ---------------------------------------------------------------------------
def load_database(custom: str | None) -> Database:
    if custom:
        source = Path(custom)
        if source.is_file():
            try:
                data = json.loads(source.read_text(encoding="utf-8"))
                db = {str(cat): [(str(i), str(d)) for i, d in items] for cat, items in data.items()}
                db = {c: v for c, v in db.items() if not c.startswith(("Discovered:", "Descobertos:"))}
                return db
            except (OSError, ValueError, TypeError):
                pass
    return {cat: list(items) for cat, items in MASTER_DB.items()}


# ---------------------------------------------------------------------------
# 7. PROFILE - XML read/write (Profile class)
# ---------------------------------------------------------------------------
PICKUP_PREFIXES = ("ItemIndex.", "EquipmentIndex.", "DroneIndex.", "ArtifactIndex.", "LunarCoin.")


def _norm_kind(code: str, kind: str) -> str:
    """Logbook items/equipment/drones live in <discoveredPickups>, not in <unlock>."""
    if kind != "unlock":
        return kind
    if code.startswith(("DroneLog.", "SurvivorLog.")):
        return "statlog"
    return "pickup" if code.startswith(PICKUP_PREFIXES) else kind


class Profile:
    ACH_TAG = "achievementsList"
    UNLOCK_TAG = "unlock"

    def __init__(self, path: Path) -> None:
        self.path = path
        self.tree = ET.parse(path)
        self.root = self.tree.getroot()
        self.name = (self.root.findtext(".//name") or "").strip()
        self._parents = {child: parent for parent in self.root.iter() for child in parent}

        node = self.root.find(self.ACH_TAG) or self.root.find(f".//{self.ACH_TAG}")
        self._ach_node = node
        self.achievements: dict[str, None] = (
            dict.fromkeys((node.text or "").split()) if node is not None else {}
        )

        self._unlock_nodes = list(self.root.iter(self.UNLOCK_TAG))
        self.unlocks: set[str] = {(n.text or "").strip() for n in self._unlock_nodes} - {""}

        stats = self.root.find("stats")
        self._stat_nodes: dict[str, ET.Element] = (
            {n.get("name"): n for n in stats if n.tag == "stat" and n.get("name")} if stats is not None else {}
        )
        self._stats_node = stats
        self._stats_dirty = False
        self._pick_node = self.root.find("discoveredPickups")
        self.pickups: dict[str, None] = (
            dict.fromkeys((self._pick_node.text or "").split()) if self._pick_node is not None else {}
        )

        self._coin_node = self._find_coin_node()
        self._base_pick = frozenset(self.pickups)
        self._base_unlocks = frozenset(self.unlocks)
        self._base_ach = frozenset(self.achievements)
        self._coin_baseline = self.coins
        self._base_stats = self._stats_snapshot()

    def _stats_snapshot(self) -> dict[str, str]:
        return {k: (n.text or "").strip() for k, n in self._stat_nodes.items()}

    @property
    def stats_changed(self) -> int:
        """Number of statistics that differ from the last load/save."""
        now = self._stats_snapshot()
        return sum(1 for k, v in now.items() if self._base_stats.get(k, "0") != v)

    def _find_coin_node(self) -> ET.Element | None:
        for xpath in ("coins", ".//coins", ".//stat[@name='userCoins']"):
            node = self.root.find(xpath)
            if node is not None:
                return node
        return None

    @property
    def coins(self) -> int | None:
        if self._coin_node is None:
            return None
        text = (self._coin_node.text or "").strip()
        return int(text) if text.isdigit() else None

    @coins.setter
    def coins(self, value: int) -> None:
        if self._coin_node is None:
            raise RuntimeError("coin node not found")
        self._coin_node.text = str(value)

    @property
    def recognized(self) -> bool:
        return bool(self.unlocks or self.achievements)

    @property
    def added(self) -> int:
        return (len(self.unlocks - self._base_unlocks) + len(set(self.achievements) - self._base_ach)
                + len(set(self.pickups) - self._base_pick))

    @property
    def removed(self) -> int:
        return (len(self._base_unlocks - self.unlocks) + len(self._base_ach - set(self.achievements))
                + len(self._base_pick - set(self.pickups)))

    @property
    def dirty(self) -> bool:
        return bool(self.added or self.removed or self.stats_changed or self.coins != self._coin_baseline)

    def ensure_stat(self, name: str, minimum: int = 1) -> None:
        """Ensure a minimum value in a statistic (the logbook requires kills/visits > 0)."""
        node = self._stat_nodes.get(name)
        if node is None:
            if self._stats_node is None:
                return
            node = ET.Element("stat", {"name": name})
            node.text = "0"
            node.tail = self._stats_node[-1].tail if len(self._stats_node) else None
            self._stats_node.append(node)
            self._stat_nodes[name] = node
        try:
            current = float((node.text or "0").strip() or 0)
        except ValueError:
            current = 0
        if current < minimum:
            node.text = str(minimum)
            self._stats_dirty = True

    def _stat_value(self, name: str) -> float:
        node = self._stat_nodes.get(name)
        try:
            return float((node.text or "0").strip()) if node is not None else 0
        except ValueError:
            return 0

    def _discover(self, code: str) -> None:
        for stat in ref.REF_DISCOVERY.get(code, ()):
            self.ensure_stat(stat)

    def _bag(self, kind: str):
        if kind == "achievement":
            return self.achievements
        return self.pickups if kind == "pickup" else self.unlocks

    def find_real(self, code: str, kind: str = "unlock") -> str | None:
        kind = _norm_kind(code, kind)
        if kind == "statlog":
            stats = ref.REF_DISCOVERY.get(code, [])
            need = [c for c in ref.REF_COMPANIONS.get(code, ()) if c.startswith("Characters.")]
            ok = bool(stats) and all(self._stat_value(x) > 0 for x in stats) and all(c in self.unlocks for c in need)
            return code if ok else None
        bag = self._bag(kind)
        if code in bag:
            return code
        low = code.lower()
        return next((k for k in bag if k.lower() == low), None)

    def has(self, code: str, kind: str = "unlock") -> bool:
        kind = _norm_kind(code, kind)
        return self.find_real(code, kind) is not None

    def add(self, code: str, kind: str = "unlock") -> None:
        kind = _norm_kind(code, kind)
        if kind == "achievement":
            if self._ach_node is not None and not self.has(code, kind):
                self.achievements.setdefault(code, None)
        elif kind == "statlog":
            self._discover(code)
        elif kind == "pickup":
            if self._pick_node is not None and not self.has(code, kind):
                self.pickups.setdefault(code, None)
            self._discover(code)
        else:
            if not self.has(code, kind):
                self.unlocks.add(code)
            self._discover(code)

    def remove(self, code: str, kind: str = "unlock") -> None:
        kind = _norm_kind(code, kind)
        real = self.find_real(code, kind)
        if real is None:
            return
        if kind == "achievement":
            self.achievements.pop(real, None)
        elif kind == "pickup":
            self.pickups.pop(real, None)
        elif kind == "statlog":
            for stat in ref.REF_DISCOVERY.get(code, []):
                node = self._stat_nodes.get(stat)
                if node is not None and self._stat_value(stat) <= 1:   # does not erase real progress
                    node.text = "0"
                    self._stats_dirty = True
        else:
            self.unlocks.discard(real)

    def state(self, code: str, kind: str = "unlock") -> int:
        if self.has(code, kind):
            return 2
        linked = ACH_LINKS.get(code) if kind == "unlock" else None
        return 1 if linked and self.has(linked, "achievement") else 0

    def count(self, items: list[tuple[str, str]], kind: str = "unlock") -> int:
        return sum(1 for code, _ in items if self.state(code, kind) > 0)

    def _apply(self) -> None:
        if self._ach_node is not None:
            self._ach_node.text = " ".join(self.achievements)
        if self._pick_node is not None:
            self._pick_node.text = " ".join(self.pickups)

        kept: set[str] = set()
        for node in list(self._unlock_nodes):
            code = (node.text or "").strip()
            if code in self.unlocks and code not in kept:
                kept.add(code)
                continue
            parent = self._parents.get(node)
            if parent is not None:
                parent.remove(node)
            self._unlock_nodes.remove(node)

        new_codes = sorted(self.unlocks - kept)
        if not new_codes:
            return
        if self._unlock_nodes:
            anchor = self._unlock_nodes[-1]
            parent = self._parents[anchor]
            pos = list(parent).index(anchor) + 1
            tail = anchor.tail
        else:
            parent, pos, tail = self.root, len(self.root), None
        for code in new_codes:
            element = ET.Element(self.UNLOCK_TAG)
            element.text = code
            element.tail = tail
            parent.insert(pos, element)
            pos += 1
            self._unlock_nodes.append(element)
            self._parents[element] = parent

    def save(self, dry_run: bool = False) -> Path | None:
        self._apply()
        if dry_run:
            return None
        backup = make_backup(self.path)
        tmp = self.path.with_name(self.path.name + ".tmp")
        try:
            self.tree.write(tmp, encoding="utf-8", xml_declaration=True)
            ET.parse(tmp)
            os.replace(tmp, self.path)
        finally:
            tmp.unlink(missing_ok=True)
        self._base_unlocks = frozenset(self.unlocks)
        self._base_ach = frozenset(self.achievements)
        self._base_pick = frozenset(self.pickups)
        self._coin_baseline = self.coins
        self._base_stats = self._stats_snapshot()
        return backup


def set_state(profile: Profile, code: str, kind: str, on: bool) -> None:
    for companion in ref.REF_COMPANIONS.get(code, ()):
        (profile.add if on else profile.remove)(companion, "unlock")
    linked = ACH_LINKS.get(code) if kind == "unlock" else None
    if on:
        profile.add(code, kind)
        if linked:
            profile.add(linked, "achievement")
    else:
        profile.remove(code, kind)
        if linked:
            profile.remove(linked, "achievement")


def link_note(profile: Profile, code: str, kind: str) -> str:
    achievement = ACH_LINKS.get(code) if kind == "unlock" else None
    if not achievement:
        return ""
    state = "yes" if profile.has(achievement, "achievement") else "no"
    return f"achievement {achievement}: {state}"


# ---------------------------------------------------------------------------
# 8. UNLOCK ALL + RESET + SYNC LOGBOOK
# ---------------------------------------------------------------------------
def _cats(db: Database, what: str) -> list[str]:
    """Achievement ('achievement') or logbook ('logbook') categories of the database."""
    if what == "achievement":
        return [c for c in db if c.endswith((ACH_SUFFIX, _LEGACY_ACH_SUFFIX))]
    return [c for c in db if c == "Logbook" or c.endswith(PICK_SUFFIX)]


def _group_of(cat: str) -> str:
    kind = kind_of(cat)
    if kind == "achievement":
        return "achievement"
    return "logbook" if (cat == "Logbook" or cat.endswith(PICK_SUFFIX)) else "unlock"


_DLC_CACHE: dict[str, str] = {}

DLC_LABELS: dict[str, str] = {
    "Base": "Base game", "SotV": "Survivors of the Void",
    "SotS": "Seekers of the Storm", "AC": "Alloyed Collective",
}


def dlc_of(code: str) -> str:
    """Short DLC code of any ID: 'Base', 'SotV', 'SotS' or 'AC'."""
    got = _DLC_CACHE.get(code)
    if got is None:
        got = _DLC_CACHE[code] = identify(code, SURVIVOR_LABELS).dlc or "Base"
    return got


def dlc_progress(profile: Profile, db: Database) -> dict[str, tuple[int, int]]:
    """{dlc: (have, total)} over every entry of the database."""
    out = {k: [0, 0] for k in DLC_LABELS}
    for cat, entries in db.items():
        kind = kind_of(cat)
        for code, _ in entries:
            row = out.setdefault(dlc_of(code), [0, 0])
            row[1] += 1
            if profile.state(code, kind) == 2:
                row[0] += 1
    return {k: (v[0], v[1]) for k, v in out.items() if v[1]}


def unlock_all(profile: Profile, db: Database, apply: bool = True,
               dlc: str | None = None) -> dict[str, int]:
    """Unlock EVERYTHING the database knows: survivors, skills, skins, items, artifacts,
    Eclipse, Newt statues/shop, achievements and logbook.

    `dlc` limits it to one content pack ('Base', 'SotV', 'SotS' or 'AC'); None = everything.
    Returns how many entries were missing per group ('unlock', 'achievement', 'logbook').
    With apply=False it only counts, without changing the profile.
    """
    counts = {"unlock": 0, "achievement": 0, "logbook": 0}
    for cat, entries in db.items():
        group = _group_of(cat)
        kind = kind_of(cat)
        for code, _ in entries:
            if dlc is not None and dlc_of(code) != dlc:
                continue
            if profile.state(code, kind) != 2:
                counts[group] += 1
            if apply:   # also for existing ones: ensures linked unlocks and statistics
                set_state(profile, code, kind, True)
    return counts


def reset_all(profile: Profile, db: Database, apply: bool = True) -> dict[str, int]:
    """RESET: lock EVERYTHING again so it can be unlocked afresh.

    Removes every unlock, achievement and logbook entry from the profile - both the ones the
    database knows about and any extra ones found only in the profile. Lunar coins are left
    alone. ALL numeric statistics are set to 0 (challenges and logbook entries are driven by them).

    Returns how many entries were set per group ('unlock', 'achievement', 'logbook') before
    the reset. With apply=False it only counts, without changing the profile.
    """
    counts = {
        "unlock": len(profile.unlocks),
        "achievement": len(profile.achievements),
        "logbook": len(profile.pickups),
    }
    if not apply:
        return counts
    for cat, entries in db.items():          # also resets linked entries and planted logbook stats
        kind = kind_of(cat)
        for code, _ in entries:
            set_state(profile, code, kind, False)
    profile.unlocks.clear()                  # anything left that only the profile knew about
    profile.achievements.clear()
    profile.pickups.clear()
    # Many challenges (achievements) and logbook entries are driven by statistics (deaths, kills,
    # gold, stages, visits, summons, time held...) and the game re-grants them from those
    # numbers. Set EVERY numeric statistic to 0 so nothing can come back by itself.
    for node in profile._stat_nodes.values():
        text = (node.text or "").strip()
        if text and text != "0":
            try:
                float(text)
            except ValueError:
                continue
            node.text = "0"
            profile._stats_dirty = True
    return counts


_GATE_PREFIXES = ("Items.", "Characters.")


def _logbook_gates(code: str) -> list[str]:
    """Unlocks that must exist in the profile for this entry to be available in game."""
    gates = [c for c in ref.REF_COMPANIONS.get(code, ()) if c.startswith(_GATE_PREFIXES)]
    if code.startswith("SurvivorLog."):
        gates += [c for c in ref.REF_SURVIVOR_LOG.get(code, ("", "", []))[2] if c not in gates]
    return gates


def _logbook_extras(code: str) -> list[str]:
    """Linked entries (e.g. the Shopkeeper's hidden log) that go along with this one."""
    return [c for c in ref.REF_COMPANIONS.get(code, ()) if not c.startswith(_GATE_PREFIXES)]


def _logbook_wanted(profile: Profile, code: str) -> bool:
    """Whether the entry should be in the logbook, given what the profile really has unlocked.

    Only what is locked in the game (padlock) is left out: entries with an associated unlock
    (items, equipment, survivors) require that unlock to exist in the profile; everything
    else is available from the start and goes into the logbook.
    """
    return all(profile.has(g, "unlock") for g in _logbook_gates(code))


def logbook_sync_plan(profile: Profile, db: Database) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Compare ALL logbook entries with the real state of the profile.

    Returns (to_add, to_remove) as lists of (code, kind).
    """
    add: list[tuple[str, str]] = []
    remove: list[tuple[str, str]] = []
    for cat in _cats(db, "logbook"):
        kind = kind_of(cat)
        for code, _ in db[cat]:
            want = _logbook_wanted(profile, code)
            have = profile.has(code, kind)
            if want and not have:
                add.append((code, kind))
            elif have and not want:
                remove.append((code, kind))
    return add, remove


def sync_logbook(profile: Profile, add: list[tuple[str, str]], remove: list[tuple[str, str]]) -> None:
    # direct add/remove (not set_state) so the unlocks that serve as proof are left alone
    for code, kind in add:
        profile.add(code, kind)
        for extra in _logbook_extras(code):
            profile.add(extra, "unlock")
    for code, kind in remove:
        profile.remove(code, kind)
        for extra in _logbook_extras(code):
            profile.remove(extra, "unlock")


Entry = tuple[str | None, str | None, str, str]


def logbook_entries(db: Database) -> list[tuple[str, str]]:
    """Logbook entries for the single 'Logbook' page: Monsters, Environments and Drones.

    Survivors have their own page and items/equipment are in 'Items'.
    """
    order = {"Monster": 0, "Environment": 1, "Drone": 2}
    out: list[tuple[int, str, str]] = []
    for code, label in db.get("Logbook", []):
        if code.startswith("Logs.Stages."):
            group = "Environment"
        elif code.startswith(("Logs.", "Log.")):
            group = "Monster"
        elif code.startswith(("DroneIndex.", "DroneLog.")):
            group = "Drone"
        else:
            continue
        out.append((order[group], code, f"{group} · {label.removeprefix('Stages.')}"))
    out.sort(key=lambda t: (t[0], t[2].lower()))
    return [(c, l) for _, c, l in out]


# ---------------------------------------------------------------------------
# 9. SURVIVORS - detailed entries (skills, skins, achievements)
# ---------------------------------------------------------------------------
def _unlock_group(code: str, keys: list[str]) -> str | None:
    parts = code.split(".")
    if len(parts) < 2:
        return None
    if not any(seg.lower().startswith(k) for seg in parts[1:] for k in keys):
        return None
    head = parts[0].lower()
    if head == "skills":
        return "skill"
    if head == "skins":
        return "skin"
    return "other" if head not in ("items", "logs", "artifacts") else None


def survivor_entries(data: tuple, profile: Profile | None = None) -> list[Entry]:
    name, s_unlock, s_ach, skills, skins = data
    keys = SURVIVOR_KEYS.get(name, [name.lower()])
    if profile is not None and s_unlock is None and s_ach:
        s_unlock = next((c for c in sorted(profile.unlocks) if c.startswith("Characters.")
                         and any(c.split(".", 1)[1].lower().startswith(k) for k in keys)), None)
    entries: list[Entry] = []
    if s_unlock or s_ach:
        entries.append((s_ach, s_unlock, f"Survivor: {name}", "surv"))
    entries += [(a, u, f"Skill · {label}", "skill") for a, label, u in skills]
    entries += [(a, u, f"Skin · {label}", "skin") for a, label, u in skins]

    known = {u.lower() for _, u, _, _ in entries if u}
    known_a = {a.lower() for a, _, _, _ in entries if a}

    def extra(code: str, note: str) -> None:
        group = _unlock_group(code, keys)
        if group is None or code.lower() in known:
            return
        known.add(code.lower())
        parts = code.split(".")
        tail = ".".join(parts[2:]) if len(parts) > 2 else ".".join(parts)
        label = {"skill": "Skill", "skin": "Skin"}.get(group, f"Unlock {parts[0]}")
        entries.append((None, code, f"{label} · {tail}  ({note})", group))

    for code in [f"Skills.{x}" for x in _SKILLS] + [f"Skins.{o}.Alt1" for o in _SKIN_OWNERS]:
        extra(code, "ID without linked achievement")

    if profile is not None:
        for code in sorted(profile.unlocks):
            extra(code, "from profile")
        prefixes = ACH_PREFIXES.get(name, [name.lower()])
        for ach in sorted(profile.achievements):
            if ach.lower() not in known_a and any(ach.lower().startswith(p) for p in prefixes):
                known_a.add(ach.lower())
                entries.append((ach, None, f"Achievement · {ach}  (from profile)", "ach"))
    return entries


def entry_state(profile: Profile, ach: str | None, unlock: str | None) -> int:
    have_a = ach is not None and profile.has(ach, "achievement")
    have_u = unlock is not None and profile.has(unlock)
    complete = (ach is None or have_a) and (unlock is None or have_u)
    return 2 if complete else (1 if have_a or have_u else 0)


def entry_note(profile: Profile, ach: str | None, unlock: str | None) -> str:
    parts = []
    if ach:
        parts.append(f"achievement {ach}: {'yes' if profile.has(ach, 'achievement') else 'no'}")
    if unlock:
        parts.append(f"unlock {unlock}: {'yes' if profile.has(unlock) else 'no'}")
    return " · ".join(parts)


def set_entry(profile: Profile, ach: str | None, unlock: str | None, on: bool) -> None:
    if ach:
        (profile.add if on else profile.remove)(ach, "achievement")
    if unlock:
        (profile.add if on else profile.remove)(unlock, "unlock")


# ---------------------------------------------------------------------------
# 10. REPORTS - diagnostics and profile status
# ---------------------------------------------------------------------------
def diagnose_report(profile: Profile) -> Path:
    out = SCRIPT_DIR / f"diagnostics_{profile.path.stem}.txt"
    paths: Counter[str] = Counter()

    def walk(element: ET.Element, prefix: str) -> None:
        here = f"{prefix}/{element.tag}"
        paths[here] += 1
        for child in element:
            walk(child, here)

    walk(profile.root, "")
    lines = [
        f"{APP_NAME} v{VERSION} - diagnostics",
        f"File: {profile.path}",
        f"Size: {profile.path.stat().st_size} bytes",
        f"Root: <{profile.root.tag}>",
        "",
        "Structure (path x occurrences):",
        *[f"  {p} x{n}" for p, n in sorted(paths.items())],
        "",
        f"Coins: {profile.coins}",
        f"Achievements ({len(profile.achievements)}): " + " ".join(sorted(profile.achievements)),
        "",
        f"Unlocks ({len(profile.unlocks)}):",
        *[f"  {u}" for u in sorted(profile.unlocks)],
        "",
        "Start of file (1500 characters):",
        profile.path.read_text(encoding="utf-8", errors="replace")[:1500],
    ]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def status_report(profile: Profile, db: Database) -> Path:
    out = SCRIPT_DIR / f"status_{profile.path.stem}.txt"
    lines = [
        f"{APP_NAME} v{VERSION} - profile status '{profile.name or profile.path.name}'",
        f"File: {profile.path}",
        "",
    ]
    for data in SURVIVOR_DATA:
        entries = survivor_entries(data, profile)
        done = [e for e in entries if entry_state(profile, e[0], e[1]) == 2]
        part = [e for e in entries if entry_state(profile, e[0], e[1]) == 1]
        miss = [e for e in entries if entry_state(profile, e[0], e[1]) == 0]
        lines.append(f"=== {data[0]}  ({len(done)}/{len(entries)} complete) ===")
        for title, group in (("UNLOCKED", done), ("PARTIAL", part), ("LOCKED", miss)):
            lines.append(f"  {title}:")
            if not group:
                lines.append("    -")
            for ach, unlock, label, _ in group:
                ids = " / ".join(x for x in (ach, unlock) if x) or "?"
                lines.append(f"    {label}  <{ids}>")
        lines.append("")
    lines.append("=== Rest of the database ===")
    for cat, items in db.items():
        kind = kind_of(cat)
        missing = [(c, d) for c, d in items if profile.state(c, kind) == 0]
        lines.append(f"  {cat}: {len(items) - len(missing)}/{len(items)}")
        lines += [f"    missing: {d}  <{c}>" for c, d in missing]
    extra_u = sorted(u for u in profile.unlocks if u.lower() not in known_codes(db, "unlock"))
    extra_a = sorted(a for a in profile.achievements if a.lower() not in known_codes(db, "achievement"))
    lines += ["", f"=== In the profile but not in the database ({len(extra_u)} unlocks, {len(extra_a)} achievements) ==="]
    lines += [f"  unlock: {u}" for u in extra_u] + [f"  achievement: {a}" for a in extra_a]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out
