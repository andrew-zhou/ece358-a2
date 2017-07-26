#!/bin/python3

from rdt.itree import Interval, IntervalList
from rdt.segment import Segment, SegmentFlags

from collections import deque
from enum import Enum
from socket import socket, AF_INET, SOCK_DGRAM
from threading import Lock, Timer
from time import sleep

from util import *

class Connection(object):
    TIMEOUT_INTERVAL = 4
    MAX_PAYLOAD_SIZE = 800
    MAX_SEQ = 2 ** 32

    def __init__(self, my_ip, my_port, their_ip, their_port, send_socket=None):
        """Connection is the rdt equivalent of a TCP client socket. Use for
        sending/receiving data in a dedicated connection with a single peer.

        Parameters:
            my_ip: (string) IP Address of current client
            my_port: (int) Port of current client
        """
        self.tcb = ConnectionTCB(my_ip, my_port, their_ip, their_port)
        self.send_buffer = ConnectionBuffer(buf=deque())
        self.recv_buffer = ConnectionBuffer(buf=ConnectionReceiveWindow())
        self.timer = ConnectionSendTimer(self.TIMEOUT_INTERVAL, self._timeout)
        self.seq = 0  # Keep track of the earliest sent un-ack'd segment 
        self.next_seq = 0  # Keep track of the next seq number to send
        self.ack = 0  # Keep track of the earliest received segment not sent to client
        self.next_ack = 0  # Keep track of the next expected seq number from peer
        self.send_socket = send_socket or socket(AF_INET, SOCK_DGRAM)

    def peer(self):
        """Returns the (ip, port) of the other side of the connection."""
        return self.tcb.their_ip, self.tcb.their_port

    def status(self):
        """Returns the current ConnectionStatus."""
        return self.tcb.status

    def send(self, data):
        """Send payload data to the peer.

        data: (bytes) Bytes to send as payload
        """
        # Check if connection is closed
        if self.status() == ConnectionStatus.CLOSED:
            raise ConnectionClosedException()

        # Break payload into chunks of max payload size
        chunks = [data[i:i + self.MAX_PAYLOAD_SIZE] for i in range(0, len(data), self.MAX_PAYLOAD_SIZE)]

        # Send out chunks
        for chunk in chunks:
            self._send_new(chunk, SegmentFlags(ack=True))

    def recv(self, max_size):
        """Returns the payload of received and buffered data up to max_size.
        This is a blocking call - it will block if the next in-order byte is not yet received.
        """
        # In an attempt to make this more performant, we sleep for a second between
        # iterations of acquiring the buffer mutex in an attempt to avoid hogging the mutex.
        data = None
        while True:
            # Raise exception if connection is closed.
            if self.status() == ConnectionStatus.CLOSED:
                raise ConnectionClosedException()
            with self.recv_buffer.lock:
                if self.recv_buffer.buffer.ready():
                    #eprint('Buffer is expected to have: {} bytes'.format(self.recv_buffer.buffer.expected))
                    data = self.recv_buffer.buffer.get(max_size)
                    break
            sleep(0.1)

        #eprint('Received {} bytes of data to application'.format(len(data)))
        # Shift the base ack
        self.ack = (self.ack + len(data)) % self.MAX_SEQ
        return data

    def close(self):
        """Closes the connection with the peer."""
        # Handle closing logic
        self.timer.stop()
        # Send FIN
        self._send(b'', SegmentFlags(syn=False, ack=False, fin=True), self.next_seq)
        # Update status
        self.tcb.status = ConnectionStatus.CLOSED

    # === Helper Methods - Do NOT Call in Application Layer ===
    def _send_new(self, data, flags):
        # Send segment
        seq = self.next_seq
        # eprint('Sending segment for first time with seq: {}'.format(seq))
        self._send(data, flags, seq)

        # Update next_seq
        self.next_seq = (self.next_seq + len(data)) % self.MAX_SEQ

        # Add to send_buffer
        block = ConnectionSentBlock(data, seq, flags)
        with self.send_buffer.lock:
            self.send_buffer.buffer.append((seq, block))

        # Start timer if not already started
        self.timer.start()

    def _send(self, data, flags, seq):
        # Create segment
        source = self.tcb.my_port
        dest = self.tcb.their_port
        ack = self.next_ack
        segment = Segment(source, dest, seq, ack, flags, data)

        # Send via. UDP
        self.send_socket.sendto(segment.to_bytes(), self.peer())

    def _timeout(self):
        with self.send_buffer.lock:
            for _, block in self.send_buffer.buffer:
                # eprint('Timeout: sending seq {}'.format(block.seq))
                self._send(block.data, block.flags, block.seq)
        #eprint('Timed out')

    def _receive_segment(self, segment):
        """This is called by the connection manager to put segments received
        by the UDP socket into the connection's buffer. This is not for state transition
        related segments (ie. SYN, FIN).
        """
        # ACK all sent segments up to segment.ack
        def _bytes_to_ack(val, lo, hi):
            wraparound = lo > hi
            is_valid = (
                (wraparound and (val > lo or val <= hi)) or
                (not wraparound and val > lo and val <= hi)
            )
            if not is_valid:
                return 0
            if wraparound and val < lo:
                return (Connection.MAX_SEQ - lo) + val
            else:
                return val - lo

        if segment.flags.ack:
            ack = segment.ack
            with self.send_buffer.lock:
                bytes_to_ack = _bytes_to_ack(ack, self.seq, self.next_seq)
                self.seq = (self.seq + bytes_to_ack) % self.MAX_SEQ
                while bytes_to_ack > 0 and self.send_buffer.buffer:
                    seq, block = self.send_buffer.buffer.popleft()
                    # eprint('ACKING block with sequence: {}'.format(seq))
                    if len(block.data) > bytes_to_ack:
                        # Do a partial ACK
                        new_data = block.data[bytes_to_ack:]
                        new_seq = (seq + bytes_to_ack) % self.MAX_SEQ
                        new_block = ConnectionSentBlock(new_data, new_seq, block.flags)
                        self.send_buffer.buffer.appendleft((new_seq, new_block))
                        # eprint('PARTIAL REPUT ACK FOR: {}'.format(new_seq))
                    bytes_to_ack -= len(block.data)
                # if not self.send_buffer.buffer:
                #     self.timer.stop()

        # Store payload in recv buffer
        seq = segment.seq
        offset = seq - self.ack if seq >= self.ack else (seq + self.MAX_SEQ - self.ack)
        if len(segment.payload) > 0:
            with self.recv_buffer.lock:
                #eprint('Segment seq: {}'.format(seq))
                self.recv_buffer.buffer.put(segment.payload, offset)
                self.next_ack = (self.ack + self.recv_buffer.buffer.expected) % self.MAX_SEQ
                # eprint('My desired ack is: {}'.format(self.next_ack))

        if not segment.flags.ack or len(segment.payload) > 0:
            # Send back an ACK
            self._send(b'', SegmentFlags(ack=True), self.next_seq)

    # === Connection Establishment Methods - Do NOT Call in Application Layer ===

    def _send_syn(self):
        if self.status() == ConnectionStatus.CLOSED:
            self.tcb.status = ConnectionStatus.SYN_SENT
            # Send SYN packet
            self._send_new(b'', SegmentFlags(syn=True, ack=False, fin=False))

    def _recv_syn(self, segment):
        if self.status() == ConnectionStatus.CLOSED:
            self.tcb.status = ConnectionStatus.SYN_RECD
            # Handle receiving the SYN
            self.ack = (segment.seq + 1) % self.MAX_SEQ
            self.next_ack = self.ack
            # Send SYN/ACK back
            self._send_new(b'', SegmentFlags(syn=True, ack=True, fin=False))

    def _recv_syn_ack(self, segment):
        if self.status() == ConnectionStatus.SYN_SENT:
            # Handle receiving the SYN/ACK
            self.ack = (segment.seq + 1) % self.MAX_SEQ
            self.next_ack = self.ack
            self.seq = segment.ack
            self.next_seq = segment.ack
            with self.send_buffer.lock:
                self.send_buffer.buffer.clear()
            self.tcb.status = ConnectionStatus.ESTAB
        if self.status() == ConnectionStatus.ESTAB:
            # Send ACK
            self._send(b'', SegmentFlags(syn=False, ack=True, fin=False), self.next_seq)

    def _establish(self, segment):
        if self.tcb.status == ConnectionStatus.SYN_RECD:
            self.tcb.status = ConnectionStatus.ESTAB
            # Handle receiving the ACK
            self.seq = segment.ack
            self.next_seq = segment.ack
            # Clear the send buffer
            with self.send_buffer.lock:
                self.send_buffer.buffer.clear()

    def _recv_fin(self, segment):
        if self.tcb.status == ConnectionStatus.ESTAB:
            # Handle closing logic
            self.timer.stop()
            # Handle receiving the FIN
            self.next_ack = (segment.seq + 1) % self.MAX_SEQ
            # Send ACK back
            self._send(b'', SegmentFlags(syn=False, ack=True, fin=False), self.next_seq)
            # Update status
            self.tcb.status = ConnectionStatus.CLOSED


