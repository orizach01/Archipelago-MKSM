"""Entrance rando: one region per room, so a door can be rewired to any other.

Four entry points, called from MKSMWorld's generation steps - see layouts/.
The room graph is built here in full, with its vanilla destinations; shuffling
happens later, in connect_entrances, which needs a complete graph with its
rules already attached.
"""
from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Iterable, Optional

from BaseClasses import EntranceType, Region
from entrance_rando import (EntranceRandomizationError,
                            disconnect_entrance_for_randomization, randomize_entrances)
from rule_builder.rules import AtLeast, Rule, Has, CanReachRegion, Or

from .. import locations, rules
from ..entrance_doors import DOOR_OBJECTS
from ..consts import (SWING, LONG_JUMP, WALL_CLIMB, WALL_JUMP, WALL_RUN,
                      DOUBLE_JUMP, FIST_OF_RUIN)
from ..locations import SMOKE_MISSION_LOCATIONS, event
from ..rules import LAUNCHING_THROW, FOUNDRY_RULE, ANY_PROJECTILE_MOVE

if TYPE_CHECKING:
    from ..world import MKSMWorld


# Rooms are regions here, so "can reach the Tombs" is "can reach one of these".
# Mind vanilla's splits when filling these in: its "Tombs" and "Tombs - Baraka
# arena" are different regions, and Wu-Shi is four, so a room's name prefix does
# not say which area rule it belongs to.
def _any(*regions: str) -> Rule:
    return Or(*(CanReachRegion(r) for r in regions))


# Same chain as vanilla, spelled in rooms. An empty area above makes its rule
# always_false, so an unfilled area claims nothing rather than guessing.
SMOKE_1: Rule = CanReachRegion("Tombs (0x05)")
SMOKE_2: Rule = SMOKE_1 & CanReachRegion("Wu-Shi (0x6c) entrance")
SMOKE_3: Rule = SMOKE_2 & CanReachRegion("Tombs (0x14)")
SMOKE_4: Rule = SMOKE_3 & CanReachRegion("Portal (0xc0) monastery")
SMOKE_5: Rule = SMOKE_4

# Vanilla prices the shop by how many of five areas are open - 0, 2, 3 and 5 of
# them, so 0%, 40%, 60% and 100%. Areas stop meaning that once doors are
# shuffled: one of them can drop you in the Monastery in the first minute, so
# "five areas open" no longer says anything about how much of the game you have
# played. The count of rooms you can reach does, so the same four tiers are
# re-based on rooms.
#
# Solved, not read off: walking the playthrough sphere by sphere over 20 vanilla
# seeds, vanilla's tiers open once 15%, 31% and 50% of the progression items are
# in hand. These are the room counts whose median opening moment matches that,
# across 30 shuffled seeds - 21 rooms lands on 0.15 and 39 on 0.27. The solver
# put tier 5 at 51; it is 45 here instead, because the room curve flattens at
# the end - every seed opens all 66 eventually, and the last few arrive past
# 0.75 - so a high threshold drags that tier later than vanilla's 0.50.
#
# Taking the median room count at vanilla's moment instead gives 35/49/60, which
# opens far too late (0.28/0.52/0.78): a threshold is a requirement, so the
# median count is reached at the median moment or later, and rooms open fast
# early then plateau, which skews it further.
#
# No threshold here can strand a purchase: every seed measured had all 66 rooms
# reachable with the full item set, so a slow tier is only ever slow. Re-measure
# if the room graph changes shape.
PURCHASE_ROOM_TIERS = {0: 0, 2: 21, 3: 39, 5: 45}


def _rooms_reached(world: MKSMWorld, count: int) -> Rule:
    """At least `count` distinct rooms reachable.

    Built from world.reg rather than a list here, so it cannot drift from the
    region set. One child per ROOM, not per region: 0x21 is four regions and
    0x02 is two, and letting those count several times each would measure the
    logic model instead of the game.

    Only ever put this on a location. World.set_rule registers an entrance's
    indirect conditions from every region a rule names, so on an entrance this
    would register one per room and make that entrance re-tested every time any
    of them opens.
    """
    parts: dict = {}
    for (room, _part), region in world.reg.items():
        if room != "Menu":
            parts.setdefault(room, []).append(region.name)

    assert count <= len(parts), (
        f"purchase tier wants {count} rooms but there are only {len(parts)} - "
        f"AtLeast would quietly resolve to always-false and the shop checks "
        f"would be unreachable")

    return AtLeast(count, *(_any(*names) for names in parts.values()))


# Doors that stay vanilla, as the (room, spawn) mouths they sit in. Mirrors
# EXCLUDE in the client's shuffle_entrances.py, and for the same reasons: both
# halves of each pair are named, so neither can be shuffled on its own.
VANILLA_DOORS = {
    # 0x47 -> 0x49, the final boss room. One-way, and the only route to the goal.
    (0x47, 3),
    # 0xc2 <-> 0xc3 is the Kitana fight ending in a cutscene that moves you
    # between them. Not a door you walk through, so shuffling it would send the
    # cutscene somewhere it does not belong.
    (0xc2, 2), (0xc3, 1),
    # Portals that do not exist until you have TRAVELLED THROUGH THEM from the
    # far side - tested in game, not inferred. Shuffled, that is a trap with no
    # way out: the far end is lit only by walking the near one, so if the near
    # end lands somewhere only reachable through the far one, the portal is dead
    # forever and so is whatever is behind it.
    (0xc0, 7), (0xc2, 6),  # the monastery
    (0xc1, 5), (0x88, 4),  # Deadly Peaks
    (0x6a, 3), (0x0f, 2),  # Wu-Shi <-> Baraka
    # The Smoke-mission portal. It opens only after four missions are done, but
    # 0x4a is where mission 5 is completed, so a shuffled way in lets you finish
    # 5 before the rest and leaves the portal shut. 0x4a has only this mouth, so
    # the room is entirely outside the shuffle.
    (0x92, 2), (0x4a, 1),
}

