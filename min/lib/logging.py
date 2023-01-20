W=len
C=''
import io,sys
from collections import namedtuple as M
import machine as N,uasyncio as D
from lib import defaulter_dict as O
I=50
J=40
K=30
G=20
L=10
P=0
Q={I:'CRIT',J:'ERROR',K:'WARN',G:'INFO',L:'DEBUG'}
E=sys.stderr
def R(*B,**D):A=io.StringIO();print(*B,**D,file=A,end=C);E=A.getvalue();A.close();return E
class A:
	_lock=D.Lock();_loop=D.get_event_loop();_tasks=[]
	async def _atomic_print(*B,**C):
		async with A._lock:print(*B,**C)
	def print(*C,**E):B=D.create_task(A._atomic_print(*C,**E));A._tasks.append(B);A._loop.run_until_complete(B);A._tasks.remove(B)
	def flush():A._loop.run_until_complete(D.gather(*A._tasks))
def S(*B,**C):A.print(*B,**C)
def flush():A.flush()
T=N.RTC()
def U():[A,B,C,D,E,F,G,H]=T.datetime();return f"{A}/{B}/{C} {D}:{E:02}:{F:02}"
class H:
	Record=M('Record','levelname levelno message name')
	@staticmethod
	def default_handler(r):
		F='\n  ';B='\n';A=r.message.lstrip(B);D=B*(W(r.message)-W(A))
		if B in A:A=F+F.join(A.split(B))
		S(D,*['[',r.levelname,r.name and':'+r.name,'] ',U(),' ']if A else C,A,sep=C,file=E)
	def __init__(A,name,level=P):A.name=name;A.level=level;A.handlers=[H.default_handler]
	def set_level(A,level):A.level=level
	def add_handler(A,handler):A.handlers.append(handler)
	def enabled_for(A,level):return level>=(A.level or F)
	def log(B,level,*C,**D):
		A=level
		if B.enabled_for(A):
			E=H.Record(levelname=Q.get(A)or'LVL%s'%A,levelno=A,message=R(*C,**D),name=B.name)
			for F in B.handlers:F(E)
	def debug(A,msg,*B,**C):A.log(L,msg,*B,**C)
	def info(A,msg,*B,**C):A.log(G,msg,*B,**C)
	def warning(A,msg,*B,**C):A.log(K,msg,*B,**C)
	def error(A,msg,*B,**C):A.log(J,msg,*B,**C)
	def critical(A,msg,*B,**C):A.log(I,msg,*B,**C)
	def exception(A,e,msg=C,*B,**C):A.error(msg,*B,**C);sys.print_exception(e,E)
F=G
V=O()
def config(level=F,stream=None):
	A=stream;global F,E;F=level
	if A:E=A
def instance(name=C):return V.get(name,H)
B=instance()
def debug(msg,*A,**C):B.debug(msg,*A,**C)
def info(msg,*A,**C):B.info(msg,*A,**C)
def warning(msg,*A,**C):B.warning(msg,*A,**C)
def error(msg,*A,**C):B.error(msg,*A,**C)
def critical(msg,*A,**C):B.critical(msg,*A,**C)
def exception(e,msg=C,*A,**C):B.exception(e,msg,*A,**C)
class log:
	def __init__(C,*A,**B):info(*A,**B)
	debug=debug;info=info;warning=warning;error=error;critical=critical;exception=exception;config=config;instance=instance;flush=flush
def X(msg,*A,**C):B.info(msg,*A,**C)