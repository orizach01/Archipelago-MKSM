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


EVENT_RECORD_SIZE = 8
EVENT_LOG_SIZE = 16000  # bytes the game reserves for EVENT_LOG_ARRAY


def _make_event(room: int, event: int):
    return tuple([room, 0, 0, 0, event, 0, 0, 0])


def chunk_events(data) -> list[tuple[int, ...]]:
    """Split a flat event-log byte array into fixed-size event records."""
    return [tuple(data[i:i + EVENT_RECORD_SIZE]) for i in range(0, len(data), EVENT_RECORD_SIZE)]


def flatten_events(events) -> list[int]:
    """Inverse of chunk_events."""
    return [byte for event in events for byte in event]


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
            "LF: koin in the brutality room": {0x005d82a1: [5, 6, 7], 0x005d82a8: [2, 3]},

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
            "ST: koin from a high button in the rolling spikes room": {0x005d828b: [7], 0x005d82a6: [3]},
            "ST: koin above the ceiling in the room with the hooks": {0x005d82a4: [7]},
            "ST: koin from shooting the dragon koin in the test your might room": {0x005d82a4: [6]},
            "ST: koin from killing the strolling skeleton": {
                0x005d82a0: [3, 4, 5, 6, 7], 0x005d82a1: [0], 0x005d82a5: [5], 0x005d82a7: [7]
            },
            "ST: koin from the button in Orochi hellbeast's room": {0x005d829f: [5, 6, 7], 0x005d82a0: [0, 1, 2]},
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
        "EXP": 0xc2e224,
        "TOTAL_EVENTS": 0xc2def0,
        "EVENT_LOG_ARRAY": 0xc2a070,
        "PAUSE_FLAG": 0x4c49e8,

        "SQUARE_UPGRADE": 0xc29844,
        "TRIANGLE_UPGRADE": 0xc29845,
        "CIRCLE_UPGRADE": 0xc29846,
        "R2_UPGRADE": 0xc29847,

        "COMBO_1": 0xc29851,
        "COMBO_2": 0xc29852,
        "COMBO_3": 0xc29853,
        "COMBO_4": 0xc29854,
        "COMBO_5": 0xc29855,

        "WALL_CLIMB": 0xc29848,
        "WALL_RUN": 0xc29849,
        "WALL_JUMP": 0xc2984a,
        "DOUBLE_JUMP": 0xc2984b,
        "LONG_JUMP": 0xc2984c,
        "SWING": 0xc2984d,
        "FIST_OF_RUIN": 0xc2984e,

        "HEALTH_UPGRADES": 0xc29760,
        "MAX_HEALTH": (0xc29714, 0xc08930),
        "CUR_HEALTH": 0xc08928,

        "BLOOD_BAR": 0xc2e260,

        "CURRENT_ANIMATION": 0x5e6b64,

        "KOIN_FORMAT_STRING": 0x5777b8,
        "TIME_FORMAT_STRING": 0x5777c0,  # 14 spaces then NULL
        "RED_KOIN_STRING": 0xc47d00,
        "GAME_TIME_STRING": 0xc47b80,

        "CURRENT_CHARACTER": 0xc2974c,

        "DEBUG_MENU": (0x4c6fe0, 0x4c6fe4),

        "FORCE_UI_INST": 0x183eb8,
        "EXP_STRING": 0xc48380,
        "EXP_FMT": 0x5770d0,

        "CURRENT_AREA": 0xc29748,

        # A single boolean in a table of them, just past the event log, flipped 0 -> 1 when
        # Scorpion's medallion was picked up. Holding it at 0 keeps the game's medallion
        # count below five, so the portal cutscene that opens the foundry door never fires.
        # This is the only lever that works: the count is not in the event log (wiping it
        # changes nothing) and not in the ability flags, and the door-opening events can't
        # be stripped because 0x3e doubles as the cutscene's "already played" marker.
        "FOUNDRY_DOOR_FLAG": 0xc2e04c,

        "STARTING_AREA": 0x5e2fc4,
        "MAIN_MENU_OPTION": 0x5ca2ac,

        "MAX_MANA": (
            0x169838,
            0x18afe4,
        )
    }
}

