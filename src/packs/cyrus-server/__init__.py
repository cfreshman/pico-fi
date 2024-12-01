"""
pico-cyrus-server

companion to freshman.dev
"""
from lib.logging import log
from pico_fi import App
from lib import LED

"""
SETTINGS
"""
GPIO = None
# set to GP## of component (or list) to use instead of on-board LED, for example:
GPIO = ['LED', 16, 12, 19, 8, 26, 4]
""""""

def configure(app: App):
  power = True
  app.indicator = None
  leds = [LED(pin=pin, brightness=1) for pin in GPIO]

  @app.connected
  def connected():
    for led in leds: led.on()

  @app.route('/online')
  def set_online(req, res):
    online = int(req.query['x'])
    log.info('set online LEDs:', online)
    for i in range(len(leds)):
      if i < online: leds[i].on()
      else: leds[i].off()
    res.ok()

  @app.route('/led-toggle')
  def toggle_power(req, res):
    nonlocal power
    power = not power
    for led in leds:
      if power: led.on()
      else: led.off()
    log.info('toggled LEDs:', power)
    res.ok()
  
  @app.route('/led-brightness')
  def set_brightness(req, res):
    brightness = float(req.query['x'])
    for led in leds: led.set(brightness)
    log.info('set LED brightness:', brightness)
    res.ok()
