"""
Basic module configuration showcase
$ python3 build -a hello-world
"""
from lib.logging import log
from pico_fi import App
from lib.handle.http import HTTP
from lib.handle.ws import WebSocket
import json
import gc

sockets = {}

def configure(app: App):

  @app.event('chess-join')
  def join(msg: WebSocket.Message):
    global sockets
    id, room_id, *_ = json.loads(msg.content)
    if id not in sockets:
      for other in sockets.keys():
        msg.reply('chess-join', other)
      sockets[id] = msg
      for socket in sockets.values():
        socket.reply(f'chess-join:{room_id} {id}')
    gc.collect()

  @app.event('chess-echo')
  def echo(msg: WebSocket.Message):
    global sockets
    id, room_id, *message = json.loads(msg.content)
    if id in sockets:  
      for socket in sockets.values():
        socket.reply(f'chess-echo:{room_id} {id} {json.dumps(message)}')
    gc.collect()
  
  @app.event('chess-emit')
  def emit(msg: WebSocket.Message):
    global sockets
    id, room_id, *message = json.loads(msg.content)
    if id in sockets:  
      for other, socket in sockets.items():
        if other != id:
          socket.reply(f'chess-emit:{room_id} {id} {json.dumps(message)}')
    gc.collect()

  @app.event('chess-leave')
  def leave(msg: WebSocket.Message):
    global sockets
    id, room_id, *_ = json.loads(msg.content)
    if id in sockets:
      del sockets[id]
      for socket in sockets.values():
        socket.reply(f'chess-leave:{room_id} {id}')
    gc.collect()
