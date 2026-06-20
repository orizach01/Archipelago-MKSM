from __future__ import annotations

from typing import TYPE_CHECKING

from BaseClasses import Location, Region, LocationProgressType
from .items import MKSMItem

if TYPE_CHECKING:
    from .world import MKSMWorld

REGION_NAME_LOCATIONS = {
    "Goro's Lair 1": {
        "GL: koin inside the skeleton": 1,
        "GL: koin above the doorway": 2,
        "GL: koin from shooting the moon": 3,
        "GL: koin on the ledge after the pit": 4,
        "GL: koin from the chandelier": 5,
        "GL: koin above the breakable door": 6,
    },
    "Goro's Lair - Boss arena": {
        "GL: Oni Warlord defeated": 7,
        "GL: long jump obtained": 8,
    },
    "Goro's Lair 2": {
        "GL: koin on the ledge after the broken bridge": 9
    },
    "Wu-Shi": {
        "WSA: koin from the catapult": 10,
        "WSA: koin after the tree branch swing": 11,
        "WSA: koin after the bamboo swing": 12,
        "WSA: koin on a high wall near the lava pots": 13,
        "WSA: wu-shi academy health upgrade": 14
    },
    "Wu-Shi - Ermac arena": {
        "WSA: koin from defeating Ermac": 15,
        "WSA: Ermac defeated": 16
    },
    "Wu-Shi - Fire": {
        "WSA: koin in the small room": 17
    },
    "Wu-Shi - Wall Run area": {
        "WSA: wall run obtained": 18
    },
    "Portal 2": {
        "P: koin from performing a fatality on the dragon symbol": 19
    },
    "Netherrealm": {
        "N: koin above the arch": 20,
        "N: Scorpion defeated": 21
    },
    "Forest": {
        "LF: koin behind the breakable wall": 22,
        "LF: koin behind the living tree": 23,
        "LF: koin hidden behind the waterfall": 24,
        "LF: koin near the giant snake head": 25,
        "LF: koin from shooting the closed eye": 26,
        "LF: Forest health upgrade": 27
    },
    "Forest - Bridges": {
        "LF: koin from shooting at dragon koin": 28,
        "LF: koin from defeating Mileena": 29,
        "LF: Mileena defeated": 30
    },
    "Forest - Reptile arena": {
        "LF: koin from breaking the fast statues": 31,
        "LF: Reptile defeated": 32,
        "LF: climb obtained": 33,
    },
    "Wasteland 1": {
        "W: koin from impaling an enemy on the big spike": 34,
        "W: koin on the ledge above": 35,
        "W: koin found after freeing kabal": 36,
        "W: koin from defeating the Oni Warlord in the blood bath room": 37,
        "W: koin found on the lion statue": 38,
        "W: Kabal freed": 39,
        "W: Wasteland health upgrade": 40,
        "W: Sub-Zero defeated": 41,
    },
    "Wasteland 2": {
        "W: koin found above the spike wheel": 42
    },
    "Wasteland 3": {
        "W: koin from shooting the dragon koin": 43,
        "W: koin from goro's arena": 44,
        "W: Goro defeated": 45,
        "W: Double jump obtained": 46
    },
    "Dead Pool": {
        "DP: koin from drowning enemies in both pools": 47,
        "DP: swing obtained": 48
    },
    "Tombs": {
        "ST: koin from shooting the dragon koin near the portal": 49,
        "ST: koin above Baraka's entrance": 50,
        "ST: koin from using all three death traps": 51,
        "ST: koin from the broken statue": 52,
        "ST: koin above the broken statue": 53,
        "ST: koin from high button in the rolling spikes room": 54,
        "ST: koin above the ceiling in the room with the hooks": 55,
        "ST: koin from shooting the dragon koin in the test your might room": 56,
        "ST: koin from killing the strolling skeleton": 57,
        "ST: koin from the button after defeating orochi hellbeast": 58,
        "ST: koin from impaling an enemy on the rising spikes": 59,
        "ST: koin from launching a tarkata on the flying bird": 60,
        "ST: koin behind statue in the falling spike trap room": 61,
        "ST: koin above broken statue in the falling spike trap room": 62,
        "ST: koin near the fan": 63,
        "ST: koin from the destroyed soul tomb": 64,
    },
    "Tombs - Baraka arena": {
        "ST: Baraka defeated": 65,
        "ST: wall jump obtained": 66
    },
    "Monastery": {
        "EM: koin from shooting the dragon koin behind the window": 67,
        "EM: koin from impaling enemies on the statue's hands": 68,
        "EM: koin above the ceiling in the multality room": 69,
    },
    "Monastery - Kitana arena": {
        "EM: koin from the Kitana Mileena and Jade arena": 70,
        "EM: Kitana Mileena and Jade defeated": 71,
        "EM: Fist of Ruin obtained": 72,
    },
    "Foundry": {
        "F: koin from wall jumping above the main room": 73,
        "F: koin above the wood ceiling": 74,
        "F: koin from breaking the big pot": 75,
        "F: koin behind the fire": 76,
        "F: koin from shooting the dragon koin behind the breakable wall": 77,
        "F: koin above the lava pit": 78,
        "F: koin from smash an enemy with the big hammers": 79,
        "F: koin from breaking the pipe with the axe": 80,
        "F: Kano defeated": 81,
        "F: Shao Kahn defeated": 82,
    }
}

