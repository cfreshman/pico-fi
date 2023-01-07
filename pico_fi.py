"""
Main orchestration class
"""
import binascii
import gc
import json
import select
import time

import network
import machine
import uasyncio

from z_handle_dns import DNS
from z_handle_http import HTTP
from z_handle_ws import WebSocket
from z_lib import encode, randalpha, delimit, LED
from z_logging import cmt, log
from z_server import Orchestrator, SocketPollHandler, IpSink
from z_store import Store


class App:
    """
    Pico W access point serving single offline website with persistent get/set API

    This serves as a communication node between clients
    It provides the common site, persistent state, and websockets
    Design the site to offload processing & temporary storage to the client
    """

    IP = '192.168.4.1'

    def __init__(self, id=None, password='', indicator=None):
        self.id = id
        self.sta_ip = None
        self.sta = network.WLAN(network.STA_IF)
        if self.sta.isconnected(): self.sta.disconnect()
        self.sta.active(False)
        self.ip_sink = IpSink(App.IP)
        self.ap_ip = self.ip_sink.get()
        self.ap = network.WLAN(network.AP_IF)
        if self.ap.isconnected(): self.ap.disconnect()
        self.ap.active(False)
        self.ap.config(password=password)
        if not password: self.ap.config(security=0)
        self.ap.ifconfig(
            # IP address, netmask, gateway, DNS
            (self.ap_ip, '255.255.255.0', self.ap_ip, self.ap_ip)
        )
        self.poller = select.poll()
        self.orch = Orchestrator(self.poller)
        self.servers: SocketPollHandler = []
        self.routes = {
            b'/portal': b'./portal.html',
            b'/': b'./index.html',
            b'/favicon.ico': b'',
            b'/get': self.get,
            b'/set': self.set,
            b'/api': self.api,
            b'/pins': self.pins,
        }

        if indicator and not isinstance(indicator, LED): indicator = LED(indicator, 5)
        self.indicator = indicator or LED.Mock()

    def route(self, path):
        """
        decorator for HTTP requests

        @opp.route('/foo')
        def bar(req, res):
            res.text(req.params['baz'])
        """
        if path[0] != '/': path = '/' + path
        def decorator(handler):
            def wrapper(*args, **kwargs):
                handler(*args, **kwargs)
            self.routes[encode(path)] = wrapper
        return decorator

    def start(self):
        cmt('start pico-fi')
        Store.load()
        self.servers = [
            DNS(self.orch, self.ap_ip),
            WebSocket(self.orch),
            HTTP(self.orch, self.ip_sink, self.routes),
        ]

        # start access point
        # if ID undefined, read previous or generate new
        STORE_ID_KEY = 'id'
        if not self.id: self.id = Store.get(STORE_ID_KEY, 'w-'+randalpha(7))
        self.ap.config(essid=self.id)
        open('board.py', 'w').write(f'name = "{self.id}"')
        Store.write({ STORE_ID_KEY: self.id })
        self.ap.active(True)
        self.indicator.on()
        log.info('access point:', self.ap.config('essid'), self.ap.ifconfig())

        # scan for other networks
        networks = sorted(self.sta.scan(), key=lambda x: -x[3])
        log.info('found', len(networks), 'networks')
        if networks:
            id_len = max(len(x[0]) for x in networks)
            for x in networks:
                ssid_padded = x[0].decode() + ' '*(id_len - len(x[0]))
                bssid = delimit(binascii.hexlify(x[1]).decode(), 2, ':')
                log.info(
                f'{-x[3]} {ssid_padded} ({bssid}) chnl={x[2]} sec={x[4]} hid={x[5]}')
        
        # reconnect to last network if one exists
        self.connect()
    
    def connect(self, ssid=None, key=None, wait=True):
        STORE_NETWORK_KEY = 'network'
        if not ssid:
            network = Store.get(STORE_NETWORK_KEY)
            log.info('stored network login:', network)
            if not network: return
            ssid = network['ssid']
            key = network['key']
            # TODO FIX for some reason, the AP doesn't work when the STA is connected to start

        else:
            log.info('store network login:', { 'ssid': ssid, 'key': key })
            Store.write({ STORE_NETWORK_KEY: { 'ssid': ssid, 'key': key } })
            Store.save()

        self.sta.active(True)
        self.sta.connect(ssid, key)
        if not wait: return

        # wait up to 10s for connection to succeed
        wait = 10
        while wait > 0:
            wait -= 1
            status = self.sta.status()
            log.info(f'network connect attempt status', status)
            if 0 <= status < 3: time.sleep(1)
            else: break

        if status == 3:
            self.sta_ip = self.sta.ifconfig()[0]
            self.ip_sink.set(False)
            log.info(f'network connected with ip', self.sta_ip)
        else:
            log.info('network connect failed')

    def stop(self):
        cmt('stop pico-fi')
        self.indicator.off()
        self.ap.active(False)
        self.sta.active(False)
        for server in self.servers: server.stop()
        Store.save()
        log.flush()
        gc.collect()


    def switch(self, req: HTTP.Request, res: HTTP.Response):
        if self.ip_sink.get(): res.redirect(b'http://{:s}/portal'.format(self.ip_sink.get()))
        else: res.redirect(b'http://{:s}/'.format(App.IP))

    """
    get and set query with single param data=<JSON>
    """
    def _parse_data_from_query(self, query):
        log.debug(query.get('data', '{}'))
        return { 'data': json.loads(query.get('data', '{}')) }

    def get(self, req: HTTP.Request, res: HTTP.Response):
        data = self._parse_data_from_query(req.query)
        log.info('get', data)
        Store.read(data)
        res.json(data)

    def set(self, req: HTTP.Request, res: HTTP.Response):
        data = self._parse_data_from_query(req.query)
        log.info('set', data)
        Store.write(data)
        res.ok()
        log.debug('updated store', Store.store)

    def api(self, req: HTTP.Request, res: HTTP.Response):
        parts = req.path.split(b'/')[2:]
        prefix = parts[0]
        path = b'/'.join(parts)
        data = self._parse_data_from_query(req.query)['data']
        log.info('api', path, data)
        handler = {
            b'networks': self.api_networks,
            b'network-connect': self.api_network_connect,
            b'network-status': self.api_network_status,
            b'network-switch': self.api_network_switch,
            b'network-disconnect': self.api_network_disconnect,
        }.get(prefix, None)
        if handler: handler(req, data, res)
        else: res.send(HTTP.Status.NOT_FOUND)

    def api_networks(self, req: HTTP.Request, data, res: HTTP.Response):
        networks = [{
            'ssid': x[0],
            'pretty_bssid': delimit(binascii.hexlify(x[1]).decode(), 2, ':'),
            'bssid': binascii.hexlify(x[1]).decode(),
            'channel': x[2],
            'RSSI': x[3],
            'security': x[4],
            'hidden': x[5],
        } for x in sorted(self.sta.scan(), key=lambda x: -x[3])]
        res.json(networks)
    def api_network_connect(self, req: HTTP.Request, data, res: HTTP.Response):
        log.info('network connect', data['ssid'], data['key'], binascii.unhexlify(data['bssid']))
        self.connect(data['ssid'], data['key'], False)
        res.json({ 'status': self.sta.status() })
    def api_network_status(self, req: HTTP.Request, data, res: HTTP.Response):
        status = self.sta.status()
        log.info(f'network connect status', status)

        # return IP if connected to wifi
        if status == 3:
            self.sta_ip = self.sta.ifconfig()[0]
            log.info(f'network connected with ip', self.sta_ip)
            res.json({ 'ip': str(self.sta_ip), 'ssid': self.sta.config('ssid') })
        elif status >= 0: res.json({ 'status': status })
        else: res.json({ 'error': 'connection error', 'status': status })
    def api_network_switch(self, req: HTTP.Request, data, res: HTTP.Response):
        log.info('network switch')
        if (self.sta_ip):
            res.ok()
            async def _off():
                time.sleep(1.5)
                self.ip_sink.set(False)
                self.ap.active(False)
            uasyncio.create_task(_off())
        else: res.error('not connected to the internet')
    def api_network_disconnect(self, req: HTTP.Request, data, res: HTTP.Response):
        log.info('network disconnect')
        self.sta.disconnect()
        Store.write({ 'network': None })
        res.ok()


    _pins_template = """<!DOCTYPE html>
    <html>
        <head><title>Pico pins</title></head>
        <body><h1>ESP8266 Pins</h1>
            <table border="1"> <tr><th>Pin</th><th>Value</th></tr> %s </table>
        </body>
    </html>
    """
    _pins = [machine.Pin(i, machine.Pin.IN) for i in (0, 2, 4, 5, 12, 13, 14, 15)]
    def pins(self, req: HTTP.Request, res: HTTP.Response):
        rows = ['<tr><td>%s</td><td>%d</td></tr>' % (str(p), p.value()) for p in App._pins]
        res.ok(App._pins_template % '\n'.join(rows))


    def run(self):
        self.start()
        try:
            start = time.time()
            while True:
                # gc between socket events or once per minute
                gc.collect()
                for response in self.poller.ipoll(60_000):
                    self.indicator.pulse()
                    self.orch.handle(*response)

                # write store to file at most once per minute
                now = time.time()
                if now - start > 60:
                    Store.save()
                    start = now

        except Exception as e:
            log.exception(e)
            self.stop()


def run(id=None, password='', indicator=None):
    app = App(id, password, indicator)
    app.run()
    return app
