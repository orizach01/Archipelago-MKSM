"""
MKSMClient.py

Archipelago client for Mortal Kombat: Shaolin Monks.
Connects to a running PCSX2 instance via the PINE protocol and bridges
location checks and received items to the Archipelago server.
"""

from __future__ import annotations

import asyncio
import multiprocessing
import traceback
import typing
from collections import deque

# CommonClient import first to trigger ModuleUpdater
from CommonClient import CommonContext, server_loop, get_base_parser, handle_url_arg, logger, \
    ClientCommandProcessor, gui_enabled

import Utils
from worlds.mksm.consts import GameState, DEFAULT_EVENT_ARRAY, EVENTS_TO_LOCATION_NAME, \
    chunk_events, flatten_events

from .MKSMInterface import MKSMInterface
from .callbacks import game_watcher as run_callbacks, on_pause_changed

EMULATOR_RECONNECT_DELAY = 5  # seconds between PCSX2 connection attempts
TICK_INTERVAL = 0.01  # seconds between full game_watcher passes
MAX_QUEUED_MESSAGES = 20  # cap on the in-game ticker backlog


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
        """prints the last event's room and the last n events in the server's saved event log
        Usage: /events   or   /events 10"""
        ctx: MKSMContext = self.ctx
        try:
            count = max(int(n), 1)
        except ValueError:
            self.output(f"'{n}' is not a number")
            return False

        events = chunk_events(ctx.stored_data.get("EVENT_ARRAY") or [])

        if not events:
            self.output("event log is empty")
            return True

        # this reads the server's stored array, not live game memory, so it's whatever
        # room last logged an event rather than necessarily where the player is now.
        self.output(f"last event's room: {hex(events[-1][0])}")

        for event in events[-count:]:
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

    async def _cmd_removeevent(self) -> bool:
        """removes all events from the room the last event happened in, use in cases of
        softlocks if exited at wrong times, use only on main menu"""
        ctx: MKSMContext = self.ctx
        if ctx.game_state != GameState.MAIN_MENU:
            self.output("only use /removeevent on the main menu")
            return True

        current_events = ctx.stored_data.get("EVENT_ARRAY")

        if not current_events or current_events == DEFAULT_EVENT_ARRAY:
            self.output("no event to remove")
            return True

        events = chunk_events(current_events)
        default_events = set(chunk_events(DEFAULT_EVENT_ARRAY))
        last_room = events[-1][0]
        self.output(f"Removing non-default events from last room: {hex(last_room)}")
        remaining_events = [
            event for event in events
            if event[0] != last_room or event in default_events
        ]
        new_array = flatten_events(remaining_events)

        # no clear_event_log here on purpose: clear_events() pushes the server array back
        # into the game on the next non-gameplay tick, which the main-menu guard guarantees.
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
        if not ctx.game_interface.get_connection_state():
            self.output("can't restore default events - not connected to the game.")
            return False
        if ctx.game_state == GameState.GAMEPLAY:
            self.output("only use /default outside of gameplay.")
            return False

        current_events = list(ctx.stored_data.get("EVENT_ARRAY") or [])
        existing = set(chunk_events(current_events))

        missing_events = [event for event in chunk_events(DEFAULT_EVENT_ARRAY) if event not in existing]
        new_array = current_events + flatten_events(missing_events)

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
    items_handling = 0b111  # receive all items, including our own and starting inventory
    want_slot_data = True
    command_processor = MKSMCommandProcessor
    game_interface: MKSMInterface
    game_state: GameState
    prev_state: GameState
    is_paused: bool
    set_upgrades_in_pause: bool = False
    moves_label_synced: bool | None = None  # None means nothing written yet
    health_upgrades: int = 0
    exp_items_given: int = 0
    pending_server_address: str | None
    was_dead: bool
    message_queue: deque
    message_timer: float | None
    current_message: str | None
    last_time: float
    last_error_message: str | None = None
    pcsx2_sync_task: asyncio.Task | None = None
    is_paused_task: asyncio.Task | None = None

    def __init__(self, server_address: str | None, password: str | None) -> None:
        super().__init__(server_address, password)
        self.is_connected_to_server = False
        self.is_connected_to_game = False
        self.is_paused = False
        self.game_interface = MKSMInterface(logger)
        self.game_state = GameState.BOOTING
        self.prev_state = GameState.BOOTING
        self.slot_data = None
        self.pending_server_address = None
        self.was_dead = False
        self.message_queue = deque(maxlen=MAX_QUEUED_MESSAGES)
        self.message_timer = None  # None means no message is currently being displayed
        self.current_message = None

    def ready_to_connect(self) -> bool:
        return self.is_connected_to_game and self.game_interface.get_game_state() == GameState.MAIN_MENU

    async def connect(self, address: str | None = None) -> None:
        # gates the GUI's Connect button and /connect, since both route through here.
        if not self.ready_to_connect():
            self.pending_server_address = address or self.server_address
            logger.info("can't connect yet - will connect once the game reaches the main menu.")
            return
        self.pending_server_address = None
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
                now_paused = ctx.game_interface.is_paused()
                if now_paused != ctx.is_paused:
                    ctx.is_paused = now_paused
                    # Respond on the same iteration that saw the edge. Leaving it to
                    # game_watcher costs a whole tick of blocking PINE work, by which
                    # point the game has already built the pause menu from these values.
                    if ctx.slot_data is not None and ctx.server is not None and ctx.slot is not None:
                        on_pause_changed(ctx, now_paused)
            # A bare yield, not a timed sleep: on Windows any nonzero delay rounds up to
            # the ~15.6ms timer granularity, which is a whole PS2 frame. sleep(0) is
            # special-cased to skip the timer entirely and reschedules in ~0.05ms.
            await asyncio.sleep(0)
        except ConnectionError:
            # Clear the flag here rather than waiting for pcsx2_sync_task to notice: that
            # task can only run if we hand the loop back, and without both the clear and
            # the sleep this handler spins forever on a dead socket, freezing the client.
            ctx.game_interface.disconnect_from_game()
            update_connection_status(ctx, False)
            await asyncio.sleep(EMULATOR_RECONNECT_DELAY)
        except RuntimeError as e:
            logger.error(str(e))
            await asyncio.sleep(3)
        except Exception:
            logger.error(traceback.format_exc())
            await asyncio.sleep(3)


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
            update_connection_status(ctx, False)
            await asyncio.sleep(EMULATOR_RECONNECT_DELAY)
        except RuntimeError as e:
            logger.error(str(e))
            await asyncio.sleep(3)
        except Exception:
            logger.error(traceback.format_exc())
            await asyncio.sleep(3)


