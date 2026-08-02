"""
MKSMClient.py

Archipelago client for Mortal Kombat: Shaolin Monks.
Connects to a running PCSX2 instance via the PINE protocol and bridges
location checks to the Archipelago server.

Minimal scope for now: detects collected red koins only. Item granting
and other location categories come later.
"""

from __future__ import annotations

import asyncio
import logging
import multiprocessing
import sys
import traceback
import typing
from typing import Optional
from collections import deque

from BaseClasses import ItemClassification
# CommonClient import first to trigger ModuleUpdater
from CommonClient import CommonContext, server_loop, get_base_parser, handle_url_arg, logger, \
    ClientCommandProcessor, gui_enabled

import Utils
from worlds.mksm.consts import GameState, DEFAULT_EVENT_ARRAY, EVENTS_TO_LOCATION_NAME

from .MKSMInterface import MKSMInterface
from .callbacks import game_watcher as run_callbacks

EMULATOR_RECONNECT_DELAY = 5  # seconds between PCSX2 connection attempts


class MKSMCommandProcessor(ClientCommandProcessor):
    ctx: MKSMContext

    # def _cmd_exp(self, value: str = "1000") -> bool:
    #     """Add given exp
    #     Usage: /exp   or   /exp 5000"""
    #     ctx: MKSMContext = self.ctx
    #     ctx.game_interface.add_exp(int(value))
    #     self.output(f"Added {value} EXP")
    #     return True

    # def _cmd_health(self):
    #     """
    #     prints current health status
    #     """
    #     ctx: MKSMContext = self.ctx
    #     print(ctx.game_interface.health_status())
    #     return True

    def _cmd_events(self, n: str = "5") -> bool:
        """prints the current room and the last n events in the server's saved event log
        Usage: /events   or   /events 10"""
        ctx: MKSMContext = self.ctx
        current_events = list(ctx.stored_data.get("EVENT_ARRAY") or [])
        events = [tuple(current_events[i:i + 8]) for i in range(0, len(current_events), 8)]

        if not events:
            self.output("event log is empty")
            return True

        self.output(f"current room: {hex(events[-1][0])}")

        for event in events[-int(n):]:
            room, event_code = event[0], event[4]
            location_name = EVENTS_TO_LOCATION_NAME.get(event, "<unmapped>")
            self.output(f"room={hex(room)} event={hex(event_code)} ({location_name})")

        return True

    def _cmd_debug(self) -> bool:
        """
        Toggles whether the Debug menu replaces the options in the pause screen
        """
        ctx: MKSMContext = self.ctx
        if not ctx.game_interface.get_connection_state():
            self.output("can't toggle debug menu - not connected to the game.")
            return False

        is_debug = ctx.game_interface.toggle_debug_menu()

        if is_debug:
            self.output("Debug Menu turned ON")
        else:
            self.output("Debug Menu turned OFF")

        return True

    def _cmd_connect(self, address: str = "") -> bool:
        """Connect to a MultiWorld Server"""
        ctx: MKSMContext = self.ctx
        if not ctx.ready_to_connect():
            self.output("can't connect - not at the main menu.")
            return False
        return super()._cmd_connect(address)

    async def _cmd_removeevent(self) -> bool:
        """removes all events from the room the last event happened in, use in cases of
        softlocks if exited at wrong times, use only on main menu"""
        ctx: MKSMContext = self.ctx
        if ctx.game_state != GameState.MAIN_MENU:
            self.output("only use /removeevents on main menu")
            return True

        current_events = ctx.stored_data.get("EVENT_ARRAY")

        if not current_events or current_events == DEFAULT_EVENT_ARRAY:
            self.output("no event to remove")
            return True

        events = [tuple(current_events[i:i + 8]) for i in range(0, len(current_events), 8)]
        default_events = {tuple(DEFAULT_EVENT_ARRAY[i:i + 8]) for i in range(0, len(DEFAULT_EVENT_ARRAY), 8)}
        last_room = events[-1][0]
        self.output(f"Removing non-default events from last room: {hex(last_room)}")
        remaining_events = [
            event for event in events
            if event[0] != last_room or event in default_events
        ]
        new_array = [byte for event in remaining_events for byte in event]

        await ctx.send_msgs([{"cmd": "Set",
                              "key": "EVENT_ARRAY",
                              "operations": [
                                  {
                                      "operation": "replace",
                                      "value": new_array
                                  }
                              ],
                              }])

        return True

    async def _cmd_default(self) -> bool:
        """adds the default event array's entries back into the current event array
        (without removing anything already there)"""
        ctx: MKSMContext = self.ctx

        current_events = list(ctx.stored_data.get("EVENT_ARRAY") or [])
        existing = {tuple(current_events[i:i + 8]) for i in range(0, len(current_events), 8)}
        default_events = [tuple(DEFAULT_EVENT_ARRAY[i:i + 8]) for i in range(0, len(DEFAULT_EVENT_ARRAY), 8)]

        missing_events = [event for event in default_events if event not in existing]
        new_array = current_events + [byte for event in missing_events for byte in event]

        ctx.game_interface.clear_event_log(bytes(new_array))

        await ctx.send_msgs([{"cmd": "Set",
                              "key": "EVENT_ARRAY",
                              "operations": [
                                  {
                                      "operation": "replace",
                                      "value": new_array
                                  }
                              ],
                              }])

        return True

    async def _cmd_deathlink(self):
        ctx: MKSMContext = self.ctx
        is_death_link = "DeathLink" in ctx.tags
        self.output(f"Setting Death Link: {not is_death_link}")
        await ctx.update_death_link(not is_death_link)


