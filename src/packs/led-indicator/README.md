## pico-led-indicator

Sync an LED (or other component) to an endpoint. Press BOOTSEL to turn off  

For example, use as a physical notification system or daily reminder 

https://user-images.githubusercontent.com/19336643/222288358-0db43417-c58f-401e-b42d-7beaf3b18e99.mov



### Setup

1. Build [pico-fi](../../../README.md) with led-indicator enabled:  
   Hold BOOTSEL, plug in Pico,
   ```
   curl http://micropython.org/download/rp2-pico-w/rp2-pico-w-latest.uf2 > $([ $(uname) == Darwin ] && echo /Volumes || echo /media/$USER)/RPI-RP2/m.uf2
   pip3 install rshell
   git clone https://github.com/cfreshman/pico-fi
   cd pico-fi && python3 build -a --packs led-indicator
   ```
1. (Optional) Connect an LED between GP17 and GND  
1. Go to [switches.freshman.dev](https://switches.freshman.dev) and turn on `default/default`  
1. If the LED doesn't turn on but you can see new messages in the console, trying flipping the LED
1. If the LED does turn on:
   - Press BOOTSEL to turn it off
   - Confirm `default/default` updates after a few seconds
   - [Edit the endpoint](./__init__.py#L25)
