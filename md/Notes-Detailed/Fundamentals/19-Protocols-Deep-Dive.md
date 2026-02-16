# CHAPTER 19: PROTOCOLS DEEP DIVE
*TCP, UDP, TLS, HTTP/3, gRPC, and WebRTC*

This chapter provides in-depth coverage of core networking protocols
essential for system design interviews.

## SECTION 19.1: PROTOCOL PROPERTIES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT MAKES A PROTOCOL?                                                |
|                                                                         |
|  A protocol is a set of rules for communication between systems.       |
|  Each protocol makes tradeoffs between these properties:               |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  KEY PROTOCOL PROPERTIES                                       |  |
|  |                                                                 |  |
|  |  1. RELIABILITY                                                |  |
|  |     -------------                                               |  |
|  |     Does data arrive guaranteed?                               |  |
|  |     * Reliable: TCP (retransmits lost packets)                |  |
|  |     * Unreliable: UDP (fire and forget)                       |  |
|  |                                                                 |  |
|  |  2. ORDERING                                                   |  |
|  |     ------------                                                |  |
|  |     Does data arrive in order?                                |  |
|  |     * Ordered: TCP (sequence numbers)                         |  |
|  |     * Unordered: UDP (packets may arrive out of order)        |  |
|  |                                                                 |  |
|  |  3. CONNECTION-ORIENTED vs CONNECTIONLESS                      |  |
|  |     ------------------------------------                        |  |
|  |     Is there a handshake before sending data?                 |  |
|  |     * Connection-oriented: TCP (3-way handshake)              |  |
|  |     * Connectionless: UDP (send immediately)                  |  |
|  |                                                                 |  |
|  |  4. FLOW CONTROL                                               |  |
|  |     -------------                                               |  |
|  |     Can receiver slow down sender?                            |  |
|  |     * Yes: TCP (sliding window)                               |  |
|  |     * No: UDP (sender can overwhelm receiver)                 |  |
|  |                                                                 |  |
|  |  5. CONGESTION CONTROL                                         |  |
|  |     ------------------                                          |  |
|  |     Does protocol adapt to network congestion?                |  |
|  |     * Yes: TCP (slow start, congestion avoidance)            |  |
|  |     * No: UDP (can flood network)                             |  |
|  |                                                                 |  |
|  |  6. STATEFUL vs STATELESS                                      |  |
|  |     ---------------------                                       |  |
|  |     Does protocol maintain state between messages?            |  |
|  |     * Stateful: TCP (connection state)                        |  |
|  |     * Stateless: HTTP (each request independent)              |  |
|  |                                                                 |  |
|  |  7. DUPLEX MODE                                                |  |
|  |     ------------                                                |  |
|  |     * Simplex: One direction only                             |  |
|  |     * Half-duplex: Both directions, one at a time            |  |
|  |     * Full-duplex: Both directions simultaneously (TCP)       |  |
|  |                                                                 |  |
|  |  8. LATENCY                                                    |  |
|  |     -----------                                                 |  |
|  |     How much overhead before first data?                      |  |
|  |     * High: TCP+TLS (3+ RTT)                                  |  |
|  |     * Low: UDP (0 RTT)                                        |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### PROTOCOL PROPERTIES COMPARISON

