
class Order:
    def __init__(self, price, volume, id, side, is_completed):
        self.price = price
        self.volume = volume
        self.id = id
        self.side = side
        self.is_completed = is_completed

    def get_price(self):
        return self.price

    def get_volume(self):
        return self.volume

    def get_id(self):
        return self.id

    def get_side(self):
        return self.side

    def get_is_completed(self):
        return self.is_completed

    def set_is_completed(self, is_complete):
        self.is_completed = is_complete