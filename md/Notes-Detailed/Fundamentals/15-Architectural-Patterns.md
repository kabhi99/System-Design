# CHAPTER 15: ARCHITECTURAL PATTERNS
*Client-Server, Serverless, P2P, Gossip Protocol*

This chapter covers architectural patterns and distributed system protocols
commonly asked in system design interviews.

## SECTION 15.1: CLIENT-SERVER ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS CLIENT-SERVER?                                                |
|                                                                         |
|  A distributed architecture where clients request services and         |
|  servers provide them. The most common architecture on the web.       |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  +----------+                        +----------+              |  |
|  |  |  CLIENT  | ------ Request ------> |  SERVER  |              |  |
|  |  |          |                        |          |              |  |
|  |  | (Browser,| <----- Response ------ | (Web,    |              |  |
|  |  |  Mobile) |                        |  API)    |              |  |
|  |  +----------+                        +----------+              |  |
|  |                                                                 |  |
|  |  CLIENT:                                                       |  |
|  |  * Initiates requests                                         |  |
|  |  * Displays data to user                                      |  |
|  |  * Lightweight processing                                     |  |
|  |                                                                 |  |
|  |  SERVER:                                                       |  |
|  |  * Waits for requests                                         |  |
|  |  * Processes business logic                                   |  |
|  |  * Manages data storage                                       |  |
|  |  * Serves multiple clients                                    |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CLIENT-SERVER TIERS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1-TIER (Monolithic)                                                   |
|  ====================                                                   |
|                                                                         |
|  Everything on one machine                                             |
|  +---------------------------------+                                   |
|  |     UI + Logic + Database       |                                   |
|  |     (Desktop Application)       |                                   |
|  +---------------------------------+                                   |
|                                                                         |
|  Example: MS Access, Excel with VBA                                   |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2-TIER (Client-Server)                                                |
|  =======================                                                |
|                                                                         |
|  +------------------+        +------------------+                      |
|  |      CLIENT      |<------>|      SERVER      |                      |
|  | (UI + Some Logic)|        | (Database)       |                      |
|  +------------------+        +------------------+                      |
|                                                                         |
|  Example: Desktop app with SQL Server                                 |
|  Problem: Fat client, hard to update                                  |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3-TIER (Web Architecture)                                             |
|  ==========================                                             |
|                                                                         |
|  +-----------+      +-----------+      +-----------+                  |
|  |   CLIENT  |<---->|APPLICATION|<---->|  DATABASE |                  |
|  |   (UI)    |      |  SERVER   |      |   SERVER  |                  |
|  |           |      | (Logic)   |      |           |                  |
|  +-----------+      +-----------+      +-----------+                  |
|   Presentation       Business           Data                           |
|      Tier              Tier             Tier                           |
|                                                                         |
|  Example: Browser > Node.js > PostgreSQL                              |
|  Most common web architecture                                         |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  N-TIER (Enterprise)                                                   |
|  ===================                                                    |
|                                                                         |
|  +------+ +------+ +------+ +------+ +------+ +------+               |
|  |Client|>|CDN   |>|LB    |>|App   |>|Cache |>|DB    |               |
|  +------+ +------+ +------+ +------+ +------+ +------+               |
|                                                                         |
|  Modern web: CDN + Load Balancer + App Servers + Cache + Database    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### THIN CLIENT vs THICK CLIENT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  THIN CLIENT                    THICK CLIENT                   |  |
|  |  ===========                    ============                    |  |
|  |                                                                 |  |
|  |  Minimal processing             Significant processing         |  |
|  |  Server does the work           Client does the work          |  |
|  |                                                                 |  |
|  |  Examples:                      Examples:                      |  |
|  |  * Web browser                  * Native mobile apps          |  |
|  |  * Terminal                     * Desktop applications        |  |
|  |  * Chromebook                   * Games                       |  |
|  |  * Dumb terminals              * PWAs with offline mode      |  |
|  |                                                                 |  |
|  |  PROS:                          PROS:                          |  |
|  |  * Easy to update               * Works offline               |  |
|  |  * Lower client cost            * Better UX (responsive)      |  |
|  |  * Centralized control          * Less server load            |  |
|  |                                                                 |  |
|  |  CONS:                          CONS:                          |  |
|  |  * Needs network                * Harder to update            |  |
|  |  * Server bottleneck            * Security concerns           |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  MODERN TREND: Hybrid (React/Vue apps - thick client + API server)   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 15.2: SERVERLESS ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS SERVERLESS?                                                   |
|                                                                         |
|  "Serverless" doesn't mean no servers - it means YOU don't manage     |
|  the servers. Cloud provider handles all infrastructure.              |
|                                                                         |
|  Two main forms:                                                       |
|  1. FaaS (Functions as a Service) - AWS Lambda, Azure Functions       |
|  2. BaaS (Backend as a Service) - Firebase, Supabase                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### FUNCTION AS A SERVICE (FaaS)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HOW FaaS WORKS                                                        |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  TRADITIONAL SERVER                                            |  |
|  |                                                                 |  |
|  |  +---------------------------------------------------------+  |  |
|  |  |                    Server Running 24/7                  |  |  |
|  |  |  ▓▓░░░░▓▓▓░░░░░░░░▓▓░░░░░░▓▓▓▓░░░░░░░░░░░░░░░▓▓░░░░   |  |  |
|  |  |      ^              ^            ^                ^     |  |  |
|  |  |   requests       requests     requests         requests |  |  |
|  |  +---------------------------------------------------------+  |  |
|  |  Pay for: 24 hours, even when idle                          |  |
|  |                                                                 |  |
|  |  ------------------------------------------------------------  |  |
|  |                                                                 |  |
|  |  SERVERLESS (FaaS)                                             |  |
|  |                                                                 |  |
|  |       +--+        +---+       +--+       +----+      +--+    |  |
|  |       |▓▓|        |▓▓▓|       |▓▓|       |▓▓▓▓|      |▓▓|    |  |
|  |  -----+--+--------+---+-------+--+-------+----+------+--+--  |  |
|  |       ^            ^           ^           ^          ^      |  |
|  |    spin up      spin up    spin up     spin up    spin up    |  |
|  |                                                                 |  |
|  |  Pay for: Only execution time (ms billing)                   |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SERVERLESS ARCHITECTURE PATTERNS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PATTERN 1: API BACKEND                                                |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Client > API Gateway > Lambda > DynamoDB                     |  |
|  |                                                                 |  |
|  |  +--------+    +-------------+    +--------+    +----------+ |  |
|  |  | Mobile |--->| API Gateway |--->| Lambda |--->| DynamoDB | |  |
|  |  |  App   |    |             |    |        |    |          | |  |
|  |  +--------+    +-------------+    +--------+    +----------+ |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  PATTERN 2: EVENT PROCESSING                                           |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  S3 Upload > Lambda > Process > Store Result                  |  |
|  |                                                                 |  |
|  |  +--------+    +--------+    +--------+    +--------+        |  |
|  |  | S3     |--->| Lambda |--->|Process |--->| S3 /   |        |  |
|  |  | Bucket |    |Trigger |    | Image  |    |DynamoDB|        |  |
|  |  +--------+    +--------+    +--------+    +--------+        |  |
|  |                                                                 |  |
|  |  Use case: Image thumbnails, video transcoding, ETL          |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  PATTERN 3: SCHEDULED JOBS                                             |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  CloudWatch Events > Lambda (cron)                             |  |
|  |                                                                 |  |
|  |  +----------------+    +--------+                              |  |
|  |  | EventBridge    |--->| Lambda |--> Send reports, cleanup    |  |
|  |  | (cron: 0 9 * *)|    |        |                              |  |
|  |  +----------------+    +--------+                              |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  PATTERN 4: STREAM PROCESSING                                          |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Kinesis/SQS > Lambda > Real-time processing                  |  |
|  |                                                                 |  |
|  |  +---------+    +--------+    +--------+                      |  |
|  |  | Kinesis |--->| Lambda |--->|Analytics|                     |  |
|  |  | Stream  |    |        |    |  DB     |                     |  |
|  |  +---------+    +--------+    +--------+                      |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SERVERLESS PROS AND CONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ADVANTAGES                                                             |
|  ==========                                                             |
|                                                                         |
|  Y NO SERVER MANAGEMENT                                                |
|    No patching, no capacity planning, no scaling configuration        |
|                                                                         |
|  Y PAY PER USE                                                         |
|    Billed by execution time (ms) and invocations                      |
|    Zero cost when idle                                                 |
|                                                                         |
|  Y AUTO-SCALING                                                        |
|    Scales from 0 to thousands of concurrent executions               |
|    No configuration needed                                            |
|                                                                         |
|  Y FASTER TIME TO MARKET                                               |
|    Focus on code, not infrastructure                                  |
|                                                                         |
|  Y BUILT-IN HIGH AVAILABILITY                                          |
|    Cloud provider handles redundancy                                  |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  DISADVANTAGES                                                          |
|  =============                                                          |
|                                                                         |
|  X COLD START LATENCY                                                  |
|    First request takes longer (100ms - 5s)                            |
|    VPC-attached functions even slower                                 |
|                                                                         |
|  X EXECUTION TIME LIMITS                                               |
|    AWS Lambda: 15 minutes max                                         |
|    Not for long-running processes                                     |
|                                                                         |
|  X VENDOR LOCK-IN                                                      |
|    Different APIs across providers                                    |
|    Migration is painful                                               |
|                                                                         |
|  X DEBUGGING DIFFICULTY                                                |
|    Distributed tracing is harder                                      |
|    Local testing is limited                                           |
|                                                                         |
|  X STATELESS CONSTRAINT                                                |
|    No local state between invocations                                 |
|    Need external storage for state                                    |
|                                                                         |
|  X COST AT SCALE                                                       |
|    Can become expensive with high, consistent traffic                |
|    24/7 workloads cheaper on containers/VMs                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHEN TO USE SERVERLESS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  GOOD FIT:                                                              |
|  * Variable/unpredictable traffic                                      |
|  * Event-driven workloads                                              |
|  * APIs with sporadic traffic                                          |
|  * Background jobs, scheduled tasks                                    |
|  * Prototypes and MVPs                                                 |
|  * Image/video processing                                              |
|                                                                         |
|  BAD FIT:                                                               |
|  * Long-running processes (> 15 min)                                   |
|  * Constant high traffic (cheaper with containers)                    |
|  * Low latency requirements (cold start issue)                        |
|  * Stateful applications                                               |
|  * WebSocket long connections                                          |
|                                                                         |
|  SERVERLESS SERVICES (AWS):                                            |
|  * Compute: Lambda                                                     |
|  * Database: DynamoDB, Aurora Serverless                              |
|  * Storage: S3                                                         |
|  * API: API Gateway                                                    |
|  * Events: EventBridge, SNS, SQS                                      |
|  * Auth: Cognito                                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 15.3: PEER-TO-PEER (P2P) ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS P2P?                                                          |
|                                                                         |
|  A distributed architecture where all nodes (peers) are equal.        |
|  Each peer is both client AND server.                                 |
|  No central server.                                                    |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  CLIENT-SERVER:                 PEER-TO-PEER:                  |  |
|  |                                                                 |  |
|  |       +--------+                +----+     +----+              |  |
|  |       | SERVER |                | P1 |<--->| P2 |              |  |
|  |       +---+----+                +--+-+     +-+--+              |  |
|  |      +----+----+                   |    \  /  |                 |  |
|  |      v    v    v                   |     \/   |                 |  |
|  |   +--+  +--+  +--+                 |     /\   |                 |  |
|  |   |C1|  |C2|  |C3|                 |    /  \  |                 |  |
|  |   +--+  +--+  +--+              +--v--+     +v---+             |  |
|  |                                 | P3  |<--->| P4 |             |  |
|  |   All clients depend            +-----+     +----+             |  |
|  |   on server                     All peers connected            |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### P2P NETWORK TYPES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. UNSTRUCTURED P2P                                                   |
|  ====================                                                   |
|                                                                         |
|  Random connections, no organization                                   |
|                                                                         |
|  * Gnutella (early file sharing)                                      |
|  * Discovery: Flooding (broadcast to all neighbors)                   |
|  * Simple but inefficient                                             |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. STRUCTURED P2P (DHT - Distributed Hash Table)                     |
|  ===================================================                   |
|                                                                         |
|  Organized structure for efficient lookups                            |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  DHT: Keys mapped to specific nodes using consistent hashing   |  |
|  |                                                                 |  |
|  |  key = hash("file.mp3")                                        |  |
|  |  node = find_successor(key)  > Route to responsible node      |  |
|  |                                                                 |  |
|  |  Lookup: O(log N) hops instead of O(N) flooding               |  |
|  |                                                                 |  |
|  |  Examples:                                                     |  |
|  |  * Chord: Ring-based DHT                                      |  |
|  |  * Kademlia: Used by BitTorrent, IPFS, Ethereum               |  |
|  |  * Pastry, Tapestry                                           |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. HYBRID P2P                                                         |
|  ===============                                                        |
|                                                                         |
|  Central server for coordination, P2P for data transfer               |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  +------------------+                                          |  |
|  |  |  Tracker/Index   |  < Knows who has what files             |  |
|  |  |     Server       |                                          |  |
|  |  +--------+---------+                                          |  |
|  |           | "Who has file X?"                                  |  |
|  |           v                                                     |  |
|  |  +----------------+                                            |  |
|  |  | Peer A         |<------ Direct transfer ------>| Peer B   | |  |
|  |  | (has file)     |        (P2P, no server)       | (wants)  | |  |
|  |  +----------------+                                +----------+|  |
|  |                                                                 |  |
|  |  Example: BitTorrent with tracker                             |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### BITTORRENT DEEP DIVE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BITTORRENT ARCHITECTURE                                               |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  KEY CONCEPTS:                                                  |  |
|  |                                                                 |  |
|  |  * TORRENT FILE: Metadata (file info, tracker URL, piece hashes)| |
|  |  * TRACKER: Coordinates peers (who has what)                   |  |
|  |  * SWARM: All peers sharing a file                            |  |
|  |  * SEEDER: Has complete file, only uploads                    |  |
|  |  * LEECHER: Downloading, also uploads pieces they have        |  |
|  |  * PIECE: File split into chunks (typically 256KB-1MB)        |  |
|  |                                                                 |  |
|  |  ------------------------------------------------------------  |  |
|  |                                                                 |  |
|  |  HOW IT WORKS:                                                  |  |
|  |                                                                 |  |
|  |  1. Download .torrent file (or use magnet link)               |  |
|  |  2. Contact tracker to get list of peers                      |  |
|  |  3. Connect to multiple peers                                 |  |
|  |  4. Request different pieces from different peers             |  |
|  |  5. Share pieces you have with others (tit-for-tat)          |  |
|  |  6. Verify pieces with hash (from .torrent)                   |  |
|  |                                                                 |  |
|  |  +--------------------------------------------------------+   |  |
|  |  |                                                        |   |  |
|  |  |  File: [P1][P2][P3][P4][P5][P6][P7][P8]               |   |  |
|  |  |                                                        |   |  |
|  |  |  Peer A has: [P1][P2][  ][P4][  ][  ][P7][  ]          |   |  |
|  |  |  Peer B has: [  ][P2][P3][  ][P5][  ][  ][P8]          |   |  |
|  |  |  Peer C has: [P1][  ][  ][P4][P5][P6][  ][  ]          |   |  |
|  |  |                                                        |   |  |
|  |  |  You download from multiple peers simultaneously!      |   |  |
|  |  |  Rarest piece first strategy                          |   |  |
|  |  |                                                        |   |  |
|  |  +--------------------------------------------------------+   |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  WHY P2P IS BRILLIANT FOR FILE SHARING:                                |
|  * More popular file = more seeders = faster download                 |
|  * Server cost > Zero (no central server needed)                      |
|  * Bandwidth > Distributed across all peers                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### P2P USE CASES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MODERN P2P APPLICATIONS                                               |
|                                                                         |
|  1. FILE SHARING                                                        |
|     * BitTorrent                                                       |
|     * IPFS (InterPlanetary File System)                               |
|                                                                         |
|  2. BLOCKCHAIN & CRYPTOCURRENCY                                        |
|     * Bitcoin, Ethereum                                               |
|     * Every node has full ledger copy                                 |
|                                                                         |
|  3. VIDEO STREAMING                                                     |
|     * WebRTC (browser video calls)                                    |
|     * Peer-assisted CDN (reduce server load)                         |
|                                                                         |
|  4. COMMUNICATION                                                       |
|     * Skype (historically P2P, now hybrid)                            |
|     * Matrix protocol                                                 |
|                                                                         |
|  5. DECENTRALIZED APPLICATIONS (dApps)                                 |
|     * Smart contracts                                                 |
|     * Decentralized storage (Filecoin, Storj)                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### P2P PROS AND CONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ADVANTAGES                         DISADVANTAGES                       |
|  ==========                         =============                       |
|                                                                         |
|  Y No single point of failure      X Complex to implement             |
|  Y Scales naturally (more peers    X Security challenges              |
|    = more capacity)                   (malicious peers)                |
|  Y No central server cost          X NAT traversal issues             |
|  Y Censorship resistant            X Inconsistent performance          |
|  Y Geographic distribution         X Discovery/coordination            |
|                                       is difficult                      |
|                                     X Legal concerns (piracy)          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 15.4: GOSSIP PROTOCOL

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS GOSSIP PROTOCOL?                                              |
|                                                                         |
|  A peer-to-peer communication protocol where nodes exchange            |
|  information like people spreading rumors/gossip.                      |
|                                                                         |
|  Each node periodically picks a random peer and exchanges state.      |
|  Information eventually spreads to all nodes.                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### HOW GOSSIP WORKS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  GOSSIP PROPAGATION                                                    |
|                                                                         |
|  Round 1: Node A has new data                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |      +----+                                                    |  |
|  |      | A* | < Has new info                                    |  |
|  |      +----+                                                    |  |
|  |      /    \                                                    |  |
|  |   +----+ +----+                                               |  |
|  |   | B  | | C  |                                               |  |
|  |   +----+ +----+                                               |  |
|  |   /         \                                                  |  |
|  | +----+    +----+                                              |  |
|  | | D  |    | E  |                                              |  |
|  | +----+    +----+                                              |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  Round 2: A gossips to B                                              |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |      +----+ --gossip--> +----+                                |  |
|  |      | A* |             | B* | < Now B has info              |  |
|  |      +----+             +----+                                |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  Round 3: A>C, B>D (parallel gossip)                                 |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |      +----+             +----+                                |  |
|  |      | A* |--gossip-->| C* |                                 |  |
|  |      +----+             +----+                                |  |
|  |      +----+             +----+                                |  |
|  |      | B* |--gossip-->| D* |                                 |  |
|  |      +----+             +----+                                |  |
|  |                                                                 |  |
|  |  Exponential spread: 1 > 2 > 4 > 8 > 16...                   |  |
|  |  Time to reach all N nodes: O(log N) rounds                  |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### GOSSIP PROTOCOL TYPES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. ANTI-ENTROPY (Push-Pull)                                           |
|  =============================                                          |
|                                                                         |
|  Nodes exchange ENTIRE state to reconcile differences                  |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Node A: {key1: v1, key2: v2}                                  |  |
|  |  Node B: {key1: v1, key3: v3}                                  |  |
|  |                                                                 |  |
|  |  After exchange:                                                |  |
|  |  Node A: {key1: v1, key2: v2, key3: v3}                       |  |
|  |  Node B: {key1: v1, key2: v2, key3: v3}                       |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  USE: Data synchronization, eventual consistency                      |
|  USED BY: Cassandra (repair), Dynamo                                  |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. RUMOR MONGERING (Push)                                            |
|  ===========================                                           |
|                                                                         |
|  Spread updates like rumors, stop after a while                       |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Node A: "New update: key1 = v2"                               |  |
|  |          > Tell random peer                                    |  |
|  |          > Keep telling until k peers already knew             |  |
|  |          > Then stop (rumor is "dead")                        |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  USE: Fast update propagation                                         |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. FAILURE DETECTION                                                  |
|  =====================                                                  |
|                                                                         |
|  Gossip about node health/membership                                   |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Node A: "Node C heartbeat: 1705000000"                       |  |
|  |  Node B: "Node C heartbeat: 1705000010"                       |  |
|  |                                                                 |  |
|  |  Merge: Use latest heartbeat                                   |  |
|  |  If heartbeat too old > Mark node as failed                   |  |
|  |                                                                 |  |
|  |  SWIM Protocol: Suspicion > Confirm > Remove                  |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  USED BY: Consul, Cassandra, Serf                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### GOSSIP USE CASES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHERE GOSSIP IS USED                                                  |
|                                                                         |
|  1. DATABASES                                                           |
|     * Cassandra: Cluster membership, schema changes                   |
|     * DynamoDB: Ring membership                                       |
|     * CockroachDB: Node liveness                                      |
|                                                                         |
|  2. DISTRIBUTED SYSTEMS                                                 |
|     * Consul: Service discovery, health checks                        |
|     * Serf: Cluster membership                                        |
|     * Kubernetes: Node status (partial)                               |
|                                                                         |
|  3. BLOCKCHAIN                                                          |
|     * Bitcoin: Transaction and block propagation                      |
|     * Ethereum: Peer discovery                                        |
|                                                                         |
|  4. MONITORING                                                          |
|     * Prometheus Alertmanager: Alert deduplication                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### GOSSIP PROS AND CONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ADVANTAGES                         DISADVANTAGES                       |
|  ==========                         =============                       |
|                                                                         |
|  Y Highly scalable                 X Eventual consistency only        |
|    (no central coordinator)          (not immediate)                   |
|                                                                         |
|  Y Fault tolerant                  X Bandwidth overhead               |
|    (works with failures)             (redundant messages)              |
|                                                                         |
|  Y Simple to implement             X No guaranteed delivery           |
|                                       (probabilistic)                   |
|  Y Decentralized                                                       |
|                                     X Convergence time                 |
|  Y Robust (works in hostile          uncertain                         |
|    network conditions)                                                  |
|                                                                         |
|  CONVERGENCE TIME:                                                      |
|  O(log N) rounds to reach all N nodes (high probability)             |
|                                                                         |
|  BANDWIDTH:                                                             |
|  Each node sends O(log N) messages per round                          |
|  Total: O(N log N) messages per update                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## QUICK REFERENCE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ARCHITECTURE COMPARISON                                               |
|                                                                         |
|  +----------------------------------------------------------------+   |
|  |                                                                |   |
|  |  Architecture      Best For                   Trade-off       |   |
|  |  ------------------------------------------------------------ |   |
|  |                                                                |   |
|  |  Client-Server     Most web apps,             Central point   |   |
|  |                    clear responsibility        of failure      |   |
|  |                                                                |   |
|  |  Serverless        Variable load,             Cold start,     |   |
|  |                    event-driven               vendor lock-in  |   |
|  |                                                                |   |
|  |  P2P               File sharing,              Complex,        |   |
|  |                    censorship resistance      NAT issues      |   |
|  |                                                                |   |
|  |  Gossip            Failure detection,         Eventual        |   |
|  |  Protocol          cluster membership         consistency     |   |
|  |                                                                |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 15

