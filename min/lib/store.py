I='store.json'
H=None
C=open
G=dict
F=type
import json as A
from lib.logging import log as D
store={}
class E:
	store=store
	def read(A,store=store):
		D=store
		for B in A:
			if B in D:
				C=D[B]
				if F(C)is G and F(A[B])is G:E.read(A[B],C)
				else:A[B]=C
		return A
	def get(B,default=H):D.info(B,A.dumps(store));return E.read({B:default})[B]
	def write(L,store=store):
		B=store
		for (A,C) in L.items():
			I=F(C)is G;J=A in B;K=J and F(B[A])is G
			if I and K:E.write(C,B[A])
			elif J and not(C is H or B[A]is H)and K!=I:0
			else:B[A]=C
			D.debug('store write',A,C,A in B and B[A])
	def save():B=C(I,'w');B.write(A.dumps(store));D.debug('saved store',store)
	def load():
		try:B=C(I,'r')
		except Exception as F:B=C(I,'x');B.write('')
		E.write(A.loads(B.read()or A.dumps({})));D.debug('loaded store',store)