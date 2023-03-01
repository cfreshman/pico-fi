import os, re, io, sys

from lib.handle.http import HTTP
from lib import unquote_to_bytes, randalphanum
from lib.logging import str_print, atomic_print, log
from lib.bootsel import pressed
from pico_fi import App

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


def configure(app):

  @app.route('/repl')
  def repl(req: HTTP.Request, res: HTTP.Response):
    global _repl_locals, _tokens, _auth
    
    outputs = []
    def _print(*a, **k):
      line = str_print(*a, **({ 'end': '\n' } | k))
      atomic_print('>', line, end='')
      outputs.append(line)
    
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
          print(f'token = "{randalphanum(16)}"')
        else:
          del _auth[user]
          if not len(_auth): _auth = False
        if _auth:
          with open('user.py', 'w') as f: f.write(f'{user} = "{passhash}"')
        else: os.remove('user.py')

      command = unquote_to_bytes(req.query['command']).decode()
      log.info('repl\n' + command + '\n')
      _repl_locals['app'] = app
      routes = set(app.routes.keys())
      exec(command, globals() | { 'print': _print }, _repl_locals)
      added = set(app.routes.keys()) - routes
      if added: 
        print('added routes:', added)
        outputs.append(f'added routes: {" ".join(x.decode() for x in added)}')
      res.text(''.join(outputs))
    except Exception as e:
      result = repr(e)
      log.error(e)
      res.text('error: ' + result)
