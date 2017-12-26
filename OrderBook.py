import gdax
import time

from Order import Order

class OrderBook(object):

    def __init__(self, product):
        self.DEPTH_OF_LOCAL_BOOK = 20
        self.asks = []
        self.bids = []
        self.order_book = gdax.OrderBook(product_id=product)
        self.order_book.start()
        time.sleep(4) # need to sleep for 4 seconds between API calls
        self.update_book()

    def close_book(self):
        self.order_book.close()

    def update_book(self):
        new_book = self.order_book.get_current_book()
        new_asks = new_book['asks']
        self.asks = []
        for i in range(len(new_asks) - 1, len(new_asks) - self.DEPTH_OF_LOCAL_BOOK, -1):
            self.asks.append(Order(new_asks[i][0], new_asks[i][1], new_asks[i][2], 'ask', False))
        new_bids = new_book['bids']
        for i in range(len(new_bids) - 1, len(new_bids) - self.DEPTH_OF_LOCAL_BOOK, -1):
            self.bids.append(Order(new_bids[i][0], new_bids[i][1], new_bids[i][2], 'bid', False))

    def get_asks(self):
        return self.asks

    def get_bids(self):
        return self.bids
