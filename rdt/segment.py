#!/bin/python3

from rdt.checksum import generate_checksum

import socket
import struct
import sys


class Segment(object):
    HEADER_SIZE = 20  # Header is always 20 bytes
    HEADER_FORMAT = '!2H3LcxH'  # Struct format string for header

    def __init__(self, source, dest, seq, ack, flags, payload, size=None, checksum=None):
        """Segment encapsulates the rdt segment format and logic for
        converting between this high-level representation and a byte representation.

        Parameters:
            source: (int) Source port
            dest: (int) Destination port
            seq: (int) Sequence number
            ack: (int) Acknowledgement number
            flags: (SegmentFlags) SYN/ACK/FIN flags
            payload: (bytes) Data to send (as bytes)
            size: (int|None) Optionally specify size in bytes, otherwise calculated
            checksum: (int|None) Optionally specify checksum in big endian, otherwise calculated
        """
        self.source = source
        self.dest = dest
        self.seq = seq
        self.ack = ack
        self.flags = flags
        self.payload = payload

        # Size of segment is header + payload
        self.size = Segment.HEADER_SIZE + len(payload)

        # Set checksum
        self.checksum = self._calculate_checksum()

    def to_bytes(self):
        """Converts to a byte representation. As part of this conversion,
        we transform all ints in the header into network endian order.
        """
        return struct.pack(
            self.HEADER_FORMAT,
            socket.htons(self.source),
            socket.htons(self.dest),
            socket.htonl(self.size),
            socket.htonl(self.seq),
            socket.htonl(self.ack),
            self.flags.to_byte(),
            socket.htons(self.checksum)
        ) + self.payload

    @classmethod
    def from_bytes(cls, bytes_):
        """Converts to the class representation. As part of this conversion,
        we transform all ints in the header into host endian order with the
        exception of the checksum which we leave in network order.
        """
        # Unpack the header
        source, dest, size, seq, ack, flag_byte, checksum = struct.unpack(cls.HEADER_FORMAT, bytes_[:cls.HEADER_SIZE])

        # Convert to host endian
        source = socket.ntohs(source)
        dest = socket.ntohs(dest)
        size = socket.ntohl(size)
        seq = socket.ntohl(seq)
        ack = socket.ntohl(ack)

        # Convert flags to object
        flags = SegmentFlags.from_byte(flag_byte)

        # Unpack payload
        payload = bytes_[cls.HEADER_SIZE:size]

        # Wrap in object
        segment = Segment(source, dest, seq, ack, flags, payload, size, checksum)
        return segment

    def _calculate_checksum(self):
        # Convert to bytes in system endian
        bytes_ = (
            self.source.to_bytes(2, sys.byteorder) +
            self.dest.to_bytes(2, sys.byteorder) +
            self.size.to_bytes(4, sys.byteorder) +
            self.seq.to_bytes(4, sys.byteorder) +
            self.ack.to_bytes(4, sys.byteorder) +
            self.flags.to_byte() +
            b'\x00\x00\x00' +
            self.payload
        )

        # Return checksum
        return generate_checksum(bytes_)


class SegmentFlags(object):
    SYN_MASK = 1 << 7
    ACK_MASK = 1 << 6
    FIN_MASK = 1 << 5

    def __init__(self, syn=False, ack=False, fin=False):
        """SegmentFlags is a data class for the three possible flags and
        allows for converting between this high-level representation and a byte representation.
        """
        self.syn = syn
        self.ack = ack
        self.fin = fin

    def to_byte(self):
        # Endianness doesn't matter here since it's just one byte
        return (
            (self.SYN_MASK if self.syn else 0) |
            (self.ACK_MASK if self.ack else 0) |
            (self.FIN_MASK if self.fin else 0)
        ).to_bytes(1, 'big')

    @classmethod
    def from_byte(cls, byte):
        val = int.from_bytes(byte, sys.byteorder)
        syn = val & cls.SYN_MASK != 0
        ack = val & cls.ACK_MASK != 0
        fin = val & cls.FIN_MASK != 0
        flags = SegmentFlags(syn=syn, ack=ack, fin=fin)
        return flags