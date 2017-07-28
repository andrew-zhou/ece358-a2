#!/bin/python3
import os
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
        # eprint("Established connection with client at %s %s" % (client_ip, client_port))
        file_name = "%s.%s.%s.%s" % (client_ip, client_port, self.ip, self.port)
        file_path = os.path.join(self.file_dir, file_name)
        try:
            # Send client initial file contents
            try:
                with open(file_path, 'rb') as fh:
                    file_bytes = fh.read()
                    # eprint("START: send file %s of size %d" % (file_path, len(file_bytes)))
                    application_send(conn, file_bytes)
            except FileNotFoundError:
                # eprint("START: send empty file")
                application_send(conn, b'')

            # Append new contents to file
            while True:
                new_file_bytes = application_recv(conn)
                # eprint("Received new contents of size %d for file %s" % (len(new_file_bytes), file_path))
                with open(file_path, 'a+b') as fh:
                    fh.write(new_file_bytes)
                application_send(conn, new_file_bytes)
        except ConnectionClosedException:
            eprint("Connection closed with client at %s %s" % (client_ip, client_port))
        except PermissionError as pe:
            eprint("Error with permissions on file %s. Raw error %s" % (file_path, pe))
            conn.close()
        except Exception as e:
            eprint("Unexpected error: %s" % e)
            if conn.status() != ConnectionStatus.CLOSED:
                conn.close()

    def start(self):
        # eprint("Listening at %s %d" % (self.ip, self.port))
        conn_queue = Queue()
        m = Manager(self.ip, self.port, conn_queue)
        t = Thread(target=m.start)
        t.daemon = True
        t.start()
        while True:
            conn = conn_queue.get()
            conn_t = Thread(target=self._handle_connection, args=(conn,))
            conn_t.daemon = True
            conn_t.start()

if __name__ == '__main__':
    port, file_dir = get_args(2)
    ip = "0.0.0.0"
    server = FileServer(ip, int(port), file_dir)
    server.start()
