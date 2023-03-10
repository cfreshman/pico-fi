## pico-remote-repl

Run MicroPython commands on your Pico W, wirelessly

![](https://freshman.dev/api/file/public-pico-remote-repl.png)

### Setup
1. Install [pico-fi](/README.md#install)
1. Build with **remote-repl** enabled
   ```
   python3 build -a --packs remote-repl
   ```
1. Once you've connected the Pico W to a network, access the remote repl through the Pico's web address

### Examples

pico-fi's `app` is exposed as a global variable within the REPL:
```
# Disable pico-fi's on-board LED indicator to use for something else
app.indicator = None

# Add a route
@app.route('/led')
def toggle(req, res):
   from machine import Pin
   led = Pin('LED', Pin.OUT)
   led.value(1 - led.value())
   res.text(f'LED: {led.value()}')
```
---
`lib` includes some useful utilities:
```
# Wait for BOOTSEL press

import time
from lib.bootsel import pressed

while True:
  if pressed(): break
  time.sleep(.1)

print('BOOTSEL pressed')
```
---
```
# Get external IP (can be accessed if internal IP is port-forwarded)

app.indicator = None
@app.route('/led')
def toggle(req, res):
  from machine import Pin
  led = Pin('LED', Pin.OUT)
  led.value(1 - led.value())

import urequests
print('internal:', app.sta.ifconfig()[0] + '/led')
print('external:', urequests.request('GET', 'https://ident.me').text + '/led')
```
---
```
# Random pokemon

import urequests
p = urequests.request(
  'GET', 
  'https://api.pikaserve.xyz/pokemon/random'
  ).json()
print(
  p['name']['english']+':',
  p['species'])
print(p['description'])
```