# Where Smoke is met. The room, not the area.
SMOKE_MISSION_ROOM: tuple = (0x92, None)

# Which room each location sits in, as (room, part) keys into world.reg. The
# names and ids live in locations.REGION_NAME_LOCATIONS and are shared with
# vanilla - that table is the datapackage and must not vary by option - so this
# one holds names only. _check_placement keeps the two in step.
ROOM_LOCATIONS: dict[tuple, tuple[str, ...]] = {
    (0x00, None): (
        "ST: koin from impaling an enemy on the rising spikes",
    ),
    (0x01, None): (
        "ST: koin from launching a tarkata on the flying bird",
    ),
    (0x02, "top"): (
        "ST: koin near the fan",
    ),
    (0x03, "bottom"): (
        "ST: koin behind statue in the falling spike trap room",
        "ST: koin above broken statue in the falling spike trap room",
    ),
    (0x04, None): (
        "ST: koin from the destroyed soul tomb",
    ),
    (0x06, "main"): (
        "ST: koin above Baraka's entrance",
    ),
    (0x07, "entrance"): (
        "ST: koin from a high button in the rolling spikes room",
    ),
    (0x08, None): (
        "ST: koin from shooting the dragon koin in the test your might room",
    ),
    (0x0c, None): (
        "ST: koin from the button in Orochi hellbeast's room",
    ),
    (0x0f, None): (
        "ST: Baraka defeated",
        "ST: wall jump obtained",
    ),
    (0x11, None): (
        "ST: koin above the ceiling in the room with the hooks",
    ),
    (0x13, None): (
        "ST: koin from killing the strolling skeleton",
    ),
    (0x18, None): (
        "ST: koin from using all three death traps",
    ),
    (0x19, "top"): (
        "ST: koin from the broken statue",
        "ST: koin above the broken statue",
    ),
    (0x1e, None): (
        "ST: koin from shooting the dragon koin near the portal",
    ),
    (0x21, "bottom"): (
        "W: koin from impaling an enemy on the big spike",
    ),
    (0x21, "middle"): (
        "W: koin on the ledge above",
        "W: Wasteland health upgrade",
    ),
    (0x29, None): (
        "W: koin from defeating the Oni Warlord in the blood bath room",
    ),
    (0x2c, None): (
        "W: Sub-Zero defeated",
        "W: koin found on the lion statue",
    ),
    (0x2d, "top"): (
        "W: koin found above the spike wheel",
    ),
    (0x2e, "top"): (
        "W: koin from shooting the dragon koin",
    ),
    (0x2f, None): (
        "W: koin from Goro's arena",
        "W: Goro defeated",
        "W: Double jump obtained",
    ),
    (0x30, "top"): (
        "W: Kabal freed",
        "W: koin found after freeing kabal",
    ),
    (0x40, "entrance"): (
        "F: koin from wall jumping above the main room",
        "F: koin above the wood ceiling",
        "F: koin above the lava pit",
    ),
    (0x41, None): (
        "F: koin behind the fire",
    ),
    (0x42, "top"): (
        "F: koin from breaking the big pot",
    ),
    (0x43, "middle"): (
        "F: koin from shooting the dragon koin behind the breakable wall",
    ),
    (0x44, None): (
        "F: koin from smashing an enemy with the big hammers",
    ),
    (0x45, None): (
        "F: koin from breaking the pipe with the axe",
    ),
    (0x48, None): (
        "F: Kano defeated",
    ),
    (0x49, None): (
        "F: Shao Kahn defeated",
    ),
    (0x60, None): (
        "GL: koin inside the skeleton",
        "GL: koin above the doorway",
    ),
    (0x62, None): (
        "GL: koin from shooting the moon",
        "GL: koin on the ledge after the pit",
    ),
    (0x63, "main"): (
        "GL: koin from the chandelier",
    ),
    (0x63, "gate"): (
        "GL: koin behind the cage",
    ),
    (0x64, None): (
        "GL: koin above the breakable door",
    ),
    (0x65, "boss"): (
        "GL: Oni Warlord defeated",
        "GL: long jump obtained",
    ),
    (0x65, "exit"): (
        "GL: koin on the ledge after the broken bridge",
    ),
    (0x67, "entrance"): (
        "WSA: koin from the catapult",
        "WSA: koin next to the boulders",
    ),
    (0x68, "entrance"): (
        "WSA: koin on a high wall near the lava pots",
        "WSA: wu-shi academy health upgrade",
    ),
    (0x6a, "main"): (
        "WSA: koin in the small room",
    ),
    (0x6a, "wall-run"): (
        "WSA: wall run obtained",
    ),
    (0x6b, "main"): (
        "WSA: koin after the tree branch swing",
    ),
    (0x6b, "top"): (
        "WSA: koin after the bamboo swing",
    ),
    (0x6c, "shrine"): (
        "WSA: koin from defeating Ermac",
        "WSA: Ermac defeated",
    ),
    (0x6e, None): (
        "WSA: koin in the tree",
        "WSA: koin after the bridge",
    ),
    (0x81, "main"): (
        "LF: koin behind the breakable wall",
    ),
    (0x81, "waterfall"): (
        "LF: koin hidden behind the waterfall",
    ),
    (0x82, None): (
        "LF: koin behind the living tree",
    ),
    (0x84, None): (
        "LF: koin from shooting at dragon koin",
        "LF: koin from defeating Mileena",
        "LF: Mileena defeated",
    ),
    (0x88, "entrance"): (
        "DP: koin from drowning enemies in the pool",
        "DP: swing obtained",
    ),
    (0x89, None): (
        "LF: koin near the giant snake head",
        "LF: Forest health upgrade",
    ),
    (0x8e, None): (
        "LF: koin from breaking the fast statues",
    ),
    (0x8f, None): (
        "LF: koin from shooting the closed eye",
    ),
    (0x90, None): (
        "LF: Reptile defeated",
        "LF: climb obtained",
    ),
    (0x93, None): (
        "LF: koin near the waterfall",
        "LF: koin behind the rock",
    ),
    (0xa0, None): (
        "N: koin above the arch",
        "N: Scorpion defeated",
        "N: Medallion from defeating Scorpion",
    ),
    (0xc0, "main"): (
        "P: koin above the platform",
    ),
    (0xc1, "main"): (
        "P: koin from performing a fatality on the dragon symbol",
    ),
    (0xc2, "bottom"): (
        "EM: koin above the ceiling in the multality room",
    ),
    (0xc3, None): (
        "EM: koin from the Kitana Mileena and Jade arena",
        "EM: Kitana Mileena and Jade defeated",
        "EM: Fist of Ruin obtained",
    ),
    (0xc4, None): (
        "EM: koin from shooting the dragon koin behind the window",
    ),
    (0xc6, None): (
        "EM: koin from impaling enemies on the statue's hands",
    ),
    (0xc7, None): (
        "EM: koin from breaking the statue",
    ),
}


