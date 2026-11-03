"""
The PINE API.
This is the client side implementation of the PINE protocol.
It allows for a three-way communication between the emulated game, the emulator and an external
tool, using the external tool as a relay for all communication. It is a socket based IPC that
is _very_ fast.

If you want to draw comparisons you can think of this as an equivalent of the BizHawk LUA API,
although with the logic out of the core and in an external tool. While BizHawk would run a lua
script at each frame in the core of the emulator we opt instead to keep the entire logic out of
the emulator to make it more easily extensible, more portable, require less code and be more
performant.

---
Originally from the Sly Cooper and the Thievius Raccoonus APWorld by hoppel16:
https://github.com/hoppel16/ArchipelagoBranchSly1
Used with credit under the spirit of the open-source AP community.
---
"""
import os
import struct
from enum import IntEnum
from platform import system
from typing import NoReturn
import socket


class Pine:
    """ Exposes PS2 memory within a running instance of the PCSX2 emulator using the Pine IPC Protocol. """

    MAX_IPC_SIZE: int = 650000
    MAX_IPC_RETURN_SIZE: int = 450000
    MAX_BATCH_REPLY_COUNT: int = 50000

    class IPCResult(IntEnum):
        IPC_OK = 0,
        IPC_FAIL = 0xFF

    class IPCCommand(IntEnum):
        READ8 = 0,
        READ16 = 1,
        READ32 = 2,
        READ64 = 3,
        WRITE8 = 4,
        WRITE16 = 5,
        WRITE32 = 6,
        WRITE64 = 7,
        VERSION = 8,
        SAVE_STATE = 9,
        LOAD_STATE = 0xA,
        TITLE = 0xB,
        ID = 0xC,
        UUID = 0xD,
        GAME_VERSION = 0xE,
        STATUS = 0xF,
        UNIMPLEMENTED = 0xFF,

    class DataSize(IntEnum):
        INT8 = 1,
        INT16 = 2,
        INT32 = 4,
        INT64 = 8,

    def __init__(self, slot: int = 28011):
        if not 0 < slot <= 65536:
            raise ValueError("Provided slot number is outside valid range")
        self._slot: int = slot
        self._sock: socket.socket = socket.socket()
        self._sock_state: bool = False

    def _init_socket(self) -> None:
        if system() == "Windows":
            socket_family = socket.AF_INET
            socket_name = ("127.0.0.1", self._slot)
        elif system() == "Linux":
            socket_family = socket.AF_UNIX
            socket_name = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
            socket_name += "/pcsx2.sock"
        elif system() == "Darwin":
            socket_family = socket.AF_UNIX
            socket_name = os.environ.get("TMPDIR", "/tmp")
            socket_name += "/pcsx2.sock"
        else:
            socket_family = socket.AF_UNIX
            socket_name = "/tmp/pcsx2.sock"

        try:
            self._sock = socket.socket(socket_family, socket.SOCK_STREAM)
            self._sock.settimeout(5.0)
            self._sock.connect(socket_name)
        except socket.error:
            self._sock.close()
            self._sock_state = False
            return

        self._sock_state = True

    def connect(self) -> None:
        if not self._sock_state:
            self._init_socket()

    def disconnect(self) -> None:
        if self._sock_state:
            self._sock.close()
            self._sock_state = False

    def is_connected(self) -> bool:
        return self._sock_state

    def read_int8(self, address: int) -> int:
        request = Pine._create_request(Pine.IPCCommand.READ8, address, 9)
        return Pine.from_bytes(self._send_request(request)[-1:])

    def read_int16(self, address) -> int:
        request = Pine._create_request(Pine.IPCCommand.READ16, address, 9)
        return Pine.from_bytes(self._send_request(request)[-2:])

    def read_int32(self, address) -> int:
        request = Pine._create_request(Pine.IPCCommand.READ32, address, 9)
        return Pine.from_bytes(self._send_request(request)[-4:])

    def read_int64(self, address) -> int:
        request = Pine._create_request(Pine.IPCCommand.READ64, address, 9)
        return Pine.from_bytes(self._send_request(request)[-8:])

    _READ_BY_SIZE = {8: IPCCommand.READ64, 4: IPCCommand.READ32, 2: IPCCommand.READ16, 1: IPCCommand.READ8}
    _WRITE_BY_SIZE = {8: IPCCommand.WRITE64, 4: IPCCommand.WRITE32, 2: IPCCommand.WRITE16, 1: IPCCommand.WRITE8}

    @staticmethod
    def _pieces(length: int) -> list[tuple[int, int]]:
        """Splits a span into (offset, size) pieces of 8, then 4, 2 and 1 bytes."""
        pieces = []
        offset = 0
        while offset < length:
            left = length - offset
            size = 8 if left >= 8 else 4 if left >= 4 else 2 if left >= 2 else 1
            pieces.append((offset, size))
            offset += size
        return pieces

    def read_bytes(self, address: int, length: int) -> bytes:
        commands = [(Pine.to_bytes(Pine._READ_BY_SIZE[size], 1) + Pine.to_bytes(address + offset, 4), size)
                    for offset, size in Pine._pieces(length)]
        return self._send_batch(commands)

    def write_int8(self, address: int, value: int) -> None:
        request = Pine._create_request(Pine.IPCCommand.WRITE8, address, 9 + Pine.DataSize.INT8)
        request += value.to_bytes(length=1, byteorder="little")
        self._send_request(request)

    def write_int16(self, address: int, value: int) -> None:
        request = Pine._create_request(Pine.IPCCommand.WRITE16, address, 9 + Pine.DataSize.INT16)
        request += value.to_bytes(length=2, byteorder="little")
        self._send_request(request)

    def write_int32(self, address: int, value: int) -> None:
        request = Pine._create_request(Pine.IPCCommand.WRITE32, address, 9 + Pine.DataSize.INT32)
        request += value.to_bytes(length=4, byteorder="little")
        self._send_request(request)

    def write_int64(self, address: int, value: int) -> None:
        request = Pine._create_request(Pine.IPCCommand.WRITE64, address, 9 + Pine.DataSize.INT64)
        request += value.to_bytes(length=8, byteorder="little")
        self._send_request(request)

    def write_float(self, address: int, value: float) -> None:
        request = Pine._create_request(Pine.IPCCommand.WRITE32, address, 9 + Pine.DataSize.INT32)
        request += struct.pack("<f", value)
        self._send_request(request)

    def write_bytes(self, address: int, data: bytes) -> None:
        commands = [(Pine.to_bytes(Pine._WRITE_BY_SIZE[size], 1) + Pine.to_bytes(address + offset, 4)
                     + bytes(data[offset:offset + size]), 0)
                    for offset, size in Pine._pieces(len(data))]
        self._send_batch(commands)

    def _send_batch(self, commands: list[tuple[bytes, int]]) -> bytes:
        """Sends many commands as few messages as possible: PINE runs every command in a
        message and replies once, with all the read data concatenated in command order.
        `commands` holds (encoded command, bytes it returns). Each message stays under
        PCSX2's request, reply and command-count limits. Returns all read data joined."""
        out = []
        start = 0
        while start < len(commands):
            end = start
            request_size = 4
            reply_size = 5
            while end < len(commands) and end - start < Pine.MAX_BATCH_REPLY_COUNT:
                command, returns = commands[end]
                if (request_size + len(command) > Pine.MAX_IPC_SIZE
                        or reply_size + returns > Pine.MAX_IPC_RETURN_SIZE):
                    break
                request_size += len(command)
                reply_size += returns
                end += 1

            request = Pine.to_bytes(request_size, 4) + b"".join(command for command, _ in commands[start:end])
            reply = self._send_request(request)
            if len(reply) != reply_size:
                # _send_request read exactly the length PCSX2 announced, so the socket is
                # still in step; the reply just doesn't match what we asked for
                raise ConnectionError(f"Unexpected batch reply size from PCSX2 ({len(reply)}, expected {reply_size}).")
            out.append(reply[5:])
            start = end
        return b"".join(out)

    def get_game_id(self) -> str:
        request = Pine.to_bytes(5, 4) + Pine.to_bytes(Pine.IPCCommand.ID, 1)
        response = self._send_request(request)
        return response[9:-1].decode("ascii")

    def get_status(self) -> int:
        """Returns 0=Running, 1=Paused, 2=Shutdown"""
        request = Pine.to_bytes(5, 4) + Pine.to_bytes(Pine.IPCCommand.STATUS, 1)
        response = self._send_request(request)
        return Pine.from_bytes(response[5:9])

    def _send_request(self, request: bytes) -> bytes:
        if not self._sock_state:
            self._init_socket()
            if not self._sock_state:
                raise ConnectionError("Could not connect to PCSX2.")

        try:
            self._sock.sendall(request)
        except socket.error:
            self._drop("Lost connection to PCSX2.")

        # A reply is a 4-byte little-endian total length followed by the rest of that
        # many bytes. Read exactly that much and no more: requests and replies are
        # matched by position on a shared socket, so a single byte left unread shifts
        # every later reply onto the wrong request - silently, and permanently.
        header = self._recv_exactly(4)
        total_length = Pine.from_bytes(header)
        if not 5 <= total_length <= Pine.MAX_IPC_SIZE:
            self._drop(f"Invalid response size from PCSX2 ({total_length}).")

        result = header + self._recv_exactly(total_length - 4)

        if result[4] == Pine.IPCResult.IPC_FAIL:
            # the reply was read in full, so the stream is still aligned here
            raise ConnectionError("Failure indicated in PCSX2 response.")

        return result

    def _recv_exactly(self, count: int) -> bytes:
        """Read exactly count bytes off the socket, or drop the connection trying."""
        buffer = b''
        while len(buffer) < count:
            try:
                chunk = self._sock.recv(count - len(buffer))
            except TimeoutError:
                self._drop("Response from PCSX2 timed out.")
            except socket.error:
                self._drop("Lost connection to PCSX2.")
            if not chunk:
                self._drop("PCSX2 closed the connection.")
            buffer += chunk
        return buffer

    def _drop(self, message: str) -> NoReturn:
        """Close the socket and raise. Any failure part-way through a reply leaves the
        stream at an unknown offset, and there is no way to work out how much of the
        reply is still in flight - so reconnecting is the only safe recovery."""
        try:
            self._sock.close()
        finally:
            self._sock_state = False
        raise ConnectionError(message)

    @staticmethod
    def _create_request(command: IPCCommand, address: int, size: int = 0) -> bytes:
        ipc = Pine.to_bytes(size, 4)
        ipc += Pine.to_bytes(command, 1)
        ipc += Pine.to_bytes(address, 4)
        return ipc

    @staticmethod
    def to_bytes(value: int, size: int) -> bytes:
        return value.to_bytes(length=size, byteorder="little")

    @staticmethod
    def from_bytes(arr: bytes) -> int:
        return int.from_bytes(arr, byteorder="little")
