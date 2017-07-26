#!/bin/python3

from rdt.checksum import verify_checksum
from rdt.connection import Connection, ConnectionStatus
from rdt.segment import Segment, SegmentFlags

from queue import Queue
from socket import socket, AF_INET, SOCK_DGRAM
from sys import stderr
from threading import Thread, Lock

class Manager(object):
    NUM_THREADS = 20
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
        self.segments = Queue()
        self.partial_segments = {}

    def start(self):
        self.socket.bind((self.ip, self.port))
        threads = []
        for _ in range(self.NUM_THREADS):
            t = Thread(target=self._handle_thread)
            t.daemon = True
            threads.append(t)
        for t in threads:
            t.start()

        # Main socket loop
        while True:
            datagram, addr = self.socket.recvfrom(4096)
            # Add data to partial segments
            if addr not in self.partial_segments:
                self.partial_segments[addr] = bytearray()
            self.partial_segments[addr] += datagram
            # Check if partial segment is complete segment
            seg_bytes = self.partial_segments[addr]
            if len(seg_bytes) >= 20:  # Must be at least size of header
                segment = Segment.from_bytes(bytes(seg_bytes))
                if segment.size == len(seg_bytes):
                    # This is a full segment, remove from partial segments, add to queue
                    del self.partial_segments[addr]
                    self.segments.put((addr, segment, seg_bytes))

    def _handle_thread(self):
        while True:
            addr, segment, seg_bytes = self.segments.get()
            self._handle_segment(addr, segment, seg_bytes)

    def _handle_segment(self, addr, segment, seg_bytes):
        # Sanity checks
        is_syn = segment.flags.syn
        seg_key = (addr[0], segment.source)
        valid = True
        try:
            verify_checksum(seg_bytes)
            if self.port != segment.dest or addr[1] != segment.source:
                raise Exception('Port does not match.')
        except Exception as e:
            print('Invalid segment received.', file=stderr)
            valid = False
            if not is_syn:
                # Send back an ACK
                with self.connections_lock:
                    conn = self.connections.get(seg_key)
                    if conn:
                        conn._send(b'', SegmentFlags(ack=True), conn.next_seq)
        if not valid:
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
