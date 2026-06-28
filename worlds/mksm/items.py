from __future__ import annotations

from typing import TYPE_CHECKING

from BaseClasses import Item, ItemClassification
from .consts import CHARACTER_PURCHASE_AMOUNTS, HEALTH_UPGRADE_AMOUNT, BLOOD_BAR_AMOUNT

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
    "5000 XP": 20,
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
    "5000 XP": ItemClassification.filler,
}


class MKSMItem(Item):
    game = "Mortal Kombat: Shaolin Monks"


def get_random_filler_item_name(world: MKSMWorld) -> str:
    return "5000 XP"


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

    amounts = CHARACTER_PURCHASE_AMOUNTS[world.options.character.value]

    itempool += [world.create_item(f"Combo {i + 1}") for i in range(amounts.combo)]
    itempool += [world.create_item("Square special upgrade") for _ in range(amounts.square)]
    itempool += [world.create_item("Triangle special upgrade") for _ in range(amounts.triangle)]
    itempool += [world.create_item("Circle special upgrade") for _ in range(amounts.circle)]
    itempool += [world.create_item("R2 special upgrade") for _ in range(amounts.r2)]

    itempool += [world.create_item("Health upgrade") for _ in range(HEALTH_UPGRADE_AMOUNT)]
    itempool += [world.create_item("Blood bar") for _ in range(BLOOD_BAR_AMOUNT)]

    number_of_unfilled_locations = len(world.multiworld.get_unfilled_locations(world.player))
    current_count = len(itempool)

    assert current_count <= number_of_unfilled_locations

    diff = number_of_unfilled_locations - current_count

    xp_filler_count = diff // 4
    red_koin_count = diff - xp_filler_count

    world.red_koin_amount = red_koin_count
    itempool += [world.create_item("Red Koin") for _ in range(red_koin_count)]
    itempool += [world.create_item("5000 XP") for _ in range(xp_filler_count)]

    world.multiworld.itempool += itempool
