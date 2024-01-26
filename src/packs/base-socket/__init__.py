"""
Basic module configuration showcase
$ python3 build -a hello-world
"""
from lib.logging import log
from pico_fi import App
from lib.handle.http import HTTP
from lib.handle.ws import WebSocket

sockets = {}

def configure(app: App):

  @app.event('echo-join')
  def join(msg: WebSocket.Message):
    global sockets
    id = msg.content
    if id not in sockets:
      for other in sockets.keys():
        msg.reply('echo-join', other)
      sockets[id] = msg
      for socket in sockets.values():
        socket.reply(f'echo-join {id}')

  @app.event('echo-echo')
  def echo(msg: WebSocket.Message):
    global sockets
    id, message = msg.content.split(' ', 1)
    if id in sockets:  
      for socket in sockets.values():
        socket.reply(f'echo-echo {id} {message}')
  
  @app.event('echo-leave')
  def leave(msg: WebSocket.Message):
    global sockets
    id = msg.content
    if id in sockets:
      del sockets[id]
      for socket in sockets.values():
        socket.reply(f'echo-leave {id}')
