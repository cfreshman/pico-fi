'\nMain orchestration class\n'
_I='status'
_H='data'
_G='key'
_F='connect'
_E='start'
_D=True
_C='ssid'
_B=None
_A=False
import binascii,gc,json,select,time,os,network,uasyncio
from lib.handle.dns import DNS
from lib.handle.http import HTTP
from lib.handle.ws import WebSocket
from lib import encode,randlower,delimit,LED
from lib.logging import cmt,log
from lib.server import Orchestrator,SocketPollHandler,IpSink
from lib.store import Store
class App:
	'\n    Pico W access point serving single offline website with persistent get/set API\n\n    This serves as a communication node between clients\n    It provides the common site, persistent state, and websockets\n    Design the site to offload processing & temporary storage to the client\n    ';IP='192.168.4.1'
	def __init__(A,id=_B,password='',indicator=_B):
		L='packs';H=password;G='configure';F='routes';C=indicator;A.running=_A;A.id=id;A.sta_ip=_B;A.sta=network.WLAN(network.STA_IF)
		if A.sta.isconnected():A.sta.disconnect()
		A.sta.active(_A);A.ip_sink=IpSink(App.IP);A.ap_ip=A.ip_sink.get();A.ap=network.WLAN(network.AP_IF)
		if A.ap.isconnected():A.ap.disconnect()
		A.ap.active(_A);A.ap.config(password=H)
		if not H:A.ap.config(security=0)
		A.ap.ifconfig((A.ap_ip,'255.255.255.0',A.ap_ip,A.ap_ip));A.poller=select.poll();A.orch=Orchestrator(A.poller);A.servers=[];A.routes={b'/portal':b'/public/portal.html',b'/':b'/public/index.html',b'/favicon.ico':b'',b'/get':A.get,b'/set':A.set,b'/api':A.api}
		if C and not isinstance(C,LED):C=LED(C,0.05)
		A.indicator=C or LED.Mock();A.effects={_E:[],_F:[]}
		try:
			I=getattr(__import__(L),L);log.info('defined packs:',I)
			for J in I:
				try:
					log.info('import',f"packs/{J}");K=__import__(f"packs/{J}");B={}
					for D in [F,G]:
						if hasattr(K,D):B[D]=getattr(K,D)
					if len(B):log.info('-',*B.keys())
					if F in B:A.routes=A.routes|B[F]
					if G in B:B[G](A)
				except Exception as E:log.error(E)
			log.info('configured routes:',*A.routes.keys())
		except Exception as E:log.exception(E)
	def route(B,path):
		"\n        decorator for HTTP requests\n\n        @app.route('/foo')\n        def bar(req, res):\n            res.text(req.params['baz'])\n        ";A=path
		if A[0]!='/':A='/'+A
		def C(handler):
			def C(*A,**B):handler(*(A),**B)
			B.routes[encode(A)]=C
		return C
	def started(A,func):"\n        decorator for start callbacks\n\n        @app.started\n        def start():\n            print('started')\n        ";A.effects[_E].append(func);return func
	def connected(A,func):"\n        decorator for connect callbacks\n\n        @app.connected\n        def connect():\n            print('connected')\n        ";A.effects[_F].append(func);return func
	def start(A):
		cmt('start pico-fi');Store.load();A.servers=[DNS(A.orch,A.ap_ip),WebSocket(A.orch),HTTP(A.orch,A.ip_sink,A.routes)];D='id'
		if not A.id or isinstance(A.id,int):A.id=Store.get(D,'w-'+randlower(A.id or 7))
		A.ap.config(essid=A.id);open('board.py','w').write(f'name = "{A.id}"');Store.write({D:A.id});A.ap.active(_D);A.indicator and A.indicator.on();log.info('access point:',A.ap.config('essid'),A.ap.ifconfig());C=sorted(A.sta.scan(),key=lambda x:-x[3]);log.info('found',len(C),'networks')
		if C:
			E=max((len(A[0])for A in C))
			for B in C:F=B[0].decode()+' '*(E-len(B[0]));G=delimit(binascii.hexlify(B[1]).decode(),2,':');log.info(f"{-B[3]} {F} ({G}) chnl={B[2]} sec={B[4]} hid={B[5]}")
		while A.effects[_E]:A.effects[_E].pop(0)()
		A.connect()
	def connect(A,ssid=_B,key=_B,wait=_D):
		E=key;D=wait;C=ssid;H='network.json'
		if not C:
			try:
				with open(H)as F:B=json.loads(F.read())
				log.info('stored network login:',B);C=B[_C];E=B[_G]
			except:log.info('no stored network login');return
		else:
			B={_C:C,_G:E};log.info('store network login:',B)
			with open(H,'w')as F:F.write(json.dumps(B))
		A.sta.active(_D);A.sta.connect(C,E)
		if not D:return
		D=10
		while D>0:
			D-=1;G=A.sta.status();log.info(f"network connect attempt status",G)
			if 0<=G<3:time.sleep(1)
			else:break
		if G==3:
			A.sta_ip=A.sta.ifconfig()[0];A.ip_sink.set(_A);log.info(f"network connected with ip",A.sta_ip);log.info(f"OPEN http://{A.sta_ip} TO ACCESS PICO W")
			while A.effects[_F]:A.effects[_F].pop(0)()
		else:log.info('network connect failed');A.sta.active(_A)
	def stop(A):
		cmt('stop pico-fi');A.indicator and A.indicator.off();A.ap.active(_A);A.sta.active(_A)
		for B in A.servers:B.stop()
		Store.save();log.flush();gc.collect();A.running=_A
	def switch(A,req,res):
		if A.ip_sink.get():res.redirect(b'http://{:s}/portal'.format(A.ip_sink.get()))
		else:res.redirect(b'http://{:s}/'.format(App.IP))
	'\n    get and set query with single param data=<JSON>\n    '
	def _parse_data_from_query(B,query):A=query;log.debug(A.get(_H,'{}'));return{_H:json.loads(A.get(_H,'{}'))}
	def get(B,req,res):A=B._parse_data_from_query(req.query);log.info('get',A);Store.read(A);res.json(A)
	def set(B,req,res):A=B._parse_data_from_query(req.query);log.info('set',A);Store.write(A);res.ok();log.debug('updated store',Store.store)
	def api(A,req,res):
		B=req;C=B.path.split(b'/')[2:];F=C[0];G=b'/'.join(C);D=A._parse_data_from_query(B.query)[_H];log.info('api',G,D);E={b'networks':A.api_networks,b'network-connect':A.api_network_connect,b'network-status':A.api_network_status,b'network-switch':A.api_network_switch,b'network-disconnect':A.api_network_disconnect}.get(F,_B)
		if E:E(B,D,res)
		else:res.send(HTTP.Response.Status.NOT_FOUND)
	def api_networks(B,req,data,res):A=[{_C:A[0],'pretty_bssid':delimit(binascii.hexlify(A[1]).decode(),2,':'),'bssid':binascii.hexlify(A[1]).decode(),'channel':A[2],'RSSI':A[3],'security':A[4],'hidden':A[5]}for A in sorted(B.sta.scan(),key=lambda x:-x[3])];res.json(A)
	def api_network_connect(B,req,data,res):A=data;log.info('network connect',A[_C],A[_G],binascii.unhexlify(A['bssid']));B.connect(A[_C],A[_G],_A);res.json({_I:B.sta.status()})
	def api_network_status(A,req,data,res):
		C=res;B=A.sta.status();log.info(f"network connect status",B)
		if B==3:A.sta_ip=A.sta.ifconfig()[0];log.info(f"network connected with ip",A.sta_ip);C.json({'ip':str(A.sta_ip),_C:A.sta.config(_C)})
		elif B>=0:C.json({_I:B})
		else:C.json({'error':'connection error',_I:B})
	def api_network_switch(A,req,data,res):
		log.info('network switch')
		if A.sta_ip:
			res.ok()
			async def B():
				time.sleep(1.5);A.ip_sink.set(_A);A.ap.active(_A)
				for B in A.connectCallbacks:B()
				A.connectCallbacks=[]
			uasyncio.create_task(B())
		else:res.error('not connected to the internet')
	def api_network_disconnect(A,req,data,res):log.info('network disconnect');A.sta.disconnect();Store.write({'network':_B});res.ok()
	def run(A):
		if A.running:return
		A.running=_D;A.start()
		try:
			B=time.time()
			while _D:
				gc.collect()
				for D in A.poller.ipoll(60000):A.indicator and A.indicator.pulse();A.orch.handle(*(D))
				C=time.time()
				if C-B>60:Store.save();B=C
		except Exception as E:log.exception(E);A.stop()
def run(id=_B,password='',indicator=_B):A=App(id,password,indicator);A.run();return A