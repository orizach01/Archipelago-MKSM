"""
Callbacks.py

Per-tick game-state callbacks for the MKSM Archipelago client.
Minimal scope for now: detect collected red koins and report them.
Item granting / other location types come later.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from NetUtils import ClientStatus
from .consts import GameState, DEFAULT_EVENT_ARRAY, EVENTS_TO_LOCATION_NAME, ANIMATIONS_TO_LOCATION_NAME
from .items import ITEM_NAME_TO_ID
from .locations import LOCATION_NAME_TO_ID

if TYPE_CHECKING:
    from .MKSMClient import MKSMContext


async def game_watcher(ctx: MKSMContext) -> None:
    """Called once per tick by the client's main loop."""
    # TODO red koin cmd
    # TODO debug cmd
    # TODO change filler to be XP
    if ctx.game_interface.current_game is None:
        return  # not connected to the emulator/game yet

    read_game_state(ctx)
    ctx.is_paused = ctx.game_interface.is_paused()
    clear_events(ctx)
    clear_xp(ctx)

    set_character(ctx)
    set_move_upgrades(ctx)
    set_abilities(ctx)
    set_health_upgrades(ctx)
    set_blood_bar(ctx)
    set_xp_items(ctx)
    update_koin_counter(ctx)

    await check_move_upgrades(ctx)
    await sync_red_koins(ctx)
    await update_events_in_server(ctx)
    await update_xp_in_server(ctx)
    await check_red_koins(ctx)
    await check_events(ctx)
    await check_finishing_moves(ctx)
    await check_completed_game(ctx)


def clear_events(ctx: MKSMContext):
    if ctx.prev_state == GameState.MAIN_MENU and ctx.game_state in (GameState.LOADING, GameState.INTRO_FMV):
        ctx.game_interface.clear_event_log(bytes(ctx.stored_data["EVENT_ARRAY"] or DEFAULT_EVENT_ARRAY))


def clear_xp(ctx: MKSMContext) -> None:
    if ctx.prev_state == GameState.MAIN_MENU and ctx.game_state in (GameState.LOADING, GameState.INTRO_FMV):
        ctx.game_interface.set_xp(ctx.stored_data["CURRENT_XP"] or 0)


async def update_events_in_server(ctx: MKSMContext) -> None:
    if not ctx.game_state == GameState.GAMEPLAY:
        return

    current_events = list(ctx.game_interface.get_event_block())
    if current_events == ctx.stored_data.get("EVENT_ARRAY"):
        return  # already in sync with the server, nothing to push
    await ctx.send_msgs([{"cmd": "Set",
                          "key": "EVENT_ARRAY",
                          "operations": [
                              {
                                  "operation": "replace",
                                  "value": current_events
                              }
                          ],
                          }])


async def update_xp_in_server(ctx: MKSMContext) -> None:
    if not ctx.game_state == GameState.GAMEPLAY:
        return

    current_xp = ctx.game_interface.get_current_xp()

    await ctx.send_msgs([{"cmd": "Set",
                          "key": "CURRENT_XP",
                          "operations": [
                              {
                                  "operation": "replace",
                                  "value": current_xp
                              }
                          ],
                          }])


def read_game_state(ctx) -> None:
    current_state = ctx.game_interface.get_game_state()
    if current_state != ctx.game_state:
        ctx.prev_state = ctx.game_state
        ctx.game_state = current_state


async def sync_red_koins(ctx: MKSMContext) -> None:
    """One-time sync run the first tick we have both a live game connection and
    server state: clears every red koin's bits in game memory except for the
    locations the AP server already considers checked. See
    MKSMInterface.clear_uncollected_red_koins for why."""
    if ctx.prev_state == GameState.MAIN_MENU and ctx.game_state in (GameState.LOADING, GameState.INTRO_FMV):
        koin_names = ctx.game_interface.addresses.get("RED_KOINS", {}).keys()
        checked_names = {name for name in koin_names if LOCATION_NAME_TO_ID[name] in ctx.checked_locations}
        ctx.game_interface.clear_uncollected_red_koins(checked_names)


async def check_red_koins(ctx: MKSMContext) -> None:
    if not ctx.game_state == GameState.GAMEPLAY:
        return

    checked_names = ctx.game_interface.get_checked_red_koins()
    if not checked_names:
        return

    location_ids = {LOCATION_NAME_TO_ID[name] for name in checked_names}
    await ctx.check_locations(location_ids)


