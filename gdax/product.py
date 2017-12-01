"""
Wait, maybe this is not useful if we use Decimal everywhere...
"""

from   collections import namedtuple
from   decimal import Decimal

ProductInfo = namedtuple('ProductInfo', ['size_unit', 'price_unit'])

BTC_USD = ProductInfo(Decimal('0.00000001'), Decimal('0.01'))
ETH_USD = ProductInfo(Decimal('0.00000001'), Decimal('0.01'))
ETH_BTC = ProductInfo(Decimal('0.00000001'), Decimal('0.00001'))

ID_TO_INFO = {
    "BTC-USD" : BTC_USD,
    "ETH-USD" : ETH_USD,
    "ETH-BTC" : ETH_BTC,
}

def get_info(product_id):
    try:
        return ID_TO_INFO[product_id]
    except KeyError:
        raise ValueError("Unknown product_id {}".format(product_id))
