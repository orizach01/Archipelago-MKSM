from collections.abc import Mapping
from typing import Any, Optional

from BaseClasses import Tutorial
# Imports of base Archipelago modules must be absolute.
from Options import OptionError, Option
from worlds.AutoWorld import World, WebWorld

# Imports of your world's files must be relative.
from . import items, locations, regions, rules  # , web_world

from . import options as mksm_options  # rename due to a name conflict with World.options
from .consts import FILLER_EXP
from .location_groups import LOCATION_GROUPS
from .options import OPTION_GROUPS


class MKSMWebWorld(WebWorld):
    theme = "stone"
    option_groups = OPTION_GROUPS
    tutorials = [Tutorial(
        "Multiworld Setup Guide",
        "A guide for setting up Mortal Kombat: Shaolin Monks to be played in Archipelago.",
        "English",
        "setup_en.md",
        "setup/en",
        ["orizach01"]
    )]


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

    location_name_groups = LOCATION_GROUPS

    topology_present = True

    origin_region_name = "Menu"

    ut_can_gen_without_yaml = True

    def generate_early(self) -> None:
        re_gen_passthrough = getattr(self.multiworld, "re_gen_passthrough", {})
        if re_gen_passthrough and self.game in re_gen_passthrough:
            # Get the passed through slot data from the real generation
            slot_data: dict[str, Any] = re_gen_passthrough[self.game]

            slot_options: dict[str, Any] = slot_data.get("options", {})
            # Set all your options here instead of getting them from the yaml
            for key, value in slot_options.items():
                opt: Optional[Option] = getattr(self.options, key, None)
                if opt is not None:
                    # You can also set .value directly but that won't work if you have OptionSets
                    setattr(self.options, key, opt.from_any(value))

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
        rules.set_all_rules(self)

    def create_items(self) -> None:
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
            "shopsanity": bool(self.options.shopsanity.value),
            "wu_shi_start": bool(self.options.wu_shi_start.value),
            "skip_tutorial": bool(self.options.skip_tutorial.value),
            "randomize_tournament_victories": bool(self.options.randomize_tournament_victories.value),
            "mana_upgrades": bool(self.options.mana_upgrades.value),
            "options": self.options.as_dict("character",
                                            "red_koin_need_percent",
                                            "boss_goal",
                                            "fatalitysanity",
                                            "shopsanity",
                                            "wu_shi_start",
                                            "skip_tutorial",
                                            "randomize_tournament_victories",
                                            "mana_upgrades",
                                            )
        }

    @staticmethod
    def interpret_slot_data(slot_data: dict[str, Any]) -> dict[str, Any]:
        # Trigger a regen in UT
        return slot_data