class MKSMContext(CommonContext):
    game = "Mortal Kombat: Shaolin Monks"
    items_handling = 0b111  # receive all items, even though we don't act on them yet
    want_slot_data = True
    command_processor = MKSMCommandProcessor
    game_interface: MKSMInterface
    game_state: GameState
    prev_state: GameState
    is_paused: bool
    set_upgrades_in_pause: bool = False
    health_upgrades: int = 0
    exp_items_given: int = 0
    first_loop: bool
    pending_server_address: str | None
    emulator_settled: bool
    was_dead: bool
    message_queue: deque
    message_timer: float | None
    current_message: str | None
    last_time: float
    last_error_message: Optional[str] = None

    def __init__(self, server_address: str | None, password: str | None) -> None:
        super().__init__(server_address, password)
        self.is_connected_to_server = False
        self.is_connected_to_game = False
        self.is_paused = False
        self.game_interface = MKSMInterface(logger)
        self.game_state = GameState.BOOTING
        self.prev_state = GameState.BOOTING
        self.slot_data = None
        self.first_loop = True
        self.pending_server_address = None
        self.emulator_settled = False
        self.was_dead = False
        self.message_queue = deque()
        self.message_timer = None  # None means no message is currently being displayed
        self.current_message = None

    def ready_to_connect(self) -> bool:
        return self.is_connected_to_game and self.game_interface.get_game_state() == GameState.MAIN_MENU

    async def connect(self, address: str | None = None) -> None:
        # gates the GUI's Connect button too, since it calls ctx.connect() directly
        # rather than going through the command processor's _cmd_connect.
        if not self.ready_to_connect():
            logger.info("can't connect - not at the main menu.")
            return
        await super().connect(address)

    async def server_auth(self, password_requested: bool = False) -> None:
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_package(self, cmd: str, args: dict) -> None:
        if cmd == "Connected":
            self.slot_data = args.get("slot_data", {})

    def on_deathlink(self, data: typing.Dict[str, typing.Any]) -> None:
        super().on_deathlink(data)
        self.game_interface.kill_player()

    def on_print_json(self, args: dict):
        super().on_print_json(args)

        if "type" in args and args["type"] == "ItemSend":
            item = args["item"]
            recipient = args["receiving"]

            # Receiving an item from the server
            if self.slot_concerns_self(recipient):
                item_name = self.item_names.lookup_in_game(item.item)

                if self.slot_concerns_self(item.player):
                    # found self item
                    location_name = self.location_names.lookup_in_game(item.location)
                    message = f"Found {item_name} ({location_name})"
                    self.message_queue.append(message)
                else:
                    # got from someone else
                    finder = self.player_names[item.player]
                    location_name = self.location_names.lookup_in_slot(item.location, item.player)
                    message = f"Received {item_name} from {finder} ({location_name})"
                    self.message_queue.append(message)

            # Sending an item to the server.
            elif self.slot_concerns_self(item.player):
                item_name = self.item_names.lookup_in_slot(item.item, recipient)

                owner = self.player_names[recipient]

                location_name = self.location_names.lookup_in_game(item.location)

                message = f"Sent {item_name} to {owner} ({location_name})"
                self.message_queue.append(message)


