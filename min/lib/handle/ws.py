import binascii as A,hashlib as C,select as B
from lib.stream.ws import WS
from lib import chain
from lib.logging import log
from lib.server import Orchestrator,Protocol as D,ProtocolHandler as E,connection as F
class G(E):
	class Message:
		def __init__(A,ws,sock,data):A._ws=ws;A._sock=sock;A.data=data
		def reply(A,data):A._ws.send(A._sock,data)
	def __init__(A,orch,handler=None):super().__init__(orch,D.WebSocket);A.io=WS(orch.poller);A.handler=handler;A.conns=set()
	KeyHeader=b'Sec-WebSocket-Key';_AcceptMagicNumber=b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
	@staticmethod
	def get_http_upgrade_header(key):B=chain(key,lambda x:x+G._AcceptMagicNumber,lambda x:C.sha1(x).digest(),lambda x:A.b2a_base64(x));return b'HTTP/1.1 101 Switching Protocols\r\n'+b'Upgrade: websocket\r\n'+b'Connection: Upgrade\r\n'+b'Sec-WebSocket-Accept: '+B+b'\r\n'
	def handle(A,sock,event):
		D=event;C=sock;E=F.of(C);log.debug('SOCKET EVENT',E,D&B.POLLOUT,D&B.POLLIN)
		if E not in A.conns:A.conns.add(E);A.io.send(C,WS.Opcode.PING)
		elif D&B.POLLOUT:A.write(C)
		else:A.read(C)
	def read(A,sock):
		B=A.io.read(sock)
		if B:
			log.info('WebSocket message:',B.decode())
			if A.handler:A.handler(B)
			else:A.io.send(sock,WS.Opcode.TEXT,B)
	def write(A,sock):
		if A.io.write(sock):A.poller.modify(sock,B.POLLIN)