def create_region(world: MKSMWorld, room, part: Optional[str], name: str,
                  spawns: Iterable[int] = ()) -> Region:
    """Make a region and index it two ways.

    world.reg[room, part]     the region itself, for internal links between the
                              parts of a split room
    world.mouth[room, spawn]  which region each door mouth sits in, which is what
                              connections are actually between

    A room with one region lists all its spawns here; a split room lists each
    part's own spawns, so every (room, spawn) in entrance_pairs.json ends up
    pointing at exactly one region.

    `part` tells a room's regions apart - "bottom"/"top", "base"/"ledge" - and
    None is for a room that has only one. It is appended to `name`, so a split
    room is written with the same name twice and the parts name themselves:

        create_region(world, 0x02, "bottom", "Tombs (0x02)", (1, 2))
        create_region(world, 0x02, "top",    "Tombs (0x02)", (3,))
        -> "Tombs (0x02) bottom" and "Tombs (0x02) top"
    """
    assert (room, part) not in world.reg, (
        f"two regions share the key ({room!r}, {part!r}) - give each part of a "
        f"split room its own `part`, or the second silently replaces the first")
    r = Region(f"{name} {part}" if part else name,
               player=world.player, multiworld=world.multiworld)
    world.multiworld.regions.append(r)
    world.reg[room, part] = r
    for spawn in spawns:
        world.mouth[room, spawn] = r
    return r


def two_way(world: MKSMWorld, a: tuple, b: tuple,
            there: Optional[Rule] | bool = None,
            back: Optional[Rule] | bool = None) -> None:
    """Join two door mouths, both directions, named by the mouth.

    `a` and `b` are (room, spawn). Region.connect is one-directional, so a door
    needs both halves written - a missing reverse is invisible until generation
    places something behind a door you cannot come back through.

    The name is the mouth, not the destination: the destination moves when
    entrances are shuffled, the mouth does not. It matches entrance_pairs.json's
    key, so an entrance in a spoiler log maps straight onto a door.

    `there` and `back` are separate because a lock is usually one-sided - 0x00's
    sword door only bars the way out of 0x00, and 0x04 -> 0x00 opens freely.
    Each takes a rule, None for a free trip, or False for a direction that does
    not exist at all: 0x67 has no door back to 0x65, so the edge is left out
    rather than written as a locked one.
    """
    A, B = world.mouth[a], world.mouth[b]
    if there is not False:
        A.connect(B, name=f"{A.name}: exit {a[1]}", rule=there)
    if back is not False:
        B.connect(A, name=f"{B.name}: exit {b[1]}", rule=back)


def inside(world: MKSMWorld, room, a: Optional[str], b: Optional[str],
           there: Optional[Rule] | bool = None,
           back: Optional[Rule] | bool = None) -> None:
    """Link two parts of ONE room: a ledge, a drop, a gate.

    Not a door and never shuffled. randomize_entrances reshuffles entrances and
    cannot tell a ledge from a doorway, so these are named after their regions
    rather than after a mouth, which is what keeps them out of the pool.

    `there` is a -> b and `back` is b -> a. Each takes a rule, or None for a
    free link, or False for a direction that does not exist at all - plenty of
    internal links are one-way by geometry, and leaving the edge out is how AP
    is told so:

        inside(world, 0x02, "bottom", "top", there=FAN)        # drop back free
        inside(world, 0x21, "base", "ledge", there=CLIMB, back=False)
    """
    A, B = world.reg[room, a], world.reg[room, b]
    if there is not False:
        A.connect(B, name=f"{A.name} -> {B.name}", rule=there)
    if back is not False:
        B.connect(A, name=f"{B.name} -> {A.name}", rule=back)