def update_connection_status(ctx: MKSMContext, status: bool):
    if ctx.is_connected_to_game == status:
        return

    if status:
        logger.info("Connected to MKSM")
    else:
        logger.info("Unable to connect to the PCSX2 instance, attempting to reconnect...")

    ctx.is_connected_to_game = status


async def paused_task(ctx: MKSMContext):
    while not ctx.exit_event.is_set():
        try:
            if ctx.is_connected_to_game:
                ctx.is_paused = ctx.game_interface.is_paused()
            await asyncio.sleep(0.00001)
        except ConnectionError:
            ctx.game_interface.disconnect_from_game()
        except Exception as e:
            if isinstance(e, RuntimeError):
                logger.error(str(e))
            else:
                logger.error(traceback.format_exc())
            await asyncio.sleep(3)
            continue


async def pcsx2_sync_task(ctx: MKSMContext):
    logger.info("Starting MKSM Connector, attempting to connect to emulator...")
    ctx.game_interface.connect_to_game()
    while not ctx.exit_event.is_set():
        try:
            is_connected = ctx.game_interface.get_connection_state()
            update_connection_status(ctx, is_connected)
            if is_connected:
                await _handle_game_ready(ctx)
            else:
                await _handle_game_not_ready(ctx)
        except ConnectionError:
            ctx.game_interface.disconnect_from_game()
        except Exception as e:
            if isinstance(e, RuntimeError):
                logger.error(str(e))
            else:
                logger.error(traceback.format_exc())
            await asyncio.sleep(3)
            continue


async def _handle_game_ready(ctx: MKSMContext) -> None:
    connected_to_server = (ctx.server is not None) and (ctx.slot is not None)

    new_connection = ctx.is_connected_to_server != connected_to_server

    if new_connection:
        loop = asyncio.get_running_loop()
        ctx.last_time = loop.time()

    await run_callbacks(ctx, connected_to_server)

    if ctx.server:
        ctx.last_error_message = None
        if not ctx.slot:
            await asyncio.sleep(1)
            return

        await asyncio.sleep(0.001)
    else:
        message = "Waiting for player to connect to server"
        if ctx.last_error_message is not message:
            logger.info("Waiting for player to connect to server")
            ctx.last_error_message = message
        await asyncio.sleep(1)


async def _handle_game_not_ready(ctx: MKSMContext):
    """If the game is not connected, this will attempt to retry connecting to the game."""
    ctx.game_interface.connect_to_game()
    await asyncio.sleep(3)


def launch_client():
    Utils.init_logging("MKSM Client")

    async def main():
        multiprocessing.freeze_support()
        logger.info("main")
        parser = get_base_parser()
        args = parser.parse_args()
        ctx = MKSMContext(args.connect, args.password)

        logger.info("Connecting to server...")
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="Server Loop")
        ctx.tags.add("Client")

        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()

        ctx.set_notify("EVENT_ARRAY")
        ctx.set_notify("CURRENT_EXP")
        ctx.set_notify("EXP_ITEMS_GIVEN")

        logger.info("Running game...")
        ctx.pcsx2_sync_task = asyncio.create_task(pcsx2_sync_task(ctx), name="PCSX2 Sync")
        ctx.is_paused_task = asyncio.create_task(paused_task(ctx), name="Paused Sync")

        await ctx.exit_event.wait()
        ctx.server_address = None

        await ctx.shutdown()

        if ctx.pcsx2_sync_task:
            await asyncio.sleep(3)
            await ctx.pcsx2_sync_task

        if ctx.is_paused_task:
            await asyncio.sleep(3)
            await ctx.is_paused_task

    import colorama

    colorama.init()

    asyncio.run(main())
    colorama.deinit()


if __name__ == "__main__":
    launch_client()
