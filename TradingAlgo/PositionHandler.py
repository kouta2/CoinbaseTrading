from decimal import Decimal

class PositionHandler:

    def __init__(self, product, account_details, orders):
        self.position = 0 # the amount of cryptocurrency I have
        self.soft_position = 0 # the pessimistic amount of cryptocurrency I have
        self.cash = 0 # the amount of cash I have available
        self.soft_cash = 0 # the pessimistic amount of cash I have
        for account in account_details:
            if account['currency'] == 'USD':
                self.cash = Decimal(float(account['available']))
            else:
                self.position = Decimal(float(account['available']))

        self.soft_position = self.position
        self.soft_cash = self.cash
        for page_of_orders in orders:
            for order in page_of_orders:
                if order['side'] == 'buy':
                    size = Decimal(float(order['size']))
                    self.soft_position += size
                    self.soft_cash -= Decimal(float(order['price'])) * size

    def get_position(self):
        return self.position

    def get_soft_position(self):
        return self.soft_position

    def get_cash(self):
        return self.cash

    def get_soft_cash(self):
        return self.soft_cash

    def restore_soft_info(self, order):
        if order.get_is_completed() == False:
            if order.get_side() == 'buy':
                self.soft_cash += order.get_price() * order.get_volume()
            else:
                self.soft_position += order.get_volume()

    def update_position(self, order):
        size = order.get_volume()
        price = order.get_price()
        if order.get_is_completed() == True:
            if order.get_side() == 'buy':
                self.position += size
                self.soft_position += size
                self.cash -= size * price
            else:
                self.position -= size
                self.cash += size * price
                self.soft_cash += size * price
        else:
            if order.get_side() == 'buy':
                # self.soft_position += size
                self.soft_cash -= size * price
            else:
                self.soft_position -= size
                # self.soft_cash += size * price
