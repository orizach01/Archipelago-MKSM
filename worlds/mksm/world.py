from collections.abc import Mapping
from types import ModuleType
from typing import Any, Optional

from BaseClasses import Tutorial
# Imports of base Archipelago modules must be absolute.
from Options import OptionError, Option
from worlds.AutoWorld import World, WebWorld

# Imports of your world's files must be relative.
from . import items, layouts, locations, rules  # , web_world

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

    # The layout this seed is built with, picked in create_regions. Vanilla and
    # entrance rando are separate modules under layouts/, each with the same
    # four entry points.
    layout: ModuleType

    # Built by the entrance rando layout, which makes a region per room instead
    # of per area. Empty in a vanilla seed.
    #   reg[room, part]     -> Region   ("part" is None for a one-region room)
    #   mouth[room, spawn]  -> Region   which region a door mouth sits in
    reg: dict
    mouth: dict

    # Where each shuffled door now leads, for the client to write into the game:
    #   {"<map hex>": {"<loadmap object>": [dest map, spawn]}}
    # Empty in a vanilla seed. Built in connect_entrances, sent in slot data.
    entrance_redirects: dict

    options_dataclass = mksm_options.MKSMOptions
    options: mksm_options.MKSMOptions

    item_name_to_id = items.ITEM_NAME_TO_ID
    location_name_to_id = locations.LOCATION_NAME_TO_ID

    location_name_groups = LOCATION_GROUPS

    topology_present = True

    origin_region_name = "Menu"

    ut_can_gen_without_yaml = True

    web = MKSMWebWorld()

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

        if self.options.randomize_entrances:
            # Entrance rando always starts at the Portal. Its region graph hangs
            # off 0xc0, and the tutorial route out of Goro's Lair assumes doors
            # that are no longer where it expects them. Set on the option rather
            # than only in slot_data, so logic, the item pool and the spoiler all
            # agree with what the client will do.
            self.options.portal_start.value = 1

        no_bosses = self.options.boss_goal == mksm_options.BossGoal.option_no_bosses
        no_koins = self.options.red_koin_need_percent == 0
        if no_bosses and no_koins:
            raise OptionError(
                f"{self.player_name}: boss_goal is set to no_bosses and "
                f"red_koin_need_percent is 0, which leaves no goal to complete. "
                f"Raise red_koin_need_percent above 0, or pick a boss_goal."
            )

    def create_regions(self) -> None:
        self.layout = layouts.pick(self)

        # Locations before connections: a connection's rule resolves the moment
        # Region.connect is called, and a rule naming a location or a region
        # looks it up then, to register the indirect condition. Resolve it
        # before the thing exists and it raises. Nothing in location creation
        # needs an entrance, so this order is safe for either layout.
        self.layout.create_regions(self)
        self.layout.create_locations(self)
        self.layout.connect(self)

    def set_rules(self) -> None:
        rules.set_all_rules(self)
        self.layout.set_rules(self)

    def connect_entrances(self) -> None:
        self.layout.connect_entrances(self)

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
            "portal_start": bool(self.options.portal_start.value),
            "skip_tutorial": bool(self.options.skip_tutorial.value),
            "randomize_tournament_victories": bool(self.options.randomize_tournament_victories.value),
            "mana_upgrades": bool(self.options.mana_upgrades.value),
            "lock_special_moves": bool(self.options.lock_special_moves.value),
            "smoke_missions": bool(self.options.smoke_missions.value),
            "randomize_entrances": bool(self.options.randomize_entrances.value),
            "entrance_redirects": self.entrance_redirects,
            "options": self.options.as_dict("character",
                                            "red_koin_need_percent",
                                            "boss_goal",
                                            "fatalitysanity",
                                            "shopsanity",
                                            "portal_start",
                                            "skip_tutorial",
                                            "randomize_tournament_victories",
                                            "mana_upgrades",
                                            "lock_special_moves",
                                            "smoke_missions",
                                            "randomize_entrances",
                                            )
        }

    @staticmethod
    def interpret_slot_data(slot_data: dict[str, Any]) -> dict[str, Any]:
        # Trigger a regen in UT
        return slot_data