LOCATION_NAME_TO_ID = {loc: loc_id for k, v in REGION_NAME_LOCATIONS.items() for loc, loc_id in v.items()}


class MKSMLocation(Location):
    game = "Mortal Kombat: Shaolin Monks"


def create_all_locations(world: MKSMWorld) -> None:
    create_region_locations(world)
    create_event_locations(world)

    world.get_location("GL: koin above the doorway").progress_type = LocationProgressType.EXCLUDED
    world.get_location("GL: koin above the breakable door").progress_type = LocationProgressType.EXCLUDED


def create_region_locations(world: MKSMWorld) -> None:
    for region_name in REGION_NAME_LOCATIONS:
        region = world.get_region(region_name)
        region.add_locations(REGION_NAME_LOCATIONS[region_name], MKSMLocation)


def create_event_locations(world: MKSMWorld) -> None:
    monastery_kitana: Region = world.get_region("Monastery - Kitana arena")
    forest_reptile: Region = world.get_region("Forest - Reptile arena")
    tombs_baraka: Region = world.get_region("Tombs - Baraka arena")
    wasteland_3: Region = world.get_region("Wasteland 3")
    dead_pool: Region = world.get_region("Dead Pool")
    netherrealm: Region = world.get_region("Netherrealm")
    foundry: Region = world.get_region("Foundry")

    monastery_kitana.add_event(
        location_name="Kitana defeated event",
        item_name="Kitana defeated item",
        location_type=MKSMLocation,
        item_type=MKSMItem,
    )

    forest_reptile.add_event(
        location_name="Reptile defeated event",
        item_name="Reptile defeated item",
        location_type=MKSMLocation,
        item_type=MKSMItem,
    )

    tombs_baraka.add_event(
        location_name="Baraka defeated event",
        item_name="Baraka defeated item",
        location_type=MKSMLocation,
        item_type=MKSMItem,
    )

    wasteland_3.add_event(
        location_name="Goro defeated event",
        item_name="Goro defeated item",
        location_type=MKSMLocation,
        item_type=MKSMItem,
    )

    netherrealm.add_event(
        location_name="Scorpion defeated event",
        item_name="Scorpion defeated item",
        location_type=MKSMLocation,
        item_type=MKSMItem,
    )

    foundry.add_event(
        location_name="Shao Kahn defeated event",
        item_name="Shao Kahn defeated item",
        location_type=MKSMLocation,
        item_type=MKSMItem,
    )

    dead_pool.add_event(
        location_name="Dead Pool event",
        item_name="Dead Pool item",
        location_type=MKSMLocation,
        item_type=MKSMItem,
    )
