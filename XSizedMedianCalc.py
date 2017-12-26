from MedianCalc import MedianCalc
from collections import deque

class XSizedMedianCalc(MedianCalc):
    def __init__(self, time_data, list_of_data, size):
        super(XSizedMedianCalc, self).__init__(time_data, list_of_data)
        self.time_data = deque(time_data)
        self.list_of_data = deque(list_of_data)
        self.size = size

    def add_time(self, time):
        self.time_data.append(time)
        if len(self.time_data) > self.size:
            self.time_data.popleft()

    def add_data(self, data):
        self.list_of_data.append(data)
        self.push_data(data)
        if len(self.list_of_data) > self.size:
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