async def _handle_game_ready(ctx: MKSMContext) -> None:
    connected_to_server = (ctx.server is not None) and (ctx.slot is not None)

    if ctx.is_connected_to_server != connected_to_server:
        ctx.is_connected_to_server = connected_to_server
        ctx.last_time = asyncio.get_running_loop().time()

    await _try_pending_connect(ctx)
    await run_callbacks(ctx, connected_to_server)

    if ctx.server:
        ctx.last_error_message = None
        if not ctx.slot:
            await asyncio.sleep(1)
            return

        await asyncio.sleep(TICK_INTERVAL)
    else:
        message = "Waiting for player to connect to server"
        if ctx.last_error_message != message:
            logger.info(message)
            ctx.last_error_message = message
        await asyncio.sleep(1)


async def _try_pending_connect(ctx: MKSMContext) -> None:
    """server_loop() reads ctx.server_address directly and never goes through
    MKSMContext.connect, so a CLI/URL address would skip the main-menu gate that the
    GUI button and /connect both respect. launch_client holds the address here
    instead, and we spend it once the game is actually ready."""
    if ctx.pending_server_address is None or ctx.server is not None:
        return
    if not ctx.ready_to_connect():
        return

    address, ctx.pending_server_address = ctx.pending_server_address, None
    logger.info(f"Game reached the main menu - connecting to {address}")
    await ctx.connect(address)


async def _handle_game_not_ready(ctx: MKSMContext):
    """If the game is not connected, this will attempt to retry connecting to the game."""
    ctx.game_interface.connect_to_game()
    await asyncio.sleep(3)


def launch_client():
    Utils.init_logging("MKSM Client")

    async def main():
        multiprocessing.freeze_support()
        parser = get_base_parser()
        # get_base_parser() defines neither of these, but handle_url_arg reads both.
        parser.add_argument("--name", default=None, help="Slot Name to connect as.")
        parser.add_argument("url", nargs="?", help="Archipelago connection url")
        args = handle_url_arg(parser.parse_args(), parser)

        # server_address stays None so server_loop doesn't connect behind the main-menu
        # gate; _try_pending_connect spends the address once the game is ready.
        ctx = MKSMContext(None, args.password)
        ctx.pending_server_address = args.connect
        if args.name:
            ctx.auth = args.name

        ctx.server_task = asyncio.create_task(server_loop(ctx), name="Server Loop")
        ctx.tags.add("Client")

        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()

        ctx.set_notify("EVENT_ARRAY")
        ctx.set_notify("CURRENT_EXP")
        ctx.set_notify("EXP_ITEMS_GIVEN")

        ctx.pcsx2_sync_task = asyncio.create_task(pcsx2_sync_task(ctx), name="PCSX2 Sync")
        ctx.is_paused_task = asyncio.create_task(paused_task(ctx), name="Paused Sync")

        await ctx.exit_event.wait()
        ctx.server_address = None

        await ctx.shutdown()

        for task in (ctx.pcsx2_sync_task, ctx.is_paused_task):
            if task:
                await task

    import colorama

    colorama.init()

    asyncio.run(main())
    colorama.deinit()


if __name__ == "__main__":
    launch_client()