def create_regions(world: MKSMWorld) -> None:
    """Every room as its own region, for randomize_entrances."""
    world.reg = {}
    world.mouth = {}

    create_region(world, "Menu", None, "Menu")
    create_region(world, 0x00, None, "Tombs (0x00)", (1, 2, 3))
    create_region(world, 0x01, None, "Tombs (0x01)", (1, 2))
    create_region(world, 0x02, "bottom", "Tombs (0x02)", (1, 2))
    create_region(world, 0x02, "top", "Tombs (0x02)", (3,))
    create_region(world, 0x03, "bottom", "Tombs (0x03)", (1,))
    create_region(world, 0x03, "top", "Tombs (0x03)", (2,))
    create_region(world, 0x04, None, "Tombs (0x04)", (1,))
    create_region(world, 0x05, None, "Tombs (0x05)", (1, 2))
    create_region(world, 0x06, "main", "Tombs (0x06)", (1, 2, 3))
    create_region(world, 0x06, "baraka", "Tombs (0x06)", (6,))
    create_region(world, 0x06, "smoke", "Tombs (0x06)", (5,))
    create_region(world, 0x07, "entrance", "Tombs (0x07)", (1,))
    create_region(world, 0x07, "exit", "Tombs (0x07)", (2,))
    create_region(world, 0x08, None, "Tombs (0x08)", (1,))
    create_region(world, 0x0c, None, "Tombs (0x0c)", (1,))
    create_region(world, 0x0f, None, "Tombs (0x0f)", (1, 2))
    create_region(world, 0x11, None, "Tombs (0x11)", (1, 2))
    create_region(world, 0x13, None, "Tombs (0x13)", (1, 2))
    create_region(world, 0x14, None, "Tombs (0x14)", (1,))
    create_region(world, 0x18, None, "Tombs (0x18)", (1, 2, 3))
    create_region(world, 0x19, "bottom", "Tombs (0x19)", (1,))
    create_region(world, 0x19, "top", "Tombs (0x19)", (2,))
    create_region(world, 0x1e, None, "Tombs (0x1e)", (1, 2))
    create_region(world, 0x21, "bottom", "Wastelands (0x21)", (1,))
    create_region(world, 0x21, "sub-zero", "Wastelands (0x21)", (2,))
    create_region(world, 0x21, "top", "Wastelands (0x21)", (4,))
    create_region(world, 0x21, "middle", "Wastelands (0x21)", (6,))
    create_region(world, 0x29, None, "Wastelands (0x29)", (1,))
    create_region(world, 0x2c, None, "Wastelands (0x2c)", (1, 2))
    create_region(world, 0x2d, "bottom", "Wastelands (0x2d)", (1,))
    create_region(world, 0x2d, "top", "Wastelands (0x2d)", (2,))
    create_region(world, 0x2e, "bottom", "Wastelands (0x2e)", (1, 3))
    create_region(world, 0x2e, "top", "Wastelands (0x2e)", (2,))
    create_region(world, 0x2f, None, "Wastelands (0x2f)", (1,))
    create_region(world, 0x30, "bottom", "Wastelands (0x30)", (1,))
    create_region(world, 0x30, "top", "Wastelands (0x30)")
    create_region(world, 0x40, "entrance", "Foundry (0x40)", (1, 2))
    create_region(world, 0x40, "exit", "Foundry (0x40)", (3,))
    create_region(world, 0x41, None, "Foundry (0x41)", (1, 2))
    create_region(world, 0x42, "bottom", "Foundry (0x42)", (1, 2, 4))
    create_region(world, 0x42, "top", "Foundry (0x42)", (3,))
    create_region(world, 0x43, "bottom", "Foundry (0x43)", (1,))
    create_region(world, 0x43, "middle", "Foundry (0x43)")
    create_region(world, 0x43, "top", "Foundry (0x43)", (2,))
    create_region(world, 0x44, None, "Foundry (0x44)", (1, 2))
    create_region(world, 0x45, None, "Foundry (0x45)", (1,))
    create_region(world, 0x47, None, "Foundry (0x47)", (1, 2, 3))
    create_region(world, 0x48, None, "Foundry (0x48)", (1,))
    create_region(world, 0x49, None, "Foundry (0x49)", (1,))
    create_region(world, 0x4a, None, "The Pit (0x4a)", (1,))
    create_region(world, 0x60, None, "Goro's Lair (0x60)", (4,))
    create_region(world, 0x62, None, "Goro's Lair (0x62)", (1, 2))
    create_region(world, 0x63, "main", "Goro's Lair (0x63)", (1, 2))
    create_region(world, 0x63, "gate", "Goro's Lair (0x63)", (3,))
    create_region(world, 0x64, None, "Goro's Lair (0x64)", (1, 2, 3))
    create_region(world, 0x65, "entrance", "Goro's Lair (0x65)", (1,))
    create_region(world, 0x65, "boss", "Goro's Lair (0x65)", )
    create_region(world, 0x65, "exit", "Goro's Lair (0x65)", (2,))
    create_region(world, 0x66, "entrance", "Goro's Lair (0x66)", (1,))
    create_region(world, 0x66, "exit", "Goro's Lair (0x66)", (2,))
    create_region(world, 0x67, "entrance", "Wu-Shi (0x67)")
    create_region(world, 0x67, "statue", "Wu-Shi (0x67)", (2,))
    create_region(world, 0x67, "exit", "Wu-Shi (0x67)", (3,))
    create_region(world, 0x68, "entrance", "Wu-Shi (0x68)", (1, 5))
    create_region(world, 0x68, "exit", "Wu-Shi (0x68)", (2,))
    create_region(world, 0x6a, "main", "Wu-Shi (0x6a)", (1, 3))
    create_region(world, 0x6a, "wall-run", "Wu-Shi (0x6a)")
    create_region(world, 0x6b, "main", "Wu-Shi (0x6b)", (1, 3))
    create_region(world, 0x6b, "statue", "Wu-Shi (0x6b)", (4,))
    create_region(world, 0x6b, "top", "Wu-Shi (0x6b)", (2,))
    create_region(world, 0x6c, "entrance", "Wu-Shi (0x6c)", (1,))
    create_region(world, 0x6c, "shrine", "Wu-Shi (0x6c)")
    create_region(world, 0x6e, None, "Wu-Shi (0x6e)", (1,))
    create_region(world, 0x80, "main", "Forest (0x80)", (2,))
    create_region(world, 0x80, "statue", "Forest (0x80)", (1,))
    create_region(world, 0x80, "top", "Forest (0x80)", (3,))
    create_region(world, 0x81, "main", "Forest (0x81)", (1, 2))
    create_region(world, 0x81, "waterfall", "Forest (0x81)")
    create_region(world, 0x82, None, "Forest (0x82)", (1, 2, 3))
    create_region(world, 0x84, None, "Forest (0x84)", (1,))
    create_region(world, 0x88, "entrance", "Dead Pool (0x88)", (0,))
    create_region(world, 0x88, "door", "Dead Pool (0x88)")
    create_region(world, 0x88, "exit", "Dead Pool (0x88)", (4,))
    create_region(world, 0x89, None, "Forest (0x89)", (1, 3))
    create_region(world, 0x8e, None, "Forest (0x8e)", (1, 2, 3))
    create_region(world, 0x8f, None, "Forest (0x8f)", (1, 2))
    create_region(world, 0x90, None, "Forest (0x90)", (1,))
    create_region(world, 0x92, None, "Forest (0x92)", (1, 2))
    create_region(world, 0x93, None, "Forest (0x93)", (1,))
    create_region(world, 0xa0, None, "Netherrealm (0xa0)", (1,))
    create_region(world, 0xc0, "main", "Portal (0xc0)", (1, 4, 5))
    create_region(world, 0xc0, "monastery", "Portal (0xc0)", (2, 7))
    create_region(world, 0xc0, "tombs", "Portal (0xc0)", (3,))
    create_region(world, 0xc1, "main", "Portal (0xc1)", (1,))
    create_region(world, 0xc1, "wastelands", "Portal (0xc1)", (4, 5))
    create_region(world, 0xc1, "netherrealm", "Portal (0xc1)", (2,))
    create_region(world, 0xc1, "foundry", "Portal (0xc1)", (3,))
    create_region(world, 0xc2, "bottom", "Monastery (0xc2)", (1, 6))
    create_region(world, 0xc2, "top", "Monastery (0xc2)", (2,))
    create_region(world, 0xc3, None, "Monastery (0xc3)", (1,))
    create_region(world, 0xc4, None, "Monastery (0xc4)", (1, 2))
    create_region(world, 0xc5, None, "Monastery (0xc5)", (1, 2, 3))
    create_region(world, 0xc6, None, "Monastery (0xc6)", (1, 2))
    create_region(world, 0xc7, None, "Monastery (0xc7)", (1,))


