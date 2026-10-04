from dataclasses import dataclass

from Options import Choice, PerGameCommonOptions, Range, DefaultOnToggle, Toggle


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
    option_baraka = 4
    option_kitana = 5
    option_reptile = 6
    option_johnny_cage = 7

    default = option_liu_kang

    def is_vs(self):
        return self in (
            Character.option_baraka,
            Character.option_kitana,
            Character.option_reptile,
            Character.option_johnny_cage,
        )

    def can_shoot_moon(self):
        return self in (
            Character.option_liu_kang,
            Character.option_kung_lao,
        )


class RedKoinPercent(Range):
    """
    There are 60 Red Koins in the item pool.
    Choose what percent of the 60 Red Koins are needed for goal.

    0 - the goal will be beating the boss goal only, will turn Red Koins to filler.
    80 (default) - get at least 80% of all Red Koins AND beat the boss goal to win.
    100 - get ALL 60 Red Koins AND beat the boss goal.

    There is a tracker in the pause menu that shows: current amount / needed for goal / total in the multiworld.
    """
    display_name = "Red Koin goal percent"
    range_start = 0
    range_end = 100

    default = 80


class BossGoal(Choice):
    """
    What bosses are needed for goal.
    The goal also includes getting enough Red Koins, set in the red_koin_need_percent option.

    no_bosses - no bosses at all are needed, the goal is Red Koins only.
    shao_kahn_only (default) - only the final boss of the game is needed for the goal.
    main_bosses - all main bosses (Kitana, Reptile, Baraka, Goro and Scorpion) and the final boss.
    main_and_secret_bosses - all previously mentioned bosses and all secret bosses (Ermac, Mileena and Kano).

    Setting this to no_bosses requires red_koin_need_percent to be above 0.
    """
    display_name = "Boss Goal"

    option_no_bosses = -1
    option_shao_kahn_only = 0
    option_main_bosses = 1
    option_main_and_secret_bosses = 2

    default = option_shao_kahn_only


class Fatalitysanity(DefaultOnToggle):
    """
    If on, adds checks for performing all of your character's different fatalities, multalities and brutality
    """
    display_name = "Fatalitysanity"


class SkipTutorial(Toggle):
    """
    Turn this option on to skip the turotials in Goro's Lair.
    Irrelevant when Wu-Shi start is on.
    """
    display_name = "Skip Tutorial"


class WuShiStart(Toggle):
    """
    If on, when pressing new game in the main menu, the game will start in Wu-Shi instead of Goro's Lair.
    You can get to Goro's Lair from Wu-Shi after getting the fist of ruin ability.
    This option allows for faster starts and more varied seeds.
    """
    display_name = "Wu-Shi Academy start"


@dataclass
class MKSMOptions(PerGameCommonOptions):
    character: Character
    red_koin_need_percent: RedKoinPercent
    boss_goal: BossGoal
    fatalitysanity: Fatalitysanity
    wu_shi_start: WuShiStart
    skip_tutorial: SkipTutorial
