e='bssid'
d='network'
c=':'
b=sorted
a=isinstance
S='status'
R=b'/'
Q=len
N='data'
M=True
J='key'
F='ssid'
E=False
D=None
import binascii as G,gc,json,select as T,time as H,network as I,machine,uasyncio as U
from lib.handle.dns import DNS
from lib.handle.http import HTTP as O
from lib.handle.ws import WebSocket as V
from lib import encode as W,randlower as X,delimit as P,LED as K
from lib.logging import cmt,log as B
from lib.server import Orchestrator as Y,SocketPollHandler,IpSink as Z
from lib.store import Store as C
class L:
	IP='192.168.4.1'
	def __init__(A,id=D,password='',indicator=D):
		C=password;B=indicator;A.id=id;A.sta_ip=D;A.sta=I.WLAN(I.STA_IF)
		if A.sta.isconnected():A.sta.disconnect()
		A.sta.active(E);A.ip_sink=Z(L.IP);A.ap_ip=A.ip_sink.get();A.ap=I.WLAN(I.AP_IF)
		if A.ap.isconnected():A.ap.disconnect()
		A.ap.active(E);A.ap.config(password=C)
		if not C:A.ap.config(security=0)
		A.ap.ifconfig((A.ap_ip,'255.255.255.0',A.ap_ip,A.ap_ip));A.poller=T.poll();A.orch=Y(A.poller);A.servers=[];A.routes={b'/portal':b'/public/portal.html',R:b'/public/index.html',b'/favicon.ico':b'',b'/get':A.get,b'/set':A.set,b'/api':A.api}
		if B and not a(B,K):B=K(B,0.05)
		A.indicator=B or K.Mock()
	def route(B,path):
		D='/';A=path
		if A[0]!=D:A=D+A
		def C(handler):
			def C(*A,**B):handler(*A,**B)
			B.routes[W(A)]=C
		return C
	def start(A):
		cmt('start pico-fi');C.load();A.servers=[DNS(A.orch,A.ap_ip),V(A.orch),O(A.orch,A.ip_sink,A.routes)];F='id'
		if not A.id or a(A.id,int):A.id=C.get(F,'w-'+X(A.id or 7))
		A.ap.config(essid=A.id);open('board.py','w').write(f'name = "{A.id}"');C.write({F:A.id});A.ap.active(M);A.indicator.on();B.info('access point:',A.ap.config('essid'),A.ap.ifconfig());E=b(A.sta.scan(),key=lambda x:-x[3]);B.info('found',Q(E),'networks')
		if E:
			H=max((Q(A[0])for A in E))
			for D in E:I=D[0].decode()+' '*(H-Q(D[0]));J=P(G.hexlify(D[1]).decode(),2,c);B.info(f"{-D[3]} {I} ({J}) chnl={D[2]} sec={D[4]} hid={D[5]}")
		A.connect()
	def connect(A,ssid=D,key=D,wait=M):
		I=wait;G=key;D=ssid;N=d
		if not D:
			K=C.get(N);B.info('stored network login:',K)
			if not K:return
			D=K[F];G=K[J]
		else:B.info('store network login:',{F:D,J:G});C.write({N:{F:D,J:G}});C.save()
		A.sta.active(M);A.sta.connect(D,G)
		if not I:return
		I=10
		while I>0:
			I-=1;L=A.sta.status();B.info(f"network connect attempt status",L)
			if 0<=L<3:H.sleep(1)
			else:break
		if L==3:A.sta_ip=A.sta.ifconfig()[0];A.ip_sink.set(E);B.info(f"network connected with ip",A.sta_ip)
		else:B.info('network connect failed');A.sta.active(E)
	def stop(A):
		cmt('stop pico-fi');A.indicator.off();A.ap.active(E);A.sta.active(E)
		for D in A.servers:D.stop()
		C.save();B.flush();gc.collect()
	def switch(A,req,res):
		if A.ip_sink.get():res.redirect(b'http://{:s}/portal'.format(A.ip_sink.get()))
		else:res.redirect(b'http://{:s}/'.format(L.IP))
	def _parse_data_from_query(D,query):C='{}';A=query;B.debug(A.get(N,C));return{N:json.loads(A.get(N,C))}
	def get(D,req,res):A=D._parse_data_from_query(req.query);B.info('get',A);C.read(A);res.json(A)
	def set(D,req,res):A=D._parse_data_from_query(req.query);B.info('set',A);C.write(A);res.ok();B.debug('updated store',C.store)
	def api(A,req,res):
		C=req;E=C.path.split(R)[2:];H=E[0];I=R.join(E);F=A._parse_data_from_query(C.query)[N];B.info('api',I,F);G={b'networks':A.api_networks,b'network-connect':A.api_network_connect,b'network-status':A.api_network_status,b'network-switch':A.api_network_switch,b'network-disconnect':A.api_network_disconnect}.get(H,D)
		if G:G(C,F,res)
		else:res.send(O.Response.Status.NOT_FOUND)
	def api_networks(B,req,data,res):A=[{F:A[0],'pretty_bssid':P(G.hexlify(A[1]).decode(),2,c),e:G.hexlify(A[1]).decode(),'channel':A[2],'RSSI':A[3],'security':A[4],'hidden':A[5]}for A in b(B.sta.scan(),key=lambda x:-x[3])];res.json(A)
	def api_network_connect(C,req,data,res):A=data;B.info('network connect',A[F],A[J],G.unhexlify(A[e]));C.connect(A[F],A[J],E);res.json({S:C.sta.status()})
	def api_network_status(A,req,data,res):
		D=res;C=A.sta.status();B.info(f"network connect status",C)
		if C==3:A.sta_ip=A.sta.ifconfig()[0];B.info(f"network connected with ip",A.sta_ip);D.json({'ip':str(A.sta_ip),F:A.sta.config(F)})
		elif C>=0:D.json({S:C})
		else:D.json({'error':'connection error',S:C})
	def api_network_switch(A,req,data,res):
		B.info('network switch')
		if A.sta_ip:
			res.ok()
			async def C():H.sleep(1.5);A.ip_sink.set(E);A.ap.active(E)
			U.create_task(C())
		else:res.error('not connected to the internet')
	def api_network_disconnect(A,req,data,res):B.info('network disconnect');A.sta.disconnect();C.write({d:D});res.ok()
	def run(A):
		A.start()
		try:
			D=H.time()
			while M:
				gc.collect()
				for F in A.poller.ipoll(60000):A.indicator.pulse();A.orch.handle(*F)
				E=H.time()
				if E-D>60:C.save();D=E
		except Exception as G:B.exception(G);A.stop()
def run(id=D,password='',indicator=D):A=L(id,password,indicator);A.run();return A