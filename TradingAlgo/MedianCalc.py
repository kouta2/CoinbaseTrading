import heapq

class MedianCalc(object):

    def __init__(self, time_data, list_of_data):
        # Default Min Heap
        self.max_heap = [] # has smaller values
        self.min_heap = [] # has largest values
        for elem in list_of_data:
            self.push_data(elem)

    def get_median(self):
        if len(self.max_heap) > len(self.min_heap):
            return self.max_heap[0][1]
        else:
            return round((self.max_heap[0][1] + self.min_heap[0]) / 2, 2)

    def push_data(self, data):
        if len(self.max_heap) > len(self.min_heap):
            heapq.heappush(self.min_heap, (heapq.heappushpop(self.max_heap, (round(-data, 2), data)))[1])
        else:
            val = heapq.heappushpop(self.min_heap, data)
            heapq.heappush(self.max_heap, (round(-val, 2), val))

    def remove_data_from_heap(self, data):
        if data <= self.max_heap[0][1]:
            try:
                self.max_heap.remove((round(-data, 2), data))
                if len(self.max_heap) < len(self.min_heap):
                    val = heapq.heappop(self.min_heap)
                    heapq.heappush(self.max_heap, (round(-val, 2), val))
            except ValueError:
                print('Value Does Not Exist in Max Heap!')
        else:
            try:
                self.min_heap.remove(data)
                if len(self.max_heap) - 2 == len(self.min_heap):
                    heapq.heappush(self.min_heap, (heapq.heappop(self.max_heap))[1])
            except ValueError:
                print('Value Does Not Exist in Min Heap!')


if __name__=="__main__":
    m = MedianCalc([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], [5, 2, 4, 1, 3, 4, 9, 5, 7, 1])
    print(m.get_median())

    m.push_data(14)
    print(m.get_median())

    m.push_data(9)
    print(m.get_median())

    m.remove_data_from_heap(9)
    print(m.get_median())

    m.remove_data_from_heap(14)
    print(m.get_median())

