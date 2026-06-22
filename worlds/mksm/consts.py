from dataclasses import dataclass
from enum import Enum

from .options import Character


@dataclass(frozen=True)
class CharacterPurchaseAmounts:
    combo: int
    square: int
    triangle: int
    circle: int
    r2: int


class GameState(Enum):
    BOOTING = 0x05
    MAIN_MENU = 0x08
    LOADING = 0x09
    GAMEPLAY = 0x0a
    GAME_BOOTING_FMVS = 0x10
    INTRO_FMV = 0x12
    GAME_BEATEN_FMV = 0x13
    CREDITS = 0x14
    UNKNOWN = 0xFF

    @classmethod
    def _missing_(cls, value):
        return cls.UNKNOWN


def _make_event(room: int, event: int):
    return [room, 0, 0, 0, event, 0, 0, 0]


CHARACTER_PURCHASE_AMOUNTS: dict[int, CharacterPurchaseAmounts] = {
    Character.option_liu_kang: CharacterPurchaseAmounts(combo=5, square=3, triangle=3, circle=2, r2=4),
    Character.option_kung_lao: CharacterPurchaseAmounts(combo=5, square=2, triangle=2, circle=4, r2=4),
    Character.option_sub_zero: CharacterPurchaseAmounts(combo=2, square=0, triangle=2, circle=2, r2=4),
    Character.option_scorpion: CharacterPurchaseAmounts(combo=3, square=2, triangle=2, circle=2, r2=4),
}

HEALTH_UPGRADE_AMOUNT = 4
BLOOD_BAR_AMOUNT = 3