```
+-------------------------------------------------------------------------+
|                                                                         |
|  +----------------------------------------------------------------+   |
|  |                                                                |   |
|  |  Property        TCP         UDP         QUIC        WebSocket|   |
|  |  ------------------------------------------------------------ |   |
|  |                                                                |   |
|  |  Reliable        Yes         No          Yes         Yes      |   |
|  |                                                                |   |
|  |  Ordered         Yes         No          Yes*        Yes      |   |
|  |                                (per-stream)                    |   |
|  |                                                                |   |
|  |  Connection      Yes         No          Yes         Yes      |   |
|  |                                                                |   |
|  |  Flow Control    Yes         No          Yes         Yes      |   |
|  |                                                                |   |
|  |  Congestion Ctrl Yes         No          Yes         Inherits |   |
|  |                                                     (TCP)     |   |
|  |                                                                |   |
|  |  Handshake RTT   1-2         0           0-1         1+       |   |
|  |                                                                |   |
|  |  Encryption      No*         No          Yes         No*      |   |
|  |                  (TLS)                   (built-in)  (WSS)    |   |
|  |                                                                |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 19.2: TCP DEEP DIVE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TCP 3-WAY HANDSHAKE                                                   |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Client                                Server                   |  |
|  |    |                                     |                      |  |
|  |    |                                     | LISTEN               |  |
|  |    |                                     |                      |  |
|  |    |---- SYN (seq=x) ------------------->|                      |  |
|  |    |     "I want to connect"             |                      |  |
|  |    |                                     |                      |  |
|  |    |<--- SYN-ACK (seq=y, ack=x+1) -------|                      |  |
|  |    |     "OK, I acknowledge your SYN"    |                      |  |
|  |    |                                     |                      |  |
|  |    |---- ACK (ack=y+1) ----------------->|                      |  |
|  |    |     "I acknowledge your SYN"        |                      |  |
|  |    |                                     |                      |  |
|  |    |        CONNECTION ESTABLISHED       |                      |  |
|  |    |<======== Data Transfer ===========>|                      |  |
|  |                                                                 |  |
|  |  WHY 3-WAY?                                                    |  |
|  |  * Synchronize sequence numbers                               |  |
|  |  * Confirm both sides can send AND receive                   |  |
|  |  * Prevent old duplicate connections                         |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### TCP 4-WAY TERMINATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CONNECTION CLOSE                                                      |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Client                                Server                   |  |
|  |    |                                     |                      |  |
|  |    |---- FIN --------------------------->|                      |  |
|  |    |     "I'm done sending"              |                      |  |
|  |    |                                     |                      |  |
|  |    |<--- ACK ----------------------------|                      |  |
|  |    |     "Got it"                        |                      |  |
|  |    |                                     |                      |  |
|  |    |     (Server may still send data)    |                      |  |
|  |    |                                     |                      |  |
|  |    |<--- FIN ----------------------------|                      |  |
|  |    |     "I'm done too"                  |                      |  |
|  |    |                                     |                      |  |
|  |    |---- ACK --------------------------->|                      |  |
|  |    |     "Got it"                        |                      |  |
|  |    |                                     |                      |  |
|  |    |        CONNECTION CLOSED            |                      |  |
|  |                                                                 |  |
|  |  TIME_WAIT: Client waits 2×MSL (Max Segment Lifetime)         |  |
|  |  to ensure all packets are gone from network                  |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### TCP FLOW CONTROL (Sliding Window)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SLIDING WINDOW MECHANISM                                              |
|                                                                         |
|  Receiver advertises how much data it can buffer (rwnd)               |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Sender's view of data:                                        |  |
|  |                                                                 |  |
|  |  [ACKed][ACKed][Sent][Sent][Sent][Can Send][Can Send][Blocked] |  |
|  |  +-------------++-------------------------++----------------+  |  |
|  |     Already      Outstanding (in flight)     Waiting for       |  |
|  |     confirmed                                window space      |  |
|  |                                                                 |  |
|  |  <---------------- Window Size ------------------>              |  |
|  |                                                                 |  |
|  |  Receiver ACKs with: "Got bytes 1-1000, window=5000"          |  |
|  |  Sender can have up to 5000 bytes in flight                   |  |
|  |                                                                 |  |
|  |  If receiver buffer fills: window=0 (sender pauses)           |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  PREVENTS: Fast sender overwhelming slow receiver                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### TCP CONGESTION CONTROL

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CONGESTION CONTROL PHASES                                             |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Congestion                                                    |  |
|  |  Window (cwnd)                                                 |  |
|  |       ^                                                        |  |
|  |       |                           /\                          |  |
|  |       |                          /  \  Congestion!            |  |
|  |       |                         /    \ (packet loss)          |  |
|  |       |                        /      \                        |  |
|  |       |                       /        \ ssthresh halved      |  |
|  |       |                ------+----------\-----------          |  |
|  |       |              /  Congestion        \                    |  |
|  |       |             /   Avoidance          \                   |  |
|  |       |            /   (linear increase)    \                  |  |
|  |       |    ////// ssthresh                   \                 |  |
|  |       |   / Slow Start                        \----           |  |
|  |       |  / (exponential)                                      |  |
|  |       |/                                                       |  |
|  |       +----------------------------------------------> Time   |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  PHASES:                                                               |
|                                                                         |
|  1. SLOW START                                                        |
|     * Start with cwnd = 1 MSS (Max Segment Size)                     |
|     * Double cwnd every RTT (exponential growth)                     |
|     * Until: cwnd reaches ssthresh OR packet loss                   |
|                                                                         |
|  2. CONGESTION AVOIDANCE                                              |
|     * Increase cwnd by 1 MSS per RTT (linear growth)                |
|     * More conservative than slow start                              |
|                                                                         |
|  3. ON PACKET LOSS                                                     |
|     Fast Retransmit: 3 duplicate ACKs -> retransmit immediately       |
|     Fast Recovery: ssthresh = cwnd/2, cwnd = ssthresh + 3           |
|     Timeout: ssthresh = cwnd/2, cwnd = 1 (back to slow start)       |
|                                                                         |
|  ALGORITHMS: Tahoe, Reno, NewReno, CUBIC (Linux default), BBR       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### TCP HEAD-OF-LINE BLOCKING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE PROBLEM                                                           |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Packets sent: [1][2][3][4][5][6]                              |  |
|  |                                                                 |  |
|  |  Packets received: [1][2][X][4][5][6]                          |  |
|  |                        |                                        |  |
|  |                   Packet 3 lost                                |  |
|  |                                                                 |  |
|  |  Application sees: [1][2]... WAITING...                       |  |
|  |                                                                 |  |
|  |  Even though 4,5,6 are received, TCP must deliver IN ORDER    |  |
|  |  Application waits for packet 3 retransmission                |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  WHY IT MATTERS:                                                        |
|  * HTTP/2 multiplexing on single TCP = all streams blocked           |
|  * One lost packet delays ALL concurrent requests                    |
|                                                                         |
|  SOLUTION: QUIC (UDP-based, per-stream ordering)                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 19.3: UDP DEEP DIVE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  UDP HEADER (8 bytes only!)                                           |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  0                   1                   2                   3  |  |
|  |  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1|  |
|  |  +---------------------------+---------------------------+      |  |
|  |  |     Source Port (16)      |   Destination Port (16)   |     |  |
|  |  +---------------------------+---------------------------+      |  |
|  |  |      Length (16)          |      Checksum (16)        |     |  |
|  |  +---------------------------+---------------------------+      |  |
|  |  |                        Data                           |      |  |
|  |  +-------------------------------------------------------+      |  |
|  |                                                                 |  |
|  |  Compare to TCP: 20+ bytes header                              |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  UDP CHARACTERISTICS:                                                   |
|                                                                         |
|  [x] No connection setup (send immediately)                             |
|  [x] No state maintained                                                |
|  [x] Minimal header overhead (8 bytes vs 20+ TCP)                       |
|  [x] No flow/congestion control (can send as fast as possible)         |
|  [x] Supports broadcast and multicast                                   |
|                                                                         |
|  [ ] No delivery guarantee                                              |
|  [ ] No ordering guarantee                                              |
|  [ ] No duplicate protection                                            |
|  [ ] No fragmentation handling (application must handle)               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### UDP USE CASES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHEN TO USE UDP                                                       |
|                                                                         |
|  1. DNS                                                                 |
|     * Small queries, quick responses                                  |
|     * Retry at application level if lost                             |
|                                                                         |
|  2. STREAMING (Video/Audio)                                            |
|     * Late packet = useless (already played that frame)              |
|     * Skip and continue better than wait                             |
|                                                                         |
|  3. GAMING                                                              |
|     * Real-time state updates                                         |
|     * Latest state matters, old state doesn't                        |
|     * Low latency critical                                            |
|                                                                         |
|  4. VOIP                                                                |
|     * Real-time audio                                                 |
|     * Packet loss = brief glitch (acceptable)                        |
|     * Retransmit = delayed audio (worse)                             |
|                                                                         |
|  5. QUIC (HTTP/3)                                                       |
|     * Build reliable protocol on top of UDP                          |
|     * Get benefits of both worlds                                    |
|                                                                         |
|  6. IoT / TELEMETRY                                                     |
|     * Frequent small updates                                          |
|     * Missing one reading is fine                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 19.4: TLS DEEP DIVE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS TLS?                                                          |
|                                                                         |
|  Transport Layer Security - provides:                                  |
|  * Encryption (privacy)                                               |
|  * Authentication (verify server identity)                            |
|  * Integrity (detect tampering)                                       |
|                                                                         |
|  TLS 1.2 vs TLS 1.3                                                    |
|  +----------------------------------------------------------------+   |
|  |                                                                |   |
|  |  Feature            TLS 1.2          TLS 1.3                  |   |
|  |  ------------------------------------------------------------ |   |
|  |  Handshake RTT      2 RTT            1 RTT (0-RTT resumption) |   |
|  |  Key Exchange       RSA/DH/ECDH      ECDH only (forward sec.) |   |
|  |  Cipher Suites      Many (some weak) Few (all strong)         |   |
|  |  Encryption         AES-CBC/GCM      AES-GCM, ChaCha20        |   |
|  |                                                                |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### TLS 1.3 HANDSHAKE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TLS 1.3 HANDSHAKE (1-RTT)                                            |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Client                                Server                   |  |
|  |    |                                     |                      |  |
|  |    |---- ClientHello ------------------->|                      |  |
|  |    |     * Supported cipher suites       |                      |  |
|  |    |     * Key share (ECDH public key)   |                      |  |
|  |    |     * Random                        |                      |  |
|  |    |                                     |                      |  |
|  |    |<--- ServerHello --------------------|                      |  |
|  |    |     * Chosen cipher suite           |                      |  |
|  |    |     * Key share (ECDH public key)   |                      |  |
|  |    |<--- {EncryptedExtensions} ----------|                      |  |
|  |    |<--- {Certificate} ------------------|                      |  |
|  |    |<--- {CertificateVerify} ------------|                      |  |
|  |    |<--- {Finished} ---------------------|                      |  |
|  |    |                                     |                      |  |
|  |    |     Both compute shared secret      |                      |  |
|  |    |     from ECDH key exchange         |                      |  |
|  |    |                                     |                      |  |
|  |    |---- {Finished} -------------------->|                      |  |
|  |    |                                     |                      |  |
|  |    |<=== Encrypted Application Data ===>|                      |  |
|  |                                                                 |  |
|  |  {} = encrypted                                                |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  0-RTT RESUMPTION:                                                      |
|  If client has previous session, can send data with first message!   |
|  (Risk: replay attacks, so only safe for idempotent requests)        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CERTIFICATES AND KEYS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PUBLIC KEY INFRASTRUCTURE (PKI)                                       |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |                    Certificate Authority (CA)                  |  |
|  |                    (DigiCert, Let's Encrypt)                   |  |
|  |                             |                                   |  |
|  |                    Signs certificates                          |  |
|  |                             |                                   |  |
|  |                             v                                   |  |
|  |                    +-----------------+                         |  |
|  |                    |   Certificate   |                         |  |
|  |                    |                 |                         |  |
|  |                    | * Domain name   |                         |  |
|  |                    | * Public key    |                         |  |
|  |                    | * Issuer (CA)   |                         |  |
|  |                    | * Expiry date   |                         |  |
|  |                    | * CA signature  |                         |  |
|  |                    |                 |                         |  |
|  |                    +--------+--------+                         |  |
|  |                             |                                   |  |
|  |                    Installed on server                         |  |
|  |                             |                                   |  |
|  |                             v                                   |  |
|  |  +---------------------------------------------------------+  |  |
|  |  |                    Server                               |  |  |
|  |  |                                                         |  |  |
|  |  |  Private Key (secret, never leaves server)             |  |  |
|  |  |  Certificate (public, sent to clients)                 |  |  |
|  |  |                                                         |  |  |
|  |  +---------------------------------------------------------+  |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  CERTIFICATE CHAIN:                                                     |
|                                                                         |
|  Root CA (trusted by browsers)                                        |
|      |                                                                 |
|      +-- Intermediate CA (signed by Root)                             |
|              |                                                         |
|              +-- Server Certificate (signed by Intermediate)          |
|                                                                         |
|  Client verifies chain up to trusted root                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### FORWARD SECRECY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PERFECT FORWARD SECRECY (PFS)                                        |
|                                                                         |
|  Even if server's private key is compromised LATER,                   |
|  past recorded traffic cannot be decrypted.                           |
|                                                                         |
|  HOW IT WORKS:                                                          |
|  * Ephemeral keys generated for each session                         |
|  * Shared secret derived from ephemeral keys                         |
|  * Ephemeral keys discarded after session                            |
|                                                                         |
|  WITHOUT PFS (RSA key exchange):                                       |
|  1. Server private key compromised                                    |
|  2. Attacker decrypts recorded session                               |
|  3. All past traffic exposed                                          |
|                                                                         |
|  WITH PFS (ECDHE):                                                      |
|  1. Server private key compromised                                    |
|  2. Attacker cannot decrypt past sessions                            |
|  3. Each session used unique ephemeral keys                          |
|                                                                         |
|  TLS 1.3 REQUIRES forward secrecy (ECDHE only)                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 19.5: HTTP/3 AND QUIC DEEP DIVE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  QUIC (Quick UDP Internet Connections)                                 |
|                                                                         |
|  HTTP/3 = HTTP over QUIC (instead of TCP)                             |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  HTTP/1.1, HTTP/2 Stack:       HTTP/3 Stack:                   |  |
|  |                                                                 |  |
|  |  +-----------------+           +-----------------+             |  |
|  |  |    HTTP         |           |    HTTP/3       |             |  |
|  |  +-----------------+           +-----------------+             |  |
|  |  |    TLS          |           |    QUIC         |             |  |
|  |  +-----------------+           |  (TLS built-in) |             |  |
|  |  |    TCP          |           +-----------------+             |  |
|  |  +-----------------+           |    UDP          |             |  |
|  |  |    IP           |           +-----------------+             |  |
|  |  +-----------------+           |    IP           |             |  |
|  |                                +-----------------+             |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUIC BENEFITS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. FASTER CONNECTION ESTABLISHMENT                                    |
|  ====================================                                   |
|                                                                         |
|  TCP + TLS:                                                            |
|  * TCP handshake: 1 RTT                                               |
|  * TLS handshake: 1-2 RTT                                             |
|  * Total: 2-3 RTT before first data                                   |
|                                                                         |
|  QUIC:                                                                  |
|  * Combined handshake: 1 RTT                                          |
|  * 0-RTT for resumed connections!                                     |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. NO HEAD-OF-LINE BLOCKING                                           |
|  ============================                                           |
|                                                                         |
|  TCP: One lost packet blocks ALL streams                              |
|  QUIC: Lost packet only blocks THAT stream                           |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  HTTP/2 over TCP (packet 3 lost):                              |  |
|  |                                                                 |  |
|  |  Stream A: [1][2][BLOCKED][BLOCKED][BLOCKED]                  |  |
|  |  Stream B: [1][2][BLOCKED][BLOCKED][BLOCKED]                  |  |
|  |  Stream C: [1][2][BLOCKED][BLOCKED][BLOCKED]                  |  |
|  |                                                                 |  |
|  |  HTTP/3 over QUIC (stream A packet lost):                     |  |
|  |                                                                 |  |
|  |  Stream A: [1][2][BLOCKED]                                    |  |
|  |  Stream B: [1][2][3][4][5] [x] continues                       |  |
|  |  Stream C: [1][2][3][4][5] [x] continues                       |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. CONNECTION MIGRATION                                               |
|  ========================                                               |
|                                                                         |
|  TCP identified by: (src_ip, src_port, dst_ip, dst_port)             |
|  If IP changes (WiFi -> cellular), connection breaks                  |
|                                                                         |
|  QUIC identified by: Connection ID (random token)                    |
|  IP can change, connection continues!                                 |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  4. ALWAYS ENCRYPTED                                                   |
|  ===================                                                    |
|                                                                         |
|  TLS 1.3 built into QUIC                                              |
|  Cannot be downgraded or disabled                                     |
|  Even packet numbers are encrypted                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 19.6: gRPC DEEP DIVE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  gRPC ARCHITECTURE                                                     |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  +-------------+                       +-------------+         |  |
|  |  |   Client    |                       |   Server    |         |  |
|  |  |             |                       |             |         |  |
|  |  | +---------+ |                       | +---------+ |         |  |
|  |  | |  Stub   | |                       | | Service | |         |  |
|  |  | | (gen'd) | |                       | |  Impl   | |         |  |
|  |  | +----+----+ |                       | +----^----+ |         |  |
|  |  |      |      |                       |      |      |         |  |
|  |  | +----v----+ |    +-----------+     | +----+----+ |         |  |
|  |  | | Channel | |<-->|  HTTP/2   |<--->| | Server  | |         |  |
|  |  | |         | |    | (binary)  |     | | Skeleton| |         |  |
|  |  | +---------+ |    +-----------+     | +---------+ |         |  |
|  |  |             |                       |             |         |  |
|  |  +-------------+                       +-------------+         |  |
|  |                                                                 |  |
|  |  Generated from .proto files:                                  |  |
|  |  * Client stub (call like local function)                     |  |
|  |  * Server skeleton (implement interface)                      |  |
|  |  * Message serializers (Protobuf)                             |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### gRPC STREAMING MODES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FOUR COMMUNICATION PATTERNS                                           |
|                                                                         |
|  1. UNARY (Simple RPC)                                                 |
|  ========================                                               |
|                                                                         |
|  Client sends ONE request, server sends ONE response                  |
|                                                                         |
|  rpc GetUser(UserRequest) returns (User);                             |
|                                                                         |
|  Client ---- Request ----> Server                                     |
|  Client <--- Response ---- Server                                     |
|                                                                         |
|  USE: Simple queries, CRUD operations                                 |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. SERVER STREAMING                                                   |
|  =======================                                                |
|                                                                         |
|  Client sends ONE request, server sends STREAM of responses           |
|                                                                         |
|  rpc ListUsers(ListRequest) returns (stream User);                    |
|                                                                         |
|  Client ---- Request ----> Server                                     |
|  Client <--- Response 1 --- Server                                    |
|  Client <--- Response 2 --- Server                                    |
|  Client <--- Response 3 --- Server                                    |
|  Client <--- (end) -------- Server                                    |
|                                                                         |
|  USE: Fetching large datasets, real-time updates, logs                |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. CLIENT STREAMING                                                   |
|  =======================                                                |
|                                                                         |
|  Client sends STREAM of requests, server sends ONE response           |
|                                                                         |
|  rpc UploadFile(stream FileChunk) returns (UploadStatus);            |
|                                                                         |
|  Client ---- Chunk 1 ----> Server                                     |
|  Client ---- Chunk 2 ----> Server                                     |
|  Client ---- Chunk 3 ----> Server                                     |
|  Client ---- (end) -----> Server                                      |
|  Client <--- Response ---- Server                                     |
|                                                                         |
|  USE: File upload, batch processing, aggregation                     |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  4. BIDIRECTIONAL STREAMING                                            |
|  ===============================                                        |
|                                                                         |
|  Both client and server send STREAMS (simultaneously)                 |
|                                                                         |
|  rpc Chat(stream ChatMessage) returns (stream ChatMessage);           |
|                                                                         |
|  Client ================================== Server                     |
|         ---- Message ---->                                            |
|         <--- Message ----                                             |
|         ---- Message ---->                                            |
|         ---- Message ---->                                            |
|         <--- Message ----                                             |
|  ================================================                     |
|                                                                         |
|  USE: Chat, gaming, collaborative editing                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### gRPC FEATURES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KEY gRPC FEATURES                                                     |
|                                                                         |
|  1. PROTOCOL BUFFERS (Protobuf)                                       |
|     * Binary serialization (5-10x smaller than JSON)                 |
|     * Strongly typed schema                                           |
|     * Code generation for 10+ languages                              |
|     * Schema evolution (backward compatible)                         |
|                                                                         |
|  2. HTTP/2                                                              |
|     * Multiplexing                                                    |
|     * Header compression                                              |
|     * Binary framing                                                  |
|     * Server push (for streaming)                                    |
|                                                                         |
|  3. DEADLINES/TIMEOUTS                                                 |
|     * Client sets deadline for RPC                                   |
|     * Propagated across service calls                                |
|     * Server can check if deadline exceeded                          |
|                                                                         |
|  4. CANCELLATION                                                       |
|     * Client can cancel RPC                                          |
|     * Propagates to server (stop work)                               |
|                                                                         |
|  5. INTERCEPTORS                                                       |
|     * Middleware for logging, auth, metrics                          |
|     * Client-side and server-side                                    |
|                                                                         |
|  6. LOAD BALANCING                                                     |
|     * Client-side LB built-in                                        |
|     * Works with service discovery                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 19.7: WEBRTC FUNDAMENTALS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS WEBRTC?                                                       |
|                                                                         |
|  Real-time communication (audio, video, data) directly between        |
|  browsers/apps, without going through a server (peer-to-peer).        |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  WEBRTC PROTOCOL STACK                                         |  |
|  |                                                                 |  |
|  |  +---------------------------------------------------------+  |  |
|  |  |              Application (getUserMedia, etc.)           |  |  |
|  |  +---------------------------------------------------------+  |  |
|  |  |  SRTP (audio/video)  |  SCTP (data channel)            |  |  |
|  |  +----------------------+----------------------------------+  |  |
|  |  |              DTLS (encryption)                          |  |  |
|  |  +---------------------------------------------------------+  |  |
|  |  |              ICE (connectivity)                         |  |  |
|  |  +---------------------------------------------------------+  |  |
|  |  |              UDP (transport)                            |  |  |
|  |  +---------------------------------------------------------+  |  |
|  |                                                                 |  |
|  |  PROTOCOLS:                                                    |  |
|  |  * ICE: Find best path to connect peers (NAT traversal)       |  |
|  |  * STUN: Discover public IP address                           |  |
|  |  * TURN: Relay when direct connection impossible              |  |
|  |  * DTLS: Key exchange and encryption setup                    |  |
|  |  * SRTP: Encrypted real-time media                            |  |
|  |  * SCTP: Reliable/unreliable data channels                    |  |
|  |  * SDP: Describe media session parameters                     |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WEBRTC CONNECTION FLOW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WEBRTC PEER CONNECTION SETUP                                          |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Peer A                Signaling Server              Peer B    |  |
|  |    |                         |                          |      |  |
|  |    |-- 1. Create Offer (SDP) |                          |      |  |
|  |    |                         |                          |      |  |
|  |    |-- 2. Send Offer ------->|                          |      |  |
|  |    |                         |-- 3. Forward Offer ----->|      |  |
|  |    |                         |                          |      |  |
|  |    |                         |<- 4. Send Answer --------|      |  |
|  |    |<- 5. Forward Answer ----|                          |      |  |
|  |    |                         |                          |      |  |
|  |    |-- 6. ICE Candidates --->|                          |      |  |
|  |    |                         |-- 7. Forward ----------->|      |  |
|  |    |<------------------------------- 8. ICE Candidates -|      |  |
|  |    |                         |                          |      |  |
|  |    |   9. ICE checks connectivity options               |      |  |
|  |    |                                                    |      |  |
|  |    |<=========== 10. DTLS Handshake ===================>|      |  |
|  |    |                                                    |      |  |
|  |    |<=========== 11. SRTP Media Flow =================>|      |  |
|  |    |                (peer-to-peer!)                     |      |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  NOTE: Signaling server only for setup.                               |
|  Media flows directly between peers (usually).                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WEBRTC USE CASES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WEBRTC APPLICATIONS                                                   |
|                                                                         |
|  1. VIDEO CONFERENCING                                                 |
|     * Google Meet, Zoom (web client)                                  |
|     * 1:1 or small group P2P                                          |
|     * Larger groups: SFU (Selective Forwarding Unit)                 |
|                                                                         |
|  2. SCREEN SHARING                                                     |
|     * getDisplayMedia() API                                           |
|                                                                         |
|  3. FILE TRANSFER                                                      |
|     * Data channels (SCTP)                                            |
|     * P2P, no server storage                                          |
|                                                                         |
|  4. GAMING                                                              |
|     * Low-latency game state sync                                     |
|     * Voice chat                                                      |
|                                                                         |
|  5. IOT / REMOTE ACCESS                                                |
|     * Camera streaming                                                |
|     * Remote desktop                                                  |
|                                                                         |
|  WEBRTC vs WEBSOCKET:                                                   |
|  +----------------------------------------------------------------+   |
|  |                                                                |   |
|  |  Feature          WebSocket        WebRTC                     |   |
|  |  ------------------------------------------------------------ |   |
|  |  Transport        TCP              UDP (usually)              |   |
|  |  Path             Client-Server    Peer-to-Peer               |   |
|  |  Latency          Medium           Low                        |   |
|  |  Media optimized  No               Yes (SRTP)                 |   |
|  |  NAT traversal    N/A              Built-in (ICE)             |   |
|  |  Use case         Chat, updates    Video, audio, gaming       |   |
|  |                                                                |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 19.8: PROTOCOL SELECTION GUIDE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CHOOSING THE RIGHT PROTOCOL                                           |
|                                                                         |
|  +----------------------------------------------------------------+   |
|  |                                                                |   |
|  |  Use Case                    Recommended Protocol             |   |
|  |  ------------------------------------------------------------ |   |
|  |                                                                |   |
|  |  External API                REST (HTTP/1.1 or HTTP/2)        |   |
|  |                                                                |   |
|  |  Internal microservices      gRPC (HTTP/2)                    |   |
|  |                                                                |   |
|  |  Real-time chat              WebSocket                        |   |
|  |                                                                |   |
|  |  Server notifications        SSE or WebSocket                 |   |
|  |                                                                |   |
|  |  Video/audio call            WebRTC                           |   |
|  |                                                                |   |
|  |  Gaming (real-time)          UDP or WebRTC                    |   |
|  |                                                                |   |
|  |  File streaming              HTTP/2 or gRPC streaming         |   |
|  |                                                                |   |
|  |  IoT telemetry               MQTT or UDP                      |   |
|  |                                                                |   |
|  |  Mobile apps (lossy net)     HTTP/3 (QUIC)                    |   |
|  |                                                                |   |
|  |  Browser (modern)            HTTP/2, upgrade to HTTP/3        |   |
|  |                                                                |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 19

