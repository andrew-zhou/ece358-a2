#!/bin/python3

from rdt.checksum import verify_checksum
from rdt.connection import Connection, ConnectionStatus
from rdt.segment import Segment, SegmentFlags

from queue import Queue
from socket import socket, AF_INET, SOCK_DGRAM
from sys import stderr
from threading import Thread, Lock

class Manager(object):
    def __init__(self, ip, port, conn_queue):
        """Manager acts as a bridge between the high-level RDT Connections and
        low-level UDP socket. It binds a UDP socket to a given IP/Port,
        verifies the integrity of incoming datagrams, manages the creation and
        state transitions of various connections, and routes the RDT segments
        to their appropriate connections.

        Parameters:
            ip: (string) IP Address to bind server socket to
            port: (int) Port to bind server socket to
            conn_queue: (queue.Queue) Synchronized queue for accessing new connections.
            When a new connection is established, Manager will put the connection in conn_queue.
        """
        self.ip = ip
        self.port = port
        self.conn_queue = conn_queue

        self.connections = {}
        self.connections_lock = Lock()  # Lock to access self.connections
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.datagrams = Queue()        

    def start(self):
        self.socket.bind((self.ip, self.port))
        t = Thread(target=self._handle_all)
        t.daemon = True
        t.start()

        # Main socket loop
        while True:
            datagram, addr = self.socket.recvfrom(4096)
            self.datagrams.put((addr, datagram))

    def _handle_all(self):
        while True:
            addr, datagram = self.datagrams.get()
            self._handle_datagram(addr, datagram)

    def _handle_datagram(self, addr, datagram):
        # Sanity checks
        segment = None
        is_syn = False
        seg_key = None
        try:
            if isinstance(datagram, str):
                datagram = datagram.encode()
            elif not isinstance(datagram, bytes):
                datagram = bytes(datagram)
            segment = Segment.from_bytes(datagram)
            is_syn = segment.flags.syn
            seg_key = (addr[0], segment.source)
            verify_checksum(datagram)
            if self.port != segment.dest or addr[1] != segment.source:
                raise Exception('Port does not match.')
        except Exception as e:
            print('Invalid segment received.', file=stderr)
            if not is_syn and seg_key:
                # Send back an ACK
                with self.connections_lock:
                    conn = self.connections.get(seg_key)
                    if conn:
                        conn._send(b'', SegmentFlags(ack=True), conn.next_seq)

        if not segment:
            return

        # Check if segment is attempting to SYN
        if segment.flags.syn and not segment.flags.ack and not segment.flags.fin:
            with self.connections_lock:
                # Invalid if there is an existing open connection
                if seg_key in self.connections:
                    old_conn = self.connections[seg_key]
                    if old_conn.status() == ConnectionStatus.CLOSED:
                        del self.connections[seg_key]
                    else:
                        return
                new_conn = Connection(self.ip, self.port, addr[0], segment.source, send_socket=self.socket)
                new_conn._recv_syn(segment)
                self.connections[seg_key] = new_conn
        elif segment.flags.syn and segment.flags.ack and not segment.flags.fin:
            with self.connections_lock:
                # Valid only if there is an existing connection in syn-sent state
                conn = self.connections.get(seg_key)
                if conn and conn.status() == ConnectionStatus.SYN_SENT:
                    conn._recv_syn_ack(segment)
                    self.conn_queue.put(conn)
        elif segment.flags.fin and not segment.flags.syn and not segment.flags.ack:
            with self.connections_lock:
                # Valid only if there is an existing connection in estab state
                conn = self.connections.get(seg_key)
                if conn and conn.status() == ConnectionStatus.ESTAB:
                    conn._recv_fin(segment)
        else:
            with self.connections_lock:
                conn = self.connections.get(seg_key)
                if not conn:
                    return
                if conn.status() == ConnectionStatus.SYN_RECD:
                    if segment.flags.ack:
                        conn._establish(segment)
                        self.conn_queue.put(conn)
                    else:
                        return
                if conn.status() == ConnectionStatus.ESTAB:
                    conn._receive_segment(segment)
