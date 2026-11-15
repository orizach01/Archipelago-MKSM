"""Vanilla: one region per area, the way the world was built before entrance
rando existed.

Four entry points, called from MKSMWorld's generation steps - see layouts/.
The areas are coarse on purpose: with the doors unshuffled, reaching any part of
an area means reaching all of it, so a single region per area says the same
thing as a graph of its rooms would.
"""
from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from BaseClasses import Region
from rule_builder.rules import AtLeast, Rule, CanReachRegion

from .. import locations, rules
from ..consts import (SWING, LONG_JUMP, WALL_CLIMB, WALL_JUMP, WALL_RUN,
                      DOUBLE_JUMP, FIST_OF_RUIN)
from ..items import MKSMItem
from ..locations import (MKSMLocation, REGION_NAME_LOCATIONS,
                         SMOKE_MISSION_LOCATIONS)
from ..options import BossGoal
from ..rules import ANY_PROJECTILE_MOVE, FOUNDRY_RULE, WU_SHI_RULE

if TYPE_CHECKING:
    from ..world import MKSMWorld


# One region per area, so "can reach the Tombs" is just that region.
SMOKE_1: Rule = CanReachRegion("Tombs")
SMOKE_2: Rule = SMOKE_1 & CanReachRegion("Wu-Shi") & FIST_OF_RUIN
SMOKE_3: Rule = SMOKE_2 & CanReachRegion("Tombs")
SMOKE_4: Rule = SMOKE_3 & CanReachRegion("Monastery")
SMOKE_5: Rule = SMOKE_4

# The shop tiers count how many of these five are open: 0, 2, 3 and 5 of them.
# With the doors unshuffled, that tracks how far into the game you are, and so
# roughly how much EXP you have had the chance to earn.
PURCHASE_AREAS = tuple(CanReachRegion(name) for name in
                       ("Monastery", "Forest", "Tombs", "Netherrealm", "Wasteland 1"))


def _tier_rule(tier: int) -> Rule:
    return AtLeast(tier, *PURCHASE_AREAS)

# Smoke is met in the Forest
SMOKE_MISSION_REGION = "Forest"


def create_regions(world: MKSMWorld) -> None:
    player, multiworld = world.player, world.multiworld
    region = partial(Region, player=player, multiworld=multiworld)

    menu = region("Menu")
    goros_lair_1 = region("Goro's Lair 1")
    goros_lair_2 = region("Goro's Lair 2")
    goros_lair_boss = region("Goro's Lair - Boss arena")
    wu_shi = region("Wu-Shi")
    wu_shi_ermac = region("Wu-Shi - Ermac arena")
    wu_shi_fire = region("Wu-Shi - Fire")
    wu_shi_wallrun = region("Wu-Shi - Wall Run area")
    portal_1 = region("Portal 1")
    portal_2 = region("Portal 2")
    monastery = region("Monastery")
    monastery_kitana = region("Monastery - Kitana arena")
    forest = region("Forest")
    forest_bridges = region("Forest - Bridges")
    forest_reptile = region("Forest - Reptile arena")
    tombs = region("Tombs")
    tombs_baraka = region("Tombs - Baraka arena")
    wasteland_1 = region("Wasteland 1")
    wasteland_2 = region("Wasteland 2")
    wasteland_3 = region("Wasteland 3")
    dead_pool = region("Dead Pool")
    netherrealm = region("Netherrealm")
    foundry = region("Foundry")

    regions = [
        menu,
        goros_lair_1,
        goros_lair_2,
        goros_lair_boss,
        wu_shi,
        wu_shi_ermac,
        wu_shi_fire,
        wu_shi_wallrun,
        portal_1,
        portal_2,
        monastery,
        monastery_kitana,
        forest,
        forest_bridges,
        forest_reptile,
        tombs,
        tombs_baraka,
        wasteland_1,
        wasteland_2,
        wasteland_3,
        dead_pool,
        netherrealm,
        foundry,
    ]

    world.multiworld.regions += regions

def create_locations(world: MKSMWorld) -> None:
    for region_name, region_locations in REGION_NAME_LOCATIONS.items():
        world.get_region(region_name).add_locations(region_locations, MKSMLocation)

    if world.options.smoke_missions:
        world.get_region(SMOKE_MISSION_REGION).add_locations(
            SMOKE_MISSION_LOCATIONS, MKSMLocation)

    locations.create_shared_locations(world)
    _create_events(world)