class ConnectionTCB(object):
    def __init__(self, my_ip, my_port, their_ip, their_port):
        self.my_ip = my_ip
        self.my_port = my_port
        self.their_ip = their_ip
        self.their_port = their_port
        self.status = ConnectionStatus.CLOSED


class ConnectionStatus(Enum):
    CLOSED = 1
    SYN_SENT = 2
    SYN_RECD = 3
    ESTAB = 4


class ConnectionSentBlock(object):
    """Data class to keep track of sent objects in buffer."""
    def __init__(self, data, seq, flags):
        self.data = data
        self.seq = seq
        self.flags = flags


class ConnectionSendTimer(object):
    """Timer that re-runs itself. Need this since Python doesn't come with a
    repeating timer out of the box.
    """
    def __init__(self, interval, func):
        self._timer = None
        self.interval = interval
        self.func = func
        self.is_running = False

    def start(self):
        if not self.is_running:
            # eprint('Starting timer!!!')
            self._timer = Timer(self.interval, self._run)
            self._timer.daemon = True
            self._timer.start()
            self.is_running = True

    def stop(self):
        # if self.is_running:
        #     eprint('Stoping timer!!!')
        self._timer.cancel()
        self.is_running = False

    def _run(self):
        # eprint('=== Calling timer func ===')
        self.func()
        self.is_running = False
        self.start()

