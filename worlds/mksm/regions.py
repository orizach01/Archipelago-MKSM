from __future__ import annotations

from typing import TYPE_CHECKING
from functools import partial

from BaseClasses import Entrance, Region

if TYPE_CHECKING:
    from .world import MKSMWorld


def create_all_regions(world: MKSMWorld) -> None:
    player, multiworld = world.player, world.multiworld
    create_region = partial(Region, player=player, multiworld=multiworld)

    menu = create_region("Menu")
    goros_lair_1 = create_region("Goro's Lair 1")
    goros_lair_2 = create_region("Goro's Lair 2")
    goros_lair_boss = create_region("Goro's Lair - Boss arena")
    wu_shi = create_region("Wu-Shi")
    wu_shi_ermac = create_region("Wu-Shi - Ermac arena")
    wu_shi_fire = create_region("Wu-Shi - Fire")
    wu_shi_wallrun = create_region("Wu-Shi - Wall Run area")
    portal_1 = create_region("Portal 1")
    portal_2 = create_region("Portal 2")
    monastery = create_region("Monastery")
    monastery_kitana = create_region("Monastery - Kitana arena")
    forest = create_region("Forest")
    forest_bridges = create_region("Forest - Bridges")
    forest_reptile = create_region("Forest - Reptile arena")
    tombs = create_region("Tombs")
    tombs_baraka = create_region("Tombs - Baraka arena")
    wasteland_1 = create_region("Wasteland 1")
    wasteland_2 = create_region("Wasteland 2")
    wasteland_3 = create_region("Wasteland 3")
    dead_pool = create_region("Dead Pool")
    netherrealm = create_region("Netherrealm")
    foundry = create_region("Foundry")

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
