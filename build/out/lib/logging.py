"""
timestamped level-logging
"""
import io
import sys
from collections import namedtuple

import machine
import uasyncio

from lib import defaulter_dict

CRITICAL = 50
ERROR = 40
WARNING = 30
INFO = 20
DEBUG = 10
NOTSET = 0
_level_dict = {
    CRITICAL: 'CRIT',
    ERROR: 'ERROR',
    WARNING: 'WARN',
    INFO: 'INFO',
    DEBUG: 'DEBUG',
}

_stream = sys.stderr


def str_print(*args, **kwargs):
    output = io.StringIO()
    print(*args, **({ 'end':'' } | kwargs | { 'file':output }))
    value = output.getvalue()
    output.close()
    return value


class AtomicPrint:
    _lock = uasyncio.Lock()
    _loop = uasyncio.get_event_loop()
    _tasks = []

    async def _atomic_print(*args, **kwargs):
        async with AtomicPrint._lock: print(*args, **kwargs)

    def print(*args, **kwargs):
        task = uasyncio.create_task(AtomicPrint._atomic_print(*args, **kwargs))
        AtomicPrint._tasks.append(task)
        AtomicPrint._loop.run_until_complete(task)
        AtomicPrint._tasks.remove(task)

    def flush():
        AtomicPrint._loop.run_until_complete(uasyncio.gather(*AtomicPrint._tasks))


def atomic_print(*args, **kwargs):
    AtomicPrint.print(*args, **kwargs)

def flush():
    AtomicPrint.flush()


rtc = machine.RTC()
def timestamp():
    [year, month, mday, hour, minute, second, weekday, yearday] = rtc.datetime()
    return f'{year}/{month}/{mday} {hour}:{minute:02}:{second:02}'


class Logger:
    """atomic logger"""
    Record = namedtuple('Record', 'levelname levelno message name')

    @staticmethod
    def default_handler(r):
        """output message as [LEVEL:logger] timestamp message"""

        # move newlines above [LEVEL]
        message = r.message.lstrip('\n')
        spacer = '\n' * (len(r.message) - len(message))
        if '\n' in message:
            message = '\n  ' + '\n  '.join(message.split('\n'))
        atomic_print(
            spacer,
            *['[', r.levelname, r.name and ':'+r.name, '] ', timestamp(), ' '] if message else '',
            message, sep='', file=_stream)

    def __init__(self, name, level=NOTSET):
        self.name = name
        self.level = level
        self.handlers = [Logger.default_handler]

    def set_level(self, level): self.level = level
    def add_handler(self, handler): self.handlers.append(handler)
    def enabled_for(self, level): return level >= (self.level or _level)

    def log(self, level, *r, **k):
        if self.enabled_for(level):
            record = Logger.Record(
                levelname=_level_dict.get(level) or 'LVL%s' % level,
                levelno=level,
                message=str_print(*r, **k),
                name=self.name)
            for h in self.handlers: h(record)

    def debug(self, *r, **k): self.log(DEBUG, *r, **k)
    def info(self, *r, **k): self.log(INFO, *r, **k)
    def warning(self, *r, **k): self.log(WARNING, *r, **k)
    def error(self, *r, **k): self.log(ERROR, *r, **k)
    def critical(self, *r, **k): self.log(CRITICAL, *r, **k)
    def exception(self, e, *r, **k):
        self.error(*r, **k)
        sys.print_exception(e, _stream)


_level = INFO
# _level = DEBUG
_loggers = defaulter_dict()

def config(level=_level, stream=None):
    global _level, _stream
    _level = level
    if stream: _stream = stream

def instance(name=""): return _loggers.get(name, Logger)

root = instance()
def debug(*r, **k): root.debug(*r, **k)
def info(*r, **k): root.info(*r, **k)
def warning(*r, **k): root.warning(*r, **k)
def error(*r, **k): root.error(*r, **k)
def critical(*r, **k): root.critical(*r, **k)
def exception(e, msg='', *r, **k): root.exception(e, *r, **k)

class log:
    def __init__(self, *r, **k): info(*r, **k)
    debug = debug
    info = info
    warning = warning
    error = error
    critical = critical
    exception = exception

    config = config
    instance = instance
    flush = flush

def cmt(*r, **k): root.info(*r, **k)
