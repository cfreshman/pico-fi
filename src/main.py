import pico_fi


pico_fi.run(id='w-pico', password='pico1234', indicator='LED')
# You should see wireless network 'w-pico' appear
# Log in with the above password
# The on-board LED will visualize network activity
# Optional: connect an external LED (set indicator to GPIO #)



"""
Example with randomized network name (w-pico-#######) and custom routes
"""
# from machine import Pin
# import pico_fi
# from lib.handle.http import HTTP


# led = Pin('LED', Pin.OUT)
# app = pico_fi.App(id=7, password='pico1234')

# @app.route('/led')
# def toggle_led(req: HTTP.Request, res: HTTP.Response):
#   led.toggle()

# @app.route('/')
# def index(req: HTTP.Request, res: HTTP.Response): res.html("""
# <button
# onclick="fetch(`/led`)"
# style="width:100%;height:100%;font-size:10vw;cursor:pointer"
# >TOGGLE</button>""")

# led.on() # turn on LED if app was initialized successfully
# app.run() # listen for requests
