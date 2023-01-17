## pico-fi

A MicroPython webserver framework for the Pico W with a captive portal for wireless network login

For example, toggle the on-board LED wirelessly:
```python
from machine import Pin
import pico_fi


led = Pin('LED', Pin.OUT)
app = pico_fi.App(id='w-pico', password='pico1234')

@app.route('/led')
def toggle_led(req, res): led.toggle()

@app.route('/')
def index(req, res): res.html("""
<button
onclick="fetch(`/led`)"
style="width:100%;height:100%;font-size:10vw;cursor:pointer"
>TOGGLE</button>""")

led.on() # turn on LED if app was initialized successfully
app.run() # listen for requests
```

`750KB` supported app weight (`2MB` Pico W flash storage - MicroPython (`1.15MB`) - pico-fi (`< 100KB`))

### Features
1. A captive portal which connects the Pico to a wireless network
1. A single HTML page to serve from the Pico by default
1. DNS, HTTP, and WebSocket handlers for incoming requests
1. Persisted global state with get & set API routes
1. User-defined routes

### Prerequisites

1. A Pico W loaded with [MicroPython](https://www.raspberrypi.com/documentation/microcontrollers/micropython.html#drag-and-drop-micropython)
1. [rshell](https://github.com/dhylands/rshell)

### Install

1. Open your Unix shell
1. Download pico-fi
   ```
   git clone https://github.com/cfreshman/pico-fi; cd pico-fi/src
   ```
1. Connect to the board & copy files
   ```
   rshell
   ```
   ```
   rsync . /pyboard; repl
   ```
1. Soft-reboot with `CTRL+D`

You should see a new `w-pico` wireless network appear (password: `pico1234`). Connect to this network with your computer or smartphone. If the portal doesn't open automatically, try opening an arbitrary website.

Notes:
* After setup, the board name (`pyboard`) will be re-assigned to the network ID as specified in main.py (`w-pico` by default) if you restart rshell:  
  `CTRL-X` to exit repl  
  `CTRL-C` to exit rshell  
  ```
  rshell
  ```
  ```
  rsync . /w-pico; repl
  ```
* Edit the SSID/password or add additional routes in `main.py`
* Edit `index.html` to serve a single static site
* If rshell fails to connect (**after** installing MicroPython), try unplugging the Pico to reset
* If the rshell repl connects but something else isn't working, try restarting the Pico:  
  `CTRL-D` within the repl to stop execution
  ```
  import machine
  machine.reset()
  ```
  `CTRL-C` `CTRL-C` to exit repl & rshell
  ```
  rshell
  ```  
  In my experience with iOS, if something goes wrong while trying to connect, this might be necessary to reset the wireless network  
  But try opening the capture portal (`http://192.128.4.1/portal`) in a web browser first
