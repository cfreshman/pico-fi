import io
import socket
import select

from lib.stream.tcp import TCP
from lib import decode_bytes, defaulter_dict, encode, encode_bytes, format_bytes, enum
from lib.logging import log


class enum: pass

class WS(TCP):
    """
    read & write WebSocket frames
    write same as TCP, but parse & prepare additional info to signal frames
    over otherwise continuous connection
    """

    class FIN:
        NON_FINAL = 0x0
        FINAL = 0x1
        @staticmethod
        def name(final):
            return (
                [x for x in dir(WS.FIN) if getattr(WS.FIN, x) == final]
                or [None])[0]

    class Opcode:
        CONTINUE = 0x0
        TEXT = 0x1
        BINARY = 0x2
        CLOSE = 0x8
        PING = 0x9
        PONG = 0xA
        @staticmethod
        def name(opcode):
            return (
                [x for x in dir(WS.Opcode) if getattr(WS.Opcode, x) == opcode]
                or [None])[0]

    class Mask:
        OFF = 0x0
        ON = 0x1

    LOW_PAYLOAD_LEN = 125
    MID_PAYLOAD_LEN = 2 << 15 - 1
    MAX_PAYLOAD_LEN = 2 << 62 - 1 # I don't think we'll need to worry about that

    class ReadFrame:
        def __init__(self, sock: socket.socket):
            # expect start of WebSocket frame
            self.sock = sock
            self.data = b''
            self.done = False
            self.final = False
            self.opcode = None

        def read(self):
            if self.data: # continue prev read
                self.data += self.sock.read(self.len - len(self.data))
            else:
                try: bAB = self.sock.recv(2)
                except: bAB = None
                if not bAB: return # no data to read
                bA = bAB[0]
                self.final = (bA & 0b1000_0000) > 7
                self.opcode = bA & 0b0000_1111
                log.debug(
                    'WebSocket frame read: header', format_bytes(bAB),
                    WS.FIN.name(self.final), WS.Opcode.name(self.opcode))
                bB = bAB[1]
                self.mask = bB & 0b1000_0000
                self.len = bB & 0b0111_1111
                ext = 0
                if self.len == 126: ext = 2
                if self.len == 127: ext = 8
                if ext: self.len = decode_bytes(self.sock.recv(ext))

                self.mask = self.sock.recv(4) if self.mask else 0
                self.data = bytearray(self.sock.read(self.len))
            if len(self.data) == self.len:
                # read completed, unmask data
                if self.mask:
                    for i in range(len(self.data)):
                        j = i % 4
                        self.data[i] = self.data[i] ^ self.mask[j]
                log.debug(
                    'WebSocket completed frame read:',
                    WS.Opcode.name(self.opcode), self.data)
                self.done = True
            else:
                log.debug('WebSocket frame read:', len(self.data), '/', self.len, 'bytes')

    class ReadMessage:
        def __init__(self, sock):
            self.sock = sock
            self.frame: WS.ReadFrame = WS.ReadFrame(sock)
            self.data = b''
            self.done = False
            self.opcode = None

        def read(self):
            self.frame.read()
            self.opcode = self.opcode or self.frame.opcode
            if self.frame.done:
                self.data += self.frame.data
                if self.frame.final:
                    self.done = True
                    del self.frame
                else:
                    self.frame = WS.ReadFrame(self.sock)
            elif not self.frame.data: # initial frame empty, end read
                self.done = True


    def __init__(self, poller):
        super().__init__(poller)
        self.messages: dict[int, WS.ReadMessage] = defaulter_dict()
    
    def end(self, sock: socket.socket):
        del self.messages[id(sock)]
        super().end(sock)

    def read(self, sock: socket.socket) -> tuple(bytes, str or bytes):
        message = self.messages.get(id(sock), lambda x: WS.ReadMessage(sock))
        try: message.read()
        except Exception as e:
            log.exception(e)
            message.opcode = WS.Opcode.CLOSE
            message.done = True
        if message.done:
            if message.opcode == WS.Opcode.CLOSE: self.end(sock)
            else:
                del self.messages[id(sock)]
                self._poller.modify(sock, select.POLLOUT)
            return [message.opcode, message.data]

    def send(self,
        sock: socket.socket, 
        opcode: int,
        message: str or bytes=b''):

        # construct frame - send in single message
        header = bytearray()
        data = encode(str(message))

        FIN_RSV_opcode = WS.FIN.FINAL << 7 | opcode
        header += bytes((FIN_RSV_opcode,))

        payload_len = len(data)
        ext_payload_len = b''
        if payload_len > WS.MID_PAYLOAD_LEN:
            # use next 8 bytes for length
            ext_payload_len = encode_bytes(payload_len, 8)
            payload_len = 127
        elif payload_len > WS.LOW_PAYLOAD_LEN:
            # use next 2 bytes for length
            ext_payload_len = encode_bytes(payload_len, 2)
            payload_len = 126
        header += bytes((WS.Mask.OFF << 7 | payload_len,)) + ext_payload_len

        log.debug(
            'WebSocket frame send:', format_bytes(header[:2]),
            WS.FIN.name(header[0] > 7), WS.Opcode.name(header[0] & 1),
            'length:', len(data))
        
        super().prepare(sock, io.BytesIO(header + data))

    def prepare(self, sock: socket.socket, *data: list[bytes or io.BufferedIOBase]):
        """prepare WebSocket frames"""

        message = b''
        for x in data:
            if isinstance(x, io.BytesIO): message += x.read()
            else: message += x

        # prepend frame info for data
        self.send(sock, WS.Opcode.TEXT, message)

    def clear(self, sock: socket.socket):
        if id(sock) in self.messages: del self.messages[id(sock)]
        super().clear(sock)
