"""
HTTP handler
"""
import io
import json
import select
import socket
from collections import namedtuple

import micropython

from z_handle_ws import WebSocket
from z_io_tcp import TCP
from z_lib import encode, unquote
from z_logging import cmt, log
from z_server import Orchestrator, Protocol, Server, connection, IpSink


class HTTP(Server):
    """
    serve single index.html page, get/set persistent state API, and upgrade connections to websocket
    """

    class Status:
        OK = b'HTTP/1.1 200 OK'
        REDIRECT = b'HTTP/1.1 307 Temporary Redirect'
        BAD_REQUEST = b'HTTP/1.1 400 Bad Request'
        NOT_FOUND = b'HTTP/1.1 404 Not Found'
        SERVER_ERROR = b'HTTP/1.1 500 Internal Server Error'

        @staticmethod
        def of(code: int): return {
            200: HTTP.Status.OK,
            307: HTTP.Status.REDIRECT,
            400: HTTP.Status.BAD_REQUEST,
            404: HTTP.Status.NOT_FOUND,
            500: HTTP.Status.SERVER_ERROR,
        }.get(code, HTTP.Status.SERVER_ERROR)

    NL = b'\r\n'
    END = NL + NL

    Request = namedtuple('Request', ['host', 'method', 'path', 'raw_query', 'query', 'headers', 'body'])
    class Response:
        def __init__(self, http, sock):
            self.http: HTTP = http
            self.sock = sock

        def send(self, header: bytes or int or list[bytes], body: bytes or str or io.BytesIO = b''):
            if isinstance(header, int): header = HTTP.Status.of(header)
            if isinstance(header, list): header = HTTP.NL.join(header)
            if header[-len(HTTP.NL):] != HTTP.NL: header += HTTP.NL
            self.http.prepare(self.sock, header, encode(body))

        def ok(self, body: bytes or str = b''): self.send(HTTP.Status.OK, body)
        def error(self, message: bytes or str): self.send(HTTP.Status.SERVER_ERROR, message)
        def redirect(self, url: bytes or str): self.send([HTTP.Status.REDIRECT, b'Location: ' + encode(url)])
        def text(self, content: bytes or str): self.send([HTTP.Status.OK, b'Content-Type: text/plain'], content)
        def json(self, data): self.send([HTTP.Status.OK, b'Content-Type: application/json'], json.dumps(data))
        def file(self, path: bytes or str):
            log.info('reply with file', path)
            try: self.send(HTTP.Status.OK, open(path, 'rb'))
            except Exception as e:
                log.exception(e, 'error reading file', path)
                self.send(HTTP.Status.NOT_FOUND)


    def __init__(self, orch: Orchestrator, ip_sink: IpSink, routes: dict[bytes, bytes or function]):
        super().__init__(orch, 80, Protocol.HTTP)
        self.tcp = TCP(orch.poller)
        self.ip_sink = ip_sink
        self.ip = ip_sink.get()
        self.routes = routes
        self.ws_upgrades = set()

        # queue up to 5 connection requestss before refusing
        self.sock.listen(5)
        self.sock.setblocking(False)

    @micropython.native
    def handle(self, sock, event):
        if sock is self.sock: self.accept(sock) # new connection
        elif event & select.POLLIN: self.read(sock) # connection has data to read
        elif event & select.POLLOUT: self.write(sock) # connection has space to send data
        else: return True # pass to next handler

    def accept(self, server_sock):
        """accept a new client socket and register it for polling"""

        try: client_sock, addr = server_sock.accept()
        except Exception as e: return log.exception(e, 'failed to accept connection request on', server_sock)

        # allow requests
        client_sock.setblocking(False)
        client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.orch.register(connection(self.proto.transport, client_sock), self) # register HTTP handler in orchestrator
        self.poller.register(client_sock, select.POLLIN) # register as POLLIN to trigger read

    def parse_request(self, raw_req: bytes):
        """parse a raw HTTP request"""

        log.info(raw_req)
        log.flush()
        header_bytes, body_bytes = raw_req.split(HTTP.END)
        header_lines = header_bytes.split(HTTP.NL)
        req_type, full_path, *_ = header_lines[0].split(b' ')
        path, *rest = full_path.split(b'?', 1)
        raw_query = rest[0] if len(rest) else None
        query = {
            unquote(key): unquote(val)
            for key, val in [param.split(b'=') for param in raw_query.split(b'&')]
        } if raw_query else {}
        headers = {
            key: val
            for key, val in [line.split(b': ', 1) for line in header_lines[1:]]
        }
        host = headers[b'Host']

        log.info('HTTP REQUEST:', (host + path).decode())
        log.debug(raw_req.decode().strip())
        return HTTP.Request(host, req_type, path, raw_query, query, headers, body_bytes)

    def parse_route(self, req: Request):
        log.info(req.path.split(b'/'))
        prefix = b'/'+(req.path.split(b'/')+[b''])[1]
        return (req.host == self.ip or not self.ip_sink.get()) and self.routes.get(prefix, None)
    def handle_request(self, sock, req: Request):
        """respond to an HTTP request"""

        if WebSocket.KeyHeader in req.headers:
            cmt('upgrade HTTP to WebSocket')
            self.ws_upgrades.add(connection.of(sock))
            self.prepare(sock, WebSocket.get_http_upgrade_header(req.headers[WebSocket.KeyHeader]))
            return

        res = HTTP.Response(self, sock)
        route = self.parse_route(req)
        ip_redirect = self.ip_sink.get()
        if route:
            if isinstance(route, bytes): res.file(route)
            elif callable(route): route(req, res)
            else: res.send(HTTP.Status.NOT_FOUND)

        # redirect non-matches to landing switch
        elif ip_redirect: res.redirect(b'http://{:s}/portal{:s}'.format(ip_redirect, b'?'+req.raw_query if req.raw_query else b''))

        # attempt to send file
        else: res.file(req.path)

    def read(self, sock):
        """read client request data from socket"""

        request = self.tcp.read(sock)
        if not request: self.tcp.end(sock) # empty stream, close immediately
        elif request[-4:] == HTTP.END:
            # end of HTTP request, parse & handle
            req = self.parse_request(request)
            self.handle_request(sock, req)

    def prepare(self, sock, headers: bytes, body: bytes or io.BytesIO=None):
        log.info('HTTP RESPONSE',
            f': body length {len(body) if isinstance(body, bytes) else "unknown"}' if body else '',
            '\n', encode(headers).decode().strip(), sep='')
        self.tcp.prepare(sock, headers, b'\n', body)

    def write(self, sock):
        if self.tcp.write(sock):
            conn = connection.of(sock)
            if conn in self.ws_upgrades:
                # we upgraded this to a WebSocket, switch handler but keep open
                self.orch.register(conn, Protocol.WebSocket)
                self.poller.register(sock, select.POLLIN) # switch back to read
                cmt('upgraded HTTP to WebSocket')
                self.tcp.clear(sock)
                self.ws_upgrades.remove(conn)
            else:
                self.tcp.end(sock) # HTTP response complete, end connection
