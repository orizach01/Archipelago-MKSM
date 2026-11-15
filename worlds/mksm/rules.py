from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from rule_builder.options import OptionFilter
from rule_builder.rules import AtLeast, Has, Rule
from .consts import (TOURNAMENT_VICTORY_AMOUNT, DOUBLE_JUMP, WALL_RUN, WALL_JUMP,
                     WALL_CLIMB, SWING, LONG_JUMP, FIST_OF_RUIN, FATALITY,
                     MULTALITY, BRUTALITY)
from .locations import FINISHING_MOVES_LOCATIONS
from .options import (BossGoal, Shopsanity, RandomizeTournamentVictories, PortalStart,
                      LockSpecialMoves, Character)

if TYPE_CHECKING:
    from .world import MKSMWorld

# Needs R2 upgraded twice. With lock_special_moves the first R2 item only unlocks the move;
# with shopsanity off the upgrades are bought in the shop, so only the unlock is an item.
LAUNCHING_THROW = (
        Has("R2 special upgrade",
            count=1,
            options=[OptionFilter(Shopsanity, False), OptionFilter(LockSpecialMoves, True)],
            filtered_resolution=True,
            )
        & Has("R2 special upgrade",
              count=2,
              options=[OptionFilter(Shopsanity, True), OptionFilter(LockSpecialMoves, False)],
              filtered_resolution=True,
              )
        & Has("R2 special upgrade",
              count=3,
              options=[OptionFilter(Shopsanity, True), OptionFilter(LockSpecialMoves, True)],
              filtered_resolution=True,
              )
)


def _move_unlock(item: str, characters: list[int]) -> Rule:
    """Has the move's unlock item, but only when lock_special_moves is on and the character uses that move."""
    return Has(item,
               options=[OptionFilter(LockSpecialMoves, True), OptionFilter(Character, characters, "in")],
               filtered_resolution=True)


# Characters not listed (VS characters) always pass, as does lock_special_moves being off
PROJECTILE_MOVE = (_move_unlock("Square special upgrade", [Character.option_liu_kang, Character.option_sub_zero])
                   & _move_unlock("Circle special upgrade", [Character.option_kung_lao, Character.option_scorpion]))
# Same, but Scorpion and Sub-Zero always pass too
MOON_RULE = (_move_unlock("Square special upgrade", [Character.option_liu_kang])
             & _move_unlock("Circle special upgrade", [Character.option_kung_lao]))
# Every character's projectile, VS characters included (Baraka's Blade Spark and Johnny Cage's
# Shadow Bolt are Square, Kitana's Fan Throw is Circle, Reptile has Acid Spit on Square and
# Force Ball on Circle). Used where the VS characters' shooting koin events don't skip the need.
ANY_PROJECTILE_MOVE = (
        _move_unlock("Square special upgrade", [Character.option_liu_kang, Character.option_sub_zero,
                                                Character.option_baraka, Character.option_johnny_cage])
        & _move_unlock("Circle special upgrade", [Character.option_kung_lao, Character.option_scorpion,
                                                  Character.option_kitana])
        & (_move_unlock("Square special upgrade", [Character.option_reptile])
           | _move_unlock("Circle special upgrade", [Character.option_reptile]))
)

# The boss events. Both layouts name them the same way - "<boss> defeated", the
# thing itself - so these work whichever one built the seed.
KITANA = Has("Kitana defeated")
REPTILE = Has("Reptile defeated")
BARAKA = Has("Baraka defeated")
GORO = Has("Goro defeated")
SCORPION = Has("Scorpion defeated")
ERMAC = Has("Ermac defeated")
MILEENA = Has("Mileena defeated")
KANO = Has("Kano defeated")
SHAO_KAHN = Has("Shao Kahn defeated")

TOURNAMENT_VICTORY_RULE = Has("Tournament victory",
                              count=TOURNAMENT_VICTORY_AMOUNT,
                              options=[OptionFilter(RandomizeTournamentVictories, True)])

BOSSES_RULE = KITANA & REPTILE & BARAKA & GORO & SCORPION & OptionFilter(RandomizeTournamentVictories, False)

FOUNDRY_RULE = (TOURNAMENT_VICTORY_RULE | BOSSES_RULE) & (WALL_CLIMB & WALL_RUN & DOUBLE_JUMP)

WU_SHI_RULE = Has("Wu-Shi access",
                  options=[OptionFilter(PortalStart, True)],
                  filtered_resolution=True)


def set_all_rules(world: MKSMWorld) -> None:
    """Every rule that does not name a region.

    The ones that do - the purchase tiers and the Smoke missions - need a region
    set to name, so each layout supplies its own and calls the helpers below.
    """
    set_all_location_rules(world)
    set_completion_condition(world)
    set_finishing_moves_rules(world)


