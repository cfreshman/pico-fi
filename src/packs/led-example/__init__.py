"""
Toggle the on-board LED
$ python3 build -a led-example
"""
from lib.logging import log
from pico_fi import App
from lib.handle.http import HTTP
from lib.handle.ws import WebSocket
from machine import Pin

def configure(app: App):
  # Runs after app is initialized
  log.info('LED configure')

  # (on-board LED will be on if started successfully)
  led = Pin('LED', Pin.OUT)
  @app.started
  def started(): led.on() 

  # Wait for the login screen to appear
  # Once logged in, you'll see a button to toggle the LED
  @app.route('/led')
  def toggle_led(req, res): led.toggle()
