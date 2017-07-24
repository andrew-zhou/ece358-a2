#!/bin/python3
import os
import sys
from datetime import datetime

from queue import Queue
from threading import Thread
from rdtlossy.manager import Manager
from rdtlossy.connection import Connection
from rdtlossy.connection import ConnectionClosedException, ConnectionStatus

from util import *

class NiceClient(object):
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

    def start(self):
        conn_queue = Queue()
        connections = {}
        m = Manager(self.ip, self.port, conn_queue)
        t = Thread(target=m.start)
        t.daemon = True
        t.start()

        # USAGE:
        # can use 'last', instead of reentering serverip and serverport
        # con <server_ip> <server_port>
        #       -> establishes connection and prints what it recieves
        # add <server_ip> <server_port>
        #       -> asks for some text to append to file, prints what it recieves
        # dis <server_ip> <server_port>
        #       -> initiates close
        # 
        while True:
            inp = input('>>')
            cmd = inp.split(' ')

            if cmd[0] == 'con':
                if cmd[1] == 'last':
                    server_ip, server_port = last
                else:
                    server_ip = cmd[1]
                    server_port = int(cmd[2])
                    last = (server_ip, server_port)
                m.connections[(server_ip, server_port)] = Connection(self.ip, self.port, server_ip, server_port, send_socket=m.socket)
                m.connections[(server_ip, server_port)]._send_syn()
                print('sent syn')
                connections[(server_ip, server_port)] = conn_queue.get()
                print('We got em')
                data = application_recv(connections[(server_ip, server_port)])
                print('recieved')
                # print(data)

            elif cmd[0] == 'add':
                if cmd[1] == 'last':
                    server_ip, server_port = last
                else:
                    server_ip = cmd[1]
                    server_port = int(cmd[2])
                    last = (server_ip, server_port)
                text = input('Enter some text to add: ')
                application_send(connections[(server_ip, server_port)], bytes(text, 'utf-8'))
                print('sent, now receiving: ')
                data = application_recv(connections[(server_ip, server_port)])
                print('recieved')
                # print(data)

            elif cmd[0] == 'dis':
                if cmd[1] == 'last':
                    server_ip, server_port = last
                else:
                    server_ip = cmd[1]
                    server_port = int(cmd[2])
                    last = (server_ip, server_port)
                connections[(server_ip, server_port)].close()

            elif cmd[0] == 'file':
                if cmd[1] == 'last':
                    server_ip, server_port = last
                else:
                    server_ip = cmd[1]
                    server_port = int(cmd[2])
                    last = (server_ip, server_port)
                file_name = input('Enter the filename: ')
                file = open(file_name, 'rb')
                file_data = file.read()

                application_send(connections[(server_ip, server_port)], file_data)
                print('sent, now receiving: ')
                data = application_recv(connections[(server_ip, server_port)])
                print('received')
                print(data)

            elif cmd[0] == 'time':
                if cmd[1] == 'last':
                    server_ip, server_port = last
                else:
                    server_ip = cmd[1]
                    server_port = int(cmd[2])
                    last = (server_ip, server_port)
                file_name = input('Enter the filename: ')
                file = open(file_name, 'rb')
                file_data = file.read()

                start = datetime.now()
                application_send(connections[(server_ip, server_port)], file_data)
                data = application_recv(connections[(server_ip, server_port)])
                end = datetime.now()
                print (end - start)

            else:
                print('Sorry no comprende')


if __name__ == '__main__':
    port, file_dir = get_args(2)
    ip = get_non_loopback_ip()
    client = NiceClient(ip, int(port))
    client.start()
