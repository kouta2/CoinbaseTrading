from collections import deque
from functools import reduce

from XSizedMedianCalc import XSizedMedianCalc

class PriceHandler:

    def __init__(self, historic_data):
        self.times, self.prices, self.slopes, self.concavities = PriceHandler.get_prices(historic_data)
        self.HISTORY_DEPTH = len(self.prices)
        self.min_price = min(self.prices)
        self.max_price = max(self.prices)
        self.avg_price = reduce(lambda x, y: x + y, self.prices) / len(self.prices)
        self.median_calc = XSizedMedianCalc(self.times, self.prices, self.HISTORY_DEPTH)

    '''
        given historic data, returns 4 lists:
        1.) the start times of these intervals
        2.) prices which is the average price at every interval of historic data
        3.) the slope of the price with respect to the previous prices
        4.) the concavity of the slope with respect to the previous slope
    '''
    @staticmethod
    def get_prices(historic_data):
        times = deque([])
        prices = deque([])  # keeps track of price at every interval
        slopes = deque([])  # keeps track of slopes of prices
        concavities = deque(
            [])  # keeps track of concavity of slope (used for determining if it is concave up or concave down)
        for historic_chunk in historic_data:
            for data_pt in historic_chunk:
                # averaging the low, high, open and closing prices in the interval
                avg_price = (data_pt[1] + data_pt[2] + data_pt[3] + data_pt[4]) / 4
                times.append(data_pt[0])
                prices.append(avg_price)
                if (len(slopes) == 0):
                    slopes.append(0)
                    concavities.append(0)
                else:
                    slopes.append(prices[-1] - prices[-2])
                    concavities.append(slopes[-1] - slopes[-2])

        return (times, prices, slopes, concavities)

    def update_price_info(self):
        pass

    def get_price_info(self):
        return (self.min_price, self.max_price, self.avg_price, self.median_calc.get_median())

    def get_min_price(self):
        return self.min_price

    def get_max_price(self):
        return self.max_price

    def get_avg_price(self):
        return self.avg_price

    def get_median_price(self):
        return self.median_calc.get_median()
