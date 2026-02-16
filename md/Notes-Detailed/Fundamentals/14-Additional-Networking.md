# CHAPTER 14: ADDITIONAL NETWORKING FUNDAMENTALS
*OSI Model, IP Addressing, Checksums, and More*

This chapter covers networking fundamentals often asked in system design
interviews: OSI Model, IP addressing, and data integrity mechanisms.

## SECTION 14.1: OSI MODEL (Open Systems Interconnection)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE 7 LAYERS OF OSI MODEL                                             |
|                                                                         |
|  The OSI model is a conceptual framework that describes how data      |
|  moves from one computer to another over a network.                    |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Layer 7: APPLICATION                                          |  |
|  |  ---------------------                                          |  |
|  |  What user interacts with                                      |  |
|  |  Protocols: HTTP, HTTPS, FTP, SMTP, DNS, SSH, WebSocket       |  |
|  |  Data Unit: Data                                               |  |
|  |  Example: Web browser, email client                           |  |
|  |                                                                 |  |
|  |  ------------------------------------------------------------ |  |
|  |                                                                 |  |
|  |  Layer 6: PRESENTATION                                         |  |
|  |  -----------------------                                        |  |
|  |  Data formatting, encryption, compression                      |  |
|  |  Protocols: SSL/TLS, JPEG, GIF, MPEG, ASCII, JSON             |  |
|  |  Data Unit: Data                                               |  |
|  |  Example: SSL encryption, data serialization                  |  |
|  |                                                                 |  |
|  |  ------------------------------------------------------------ |  |
|  |                                                                 |  |
|  |  Layer 5: SESSION                                              |  |
|  |  -----------------                                              |  |
|  |  Manages sessions/connections between applications             |  |
|  |  Protocols: NetBIOS, RPC, PPTP                                |  |
|  |  Data Unit: Data                                               |  |
|  |  Example: Login session, API session tokens                   |  |
|  |                                                                 |  |
|  |  ------------------------------------------------------------ |  |
|  |                                                                 |  |
|  |  Layer 4: TRANSPORT                                            |  |
|  |  -------------------                                            |  |
|  |  Reliable data transfer, error recovery, flow control         |  |
|  |  Protocols: TCP, UDP                                          |  |
|  |  Data Unit: Segment (TCP) / Datagram (UDP)                    |  |
|  |  Example: Port numbers (80, 443), connection management       |  |
|  |                                                                 |  |
|  |  ------------------------------------------------------------ |  |
|  |                                                                 |  |
|  |  Layer 3: NETWORK                                              |  |
|  |  -----------------                                              |  |
|  |  Routing, logical addressing, path determination              |  |
|  |  Protocols: IP, ICMP, OSPF, BGP                               |  |
|  |  Data Unit: Packet                                            |  |
|  |  Example: IP addresses, routers                               |  |
|  |                                                                 |  |
|  |  ------------------------------------------------------------ |  |
|  |                                                                 |  |
|  |  Layer 2: DATA LINK                                            |  |
|  |  -------------------                                            |  |
|  |  Physical addressing, frame synchronization, error detection  |  |
|  |  Protocols: Ethernet, Wi-Fi (802.11), PPP, ARP                |  |
|  |  Data Unit: Frame                                             |  |
|  |  Example: MAC addresses, switches, NICs                       |  |
|  |                                                                 |  |
|  |  ------------------------------------------------------------ |  |
|  |                                                                 |  |
|  |  Layer 1: PHYSICAL                                             |  |
|  |  ------------------                                             |  |
|  |  Physical transmission of raw bits                            |  |
|  |  Media: Cables, fiber optics, radio waves                     |  |
|  |  Data Unit: Bits                                              |  |
|  |  Example: Ethernet cables, hubs, repeaters                    |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### OSI MODEL VISUAL

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DATA FLOW THROUGH OSI LAYERS                                          |
|                                                                         |
|  SENDER                                    RECEIVER                     |
|                                                                         |
|  +-------------+                          +-------------+              |
|  | Application |  ------- Data ---------> | Application |              |
|  +-------------+                          +-------------+              |
|  |Presentation |  ------- Data ---------> |Presentation |              |
|  +-------------+                          +-------------+              |
|  |   Session   |  ------- Data ---------> |   Session   |              |
|  +-------------+                          +-------------+              |
|  |  Transport  |  ------ Segment -------> |  Transport  |              |
|  +-------------+                          +-------------+              |
|  |   Network   |  ------ Packet --------> |   Network   |              |
|  +-------------+                          +-------------+              |
|  |  Data Link  |  ------ Frame ---------> |  Data Link  |              |
|  +-------------+                          +-------------+              |
|  |  Physical   |  ------ Bits ----------> |  Physical   |              |
|  +-------------+                          +-------------+              |
|        |                                         ^                      |
|        +---------> Physical Medium --------------+                      |
|                    (cables, radio)                                      |
|                                                                         |
|  ENCAPSULATION (Sending):                                              |
|  Each layer adds its header -> Data becomes larger                      |
|                                                                         |
|  [App Data]                                                            |
|  [Transport Header | App Data]                                         |
|  [Network Header | Transport Header | App Data]                        |
|  [Data Link Header | Network | Transport | App Data | Trailer]        |
|                                                                         |
|  DECAPSULATION (Receiving):                                            |
|  Each layer removes its header -> Data becomes smaller                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### OSI vs TCP/IP MODEL

