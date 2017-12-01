# TODO: this thing can totally live outside of gdax


from   bintrees import RBTree
from   decimal import Decimal


class Order(object):
    # TODO: add timestamp?
    def __init__(self, id, side, price, size):
        self.id    = id
        self.side  = side
        self.price = Decimal(price)
        self.size  = Decimal(size)


    # TODO: decouple gdax-specific logic
    @classmethod
    def from_message(cls, order_dict):
        return cls(
            id    = order_dict.get('order_id') or order_dict['id'],
            side  = order_dict['side'],
            price = order_dict['price'],
            size  = order_dict.get('size') or order_dict['remaining_size']
        )


class OrderdBookL2(object):
    def __init__(self):
        self._orders = {}
        self._ask_sizes = RBTree()
        self._bid_sizes = RBTree()


    def _update_size(self, side, price, delta):
        sizes = self._ask_sizes if side == 'ask' else self._bid_sizes
        new_size = sizes.get(price, default=0) + delta
        if new_size < 0:
            raise ValueError()  # Make BookError
        if new_size == 0:
            try:
                sizes.remove(price)
            except KeyError:
                # TODO: is this ever going to happen? log something
                pass
        else:
            sizes.insert(price, new_size)


    def update_order(self, order):
        order = self._orders.get(order.id)
        old_size = 0 if order is None else order.size
        self._orders[order.id] = order
        if order.size == 0:
            del self._orders[order.id]
        delta = order.size - old_size
        self._update_size(order.side, order.price, delta)


    def remove_order(self, id):
        order = self._orders.get(id)
        if order is None:
            raise ValueError()  # TODO: BookError
        else:
            self._update_size(order.side, order.price, -order.size)


    def get_order(self, id):
        return self._order.get(id)


    def best_bids(self, cnt):
        return self._bid_sizes.nlargest(cnt)


    def best_asks(self, cnt):
        return self._ask_sizes.nsmallest(cnt)


    def best_bid(self):
        return self._bid_sizes.max_item()


    def best_ask(self):
        return self._ask_sizes.min_item()
