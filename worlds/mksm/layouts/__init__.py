"""The two region layouts: one region per area, or one region per room.

Vanilla and entrance rando are different logic models rather than variants of
one, so each gets a module instead of an option check at every turn. Both expose
the same four entry points, called from MKSMWorld's generation steps:

    create_regions(world)    make the regions
    create_locations(world)  put the locations and the events in them
    connect(world)           wire the entrances
    set_rules(world)         only the rules that name regions

Everything that does not depend on the shape of the graph stays shared. Location
names and ids especially: location_name_to_id is the datapackage and has to be
identical in every seed of the game, so the layouts differ in where a location
is placed, never in which locations exist or what they are called.
"""
from __future__ import annotations

from types import ModuleType
from typing import TYPE_CHECKING

from . import er, vanilla

if TYPE_CHECKING:
    from ..world import MKSMWorld


def pick(world: "MKSMWorld") -> ModuleType:
    """The layout this seed is built with."""
    return er if world.options.randomize_entrances else vanilla
