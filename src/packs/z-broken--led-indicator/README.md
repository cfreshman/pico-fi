## pico-led-indicator

Sync an LED (or other component) to an endpoint. Press BOOTSEL to turn off

For example, as a physical notification system or daily reminder


### Setup

### Setup
1. Install [pico-fi](/README.md#install)
1. Build with **led-indicator** enabled
   ```
   python3 build -a led-indicator
   ```
1. (Optional) Connect an LED between GP17 and GND  
1. Go to [switches.freshman.dev](https://switches.freshman.dev) and turn on `default/default`  
1. If the LED doesn't turn on but you can see new messages in the console, trying flipping the LED
1. If the LED does turn on:
   - Press BOOTSEL to turn it off
   - Confirm `default/default` updates after a few seconds
   - [Edit the endpoint](./__init__.py#L25)
