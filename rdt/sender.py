#!/bin/python3

from rdt.constants import WINDOW_SIZE
from rdt.checksum import verify_checksum
from rdt.segment import Segment

from queue import PriorityQueue
from threading import Timer


class SenderSocket(object):
	def __init__(self):
		self.seq = 0
		self.next_seq = 1
		self.ack = 0
		self.buffer = PriorityQueue()
		self.timer = None
		self.connection = None  # TODO

	def send(self, data):
		if self.next_seq < self.seq + WINDOW_SIZE:
			
			# TODO: Actual send
			if self.send_base == self.next_seq_num:
				# TODO: Start timer
				pass
			self.next_seq_num += len(data)
		else:
			raise WindowFullException()

	def recv(self, seg_bytes):
		verify_checksum(seg_bytes)

		segment = Segment.from_bytes(seg_bytes)

		if segment.flags.

		if ack_num > self.send_base:
			self.send_base = ack_num
		if self.send_base == self.next_seq_num:
			# TODO: Stop timer
			pass
		else:
			# TODO: Start timer
			pass


class WindowFullException(Exception):
	pass