def _check_placement(world: MKSMWorld) -> None:
    """Every location in exactly one real room.

    ROOM_LOCATIONS holds names only - the ids come from the shared table - so
    the two can drift apart without Python noticing. They must not: a name
    placed in no room is a check the seed would silently be missing, and the
    other three mistakes surface much later, from AP, with far less to say.
    """
    expected = {n for names in locations.REGION_NAME_LOCATIONS.values() for n in names}
    placed = Counter(n for names in ROOM_LOCATIONS.values() for n in names)

    problems = []
    for label, names in (
            ("placed in no room", sorted(expected - set(placed))),
            ("placed in more than one", sorted(n for n, c in placed.items() if c > 1)),
            ("not a location", sorted(set(placed) - expected)),
    ):
        if names:
            problems.append(f"{len(names)} {label}: {names}")
    unknown_keys = [k for k in ROOM_LOCATIONS if k not in world.reg]
    if unknown_keys:
        problems.append(f"{len(unknown_keys)} key(s) with no region: {unknown_keys}")

    if problems:
        raise ValueError("ROOM_LOCATIONS in worlds/mksm/layouts/er.py - "
                         + "; ".join(problems))


def create_locations(world: MKSMWorld) -> None:
    """Locations and events, in the room each one is actually in."""
    _check_placement(world)

    for key, names in ROOM_LOCATIONS.items():
        locations.add_named(world.reg[key], names)

    if world.options.smoke_missions:
        world.reg[SMOKE_MISSION_ROOM].add_locations(
            SMOKE_MISSION_LOCATIONS, locations.MKSMLocation)

    locations.create_shared_locations(world)
    _create_events(world)


