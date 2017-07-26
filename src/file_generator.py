#!/bin/python3
import os
import util

# Usage: python3 file_generator.py <file_name> <num_bytes>
if __name__ == '__main__':
    file_name, num_bytes = util.get_args(2)
    byte_contents = os.urandom(int(num_bytes))
    with open(file_name, 'wb') as fh:
        fh.write(byte_contents)