async def check_move_upgrades(ctx: MKSMContext) -> None:
    if ctx.is_paused:
        current_upgrades = ctx.game_interface.get_upgrade_amounts()
        square = min(current_upgrades.square, 4)
        triangle = min(current_upgrades.triangle, 4)
        circle = min(current_upgrades.circle, 5)
        r2 = min(current_upgrades.r2, 5)
        checked_names = set()
        checked_names |= {f"Purchase upgrade - Square {i}" for i in range(2, square + 1)}
        checked_names |= {f"Purchase upgrade - Triangle {i}" for i in range(2, triangle + 1)}
        checked_names |= {f"Purchase upgrade - Circle {i}" for i in range(2, circle + 1)}
        checked_names |= {f"Purchase upgrade - R2 {i}" for i in range(2, r2 + 1)}

        prefixes = ["1st", "2nd", "3rd", "4th", "5th"]
        checked_names |= {f"Purchase {prefixes[i]} combo" for i in range(current_upgrades.combo)}

        if not checked_names:
            return

        location_ids = {LOCATION_NAME_TO_ID[name] for name in checked_names}
        await ctx.check_locations(location_ids)


def set_move_upgrades(ctx: MKSMContext) -> None:
    if ctx.is_paused:
        if not ctx.set_upgrades_in_pause:
            # set by checked
            square = sum(
                [
                    LOCATION_NAME_TO_ID[f"Purchase upgrade - Square {i}"] in ctx.checked_locations
                    for i in range(2, 5)
                ]
            )

            triangle = sum(
                [
                    LOCATION_NAME_TO_ID[f"Purchase upgrade - Triangle {i}"] in ctx.checked_locations
                    for i in range(2, 5)
                ]
            )

            circle = sum(
                [
                    LOCATION_NAME_TO_ID[f"Purchase upgrade - Circle {i}"] in ctx.checked_locations
                    for i in range(2, 6)
                ]
            )

            r2 = sum(
                [
                    LOCATION_NAME_TO_ID[f"Purchase upgrade - R2 {i}"] in ctx.checked_locations
                    for i in range(2, 6)
                ]
            )

            combo_1 = LOCATION_NAME_TO_ID[f"Purchase 1st combo"] in ctx.checked_locations
            combo_2 = LOCATION_NAME_TO_ID[f"Purchase 2nd combo"] in ctx.checked_locations
            combo_3 = LOCATION_NAME_TO_ID[f"Purchase 3rd combo"] in ctx.checked_locations
            combo_4 = LOCATION_NAME_TO_ID[f"Purchase 4th combo"] in ctx.checked_locations
            combo_5 = LOCATION_NAME_TO_ID[f"Purchase 5th combo"] in ctx.checked_locations

            ctx.game_interface.set_move_upgrades(square=square, triangle=triangle, circle=circle, r2=r2)
            ctx.game_interface.set_combos(combo_1=combo_1,
                                          combo_2=combo_2,
                                          combo_3=combo_3,
                                          combo_4=combo_4,
                                          combo_5=combo_5)

            ctx.set_upgrades_in_pause = True


    else:
        # set by received
        square = sum([1 for item in ctx.items_received if item.item == ITEM_NAME_TO_ID["Square special upgrade"]])
        triangle = sum([1 for item in ctx.items_received if item.item == ITEM_NAME_TO_ID["Triangle special upgrade"]])
        circle = sum([1 for item in ctx.items_received if item.item == ITEM_NAME_TO_ID["Circle special upgrade"]])
        r2 = sum([1 for item in ctx.items_received if item.item == ITEM_NAME_TO_ID["R2 special upgrade"]])

        square = min(square, 5)
        triangle = min(triangle, 5)
        circle = min(circle, 5)
        r2 = min(r2, 5)

        combo_1 = len([item for item in ctx.items_received if item.item == ITEM_NAME_TO_ID["Combo 1"]]) > 0
        combo_2 = len([item for item in ctx.items_received if item.item == ITEM_NAME_TO_ID["Combo 2"]]) > 0
        combo_3 = len([item for item in ctx.items_received if item.item == ITEM_NAME_TO_ID["Combo 3"]]) > 0
        combo_4 = len([item for item in ctx.items_received if item.item == ITEM_NAME_TO_ID["Combo 4"]]) > 0
        combo_5 = len([item for item in ctx.items_received if item.item == ITEM_NAME_TO_ID["Combo 5"]]) > 0

        ctx.game_interface.set_move_upgrades(square=square, triangle=triangle, circle=circle, r2=r2)
        ctx.game_interface.set_combos(combo_1=combo_1,
                                      combo_2=combo_2,
                                      combo_3=combo_3,
                                      combo_4=combo_4,
                                      combo_5=combo_5)

        ctx.set_upgrades_in_pause = False


