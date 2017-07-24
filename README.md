# ECE358 Programming Assignment #2

## Build
``` make ```

## Run
Client
```

```

Server
```
$ ./pa2-358s17 <port> <file_directory_path> 
```

## Things to test
- [x] Reliable connection (Order is preserved)
- [ ] Performance (>= 10Mbps)
- [x] Multiple clients per server
- [x] Multiple servers running simultaneously
- [x] Initiate connection closure from server side
- [ ] Invalid segment checksums
- [ ] Dropped segments from server to client
- [ ] SYN/Data segment after connection closure
- [x] Server lacks permission to edit file
- [ ] Super large payloads requiring wrap around
- [ ] Server and Client sending/recieving to eachother at the same time
