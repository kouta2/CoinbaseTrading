

class PositionHandler:

    def __init__(self, product, account_details, orders):
        self.position = 0 # the amount of cryptocurrency we have
        self.soft_position = 0 # the amount of cryptocurrency we have assuming all orders are fulfilled
        self.cash = 0 # the amount of cash we have available
        self.soft_cash = 0 # the amount of cash we have assuming all orders are fulfilled
        for account in account_details:
            if account['currency'] == 'USD':
                self.cash = float(account['available'])
            else:
                self.position = float(account['available'])

        self.soft_position = self.position
        self.soft_cash = self.cash
        for page_of_orders in orders:
            for order in page_of_orders:
                if order['side'] == 'buy':
                    size = float(order['size'])
                    self.soft_position += size
                    self.soft_cash -= float(order['price']) * size

    def get_position(self):
        return self.position

    def get_soft_position(self):
        return self.soft_position

    def get_cash(self):
        return self.cash

    def get_soft_cash(self):
        return self.soft_cash

    def update_position(self, order):
        size = order.get_volume()
        price = order.get_price()
        if order.get_is_completed() == True:
            if order.get_side() == 'bid':
                self.position += size
                self.cash -= size * price
            else:
                self.position -= size
                self.cash += size * price
        else:
            if order.get_side() == 'bid':
                self.soft_position += size
                self.soft_cash -= size * price
            else:
                self.soft_position -= size
                self.soft_cash += size * price