def _create_events(world: MKSMWorld) -> None:
    event(world.reg[0x02, "top"], "Tombs sword button")
    event(world.reg[0x02, "top"], "Tombs fan destroyed")
    event(world.reg[0x04, None], "Tombs soul tomb destroyed", rule=FIST_OF_RUIN)
    event(world.reg[0x07, "entrance"], "Tombs spike walls lowered")
    event(world.reg[0x08, None], "Tombs Orochi door opened")
    event(world.reg[0x0c, None], "Tombs Orochi Hellbeast defeated")
    event(world.reg[0x0f, None], "Baraka defeated")
    event(world.reg[0x21, "middle"], "Wastelands middle junk cleared",
          rule=WALL_CLIMB)
    event(world.reg[0x21, "top"], "Wastelands top junk cleared",
          rule=WALL_CLIMB & (WALL_JUMP | (WALL_RUN & DOUBLE_JUMP)))
    event(world.reg[0x29, None], "Wastelands gate opened")
    event(world.reg[0x2c, None], "Sub-Zero defeated")
    event(world.reg[0x2f, None], "Goro defeated")
    event(world.reg[0x40, "entrance"], "Foundry main room gate opened")
    event(world.reg[0x43, "middle"], "Foundry Orochi room top door opened")
    event(world.reg[0x44, None], "Foundry hammer room cleared",
          rule=Has("Foundry Orochi room top door opened"))
    event(world.reg[0x48, None], "Kano defeated")
    event(world.reg[0x49, None], "Shao Kahn defeated")
    event(world.reg[0x66, "entrance"], "Goro's Lair bells rung")
    event(world.reg[0x67, "entrance"], "Wu-Shi blockade destroyed")
    event(world.reg[0x68, "entrance"], "Wu-Shi lava pots dropped")
    event(world.reg[0x6a, "main"], "Wu-Shi fire cleared")
    event(world.reg[0x6b, "main"], "Wu-Shi statue destroyed", rule=FIST_OF_RUIN)
    event(world.reg[0x6c, "shrine"], "Ermac defeated")
    event(world.reg[0x80, "main"], "Forest first tree fed")
    event(world.reg[0x80, "main"], "Forest bramble cleared")
    event(world.reg[0x81, "main"], "Forest second tree fed")
    event(world.reg[0x82, None], "Forest pillar destroyed")
    event(world.reg[0x84, None], "Mileena defeated")
    event(world.reg[0x88, "entrance"], "Dead Pool cleared")
    event(world.reg[0x89, None], "Forest third tree fed")
    event(world.reg[0x90, None], "Reptile defeated")
    event(world.reg[0xa0, None], "Scorpion defeated")
    event(world.reg[0xc2, "bottom"], "Monastery statue destroyed", rule=FIST_OF_RUIN)
    event(world.reg[0xc3, None], "Kitana defeated")


