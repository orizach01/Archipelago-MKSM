from dataclasses import dataclass

from .options import Character


@dataclass(frozen=True)
class CharacterPurchaseAmounts:
    combo: int
    square: int
    triangle: int
    circle: int
    r2: int


CHARACTER_PURCHASE_AMOUNTS: dict[int, CharacterPurchaseAmounts] = {
    Character.option_liu_kang: CharacterPurchaseAmounts(combo=5, square=3, triangle=3, circle=2, r2=4),
    Character.option_kung_lao: CharacterPurchaseAmounts(combo=5, square=2, triangle=2, circle=4, r2=4),
    Character.option_sub_zero: CharacterPurchaseAmounts(combo=2, square=0, triangle=2, circle=2, r2=4),
    Character.option_scorpion: CharacterPurchaseAmounts(combo=3, square=2, triangle=2, circle=2, r2=4),
}

HEALTH_UPGRADE_AMOUNT = 4
BLOOD_BAR_AMOUNT = 3