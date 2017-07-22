#!/bin/python3

from queue import Queue
from rdt.manager import Manager
from rdt.connection import Connection
from threading import Thread

q = Queue()
m = Manager('127.0.0.1', 5052, q)
m.connections[('127.0.0.1', 5051)] = Connection('127.0.0.1', 5052, '127.0.0.1', 5051)
t = Thread(target=m.start)
t.daemon = True
t.start()
m.connections[('127.0.0.1', 5051)]._send_syn()
while True:
    k = q.get()
    print('Wow we got something!')
    print(k)
    print('We want some data!')
    data = k.recv(2 ** 20)
    print('Wow we actually got data lmao')
    print(data)
    print('We will close the connection now...')
    k.close()
    print('We cant send data anymore...right?')
    try:
    	k.send(b'This should fail')
    except Exception as e:
    	print('Got exception {}'.format(type(e)))
    print(k.status())