# Which room regions each vanilla region covers. create_vanilla_regions makes one
# region per area and create_er_regions one per room, so "can reach this area"
# has two spellings and a rule that names only one of them breaks the other mode.
#
# Mind the splits: vanilla's "Tombs" is not the same region as "Tombs - Baraka
# arena", so 0x0f belongs to the second, and Wu-Shi is four regions, not one.
# The room region's own name prefix does not say which of them it maps to.


# What each Smoke mission takes, as rules rather than as "can reach the location
# before it". Written once and used twice: by the mission locations, and by the
# doors that only open once a mission is done - 0x06's smoke door needs mission 2.
#
# Not CanReachLocation, for three reasons. The locations only exist when the
# smoke_missions option is on, so a rule naming one raises during create_regions
# in every other seed. CanReachLocation means "could reach", not "did", which is
# a poor fit for a door that physically opens on completion. And on an entrance
# it would need its indirect condition registered, which these do not.

def set_purchase_rules(world: MKSMWorld, tier_rule: "Callable[[int], Rule]") -> None:
    """Price the shop by how much of the game is open.

    The shop costs EXP, which logic cannot count, so each tier stands for "you
    have plausibly earned this much by now, buying cheapest first". How to
    measure that depends on the layout - areas opened in vanilla, rooms reached
    with entrances shuffled - so the layout passes in `tier_rule`, which turns a
    tier number into the rule for it. Which purchase sits in which tier is the
    same either way, so the table below stays here.
    """
    tiers = {
        0: [
            "Purchase upgrade - R2 2",
        ],
        2: [
            "Purchase upgrade - Square 2",
            "Purchase upgrade - Triangle 2",
            "Purchase upgrade - Circle 2",
            "Purchase upgrade - R2 3",
        ],
        3: [
            "Purchase combo 1",
            "Purchase combo 2",
            "Purchase combo 3",
            "Purchase combo 4",
            "Purchase combo 5",
        ],
        5: [
            "Purchase upgrade - Square 3",
            "Purchase upgrade - Triangle 3",
            "Purchase upgrade - Circle 3",
            "Purchase upgrade - R2 4",
            "Purchase upgrade - Square 4",
            "Purchase upgrade - Triangle 4",
            "Purchase upgrade - Circle 4",
            "Purchase upgrade - Circle 5",
            "Purchase upgrade - R2 5",
        ],
    }

    for tier, loc_names in tiers.items():
        rule = tier_rule(tier)
        for loc_name in loc_names:
            try:
                loc = world.get_location(loc_name)
            except KeyError:
                continue
            world.set_rule(loc, rule)