class ConnectionBuffer(object):
    """Very crude concurrent buffer - literally just a lock and a buffer (ie. list, dict).
    Basically just a reminder to always acquire the buffer's lock before
    attempting to access the buffer.
    """
    def __init__(self, buf):
        self.lock = Lock()
        self.buffer = buf


class ConnectionReceiveWindow(object):
    """Circular buffer. Keeps track of base and next ack."""
    WINDOW_SIZE = 2 ** 16
    def __init__(self):
        self._arr = [None] * self.WINDOW_SIZE
        self.start = 0  # Index of start of circular buffer
        self.expected = 0  # How many bytes of data we have stored in buffer
        self.itree = IntervalList()

    def put(self, data, offset):
        trimmed_data = data[:max(self.WINDOW_SIZE - offset, 0)]
        if not trimmed_data:
            return	
        ini = self.start + offset
        if ini < self.WINDOW_SIZE:
            forward_length = min(len(trimmed_data), self.WINDOW_SIZE - ini)
            self._arr[ini:ini+forward_length] = trimmed_data[:forward_length]
            wrap_length = len(trimmed_data) - forward_length
            if wrap_length > 0:
                self._arr[:wrap_length] = trimmed_data[forward_length:forward_length + wrap_length]
        else:
            ini -= self.WINDOW_SIZE
            self._arr[ini:ini + len(trimmed_data)] = trimmed_data

        self.itree.insert(offset, offset + len(trimmed_data) - 1)
        self.expected = self._calculate_expected()

    def get(self, max_size):
        size = min(max_size, self.expected)
        if size <= 0:
            return None
        data = []
        # eprint('pre: start: {}, expected: {}, size: {}'.format(self.start, self.expected, size))
        if size > (self.WINDOW_SIZE - self.start):
            total_size = size
            # We need to wrap around
            # Forward length first
            data = self._arr[self.start:self.WINDOW_SIZE]
            self._arr[self.start:self.WINDOW_SIZE] = [None] * (self.WINDOW_SIZE - self.start)
            # Wrap around now
            size -= self.WINDOW_SIZE - self.start
            data += self._arr[:size]
            self._arr[:size] = [None] * size
            # Set start and expected
            self.start = (self.start + total_size) % self.WINDOW_SIZE
            self.itree.subtract(total_size)
            self.expected -= total_size
        else:
            # No wrap around
            data = self._arr[self.start:self.start + size]
            self._arr[self.start:self.start + size] = [None] * size
            self.start = (self.start + size) % self.WINDOW_SIZE
            self.itree.subtract(size)
            self.expected -= size
        # eprint('post: start: {}, expected: {}'.format(self.start, self.expected))
        return bytes(data)

    def ready(self):
        return self.expected > 0

    def _calculate_expected(self):
        # # This is probably not the most efficient way of calculating the next_ack offset
        # # but for this size of window hopefully it'll be performant enough
        # for i in range(self.WINDOW_SIZE):
        #     if self._arr[(self.start + i) % self.WINDOW_SIZE] is None:
        #         return i
        # return self.WINDOW_SIZE
        removed = self.itree.remove_if_exists(self.expected)
        self.expected = removed + 1 if removed is not None else self.expected

class ConnectionClosedException(Exception):
    pass