EVENTS_TO_LOCATION_NAME = {
    _make_event(0x65, 0x11): "GL: Oni Warlord defeated",
    _make_event(0x65, 0x12): "GL: long jump obtained",
    _make_event(0x68, 0x6f): "WSA: wu-shi academy health upgrade",
    _make_event(0x6c, 0x5e): "WSA: Ermac defeated",
    _make_event(0x6a, 0x28): "WSA: wall run obtained",
    _make_event(0xa0, 0x8a): "N: Scorpion defeated",
    _make_event(0xa0, 0x8b): "N: Medallion from defeating Scorpion",
    _make_event(0x89, 0x2d): "LF: Forest health upgrade",
    _make_event(0x84, 0x48): "LF: Mileena defeated",
    _make_event(0x90, 0x0e): "LF: Reptile defeated",
    _make_event(0x90, 0x5a): "LF: climb obtained",
    _make_event(0x30, 0x5c): "W: Kabal freed",
    _make_event(0x21, 0x34): "W: Wasteland health upgrade",
    _make_event(0x2c, 0x0e): "W: Sub-Zero defeated",
    _make_event(0x2f, 0x05): "W: Goro defeated",
    _make_event(0x2f, 0x0c): "W: Goro defeated",
    _make_event(0x2f, 0x04): "W: Double jump obtained",
    _make_event(0x88, 0x10): "DP: swing obtained",
    _make_event(0x0f, 0x37): "ST: Baraka defeated",
    _make_event(0x0f, 0x2b): "ST: wall jump obtained",
    _make_event(0xc3, 0x3a): "EM: Kitana Mileena and Jade defeated",
    _make_event(0xc3, 0x3e): "EM: Fist of Ruin obtained",
    _make_event(0x48, 0x06): "F: Kano defeated",
}

# events that we want to automatically insert into every new run to avoid softlocks
# for example reaching the fatality room without a bloodbar will softlock the game
_DEFAULT_EVENT_ARRAY = [
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
    *_make_event(0x8e, 0x41),
    *_make_event(0x8e, 0x26),

    # events that spawn xp and the red koin in the brutality room
    # prevents needing to beat reptile to get that red koin
    # only one of the events here actually spawns the red koin, I didn't bother checking which one is it
    *_make_event(0x8e, 0x37),
    *_make_event(0x8e, 0x64),
    *_make_event(0x8e, 0x5d),
    *_make_event(0x8e, 0x5e),
    *_make_event(0x8e, 0x5f),
    *_make_event(0x8e, 0x60),
    *_make_event(0x8e, 0x61),
    *_make_event(0x8e, 0x62),
    *_make_event(0x8e, 0x63),
]

MOON_KOIN_EVENTS = [
    *_make_event(0x62, 0x3f),
    *_make_event(0x62, 0x44),
]

SHOOTING_KOIN_EVENTS = [
    *_make_event(0x8f, 0x29),  # forest eye         (forest map 16)
    *_make_event(0x84, 0x3b),  # forest bridges     (forest map 5)
    *_make_event(0x2e, 0x28),  # wasteland          (wasteland map 15)
    *_make_event(0x1e, 0x0e),  # tombs start        (tombs map 31)
    *_make_event(0x08, 0x1b),  # tombs test might   (tombs map 9)
    *_make_event(0xc4, 0x31),  # monastery window   (monastery map 6 -> 5)
    *_make_event(0x43, 0x2d),  # foundry            (foundry map 5 -> 4)
]

