"""
Play a 2-player game of mastermind
$ python3 build -a mastermind

TODO allow multiple games at once
"""
from lib.logging import log
from pico_fi import App
from lib.handle.http import HTTP
from lib.handle.ws import WebSocket
from machine import Pin

class State:
  INIT = 'init'
  PLAY = 'play'
  WIN = 'win'
  LOSE = 'lose'
class Mode:
  SINGLE = 'single'
  MULTI = 'multi'
class Color:
  RED = 'red'
  GREEN = 'green'
  YELLOW = 'yellow'
  BLUE = 'blue'
  WHITE = 'white'
  BLACK = 'black'

_state = State.INIT
_mode = Mode.MULTI
_code = []
_guesses = []
_feedbacks = []
_sockets = [None, None]
def broadcast_played():
  for i, socket in enumerate(_sockets): socket and socket.reply(f'mastermind-played {i}')

def configure(app: App):

  MAX_GUESSES = 10

  @app.event('mastermind-join')
  def join(msg: WebSocket.Message):
    global _state, _mode, _code, _guesses, _feedbacks, _sockets, broadcast_played

    if not _sockets[0]:
      _sockets[0] = msg
      broadcast_played()
    elif not _sockets[1]:
      _sockets[1] = msg
      broadcast_played()
    else:
      msg.reply('mastermind-full')
  
  @app.event('mastermind-leave')
  def leave(msg: WebSocket.Message):
    global _state, _mode, _code, _guesses, _feedbacks, _sockets, broadcast_played

    p_id = int(msg.content)
    if p_id < 2:
      _sockets[p_id] = None
  
  @app.event('mastermind-play')
  def play(msg: WebSocket.Message):
    global _state, _mode, _code, _guesses, _feedbacks, _sockets, broadcast_played

    p_id, *code = msg.content.split(' ')
    p_id = int(p_id)
    print(p_id, 'played', code)
    played = False
    if _state == State.PLAY and p_id == 1 and _mode == Mode.MULTI:
      _guesses.append(code)

      correct = 0
      expected_counts = {}
      actual_counts = {}
      for i in range(4):
        if code[i] == _code[i]:
          correct += 1
        else:
          if _code[i] not in expected_counts: expected_counts[_code[i]] = 0
          expected_counts[_code[i]] += 1
          if code[i] not in actual_counts: actual_counts[code[i]] = 0
          actual_counts[code[i]] += 1
      common = 0
      for color, actual in actual_counts.items():
        expected = expected_counts[color] if color in expected_counts else 0
        common += min(actual, expected)
      _feedbacks.append([correct, common])

      if code == _code:
        _state = State.WIN
      elif len(_guesses) > MAX_GUESSES:
        _state = State.LOSE
      played = True

    elif _state == State.INIT and p_id == 0 and _mode == Mode.MULTI:
      _code = code
      _state = State.PLAY
      played = True
    
    if played: broadcast_played()
  
  @app.event('mastermind-new')
  def new(msg: WebSocket.Message):
    global _state, _mode, _code, _guesses, _feedbacks, _sockets, broadcast_played

    p_id = int(msg.content)
    print(p_id, 'new game')
    if _state in [State.LOSE, State.WIN] and p_id == 0:
      _state = State.INIT
      _code = []
      _guesses = []
      _feedbacks = []
      _sockets = _sockets[::-1]
      broadcast_played()
    
  @app.route('/mastermind-state')
  def state(req: HTTP.Request, res: HTTP.Response):
    global _state, _mode, _code, _guesses, _feedbacks, _sockets, broadcast_played

    res.json({
      'state': _state,
      'mode': _mode,
      'code': _code,
      'guesses': _guesses,
      'feedbacks': _feedbacks,
    })
