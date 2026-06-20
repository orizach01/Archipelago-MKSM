from __future__ import annotations

from typing import TYPE_CHECKING

from BaseClasses import Item, ItemClassification

if TYPE_CHECKING:
    from .world import MKSMWorld

ITEM_NAME_TO_ID = {
    "Long Jump": 1,
    "Fist of Ruin": 2,
    "Wall Climb": 3,
    "Wall Run": 4,
    "Wall Jump": 5,
    "Swing": 6,
    "Double Jump": 7,
    "Combo 1": 8,
    "Combo 2": 9,
    "Combo 3": 10,
    "Combo 4": 11,
    "Combo 5": 12,
    "Square special upgrade": 13,
    "Triangle special upgrade": 14,
    "Circle special upgrade": 15,
    "R2 special upgrade": 16,
    "Red Koin": 17,
    "Health upgrade": 18,
    "Blood bar": 19,
    "Filler": 20,
}

DEFAULT_ITEM_CLASSIFICATIONS = {
    "Long Jump": ItemClassification.progression | ItemClassification.useful,
    "Fist of Ruin": ItemClassification.progression,
    "Wall Climb": ItemClassification.progression,
    "Wall Run": ItemClassification.progression,
    "Wall Jump": ItemClassification.progression,
    "Swing": ItemClassification.progression,
    "Double Jump": ItemClassification.progression,
    "Combo 1": ItemClassification.filler,
    "Combo 2": ItemClassification.filler,
    "Combo 3": ItemClassification.filler,
    "Combo 4": ItemClassification.filler,
    "Combo 5": ItemClassification.filler,
    "Square special upgrade": ItemClassification.filler,
    "Triangle special upgrade": ItemClassification.filler,
    "Circle special upgrade": ItemClassification.filler,
    "R2 special upgrade": ItemClassification.filler,
    "Red Koin": ItemClassification.progression_deprioritized_skip_balancing,
    "Health upgrade": ItemClassification.filler,
    "Blood bar": ItemClassification.progression_deprioritized_skip_balancing,
    "Filler": ItemClassification.filler,
}


class MKSMItem(Item):
    game = "Mortal Kombat: Shaolin Monks"


def get_random_filler_item_name(world: MKSMWorld) -> str:
    return "Filler"


def create_item_with_correct_classification(world: MKSMWorld, name: str) -> MKSMItem:
    return MKSMItem(name, DEFAULT_ITEM_CLASSIFICATIONS[name], ITEM_NAME_TO_ID[name], world.player)


def create_all_items(world: MKSMWorld) -> None:
    itempool: list[Item] = [
        world.create_item("Long Jump"),
        world.create_item("Fist of Ruin"),
        world.create_item("Wall Climb"),
        world.create_item("Wall Run"),
        world.create_item("Wall Jump"),
        world.create_item("Swing"),
        world.create_item("Double Jump"),
    ]

    # TODO: Different amount of combos per character
    itempool += [
        world.create_item("Combo 1"),
        world.create_item("Combo 2"),
        world.create_item("Combo 3"),
        world.create_item("Combo 4"),
        world.create_item("Combo 5"),
    ]

    # TODO: Different amount of upgrades per character
    square_upgrades = 3
    triangle_upgrades = 3
    circle_upgrades = 2
    r2_upgrades = 4
    itempool += [world.create_item("Square special upgrade") for _ in range(square_upgrades)]
    itempool += [world.create_item("Triangle special upgrade") for _ in range(triangle_upgrades)]
    itempool += [world.create_item("Circle special upgrade") for _ in range(circle_upgrades)]
    itempool += [world.create_item("R2 special upgrade") for _ in range(r2_upgrades)]

    itempool += [world.create_item("Health upgrade") for _ in range(4)]
    itempool += [world.create_item("Blood bar") for _ in range(3)]

    number_of_unfilled_locations = len(world.multiworld.get_unfilled_locations(world.player))
    current_count = len(itempool)

    assert current_count <= number_of_unfilled_locations

    diff = number_of_unfilled_locations - current_count

    world.red_koin_amount = diff
    itempool += [world.create_item("Red Koin") for _ in range(diff)]

    print(f"{len(itempool)=}")

    world.multiworld.itempool += itempool
