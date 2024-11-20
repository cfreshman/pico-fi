"""
pico-led-toggle

toggle an LED
"""
from lib.logging import log
from pico_fi import App
from lib import LED
from lib.handle.http import HTTP
from lib.handle.ws import WebSocket
from machine import Pin

"""
SETTINGS
"""
GPIO = None
# set to GP## of component (or list) to use instead of on-board LED, for example:
# GPIO = [4, 8, 12, 19, 26]
""""""

def configure(app: App):
  led = LED(pin=GPIO or ['LED', 17], brightness=.1)
  app.indicator = None

  @app.started
  def started(): led.on()

  @app.route('/led-toggle')
  def toggle_led(req, res): 
    led.toggle()
    log.info('led toggled:', led.get())
  
  @app.route('/led-brightness')
  def set_led_brightness(req, res):
    brightness = float(req.query['x'])
    led.on(brightness)
    log.info('led brightness set:', brightness)
