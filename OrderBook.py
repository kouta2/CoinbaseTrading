import gdax

class OrderBook(object):

    def __init__(self, product):
        self.order_book = gdax.OrderBook(product_id=product)
        self.order_book.start()

    def get_book(self):
        return self.order_book.get_current_book()

    def close_book(self):
        self.order_book.close()
