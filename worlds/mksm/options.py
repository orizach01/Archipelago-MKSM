from dataclasses import dataclass

from Options import Choice, PerGameCommonOptions


class Character(Choice):
    display_name = "Character"

    option_liu_kang = 0
    option_kung_lao = 1
    option_sub_zero = 2
    option_scorpion = 3

    default = option_liu_kang


@dataclass
class MKSMOptions(PerGameCommonOptions):
    character: Character
