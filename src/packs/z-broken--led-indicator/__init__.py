"""
pico-led-indicator

BROKEN - for some reason the pico is not able to make internet requests

sync an LED (or other component) to the state of an API endpoint
press BOOTSEL to turn off

(you can use this as a physical notification system or daily reminder)
"""

import time, urequests, uasyncio
from pico_fi import App
from lib import LED
from lib.logging import log
from lib.bootsel import pressed


GPIO = OFF_URL = ON_URL = None


"""
CONFIGURATION
"""
GPIO = None # set to GP## of component to use instead of on-board LED

# replace this with your endpoint after testing
SYNC_METHOD = 'GET'
SYNC_URL = 'https://freshman.dev/api/switch/default/default'
def parse_switch_response(response):
  """Parse urequests response to determine LED truthiness"""
  return response.json()['item']['state']

# replace this with an endpoint to request if BOOTSEL pressed while LED on
# OR comment out to disable
OFF_METHOD = 'POST'
OFF_URL = 'https://freshman.dev/api/switch/off/default/default'

# replace this with an endpoint to request if BOOTSEL pressed while LED on
# OR comment out to disable
ON_METHOD = 'POST'
ON_URL = 'https://freshman.dev/api/switch/on/default/default'
"""
END CONFIGURATION
"""

def configure(app: App):
  led = LED(pin=GPIO or ['LED', 17], brightness=.1)
  app.indicator = None

  @app.connected
  def connected():
    if ON_URL:
      log.info('(ON endpoint) attempting to', ON_METHOD, ON_URL)
      try:
        response = urequests.request(ON_METHOD, ON_URL)
        log.info('(ON endpoint) request succeeded')
        response.close()
      except Exception as e:
        log.info('(ON endpoint) request failed')
        log.exception(e)

    state = None
    async def listen():
      nonlocal state
      log.info('inside led-indicator listen')
      # listen for endpoint changes
      try:
        if state is None: log.info('(SYNC endpoint) attempting to', SYNC_METHOD, SYNC_URL)
        response = urequests.request(SYNC_METHOD, SYNC_URL)
        new_state = parse_switch_response(response)
        if state is None: log.info('(SYNC endpoint) request succeeded, value:', new_state)
        if state != new_state:
          led.set(new_state)
          log.info('new LED state:', led.get())
          if led.get(): log.info('press BOOTSEL to turn off')
          state = new_state
        response.close()
      except Exception as e:
        log.info('(SYNC endpoint) request failed')
        log.exception(e)
      
      if led.get():
        # wait for BOOTSEL press 60s
        for i in range(60 * 10):
          if pressed():
            log.info('BOOTSEL pressed')
            led.off()
            log.info('new LED state:', led.get())
            if OFF_URL:
              log.info('(OFF endpoint) attempting to', OFF_METHOD, OFF_URL)
              try:
                response = urequests.request(OFF_METHOD, OFF_URL)
                log.info('(OFF endpoint) request succeeded')
                response.close()
              except Exception as e:
                log.info('(OFF endpoint) request failed')
                log.exception(e)
            log.info('waiting for endpoint change')
            break
          await uasyncio.sleep(.1)
        
        
      """
      Uncomment to use BOOTSEL as ON switch too
      This will add up to 60s of delay to changes from the API endpoint
      """
      # else:
      #   for i in range(60 * 10):
      #     if pressed():
      #       log.info('BOOTSEL pressed')
      #       led.on()
      #       log.info('new LED state:', led.get())
      #       if ON_URL:
      #         log.info('(ON endpoint) attempting to', OFF_METHOD, OFF_URL)
      #         try:
      #           response = urequests.request(OFF_METHOD, OFF_URL)
      #           log.info('(ON endpoint) request succeeded')
      #           response.close()
      #         except Exception as e:
      #           log.info('(ON endpoint) request failed')
      #           log.exception(e)
      #       log.info('waiting for endpoint change')
      #       break
      #     time.sleep(.1)
      
      await uasyncio.sleep(1)
    async def inner():
      await uasyncio.sleep(10)
      while 1:
        uasyncio.run(listen())
    uasyncio.create_task(inner())
