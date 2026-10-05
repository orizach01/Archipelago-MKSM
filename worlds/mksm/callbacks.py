"""
Callbacks.py

Per-tick game-state callbacks for the MKSM Archipelago client.
Minimal scope for now: detect collected red koins and report them.
Item granting / other location types come later.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from NetUtils import ClientStatus
from .consts import GameState, default_event_array, EVENTS_TO_LOCATION_NAME, ANIMATIONS_TO_LOCATION_NAME, \
    FOUNDRY_DOOR_OPEN_EVENT, TOURNAMENT_VICTORY_AMOUNT, \
    FILLER_EXP, EVENT_RECORD_SIZE, chunk_events, flatten_events, MAIN_MENU_NEW_GAME_OPTION, WU_SHI_START_AREA, \
    MANA_UPGRADE_AMOUNT, HEALTH_UPGRADE_AMOUNT
from .items import ITEM_NAME_TO_ID
from .locations import LOCATION_NAME_TO_ID
from .options import BossGoal

FINAL_BOSS_LOCATION = "F: Shao Kahn defeated"

MESSAGE_DISPLAY_SECONDS = 5.0

MAIN_BOSS_LOCATIONS = [
    "EM: Kitana Mileena and Jade defeated",
    "LF: Reptile defeated",
    "ST: Baraka defeated",
    "W: Goro defeated",
    "N: Scorpion defeated",
]

SECRET_BOSS_LOCATIONS = [
    "WSA: Ermac defeated",
    "LF: Mileena defeated",
    "F: Kano defeated",
]

if TYPE_CHECKING:
    from .MKSMClient import MKSMContext


async def game_watcher(ctx: MKSMContext, ap_connected: bool) -> None:
    """Called once per tick by the client's main loop."""
    # TODO traps
    # TODO open co op doors from start
    # TODO smoke missions
    # TODO find reptile beaten flag and set it to 1 to get brutality red koin
    # TODO group locations
    # TODO group options
    # TODO tweak max mana values so that you can double jump 4 times when maxed and 3 when 2
    # TODO fix combos check in order instead of separate per combo
    # TODO make docs/setup_en.md
    # TODO add fast wushi start option
    # TODO test if wall run is enough for scorpion fight

    if ap_connected and ctx.slot_data is not None:
        loop = asyncio.get_running_loop()
        current_time = loop.time()
        dt = current_time - ctx.last_time
        ctx.last_time = current_time

        read_game_state(ctx)
        clear_events(ctx)
        sync_foundry_door(ctx)
        clear_exp(ctx)

        set_wushi_start(ctx)
        set_character(ctx)
        set_move_upgrades(ctx)
        set_abilities(ctx)
        set_health_upgrades(ctx)
        set_mana_upgrades(ctx)
        set_blood_bar(ctx)
        update_koin_counter(ctx)
        update_tournament_victories_counter(ctx)
        force_ui(ctx)

        update_message(ctx, dt)

        await check_death(ctx)
        await check_move_upgrades(ctx)
        await check_red_koins(ctx)
        await check_events(ctx)
        await check_finishing_moves(ctx)
        await check_final_boss(ctx)
        await check_completed_game(ctx)
        await sync_red_koins(ctx)
        await update_events_in_server(ctx)
        await update_exp_in_server(ctx)
        await set_exp_items(ctx)


def clear_events(ctx: MKSMContext):
    if ctx.game_state == GameState.GAMEPLAY:
        return

    if ctx.event_array_key not in ctx.stored_data or ctx.stored_data[ctx.event_array_key] is None:
        server_array = default_event_array(ctx.slot_data)
    else:
        server_array = list(ctx.stored_data[ctx.event_array_key])

    ctx.game_interface.clear_event_log(bytes(server_array))


def sync_foundry_door(ctx: MKSMContext) -> None:
    if ctx.slot_data["randomize_tournament_victories"]:
        victories = sum(item.item == ITEM_NAME_TO_ID["Tournament victory"]
                        for item in ctx.items_received)

        should_be_closed = victories < TOURNAMENT_VICTORY_AMOUNT
    else:
        should_be_closed = not all(LOCATION_NAME_TO_ID[name] in ctx.checked_locations for name in MAIN_BOSS_LOCATIONS)

    if should_be_closed:
        ctx.game_interface.set_foundry_door_flag(0)
        return

    if ctx.game_state != GameState.GAMEPLAY:
        return

    current_events = list(ctx.game_interface.get_event_block())
    if FOUNDRY_DOOR_OPEN_EVENT in chunk_events(current_events):
        return

    # putting the event at the start of the log array to not mess with the autosave system
    new_array = flatten_events([FOUNDRY_DOOR_OPEN_EVENT]) + current_events
    ctx.game_interface.clear_event_log(bytes(new_array))


