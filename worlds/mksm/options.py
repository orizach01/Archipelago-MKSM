from dataclasses import dataclass

from Options import Choice, PerGameCommonOptions, Range


class Character(Choice):
    display_name = "Character"

    option_liu_kang = 0
    option_kung_lao = 1
    option_sub_zero = 2
    option_scorpion = 3

    default = option_liu_kang


class RedKoinPercent(Range):
    display_name = "Red Koin completion percent"
    range_start = 0
    range_end = 100

    default = 80


@dataclass
class MKSMOptions(PerGameCommonOptions):
    character: Character
    red_koin_need_percent: RedKoinPercent
