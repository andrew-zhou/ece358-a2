from rdt.segment import Segment, SegmentFlags
from rdt.checksum import verify_checksum

source = 5001
dest = 5050
seq = 140
ack = 321993784
flags = SegmentFlags(fin=True)
payload = 'Hello World, this is a payload!'.encode()

segment = Segment(source, dest, seq, ack, flags, payload)

print(segment.source)
print(segment.dest)
print(segment.seq)
print(segment.ack)
print(segment.flags.syn)
print(segment.flags.ack)
print(segment.flags.fin)
print(segment.payload)
print(segment.checksum)
print(segment.size)

seg_bytes = segment.to_bytes()
print(seg_bytes)

verify_checksum(seg_bytes)

segment = Segment.from_bytes(seg_bytes)
print(segment.source)
print(segment.dest)
print(segment.seq)
print(segment.ack)
print(segment.flags.syn)
print(segment.flags.ack)
print(segment.flags.fin)
print(segment.payload)
print(segment.checksum)
print(segment.size)