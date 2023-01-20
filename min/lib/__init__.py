Z=b''
Y=next
X=int
W=bytearray
V=tuple
K=len
J=str
H=range
F=bytes
D=None
C=isinstance
import io
from random import choice as L
class M:
	def __init__(A,value):A.value=value
	def __repr__(A):return A.value
class a(M):
	def __repr__(A):
		if C(A.value,V):return V((B.decode()if C(B,(F,W))else B for B in A.value))
		return A.value.decode()if C(A.value,(F,W))else A.value
class b(dict):
	def __init__(C,*A,**B):super().__init__(*A,**B)
	def get(E,key,defaulter=D):
		C=defaulter;B=key;A=super().get(B)
		if A is D and C:A=C(B);E[B]=A
		return A
def N(*B):
	def A(*C):
		A=B[0](*C)
		for D in B[1:]:A=D(A)
		return A
	return A
def c(value,*A):return N(*A)(value)
def I(string):A=string;return A.encode()if C(A,J)else A
def d(raw,n_bytes):
	A=n_bytes;B=Z
	for C in H(A):B+=F(raw>>8*(A-1-C))
	return B
def e(raw):
	A=0
	for B in H(K(raw)):A=(A<<8)+raw[B]
	return A
def f(string):return O(string).decode()
def O(string):A=I(string).split(b'%');return A[0]+Z.join((F([X(B[:2],16)])+B[2:]for B in A[1:]))
def P(list,n):return[L(list)for A in H(n)]
class A:ascii_lowercase='abcdefghijklmnopqrstuvwxyz';ascii_uppercase=ascii_lowercase.upper();ascii_letters=ascii_lowercase+ascii_uppercase;digits='0123456789'
Q=A.digits+A.ascii_letters
R=A.digits+A.ascii_lowercase
S=A.digits+A.ascii_uppercase[:6]
def B(tokens,n):return ''.join(P(tokens,n))
def g(n):return B(A.ascii_letters,n)
def h(n):return B(Q,n)
def i(n):return B(A.ascii_lowercase,n)
def j(n):return B(R,n)
def k(n):return B(S,n)
def T(str,n):return[str[A:A+n]for A in H(0,K(str),n)]
def l(str,n,sep):return sep.join(T(str,n))
class m:
	def __init__(A,streams):A.iter=iter((io.BytesIO(I(A))if C(A,(F,J))else A for A in streams));A.curr=Y(A.iter)
	def readinto(A,bytes_like_object):
		C=memoryview(bytes_like_object);F=K(C);B=0
		while A.curr and B<F:
			E=A.curr.readinto(C[B:])
			if E==0:
				try:A.curr=Y(A.iter)
				except StopIteration:A.curr=D
			else:B+=E
		return B
import time
from machine import Pin as G,PWM
import uasyncio as U
class E:
	PWM_DUTY_CYCLE_MAX=65535
	def __init__(B,pin='LED',brightness=1):
		A=pin
		if not C(A,G):A=G(A,G.OUT)
		try:B.pwm=PWM(A);B.pwm.freq(1000)
		except ValueError as D:
			if'expecting a regular GPIO Pin'in J(D):B.pwm=E._PWM_Mock(A)
			else:raise D
		B.brightness=brightness
	def on(A,brightness=D):B=X((brightness or A.brightness)*E.PWM_DUTY_CYCLE_MAX);A.pwm.duty_u16(B)
	def off(A):A.pwm.duty_u16(0)
	def toggle(A):A.off()if A.pwm.duty_u16()else A.on()
	def pulse(A,seconds=0.1):
		async def B():A.toggle();time.sleep(seconds);A.toggle()
		U.create_task(B())
	class Mock:
		def on(A,*B):0
		def off(A,*B):0
		def toggle(A,*B):0
		def pulse(A,*B):0
	class _PWM_Mock:
		def __init__(A,pin):A.pin=pin
		def duty_u16(A,x=D):
			if x is D:return A.pin.value()*E.PWM_DUTY_CYCLE_MAX
			else:A.pin.value(x/E.PWM_DUTY_CYCLE_MAX)