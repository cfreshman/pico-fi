"""
TCP stream read & write
"""
from collections import namedtuple
import gc
import io
import select
import socket

from lib import MergedReadInto, defaulter_dict
from lib.logging import log
from lib.server import connection


class TCP:
    """read & write data to TCP"""

    # TCP/IP MSS is 536 bytes
    MSS = 536
    Writer = namedtuple('Writer', 'data buff buffmv range')

    def __init__(self, poller: select.poll):
        self._poller = poller
        self._reads: dict[int, bytes] = {}
        self._writes: defaulter_dict[int, list[TCP.Writer]] = defaulter_dict()

    def read(self, sock: socket.socket):
        """read client request data from socket"""

        # append data to full request
        sid = id(sock)
        try:
            request = self._reads.get(sid, b'') + sock.read()
        except:
            request = b''
            self.tcp.end(sock)
        self._reads[sid] = request
        return request

    def prepare(self, sock: socket.socket, *data: list[bytes or io.BufferedIOBase]):
        """prepare data for transmission and signal write event to poller"""

        data = MergedReadInto(io.BytesIO(x) if isinstance(x, bytes) else x for x in data)

        # fill buffer of TCP/IP MSS bytes
        buff = bytearray(b'00' * TCP.MSS)
        self._writes.get(id(sock), lambda x: []).append(
            TCP.Writer(data, buff, memoryview(buff), [0, data.readinto(buff)]))
        self._poller.modify(sock, select.POLLOUT)

    def write(self, sock: socket.socket) -> True or None:
        """write next packet, return True if all packets written"""

        writers = self._writes.get(id(sock))
        if not writers: return True # no data to write
        curr: TCP.Writer = writers[0]

        # write next range of bytes from body buffer (limited by TCP/IP MSS)
        try: bytes_written = sock.write(curr.buffmv[curr.range[0]:curr.range[1]])
        except OSError as e:
            writers.remove(curr)
            return log.exception(e, 'cannot write to a closed socket')

        log.debug(bytes_written, 'bytes written to', connection.of(sock))
        if bytes_written == curr.range[1] - curr.range[0]:
            # write next section of body into buffer
            curr.range[0] = 0
            curr.range[1] = curr.data.readinto(curr.buff)
            if curr.range[1] == 0:
                # out of data, remove writer from list & return True
                writers.remove(curr)
                return True
        else:
            # didn't write entire range, increment start for next write
            curr.range[0] += bytes_written

    def clear(self, sock: socket.socket):
        """clear stored data for socket, but leave socket open and untouched"""

        sid = id(sock)
        if sid in self._reads: del self._reads[sid]
        if sid in self._writes: del self._writes[sid]
        gc.collect()

    def end(self, sock: socket.socket):
        """close socket, unregister from poller, and clear data"""

        log.info('end', connection.of(sock))
        sock.close()
        self._poller.unregister(sock)
        self.clear(sock)
