"""
WebSocket handler
"""
import binascii
import hashlib
import select

from lib.stream.ws import WS
from lib import chain
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
        def __init__(self, ws, sock, data):
            self._ws = ws
            self._sock = sock
            self.data = data

        def reply(self, data: bytes or str or dict):
            self._ws.send(self._sock, data)


    def __init__(self, orch: Orchestrator, handler=None):
        super().__init__(orch, Protocol.WebSocket)
        self.io = WS(orch.poller)
        self.handler = handler
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
        if conn not in self.conns:
            self.conns.add(conn)
            # send PING frame to start
            self.io.send(sock, WS.Opcode.PING)
        elif event & select.POLLOUT: self.write(sock) # we have data to write
        else: self.read(sock)

    def read(self, sock):
        """read WebSocket frame from client and pass to handler"""
        message = self.io.read(sock)
        if message:
            log.info('WebSocket message:', message.decode())
            if self.handler: self.handler(message)
            else: self.io.send(sock, WS.Opcode.TEXT, message)

    def write(self, sock):
        # if write complete, switch back to read
        if self.io.write(sock): self.poller.modify(sock, select.POLLIN)
