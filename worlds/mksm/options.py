from dataclasses import dataclass

from Options import Choice, PerGameCommonOptions, Range


class Character(Choice):
    """
    The character you play as during the run.
    The game will force the character picked here to be your character in-game.
    That means you don't need to unlock Scorpion/Sub-Zero first in order to play as them.
    """
    display_name = "Character"

    option_liu_kang = 0
    option_kung_lao = 1
    option_sub_zero = 2
    option_scorpion = 3

    default = option_liu_kang


class RedKoinPercent(Range):
    """
    The randomizer fills the item pool with Red Koin items which are then randomized around the multiworld.
    The number of Red Koins in the pool depends on your character (some characters have more locations than others).
    To complete the goal you need to both beat Shao Kahn and have a set number of Red Koins.
    This option determines what % of all the available Red Koins in the pool is needed.
    0 means the goal will be beating Shao Kahn only.
    100 means requiring to find ALL Red Koins from locations AND beating Shao Kahn.
    80 (default) means you need to find at least 80% of all Red Koins AND beat Shao Kahn to win.
    There is a tracker in the pause menu that shows: current amount / need for goal / total in the multiworld.
    """
    display_name = "Red Koin completion percent" #TODO better name
    range_start = 0
    range_end = 100

    default = 80


@dataclass
class MKSMOptions(PerGameCommonOptions):
    character: Character
    red_koin_need_percent: RedKoinPercent
