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
import sys

# CommonClient import first to trigger ModuleUpdater
from CommonClient import CommonContext, server_loop, get_base_parser, handle_url_arg, logger, ClientCommandProcessor

import Utils
from worlds.mksm.consts import GameState, DEFAULT_EVENT_ARRAY

from .MKSMInterface import MKSMInterface
from .callbacks import game_watcher as run_callbacks

EMULATOR_RECONNECT_DELAY = 5  # seconds between PCSX2 connection attempts


class MKSMCommandProcessor(ClientCommandProcessor):
    ctx: MKSMContext

    def _cmd_xp(self, value: str = "1000") -> bool:
        """Add given xp
        Usage: /xp   or   /xp 5000"""
        ctx: MKSMContext = self.ctx
        ctx.game_interface.add_xp(int(value))
        self.output(f"Added {value} XP")
        return True

    def _cmd_health(self):
        """
        prints current health status
        """
        ctx: MKSMContext = self.ctx
        print(ctx.game_interface.health_status())
        return True

    async def _cmd_removeevent(self) -> bool:
        """removes last event in the event array, use in cases of softlocks if exited at wrong times,
        use only on main menu"""
        ctx: MKSMContext = self.ctx
        if ctx.game_state != GameState.MAIN_MENU:
            print("only use /removeevents on main menu")
            return True

        current_events = ctx.stored_data.get("EVENT_ARRAY")

        if current_events == DEFAULT_EVENT_ARRAY:
            print("no event to remove")
            return True

        await ctx.send_msgs([{"cmd": "Set",
                              "key": "EVENT_ARRAY",
                              "operations": [
                                  {
                                      "operation": "replace",
                                      "value": current_events[:-8]
                                  }
                              ],
                              }])

        return True


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

    def __init__(self, server_address: str | None, password: str | None) -> None:
        super().__init__(server_address, password)
        self.is_paused = False
        self.game_interface = MKSMInterface(logger)
        self.synced_koins = False  # set True after the one-time on-connect memory sync
        self.game_state = GameState.BOOTING
        self.prev_state = GameState.BOOTING
        self.slot_data = None

    async def server_auth(self, password_requested: bool = False) -> None:
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_package(self, cmd: str, args: dict) -> None:
        if cmd == "Connected":
            self.slot_data = args.get("slot_data", {})


async def game_watcher(ctx: MKSMContext) -> None:
    while not ctx.exit_event.is_set():
        try:
            await asyncio.wait_for(ctx.watcher_event.wait(), 0.01)
        except asyncio.TimeoutError:
            pass
        ctx.watcher_event.clear()

        if not ctx.game_interface.get_connection_state():
            ctx.synced_koins = False  # re-sync on the next successful (re)connect
            ctx.game_interface.connect_to_game()
            await asyncio.sleep(EMULATOR_RECONNECT_DELAY)
            continue

        if ctx.server is None or ctx.slot is None:
            continue  # not connected to the AP server yet

        try:
            await run_callbacks(ctx)
        except Exception:
            # Without this, any exception raised anywhere in the callback chain
            # (a PINE read/write hiccup, a bad address, anything) kills this
            # task silently and for good - the watcher just stops ticking with
            # no visible error until the client process exits.
            logger.exception("Error while running MKSM game watcher callbacks")


async def main(args) -> None:
    ctx = MKSMContext(args.connect, args.password)
    ctx.auth = args.name

    ctx.server_task = asyncio.create_task(server_loop(ctx), name="ServerLoop")
    ctx.run_cli()

    ctx.set_notify("EVENT_ARRAY")
    ctx.set_notify("CURRENT_XP")
    watcher_task = asyncio.create_task(game_watcher(ctx), name="MKSMGameWatcher")

    await ctx.exit_event.wait()

    ctx.game_interface.disconnect_from_game()
    await watcher_task
    await ctx.shutdown()


def launch(*launch_args: str) -> None:
    import colorama

    parser = get_base_parser(description="Mortal Kombat: Shaolin Monks Archipelago Client")
    parser.add_argument("--name", default=None, help="Slot Name to connect as.")
    parser.add_argument("url", nargs="?", help="Archipelago connection url")
    args = parser.parse_args(launch_args)
    args = handle_url_arg(args, parser=parser)

    colorama.just_fix_windows_console()
    asyncio.run(main(args))
    colorama.deinit()


if __name__ == "__main__":
    Utils.init_logging("MKSMClient", exception_logger="Client")
    launch(*sys.argv[1:])
