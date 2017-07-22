#!/bin/python3

from queue import Queue
from threading import Thread
from rdt.manager import Manager
from rdt.connection import ConnectionClosedException

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
        print('Lets send hello world')
        c.send(b'Hello World')
        print('Lets try and receive some data!')
        try:
        	data = c.recv(2 ** 20)
        except ConnectionClosedException:
        	print('Uh oh, the connection closed!!!')