def connect(world: MKSMWorld) -> None:
    """The vanilla door graph. Runs in create_regions, not set_rules.

    Three stages, three jobs: topology here, access rules in set_rules, and the
    shuffle in connect_entrances - which is the hook randomize_entrances goes in,
    and it needs a complete graph with its rules already attached.
    """
    menu = world.reg["Menu", None]
    menu.connect(world.reg[0xc0, "main"])

    two_way(world, (0x00, 3), (0x01, 1))
    two_way(world, (0x00, 2), (0x04, 1), there=Has("Tombs sword button"))
    two_way(world, (0x00, 1), (0x05, 2))
    two_way(world, (0x01, 2), (0x02, 1))
    inside(world, 0x02, "bottom", "top", there=Has("Tombs fan destroyed"))
    two_way(world, (0x02, 2), (0x03, 1))
    two_way(world, (0x02, 3), (0x03, 2))
    inside(world, 0x03, "bottom", "top", there=LAUNCHING_THROW)
    two_way(world, (0x05, 1), (0x06, 3))
    inside(world, 0x06, "main", "smoke", there=SMOKE_2, back=SMOKE_2)
    inside(world, 0x06, "main", "baraka",
           there=Has("Tombs soul tomb destroyed") & Has("Tombs Orochi Hellbeast defeated"),
           back=Has("Tombs soul tomb destroyed") & Has("Tombs Orochi Hellbeast defeated")
           )
    two_way(world, (0x06, 1), (0x1e, 2))
    two_way(world, (0x06, 2), (0x18, 3))
    two_way(world, (0x06, 5), (0x14, 1))
    two_way(world, (0x06, 6), (0x0f, 1), there=ANY_PROJECTILE_MOVE)
    inside(world, 0x07, "entrance", "exit", back=Has("Tombs spike walls lowered"))
    two_way(world, (0x07, 1), (0x19, 2))
    two_way(world, (0x07, 2), (0x11, 2))
    two_way(world, (0x08, 1), (0x11, 1))
    two_way(world, (0x0c, 1), (0x13, 1), back=Has("Tombs Orochi door opened"))
    two_way(world, (0x0f, 2), (0x6a, 3), there=Has("Baraka defeated"), back=Has("Baraka defeated"))
    two_way(world, (0x13, 2), (0x18, 2))
    two_way(world, (0x18, 1), (0x19, 1))
    inside(world, 0x19, "bottom", "top", there=WALL_CLIMB)
    two_way(world, (0x1e, 1), (0xc0, 3))
    inside(world, 0x21, "bottom", "sub-zero",
           there=Has("Wastelands gate opened"), back=Has("Wastelands gate opened")
           )
    inside(world, 0x21, "bottom", "middle", there=WALL_CLIMB)
    inside(world, 0x21, "middle", "top", there=WALL_JUMP | (WALL_RUN & DOUBLE_JUMP))
    two_way(world, (0x21, 1), (0xc1, 4))
    two_way(world, (0x21, 2), (0x2c, 1), there=FIST_OF_RUIN, back=FIST_OF_RUIN)
    two_way(world, (0x21, 4), (0x30, 1),
            there=Has("Wastelands top junk cleared"),
            back=Has("Wastelands top junk cleared")
            )
    two_way(world, (0x21, 6), (0x29, 1),
            there=Has("Wastelands middle junk cleared"))
    two_way(world, (0x2c, 2), (0x2d, 1), there=FIST_OF_RUIN, back=FIST_OF_RUIN)
    inside(world, 0x2d, "bottom", "top", there=WALL_CLIMB)
    two_way(world, (0x2d, 2), (0x2e, 1))
    inside(world, 0x2e, "bottom", "top", there=WALL_RUN)
    two_way(world, (0x2e, 2), (0x2f, 1))
    two_way(world, (0x2e, 3), (0x88, 0))
    inside(world, 0x30, "bottom", "top", there=WALL_CLIMB)
    inside(world, 0x40, "entrance", "exit", back=Has("Foundry main room gate opened"))
    two_way(world, (0x40, 1), (0xc1, 3))
    two_way(world, (0x40, 2), (0x42, 2))
    two_way(world, (0x40, 3), (0x47, 1))
    two_way(world, (0x41, 1), (0x43, 1))
    two_way(world, (0x41, 2), (0x42, 1))
    inside(world, 0x42, "bottom", "top", there=WALL_CLIMB)
    two_way(world, (0x42, 3), (0x45, 1), there=Has("Foundry hammer room cleared"))
    two_way(world, (0x42, 4), (0x44, 2), there=Has("Foundry hammer room cleared"))
    inside(world, 0x43, "bottom", "middle", there=LAUNCHING_THROW & WALL_CLIMB)
    inside(world, 0x43, "middle", "top", there=WALL_RUN & DOUBLE_JUMP & WALL_JUMP)
    two_way(world, (0x43, 2), (0x44, 1), there=Has("Foundry Orochi room top door opened"))
    two_way(world, (0x47, 2), (0x48, 1))
    two_way(world, (0x47, 3), (0x49, 1), back=False)
    two_way(world, (0x4a, 1), (0x92, 2), back=SMOKE_4)
    two_way(world, (0x60, 4), (0x62, 1))
    two_way(world, (0x62, 2), (0x63, 1))
    inside(world, 0x63, "main", "gate", there=False)
    two_way(world, (0x63, 2), (0x64, 1))
    two_way(world, (0x63, 3), (0x66, 2), back=Has("Goro's Lair bells rung"))
    two_way(world, (0x64, 2), (0x65, 1))
    two_way(world, (0x64, 3), (0x66, 1))
    inside(world, 0x65, "entrance", "boss", back=LONG_JUMP | DOUBLE_JUMP)
    inside(world, 0x65, "entrance", "exit", there=LONG_JUMP | DOUBLE_JUMP, back=LONG_JUMP | DOUBLE_JUMP)
    inside(world, 0x65, "exit", "boss", back=False)
    two_way(world, (0x65, 2), (0x6b, 4))
    inside(world, 0x66, "entrance", "exit", back=Has("Goro's Lair bells rung"))
    inside(world, 0x67, "entrance", "exit", back=Has("Wu-Shi blockade destroyed"))
    inside(world, 0x67, "entrance", "statue", there=FIST_OF_RUIN, back=FIST_OF_RUIN)
    two_way(world, (0x67, 2), (0x6c, 1))
    two_way(world, (0x67, 3), (0x68, 1), back=Has("Wu-Shi lava pots dropped"))
    inside(world, 0x68, "entrance", "exit", back=Has("Wu-Shi lava pots dropped"))
    two_way(world, (0x68, 2), (0x6b, 3))
    two_way(world, (0x68, 5), (0x6e, 1))
    inside(world, 0x6a, "main", "wall-run", there=FIST_OF_RUIN, back=WALL_RUN)
    two_way(world, (0x6a, 1), (0x6b, 1))
    inside(world, 0x6b, "main", "top", there=Has("Wu-Shi fire cleared") | (WALL_JUMP & DOUBLE_JUMP))
    inside(world, 0x6b, "main", "statue", there=FIST_OF_RUIN, back=FIST_OF_RUIN)
    two_way(world, (0x6b, 2), (0xc0, 1))
    inside(world, 0x6c, "entrance", "shrine", there=SWING)
    inside(world, 0x80, "main", "statue", there=FIST_OF_RUIN, back=FIST_OF_RUIN)
    inside(world, 0x80, "main", "top", back=Has("Forest bramble cleared"))
    two_way(world, (0x80, 1), (0xc0, 4))
    two_way(world, (0x80, 2), (0x84, 1), there=SWING & WALL_CLIMB, back=SWING & WALL_CLIMB)
    two_way(world, (0x80, 3), (0x81, 1))
    inside(world, 0x81, "main", "waterfall", there=Has("Forest pillar destroyed"))
    two_way(world, (0x81, 2), (0x82, 1))
    two_way(world, (0x82, 2), (0x89, 1))
    two_way(world, (0x82, 3), (0x92, 1))
    inside(world, 0x88, "entrance", "door", back=Has("Dead Pool cleared"))
    inside(world, 0x88, "door", "exit", there=SWING | (WALL_JUMP & WALL_RUN & DOUBLE_JUMP))
    two_way(world, (0x88, 4), (0xc1, 5),
            back=Has("Dead Pool cleared") & (SWING | (WALL_JUMP & WALL_RUN & DOUBLE_JUMP)))
    two_way(world, (0x89, 3), (0x8e, 1),
            there=Has("Forest first tree fed") & Has("Forest second tree fed") & Has("Forest third tree fed"), )
    two_way(world, (0x8e, 2), (0x8f, 1))
    two_way(world, (0x8e, 3), (0x93, 1))
    two_way(world, (0x8f, 2), (0x90, 1), there=FIST_OF_RUIN & (DOUBLE_JUMP | LONG_JUMP), back=FIST_OF_RUIN & WALL_CLIMB)
    two_way(world, (0xa0, 1), (0xc1, 2), back=DOUBLE_JUMP | WALL_RUN)
    inside(world, 0xc0, "main", "monastery", there=LONG_JUMP | DOUBLE_JUMP)
    inside(world, 0xc0, "main", "tombs", there=WALL_CLIMB)
    two_way(world, (0xc0, 2), (0xc4, 1))
    two_way(world, (0xc0, 5), (0xc1, 1))
    two_way(world, (0xc0, 7), (0xc2, 6), there=Has("Monastery statue destroyed"), back=FIST_OF_RUIN)
    inside(world, 0xc1, "main", "wastelands", there=WALL_JUMP | (WALL_RUN & DOUBLE_JUMP))
    inside(world, 0xc1, "main", "netherrealm", there=SWING)
    inside(world, 0xc1, "main", "foundry", there=FOUNDRY_RULE, back=FOUNDRY_RULE)
    inside(world, 0xc1, "netherrealm", "wastelands", back=False)
    inside(world, 0xc2, "bottom", "top", back=FIST_OF_RUIN)
    two_way(world, (0xc2, 1), (0xc6, 2))
    two_way(world, (0xc2, 2), (0xc3, 1))
    two_way(world, (0xc4, 2), (0xc5, 1))
    two_way(world, (0xc5, 2), (0xc6, 1))
    two_way(world, (0xc5, 3), (0xc7, 1))