def _create_events(world: MKSMWorld) -> None:
    wu_shi_ermac: Region = world.get_region("Wu-Shi - Ermac arena")
    monastery_kitana: Region = world.get_region("Monastery - Kitana arena")
    forest_reptile: Region = world.get_region("Forest - Reptile arena")
    forest_bridges: Region = world.get_region("Forest - Bridges")
    tombs_baraka: Region = world.get_region("Tombs - Baraka arena")
    wasteland_3: Region = world.get_region("Wasteland 3")
    netherrealm: Region = world.get_region("Netherrealm")
    foundry: Region = world.get_region("Foundry")

    if world.options.boss_goal >= BossGoal.option_shao_kahn_only:
        foundry.add_event(
            location_name="Shao Kahn defeated event",
            item_name="Shao Kahn defeated",
            location_type=MKSMLocation,
            item_type=MKSMItem,
            show_in_spoiler=False
        )

    if world.options.boss_goal >= BossGoal.option_main_bosses or not world.options.randomize_tournament_victories:
        monastery_kitana.add_event(
            location_name="Kitana defeated event",
            item_name="Kitana defeated",
            location_type=MKSMLocation,
            item_type=MKSMItem,
            show_in_spoiler=False
        )

        forest_reptile.add_event(
            location_name="Reptile defeated event",
            item_name="Reptile defeated",
            location_type=MKSMLocation,
            item_type=MKSMItem,
            show_in_spoiler=False
        )

        tombs_baraka.add_event(
            location_name="Baraka defeated event",
            item_name="Baraka defeated",
            location_type=MKSMLocation,
            item_type=MKSMItem,
            show_in_spoiler=False

        )

        wasteland_3.add_event(
            location_name="Goro defeated event",
            item_name="Goro defeated",
            location_type=MKSMLocation,
            item_type=MKSMItem,
            show_in_spoiler=False

        )

        netherrealm.add_event(
            location_name="Scorpion defeated event",
            item_name="Scorpion defeated",
            location_type=MKSMLocation,
            item_type=MKSMItem,
            show_in_spoiler=False

        )

    if world.options.boss_goal >= BossGoal.option_main_and_secret_bosses:
        wu_shi_ermac.add_event(
            location_name="Ermac defeated event",
            item_name="Ermac defeated",
            location_type=MKSMLocation,
            item_type=MKSMItem,
            show_in_spoiler=False
        )

        forest_bridges.add_event(
            location_name="Mileena defeated event",
            item_name="Mileena defeated",
            location_type=MKSMLocation,
            item_type=MKSMItem,
            show_in_spoiler=False
        )

        foundry.add_event(
            location_name="Kano defeated event",
            item_name="Kano defeated",
            location_type=MKSMLocation,
            item_type=MKSMItem,
            show_in_spoiler=False
        )

def connect(world: MKSMWorld) -> None:
    """Wire the flat region set.

    Every rule here is item logic, so none of it needs a region or a location to
    have been looked up first - which is why this can run in create_regions now
    rather than during set_rules, where it used to live.
    """
    menu = world.get_region("Menu")
    goros_lair_1 = world.get_region("Goro's Lair 1")
    goros_lair_2 = world.get_region("Goro's Lair 2")
    goros_lair_boss = world.get_region("Goro's Lair - Boss arena")
    wu_shi = world.get_region("Wu-Shi")
    wu_shi_ermac = world.get_region("Wu-Shi - Ermac arena")
    wu_shi_fire = world.get_region("Wu-Shi - Fire")
    wu_shi_wallrun = world.get_region("Wu-Shi - Wall Run area")
    portal_1 = world.get_region("Portal 1")
    portal_2 = world.get_region("Portal 2")
    monastery = world.get_region("Monastery")
    monastery_kitana = world.get_region("Monastery - Kitana arena")
    forest = world.get_region("Forest")
    forest_bridges = world.get_region("Forest - Bridges")
    forest_reptile = world.get_region("Forest - Reptile arena")
    tombs = world.get_region("Tombs")
    tombs_baraka = world.get_region("Tombs - Baraka arena")
    wasteland_1 = world.get_region("Wasteland 1")
    wasteland_2 = world.get_region("Wasteland 2")
    wasteland_3 = world.get_region("Wasteland 3")
    dead_pool = world.get_region("Dead Pool")
    netherrealm = world.get_region("Netherrealm")
    foundry = world.get_region("Foundry")

    if world.options.portal_start:
        menu.connect(portal_1)
    else:
        menu.connect(goros_lair_1)

    goros_lair_1.connect(goros_lair_boss)
    goros_lair_1.connect(goros_lair_2, rule=LONG_JUMP | DOUBLE_JUMP)
    goros_lair_2.connect(wu_shi)
    goros_lair_2.connect(goros_lair_boss)
    goros_lair_boss.connect(goros_lair_1, rule=LONG_JUMP | DOUBLE_JUMP)

    wu_shi.connect(wu_shi_ermac, rule=FIST_OF_RUIN & SWING)
    wu_shi.connect(wu_shi_fire)
    wu_shi_fire.connect(wu_shi_wallrun, rule=FIST_OF_RUIN)
    wu_shi.connect(portal_1)
    wu_shi.connect(goros_lair_2, rule=FIST_OF_RUIN)

    portal_1.connect(wu_shi, rule=WU_SHI_RULE)
    portal_1.connect(portal_2)

    portal_2.connect(netherrealm, rule=SWING & (DOUBLE_JUMP | WALL_RUN))

    portal_1.connect(forest, rule=FIST_OF_RUIN)
    forest.connect(forest_bridges, rule=SWING & WALL_CLIMB)
    forest.connect(forest_reptile, rule=LONG_JUMP | DOUBLE_JUMP)

    portal_2.connect(wasteland_1, rule=WALL_CLIMB & (WALL_JUMP | (WALL_RUN & DOUBLE_JUMP)))
    wasteland_1.connect(wasteland_2, rule=FIST_OF_RUIN)
    wasteland_2.connect(wasteland_3, rule=WALL_RUN)
    wasteland_2.connect(dead_pool)

    portal_1.connect(tombs, rule=WALL_CLIMB)
    tombs.connect(tombs_baraka, rule=FIST_OF_RUIN & ANY_PROJECTILE_MOVE)
    tombs_baraka.connect(wu_shi)

    portal_1.connect(monastery, rule=DOUBLE_JUMP | LONG_JUMP)
    monastery.connect(monastery_kitana)

    portal_2.connect(
        foundry,
        rule=FOUNDRY_RULE,
    )


def set_rules(world: MKSMWorld) -> None:
    """The rules that name regions. Everything else is in rules.py."""
    rules.set_purchase_rules(world, _tier_rule)
    rules.set_smoke_mission_rules(world, (SMOKE_1, SMOKE_2, SMOKE_3, SMOKE_4, SMOKE_5))


def connect_entrances(world: MKSMWorld) -> None:
    """Nothing to shuffle - the doors are where the game put them."""
    world.entrance_redirects = {}