def clear_exp(ctx: MKSMContext) -> None:
    if ctx.game_state != GameState.GAMEPLAY:
        if ctx.current_exp_key not in ctx.stored_data:
            # current_exp not updated on the server yet
            return
        ctx.game_interface.set_exp(ctx.stored_data[ctx.current_exp_key] or 0)


async def update_events_in_server(ctx: MKSMContext) -> None:
    if ctx.game_state != GameState.GAMEPLAY:
        return

    current_events = list(ctx.game_interface.get_event_block())
    current_area = ctx.game_interface.get_current_area()

    events = chunk_events(current_events)
    server_array = ctx.stored_data.get(ctx.event_array_key) or []

    # removing current room's events from the end of the array while not currently saving the game
    if not ctx.game_interface.is_currently_saving():
        while len(events) > len(server_array) // EVENT_RECORD_SIZE and events[-1][0] == current_area:
            events.pop()

    filtered_array = flatten_events(events)

    if filtered_array == server_array or len(filtered_array) < len(server_array):
        return

    await ctx.send_msgs([{"cmd": "Set",
                          "key": ctx.event_array_key,
                          "operations": [
                              {
                                  "operation": "replace",
                                  "value": filtered_array
                              }
                          ],
                          }])


async def update_exp_in_server(ctx: MKSMContext) -> None:
    if not ctx.game_state == GameState.GAMEPLAY:
        return

    current_exp = ctx.game_interface.get_current_exp()
    server_exp = ctx.stored_data.get(ctx.current_exp_key) or 0

    if current_exp == 0 and server_exp > 0:
        # spending exp on upgrades legitimately lowers it, so a drop alone isn't suspicious -
        # but a hard drop to exactly 0 means we just read a spurious/incomplete value (e.g.
        # right after an emulator reset zeroed it before the game finished booting), not a
        # real purchase. Never push that to the server.
        # TODO this results in an infinite exp situation if i have e.g 5000 exp buy a combo
        #  and restart the game, the server will say i have 5000 exp
        #  its an exploit but not too harsh
        return

    await ctx.send_msgs([{"cmd": "Set",
                          "key": ctx.current_exp_key,
                          "operations": [
                              {
                                  "operation": "replace",
                                  "value": current_exp
                              }
                          ],
                          }])


def read_game_state(ctx) -> None:
    current_state = ctx.game_interface.get_game_state()
    if current_state != ctx.game_state:
        ctx.prev_state = ctx.game_state
        ctx.game_state = current_state
        # Both the read cache and the write skip key off TOTAL_EVENTS, which a save load
        # can leave unchanged while replacing the array wholesale. A load always passes
        # through a non-gameplay state, so drop both beliefs on every transition.
        ctx.game_interface.forget_event_log_state()


async def sync_red_koins(ctx: MKSMContext) -> None:
    """One-time sync run the first tick we have both a live game connection and
    server state: clears every red koin's bits in game memory except for the
    locations the AP server already considers checked. See
    MKSMInterface.clear_uncollected_red_koins for why."""
    if ctx.game_state != GameState.GAMEPLAY:
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
    if not ctx.is_paused:
        return

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
    checked_names |= {f"Purchase combo {i}" for i in range(1, current_upgrades.combo + 1)}

    if not checked_names:
        return

    location_ids = {LOCATION_NAME_TO_ID[name] for name in checked_names}
    await ctx.check_locations(location_ids)


# how many purchase tiers exist per move, i.e. range(2, stop) over the location names
_UPGRADE_TIERS = {"square": ("Square", 5), "triangle": ("Triangle", 5),
                  "circle": ("Circle", 6), "r2": ("R2", 6)}


