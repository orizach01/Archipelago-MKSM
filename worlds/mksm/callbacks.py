"""
Callbacks.py

Per-tick game-state callbacks for the MKSM Archipelago client.
Minimal scope for now: detect collected red koins and report them.
Item granting / other location types come later.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .consts import GameState, DEFAULT_EVENT_ARRAY
from .locations import LOCATION_NAME_TO_ID

if TYPE_CHECKING:
    from .MKSMClient import MKSMContext


async def game_watcher(ctx: MKSMContext) -> None:
    """Called once per tick by the client's main loop."""
    if ctx.game_interface.current_game is None:
        return  # not connected to the emulator/game yet

    read_game_state(ctx)

    ctx.events_need_clear = ctx.game_state == GameState.MAIN_MENU
    clear_events(ctx)

    await sync_red_koins(ctx)
    await update_events_in_server(ctx)
    await check_red_koins(ctx)


def clear_events(ctx: MKSMContext):
    if ctx.prev_state == GameState.MAIN_MENU and ctx.game_state in (GameState.LOADING, GameState.INTRO_FMV):
        print("clearing events")
        print(f"{ctx.stored_data["EVENT_ARRAY"]=}")
        print(f"{ctx.stored_data["EVENT_ARRAY"] == DEFAULT_EVENT_ARRAY}")
        ctx.game_interface.clear_event_log(bytes(ctx.stored_data["EVENT_ARRAY"] or DEFAULT_EVENT_ARRAY))
        ctx.events_need_clear = False


async def update_events_in_server(ctx: MKSMContext):
    if not ctx.events_need_clear:
        await ctx.send_msgs([{"cmd": "Set",
                              "key": "EVENT_ARRAY",
                              "operations": [
                                  {
                                      "operation": "replace",
                                      "value": list(ctx.game_interface.get_event_block())
                                  }
                              ],
                              }])


def read_game_state(ctx) -> None:
    current_state = ctx.game_interface.get_game_state()
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
    checked_names = ctx.game_interface.get_checked_red_koins()
    if not checked_names:
        return

    location_ids = {LOCATION_NAME_TO_ID[name] for name in checked_names}
    await ctx.check_locations(location_ids)
