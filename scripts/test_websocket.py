#!/usr/bin/env python

"""
Demonstrates that the new WebsocketClient and correctly handle Error
in `on_message` and correctly exit.
"""

from gdax import WebsocketClient

import gdax
print gdax

class WebsocketClient4Test(WebsocketClient):
    def on_message(self, msg):
        print(msg)
        raise ValueError("Something is wrong!")

test_ws = WebsocketClient4Test(should_print=True)
test_ws.start()
