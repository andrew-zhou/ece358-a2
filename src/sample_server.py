#!/bin/python3

from queue import Queue
from threading import Thread
from rdt.manager import Manager

if __name__ == '__main__':
    q = Queue()
    m = Manager('127.0.0.1', 5051, q)
    t = Thread(target=m.start)
    t.daemon = True
    t.start()
    while True:
        c = q.get()
        print('Wow we got something!')
        print(c)