def set_abilities(ctx: MKSMContext) -> None:
    wall_climb = int(any(item.item == ITEM_NAME_TO_ID["Wall Climb"] for item in ctx.items_received))
    wall_run = int(any(item.item == ITEM_NAME_TO_ID["Wall Run"] for item in ctx.items_received))
    wall_jump = int(any(item.item == ITEM_NAME_TO_ID["Wall Jump"] for item in ctx.items_received))
    double_jump = int(any(item.item == ITEM_NAME_TO_ID["Double Jump"] for item in ctx.items_received))
    long_jump = int(any(item.item == ITEM_NAME_TO_ID["Long Jump"] for item in ctx.items_received))
    swing = int(any(item.item == ITEM_NAME_TO_ID["Swing"] for item in ctx.items_received))
    fist_of_ruin = int(any(item.item == ITEM_NAME_TO_ID["Fist of Ruin"] for item in ctx.items_received))

    ctx.game_interface.set_abilities(
        wall_climb=wall_climb,
        wall_run=wall_run,
        wall_jump=wall_jump,
        double_jump=double_jump,
        long_jump=long_jump,
        swing=swing,
        fist_of_ruin=fist_of_ruin,
    )


async def check_events(ctx: MKSMContext) -> None:
    if not ctx.game_state == GameState.GAMEPLAY:
        return
    checked_events = set()
    current_events = list(ctx.game_interface.get_event_block())
    for i in range(0, len(current_events), 8):
        event = tuple(current_events[i:i + 8])
        if event in EVENTS_TO_LOCATION_NAME:
            checked_events.add(EVENTS_TO_LOCATION_NAME[event])

    if not checked_events:
        return

    location_ids = {LOCATION_NAME_TO_ID[name] for name in checked_events}
    await ctx.check_locations(location_ids)


def set_health_upgrades(ctx: MKSMContext) -> None:
    health_upgrades = sum(item.item == ITEM_NAME_TO_ID["Health upgrade"] for item in ctx.items_received)
    health_upgrades = min(health_upgrades, 4)

    ctx.game_interface.set_health_upgrades(health_upgrades)

    if ctx.health_upgrades != health_upgrades:
        ctx.game_interface.set_full_health(health_upgrades)
        ctx.health_upgrades = health_upgrades


def set_blood_bar(ctx: MKSMContext):
    blood_bar = sum(item.item == ITEM_NAME_TO_ID["Blood bar"] for item in ctx.items_received)
    blood_bar = min(blood_bar, 3)

    ctx.game_interface.set_blood_bar(blood_bar)


async def check_finishing_moves(ctx: MKSMContext) -> None:
    animation = ctx.game_interface.get_current_animation()

    if animation not in ANIMATIONS_TO_LOCATION_NAME:
        return

    loc_name = ANIMATIONS_TO_LOCATION_NAME[animation]
    await ctx.check_locations([LOCATION_NAME_TO_ID[loc_name]])


def update_koin_counter(ctx):
    total = ctx.slot_data["red_koin_amount"]
    needed = int(total * ctx.slot_data["red_koin_need_percent"] / 100)
    current = sum(item.item == ITEM_NAME_TO_ID["Red Koin"] for item in ctx.items_received)

    current = min(current, 99)
    needed = min(needed, 99)

    ctx.game_interface.set_koin_string(current, needed)


async def check_completed_game(ctx: MKSMContext):
    total = ctx.slot_data["red_koin_amount"]
    needed = int(total * ctx.slot_data["red_koin_need_percent"] / 100)
    current = sum(item.item == ITEM_NAME_TO_ID["Red Koin"] for item in ctx.items_received)
    beat_final_boss = LOCATION_NAME_TO_ID["F: Shao Kahn defeated"] in ctx.checked_locations

    if current >= needed and beat_final_boss:
        await ctx.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
        ctx.finished_game = True


def set_character(ctx: MKSMContext) -> None:
    character_option = ctx.slot_data["character"]
    ctx.game_interface.set_character(character_option)


def set_xp_items(ctx: MKSMContext) -> None:
    if not ctx.game_state == GameState.GAMEPLAY:
        return

    xp_items = sum(item.item == ITEM_NAME_TO_ID["5000 XP"] for item in ctx.items_received)

    if xp_items != ctx.xp_items_given:
        delta = xp_items - ctx.xp_items_given
        ctx.game_interface.add_xp(delta * 5000)
        ctx.xp_items_given = xp_items
