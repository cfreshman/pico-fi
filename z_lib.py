"""
miscellaneous utilities
"""
import io
from random import randint

class enum:
    def __init__(self, value): self.value = value
    def __repr__(self): return self.value

class enumstr(enum):
    def __repr__(self):
        if isinstance(self.value, tuple):
            return tuple(x.decode() if isinstance(x, (bytes, bytearray)) else x for x in self.value)
        return self.value.decode() if isinstance(self.value, (bytes, bytearray)) else self.value

class defaulter_dict(dict):
    def __init__(self, *r, **k):
        super().__init__(*r, **k)

    def get(self, key, defaulter=None):
        value = super().get(key)
        if value is None and defaulter:
            value = defaulter(key)
            self[key] = value
        return value

class MergedReadInto:
    def __init__(self, streams: list[io.BytesIO or io.FileIO or bytes or str]):
        self.iter = iter(io.BytesIO(encode(x)) if isinstance(x, (bytes, str)) else x for x in streams)
        self.curr = next(self.iter)

    def readinto(self, bytes_like_object):
        view = memoryview(bytes_like_object)
        max_write_len = len(view)
        total_bytes_written = 0
        while self.curr and total_bytes_written < max_write_len:
            bytes_written = self.curr.readinto(view[total_bytes_written:])
            if bytes_written == 0:
                try: self.curr = next(self.iter)
                except StopIteration: self.curr = None
            else: total_bytes_written += bytes_written
        return total_bytes_written


def compose(*funcs):
    """return composition of functions: given (f, g, h), return x => h(g(f(*)))"""
    def inner(*args):
        """pass args through series of functions"""
        value = funcs[0](*args)
        for func in funcs[1:]:
            value = func(value)
        return value
    return inner

def chain(value, *funcs):
    """pass value through series of functions"""
    return compose(*funcs)(value)


def encode(string: str or bytes) -> bytes:
    """given string or bytes, return bytes"""
    return string.encode() if isinstance(string, str) else string

def encode_bytes(raw: int, n_bytes: int) -> bytes:
    """fill exact length of bytes"""
    b = b''
    for i in range(n_bytes): b += bytes(raw >> 8 * (n_bytes - 1 - i))
    return b

def decode_bytes(raw: bytes) -> int:
    x = 0
    for i in range(len(raw)): x = (x << 8) + raw[i]
    return x


def unquote(string: str or bytes) -> str: return unquote_to_bytes(string).decode()
def unquote_to_bytes(string: str or bytes) -> bytes:
    """fill-in for urllib.parse unquote_to_bytes"""

    # return with first two chars after an escape char converted from base 16
    bits = encode(string).split(b'%')
    return bits[0] + b''.join(bytes([int(bit[:2], 16)]) + bit[2:] for bit in bits[1:])

def sample(arr): return arr[randint(1, len(arr)) - 1]
def samples(arr, n=1): return [sample(arr) for i in range(n)]

_lower = 'qwertyuiopasdfghjklzxcvbnm'
_alphanum = '1234567890' + _lower + _lower.upper()
_hex = '1234567890abcdef'
def randalphanum(n: int) -> str: return ''.join(samples(_alphanum, n))
def randalpha(n: int) -> str: return ''.join(samples(_lower, n))
def randhex(n: int) -> str: return ''.join(samples(_hex, n))

def part(str, n): return [str[x:x+n] for x in range(0, len(str), n)]
def delimit(str, n, sep): return sep.join(part(str, n))


import time
from machine import Pin, PWM
import uasyncio
class LED:
  PWM_DUTY_CYCLE_MAX = 65535

  def __init__(self, pin, brightness_percent=100):
    if isinstance(pin, int): pin = Pin(pin, Pin.OUT)
    self.pwm = PWM(pin)
    self.brightness = brightness_percent
    self.pwm.freq(1000)

  def on(self, brightness=None): self.pwm.duty_u16(int((brightness or self.brightness) * .01 * LED.PWM_DUTY_CYCLE_MAX))
  def off(self): self.pwm.duty_u16(0)
  def toggle(self): self.off() if self.pwm.duty_u16() else self.on()
  async def _pulse(self):
    self.toggle()
    time.sleep(.1)
    self.toggle()
  def pulse(self): uasyncio.create_task(self._pulse())

  class Mock:
    def on(self, *a): pass
    def off(self, *a): pass
    def toggle(self, *a): pass
    def pulse(self, *a): pass
