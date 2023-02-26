## pico-led-indicator

Sync an LED (or other component) to an endpoint. Press BOOTSEL to turn off  

For example, use as a physical notification system or daily reminder 

### Setup

1. Build [pico-fi](../../../README.md) with led-indicator enabled
   ```
   python3 build -a --packs led-indicator
   ```
1. (Optional) Connect an LED between GP17 and GND  
1. Go to [freshman.dev/switches](https://freshman.dev/switches) and turn on `default/default`  
1. If the LED doesn't turn on but you can see new messages in the console, trying flipping the LED
1. If the LED does turn on:
   - Press BOOTSEL to turn it off
   - Confirm `default/default` updates after a few seconds
   - [Edit the endpoint](./__init__.py#L25)
