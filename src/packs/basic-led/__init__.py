"""
pico-basic-led

toggle the on-board LED
$ python3 build -a basic-led
"""
from lib.logging import log
from pico_fi import App
from machine import Pin

def configure(app: App):
  # runs after app is initialized
  log.info('LED configure')
  app.indicator = None

  # on-board LED will be on if started successfully
  led = Pin('LED', Pin.OUT)
  @app.started
  def started(): led.on() 

  # wait for the login screen to appear
  # once logged in, you'll see a button to toggle the LED
  @app.route('/led')
  def toggle_led(req, res): led.toggle()
