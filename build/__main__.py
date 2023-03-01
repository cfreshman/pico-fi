"""
PICO-FI BUILD

python3 build --help

# Basic automatic minified builds
python3 build --minify --sync --watch
python3 build --auto

# Minimize app size
python3 build -packs basic --clean --minify --sync --watch

# Enable web-based MicroPython console
python3 build -p remote-repl -mcws
"""

import argparse, os, time, re, sys, signal, subprocess, json

try:

  def flag_or_str_kwargs():
    return {
      'nargs': '?', 'const': True, 'default': False,
    }

  module_options = os.listdir('src/packs')
  default_board_name = 'w-pico'
  def kill(pid):
    if pid:
      os.kill(pid, signal.SIGINT)
      time.sleep(.1)
      os.system(f'kill -9 {pid}')
  def rshell(command, seconds=5):
    if args.verbose: print('   ', 'rshell', command)
    r, w = os.pipe()
    process = pid = None
    try:
      pid = os.fork()
      if pid:
        os.close(w)
        with os.fdopen(r) as f:
          import select
          i, o, e = select.select([f], [], [], seconds)
          if i: return f.read()
          else: print('rshell command timed out - try reconnecting your Pico')
      else:
        os.close(r)
        _r, _w = os.pipe()
        with os.fdopen(_w, 'w') as f:
          process = subprocess.Popen(
          f'rshell --quiet "{command}"', shell=True,
          stdout=f, stderr=f)
        with os.fdopen(_r) as f: result = f.read()
        if args.verbose: [print('   ', x) for x in result.split('\n')]
        with os.fdopen(w, 'w') as f: f.write(result)
    except KeyboardInterrupt: pass
    except Exception as e: print(e)
    finally:
      kill(pid)
      kill(process and process.pid)
    sys.exit(0) # exit if value not returned
  def indent(command):
    process = subprocess.Popen(
      command, shell=True,
      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
      encoding='utf-8', bufsize=1)
    while process.poll() is None:
      line = process.stdout.readline()
      if line: print('   ', line, end='', flush=True)

  parser = argparse.ArgumentParser(
    prog='python3 build',
    description='Build and minify pico-fi',
    epilog='Automatically build and sync remote-repl:\npython3 build -a --packs remote-repl')
  parser.add_argument('-p', '--packs', action='append',
    help=', '.join(module_options))
  parser.add_argument('-m', '--minify', action='store_true',
    help="reduce app size (50%% on average)")
  parser.add_argument('-w', '--watch', action='store_true',
    help="rebuild when files change")
  parser.add_argument('-s', '--sync', **flag_or_str_kwargs(),
    help="sync build to Pico at /<SYNC>, or /w-pico by default, and restart")
  parser.add_argument('-c', '--clean', action='store_true', 
    help="WARNING - may result in data loss: clear extra on-board files")
  parser.add_argument('-a', '--auto', action='store_true', 
    help="same as --watch --minify --sync")
  parser.add_argument('-v', '--verbose', action='store_true', 
    help="show additional output (rshell commands)")
  parser.add_argument('-n', '--network',
    help='wireless network as name:password')
  parser.add_argument('PACKS')

  args = parser.parse_args()
  packs = (args.PACKS or '').split(',')
  for pack in args.packs or []: packs.extend(pack.split(','))
  args.packs = packs
  if args.auto:
    args.watch = args.minify = True
    if not args.sync: args.sync = True
  if args.sync:
    def _read_boards():
      result = rshell('boards') or ''
      return [x.split(' @ ')[0] for x in result.split('\n') if '@' in x]
    board_names = _read_boards()
    print('Connected boards:', ''.join(board_names) or None)
    if not board_names:
      print(f"Retrying in 10s")
      time.sleep(5)
      board_names = _read_boards()
      if not board_names:
        print(f"Connect your Pico or run without --sync")
        sys.exit(0)
    if args.sync is True: args.sync = board_names[0]
    elif args.sync not in board_names: 
      print(f"Couldn't find board \"{args.sync}\"")
      sys.exit(0)
    
  print(args)

  # 1. Clear out/ and min/
  # 1. Copy src/ to out/
  # 2. Copy packs to out/
  # 3. (Optional) Minify
  # 4. (Optional) Sync to board
  # 4. (Optional) Watch for updates

  if 'help' in args: print(parser.print_help())
  else:
    while True:
      start = time.time()
      print('\nBuilding pico-fi')

      os.system('rm -rf build/out && rm -rf build/min')
      if args.sync and args.clean:
        print("\nCleaning existing files from Pico")
        time.sleep(3) # give user 3s to stop if not intentional
        os.system(f"""
        mkdir -p build/save
        """)
        rshell(f'cp /{args.sync}/board.py build/save/')
        rshell(f'cp /{args.sync}/store.json build/save/')
        rshell(f'cp /{args.sync}/network.json build/save/')
        rshell(f'rm -rf /{args.sync}')
        rshell(f'cp build/save/* /{args.sync}')

      # Only copy new files & changes to avoid excessive rsync
      # Copy src/* to out/
      # Copy src/packs/<name>/* to out/packs
      # Copy src/packs/<name>/public/* to out/public
      # Write module list to out/packs/__init__.py
      written = set()
      potential_conflicts = set()
      for (name, walk) in [
        ('src', os.walk('src')),
        *(('packs', os.walk(f'src/packs/{x}')) for x in args.packs or [])]:
        for root, dirs, files in walk:
          if 'src' == name and 'packs' in root: continue
          for file in files:
            if 'README' in file: continue
            src_path = os.path.join(root, file)
            src_modified = os.path.getmtime(src_path)
            # always copy public files from packs
            if 'packs' == name and '/public/' in src_path:
              build_path = 'build/out/public/'+file
              build_modified = 0
            else:
              build_path = src_path.replace('src', 'build/out')
              try: build_modified = os.path.getmtime(build_path)
              except Exception as e: build_modified = 0
            if build_modified < src_modified:
              print(src_path, '->', build_path)
              build_dir = build_path.replace(file, '')
              if name != 'src':
                if build_path in potential_conflicts:
                  raise f'pack path conflict: {build_path}'
                else:
                  potential_conflicts.add(build_path)
              os.system(f"""
              mkdir -p {build_dir} && cp -rf {src_path} {build_dir}
              """)
              written.add(build_path)

      packs_path = 'build/out/packs/__init__.py'
      os.makedirs(re.sub(r'/[^/]+$', '', packs_path), exist_ok=True)
      with open(packs_path, 'w') as f: f.write(f'packs = {args.packs}')

      print(f'\nBuilt in {time.time() - start:.2f}s')

      sync_dir = 'build/out'
      if args.minify:
        print('\nMinify out/ -> min/')
        time.sleep(3)
        indent('python3 build/minify.py')
        sync_dir = 'build/min'
      
      # Sync build to board
      class WatchInterrupt(Exception): pass
      try:
        repl_pid = process = None
        if args.sync:
          print(f'\nSyncing to {args.sync}')
          if args.network:
            ssid, key = args.network.split(':', maxsplit=1)
            print('Writing network credentials:', ssid, key)
            with open(f'{sync_dir}/network.json', 'w') as f:
              f.write(json.dumps({ 'ssid': ssid, 'key': key }))
          time.sleep(3)
          result = rshell(f'ls /{args.sync}')
          if 'Cannot access' in result:
            print(f"Couldn't find {args.sync}")
            sys.exit(0)

          rshell(f'rsync {sync_dir} /{args.sync}', 30)
          if args.watch:
            # fork process to open rshell console & watch files at the same time
            process = subprocess.Popen(
              ('rshell', 'repl ~ machine.soft_reset()'),
              stderr=None)
            pid = os.fork()
            if pid: repl_pid = pid
            else:
              process.communicate()
              sys.exit(0)
          else:
            os.system('rshell "repl ~ machine.soft_reset()"')

        if not args.watch: break

        # Watch 'src' and 'packs' for file changes
        print(f'\nWatching for changes')
        print(process and process.pid, repl_pid)
        while True:
          time.sleep(1)
          for walk in [os.walk('src')]:
            for root, dir, files in walk:
              for file in files:
                path = os.path.join(root, file)
                if start < os.path.getmtime(path):
                  print('Update:', path)
                  kill(process.pid)
                  kill(repl_pid)
                  raise WatchInterrupt
      except WatchInterrupt: pass
except KeyboardInterrupt: pass
