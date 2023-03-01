## pico-fi

A MicroPython webserver framework for the Pico W with a captive portal for wireless network login

> **Quickstart** Hold BOOTSEL & plug in Pico W  
> ```sh
> curl http://micropython.org/download/rp2-pico-w/rp2-pico-w-latest.uf2 > $([ $(uname) == Darwin ] && echo /Volumes || echo /media/$USER)/RPI-RP2/m.uf2
> pip3 install rshell
> git clone https://github.com/cfreshman/pico-fi
> cd pico-fi && python3 build -a --packs remote-repl
> ```
> Then connect to `w-pico` (password: `pico1234`)  
> See [packs/remote-repl](./src/packs/remote-repl/) for examples

Network Login | Landing | `--packs remote-repl`
--- | --- | ---
![](https://freshman.dev/api/file/public-pico-fi-portal-1.png) | ![](https://freshman.dev/api/file/public-pico-fi-default-index.png) | ![](https://freshman.dev/api/file/public-pico-remote-repl-mobile.png)

##### For example, toggle the on-board LED:
```python
from machine import Pin
import pico_fi

# Connect to the Pico W's network:
# (on-board LED will be on if started successfully)
app = pico_fi.App(id='w-pico', password='pico1234')
led = Pin('LED', Pin.OUT)
@app.started
def started(): led.on() 

# Wait for the login screen to appear
# Once logged in, you'll see a button to toggle the LED
@app.route('/led')
def toggle_led(req, res): led.toggle()
@app.route('/')
def index(req, res): res.html("""<button onclick="fetch(`/led`)" style="font-size:20vw">TOGGLE</button>""")

app.run()
```

Weighs `76K` - `156K` depending on configuration, supporting minified apps up to `774K`  
(`2000K` Pico W flash storage - MicroPython (`1150K`) - pico-fi (`76K`))


### Features
1. Connect the Pico to internet with your phone
1. Serve HTML from the Pico
1. Handle HTTP, WebSocket, and DNS requests
1. Persist state on the Pico with provided get & set APIs
1. Define new 'packs' for custom routes and behavior:  
   Basic example - [packs/hello-world](./src/packs/hello-world/__init__.py)  
   Sync LED to endpoint - [packs/led-indicator](./src/packs/led-indicator)  
   Web console for your Pico - [packs/remote-repl](./src/packs/remote-repl)  
1. Automatically build, minify, and sync changes to the Pico
   ```
   python3 build --packs hello-world,remote-repl --minify --sync --watch
   ```
   

### Prerequisites

Hardware
1. Pico W
1. USB to Micro USB data cable
1. LED _(optional - defaults to on-board LED)_
> [I've created a starter kit with these items](https://pico-repo/starter)  

Software
1. [MicroPython](https://www.raspberrypi.com/documentation/microcontrollers/micropython.html#drag-and-drop-micropython)
1. [rshell](https://github.com/dhylands/rshell)
> Alternatively, make edits and upload to [pico-repo.com/#how-to](https://pico-repo.com/#how-to) for a drag-n-drop .uf2  
> Then skip to `Connect to the internet`


### Install

1. Connect your Pico *with MicroPython installed*
1. Open your Unix shell *with rshell installed*
1. Download pico-fi & build
   ```
   git clone https://github.com/cfreshman/pico-fi
   cd pico-fi
   python3 build --auto
   ```
   This will automatically start pico-fi on your Pico  
> **See [build](./build/__main__.py) for options** or run `python3 build -h`

### Connect to the internet
You should see a new `w-pico` wireless network appear (password: `pico1234`). Connect to this network with your computer or smartphone. If the portal doesn't open automatically, try opening http://192.128.4.1/portal. **Expect this to take up to a minute** - the Pico is doing its best.

Edit the network name/password or add functionality in [main.py](./src/main.py), HTML in [public/index.html](./src/public/index.html)

### Looking for project ideas?
* A multiplayer chess/checkers app anyone in the area can connect to
* Publish sensor data with MQTT https://www.tomshardware.com/how-to/send-and-receive-data-raspberry-pi-pico-w-mqtt

### Potential upcoming features
- [ ] WebSocket event handlers
  - [ ] remote-repl logs in real-time
- [ ] Internet access through the Pico directly for connected devices (right now, devices have to reconnect to the base wifi network)
- [x] Minification step to support app sizes >750K
- [ ] [Create a new request](https://github.com/cfreshman/cfreshman/issues/new/choose)

### Third-party packs
* (Send me any packs you make and I'll add them here)
