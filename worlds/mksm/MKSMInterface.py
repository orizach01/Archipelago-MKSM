import struct
from logging import Logger
from typing import Optional, Dict

from .consts import ADDRESSES, GameState

from .pcsx2_interface.pine import Pine


class GameInterface:
    """
    Base class for connecting with a pcsx2 game
    taken from https://github.com/hoppel16/ArchipelagoBranchSly1/blob/main/worlds/sly1/Sly1Interface.py
    """

    pcsx2_interface: Pine = Pine()
    logger: Logger
    game_id_error: Optional[str] = None
    current_game: Optional[str] = None
    addresses: Dict = {}

    def __init__(self, logger) -> None:
        self.logger = logger

    def _read8(self, address: int):
        return self.pcsx2_interface.read_int8(address)

    def _read16(self, address: int):
        return self.pcsx2_interface.read_int16(address)

    def _read32(self, address: int):
        return self.pcsx2_interface.read_int32(address)

    def _read_bytes(self, address: int, n: int):
        return self.pcsx2_interface.read_bytes(address, n)

    def _read_float(self, address: int):
        return struct.unpack("f", self.pcsx2_interface.read_bytes(address, 4))[0]

    def _write8(self, address: int, value: int):
        self.pcsx2_interface.write_int8(address, value)

    def _write16(self, address: int, value: int):
        self.pcsx2_interface.write_int16(address, value)

    def _write32(self, address: int, value: int):
        self.pcsx2_interface.write_int32(address, value)

    def _write_bytes(self, address: int, value: bytes):
        self.pcsx2_interface.write_bytes(address, value)

    def _write_float(self, address: int, value: float):
        self.pcsx2_interface.write_float(address, value)

    def _write_u32(self, address: int, value: int):
        value = value & 0xFFFFFFFF  # truncate to 32-bit unsigned
        value_bytes = value.to_bytes(4, byteorder='little', signed=False)
        self._write_bytes(address, value_bytes)

    def _write_u64(self, address: int, value: int):
        if value < 0 or value > 0xFFFFFFFFFFFFFFFF:
            raise ValueError(f"Value {value} out of range for unsigned 64-bit write.")
        value_bytes = value.to_bytes(8, byteorder='little', signed=False)
        self._write_bytes(address, value_bytes)

    def connect_to_game(self):
        """
        Initializes the connection to PCSX2 and verifies it is connected to the
        right game
        """
        if not self.pcsx2_interface.is_connected():
            self.pcsx2_interface.connect()
            if not self.pcsx2_interface.is_connected():
                return
            self.logger.info("Connected to PCSX2 Emulator")
        try:
            game_id = self.pcsx2_interface.get_game_id()
            # The first read of the address will be null if the client is faster than the emulator
            self.current_game = None
            if game_id in ADDRESSES.keys():
                self.current_game = game_id
                self.addresses = ADDRESSES[game_id]
            if self.current_game is None and self.game_id_error != game_id and game_id != b'\x00\x00\x00\x00\x00\x00':
                self.logger.warning(
                    f"Connected to the wrong game ({game_id})")
                self.game_id_error = game_id
        except RuntimeError:
            pass
        except ConnectionError:
            pass

    def disconnect_from_game(self):
        self.pcsx2_interface.disconnect()
        self.current_game = None
        self.logger.info("Disconnected from PCSX2 Emulator")

    def get_connection_state(self) -> bool:
        try:
            connected = self.pcsx2_interface.is_connected()
            return connected and self.current_game is not None
        except RuntimeError:
            return False


class MKSMInterface(GameInterface):
    def get_checked_red_koins(self) -> set[str]:
        """Reads game memory once and returns every red koin location name
        currently flagged as collected."""
        game_state = self.get_game_state()
        if game_state != GameState.GAMEPLAY:
            return set()

        koin_addrs = self.addresses.get("RED_KOINS", {})
        if not koin_addrs:
            return set()

        all_addrs = {addr for bits in koin_addrs.values() for addr in bits}
        start, end = min(all_addrs), max(all_addrs)
        block = self._read_bytes(start, end - start + 1)

        checked = set()
        for location_name, addr_bits in koin_addrs.items():
            if all(
                    (block[addr - start] & self._mask(bits)) == self._mask(bits)
                    for addr, bits in addr_bits.items()
            ):
                checked.add(location_name)
        return checked

    @staticmethod
    def _mask(bits: list[int]) -> int:
        return sum(1 << b for b in bits)

    def clear_uncollected_red_koins(self, checked_names: set[str]) -> None:
        """Zero out every red koin's bits in game memory except for the ones in
        `checked_names`. Used once on connect so a stale save state (leftover
        bits from before this seed, debug saves, etc.) can't desync from what
        the AP server currently considers checked, or get reported as a check
        that never actually happened this run."""
        koin_addrs = self.addresses.get("RED_KOINS", {})
        if not koin_addrs:
            return

        all_addrs = {addr for bits in koin_addrs.values() for addr in bits}
        start, end = min(all_addrs), max(all_addrs)
        block = bytearray(self._read_bytes(start, end - start + 1))

        for location_name, addr_bits in koin_addrs.items():
            if location_name in checked_names:
                continue  # AP already has this checked; leave its bits alone
            for addr, bits in addr_bits.items():
                block[addr - start] &= ~self._mask(bits) & 0xFF

        self._write_bytes(start, bytes(block))

    def get_game_state(self) -> GameState:
        state_addr = self.addresses.get("GAME_STATE")
        return GameState(self._read8(state_addr))

    def clear_event_log(self, event_data: bytes) -> bool:
        print(event_data)

        # total_bytes = total_events * 8
        # self._write_bytes(self.addresses.get("EVENT_LOG_ARRAY"), bytes([0] * total_bytes))
        self._write_bytes(self.addresses.get("EVENT_LOG_ARRAY"), event_data)
        self._write32(self.addresses.get("TOTAL_EVENTS"), len(event_data) // 8)

        return False

    def get_event_block(self) -> bytes:
        total_events = self._read32(self.addresses.get("TOTAL_EVENTS"))
        total_bytes = total_events * 8
        return self._read_bytes(self.addresses.get("EVENT_LOG_ARRAY"), total_bytes)
