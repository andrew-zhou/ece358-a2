#!/bin/python3
import sys

from queue import Queue
from threading import Thread
from rdt.manager import Manager
from rdt.connection import ConnectionClosedException, ConnectionStatus

from util import *

class FileServer:
    def __init__(self, ip, port, file_dir):
        self.ip = ip
        self.port = port
        self.file_dir = file_dir

    def _handle_connection(self, conn):
        client_ip, client_port = conn.peer()
        eprint("Established connection with client at %s %s" % (client_ip, client_port))
        file_name = "%s.%s.%s.%s" % (client_ip, client_port, self.ip, self.port)
        try:
            # Send client initial file contents
            try:
                with open(file_name, 'rb') as fh:
                    file_bytes = fh.read()
                    eprint("START: send file %s of size %d" % (file_name, len(file_bytes)))
                    application_send(conn, file_bytes)
            except FileNotFoundErrror:
                eprint("START: send empty file")
                application_send(conn, b'')

            # Append new contents to file
            while True:
                new_file_bytes = application_recv(conn)
                eprint("Received new contents of size %d for file %s" % (len(file_bytes), file_name))
                with open(file_name, 'a+b') as fh:
                    fh.write(new_file_bytes)
                application_send(conn, new_file_bytes)
        except ConnectionClosedException:
            eprint("Connection closed with client at %s %s" % (client_ip, client_port))
        except:
            eprint("Unexpected error: %s" % sys.exc_info()[0])  
            if conn.status() != ConnectionStatus.CLOSED:
                conn.close()

    def start(self):
        conn_queue = Queue()
        m = Manager(ip, port, conn_queue)
        t = Thread(target=m.start)
        t.daemon = True
        t.start()
        while True:
            conn = conn_queue.get()
            conn_t = Thread(target=self._handle_connection, args=(conn))
            conn_t.start()

if __name__ == '__main__':
    port, file_dir = get_args(2)
    ip = get_non_loopback_ip()
    server = FileServer(ip, port, file_dir)
    server.start()