```
+-------------------------------------------------------------------------+
|                                                                         |
|  OSI MODEL (7 Layers)          TCP/IP MODEL (4 Layers)                 |
|                                                                         |
|  +---------------------+       +---------------------+                 |
|  |    Application      |       |                     |                 |
|  +---------------------+       |    Application      |                 |
|  |    Presentation     |  ---> |   (HTTP, FTP, DNS)  |                 |
|  +---------------------+       |                     |                 |
|  |    Session          |       +---------------------+                 |
|  +---------------------+       +---------------------+                 |
|  |    Transport        |  ---> |    Transport        |                 |
|  |    (TCP/UDP)        |       |    (TCP/UDP)        |                 |
|  +---------------------+       +---------------------+                 |
|  |    Network          |  ---> +---------------------+                 |
|  |    (IP)             |       |    Internet         |                 |
|  +---------------------+       |    (IP)             |                 |
|  |    Data Link        |       +---------------------+                 |
|  +---------------------+  ---> +---------------------+                 |
|  |    Physical         |       |  Network Access     |                 |
|  +---------------------+       |  (Ethernet, Wi-Fi)  |                 |
|                                +---------------------+                 |
|                                                                         |
|  TCP/IP is the practical model used on the internet                   |
|  OSI is the theoretical/reference model                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### OSI IN SYSTEM DESIGN CONTEXT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHICH LAYERS MATTER IN SYSTEM DESIGN?                                 |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  LAYER 7 (Application) - VERY IMPORTANT                        |  |
|  |  * API design (REST, GraphQL, gRPC)                           |  |
|  |  * HTTP methods, status codes                                 |  |
|  |  * WebSockets                                                 |  |
|  |  * L7 Load Balancers (can route by URL, headers)             |  |
|  |                                                                 |  |
|  |  LAYER 4 (Transport) - IMPORTANT                               |  |
|  |  * TCP vs UDP choice                                          |  |
|  |  * Connection management                                      |  |
|  |  * Port numbers                                               |  |
|  |  * L4 Load Balancers (route by IP/port)                      |  |
|  |                                                                 |  |
|  |  LAYER 3 (Network) - MODERATELY IMPORTANT                      |  |
|  |  * IP addressing                                              |  |
|  |  * Routing between data centers                               |  |
|  |  * VPC, subnets in cloud                                     |  |
|  |                                                                 |  |
|  |  LAYERS 1-2 - Usually abstracted by cloud providers           |  |
|  |  * You rarely think about physical cables                    |  |
|  |  * MAC addresses handled by infrastructure                   |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  COMMON INTERVIEW QUESTIONS:                                           |
|                                                                         |
|  Q: What's the difference between L4 and L7 load balancers?           |
|  A: L4 routes by IP/port (fast, no inspection)                        |
|     L7 routes by HTTP content (URL, headers, cookies)                 |
|                                                                         |
|  Q: Where does SSL/TLS operate?                                        |
|  A: Between Layer 4 (Transport) and Layer 7 (Application)             |
|     Sometimes called Layer 6 (Presentation)                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 14.2: IP ADDRESSES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS AN IP ADDRESS?                                                |
|                                                                         |
|  A unique identifier for a device on a network.                        |
|  Like a postal address for computers.                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### IPv4 (Internet Protocol version 4)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  IPv4 FORMAT                                                            |
|                                                                         |
|  32 bits, written as 4 octets separated by dots                        |
|                                                                         |
|  Example: 192.168.1.100                                                |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |     192    .    168    .     1     .    100                    |  |
|  |   +------+   +------+   +------+   +------+                    |  |
|  |   |8 bits|   |8 bits|   |8 bits|   |8 bits|                    |  |
|  |   +------+   +------+   +------+   +------+                    |  |
|  |                                                                 |  |
|  |   Each octet: 0-255 (2^8 = 256 values)                        |  |
|  |   Total addresses: 2^32 = ~4.3 billion                        |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  IPv4 ADDRESS CLASSES (Historical)                                     |
|                                                                         |
|  +--------+-----------------+---------------------------------------+ |
|  | Class  | First Octet    | Purpose                               | |
|  +--------+-----------------+---------------------------------------+ |
|  | A      | 1-126          | Large networks (16M hosts)            | |
|  | B      | 128-191        | Medium networks (65K hosts)           | |
|  | C      | 192-223        | Small networks (254 hosts)            | |
|  | D      | 224-239        | Multicast                             | |
|  | E      | 240-255        | Reserved/Experimental                 | |
|  +--------+-----------------+---------------------------------------+ |
|                                                                         |
|  PRIVATE IP RANGES (Not routable on internet)                          |
|                                                                         |
|  10.0.0.0    - 10.255.255.255   (Class A, /8)                        |
|  172.16.0.0  - 172.31.255.255   (Class B, /12)                       |
|  192.168.0.0 - 192.168.255.255  (Class C, /16)                       |
|                                                                         |
|  SPECIAL ADDRESSES:                                                     |
|  127.0.0.1     - Localhost (loopback)                                 |
|  0.0.0.0       - All interfaces / unspecified                         |
|  255.255.255.255 - Broadcast                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### IPv6 (Internet Protocol version 6)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  IPv6 FORMAT                                                            |
|                                                                         |
|  128 bits, written as 8 groups of 4 hex digits                        |
|                                                                         |
|  Example: 2001:0db8:85a3:0000:0000:8a2e:0370:7334                     |
|                                                                         |
|  Shortened: 2001:db8:85a3::8a2e:370:7334                              |
|  (leading zeros removed, :: replaces consecutive zero groups)         |
|                                                                         |
|  Total addresses: 2^128 = 340 undecillion                             |
|  (enough for every grain of sand on Earth)                            |
|                                                                         |
|  WHY IPv6?                                                              |
|  * IPv4 exhaustion (only 4.3 billion addresses)                       |
|  * IoT explosion (billions of devices need IPs)                       |
|  * Better security (IPSec built-in)                                   |
|  * No NAT needed (every device gets public IP)                        |
|                                                                         |
|  SPECIAL ADDRESSES:                                                     |
|  ::1              - Localhost                                          |
|  ::               - Unspecified (like 0.0.0.0)                        |
|  fe80::/10        - Link-local                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SUBNETTING AND CIDR

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CIDR (Classless Inter-Domain Routing)                                 |
|                                                                         |
|  Format: IP_ADDRESS / PREFIX_LENGTH                                    |
|                                                                         |
|  Example: 192.168.1.0/24                                               |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  192.168.1.0/24                                                |  |
|  |                                                                 |  |
|  |  11000000.10101000.00000001.00000000                          |  |
|  |  +--------------------------++------+                          |  |
|  |       Network (24 bits)       Host                             |  |
|  |                               (8 bits)                         |  |
|  |                                                                 |  |
|  |  Network: 192.168.1.x                                         |  |
|  |  Hosts: 192.168.1.1 to 192.168.1.254 (254 usable)            |  |
|  |  Broadcast: 192.168.1.255                                     |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  COMMON CIDR BLOCKS:                                                    |
|                                                                         |
|  /8   - 16,777,216 addresses (Class A)                                |
|  /16  - 65,536 addresses (Class B)                                    |
|  /24  - 256 addresses (Class C)                                       |
|  /32  - 1 address (single host)                                       |
|                                                                         |
|  CLOUD VPC EXAMPLE (AWS):                                               |
|                                                                         |
|  VPC: 10.0.0.0/16 (65,536 addresses)                                  |
|    +-- Public Subnet: 10.0.1.0/24 (256 addresses)                    |
|    +-- Private Subnet: 10.0.2.0/24 (256 addresses)                   |
|    +-- Database Subnet: 10.0.3.0/24 (256 addresses)                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### NAT (Network Address Translation)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NAT translates private IPs to public IPs                              |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  PRIVATE NETWORK                       INTERNET                |  |
|  |                                                                 |  |
|  |  Device A: 192.168.1.10 --+                                    |  |
|  |                           |                                     |  |
|  |  Device B: 192.168.1.11 --+--> NAT --> 203.0.113.50 --> Web  |  |
|  |                           |   Router   (Public IP)              |  |
|  |  Device C: 192.168.1.12 --+                                    |  |
|  |                                                                 |  |
|  |  All devices share ONE public IP!                             |  |
|  |  Router tracks which device made which request                |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  NAT TYPES:                                                             |
|                                                                         |
|  SNAT (Source NAT): Private -> Public (outbound)                       |
|  DNAT (Destination NAT): Public -> Private (inbound, port forwarding)  |
|  PAT (Port Address Translation): Many private -> one public (common)   |
|                                                                         |
|  WHY NAT?                                                               |
|  * Conserves IPv4 addresses                                           |
|  * Hides internal network structure                                   |
|  * Basic security (internal devices not directly reachable)           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 14.3: CHECKSUMS AND DATA INTEGRITY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY CHECKSUMS?                                                        |
|                                                                         |
|  Data can get corrupted during transmission:                          |
|  * Electrical interference                                            |
|  * Hardware failures                                                  |
|  * Software bugs                                                      |
|                                                                         |
|  Checksums detect corruption by computing a "fingerprint" of data.    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CHECKSUM TYPES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. SIMPLE CHECKSUM                                                    |
|  ===================                                                    |
|                                                                         |
|  Sum all bytes, take modulo                                           |
|                                                                         |
|  Data: [0x01, 0x02, 0x03, 0x04]                                       |
|  Checksum = (1 + 2 + 3 + 4) mod 256 = 10                             |
|                                                                         |
|  PROS: Fast, simple                                                   |
|  CONS: Misses transposition errors (1,2 vs 2,1 = same sum)           |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. CRC (Cyclic Redundancy Check)                                     |
|  ===============================                                       |
|                                                                         |
|  Polynomial division based checksum                                   |
|                                                                         |
|  Common variants:                                                      |
|  * CRC-16: 16-bit checksum                                           |
|  * CRC-32: 32-bit checksum (Ethernet, ZIP files)                     |
|  * CRC-64: 64-bit checksum                                           |
|                                                                         |
|  PROS: Catches burst errors, transposition errors                    |
|  CONS: Not cryptographically secure                                   |
|                                                                         |
|  USED BY: Ethernet (CRC-32), ZIP files, USB, disk drives            |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. CRYPTOGRAPHIC HASHES                                              |
|  ========================                                              |
|                                                                         |
|  Strong hashes for security-sensitive integrity                       |
|                                                                         |
|  * MD5: 128-bit (broken, don't use for security)                    |
|  * SHA-1: 160-bit (deprecated)                                       |
|  * SHA-256: 256-bit (current standard)                               |
|  * SHA-512: 512-bit                                                  |
|                                                                         |
|  PROS: Cryptographically secure, collision resistant                 |
|  CONS: Slower than CRC                                                |
|                                                                         |
|  USED BY: File downloads, Git commits, blockchain                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CHECKSUMS IN PROTOCOLS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PROTOCOL CHECKSUMS                                                     |
|                                                                         |
|  +----------------------------------------------------------------+   |
|  |                                                                |   |
|  |  Protocol      Checksum Type    Scope                          |   |
|  |  ------------------------------------------------------------ |   |
|  |                                                                |   |
|  |  Ethernet      CRC-32           Frame (Layer 2)                |   |
|  |                                                                |   |
|  |  IP            16-bit checksum  Header only                    |   |
|  |                (1's complement)                                |   |
|  |                                                                |   |
|  |  TCP           16-bit checksum  Header + Data + Pseudo-header |   |
|  |                                                                |   |
|  |  UDP           16-bit checksum  Header + Data (optional IPv4) |   |
|  |                                                                |   |
|  |  HTTP          None built-in    Relies on TCP                 |   |
|  |                (use Content-MD5)                              |   |
|  |                                                                |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
|  TCP CHECKSUM CALCULATION:                                              |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Pseudo-Header (for checksum calculation only):                |  |
|  |  +--------------------------------------------------------+   |  |
|  |  | Source IP | Dest IP | Zero | Protocol | TCP Length    |   |  |
|  |  +--------------------------------------------------------+   |  |
|  |                                                                 |  |
|  |  +                                                             |  |
|  |                                                                 |  |
|  |  TCP Header + Data                                             |  |
|  |  +--------------------------------------------------------+   |  |
|  |  | Src Port | Dst Port | Seq | Ack | Flags | Data...     |   |  |
|  |  +--------------------------------------------------------+   |  |
|  |                                                                 |  |
|  |  = 16-bit 1's complement sum                                  |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CHECKSUMS IN SYSTEM DESIGN

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHERE CHECKSUMS MATTER IN SYSTEM DESIGN                               |
|                                                                         |
|  1. FILE STORAGE                                                        |
|     * S3 uses MD5 (Content-MD5 header) and SHA-256                   |
|     * Git uses SHA-1 (moving to SHA-256) for commit integrity        |
|     * Detect corruption in blob storage                              |
|                                                                         |
|  2. DATA TRANSFER                                                       |
|     * Chunked uploads: verify each chunk                             |
|     * Large file downloads: verify after download                    |
|     * API responses: Content-MD5 header                              |
|                                                                         |
|  3. DISTRIBUTED SYSTEMS                                                 |
|     * Message integrity in queues                                     |
|     * Data replication verification                                   |
|     * Detecting bit rot in storage                                    |
|                                                                         |
|  4. CACHING                                                             |
|     * ETags (often based on content hash)                            |
|     * Cache validation                                                |
|                                                                         |
|  5. DEDUPLICATION                                                       |
|     * Content-addressable storage (use hash as key)                  |
|     * Same content -> same hash -> store once                          |
|                                                                         |
|  EXAMPLE: S3 Upload with Integrity                                      |
|                                                                         |
|  PUT /bucket/file HTTP/1.1                                             |
|  Content-MD5: pAzWKjOcyaVfxB8KH4O1Mg==                                |
|  x-amz-content-sha256: <SHA256-hash>                                  |
|  Content-Length: 10485760                                              |
|  [file data]                                                            |
|                                                                         |
|  S3 verifies checksums match -> rejects if corrupted                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 14.4: ARP (Address Resolution Protocol)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS ARP?                                                          |
|                                                                         |
|  Maps IP addresses (Layer 3) to MAC addresses (Layer 2)               |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Computer A wants to send data to 192.168.1.20                 |  |
|  |  But Ethernet needs MAC address, not IP!                       |  |
|  |                                                                 |  |
|  |  1. Computer A: "Who has 192.168.1.20? Tell 192.168.1.10"     |  |
|  |     (ARP Request - broadcast to all devices)                   |  |
|  |                                                                 |  |
|  |  2. Computer B (192.168.1.20): "I have it, my MAC is AA:BB:CC"|  |
|  |     (ARP Reply - unicast back to A)                            |  |
|  |                                                                 |  |
|  |  3. Computer A caches this mapping                             |  |
|  |     (ARP Cache: 192.168.1.20 -> AA:BB:CC:DD:EE:FF)             |  |
|  |                                                                 |  |
|  |  4. Now A can send Ethernet frames to B                       |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  WHY IT MATTERS:                                                        |
|  * ARP cache poisoning is a security attack                           |
|  * ARP tables in routers affect network performance                   |
|  * Understanding helps debug network issues                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## QUICK REFERENCE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  OSI MODEL MNEMONIC:                                                   |
|  "Please Do Not Throw Sausage Pizza Away"                             |
|   Physical, Data Link, Network, Transport, Session, Presentation, App |
|                                                                         |
|  KEY IP FACTS:                                                          |
|  * IPv4: 32 bits, 4.3B addresses, NAT needed                          |
|  * IPv6: 128 bits, virtually unlimited, no NAT                        |
|  * Private ranges: 10.x.x.x, 172.16-31.x.x, 192.168.x.x              |
|  * CIDR /24 = 256 addresses, /16 = 65K addresses                      |
|                                                                         |
|  CHECKSUM CHOICE:                                                       |
|  * Speed critical, no security: CRC-32                                |
|  * Data integrity + security: SHA-256                                 |
|  * Legacy compatibility: MD5 (but not for security!)                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 14

