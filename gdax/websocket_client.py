# gdax/WebsocketClient.py
# original author: Daniel Paquin
# mongo "support" added by Drew Rice
#
#
# Template object to receive messages from the gdax Websocket Feed

from __future__ import print_function
import json
import base64
import hmac
import hashlib
import time
from threading import Thread
from websocket import create_connection, WebSocketConnectionClosedException
from pymongo import MongoClient
from gdax.gdax_auth import get_auth_headers
from datetime import datetime


class WebsocketClient(object):
    def __init__(self, url="wss://ws-feed.gdax.com", products=["BTC-USD"], message_type="subscribe", mongo_collection=None,
                 should_print=True, auth=False, api_key="", api_secret="", api_passphrase="", channels=None,
                 persistent_connection=True):
        self.url = url.rstrip("/")
        self.products = products if isinstance(products, list) else [products]  # FIXME: iterables
        self.channels = channels
        self.type = message_type
        self._client_should_continue = False   # for the entire client, which may have multiple connection sessions
        self._session_should_continue = False  # for the current connection session
        self.error = None
        self.ws = None
        self.thread = None
        self.auth = auth
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_passphrase = api_passphrase
        self.should_print = should_print  # TODO: change this to `logging`
        self.mongo_collection = mongo_collection
        self.persistent_connection = persistent_connection

    def is_closed(self):
        """
        Whether the entire WebsocketClient is closed.

        Note that it is possible for the connection to be down while the client is still
        considered "open" because it is doing retries for persistent connection.
        """
        return not self._client_should_continue

    def end_session_signal(self):
        """
        We always signal the worker thread to stop listening, and then
        wait for the rest of closing procedure to be handled by the
        worker itself.
        """
        self._session_should_continue = False

    def end_client_signal(self):
        self._client_should_continue = False

    def start(self):
        # TODO: make context manager
        def _one_session():
            try:
                self._session_should_continue = True
                self._connect()
                self._listen()
            finally:
                self._disconnect()

        def _go():
            try:
                self.on_open()
                _one_session()
                while self.persistent_connection and self._client_should_continue:
                    _one_session()
            finally:
                self.on_close()

        self._client_should_continue = True
        self.thread = Thread(target=_go)
        self.thread.start()

    def _connect(self):
        if self.channels is None:
            sub_params = {'type': 'subscribe', 'product_ids': self.products}
        else:
            sub_params = {'type': 'subscribe', 'product_ids': self.products, 'channels': self.channels}

        if self.auth:
            timestamp = str(time.time())
            message = timestamp + 'GET' + '/users/self'
            sub_params.update(get_auth_headers(timestamp, message, self.api_key,  self.api_secret, self.api_passphrase))

        self.ws = create_connection(self.url)
        self.ws.send(json.dumps(sub_params))

        if self.type == "heartbeat":
            sub_params = {"type": "heartbeat", "on": True}
        else:
            sub_params = {"type": "heartbeat", "on": False}
        self.ws.send(json.dumps(sub_params))

        self.on_connection()

    def _listen(self):
        while self._client_should_continue and self._session_should_continue:
            try:
                if int(time.time() % 30) == 0:
                    # Set a 30 second ping to keep connection alive
                    self.ws.ping("keepalive")
                data = self.ws.recv()

                try:
                    msg = json.loads(data)
                except ValueError as e:
                    self.on_error(e, data)
                else:
                    self.on_message(msg)
            except Exception as e:
                self.on_error(e)

    def _disconnect(self):
        if self.type == "heartbeat":
            self.ws.send(json.dumps({"type": "heartbeat", "on": False}))
        try:
            if self.ws:
                self.ws.close()
        except WebSocketConnectionClosedException as e:
            pass

        self.on_disconnection()

    def close(self):
        """
        This can only be called from the parent thread.  (e.g. It cannot
        be called from `on_message`, `on_close`.)

        See `end_session_signal`, `end_client_signal` for in-thread calls.
        """
        self.end_client_signal()
        self.end_session_signal()
        self.thread.join()

    def on_connection(self):
        """
        Called on each successful socket connection.
        """
        if self.should_print:
            print("\n-- Socket connected --")

    def on_disconnection(self):
        self._session_should_continue = False  # Just making sure; most likely it is already set
        if self.should_print:
            print("\n-- Socket disconnected at {} --".format(datetime.now()))

    def on_open(self):
        """
        Note that this is on the opening of the entire client.  The connection
        is not established yet at this point.

        See also `on_connection`.
        """
        pass

    def on_close(self):
        """
        On the closing of the entire client.
        """
        self._client_should_continue = False  # Just making sure; most likely it is already set

    def on_message(self, msg):
        if self.mongo_collection:  # dump JSON to given mongo collection
            self.mongo_collection.insert_one(msg)

    def on_error(self, e, data=None):
        self.error = e
        self.end_session_signal()
        print('{!r} - data: {}'.format(e, data))

    def start_and_wait(self):
        """
        Start the client and wait until it exits.
        """
        self.start()
        try:
            while not self.is_closed():
                time.sleep(1)
        except KeyboardInterrupt:
            if self.should_print:
                print("quiting...")
            self.close()


if __name__ == "__main__":
    import sys
    import gdax
    import time


    class MyWebsocketClient(gdax.WebsocketClient):
        def on_open(self):
            self.url = "wss://ws-feed.gdax.com/"
            self.products = ["BTC-USD", "ETH-USD"]
            self.message_count = 0
            print("Let's count the messages!")

        def on_message(self, msg):
            if self.should_print:
                print(json.dumps(msg, indent=4, sort_keys=True))
            self.message_count += 1

        def on_close(self):
            print("-- Goodbye! --")


    wsClient = MyWebsocketClient()
    wsClient.start()
    print(wsClient.url, wsClient.products)
    try:
        while True:
            print("\nMessageCount =", "%i \n" % wsClient.message_count)
            time.sleep(1)
    except KeyboardInterrupt:
        wsClient.close()

    if wsClient.error:
        sys.exit(1)
    else:
        sys.exit(0)
