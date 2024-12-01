"""
pico-led-6

turn on 6 LEDs
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

  @app.started
  def started():
    for led in leds: led.on()

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