def set_rules(world: MKSMWorld) -> None:
    """The rules that name regions. Everything else is in rules.py."""
    rules.set_purchase_rules(
        world, lambda tier: _rooms_reached(world, PURCHASE_ROOM_TIERS[tier]))
    rules.set_smoke_mission_rules(world, (SMOKE_1, SMOKE_2, SMOKE_3, SMOKE_4, SMOKE_5))


# How many times to let GER try. It places the rooms that hold progression
# first, and a room with an event in it counts - including the dead ends, whose
# one door leads nowhere new. Spend too many of the branching doors on those
# early and the frontier dies with rooms still unplaced, which is a matter of
# the order it happened to pick rather than anything about the graph: the same
# world succeeds about one attempt in five, so a handful of tries is plenty.
ER_ATTEMPTS = 30


def _disconnected_again(world: MKSMWorld, doors: list, targets: list) -> None:
    """Put the graph back the way it was just after disconnecting, to try again.

    A failed attempt leaves its placements behind, so the entrance lists have to
    be rebuilt rather than patched: every exit is re-filed under whatever it now
    points at, and the targets, which placement removes as it consumes them, are
    put back. Rebuilt in name order so a retry is as deterministic as a first
    attempt.
    """
    for door in doors:
        door.connected_region = None
    regions = sorted(world.multiworld.get_regions(world.player), key=lambda r: r.name)
    for region in regions:
        region.entrances = []
    for region in regions:
        for exit_ in region.exits:
            if exit_.connected_region is not None:
                exit_.connected_region.entrances.append(exit_)
    for target in targets:
        target.connected_region.entrances.append(target)


def connect_entrances(world: MKSMWorld) -> None:
    """Shuffle the doors: every mouth paired with another one, both ways.

    Coupled, because the game's doors are. The client patches both objects of a
    pair, so a door that now leads somewhere new leads back the same way, and
    GER needs the two directions to carry the same name to find each other -
    which is exactly what two_way writes, the mouth rather than the destination.

    Runs after set_rules, so every edge already carries its rule and GER can
    tell which placements leave a region reachable.
    """
    doors = []
    mouth_of: dict = {}  # entrance name -> the (room, spawn) it sits in
    for key in sorted(world.mouth):
        if key in VANILLA_DOORS:
            continue
        region, spawn = world.mouth[key], key[1]
        name = f"{region.name}: exit {spawn}"
        door = next((e for e in region.exits if e.name == name), None)
        if door is None:
            # A mouth a one-way door lands on - 0x49's - with nothing leaving it.
            continue
        door.randomization_type = EntranceType.TWO_WAY
        disconnect_entrance_for_randomization(door)
        doors.append(door)
        mouth_of[door.name] = key

    doors.sort(key=lambda e: e.name)
    targets = sorted((e for region in world.multiworld.get_regions(world.player)
                      for e in region.entrances if not e.parent_region),
                     key=lambda e: e.name)

    for attempt in range(ER_ATTEMPTS):
        try:
            result = randomize_entrances(world, coupled=True, target_group_lookup={0: [0]},
                                         er_targets=targets, exits=doors)
            _record_in_spoiler(world, result)
            world.entrance_redirects = _redirects(result, mouth_of)
            return
        except EntranceRandomizationError:
            if attempt == ER_ATTEMPTS - 1:
                raise
            _disconnected_again(world, doors, targets)


def _redirects(state, mouth_of: dict) -> dict:
    """The shuffle as the game needs it: which loadmap object now goes where.

    Logic pairs mouths; the game stores a destination map and a spawn in each
    door's argument array, so every pairing becomes a write to the object sitting
    in that mouth. DOOR_OBJECTS says which object that is, and a mouth with more
    than one gets all of them - 0x65 picks between two loadmaps depending on how
    far you have got, and writing one of them would move the door only sometimes.

    Both halves of a pair appear in state.pairings, so walking it once covers
    both directions.

    Shape: {"<map hex>": {"<object>": [dest map, spawn]}}, which is what the
    client applies on each room load.
    """
    out: dict = {}
    for source, target in state.pairings:
        here, there = mouth_of.get(source), mouth_of.get(target)
        if here is None or there is None:
            continue
        room, spawn = here
        dest_room, dest_spawn = there
        for obj in DOOR_OBJECTS.get(here, ()):
            out.setdefault(f"0x{room:02x}", {})[obj] = [dest_room, dest_spawn]
    return out


def _record_in_spoiler(world: MKSMWorld, state) -> None:
    """List the door pairings in the spoiler log.

    Nothing writes these for us - a world has to hand them over itself - and a
    shuffled seed whose log does not say where the doors went is of little use
    to anyone reading it.

    Coupled placements come back twice, once per direction, so the reverse of a
    pair already written is dropped and the line reads "<=>".
    """
    spoiler = world.multiworld.spoiler
    seen = set()
    for source, target in state.pairings:
        if (target, source) in seen:
            continue
        seen.add((source, target))
        spoiler.set_entrance(source, target, "both", world.player)
