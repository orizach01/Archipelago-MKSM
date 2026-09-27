from collections.abc import Mapping
from typing import Any

# Imports of base Archipelago modules must be absolute.
from Options import OptionError
from worlds.AutoWorld import World

# Imports of your world's files must be relative.
from . import items, locations, regions, rules  # , web_world

from . import options as mksm_options  # rename due to a name conflict with World.options
from .consts import FILLER_EXP


class MKSMWorld(World):
    """
    Mortal Kombat: Shaolin Monks is a 3d action platformer based on the story of Mortal Kombat 2
    """

    game = "Mortal Kombat: Shaolin Monks"

    red_koin_amount: int

    options_dataclass = mksm_options.MKSMOptions
    options: mksm_options.MKSMOptions

    item_name_to_id = items.ITEM_NAME_TO_ID
    location_name_to_id = locations.LOCATION_NAME_TO_ID

    topology_present = True

    origin_region_name = "Menu"

    def generate_early(self) -> None:
        # Both halves of the goal can be switched off independently - boss_goal can be
        # no_bosses and red_koin_need_percent can be 0 - and with both off the seed would
        # be complete the moment it starts. Catch it here so the player finds out now
        # rather than after generating.
        no_bosses = self.options.boss_goal == mksm_options.BossGoal.option_no_bosses
        no_koins = self.options.red_koin_need_percent == 0
        if no_bosses and no_koins:
            raise OptionError(
                f"{self.player_name}: boss_goal is set to no_bosses and "
                f"red_koin_need_percent is 0, which leaves no goal to complete. "
                f"Raise red_koin_need_percent above 0, or pick a boss_goal."
            )

    def create_regions(self) -> None:
        regions.create_all_regions(self)
        locations.create_all_locations(self)

    def set_rules(self) -> None:
        print("SETTING RULES")
        rules.set_all_rules(self)

    def create_items(self) -> None:
        print("SETTING ITEMS")
        items.create_all_items(self)

    def create_item(self, name: str) -> items.MKSMItem:
        return items.create_item_with_correct_classification(self, name)

    def get_filler_item_name(self) -> str:
        return f"{FILLER_EXP} EXP"

    def fill_slot_data(self) -> Mapping[str, Any]:
        return {
            "character": self.options.character.value,
            "red_koin_amount": self.red_koin_amount,
            "red_koin_need_percent": self.options.red_koin_need_percent.value,
            "boss_goal": self.options.boss_goal.value,
            "fatalitysanity": bool(self.options.fatalitysanity.value),
        }
