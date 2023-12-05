"""
Play a 2-player game of mastermind
$ python3 build -a mastermind

TODO allow multiple games at once
"""
from lib import randloweralphanum
from lib.logging import log
from pico_fi import App
from lib.handle.http import HTTP
from lib.handle.ws import WebSocket
from machine import Pin
import json

_sockets = {}
_player_to_room = {}
_rooms = {}
def broadcast_state(code, others=[]):
  room = _rooms[code]
  for p_id in room['players'] + others:
    _player_to_room[p_id] = room['code']
    socket = _sockets[p_id]
    state = { 'room': room }
    socket and socket.reply(f'lobby-state {p_id} {json.dumps(state)}')
def do_leave_room(p_id, code):
  global _sockets, _rooms, _player_to_room, broadcast_state
  if code in _rooms:
    room = _rooms[code]
    if p_id in room['players']:
      room['players'].remove(p_id)
      del _player_to_room[p_id]
      broadcast_state(room['code'], [p_id])


def configure(app: App):

  @app.event('lobby-join')
  def join(msg: WebSocket.Message):
    global _sockets, _socket_to_player, _rooms, _player_to_room, broadcast_state, do_leave_room
    while True:
      p_id = randloweralphanum(8)
      if not p_id in _sockets:
        _sockets[p_id] = msg
        msg.reply(f'lobby-joined {p_id}')
        break
  
  @app.event('lobby-leave')
  def leave(msg: WebSocket.Message):
    global _sockets, _rooms, _player_to_room, broadcast_state, do_leave_room
    p_id = msg.content
    if p_id in _player_to_room: do_leave_room(p_id, _player_to_room[p_id])
    _sockets[p_id] = None
  
  @app.event('lobby-room-create')
  def room_create(msg: WebSocket.Message):
    global _sockets, _rooms, _player_to_room, broadcast_state, do_leave_room
    p_id = msg.content
    print(p_id, 'new room')
    if p_id in _player_to_room: do_leave_room(p_id, _player_to_room[p_id])
    while True:
      code = randloweralphanum(4)
      if not code in _rooms: break
    room = { 'code': code, 'players': [p_id], 'capacity': 4 }
    _rooms[code] = room
    _player_to_room[p_id] = code
    broadcast_state(code)

  @app.event('lobby-room-join')
  def room_join(msg: WebSocket.Message):
    global _sockets, _rooms, _player_to_room, broadcast_state, do_leave_room
    p_id, code = msg.content.split(' ')
    print(p_id, 'join', code)
    # leave previous room
    if p_id in _player_to_room: do_leave_room(p_id, _player_to_room[p_id])
    if code in _rooms:
      room = _rooms[code]
      if len(room['players']) < room['capacity']:
        room['players'].append(p_id)
        _player_to_room[p_id] = code
        broadcast_state(code)
  
  @app.event('lobby-room-leave')
  def room_leave(msg: WebSocket.Message):
    global _sockets, _rooms, _player_to_room, broadcast_state, do_leave_room
    p_id, code = msg.content.split(' ')
    print(p_id, 'leave', code)
    do_leave_room(p_id, code)

  @app.route('/lobby-state')
  def state(req: HTTP.Request, res: HTTP.Response):
    global _sockets, _rooms, _player_to_room, broadcast_state, do_leave_room

    res.json({
      'rooms': _rooms,
    })
