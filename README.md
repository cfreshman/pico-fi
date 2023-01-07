## pico-fi

A Pico W webserver which supports wireless network login with a captive portal


### Prerequisites

1. A Pico W loaded with [MicroPython](https://www.raspberrypi.com/documentation/microcontrollers/micropython.html#drag-and-drop-micropython)
1. [rshell](https://github.com/dhylands/rshell)

### Install

1. Open your Unix shell
1. Download pico-fi
   ```
   git clone https://github.com/cfreshman/pico-fi; cd pico-fi
   ```
1. Connect to the board & copy files
   ```
   rshell
   ```
   ```
   rsync . /pyboard; repl
   ```
1. Soft-reboot with `CTRL+D`

You should see a new `w-pico` wireless network appear (password: `pico1234`). Connect to this network with your computer or smartphone.

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
