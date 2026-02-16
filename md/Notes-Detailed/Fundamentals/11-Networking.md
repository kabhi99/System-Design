# CHAPTER 11: NETWORKING FUNDAMENTALS
*How Data Moves Across the Internet*

Understanding networking is essential for system design. From DNS lookups
to WebSocket connections, every system depends on the network.

## SECTION 11.1: DNS (DOMAIN NAME SYSTEM)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS DNS?                                                           |
|                                                                         |
|  Translates human-readable domain names to IP addresses.                |
|                                                                         |
|  www.example.com --> 93.184.216.34                                      |
|                                                                         |
|  DNS RESOLUTION FLOW:                                                   |
|                                                                         |
|  +-----------------------------------------------------------------+    |
|  |                                                                 |    |
|  |  Browser: "What's the IP for www.example.com?"                 |     |
|  |      |                                                          |    |
|  |      v                                                          |    |
|  |  1. Local Cache (browser, OS)                                  |     |
|  |      | miss                                                     |    |
|  |      v                                                          |    |
|  |  2. Recursive Resolver (ISP or 8.8.8.8)                        |     |
|  |      |                                                          |    |
|  |      +--> 3. Root Server: "Ask .com servers"                  |      |
|  |      |                                                          |    |
|  |      +--> 4. TLD Server (.com): "Ask example.com servers"     |      |
|  |      |                                                          |    |
|  |      +--> 5. Authoritative Server: "IP is 93.184.216.34"      |      |
|  |      |                                                          |    |
|  |      v                                                          |    |
|  |  Browser receives IP, caches it, connects                      |     |
|  |                                                                 |    |
|  +-----------------------------------------------------------------+    |
|                                                                         |
|  DNS RECORD TYPES:                                                      |
|  +----------+----------------------------------------------------+      |
|  | Type     | Purpose                                            |      |
|  +----------+----------------------------------------------------+      |
|  | A        | Maps domain to IPv4 address                        |      |
|  | AAAA     | Maps domain to IPv6 address                        |      |
|  | CNAME    | Alias to another domain                           |       |
|  | MX       | Mail server for domain                            |       |
|  | TXT      | Text records (SPF, verification)                  |       |
|  | NS       | Nameservers for domain                            |       |
|  | SRV      | Service location (port, weight)                   |       |
|  +----------+----------------------------------------------------+      |
|                                                                         |
|  TTL (Time To Live):                                                    |
|  How long resolvers cache the record                                    |
|  * Low TTL (60s): Faster updates, more DNS queries                      |
|  * High TTL (86400s): Better caching, slower updates                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DNS IN SYSTEM DESIGN

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DNS-BASED LOAD BALANCING                                               |
|                                                                         |
|  Return multiple A records for one domain:                              |
|                                                                         |
|  api.example.com.  300  A  10.0.0.1                                     |
|  api.example.com.  300  A  10.0.0.2                                     |
|  api.example.com.  300  A  10.0.0.3                                     |
|                                                                         |
|  Client picks one (usually round-robin)                                 |
|                                                                         |
|  PROS: Simple, no single point of failure                               |
|  CONS: No health checks, slow failover (TTL), client caching            |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  GSLB (Global Server Load Balancing)                                    |
|                                                                         |
|  DNS returns different IPs based on user location.                      |
|                                                                         |
|  User in US --> DNS --> 10.0.0.1 (US datacenter)                        |
|  User in EU --> DNS --> 10.0.0.2 (EU datacenter)                        |
|                                                                         |
|  SERVICES: Route 53, Cloudflare, NS1                                    |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  SERVICE DISCOVERY WITH DNS                                             |
|                                                                         |
|  Internal services register with DNS:                                   |
|  order-service.internal.example.com > 10.1.0.5                          |
|                                                                         |
|  Tools: Consul, AWS Cloud Map, Kubernetes CoreDNS                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 11.2: TCP vs UDP

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TCP (Transmission Control Protocol)                                    |
|                                                                         |
|  RELIABLE, ORDERED, CONNECTION-ORIENTED                                 |
|                                                                         |
|  CONNECTION ESTABLISHMENT (3-way handshake):                            |
|                                                                         |
|  Client              Server                                             |
|     |                   |                                               |
|     |---- SYN --------->|   "I want to connect"                         |
|     |                   |                                               |
|     |<--- SYN-ACK ------|   "OK, I acknowledge"                         |
|     |                   |                                               |
|     |---- ACK --------->|   "Connection established"                    |
|     |                   |                                               |
|                                                                         |
|  TCP FEATURES:                                                          |
|  Y Reliable delivery (retransmits lost packets)                         |
|  Y Ordered (packets reassembled in order)                               |
|  Y Flow control (don't overwhelm receiver)                              |
|  Y Congestion control (adapt to network conditions)                     |
|                                                                         |
|  OVERHEAD:                                                              |
|  * 3-way handshake adds latency                                         |
|  * 20+ byte header per packet                                           |
|  * Retransmissions can add delay                                        |
|                                                                         |
|  USE FOR: HTTP, HTTPS, SSH, Email, Databases                            |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  UDP (User Datagram Protocol)                                           |
|                                                                         |
|  FAST, UNRELIABLE, CONNECTIONLESS                                       |
|                                                                         |
|  Client              Server                                             |
|     |                   |                                               |
|     |---- Data -------->|   "Here's data, good luck!"                   |
|     |                   |                                               |
|                                                                         |
|  UDP FEATURES:                                                          |
|  Y No connection setup (immediate send)                                 |
|  Y Low latency                                                          |
|  Y Supports broadcast/multicast                                         |
|  X No reliability (packets can be lost)                                 |
|  X No ordering (packets can arrive out of order)                        |
|                                                                         |
|  USE FOR: DNS, Video streaming, Gaming, VoIP                            |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  COMPARISON                                                             |
|                                                                         |
|  +----------------+------------------+------------------+               |
|  | Feature        | TCP              | UDP              |               |
|  +----------------+------------------+------------------+               |
|  | Connection     | Required         | None             |               |
|  | Reliability    | Guaranteed       | Best effort      |               |
|  | Ordering       | Guaranteed       | Not guaranteed   |               |
|  | Speed          | Slower           | Faster           |               |
|  | Header size    | 20-60 bytes      | 8 bytes          |               |
|  | Use case       | File transfer    | Live streaming   |               |
|  +----------------+------------------+------------------+               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 11.3: HTTP/1.1, HTTP/2, HTTP/3

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HTTP/1.1 (1997)                                                        |
|                                                                         |
|  Text-based protocol, one request at a time per connection.             |
|                                                                         |
|  GET /page.html HTTP/1.1                                                |
|  Host: example.com                                                      |
|  Connection: keep-alive                                                 |
|                                                                         |
|  FEATURES:                                                              |
|  * Keep-alive connections (reuse TCP connection)                        |
|  * Pipelining (send multiple requests, rarely used)                     |
|                                                                         |
|  PROBLEMS:                                                              |
|  * Head-of-line blocking: Request 2 waits for Response 1                |
|  * Multiple connections needed for parallelism (6 per domain)           |
|  * Redundant headers sent with every request                            |
|                                                                         |
|  +-----------------------------------------------------------------+    |
|  |  Connection 1: GET /style.css --> response --> GET /app.js     |     |
|  |  Connection 2: GET /image1.png --> response                     |    |
|  |  Connection 3: GET /image2.png --> response                     |    |
|  |  (Multiple connections to parallelize)                          |    |
|  +-----------------------------------------------------------------+    |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  HTTP/2 (2015)                                                          |
|                                                                         |
|  Binary protocol with multiplexing. Single connection.                  |
|                                                                         |
|  KEY FEATURES:                                                          |
|                                                                         |
|  1. MULTIPLEXING                                                        |
|     Multiple requests/responses on single connection                    |
|     No head-of-line blocking at HTTP level                              |
|                                                                         |
|  +-----------------------------------------------------------------+    |
|  |  Single Connection:                                             |    |
|  |  ------------------------------------------>                   |     |
|  |  Stream 1: [request] -------------> [response]                 |     |
|  |  Stream 2: [request] ------> [response]                        |     |
|  |  Stream 3: [request] -----------------> [response]             |     |
|  |  (All interleaved on same connection)                          |     |
|  +-----------------------------------------------------------------+    |
|                                                                         |
|  2. HEADER COMPRESSION (HPACK)                                          |
|     Headers compressed, duplicates eliminated                           |
|                                                                         |
|  3. SERVER PUSH                                                         |
|     Server can push resources before client requests                    |
|     Request HTML > Server sends HTML + CSS + JS                         |
|                                                                         |
|  4. STREAM PRIORITIZATION                                               |
|     Client indicates which resources are more important                 |
|                                                                         |
|  STILL USES TCP: Head-of-line blocking at TCP level remains             |
|  (If packet lost, all streams wait)                                     |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  HTTP/3 (2022)                                                          |
|                                                                         |
|  HTTP over QUIC (UDP-based). Eliminates TCP limitations.                |
|                                                                         |
|  KEY FEATURES:                                                          |
|                                                                         |
|  1. QUIC TRANSPORT (UDP-based)                                          |
|     * 0-RTT connection establishment (vs 3-RTT for TCP+TLS)             |
|     * No TCP head-of-line blocking                                      |
|     * Connection migration (WiFi > cellular)                            |
|                                                                         |
|  2. INDEPENDENT STREAMS                                                 |
|     Lost packet only affects its stream, not others                     |
|                                                                         |
|  3. BUILT-IN TLS 1.3                                                    |
|     Encryption mandatory and integrated                                 |
|                                                                         |
|  CONNECTION SETUP COMPARISON:                                           |
|  +------------------------------------------------------------------+   |
|  | HTTP/1.1 + TLS: TCP handshake (1 RTT) + TLS (2 RTT) = 3 RTT    |     |
|  | HTTP/2 + TLS:   Same as HTTP/1.1 = 3 RTT                        |    |
|  | HTTP/3 (QUIC):  Combined handshake = 1 RTT (0 RTT if resumed)  |     |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  ADOPTION: Growing, supported by major browsers and CDNs                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 11.4: WEBSOCKETS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT ARE WEBSOCKETS?                                                   |
|                                                                         |
|  Full-duplex, bidirectional communication over single TCP connection.   |
|                                                                         |
|  HTTP: Request > Response (client initiates)                            |
|  WebSocket: Messages flow both ways anytime                             |
|                                                                         |
|  WEBSOCKET HANDSHAKE:                                                   |
|                                                                         |
|  Client                           Server                                |
|     |                                |                                  |
|     |--- HTTP Upgrade Request ------>|                                  |
|     |    Connection: Upgrade         |                                  |
|     |    Upgrade: websocket          |                                  |
|     |                                |                                  |
|     |<-- HTTP 101 Switching ---------|                                  |
|     |    Protocols                   |                                  |
|     |                                |                                  |
|     |<==============================>|  WebSocket connection open       |
|     |    Bidirectional messages      |                                  |
|     |                                |                                  |
|                                                                         |
|  USE CASES:                                                             |
|  * Real-time chat                                                       |
|  * Live notifications                                                   |
|  * Collaborative editing (Google Docs)                                  |
|  * Live sports scores                                                   |
|  * Multiplayer games                                                    |
|  * Stock tickers                                                        |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  WEBSOCKET vs ALTERNATIVES                                              |
|                                                                         |
|  POLLING:                                                               |
|  Client repeatedly asks: "Any new data?"                                |
|  Simple but wasteful (many empty responses)                             |
|                                                                         |
|  LONG POLLING:                                                          |
|  Server holds request until data available                              |
|  Better than polling, but still HTTP overhead                           |
|                                                                         |
|  SERVER-SENT EVENTS (SSE):                                              |
|  Server > Client only (one-way)                                         |
|  Good for feeds, notifications                                          |
|  Uses regular HTTP, simpler than WebSocket                              |
|                                                                         |
|  WEBSOCKET:                                                             |
|  Full duplex, lowest latency                                            |
|  More complex (connection management)                                   |
|                                                                         |
|  +-----------------+----------------+-------------+-----------------+   |
|  | Feature         | Polling        | SSE         | WebSocket       |   |
|  +-----------------+----------------+-------------+-----------------+   |
|  | Direction       | Client>Server  | Server>Cli  | Bidirectional   |   |
|  | Latency         | High           | Low         | Lowest          |   |
|  | Connection      | Per request    | Persistent  | Persistent      |   |
|  | Complexity      | Low            | Medium      | High            |   |
|  | Browser support | All            | Good        | Good            |   |
|  +-----------------+----------------+-------------+-----------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WEBSOCKET AT SCALE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCALING WEBSOCKET CONNECTIONS                                          |
|                                                                         |
|  CHALLENGE: Each connection is persistent (stateful)                    |
|  Can't just add more servers without coordination                       |
|                                                                         |
|  ARCHITECTURE:                                                          |
|                                                                         |
|  +-----------------------------------------------------------------+    |
|  |                                                                 |    |
|  |  Clients --> Load Balancer (sticky sessions) --> WS Servers   |      |
|  |                                                   v            |     |
|  |                                              Pub/Sub (Redis)   |     |
|  |                                                                 |    |
|  |  User A connected to Server 1                                  |     |
|  |  User B connected to Server 2                                  |     |
|  |  User A sends message to B:                                    |     |
|  |                                                                 |    |
|  |  A > Server 1 > Redis Pub/Sub > Server 2 > B                  |      |
|  |                                                                 |    |
|  +-----------------------------------------------------------------+    |
|                                                                         |
|  STICKY SESSIONS:                                                       |
|  Same client always routes to same server                               |
|  Methods: Cookie, IP hash, connection ID                                |
|                                                                         |
|  PUB/SUB FOR CROSS-SERVER:                                              |
|  Redis Pub/Sub, Kafka, or custom solution                               |
|  Servers subscribe to channels, forward to connected clients            |
|                                                                         |
|  CONNECTION LIMITS:                                                     |
|  Each server: ~10K-100K connections (depends on hardware)               |
|  Monitor: Open file descriptors, memory per connection                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 11.5: CDN (CONTENT DELIVERY NETWORK)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS A CDN?                                                         |
|                                                                         |
|  Distributed network of servers that cache content closer to users.     |
|                                                                         |
|  WITHOUT CDN:                                                           |
|  User in Tokyo -------- 200ms -------- Origin server in NYC             |
|                                                                         |
|  WITH CDN:                                                              |
|  User in Tokyo -- 20ms -- CDN edge (Tokyo) -- Origin (if miss)          |
|                                                                         |
|  CDN ARCHITECTURE:                                                      |
|                                                                         |
|  +-----------------------------------------------------------------+    |
|  |                                                                 |    |
|  |              +-----------------------------+                   |     |
|  |              |      Origin Server          |                   |     |
|  |              |      (Your servers)         |                   |     |
|  |              +-----------------------------+                   |     |
|  |                          |                                      |    |
|  |         +----------------+----------------+                    |     |
|  |         v                v                v                    |     |
|  |  +-----------+    +-----------+    +-----------+              |      |
|  |  | Edge POP  |    | Edge POP  |    | Edge POP  |              |      |
|  |  |  (NYC)    |    | (London)  |    | (Tokyo)   |              |      |
|  |  +-----+-----+    +-----+-----+    +-----+-----+              |      |
|  |        |                |                |                     |     |
|  |        v                v                v                     |     |
|  |    US Users         EU Users         Asia Users                |     |
|  |                                                                 |    |
|  +-----------------------------------------------------------------+    |
|                                                                         |
|  WHAT CDNS CACHE:                                                       |
|  * Static assets (JS, CSS, images, fonts)                               |
|  * HTML pages (if cacheable)                                            |
|  * Video content                                                        |
|  * API responses (if configured)                                        |
|                                                                         |
|  CDN PROVIDERS: Cloudflare, Fastly, Akamai, AWS CloudFront              |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  CDN CACHE CONTROL                                                      |
|                                                                         |
|  CACHE-CONTROL HEADERS:                                                 |
|                                                                         |
|  Cache-Control: public, max-age=31536000                                |
|  > Cache for 1 year (immutable assets with hash in filename)            |
|                                                                         |
|  Cache-Control: private, no-cache                                       |
|  > Don't cache in CDN, always validate                                  |
|                                                                         |
|  Cache-Control: s-maxage=3600, max-age=60                               |
|  > CDN caches 1 hour, browser caches 1 minute                           |
|                                                                         |
|  CACHE INVALIDATION:                                                    |
|  * Purge: Clear specific URLs from cache                                |
|  * Versioning: style.v2.css (new URL = fresh)                           |
|  * Hash in filename: style.a1b2c3.css                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NETWORKING - KEY TAKEAWAYS                                             |
|                                                                         |
|  DNS                                                                    |
|  ----                                                                   |
|  * Translates domains to IPs                                            |
|  * Used for load balancing (multiple A records)                         |
|  * GSLB for geo-routing                                                 |
|  * TTL controls cache duration                                          |
|                                                                         |
|  TCP vs UDP                                                             |
|  -----------                                                            |
|  * TCP: Reliable, ordered (HTTP, databases)                             |
|  * UDP: Fast, unreliable (DNS, streaming, gaming)                       |
|                                                                         |
|  HTTP VERSIONS                                                          |
|  -------------                                                          |
|  * HTTP/1.1: Text, head-of-line blocking                                |
|  * HTTP/2: Binary, multiplexing, server push                            |
|  * HTTP/3: QUIC (UDP), 0-RTT, no HOL blocking                           |
|                                                                         |
|  REAL-TIME COMMUNICATION                                                |
|  -----------------------                                                |
|  * Polling: Simple but wasteful                                         |
|  * SSE: Server > Client only                                            |
|  * WebSocket: Full duplex, lowest latency                               |
|                                                                         |
|  CDN                                                                    |
|  ----                                                                   |
|  * Cache content at edge                                                |
|  * Reduce latency for users globally                                    |
|  * Use Cache-Control headers                                            |
|                                                                         |
|  INTERVIEW TIP                                                          |
|  -------------                                                          |
|  When designing systems:                                                |
|  * Consider DNS for simple load balancing                               |
|  * Use CDN for static assets                                            |
|  * Choose WebSocket for real-time features                              |
|  * Mention HTTP/2 or HTTP/3 benefits                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 11

