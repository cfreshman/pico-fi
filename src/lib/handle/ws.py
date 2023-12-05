"""
WebSocket handler
"""
import binascii
import hashlib
import select
import socket

from lib.stream.ws import WS
from lib import chain, decode
from lib.logging import log
from lib.server import Orchestrator, Protocol, ProtocolHandler, connection


class WebSocket(ProtocolHandler):
    """
    WebSocket: continuous two-way communication with client over TCP
    """
    """
    Unlike HTTP and DNS, this handler isn't responsible for accepting new connections
    HTTP connections are upgraded & handed over instead

    Multiple writes & reads can be queued per socket
    Register a handler to receive reads & send writes
    """

    class Message:
        def __init__(self, ws, sock, opcode: WS.Opcode, data: bytes):
            self._ws = ws
            self.s_id = id(sock)
            self.opcode = opcode
            self.data = data
            if opcode == WS.Opcode.TEXT:
                [self.type, *_content] = data.split(b' ', 1)
                self.content = decode(b' '.join(_content))
            else: self.type = None

        def reply(self, *data: bytes or str or dict, opcode=WS.Opcode.TEXT):
            self._ws.emit(*data, opcode=opcode, socket_id=self.s_id)

        def share(self, *data, opcode=WS.Opcode.TEXT):
            other_ids = [
                s_id
                for s_id in [x.sock for x in self._ws.conns]
                if s_id != self.s_id]
            for s_id in other_ids:
                self._ws.emit(*data, opcode=opcode, socket_id=s_id)

        def all(self, *data, opcode=WS.Opcode.TEXT):
            self._ws.emit(*data, opcode=opcode)

        def __repr__(self) -> str:
            return f'{self.s_id} {WS.Opcode.name(self.opcode)} {self.data}'


    def __init__(self, orch: Orchestrator, events={}):
        super().__init__(orch, Protocol.WebSocket)
        self.io = WS(orch.poller)
        self.events = events
        self.conns: set[connection] = set()

    KeyHeader = b'Sec-WebSocket-Key'
    _AcceptMagicNumber = b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
    @staticmethod
    def get_http_upgrade_header(key):
        accept = chain(key,
            lambda x: x + WebSocket._AcceptMagicNumber,
            lambda x: hashlib.sha1(x).digest(),
            lambda x: binascii.b2a_base64(x))
        return (
            b'HTTP/1.1 101 Switching Protocols\r\n' +
            b'Upgrade: websocket\r\n' +
            b'Connection: Upgrade\r\n' +
            b'Sec-WebSocket-Accept: ' + accept + b'\r\n'
        )

    def handle(self, sock, event):
        conn = connection.of(sock)
        log.debug('SOCKET EVENT', conn, event & select.POLLOUT, event & select.POLLIN)
        if conn not in self.conns: self.conns.add(conn)
        elif event & select.POLLOUT: self.write(sock) # we have data to write
        else: self.read(sock)

    def emit(self, *data: str or bytes, opcode=WS.Opcode.TEXT, socket_id=0):
        if opcode == WS.Opcode.TEXT: message = ' '.join(str(x) for x in data)
        else: message = b''.join(x for x in data)
        sent = False
        for sock in [x.sock for x in self.conns]:
            if socket_id and id(sock) != socket_id: continue
            try:
                log.debug('WebSocket send', id(sock), WS.Opcode.name(opcode))
                self.io.send(sock, opcode, message)
                sent = True
                # write & read immediately
                log.debug('WebSocket flush and read')
                while not self.io.write(sock): pass
                self.read(sock)
            except Exception as e:
                log.exception(e)
                self.conns.remove(connection.of(sock))
        return sent

    def read(self, sock: socket.socket):
        """read WebSocket frame from client and pass to handler"""
        result = self.io.read(sock)
        if result:
            [opcode, data] = result
            if opcode == WS.Opcode.CLOSE: self.conns.remove(connection.of(sock))
            if opcode == WS.Opcode.PING: self.io.send(sock, WS.Opcode.PONG)
            if data:
                msg = WebSocket.Message(self, sock, opcode, data)
                handler = self.events.get(msg.type, None)
                log.debug('WebSocket read', msg, handler)
                if not handler:
                    if msg.type == b'connect':
                        self.emit('connected', msg.s_id, socket_id=msg.s_id)
                    elif opcode in self.events: handler = self.events[opcode]
                handler and handler(msg)

    def write(self, sock):
        # if write complete, switch back to read
        if self.io.write(sock): self.poller.modify(sock, select.POLLIN)
