"""
miscellaneous utilities
"""
import io
from random import choice

class enum:
    def __init__(self, value): self.value = value
    def __repr__(self): return self.value

class enumstr(enum):
    def __repr__(self):
        if isinstance(self.value, tuple):
            return tuple(
                x.decode() if isinstance(x, (bytes, bytearray)) else x
                for x
                in self.value)
        return (
            self.value.decode()
            if isinstance(self.value, (bytes, bytearray))
            else self.value)


class defaulter_dict(dict):
    def __init__(self, *r, **k):
        super().__init__(*r, **k)

    def get(self, key, defaulter=None):
        value = super().get(key)
        if value is None and defaulter:
            value = defaulter(key)
            self[key] = value
        return value


def compose(*funcs):
    """return composition of functions: f(*x) g(x) h(x) => h(g(f(*x)))"""
    def _inner(*args):
        value = funcs[0](*args)
        for func in funcs[1:]: value = func(value)
        return value
    return _inner

def chain(value, *funcs):
    """pass value through sequence of functions"""
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
    """read bytes as integer"""
    x = 0
    for i in range(len(raw)): x = (x << 8) + raw[i]
    return x


def unquote(string: str or bytes) -> str:
    return unquote_to_bytes(string).decode()
def unquote_to_bytes(string: str or bytes) -> bytes:
    """fill-in for urllib.parse unquote_to_bytes"""

    # return with first two chars after an escape char converted from base 16
    bits = encode(string).split(b'%')
    return bits[0] + b''.join(bytes([int(bit[:2], 16)]) + bit[2:] for bit in bits[1:])


def choices(list, n): return [choice(list) for _ in range(n)]

class string:
    """incomplete fill-in for string module"""
    ascii_lowercase = 'abcdefghijklmnopqrstuvwxyz'
    ascii_uppercase = ascii_lowercase.upper()
    ascii_letters = ascii_lowercase + ascii_uppercase
    digits = '0123456789'

_alphanum = string.digits + string.ascii_letters
_lower_alphanum = string.digits + string.ascii_lowercase
_hex = string.digits + string.ascii_uppercase[:6]
def randtokens(tokens: str, n: int) -> str: return ''.join(choices(tokens, n))
def randalpha(n: int) -> str: return randtokens(string.ascii_letters, n)
def randalphanum(n: int) -> str: return randtokens(_alphanum, n)
def randlower(n: int) -> str: return randtokens(string.ascii_lowercase, n)
def randloweralphanum(n: int) -> str: return randtokens(_lower_alphanum, n)
def randhex(n: int) -> str: return randtokens(_hex, n)


def part(str, n):
    """split string into groups of n tokens"""
    return [str[x:x+n] for x in range(0, len(str), n)]
def delimit(str, n, sep):
    """add delimiter to string between groups of n tokens"""
    return sep.join(part(str, n))


class MergedReadInto:
    """merge multiple str / bytes / IO streams into one"""
    def __init__(self, streams: list[io.BytesIO or io.FileIO or bytes or str]):
        self.iter = iter(
            io.BytesIO(encode(x)) if isinstance(x, (bytes, str)) else x
            for x
            in streams)
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


import time
from machine import Pin, PWM
import uasyncio
class LED:
    """LED with brightness setting. Supports on, off, set, toggle, pulse"""
    PWM_DUTY_CYCLE_MAX = 65535

    def __init__(self, pin='LED', brightness=1):
        pins = pin if isinstance(pin, list) else [pin]
        self.pwms = []
        for pin in pins:
            if not isinstance(pin, Pin): pin = Pin(pin, Pin.OUT)
            pwm = None
            try:
                pwm = PWM(pin)
                pwm.freq(1000)
            except ValueError as e:
                if 'expecting a regular GPIO Pin' in str(e):
                    pwm = LED._PWM_Mock(pin)
                else: raise e
            self.pwms.append(pwm)
        self.brightness = brightness

    def on(self, brightness=None):
        duty = int((
            brightness
            if type(brightness) is float
            else self.brightness) * LED.PWM_DUTY_CYCLE_MAX)
        [x.duty_u16(duty) for x in self.pwms]
    def off(self): [x.duty_u16(0) for x in self.pwms]

    def get(self): 
        return max(x.duty_u16() / LED.PWM_DUTY_CYCLE_MAX for x in self.pwms)
    def set(self, on): self.on(on) if on else self.off()
    def toggle(self): self.off() if self.get() else self.on()

    def pulse(self, seconds=.1):
        async def _inner():
            self.toggle()
            time.sleep(seconds)
            self.toggle()
        uasyncio.create_task(_inner())

    class Mock:
        def on(self, *a): pass
        def off(self, *a): pass
        def set(self, *a): pass
        def toggle(self, *a): pass
        def pulse(self, *a): pass

    class _PWM_Mock:
        def __init__(self, pin): self.pin = pin
        def duty_u16(self, x=None):
            if x is None: return self.pin.value() * LED.PWM_DUTY_CYCLE_MAX
            else: self.pin.value(x / LED.PWM_DUTY_CYCLE_MAX)
