"""
simple global persistent state
"""

import json

from lib.logging import log


# global state object
store = {}
class Store:
    store=store
    def read(data: dict, store=store):
        # read data keys out of store
        for k in data:
            if k in store:
                v = store[k]
                if type(v) is dict and type(data[k]) is dict:
                    Store.read(data[k], v)
                else:
                    data[k] = v
        return data
    def get(key: str, default=None):
        log.info(key, json.dumps(store))
        return Store.read({ key: default })[key]

    def write(data: dict, store=store):
        # write data values onto store
        # prevent changes to specificity (swapping b/n dict & non-dict values)
        for k, v in data.items():
            write_dict = type(v) is dict
            has_k = k in store
            is_dict = has_k and type(store[k]) is dict
            if write_dict and is_dict: Store.write(v, store[k])
            elif has_k and not (v is None or store[k] is None) and is_dict != write_dict: pass
            else: store[k] = v
            log.debug('store write', k, v, k in store and store[k])

    def save():
        f = open('store.json', 'w')
        f.write(json.dumps(store))
        log.debug('saved store', store)
    def load():
        try:
            f = open('store.json', 'r')
        except Exception as e:
            # log.exception(e, 'unable to load store\n(for first-time set up, touch store.json)')
            # sys.exit(1)
            f = open('store.json', 'x')
            f.write('')

        Store.write(json.loads(f.read() or json.dumps({})))
        log.debug('loaded store', store)
