import gdax
import logging
import time

from TradingAlgo.Order import Order

logging.basicConfig(filename='trade.log',level=logging.INFO)

class OrderBook(gdax.OrderBook):

    def on_close(self):
        super().on_close()
        if self.done_using_book == False:
            self.start()
            logging.info('{RECONNECTING_TO_ORDER_BOOK_AFTER_DISCONNECTION}')
        else:
            logging.info('{DISCONNECTED_FROM_ORDER_BOOK}')

    def __init__(self, product):
        super().__init__(product_id=product)
        self.DEPTH_OF_LOCAL_BOOK = 20
        self.asks = []
        self.bids = []
        self.start()
        time.sleep(4) # need to sleep for 4 seconds between API calls
        self.update_book()
        self.done_using_book = False

    def close_book(self):
        self.done_using_book = True
        self.close()

    def update_book(self):
        new_book = self.get_current_book()
        new_asks = new_book['asks']
        self.asks = []
        for i in range(min(len(new_asks), self.DEPTH_OF_LOCAL_BOOK)):
            self.asks.append(Order(new_asks[i][0], new_asks[i][1], new_asks[i][2], 'ask', False))
        new_bids = new_book['bids']
        self.bids = []
        for i in range(max(0, len(new_bids) - 1), max(0, len(new_bids) - 1 - self.DEPTH_OF_LOCAL_BOOK), -1):
            self.bids.append(Order(new_bids[i][0], new_bids[i][1], new_bids[i][2], 'bid', False))
        # logging.info("{UPDATING_BOOK: asks: %s, bids: %s}", [ask.get_price() for ask in self.asks], [bid.get_price() for bid in self.bids])


    def get_sell_orders(self):
        return self.asks

    def get_buy_orders(self):
        return self.bids


if __name__=="__main__":
    o = OrderBook('BTC-USD')
    i = 0
    while True:
        o.update_book()
        print('Asks:\n' + str([order.get_price() for order in o.get_sell_orders()]))
        print('Bids:\n' + str([order.get_price() for order in o.get_buy_orders()]))
        time.sleep(4)
        i += 1
        if i == 3:
            o.close_book()
