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

  module_options = os.listdir('src/packs')
  default_board_name = 'w-pico'
  def kill(pid):
    if pid:
      os.kill(pid, signal.SIGINT)
      time.sleep(.1)
      os.system(f'kill -9 {pid}')
  def rshell(command, seconds=5, no_output=False):
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
          elif no_output: return None
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
  parser.add_argument('-s', '--sync', action='store_true',
    help="sync build to Pico and restart")
  parser.add_argument('-b', '--board', action='store',
    help="specify Pico board for sync if more than one connected")
  parser.add_argument('-c', '--clean', action='store_true',
    help="WARNING - may result in data loss: clear extra on-board files")
  parser.add_argument('-a', '--auto', action='store_true', 
    help="same as --watch --minify --sync")
  parser.add_argument('-v', '--verbose', action='store_true', 
    help="show additional output (rshell commands)")
  parser.add_argument('-n', '--network',
    help='wireless network as name:password')
  parser.add_argument('--no-wait', action='store_true',
    help='skip waits between commands')
  parser.add_argument('-M', '--no-minify', action='store_true',
    help="skip minification for --auto builds (to preserve line numbers)")
  parser.add_argument('PACKS', nargs='*')

  args = parser.parse_args()
  packs = []
  for pack in (args.packs or []) + (args.PACKS or []):
    packs.extend(pack.split(','))
  args.packs = packs
  if args.auto:
    args.watch = args.minify = True
    if not args.sync: args.sync = True
    if args.no_minify: args.minify = False
  if args.sync:
    # Check for board mounted with BOOTSEL
    rpi_mount_dir = os.popen(f"""
    echo $( \\
      [ $(uname) == Darwin ] && echo /Volumes || echo /media/$USER \\
    )/RPI-RP2
    """).readline().strip()
    def _mounted():
      return 'y' in os.popen(
        f"[ -d {rpi_mount_dir} ] && echo y || echo ''").read().strip()
    if _mounted():
      print(f"Found uninitialized Pico at {rpi_mount_dir}")
      mp_response = input(
        "Install MicroPython for Pico W? [Y/n] ") or 'y'
      if mp_response.lower()[0] == 'y':
        wait_from = time.time()
        os.system(f"""
        curl http://micropython.org/download/rp2-pico-w/rp2-pico-w-latest.uf2 > {rpi_mount_dir}/m.uf2
        """)
        print(
          'MicroPython installed, waiting for Pico to disconnect and restart')
        for i in range(10): time.sleep(1)

    # Verify rshell is installed
    if not os.popen('which rshell').read().strip():
      rshell_response = input(
        "Unable to find rshell, install it now? [Y/n] ") or 'y'
      if rshell_response.lower()[0] == 'y': os.system("pip3 install rshell")

    def _read_boards():
      result = rshell('boards') or ''
      return [x.split(' @ ')[0] for x in result.split('\n') if '@' in x]
    board_names = _read_boards()
    print('Connected boards:', ''.join(board_names) or None)
    if not board_names:
      print(f"Retrying in 10s")
      time.sleep(10)
      board_names = _read_boards()
      if not board_names:
        print(f"Connect your Pico or run without --sync")
        print(f"If your Pico is already connected, reconnect while holding BOOTSEL and re-run this script to reinstall MicroPython")
        sys.exit(0)
    if args.board: args.sync = args.board
    elif args.sync: args.sync = board_names[0]
    print(board_names, args.sync)

    if args.sync not in board_names:
      print(f"Couldn't find board \"{args.sync}\"")
      sys.exit(0)
  wait = lambda: 0 if args.no_wait else time.sleep(3)
    
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
        wait()
        os.system(f"""
        mkdir -p build/save
        """)
        rshell(f'cp /{args.sync}/board.py build/save/')
        rshell(f'cp /{args.sync}/store.json build/save/')
        rshell(f'cp /{args.sync}/network.json build/save/')
        rshell(f'rm -rf /{args.sync}')
        rshell(f'cp build/save/* /{args.sync}')
        os.system('rm -rf build/sync')

      # Only copy new files & changes to avoid excessive rsync
      # Copy src/* to out/
      # Copy src/packs/<name>/* to out/packs
      # Copy src/packs/<name>/public/* to out/public
      # Write module list to out/packs/__init__.py
      potential_conflicts = set()
      index_compilation = []
      for (pack, name, walk) in [
        (None, 'src', os.walk('src')),
        *((x, 'packs', os.walk(f'src/packs/{x}')) for x in args.packs or [])]:
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
            build_dir = build_path.replace(file, '')
            index_page = pack and build_path == 'build/out/public/index.html'
            if index_page: index_compilation.append([pack, src_path])
            if build_modified < src_modified:
              print(src_path, '->', build_path)
              if name != 'src' and not index_page:
                if build_path in potential_conflicts:
                  raise Exception(f'pack path conflict: {build_path}')
                else:
                  potential_conflicts.add(build_path)
              os.system(f"""
              mkdir -p {build_dir} && cp -rf {src_path} {build_dir}
              """)
      
      if len(index_compilation) > 1:
        print('\nGenerating compiled index for multiple packs')
        # Compile index page for multiple packs
        # Copy packs as public/<pack name>.html (to preserve relative links)
        build_dir = 'build/out/public/'
        os.system(f"""
        mkdir -p {build_dir}
        """)
        links = []
        for (pack, src_path) in index_compilation:
          file_name = f'./{pack}.html'
          links.append([pack, file_name])
          os.system(f"""
          cp -rf {src_path} {build_dir}{file_name}
          """)
        links_html = '\n'.join(
          f'<a href="{href}">{pack}</a>' for (pack, href) in links)
        html_root = """
        <div>[ installed packs ]</div>
        <br/>
        <div style="
        display: flex;
        flex-direction: column;
        ">
          %s
        </div>
        <style>
        #root a {
          padding: 0.5em;
          margin-bottom: 0.5em;
          font-size: 1.2em;
          background: #ff8686;
          border-radius: 2px;
          color: black;
          border: 0.1em solid black;
          text-decoration: none;
          text-align: left;
          display: flex;
          justify-content: space-between;
        }
        #root a::after {
          content: " →";
          margin-left: 1em;
          transition: .1s;
          pointer-events: none;
        }
        #root a:hover::after {
          translate: 2em 0;
          color: black;
          transition: .33s;
        }
        </style>
        """ % (links_html)
        
        html = None
        with open('build/empty.html') as f: html = f.read()
        if html:
          html = html.replace('%ROOT%', html_root)
          with open('build/out/public/index.html', 'w') as f: f.write(html)

      packs_path = 'build/out/packs/__init__.py'
      os.makedirs(re.sub(r'/[^/]+$', '', packs_path), exist_ok=True)
      with open(packs_path, 'w') as f: f.write(f'packs = {args.packs}')

      print(f'\nBuilt in {time.time() - start:.2f}s')

      sync_dir = 'build/out'
      if args.minify:
        print('\nMinify out/ -> min/')
        wait()
        indent('python3 build/minify.py')
        sync_dir = 'build/min'
      
      # Sync build to board
      class WatchInterrupt(Exception): pass
      try:
        repl_pid = process = None
        if args.sync:
          print(f'\nSyncing to {args.sync}')
          result = rshell(f'ls /{args.sync}')
          if 'Cannot access' in result:
            print(f"Couldn't find {args.sync}")
            sys.exit(0)
          wait()

          if args.network:
            ssid, key = args.network.split(':', maxsplit=1)
            print('Writing network credentials:', ssid, key)
            with open(f'{sync_dir}/network.json', 'w') as f:
              f.write(json.dumps({ 'ssid': ssid, 'key': key }))
          
          # Only sync changed files
          os.system(f'mkdir -p build/sync')
          diff_output = os.popen(f'diff -qr {sync_dir} build/sync').read()
          updated = []
          restart = True # False
          for line in diff_output.split('\n'):
            # parse file names after 'Only in' or 'Files'
            filepath = None
            if f'Only in {sync_dir}' in line:
              # Only in <dir>: <name>
              [only, name] = line.split(': ')
              dir = only.split(' ')[-1]
              filepath = os.path.join(dir, name)
            if 'Files' in line and 'differ' in line:
              # Files <from> and <to> differ
              filepath = line.replace('Files ', '').split(' ')[0]

            if filepath:
              updated.append(filepath)
              # only restart if files outside public/ changed
              if not 'public/' in filepath: restart = True
          print('Updated files:\n' + '\n'.join(updated or ['(none)']))
          for filepath in updated:
            sync_filepath = filepath.replace(sync_dir, 'build/sync')
            sync_filedir = re.sub(r'/[^/]*$', '', sync_filepath)
            os.system(f"""
            mkdir -p {sync_filedir}
            cp -rf {filepath} {sync_filepath}
            """)

          rshell(f'rsync build/sync /{args.sync}', 60)

          print('\nRestarting device')
          # if restart: 
          #   try: rshell('repl ~ machine.reset() ~', 1, True)
          #   except: pass # expected
          # time.sleep(5)
          process = subprocess.Popen(
            ('rshell', 'repl ~ machine.soft_reset()' if restart else 'repl'),
            stderr=None)
          if args.watch:
            # fork process to open rshell console & watch files at the same time
            repl_pid = os.fork()
          if not repl_pid: process.communicate()
        if not repl_pid: sys.exit(0)

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
