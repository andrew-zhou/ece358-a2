class Interval:

    def __init__(self, low, high):
        self.low = low
        self.high = high
        self.next = None

    def __str__(self):
        return "({}, {})".format(self.low, self.high)

class IntervalList:

    def __init__(self):
        self.root = None

    def __str__(self):
        itlStr = "["
        cur = self.root
        while cur is not None:
            itlStr += str(cur) + ", "
            cur = cur.next
        itlStr += "]"
        return itlStr

    def remove_if_exists(self, val):
        cur = self.root
        prev = None
        while cur is not None:
            if cur.low <= val and val <= cur.high:
                if prev:
                    prev.next = cur.next
                else:
                    self.root = cur.next
                return cur.high
            prev = cur
            cur = cur.next
        return None

    def insert(self, low, high):
        if self.root is None:
            self.root = Interval(low, high)
            return

        newLow = low 
        newHigh = high

        parent = None
        cur = self.root
        prev = None
        started = False
        while cur is not None:
            if not parent and newLow <= cur.high and cur.low <= newHigh:
                started = True
                parent = prev
                newLow = min(newLow, cur.low)

            if started and cur.low <= newHigh:
                newHigh = max(newHigh, cur.high)

            if cur.low > newHigh:
                break

            prev = cur
            cur = cur.next

        # print('new: {} cur: {} prev: {} parent: {}'.format((newLow, newHigh), cur, prev, parent))
        node = Interval(newLow, newHigh)
        if parent:
            parent.next = node
            node.next = cur
        elif started:
            self.root = node
            node.next = cur
        elif newHigh < self.root.low:
            node.next = self.root
            self.root = node
        else:
            prev.next = node
            node.next = cur

    def subtract(self, val):
        # This is some specialized shit
        node = self.root
        alive_head = None
        while node:
            node.low = max(node.low - val, 0)
            node.high -= val
            if node.high >= 0:
                if not alive_head:
                    alive_head = node
            node = node.next
        self.root = alive_head


# if __name__ == '__main__':
#     itl = IntervalList()
#     insert_seq = [(10, 11), (1, 2), (7, 8)]
#     merge_beg = [(1, 2), (5, 6), (10, 11), (0, 1), (2, 3), (-1, 4)]
#     merge_end = [(1, 2), (5, 6), (10, 11), (9, 10), (11, 12), (8, 13)]
#     merge_mid = [(1, 2), (5, 6), (10, 11), (4, 5), (6, 7), (3, 8)]

#     insert_tests = [merge_mid]
#     for test_seq in insert_tests:
#         for interval in test_seq:
#             itl.insert(interval[0], interval[1])
#             print('Insert {} -> {}'.format(interval, itl))

#     query_seq = [3, 7, 1]
#     query_tests = []
#     for test_seq in query_tests:
#         for query_val in test_seq:
#             removed_interval_max_val = itl.remove_if_exists(query_val)
#             print('Remove {} returns {} -> {}'.format(query_val, removed_interval_max_val, itl))