ADDRESSES = {
    "SLUS-21087": {
        "RED_KOINS": {
            # Goro's Lair 1
            "GL: koin inside the skeleton": {0x005d829a: [1, 2, 3, 4, 5]},
            "GL: koin above the doorway": {0x005d828b: [6], 0x005d82a3: [6, 7], 0x005d82a4: [0, 1, 2, 3, 4]},
            "GL: koin from shooting the moon": {0x005d8295: [1], 0x005d829d: [7], 0x005d829e: [0]},
            "GL: koin on the ledge after the pit": {0x005d8291: [3, 4, 5, 6, 7], 0x005d8292: [0, 1, 2]},
            "GL: koin from the chandelier": {0x005d8298: [0, 1, 2]},
            "GL: koin above the breakable door": {0x005d82a7: [3]},

            # Goro's Lair 2
            "GL: koin on the ledge after the broken bridge": {0x005d8297: [4, 5, 6, 7], 0x005d82a5: [4]},

            # Wu-Shi
            "WSA: koin from the catapult": {0x005d8290: [2, 3, 4, 5, 6, 7], 0x005d8291: [0, 1, 2], 0x005d82a7: [1]},
            "WSA: koin after the tree branch swing": {0x005d8292: [3, 4, 5, 6]},
            "WSA: koin after the bamboo swing": {0x005d829d: [0, 1, 2], 0x005d82a8: [5]},
            "WSA: koin on a high wall near the lava pots": {0x005d82a5: [0]},

            # Wu-Shi - Ermac arena
            "WSA: koin from defeating Ermac": {0x005d82a1: [1, 2, 3, 4], 0x005d82a7: [2, 6]},

            # Wu-Shi - Fire
            "WSA: koin in the small room": {0x005d828b: [2], 0x005d8295: [6, 7], 0x005d8296: [0, 1, 2]},

            # Portal 2
            "P: koin from performing a fatality on the dragon symbol": {
                0x005d828c: [5, 6, 7], 0x005d828d: [0, 1, 2, 3, 4], 0x005d82a7: [5], 0x005d82a9: [1], 0x005d82aa: [0]
            },

            # Netherrealm
            "N: koin above the arch": {0x005d828e: [7], 0x005d828f: [0, 1, 2], 0x005d82a3: [3, 4, 5], 0x005d82a6: [5]},

            # Forest
            "LF: koin behind the breakable wall": {0x005d829c: [0, 1, 2], 0x005d82a6: [1], 0x005d82aa: [5]},
            "LF: koin behind the living tree": {0x005d82a5: [7]},
            "LF: koin hidden behind the waterfall": {0x005d828a: [4], 0x005d8299: [1, 2, 3]},
            "LF: koin near the giant snake head": {0x005d829c: [7], 0x005d829d: [5]},
            "LF: koin from shooting the closed eye": {0x005d82a7: [0]},

            # Forest - Bridges
            "LF: koin from shooting at dragon koin": {0x005d8298: [3, 4], 0x005d829b: [0]},
            "LF: koin from defeating Mileena": {0x005d82a6: [0]},

            # Forest - Reptile arena
            "LF: koin from breaking the fast statues": {0x005d82a1: [5, 6, 7], 0x005d82a8: [2, 3]},

            # Wasteland 1
            "W: koin from impaling an enemy on the big spike": {
                0x005d8296: [3], 0x005d829e: [4], 0x005d82a6: [4], 0x005d82aa: [2]
            },
            "W: koin on the ledge above": {0x005d82a9: [2]},
            "W: koin found after freeing kabal": {0x005d82a8: [1]},
            "W: koin from defeating the Oni Warlord in the blood bath room": {0x005d829b: [7], 0x005d829e: [2]},
            "W: koin found on the lion statue": {0x005d828b: [0], 0x005d829b: [4, 5, 6], 0x005d82a8: [7]},

            # Wasteland 2
            "W: koin found above the spike wheel": {0x005d829e: [3]},

            # Wasteland 3
            "W: koin from shooting the dragon koin": {0x005d828f: [5, 6, 7], 0x005d8290: [0, 1], 0x005d82aa: [3]},
            "W: koin from goro's arena": {0x005d8295: [2, 3], 0x005d82a8: [0]},

            # Dead Pool
            "DP: koin from drowning enemies in both pools": {0x005d828e: [2, 3, 4, 5, 6], 0x005d82a6: [2],
                                                             0x005d82a7: [4]},

            # Tombs
            "ST: koin from shooting the dragon koin near the portal": {
                0x005d828f: [3, 4], 0x005d82a9: [3], 0x005d82aa: [4]
            },
            "ST: koin above Baraka's entrance": {0x005d8293: [6, 7], 0x005d8294: [0], 0x005d82a9: [4]},
            "ST: koin from using all three death traps": {0x005d82ae: [4]},
            "ST: koin from the broken statue": {0x005d828c: [0]},
            "ST: koin above the broken statue": {0x005d828a: [3], 0x005d8294: [6, 7], 0x005d8295: [0], 0x005d82a9: [6]},
            "ST: koin from high button in the rolling spikes room": {0x005d828b: [7], 0x005d82a6: [3]},
            "ST: koin above the ceiling in the room with the hooks": {0x005d82a4: [7]},
            "ST: koin from shooting the dragon koin in the test your might room": {0x005d82a4: [6]},
            "ST: koin from killing the strolling skeleton": {
                0x005d82a0: [3, 4, 5, 6, 7], 0x005d82a1: [0], 0x005d82a5: [5], 0x005d82a7: [7]
            },
            "ST: koin from the button after defeating orochi hellbeast": {0x005d829f: [5, 6, 7], 0x005d82a0: [0, 1, 2]},
            "ST: koin from impaling an enemy on the rising spikes": {0x005d8294: [1, 2, 3], 0x005d82a9: [0]},
            "ST: koin from launching a tarkata on the flying bird": {0x005d829d: [3, 4], 0x005d829e: [1],
                                                                     0x005d82a5: [6]},
            "ST: koin behind statue in the falling spike trap room": {0x005d82ae: [6]},
            "ST: koin above broken statue in the falling spike trap room": {0x005d82a9: [5]},
            "ST: koin near the fan": {0x005d82a5: [1]},
            "ST: koin from the destroyed soul tomb": {
                0x005d8292: [7], 0x005d8293: [0, 1, 2, 3, 4, 5], 0x005d82a4: [5], 0x005d82a6: [7]
            },

            # Monastery
            "EM: koin from shooting the dragon koin behind the window": {0x005d8295: [4], 0x005d829d: [6],
                                                                         0x005d82a8: [4]},
            "EM: koin from impaling enemies on the statue's hands": {0x005d8298: [5, 6, 7], 0x005d8299: [0]},
            "EM: koin above the ceiling in the multality room": {0x005d828b: [1], 0x005d8297: [1, 2, 3],
                                                                 0x005d82a5: [2]},

            # Monastery - Kitana arena
            "EM: koin from the Kitana Mileena and Jade arena": {0x005d82a5: [3]},

            # Foundry
            "F: koin from wall jumping above the main room": {0x005d8295: [5]},
            "F: koin above the wood ceiling": {0x005d82a9: [7]},
            "F: koin from breaking the big pot": {0x005d828d: [5, 6, 7], 0x005d828e: [0, 1], 0x005d8294: [4]},
            "F: koin behind the fire": {0x005d829b: [1, 2, 3], 0x005d82a8: [6], 0x005d82aa: [1]},
            "F: koin from shooting the dragon koin behind the breakable wall": {
                0x005d8297: [0], 0x005d829a: [6, 7], 0x005d82a2: [0, 1, 2, 3]
            },
            "F: koin above the lava pit": {0x005d828a: [2], 0x005d8299: [4, 5, 6, 7], 0x005d829a: [0]},
            "F: koin from smash an enemy with the big hammers": {0x005d829c: [3, 4, 5, 6], 0x005d82a2: [4, 5, 6, 7]},
            "F: koin from breaking the pipe with the axe": {0x005d8296: [4, 5, 6, 7], 0x005d82a3: [0, 1, 2],
                                                            0x005d82a6: [6]},
        },
        "GAME_STATE": 0x5e1650,
        "TOTAL_EVENTS": 0xc2def0,
        "EVENT_LOG_ARRAY": 0xc2a070
    }
}

DEFAULT_EVENT_ARRAY = [
    # skip fatality event
    *_make_event(0x63, 0x15),
    *_make_event(0x63, 0x14),
    *_make_event(0x63, 0x3e),
    *_make_event(0x63, 0x37),
    *_make_event(0x63, 0x05),
    *_make_event(0x63, 0x3d),

    # skip multality event
    *_make_event(0xc2, 0x25),
    *_make_event(0xc2, 0x06),
    *_make_event(0xc2, 0x3b),
    *_make_event(0xc2, 0x1d),
    *_make_event(0xc2, 0x12),
    *_make_event(0xc2, 0x3c),

    # skip brutality event
    *_make_event(0x8e, 0x34),
    *_make_event(0x8e, 0x20),
    *_make_event(0x8e, 0x22),
    *_make_event(0x8e, 0x24),
    *_make_event(0x8e, 0x29),
    *_make_event(0x8e, 0x42),
]
