#!/bin/python3

from rdt.segment import Segment, SegmentFlags

from enum import Enum
from socket import socket, AF_INET, SOCK_DGRAM
from threading import Lock
from time import sleep

class Connection(object):
	TIMEOUT_INTERVAL = 30
	MAX_PAYLOAD_SIZE = 480
	MAX_SEQ = 2 ** 32

	def __init__(self, my_ip, my_port):
		"""Connection is the rdt equivalent of a TCP client socket. Use for
		sending/receiving data in a dedicated connection with a single peer.

		Parameters:
			my_ip: (string) IP Address of current client
			my_port: (int) Port of current client
		"""
		self.tcb = ConnectionTCB(my_ip, my_port)
		self.send_buffer = ConnectionBuffer()
		self.recv_buffer = ConnectionBuffer()
		self.timer = ConnectionSendTimer(self.TIMEOUT_INTERVAL, self._timeout)
		self.seq = 0  # Keep track of the earliest sent un-ack'd segment 
		self.next_seq = 0  # Keep track of the next seq number to send
		self.ack = 0  # Keep track of the earliest received segment not sent to client
		self.next_ack = 0  # Keep track of the next expected seq number from peer
		self.send_socket = socket(AF_INET, SOCK_DGRAM)

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
		# Break payload into chunks of max payload size
		chunks = [data[i:i + self.MAX_PAYLOAD_SIZE] for i in range(0, len(data), self.MAX_PAYLOAD_SIZE)]

		# Send out chunks
		for chunk in chunks:
			self._send_new(chunk, SegmentFlags(ack=True))

	def recv(self):
		"""Returns the payload of the next in-order segment received from the peer.
		This is a blocking call.
		"""
		# In an attempt to make this more performant, we sleep for a second between
		# iterations of acquiring the buffer mutex and iterating through the buffer in
		# an attempt to avoid hogging the mutex

		# TODO: Might have to check connection status after every iteration to kill on close
		data = None
		while True:
			with self.recv_buffer.lock:
				if self.ack in self.recv_buffer.buffer:
					data = self.recv_buffer.buffer[self.ack]
					break
			sleep(1)

		# Shift the base ack
		self.ack = (self.ack + len(data)) % self.MAX_SEQ
		return data

	# === Helper Methods - Do NOT Call in Application Layer ===
	def _send_new(self, data, flags):
		# Send segment
		seq = self.next_seq
		self._send(data, flags, seq)

		# Update next_seq
		self.next_seq = (self.next_seq + len(data)) % self.MAX_SEQ

		# Add to send_buffer
		block = ConnectionSentBlock(data, seq, flags)
		with self.send_buffer.lock:
			self.send_buffer.buffer[seq] = block

		# Start timer if not already started
		self.timer.start()

	def _send(self, data, flags, seq):
		# Create segment
		source = self.tcb.my_port
		dest = self.tcb.their_port
		ack = self.ack
		segment = Segment(source, dest, seq, ack, flags, data)

		# Send via. UDP
		self.send_socket.sendto(segment.to_bytes(), self.peer())

	def _timeout(self):
		# Get data/seq/flags for segment corresponding to self.seq
		block = None
		with self.send_buffer.lock:
			if self.seq in self.send_buffer.buffer:
				block = self.send_buffer.buffer[self.seq]

		# Re-send segment
		if block:
			self._send(block.data, block.flags, block.seq)

	def _receive_segment(self, segment):
		"""This is called by the connection manager to put segments received
		by the UDP socket into the connection's buffer. This is not for state transition
		related segments (ie. SYN, FIN).
		"""
		# ACK all sent segments up to segment.ack
		def _within_bounds(val, lo, hi):
			wraparound = lo > hi
			return (
				(wraparound and (val > lo or val <= self.hi)) or
				(not wraparound and val > lo and val <= hi)
			)

		if segment.flags.ack:
			ack = segment.ack
			with self.send_buffer.lock:
				while _within_bounds(ack, self.seq, self.next_seq)
					block = self.send_buffer.buffer.get(self.seq)
					if not block:
						# There was some logic error - this should never happen
						raise Exception('Programming error')
					self.seq = (self.seq + len(block.data)) % self.MAX_SEQ
					del self.send_buffer.buffer[self.seq]

		# Store payload in recv buffer
		# Since there's the potential for re-ordered segments in a wraparound
		# situation where their validity is ambiguous, and there is no space
		# in the header to add timestamps to do something like PAWS (see: RFC-1323),
		# we do the following:
		# consider the window of available bytes between next_ack and ack (ie. not
		# currently used). The half of those bytes closer to next_ack we accept and
		# store in the buffer. The half closer to ack we reject assuming that they
		# were re-ordered and stale
		seq = segment.seq
		if _within_bounds(seq, self.ack, self.next_ack):
			# This is a duplicate segment; ignore
			# === This is a big question??? ===
			# TODO: Do we need to consider appending bytes from this segment if
			# it starts within data that we have but continues past next_ack?
			return
		# === This is a big question??? ===
		# TODO: What about collisions with other data in the buffer???
		pass 

	# === Connection Establishment Methods - Do NOT Call in Application Layer ===
	# TODO: All of these

	def _listen(self):
		if self.status() == ConnectionStatus.CLOSED:
			self.tcb.status = ConnectionStatus.LISTEN

	def _send_syn(self, their_ip, their_port):
		if self.status() == ConnectionStatus.CLOSED:
			# TODO: Send SYN
			self.tcb.status = ConnectionStatus.SYN_SENT

	def _recv_syn(self, their_ip, their_port, seq):
		if self.status() == ConnectionStatus.LISTEN:
			self.tcb.status = ConnectionStatus.SYN_RECD
			self.tcb.their_ip = their_ip
			self.tcb.their_port = their_port
			# TODO: Handle receiving the SYN
			# TODO: Send SYN/ACK back

	def _recv_syn_ack(self, data=None):
		# Can optionally piggy-back data onto the ACK
		if self.status() == ConnectionStatus.SYN_SENT:
			# TODO: Handle receiving the SYN/ACK
			self.tcb.status = ConnectionStatus.ESTAB

	def _establish(self):
		if self.tcb.status == ConnectionStatus.SYN_SENT or self.tcb.status == ConnectionStatus.SYN_RECV:
			self.tcb.status = ConnectionStatus.ESTAB

	def _recv_fin(self):
		if self.tcb.status == ConnectionStatus.ESTAB:
			# TODO: Handle closing logic (ie. shutdown timer, flush TCB, etc.)
			# TODO: Handle receiving the FIN
			# TODO: Send ACK back
			self.tcb.status = ConnectionStatus.CLOSED


class ConnectionTCB(object):
	def __init__(self, my_ip, my_port):
		self.my_ip = my_ip
		self.my_port = my_port
		self.their_ip = None
		self.their_port = None
		self.status = ConnectionStatus.CLOSED


class ConnectionStatus(Enum):
	CLOSED = 1
	LISTEN = 2
	SYN_SENT = 3
	SYN_RECD = 4
	ESTAB = 5


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
			self._timer = Timer(self.interval, self._run)
			self._timer.start()
			self.is_running = True

	def stop(self):
		self._timer.cancel()
		self.is_running = False

	def _run(self):
		self.function()
		self.is_running = False
		self.start()

class ConnectionBuffer(object):
	"""Very crude concurrent dict - literally just a lock and a dict.
	Basically just a reminder to always acquire the buffer's lock before
	attempting to access the buffer.
	"""
	def __init__(self):
		self.lock = Lock()
		self.buffer = {}