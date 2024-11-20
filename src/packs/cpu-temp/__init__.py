"""
pico-cpu-temp

simple example of API and HTML display
"""

from machine import ADC

from pico_fi import App
from lib.logging import log
from lib.handle.http import HTTP
from lib.handle.ws import WebSocket

sensor_temp = ADC(4)
def reading_to_celsius(reading):
  return 27 - ((reading * 3.3 / 65535) - 0.706)/0.001721
def reading_to_fahrenheit(reading):
  return reading_to_celsius(reading) * 9/5 + 32

def configure(app: App):

  @app.route('/cpu-temperature')
  def cpu_temperature(req: HTTP.Request, res: HTTP.Response):
    farenheit = reading_to_fahrenheit(sensor_temp.read_u16())
    log.info('CPU temperature reading:', farenheit)
    res.text(f'{farenheit}')
