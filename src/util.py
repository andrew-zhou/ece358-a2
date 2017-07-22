#!/bin/python3
from __future__ import print_function

from constants import *
import json
import socket
import sys

MAX_CLIENTS = 80
MIN_PORT, MAX_PORT = 10000, 11000
PROBE_ADDR = ('8.8.8.8', 80)

""" Prints to stderr """	
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def application_recv(conn):
    num_bytes = int.from_bytes(conn.recv(4), byteorder='big')

"""Binds the socket to localhost and an open port from
MIN_PORT to MAX_PORT.

Returns the binded port.
"""
def mybind(socket):
	for port in range(MIN_PORT, MAX_PORT+1):
		try:
			ip = get_non_loopback_ip()
			socket.bind((ip, port))
			return ip, port
		except Exception:
			pass
	return None


"""Returns the non-loopback ip of the current host by sending
a probe to Google DNS.
"""
def get_non_loopback_ip():
	probe = socket.socket(type=socket.SOCK_DGRAM)
	probe.connect(PROBE_ADDR)
	return probe.getsockname()[0]


def get_args(num_required, num_expected=None):
	if not num_expected:
		num_expected = num_required
	args = sys.argv[1:]
	if len(args) < num_required:
		raise Exception('Missing required arguments')
	return args[:num_expected] + [None] * (max(num_expected - len(args), 0))
