V=b'?'
U=True
T=bytes
S=Exception
R=staticmethod
N=False
M=len
F=None
I=isinstance
D=b''
import io,json,select as C,socket as J
from collections import namedtuple as O
import re,micropython as P
from lib.handle.ws import WebSocket as G
from lib.stream.tcp import TCP
from lib import encode as E,unquote as K
from lib.logging import cmt,log as B
from lib.server import Orchestrator,Protocol as L,Server as Q,connection as H,IpSink
class A(Q):
	NL=b'\r\n';END=NL+NL
	class ContentType:
		class Value:TEXT=b'text/plain';TXT=TEXT;JSON=b'application/json';HTML=b'text/html';HTM=HTML;FORM=b'application/x-www-form-urlencoded';PNG=b'image/png';JPG=b'image/jpeg';JPEG=JPG;GIF=b'image/gif';SVG=b'image/svg+xml';MP3=b'audio/mpeg';MP4=b'video/mp4';PDF=b'application/pdf'
		_MIME_REGEX='^[A-Za-z0-9_-]/[A-Za-z0-9_-]$';_FILE_EXT_REGEX='^([^/]*/)?[^/.]+\\.([A-Za-z0-9_-.]+)$'
		@R
		def of(ext_or_type):
			B=ext_or_type
			if not re.match(A.ContentType._MIME_REGEX,B):C=re.match(A.ContentType._FILE_EXT_REGEX,B);B=(getattr(A.ContentType.Value,C.group(2).upper())if hasattr(A.ContentType.Value,C.group(2).upper())else D)if C else F
			return b'Content-Type: '+E(B)if B else D
	Request=O('Request','host method path raw_query query headers body')
	class Response:
		class Status:
			OK=b'HTTP/1.1 200 OK';REDIRECT=b'HTTP/1.1 307 Temporary Redirect';BAD_REQUEST=b'HTTP/1.1 400 Bad Request';NOT_FOUND=b'HTTP/1.1 404 Not Found';SERVER_ERROR=b'HTTP/1.1 500 Internal Server Error'
			@R
			def of(code):return {200:A.Response.Status.OK,307:A.Response.Status.REDIRECT,400:A.Response.Status.BAD_REQUEST,404:A.Response.Status.NOT_FOUND,500:A.Response.Status.SERVER_ERROR}.get(code,A.Response.Status.SERVER_ERROR)
		def __init__(A,http,sock):A.http=http;A.sock=sock;A.sent=N
		def send(C,header,body=D):
			B=header
			if I(B,int):B=A.Response.Status.of(B)
			if I(B,list):B=A.NL.join(B)
			if B[-M(A.NL):]!=A.NL:B+=A.NL
			C.http.prepare(C.sock,B,E(body));C.sent=U
		def ok(B,body=D):B.send(A.Response.Status.OK,body)
		def error(B,message):B.send(A.Response.Status.SERVER_ERROR,message)
		def redirect(B,url):B.send([A.Response.Status.REDIRECT,b'Location: '+E(url)])
		def content(B,type,content):B.send([A.Response.Status.OK,A.ContentType.of(type)],content)
		def text(A,content):A.content('txt',content)
		def json(A,data):A.content('json',json.dumps(data))
		def html(A,content):A.content('test/blah.html',content)
		def file(D,path):
			C=path;B.info('open file for response',C)
			try:D.content(A.Response.Status.OK,open(C,'rb'))
			except S as E:B.exception(E,'error reading file',C);D.send(A.Response.Status.NOT_FOUND)
	def __init__(A,orch,ip_sink,routes):B=ip_sink;super().__init__(orch,80,L.HTTP);A.tcp=TCP(orch.poller);A.ip_sink=B;A.ip=B.get();A.routes=routes;A.ws_upgrades=set();A.sock.listen(5);A.sock.setblocking(N)
	@P.native
	def handle(self,sock,event):
		D=event;B=sock;A=self
		if B is A.sock:A.accept(B)
		elif D&C.POLLIN:A.read(B)
		elif D&C.POLLOUT:A.write(B)
		else:return U
	def accept(A,server_sock):
		E=server_sock
		try:D,G=E.accept()
		except S as F:return B.exception(F,'failed to accept connection request on',E)
		D.setblocking(N);D.setsockopt(J.SOL_SOCKET,J.SO_REUSEADDR,1);A.orch.register(H(A.proto.transport,D),A);A.poller.register(D,C.POLLIN)
	def parse_request(R,raw_req):C=raw_req;B.info(C);B.flush();L,N=C.split(A.END);E=L.split(A.NL);O,P,*S=E[0].split(b' ');G,*H=P.split(V,1);D=H[0]if M(H)else F;Q={K(A):K(B)for(A,B)in[A.split(b'=')for A in D.split(b'&')]}if D else{};I={A:B for(A,B)in[A.split(b': ',1)for A in E[1:]]};J=I[b'Host'];B.info('HTTP REQUEST:',(J+G).decode());B.debug(C.decode().strip());return A.Request(J,O,G,D,Q,I,N)
	def parse_route(A,req):E=b'/';C=req;B.info(C.path.split(E));G=E+(C.path.split(E)+[D])[1];return(C.host==A.ip or not A.ip_sink.get())and A.routes.get(G,F)
	def handle_request(E,sock,req):
		J=sock;B=req
		if G.KeyHeader in B.headers:cmt('upgrade HTTP to WebSocket');E.ws_upgrades.add(H.of(J));E.prepare(J,G.get_http_upgrade_header(B.headers[G.KeyHeader]));return
		C=A.Response(E,J);F=E.parse_route(B);K=E.ip_sink.get()
		if F:
			if I(F,T):C.file(F)
			elif callable(F):
				F(B,C)
				if not C.sent:C.ok()
			else:C.send(A.Response.Status.NOT_FOUND)
		elif K:C.redirect(b'http://{:s}/portal{:s}'.format(K,V+B.raw_query if B.raw_query else D))
		else:C.file(b'/public'+B.path)
	def read(B,sock):
		C=sock;D=B.tcp.read(C)
		if not D:B.tcp.end(C)
		elif D[-4:]==A.END:E=B.parse_request(D);B.handle_request(C,E)
	def prepare(D,sock,headers,body=F):C=headers;A=body;B.info('HTTP RESPONSE',f": body length {M(A)if I(A,T)else'unknown'}"if A else'','\n',E(C).decode().strip(),sep='');D.tcp.prepare(sock,C,b'\n',A)
	def write(A,sock):
		B=sock
		if A.tcp.write(B):
			D=H.of(B)
			if D in A.ws_upgrades:A.orch.register(D,L.WebSocket);A.poller.register(B,C.POLLIN);cmt('upgraded HTTP to WebSocket');A.tcp.clear(B);A.ws_upgrades.remove(D)
			else:A.tcp.end(B)