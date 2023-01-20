F='.'
import gc,select as D
from lib.logging import log
from lib.server import Protocol as A,Server as B
class E(B):
	def __init__(B,orchestrator,ip):super().__init__(orchestrator,53,A.DNS);B.ip=ip
	def handle(A,sock,event):
		I=True;B=sock
		if B is not A.sock:return I
		if event==D.POLLHUP:return I
		try:F,G=B.recvfrom(1024);C=E.Query(F);log.info('DNS @ {:s} -> {:s}'.format(C.domain,A.ip));B.sendto(C.answer(A.ip.decode()),G);del C;gc.collect()
		except Exception as H:log.exception(H,'DNS server exception')
	class Query:
		def __init__(D,data):
			A=data;D.data=A;D.domain='';B=12;C=A[B]
			while C!=0:E=B+1;D.domain+=A[E:E+C].decode('utf-8')+F;B+=C+1;C=A[B]
		def answer(B,ip):A=B.data[:2];A+=b'\x81\x80';A+=B.data[4:6]+B.data[4:6];A+=b'\x00\x00\x00\x00';A+=B.data[12:];A+=b'\xc0\x0c';A+=b'\x00\x01\x00\x01';A+=b'\x00\x00\x00<';A+=b'\x00\x04';A+=bytes(map(int,ip.split(F)));return A