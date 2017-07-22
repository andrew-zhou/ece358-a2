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

    def _send(conn, num_bytes, raw_bytes):
	raw_num_bytes = num_bytes.to_bytes(4, byteorder=sys.byteorder)		
	raw_all_bytes = raw_num_bytes + raw_bytes
	conn.send(raw_all_bytes)

    def _handle_

    def _handle_connection(self, conn):
	client_ip, client_port = conn.peer()
	eprint("Received connection with client at %s %s" % (client_ip, client_port))
	file_name = "%s.%s.%s.%s" % (client_ip, client_port, self.ip, self.port)
	try:
	    try:
	        with open(file_name, 'r') as fh:
		    num_file_bytes, file_bytes = fh.tell(), fh.read()
		    eprint("Sending file %s of size %d" % (num_file_bytes, file_name))
		    self._send(num_file_bytes, file_bytes) 
	    except FileNotFoundErrror:
		self._send(0, b'')

      	    num_client_bytes = conn.recv(4)
	    while True:
		
	    
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
