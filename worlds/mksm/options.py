from dataclasses import dataclass

from Options import Choice, PerGameCommonOptions, Range, DefaultOnToggle


class Character(Choice):
    """
    The character you play as during the run.
    The game will force the character picked here to be your character in-game.
    That means you don't need to unlock Scorpion/Sub-Zero first in order to play as them.
    The VS mode exclusive characters are also available, but due to how they work they always start with fully upgraded
     special moves except for R2, so that means there will be no special move upgrade items in the multiworld except R2,
     and no blood bar upgrades beyond the first one.
    You can still purchase upgrades in the menu like with other characters.
    """
    display_name = "Character"

    option_liu_kang = 0
    option_kung_lao = 1
    option_sub_zero = 2
    option_scorpion = 3
    option_baraka = 4  # can get r2 upgrades
    option_kitana = 5  # can get r2 upgrades
    option_reptile = 6  # can get r2 upgrades
    option_johnny_cage = 7  # can get r2 upgrades

    default = option_liu_kang

    def is_vs(self):
        return self in (
            Character.option_baraka,
            Character.option_kitana,
            Character.option_reptile,
            Character.option_johnny_cage,
        )


class RedKoinPercent(Range):
    """
    The randomizer tries to fill the item pool with 60 Red Koin items which are then randomized around the multiworld.
    There may be less than 60 if there aren't enough locations in the world.
    To complete the goal you need to both beat the boss goal and have a set number of Red Koins.
    This option determines what % of all the available Red Koins in the pool is needed.
    0 means the goal will be beating the boss goal only.
    100 means requiring to get ALL 60 Red Koins AND beating the boss goal.
    80 (default) means you need to get at least 80% of all Red Koins AND beat the boss goal to win.
    There is a tracker in the pause menu that shows: current amount / needed for goal / total in the multiworld.
    """
    display_name = "Red Koin goal percent"
    range_start = 0
    range_end = 100

    default = 80


class BossGoal(Choice):
    """
    What bosses are needed for goal completion.
    The goal also includes getting enough Red Koins, set in the red_koin_need_percent option.
    main_bosses (default): all main bosses (Kitana, Reptile, Baraka, Goro and Scorpion) and the final boss.
    main_and_secret_bosses: all previously mentioned bosses and all secret bosses (Ermac, Mileena and Kano).
    """
    display_name = "Boss Goal"

    option_main_bosses = 0
    option_main_and_secret_bosses = 1

    default = option_main_bosses


class Fatalitysanity(DefaultOnToggle):
    """
    If on, adds checks for performing all of your character's different fatalities, multalities and brutality
    """
    display_name = "Fatalitysanity"


@dataclass
class MKSMOptions(PerGameCommonOptions):
    character: Character
    red_koin_need_percent: RedKoinPercent
    boss_goal: BossGoal
    fatalitysanity: Fatalitysanity
