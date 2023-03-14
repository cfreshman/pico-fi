"""
pico-led-indicator

Sync an LED (or other component) to the state of an API endpoint
Press BOOTSEL to turn off

(You can use this as a physical notification system or daily reminder)
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
def parse(response):
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
  app.indicator = LED.Mock()

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

    log.info('(SYNC endpoint) attempting to', SYNC_METHOD, SYNC_URL)
    state = None
    async def listen():
      # listen for endpoint changes
      try:
        response = urequests.request(SYNC_METHOD, SYNC_URL)
        newState = parse(response)
        if state is None: log.info('(SYNC endpoint) request succeeded, value:', newState)
        if state != newState:
          led.set(newState)
          log.info('new LED state:', led.get())
          if led.get(): log.info('press BOOTSEL to turn off')
          state = newState
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
      uasyncio.create_task(listen())
