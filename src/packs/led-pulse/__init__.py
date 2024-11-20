"""
pico-led-pulse

pulse an LED
"""
import uasyncio, math
from pico_fi import App
from lib import LED
from lib.logging import log

"""
SETTINGS
"""
GPIO = None # set to GP## of component (or list) to use instead of on-board LED
""""""

def configure(app: App):
  led = LED(pin=GPIO or ['LED', 17], brightness=0)
  app.indicator = None

  @app.started
  def started():
    log.info('start LED pulse')
    t = 0.0
    async def pulse():
      nonlocal t
      brightness = math.sin(t / math.tau * 5) / 2 + .5
      led.set(brightness)
      t = t + .1
      # log.info('set LED brightness', t, brightness)
      await uasyncio.sleep(.1)
    async def inner():
      while 1:
        uasyncio.run(pulse())
    uasyncio.create_task(inner())
