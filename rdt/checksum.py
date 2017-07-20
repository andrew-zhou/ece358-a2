#!/bin/python3

import sys

def generate_checksum(bytes_):
    # Note: assumed that bytes are provided in network byte order
    # Take ones complement sum of all byte pairs
    checksum = 0
    for pair in _all_byte_pairs(bytes_):
        val = int.from_bytes(pair, 'big')
        checksum = _bitwise_add(checksum, val)

    # Take the ones complement of the sum
    checksum = checksum ^ 0xFFFF

    # If checksum is zero, make it all 1s
    if checksum == 0:
        checksum = 0xFFFF

    return checksum

def verify_checksum(bytes_):
    # Take the ones complement sum of all byte pairs
    # Note: When verifying checksum endianness does not matter
    sum_ = 0
    for pair in _all_byte_pairs(bytes_):
        val = int.from_bytes(pair, sys.byteorder)
        sum_ = _bitwise_add(sum_, val)

    # Assert that sum is all 1s
    if sum_ != 0xFFFF:
        raise InvalidChecksumException()

def _all_byte_pairs(bytes_):
    # This is a kinda hacky way to append \x00 to a last odd byte
    # since accessing that byte by itself returns an int which can't
    # concatenate with a byte
    return [
        bytes_[idx:idx+2]
        if idx + 1 < len(bytes_)
        else bytes_[idx].to_bytes(1, sys.byteorder) + b'\x00'
        for idx in range(0, len(bytes_), 2)
    ]

def _bitwise_add(a, b):
        # Bitwise ones-complementary addition helper
        MAX = 1 << 16
        sum_ = a + b
        return sum_ if sum_ < MAX else (sum_ + 1) % MAX

class InvalidChecksumException(Exception):
    pass