GOROS_LAIR_SKIP_EVENTS = [
    *_make_event(0x60, 0x42),
    *_make_event(0x60, 0x44),
    *_make_event(0x60, 0x50),
    *_make_event(0x60, 0xad),
    *_make_event(0x60, 0x49),
    *_make_event(0x60, 0x00),
    *_make_event(0x60, 0xaf),
    *_make_event(0x60, 0xa8),
    *_make_event(0x60, 0x4d),
    *_make_event(0x60, 0x3a),
    *_make_event(0x60, 0x4b),
    *_make_event(0x60, 0x11),
    *_make_event(0x60, 0x12),
    *_make_event(0x60, 0x4c),
    *_make_event(0x60, 0x01),
    *_make_event(0x60, 0x21),
    *_make_event(0x60, 0x22),
    *_make_event(0x60, 0xa0),
    *_make_event(0x60, 0x58),
    *_make_event(0x60, 0x6d),
    *_make_event(0x60, 0xc0),
    *_make_event(0x60, 0x6f),
    *_make_event(0x60, 0x91),
    *_make_event(0x60, 0xa1),
    *_make_event(0x60, 0x53),
    *_make_event(0x60, 0x6b),
    *_make_event(0x60, 0x90),
    *_make_event(0x60, 0xa2),
    *_make_event(0x60, 0x72),
    *_make_event(0x60, 0x8f),
    *_make_event(0x60, 0xa3),
    *_make_event(0x60, 0x4f),
    *_make_event(0x60, 0x9f),
    *_make_event(0x60, 0x8e),
    *_make_event(0x62, 0x02),
    *_make_event(0x62, 0x47),
    *_make_event(0x62, 0x0a),
    *_make_event(0x62, 0x3c),
    *_make_event(0x62, 0x05),
    *_make_event(0x64, 0x00),
    *_make_event(0x64, 0x27),
    *_make_event(0x64, 0x37),
    *_make_event(0x64, 0x30),
    *_make_event(0x64, 0x26),
    *_make_event(0x65, 0x15),
    *_make_event(0x65, 0x07),
    *_make_event(0x65, 0x3d),
    *_make_event(0x65, 0x41),
    *_make_event(0x65, 0x33),
    *_make_event(0x65, 0x4b),
    *_make_event(0x65, 0x2a),
    *_make_event(0x65, 0x2f),
]

WASTELAND_EVENTS = [
    # Pre goro
    *_make_event(0x2e, 0x24),
    *_make_event(0x2e, 0x12),
    *_make_event(0x2e, 0x25),
    *_make_event(0x2e, 0x19),
    *_make_event(0x2e, 0x1e),

    # Post goro
    *_make_event(0x2e, 0x1f),
    *_make_event(0x2e, 0x2e),
]


def default_event_array(slot_data):
    character = slot_data["character"]
    wu_shi_start = slot_data["wu_shi_start"]
    skip_tutorial = slot_data["skip_tutorial"]
    character = Character(character)
    default = _DEFAULT_EVENT_ARRAY.copy()

    default += WASTELAND_EVENTS

    if not character.can_shoot_moon():
        default += MOON_KOIN_EVENTS
    if character.is_vs():
        default += SHOOTING_KOIN_EVENTS
    if wu_shi_start or skip_tutorial:
        default += GOROS_LAIR_SKIP_EVENTS

    return default


# The event we inject to open the foundry door once the player has enough Tournament
# victories. The five medallion events in FOUNDRY_DOOR_EVENTS are visual only.
#
# (0xc1, 0x33) opens the door as well, but nothing needs it: we only ever add events here,
# never remove them. Stripping these does not gate the door anyway - 0x3e doubles as the
# portal cutscene's "already played" marker, so deleting it makes the cutscene replay on
# every transit and reopen the door each time. The gate is FOUNDRY_DOOR_FLAG instead.
FOUNDRY_DOOR_OPEN_EVENT = _make_event(0xc1, 0x3e)

ANIMATIONS_TO_LOCATION_NAME = {
    # Liu Kang:
    0x14e: "Perform Shaolin Soccer (Fatality)",
    0x150: "Perform Bonebreak Combo (Fatality)",
    0x152: "Perform Head Clap (Fatality)",
    0x154: "Perform Giant Stomp (Fatality)",
    0x156: "Perform Fire Kick Combo (Fatality)",
    0x158: "Perform Flipping Uppercut (Fatality)",
    0x15a: "Perform Dragon (Fatality)",
    0x15c: "Perform Arm Rip (Fatality)",
    0x160: "Perform Fire Trails (Multality)",
    0x161: "Perform Dragon Fury (Multality)",
    0x165: "Perform Rage Mode (Brutality)",

    # Kung Lao:
    0x1f0: "Perform Body Slice (Fatality)",
    0x1f2: "Perform Mid Air Slice (Fatality)",
    0x1f7: "Perform Friendly Rabit (Fatality)",
    0x1f4: "Perform Tornado (Multality)",
    0x1f6: "Perform Hat Control (Multality)",
    0x1f9: "Perform Arm Cutter (Fatality)",
    0x1fb: "Perform Head Toss (Fatality)",
    0x1fd: "Perform Unfriendly Rabbit (Hidden Fatality)",
    0x1ff: "Perform Many Chops (Fatality)",
    0x201: "Perform Headache (Fatality)",
    0x203: "Perform Buzzsaw (Fatality)",
    0x200: "Perform Razor Edge (Brutality)",

    # Sub-Zero:
    0xa5f: "Perform Spine Rip (Fatality)",
    0xa61: "Perform Snowball (Fatality)",
    0xa63: "Perform Freeze Uppercut (Fatality)",
    0xa65: "Perform Ice Stomp (Multality)",
    0xa69: "Perform Frostbite Rage (Brutality)",

    # Scorpion:
    0x853: "Perform Flame (Fatality)",
    0x855: "Perform Spear Slice (Fatality)",
    0x857: "Perform Raise Hell (Multality)",
    0x863: "Perform Searing Blade (Brutality)",

    # Baraka:
    0x8f3: "Perform Decapitation (Fatality)",
    0x8f5: "Perform Blade Lift (Fatality)",

    # Kitana:
    0xb0b: "Perform Kiss of Death (Fatality)",
    0xb0d: "Perform Head Chop (Fatality)",

    # Reptile:
    0x97e: "Perform Head Eat (Fatality)",
    0x980: "Perform Hidden Chomp (Fatality)",
    0x97c: "Perform Face Claw (Fatality)",

    # Johnny Cage:
    0xb9e: "Perform Torso Rip (Fatality)",
    0xba0: "Perform Head Decaptation (Fatality)",
    0xb9b: "Perform Nut Buster (Fatality)",
}

