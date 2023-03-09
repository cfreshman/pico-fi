"""
Main orchestration class
"""
import binascii
import gc
import json
import select
import time
import os

import network
import uasyncio

from lib.handle.dns import DNS
from lib.handle.http import HTTP
from lib.handle.ws import WebSocket
from lib.stream.ws import WS
from lib import encode, randlower, delimit, LED
from lib.logging import cmt, log
from lib.server import Orchestrator, SocketPollHandler, IpSink
from lib.store import Store


class App:
    """
    Pico W access point serving single offline website with persistent get/set API

    This serves as a communication node between clients
    It provides the common site, persistent state, and websockets
    Design the site to offload processing & temporary storage to the client
    """

    IP = '192.168.4.1'

    def __init__(self, id=None, password='', indicator=None):
        self.running = False
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
        self.websocket = None
        self.servers: SocketPollHandler = []
        self.routes = {
            b'/portal': b'/public/portal.html',
            b'/': b'/public/index.html',
            b'/favicon.ico': b'',
            b'/get': self.get,
            b'/set': self.set,
            b'/api': self.api,
        }
        self.events = {
            b'echo': lambda msg: msg.reply(msg.content),
            # can define opcode fallback for non-text or non-match:
            WS.Opcode.TEXT: None,
            WS.Opcode.BINARY: None,
        }

        if indicator and not isinstance(indicator, LED): indicator = LED(indicator, .05)
        self.indicator = indicator or LED.Mock()

        self.effects = { 'start': [], 'connect': [] }

        # load installed packs
        try:
            packs = getattr(__import__('packs'), 'packs')
            log.info('defined packs:', packs)
            for pack in packs:
                try:
                    log.info('import', f'packs/{pack}')
                    pack_import = __import__(f'packs/{pack}')
                    pack_features = {}
                    for feature in ['routes', 'configure']:
                        if hasattr(pack_import, feature):
                            pack_features[feature] = getattr(
                                pack_import, feature)
                    
                    if len(pack_features):
                        log.info('-', *pack_features.keys())
                    if 'routes' in pack_features:
                        self.routes = self.routes | pack_features['routes']
                    if 'events' in pack_features:
                        self.events = self.events | pack_features['events']
                    if 'configure' in pack_features:
                        pack_features['configure'](self)
                except Exception as e:
                    log.error(e)
            log.info('configured routes:', *self.routes.keys())
            log.info('configured events:', *self.events.keys())
        except Exception as e:
            log.exception(e)

    def route(self, path: str or bytes):
        """
        decorator for HTTP requests

        @app.route('/foo')
        def bar(req, res):
            res.text(req.params['baz'])
        """
        if path[0] != '/': path = '/' + path
        def decorator(handler):
            def wrapper(*args, **kwargs):
                handler(*args, **kwargs)
            self.routes[encode(path)] = wrapper
        return decorator

    def event(self, type: str or bytes or WS.Opcode):
        """
        decorator for WebSocket events

        @app.event('foo')
        def bar(msg):
            msg.reply('baz')
        """
        def decorator(handler):
            def wrapper(*args, **kwargs):
                handler(*args, **kwargs)
            self.events[encode(type)] = wrapper
        return decorator

    def started(self, func):
        """
        decorator for start callbacks

        @app.started
        def start():
            print('started')
        """
        self.effects['start'].append(func)
        return func
    
    def connected(self, func):
        """
        decorator for connect callbacks

        @app.connected
        def connect():
            print('connected')
        """
        self.effects['connect'].append(func)
        return func

    def start(self):
        cmt('start pico-fi')
        Store.load()
        self.websocket = WebSocket(self.orch, self.events)
        self.servers = [
            DNS(self.orch, self.ap_ip),
            self.websocket,
            HTTP(self.orch, self.ip_sink, self.routes),
        ]

        # start access point
        # if ID undefined, read previous or generate new
        STORE_ID_KEY = 'id'
        if not self.id or isinstance(self.id, int):
            self.id = Store.get(STORE_ID_KEY, 'w-'+randlower(self.id or 7))
        self.ap.config(essid=self.id)
        open('board.py', 'w').write(f'name = "{self.id}"')
        Store.write({ STORE_ID_KEY: self.id })
        self.ap.active(True)
        self.indicator and self.indicator.on()
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
        
        while self.effects['start']: self.effects['start'].pop(0)()

        # reconnect to last network if one exists
        self.connect()

    def connect(self, ssid=None, key=None, wait=True):
        NETWORK_JSON = 'network.json'
        if not ssid:
            try:
                with open(NETWORK_JSON) as f: network = json.loads(f.read())
                log.info('stored network login:', network)
                ssid = network['ssid']
                key = network['key']
            except:
                log.info('no stored network login')
                return
        else:
            network = { 'ssid': ssid, 'key': key }
            log.info('store network login:', network)
            with open(NETWORK_JSON, 'w') as f: f.write(json.dumps(network))
            
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
            log.info(f'OPEN http://{self.sta_ip} TO ACCESS PICO W')
            while self.effects['connect']: self.effects['connect'].pop(0)()
        else:
            log.info('network connect failed')
            self.sta.active(False)

    def stop(self):
        cmt('stop pico-fi')
        self.indicator and self.indicator.off()
        self.ap.active(False)
        self.sta.active(False)
        for server in self.servers: server.stop()
        Store.save()
        log.flush()
        gc.collect()
        self.running = False


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
        res.json(data)
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
        else: res.send(HTTP.Response.Status.NOT_FOUND)

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
                for callback in self.connectCallbacks: callback()
                self.connectCallbacks = []
            uasyncio.create_task(_off())
        else: res.error('not connected to the internet')
    def api_network_disconnect(self, req: HTTP.Request, data, res: HTTP.Response):
        log.info('network disconnect')
        self.sta.disconnect()
        Store.write({ 'network': None })
        res.ok()


    def run(self):
        if self.running: return
        self.running = True
        self.start()
        try:
            start = time.time()
            while True:
                # gc between socket events or once per minute
                gc.collect()
                for response in self.poller.ipoll(60_000):
                    self.indicator and self.indicator.pulse()
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
