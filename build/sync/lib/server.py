"""
common server interfaces
"""

import select
import socket

from lib.logging import log
from lib import encode

"""
handler
"""
class SocketPollHandler:
    """handle events from a pool of sockets registered to a poller"""
    def __init__(self, poller: select.poll, name: str):
        self.poller: select.poll = poller
        self.name = name

    def handle(self, sock: socket.socket, event: int): log.exception("missing 'handle' implementation for", self)
    def __repr__(self): return f'<handler {self.name}>'


"""
transport
"""
import socket

from lib import defaulter_dict, enumstr


class transport(enumstr):
    def __init__(self, value, sock_type):
        super().__init__(value)
        self.sock_type = sock_type

class Transport:
    UDP = transport(b'UDP', socket.SOCK_DGRAM)
    TCP = transport(b'TCP', socket.SOCK_STREAM)

    @staticmethod
    def of(sock_type: int): return {
        socket.SOCK_DGRAM: Transport.UDP,
        socket.SOCK_STREAM: Transport.TCP
    }[sock_type]


class connection:
    _instances: dict[socket.SocketKind, object] = defaulter_dict()

    def __init__(self, tran: transport, sock: socket.socket=None):
        self.tran = tran
        if not sock: sock = socket.socket(socket.AF_INET, tran.sock_type)
        self.sock = sock
        connection._instances[id(sock)] = self

    def __repr__(self): return f'<connection {self.tran} {id(self.sock)}>'
    def __hash__(self): return id(self.sock)

    @staticmethod
    def of(sock: socket.socket):
        return connection._instances.get(id(sock), lambda x: log.info('missing socket for', id(sock)))


class protocol(enumstr):
    _transports: dict[enumstr, transport] = {}
    def __init__(self, value, transport: transport):
        super().__init__(value)
        if self in self._transports:
            if self._transports[self] != transport:
                raise Exception(f'multiple transports ({self._transports[self], transport}) for protocol {self}')
        else: self._transports[self] = transport

    @property
    def transport(self): return self._transports[self]

class Protocol:
    DNS = protocol(b'DNS', Transport.UDP)
    HTTP = protocol(b'HTTP', Transport.TCP)
    WebSocket = protocol(b'WebSocket', Transport.TCP)


"""
orchestrator
"""
import select
import socket


class Orchestrator(SocketPollHandler):
    """direct socket events through registered handlers"""

    def __init__(self, poller: select.poll):
        super().__init__(poller, 'Orchestrator')
        self.handlers: dict[int or protocol, SocketPollHandler or protocol] = {}
        # TODO allow for handler chain

    def register(self,
        conn: connection or protocol or transport,
        handler: SocketPollHandler or protocol or transport):

        log.info('register', conn, 'to', handler)
        self.handlers[conn] = handler

    def unregister(self,
        conn: connection or protocol or transport,
        handler: SocketPollHandler or protocol or transport):

        log.info('unregister', handler, 'for', conn)
        if self.handlers[conn] == handler: del self.handlers[conn]

    def handle(self, sock: socket.socket, event):
        conn = connection.of(sock)

        # resolve handler for connection
        handler = self.handlers.get(conn)
        if isinstance(handler, transport): handler = self.handlers.get(handler)
        if isinstance(handler, protocol): handler = self.handlers.get(handler)
        if handler and not isinstance(handler, SocketPollHandler):
            raise Exception(f'failed handler resolution (sock -> transport -> protocol -> handler), ended with protocol {handler}')

        if handler:
            # log.info('route', conn, 'to', handler)
            handler.handle(sock, event) # TODO pass to next handler if True
        else: log.info('no handler for', conn, 'in', self.handlers)


"""
protocol handler
"""
import socket


class ProtocolHandler(SocketPollHandler):
    """handle socket events according to protocol"""

    def __init__(self, orch: Orchestrator, proto: protocol, name: str=None):
        super().__init__(orch.poller, name or proto)
        self.orch = orch
        self.proto = proto
        self.orch.register(proto, self)

    def stop(self):
        self.orch.unregister(self.proto, self)


"""
server
"""
import select
import socket


class Server(ProtocolHandler):
    def __init__(self, orch: Orchestrator, port: int, proto: protocol, name: str=None):
        orch.register(proto.transport, proto) # register proto as default for transport
        super().__init__(orch, proto, name)

        # create server socket
        self.conn = connection(proto.transport)
        self.sock = self.conn.sock
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # allow overlapped reads

        self.orch.register(self.conn, self) # register as handler for connection
        self.poller.register(self.sock, select.POLLIN) # register socket for event polling

        # bind address to socket
        addr = socket.getaddrinfo('0.0.0.0', port)[0][-1]
        self.sock.bind(addr)

        log.info(self.name, f'listening on :{port}', proto.transport, proto)

    def stop(self):
        self.poller.unregister(self.sock)
        self.conn.sock.close()
        super().stop()



"""
other: IP sink
"""
class IpSink:
    def __init__(self, ip: bytes or str): self.ip = encode(ip) if ip else None
    def get(self): return self.ip
    def set(self, ip): self.ip = encode(ip) if ip else None
