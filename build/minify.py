"""
Minify build/ to min/
1. (Broken - too much memory) Concatenate lib/ scripts into one minified file
2. Update imports & minify other python scripts
3. Minify html/js/css files
4. Copy everything else (TODO other compression methods)
5. If __main__, sync to Pico

Prerequisites:
pip3 install python_minifier
npm install -g html-minifier
"""
import os, re, json
try: import python_minifier
except: python_minifier = None


def minify():
  print('\nRun python/html/js/css minifier')
  _formatBuildFile = lambda x: x.replace('build/out', '')

  lib_scripts = set()
  script_paths = []
  for root, dir, files in os.walk('build/out'):
    for file in files:
      match = re.search(r'\.py$', file)
      if match:
        path = os.path.join(root, file)
        script_paths.append(path)
  
  if lib_scripts:
    print('\nConcatenate:')
    [print(_formatBuildFile(x)) for x in sorted(lib_scripts)]
    print('\nUpdate imports:')
    [print(_formatBuildFile(x)) for x in sorted(script_paths) if x not in lib_scripts]

  """
  Read files & order according to imports
  e.g. if A imports B, C imports A, order as B C A
  """
  user_modules = {}
  script_contents = {}
  dep_tree = {}
  _parse_first_regex_group = lambda x: x.group(1) if x else None
  for path in script_paths:
    with open(path, 'r') as f:
      lines = []
      deps = set()
      for line in f.readlines():
        module = _parse_first_regex_group(re.search(r'from (\S+)', line))
        if not module:
          module = _parse_first_regex_group(re.search(r'import (\S+)', line))

        if module and module not in user_modules:
          file = 'build/out/' + module.replace('.', '/') + '.py'
          if not os.path.exists(file):
            file = file.replace('.py', '/__init__.py')
          if os.path.exists(file): user_modules[module] = file
          else: module = False

        if module in user_modules:
          if path in lib_scripts: deps.add(user_modules[module])
          # else: lines.append(re.sub(module, 'pico_fi', line))
          # TODO better way of replacing non-concatenated imports
          # Non-urgent since concatenated file is too large
          else: lines.append(line)
        else: lines.append(line)

      script_contents[path] = lines
      if path in lib_scripts: dep_tree[path] = list(deps)

  if dep_tree:
    print()
    [print(
      _formatBuildFile(k),
      [_formatBuildFile(x) for x in v])
      for k,v in sorted(dep_tree.items(), key=lambda x: len(x[1]))]
    
    # Start with pool of files without dependencies
    # Remove added files from remaining
    # Adding once deps == 0
    order = []
    import time
    print('\nFlattening dependencies')
    while dep_tree:
      added = set()
      for file,deps in dep_tree.items():
        if not deps:
          order.append(file)
          added.add(file)
      for file in added:
        del dep_tree[file]
      for file in dep_tree.keys():
        dep_tree[file] = [x for x in dep_tree[file] if x not in added]
      time.sleep(1)

    print('\nOrder:')
    [print(_formatBuildFile(x)) for x in order]

    # Concat into one file (without imports) and sync /public non-script artifacts
    print('\nConcat, minify:')
    compiled = '\n\n\n'.join(''.join(script_contents[x]) for x in order)
    os.makedirs('min/public', exist_ok=True)
    with open('min/pico_fi.py', 'w') as f:
      compiled = python_minifier.minify(compiled)
      f.write(compiled)


  # Replace import references across lib/main.py and lib/packs/ with pico_fi
  # and minify
  print('\nMinify python?', bool(python_minifier))
  if not python_minifier:
    print('To support minification of python files: "pip3 install python_minifier"')
  unminified = { 'bootsel.py', }
  for src_path in [x for x in script_paths if x not in lib_scripts]:
    contents = ''.join(script_contents[src_path])
    if python_minifier and not src_path.split('/')[-1] in unminified:
      print(_formatBuildFile(src_path))
      contents = python_minifier.minify(contents)
    min_path = src_path.replace('out', 'min')
    os.makedirs(re.sub(r'/[^/]+$', '', min_path), exist_ok=True)
    with open(min_path, 'w') as f: f.write(contents)

  # Sync & minify public files
  import shutil
  html_minifier_installed = bool(shutil.which('html-minifier'))
  print('\nMinify html/js/css?', html_minifier_installed)
  if not html_minifier_installed:
    print('To support minification of python files: "npm install -g html-minifier"')
  for root, dir, files in os.walk('build/out/public'):
    for file in files:
      src_path = os.path.join(root, file)
      min_path = src_path.replace('out', 'min')
      os.makedirs(re.sub(r'/[^/]+$', '', min_path), exist_ok=True)
      if html_minifier_installed and re.search(r'\.html$', file):
        print(_formatBuildFile(src_path))
        os.system(f"""html-minifier --collapse-boolean-attributes --collapse-whitespace --remove-comments --remove-optional-tags --remove-redundant-attributes --remove-script-type-attributes --remove-tag-whitespace --minify-css true --minify-js true -o {min_path} {src_path}""")
      else:
        os.system(f'cp {src_path} {min_path}')

  print('\nMinification complete\n')

if __name__ == '__main__': 
  minify()