CHARACTER_OPTION_TO_VALUE_IN_GAME = {
    Character.option_liu_kang: 0x00,
    Character.option_kung_lao: 0x01,
    Character.option_sub_zero: 0x58,
    Character.option_scorpion: 0x52,
    Character.option_baraka: 0x53,
    Character.option_kitana: 0x59,
    Character.option_reptile: 0x54,
    Character.option_johnny_cage: 0x5a,

}

NO_DEBUG = (0x000001a5, 0x001aa630)
YES_DEBUG = (0x0000019f, 0x001aae80)

DEFAULT_EXP_STRING = "Exp: "
DEFAULT_EXP_FMT = "%s %d"
MESSAGE_EXP_FMT = "%s"

BUTTONS_ASCII = {
    "Square": 0x2a,
    "Triangle": 0x7e,
    "Circle": 0x7c,
    "R2": 0x5e,
}

FILLER_EXP = 1000

CHARACTER_PURCHASE_AMOUNTS: dict[int, CharacterPurchaseAmounts] = {
    Character.option_liu_kang: CharacterPurchaseAmounts(combo=5, square=3, triangle=3, circle=2, r2=4),
    Character.option_kung_lao: CharacterPurchaseAmounts(combo=5, square=2, triangle=2, circle=4, r2=4),
    Character.option_sub_zero: CharacterPurchaseAmounts(combo=2, square=0, triangle=2, circle=2, r2=4),
    Character.option_scorpion: CharacterPurchaseAmounts(combo=3, square=2, triangle=2, circle=2, r2=4),
}

CHARACTER_PURCHASE_AMOUNTS |= {
    Character.option_baraka: CHARACTER_PURCHASE_AMOUNTS[Character.option_liu_kang],
    Character.option_kitana: CHARACTER_PURCHASE_AMOUNTS[Character.option_liu_kang],
    Character.option_reptile: CHARACTER_PURCHASE_AMOUNTS[Character.option_liu_kang],
    Character.option_johnny_cage: CHARACTER_PURCHASE_AMOUNTS[Character.option_liu_kang],
}

HEALTH_UPGRADE_AMOUNT = 4

BLOOD_BAR_AMOUNT = 3

SAVING_ANIMATION = 0xF
ABILITY_ANIMATION = 0x10

# How many Tournament victory items exist, and so how many are needed to open the foundry
# door. One constant on purpose: items.py builds the pool from it, rules.py gates the
# Foundry region on having them all, and callbacks.py holds FOUNDRY_DOOR_FLAG down until
# the player has this many. If the logic's threshold and the client's ever diverged,
# generation would place items behind a door the client refuses to open.
TOURNAMENT_VICTORY_AMOUNT = 5

WU_SHI_START_AREA = 0x67

MAIN_MENU_NEW_GAME_OPTION = 0

MAX_MANA_UPGRADE_VALUES = {
    0: 0x42c8,  # 100.0 (vanilla)
    1: 0x42fa,  # 125.0
    2: 0x4316,  # 150.0
    3: 0x432f,  # 175.0
    4: 0x4348,  # 200.0
}

MANA_UPGRADE_AMOUNT = max(MAX_MANA_UPGRADE_VALUES.keys())