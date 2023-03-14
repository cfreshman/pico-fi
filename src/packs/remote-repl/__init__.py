import os, re, _thread, time

from lib.handle.http import HTTP
from lib.handle.ws import WebSocket
from lib import unquote_to_bytes, randalphanum
from lib.logging import str_print, atomic_print, log
from pico_fi import App


_interrupt_ids = set()
_repl_locals = {} # maintain repl context across calls
_tokens = set() # require user auth - saved to user.py
_auth = False
try:
  with open('user.py') as f:
    match = re.match(r'(.+) = "(.+)"', f.read())
    if match:
      _auth = {}
      _auth[match.group(1)] = match.group(2)
      log.info('REPL auth:', _auth)
except: pass


def configure(app: App):

  # TODO re-enable interrupts after debugging background thread issues
  # (unable to accept additional requests even after first REPL completes)
  @app.event('interrupt')
  def interrupt(msg: WebSocket.Message):
    global _interrupt_ids
    log.info('interrupt', msg.s_id)
    _interrupt_ids.add(msg.s_id)

  @app.route('/repl')
  def repl(req: HTTP.Request, res: HTTP.Response):
    global _repl_locals, _tokens, _auth, _interrupt_ids
    log.info('repl')
    
    socket_id = int(req.socket_id or 0)
    log.info('REPL with socket', socket_id)
    socket_id and app.websocket.emit('repl begin', socket_id=socket_id)

    outputs = []
    def _print(*a, log=True, **k):
      line = str_print(*a, **({ 'end': '\n' } | k))
      log and atomic_print('>', line, end='')
      socket_id \
        and app.websocket.emit('log', line, socket_id=socket_id) \
        or outputs.append(line)
      if socket_id in _interrupt_ids:
        _interrupt_ids.remove(socket_id)
        app.websocket.emit('interrupted', socket_id=socket_id)
        raise KeyboardInterrupt('REPL interrupt')
    def _resolve():
      added = set(app.routes.keys()) - routes
      if added: _print('added routes:', ' '.join(x.decode() for x in added))
      res.text(''.join(outputs))
      time.sleep(.1)
      if socket_id: app.websocket.emit('repl complete', socket_id=socket_id)

    try:
      # AUTHORIZATION
      # request auth: ?token
      # provide auth: ?user=####&passhash=####
      #   token = "####" returned
      # normal auth: ?token=####
      # remove auth: ?token=####&user=####
      token = req.query.get('token', None)
      user = req.query.get('user', None)
      passhash = req.query.get('passhash', None)
      authed = (
        not _auth
        or token in _tokens
        or (user in _auth and _auth[user] == passhash))
      if not authed or (
        not _auth and not token is None and not token in _tokens):
        res.send([
          HTTP.Response.Status.NOT_FOUND,
          b'WWW-Authenticate: Basic realm="User Visible Realm"'])
      if user:
        if passhash:
          _auth[user] = passhash
          log.info(f'token = "{randalphanum(16)}"')
        else:
          del _auth[user]
          if not len(_auth): _auth = False
        if _auth:
          with open('user.py', 'w') as f: f.write(f'{user} = "{passhash}"')
        else: os.remove('user.py')

      command = unquote_to_bytes(req.query.get('command', '')).decode()
      app.websocket.emit('command', command)

      run_option = unquote_to_bytes(req.query.get('run_option', '')).decode()
      log.info(
        ('run option: '+run_option+'\n' if run_option else '') + 
        command + '\n')

      if len(command.split('\n')) == 1: command = f'print({command})'
      if run_option == 'startup':
        with open('startup.py', 'w') as f: f.write(command)
      _repl_locals['app'] = app
      routes = set(app.routes.keys())
      try: exec(command, globals() | { 'print': _print }, _repl_locals)
      except KeyboardInterrupt as e: _print(repr(e), log=False)
      _resolve()
      log.info('REPL completed')
      
    except Exception as e:
      log.exception(e, 'REPL outer')
      _print(repr(e), log=False)
      _resolve()

  # Run saved script on startup
  try:
    with open('startup.py') as f:
      command = f.read()
      if command:
        log.info('remote-repl: startup script')
        exec(command, globals(), _repl_locals | { 'app': app })
  except:
    log.info('remote-repl: no startup script')