def _upgrades_from_checked(ctx: MKSMContext):
    """What the pause menu should show: what the server says you have purchased."""
    counts = {
        key: sum(LOCATION_NAME_TO_ID[f"Purchase upgrade - {label} {i}"] in ctx.checked_locations
                 for i in range(2, stop))
        for key, (label, stop) in _UPGRADE_TIERS.items()
    }
    combos = [LOCATION_NAME_TO_ID[f"Purchase combo {i}"] in ctx.checked_locations for i in range(1, 6)]
    return counts, combos


def _upgrades_from_received(ctx: MKSMContext):
    """Your actual loadout during gameplay: what the server has granted you."""
    counts = {
        key: min(sum(item.item == ITEM_NAME_TO_ID[f"{label} special upgrade"]
                     for item in ctx.items_received), 5)
        for key, (label, _) in _UPGRADE_TIERS.items()
    }
    combos = [any(item.item == ITEM_NAME_TO_ID[f"Combo {i}"] for item in ctx.items_received)
              for i in range(1, 6)]
    return counts, combos


def _write_upgrades(ctx: MKSMContext, counts, combos) -> None:
    ctx.game_interface.set_move_upgrades(**counts)
    ctx.game_interface.set_combos(**{f"combo_{i}": value for i, value in enumerate(combos, 1)})


def on_pause_changed(ctx: MKSMContext, is_paused: bool) -> None:
    """Called straight from paused_task the moment the pause flag flips, rather than on
    the next tick. The game builds the pause menu from these values within a frame or
    two of setting the flag, and a tick is tens of milliseconds of blocking PINE work -
    far too late. Everything in here must stay cheap for the same reason."""
    if ctx.slot_data["shopsanity"]:
        if is_paused:
            _write_upgrades(ctx, *_upgrades_from_checked(ctx))
            ctx.set_upgrades_in_pause = True
        else:
            _write_upgrades(ctx, *_upgrades_from_received(ctx))
            ctx.set_upgrades_in_pause = False


def set_move_upgrades(ctx: MKSMContext) -> None:
    """Safety net for on_pause_changed: if an edge was missed because the loop was
    blocked inside a tick, this corrects it. Latched, so it is a no-op when the fast
    path already ran."""
    if ctx.slot_data["shopsanity"]:
        if ctx.is_paused:
            if not ctx.set_upgrades_in_pause:
                _write_upgrades(ctx, *_upgrades_from_checked(ctx))
                ctx.set_upgrades_in_pause = True
        else:
            _write_upgrades(ctx, *_upgrades_from_received(ctx))
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

    checked_events = {
        EVENTS_TO_LOCATION_NAME[event]
        for event in chunk_events(ctx.game_interface.get_event_block())
        if event in EVENTS_TO_LOCATION_NAME
    }

    if not checked_events:
        return

    location_ids = {LOCATION_NAME_TO_ID[name] for name in checked_events}
    await ctx.check_locations(location_ids)


def set_health_upgrades(ctx: MKSMContext) -> None:
    health_upgrades = sum(item.item == ITEM_NAME_TO_ID["Health upgrade"] for item in ctx.items_received)
    health_upgrades = min(health_upgrades, HEALTH_UPGRADE_AMOUNT)

    ctx.game_interface.set_health_upgrades(health_upgrades)

    if ctx.health_upgrades != health_upgrades:
        ctx.game_interface.set_full_health(health_upgrades)
        ctx.health_upgrades = health_upgrades


def set_blood_bar(ctx: MKSMContext):
    blood_bar = sum(item.item == ITEM_NAME_TO_ID["Blood bar"] for item in ctx.items_received)
    blood_bar = min(blood_bar, 3)

    ctx.game_interface.set_blood_bar(blood_bar)


async def check_finishing_moves(ctx: MKSMContext) -> None:
    if not ctx.slot_data["fatalitysanity"]:
        return

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
    total = min(total, 99)

    ctx.game_interface.set_koin_string(current, needed, total)


def update_tournament_victories_counter(ctx: MKSMContext):
    if not ctx.slot_data["randomize_tournament_victories"]:
        return

    current = sum(item.item == ITEM_NAME_TO_ID["Tournament victory"] for item in ctx.items_received)

    ctx.game_interface.set_tournament_string(current)


