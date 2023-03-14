"""
pico-cpu-temp

Example with added API *and* HTML display
"""

from machine import ADC

from pico_fi import App
from lib.logging import log
from lib.handle.http import HTTP
from lib.handle.ws import WebSocket

sensor_temp = ADC(4) 
conversion_factor = 3.3 / (65535)

def configure(app: App):

  @app.route('/cpu-temperature')
  def cpu_temperature(req: HTTP.Request, res: HTTP.Response):
    reading = sensor_temp.read_u16() * conversion_factor
    temperature = 27 - (reading - 0.706)/0.001721
    log.info('CPU temperature reading:', temperature)
    res.text(f'{temperature}')
