import pico_fi


pico_fi.run(id='w-pico', password='pico1234', indicator=17)


"""
Example with a randomized SSID (w-#######) and additional APIs
"""

# from machine import Pin, PWM
# from z_lib import LED
# from z_handle_http import HTTP

# _led = LED(Pin(17, Pin.OUT), 5)
# _led.on()

# app = pico_fi.App(password='pico-fi')

# @app.route('/led')
# def led(req: HTTP.Request, res: HTTP.Response):
#   _led.toggle()
#   res.ok()

# app.run()