def set_all_location_rules(world: MKSMWorld) -> None:
    world.set_rule(world.get_location("GL: koin above the doorway"),
                   DOUBLE_JUMP | WALL_JUMP | WALL_RUN)
    world.set_rule(world.get_location("GL: koin from shooting the moon"), MOON_RULE)
    world.set_rule(world.get_location("GL: koin above the breakable door"), DOUBLE_JUMP | WALL_JUMP)
    world.set_rule(world.get_location("WSA: koin after the tree branch swing"), SWING | DOUBLE_JUMP)
    world.set_rule(world.get_location("WSA: koin in the tree"), DOUBLE_JUMP)
    world.set_rule(world.get_location("EM: koin from breaking the statue"), FIST_OF_RUIN)
    world.set_rule(world.get_location("EM: koin from shooting the dragon koin behind the window"), PROJECTILE_MOVE)
    world.set_rule(
        world.get_location("WSA: koin after the bamboo swing"),
        SWING | (DOUBLE_JUMP & (WALL_RUN | WALL_JUMP))
    )
    world.set_rule(
        world.get_location("WSA: koin on a high wall near the lava pots"),
        WALL_RUN & WALL_JUMP & DOUBLE_JUMP  # can be WALL_JUMP & DOUBLE_JUMP but inconsistent
    )
    world.set_rule(world.get_location("P: koin from performing a fatality on the dragon symbol"), FATALITY)
    world.set_rule(world.get_location("N: koin above the arch"), LONG_JUMP | DOUBLE_JUMP)
    world.set_rule(world.get_location("LF: koin behind the living tree"), DOUBLE_JUMP)
    world.set_rule(world.get_location("LF: Forest health upgrade"), WALL_CLIMB | DOUBLE_JUMP)
    world.set_rule(world.get_location("LF: koin from shooting the closed eye"), PROJECTILE_MOVE)
    world.set_rule(world.get_location("LF: koin from shooting at dragon koin"), PROJECTILE_MOVE)
    world.set_rule(world.get_location("W: koin from impaling an enemy on the big spike"),
                   WALL_CLIMB | DOUBLE_JUMP | LONG_JUMP)
    world.set_rule(world.get_location("W: koin found on the lion statue"), DOUBLE_JUMP | WALL_RUN)
    world.set_rule(world.get_location("W: koin from shooting the dragon koin"), PROJECTILE_MOVE)
    world.set_rule(
        world.get_location("DP: koin from drowning enemies in the pool"),
        WALL_CLIMB | (WALL_JUMP & DOUBLE_JUMP)
    )
    world.set_rule(world.get_location("ST: koin above Baraka's entrance"), WALL_RUN & DOUBLE_JUMP)
    world.set_rule(world.get_location("ST: koin from the broken statue"), FIST_OF_RUIN)
    world.set_rule(world.get_location("ST: koin above the broken statue"), FIST_OF_RUIN)
    world.set_rule(world.get_location("ST: koin from a high button in the rolling spikes room"), DOUBLE_JUMP)
    world.set_rule(world.get_location("ST: koin above the ceiling in the room with the hooks"), DOUBLE_JUMP)
    world.set_rule(world.get_location("ST: koin from launching a tarkata on the flying bird"), LAUNCHING_THROW)
    world.set_rule(world.get_location("ST: koin behind statue in the falling spike trap room"), FIST_OF_RUIN)
    world.set_rule(
        world.get_location("ST: koin above broken statue in the falling spike trap room"),
        FIST_OF_RUIN & (DOUBLE_JUMP | WALL_JUMP | WALL_RUN)
    )
    world.set_rule(world.get_location("ST: koin near the fan"), LONG_JUMP | DOUBLE_JUMP)
    world.set_rule(world.get_location("ST: koin from the destroyed soul tomb"), FIST_OF_RUIN)
    world.set_rule(world.get_location("ST: wall jump obtained"), WALL_RUN | DOUBLE_JUMP)
    world.set_rule(world.get_location("ST: koin from shooting the dragon koin near the portal"), PROJECTILE_MOVE)
    world.set_rule(world.get_location("ST: koin from shooting the dragon koin in the test your might room"),
                   PROJECTILE_MOVE)
    world.set_rule(world.get_location("F: koin from smashing an enemy with the big hammers"),
                   LAUNCHING_THROW)
    world.set_rule(world.get_location("F: koin from breaking the pipe with the axe"), DOUBLE_JUMP)
    world.set_rule(world.get_location("F: koin from wall jumping above the main room"), WALL_JUMP & DOUBLE_JUMP)
    world.set_rule(
        world.get_location("F: koin above the wood ceiling"),
        DOUBLE_JUMP & (WALL_JUMP | WALL_RUN)
    )
    world.set_rule(world.get_location("F: koin above the lava pit"), DOUBLE_JUMP)
    world.set_rule(world.get_location("F: koin from shooting the dragon koin behind the breakable wall"),
                   PROJECTILE_MOVE & FIST_OF_RUIN)


def set_finishing_moves_rules(world: MKSMWorld) -> None:
    flattened_dict = {loc: loc_id for k, v in FINISHING_MOVES_LOCATIONS.items() for loc, loc_id in v.items()}
    for loc_name in flattened_dict.keys():

        try:
            # finishing moves from other characters other than the chosen one will not be in the world
            loc = world.get_location(loc_name)
        except KeyError:
            continue

        if "Fatality" in loc_name:
            world.set_rule(loc, FATALITY)
        elif "Multality" in loc_name:
            world.set_rule(loc, MULTALITY)
        elif "Brutality" in loc_name:
            world.set_rule(loc, BRUTALITY)


def set_smoke_mission_rules(world: MKSMWorld, smoke: "tuple[Rule, ...]") -> None:
    """`smoke` is what each of the five missions takes, in order, from the layout."""
    if not world.options.smoke_missions:
        return

    for n, rule in enumerate(smoke, start=1):
        world.set_rule(world.get_location(f"Complete Smoke mission {n}"), rule)


def set_completion_condition(world: MKSMWorld) -> None:
    percent = world.options.red_koin_need_percent.value
    enough_red_koins = Has("Red Koin", count=int(world.red_koin_amount * percent / 100))

    goal_rule = enough_red_koins

    if world.options.boss_goal >= BossGoal.option_shao_kahn_only:
        goal_rule = goal_rule & SHAO_KAHN

    if world.options.boss_goal >= BossGoal.option_main_bosses:
        goal_rule = goal_rule & KITANA & REPTILE & BARAKA & GORO & SCORPION

    if world.options.boss_goal >= BossGoal.option_main_and_secret_bosses:
        goal_rule = goal_rule & ERMAC & MILEENA & KANO

    world.set_completion_rule(
        goal_rule
    )
