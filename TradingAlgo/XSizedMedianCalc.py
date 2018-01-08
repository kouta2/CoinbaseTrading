from collections import deque
from decimal import Decimal

from TradingAlgo.MedianCalc import MedianCalc

class XSizedMedianCalc(MedianCalc):
    def __init__(self, time_data, list_of_data, size):
        self.list_of_data = deque([round(Decimal(elem), 2) for elem in list_of_data])
        super(XSizedMedianCalc, self).__init__(time_data, list(self.list_of_data))
        self.time_data = deque(time_data)
        self.SIZE = size

    def add_time(self, time):
        self.time_data.append(time)
        if len(self.time_data) > self.SIZE:
            self.time_data.popleft()

    def add_data(self, data):
        val = round(Decimal(data), 2)
        self.list_of_data.append(val)
        self.push_data(val)
        if len(self.list_of_data) > self.SIZE:
            self.remove_data_from_heap(self.list_of_data.popleft())


if __name__=="__main__":
    m = XSizedMedianCalc([], [], 3)
    m.add_data(4)
    print(m.get_median())

    m.add_data(7)
    print(m.get_median())

    m.add_data(9)
    print(m.get_median())

    m.add_data(9)
    print(m.get_median())

    m.add_data(10)
    print(m.get_median())

    m.add_data(3)
    print(m.get_median())

    m.add_data(5)
    print(m.get_median())