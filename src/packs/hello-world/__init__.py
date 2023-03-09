"""
Basic module configuration showcase

Enable & install on Pico:
$ python3 build --packs hello-world --sync
"""
from lib.logging import log
from pico_fi import App
from lib.handle.http import HTTP
from lib.handle.ws import WebSocket

log.info('HELLO WORLD import')

def configure(app: App):
  # Runs after app is initialized
  log.info('HELLO WORLD configure')

  @app.started
  def started():
    # Runs after access point has been started
    log.info('HELLO WORLD started')

  @app.connected
  def connected():
    # Runs after connected to wifi
    log.info('HELLO WORLD connected')
  
  @app.route('/hello')
  def hello(req: HTTP.Request, res: HTTP.Response):
    # Runs when an HTTP request is made to /hello:
    # > fetch('/hello').then(res => res.text()).then(console.log)
    # < world
    res.text('world')

  @app.event('foo')
  def foo(msg: WebSocket.Message):
    # Runs when a WebSocket message is sent starting with 'foo':
    # > let ws = new WebSocket('ws://'+location.host)
    # > ws.onmessage = e => console.log(e.data)
    # > ws.send('foo test')
    # < bar test
    msg.reply('bar', msg.content)
