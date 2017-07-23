#!/bin/python3
import os
import sys

from queue import Queue
from threading import Thread
from rdt.manager import Manager
from rdt.connection import Connection
from rdt.connection import ConnectionClosedException, ConnectionStatus

from util import *

class OrderClient(object):
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

    def start(self):
        server_tup = ('192.168.0.113', 65535)

        conn_queue = Queue()
        m = Manager(self.ip, self.port, conn_queue)
        t = Thread(target=m.start)
        t.daemon = True
        t.start()

        m.connections[server_tup] = Connection(self.ip, self.port, server_tup[0], server_tup[1], send_socket=m.socket)
        m.connections[server_tup]._send_syn()
        new_conn = conn_queue.get()

        print("START")
        num = 0
        while num <= 30:
            application_send(new_conn, bytes(str(num) + ",", 'utf-8'))
            num += 1

        while num > 0:
            data = application_recv(new_conn)
            print("GOT " + data.decode('utf-8'))
            num -= 1
        print("DONE")
        new_conn.close()

if __name__ == '__main__':
    port, = get_args(1)
    ip = get_non_loopback_ip()
    client = OrderClient(ip, int(port))
    client.start()