async def check_completed_game(ctx: MKSMContext):
    total = ctx.slot_data["red_koin_amount"]
    needed = int(total * ctx.slot_data["red_koin_need_percent"] / 100)
    current = sum(item.item == ITEM_NAME_TO_ID["Red Koin"] for item in ctx.items_received)

    boss_goal = ctx.slot_data["boss_goal"]
    required_boss_locations = []

    if boss_goal >= BossGoal.option_shao_kahn_only:
        required_boss_locations.append(FINAL_BOSS_LOCATION)
    if boss_goal >= BossGoal.option_main_bosses:
        required_boss_locations += MAIN_BOSS_LOCATIONS
    if boss_goal >= BossGoal.option_main_and_secret_bosses:
        required_boss_locations += SECRET_BOSS_LOCATIONS

    bosses_defeated = all(LOCATION_NAME_TO_ID[name] in ctx.checked_locations for name in required_boss_locations)

    if current >= needed and bosses_defeated:
        await ctx.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
        ctx.finished_game = True


def set_character(ctx: MKSMContext) -> None:
    character_option = ctx.slot_data["character"]
    ctx.game_interface.set_character(character_option)


async def check_death(ctx: MKSMContext) -> None:
    if ctx.game_state != GameState.GAMEPLAY:
        return

    is_dead = ctx.game_interface.is_dead()
    if is_dead and not ctx.was_dead and "DeathLink" in ctx.tags:
        await ctx.send_death("")
    ctx.was_dead = is_dead


async def set_exp_items(ctx: MKSMContext) -> None:
    if ctx.game_state != GameState.GAMEPLAY or ctx.exp_items_given_key not in ctx.stored_data:
        return

    exp_items = sum(item.item == ITEM_NAME_TO_ID[f"{FILLER_EXP} EXP"] for item in ctx.items_received)
    # stored_data is the cross-restart source of truth; ctx.exp_items_given is an
    # optimistic same-session cache so we don't re-grant while a Set is still in flight.
    exp_items_given = max(ctx.stored_data.get(ctx.exp_items_given_key) or 0, ctx.exp_items_given)

    if exp_items == exp_items_given:
        return

    delta = exp_items - exp_items_given

    if delta <= 0:
        ctx.exp_items_given = exp_items
        return

    ctx.game_interface.add_exp(delta * FILLER_EXP)
    ctx.exp_items_given = exp_items

    await ctx.send_msgs([{"cmd": "Set",
                          "key": ctx.exp_items_given_key,
                          "operations": [
                              {
                                  "operation": "replace",
                                  "value": exp_items
                              }
                          ],
                          }])


def update_message(ctx: MKSMContext, dt: float) -> None:
    if ctx.is_paused or ctx.game_interface.is_during_finishing_move():
        ctx.game_interface.set_default_exp_string()
        return

    if ctx.current_message is not None:
        ctx.message_timer += dt

        if ctx.message_timer < MESSAGE_DISPLAY_SECONDS:
            ctx.game_interface.set_message(ctx.current_message)
            return

        ctx.current_message = None
        ctx.message_timer = 0.0

    if ctx.message_queue:
        ctx.current_message = ctx.message_queue.popleft()
        ctx.message_timer = 0.0
        ctx.game_interface.set_message(ctx.current_message)
    else:
        ctx.game_interface.set_default_exp_string()


def force_ui(ctx: MKSMContext):
    ctx.game_interface.force_ui()


async def check_final_boss(ctx: MKSMContext):
    if ctx.game_state == GameState.GAME_BEATEN_FMV and ctx.prev_state == GameState.GAMEPLAY:
        await ctx.check_locations([LOCATION_NAME_TO_ID[FINAL_BOSS_LOCATION]])


def set_wushi_start(ctx: MKSMContext):
    if not ctx.slot_data["wu_shi_start"] or ctx.game_state != GameState.MAIN_MENU:
        return

    option = ctx.game_interface.main_menu_highlighted_option()
    if option != MAIN_MENU_NEW_GAME_OPTION:
        return

    ctx.game_interface.set_starting_area(WU_SHI_START_AREA)


def set_mana_upgrades(ctx: MKSMContext):
    if not ctx.slot_data["mana_upgrades"]:
        return

    mana_upgrades = sum(item.item == ITEM_NAME_TO_ID["Mana upgrade"] for item in ctx.items_received)
    mana_upgrades = min(mana_upgrades, MANA_UPGRADE_AMOUNT)

    ctx.game_interface.set_max_mana(mana_upgrades)
