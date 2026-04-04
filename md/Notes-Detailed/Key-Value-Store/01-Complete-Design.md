# DESIGN A DISTRIBUTED KEY-VALUE STORE (DYNAMO/CASSANDRA)

*Complete Design: Requirements, Architecture, and Interview Guide*

## SECTION 1: SCOPING THE PROBLEM WITH THE INTERVIEWER

```
+-------------------------------------------------------------------------+
|                                                                         |
|  INTERVIEWER-CANDIDATE DIALOGUE                                         |
|  (establishing scope before diving into design)                         |
|                                                                         |
|  CANDIDATE: Are we designing a distributed key-value store like         |
|    DynamoDB/Cassandra, or an in-memory cache like Redis?                |
|                                                                         |
|  INTERVIEWER: A distributed, persistent key-value store. Think          |
|    Dynamo. Cover partitioning, replication, consistency, and            |
|    conflict resolution.                                                 |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: What consistency model? Strong or eventual?                 |
|                                                                         |
|  INTERVIEWER: Tunable. Support both. Discuss quorum reads/writes        |
|    and how the user chooses their consistency level.                    |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: What scale?                                                 |
|                                                                         |
|  INTERVIEWER: Millions of keys, thousands of TPS per partition,         |
|    sub-10ms reads. Automatic scaling and rebalancing.                   |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  AGREED SCOPE:                                                          |
|                                                                         |
|  * Distributed persistent KV store (Dynamo/Cassandra style)             |
|  * Consistent hashing, replication, tunable consistency                 |
|  * Conflict resolution (vector clocks / LWW)                            |
|  * Deep dive: partition strategy + consistency guarantees               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1: TABLE OF CONTENTS

1. Requirements
2. Key Terminology
3. Scale Estimation
4. High-Level Architecture
5. Detailed Design
6. Consistent Hashing
7. Data Replication
8. Consistency and Quorum
9. Vector Clocks
10. Merkle Trees
11. Gossip Protocol
12. Hinted Handoff
13. Read Repair and Anti-Entropy
14. Bloom Filters
15. Storage Engines (LSM-Tree vs B-Tree)
16. Compaction Strategies
17. Database Schema / Data Model
18. API Design
19. Comparison: Dynamo vs Cassandra vs Redis vs etcd
20. Monitoring and Observability
21. Failure Scenarios and Mitigations
22. Interview Q&A

## SECTION 1: REQUIREMENTS

### 1.1 FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Core Operations:                                                       |
|  * put(key, value)    : Store a key-value pair                          |
|  * get(key)           : Retrieve value for a given key                  |
|  * delete(key)        : Remove a key-value pair                         |
|                                                                         |
|  Extended Operations:                                                   |
|  * Multi-get (batch reads)                                              |
|  * Range queries (for ordered key stores)                               |
|  * TTL (time-to-live) for automatic expiration                          |
|  * Compare-and-swap (CAS) for conditional updates                       |
|  * Secondary indexes (optional, Cassandra-style)                        |
|                                                                         |
|  Data Characteristics:                                                  |
|  * Key: typically < 256 bytes                                           |
|  * Value: up to 1 MB (configurable)                                     |
|  * No cross-key transactions (single-key atomicity)                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 1.2 NON-FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Availability:                                                          |
|  * 99.99% uptime (< 52.6 minutes downtime/year)                         |
|  * Always writable (AP in CAP theorem)                                  |
|  * No single point of failure                                           |
|                                                                         |
|  Performance:                                                           |
|  * Read latency: < 10ms (p99)                                           |
|  * Write latency: < 10ms (p99)                                          |
|  * Support millions of operations per second                            |
|                                                                         |
|  Scalability:                                                           |
|  * Horizontal scaling (add nodes to increase capacity)                  |
|  * Petabytes of data across thousands of nodes                          |
|  * Linear throughput scaling with node count                            |
|                                                                         |
|  Partition Tolerance:                                                   |
|  * Continue operating during network partitions                         |
|  * Tolerate up to N/2 - 1 node failures                                 |
|                                                                         |
|  Consistency:                                                           |
|  * Tunable consistency (eventual to strong)                             |
|  * Conflict resolution via vector clocks or LWW                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2: KEY TERMINOLOGY

```
+-------------------------------------------------------------------------+
||                                                                        |
||  CONSISTENT HASHING                                                    |
||  A ring-based partitioning scheme that maps keys to nodes.             |
||  Adding/removing a node only moves K/N keys on average.                |
||                                                                        |
||  VIRTUAL NODE (VNODE)                                                  |
||  Multiple hash positions per physical node on the ring.                |
||  Ensures even data distribution and smooth rebalancing.                |
||                                                                        |
||  GOSSIP PROTOCOL                                                       |
||  Peer-to-peer protocol where nodes periodically exchange               |
||  state info. Used for failure detection and membership.                |
||                                                                        |
||  VECTOR CLOCK                                                          |
||  A list of (node, counter) pairs tracking causal ordering.             |
||  Detects conflicts from concurrent writes to the same key.             |
||                                                                        |
||  MERKLE TREE                                                           |
||  A hash tree used to efficiently detect differences between            |
||  replicas. Enables fast anti-entropy synchronization.                  |
||                                                                        |
||  READ/WRITE QUORUM (W, R, N)                                           |
||  N = replicas, W = write acks, R = read acks required.                 |
||  If W + R > N, strong consistency. Tunable per operation.              |
||                                                                        |
||  HINTED HANDOFF                                                        |
||  When a target node is down, a neighbor temporarily stores             |
||  the write and forwards it once the failed node recovers.              |
||                                                                        |
||  ANTI-ENTROPY                                                          |
||  Background process comparing replicas using Merkle trees              |
||  and repairing divergence to ensure eventual consistency.              |
||                                                                        |
||  SSTABLE (SORTED STRING TABLE)                                         |
||  An immutable, sorted on-disk file of key-value pairs.                 |
||  Created when a memtable flushes. Read via binary search.              |
||                                                                        |
||  MEMTABLE                                                              |
||  In-memory sorted structure (e.g., red-black tree) that                |
||  buffers writes before flushing to SSTables on disk.                   |
||                                                                        |
||  BLOOM FILTER                                                          |
||  A space-efficient probabilistic structure for set membership.         |
||  Avoids unnecessary disk reads for keys not in an SSTable.             |
||                                                                        |
||  TOMBSTONE                                                             |
||  A special deletion marker for a key. Needed because not all           |
||  replicas see the delete immediately; removed at compaction.           |
||                                                                        |
+-------------------------------------------------------------------------+
```

## SECTION 3: SCALE ESTIMATION

### 3.1 TRAFFIC ESTIMATES

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Total operations per second:     1,000,000 (1M QPS)                     |
|  Read:Write ratio:                80:20                                  |
|  Read QPS:                        800,000                                |
|  Write QPS:                       200,000                                |
|  Peak QPS (3x):                   3,000,000                              |
|                                                                          |
|  Data volume:                                                            |
|  * Total keys:                    10 billion                             |
|  * Average key size:              100 bytes                              |
|  * Average value size:            10 KB                                  |
|  * New writes per day:            200K/s x 86400 = ~17 billion writes    |
|  * Daily data ingested:           17B x 10KB = ~170 TB/day               |
|    (with dedup/overwrites, net new ~ 5 TB/day)                           |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 3.2 STORAGE ESTIMATES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Total data (active):             10B keys x 10KB = 100 TB              |
|  Replication factor (3):          100 TB x 3 = 300 TB                   |
|  With compaction overhead (2x):   300 TB x 2 = 600 TB                   |
|  Tombstones / versioning:         ~50 TB overhead                       |
|                                                                         |
|  Total storage needed:            ~650 TB                               |
|  Nodes (2 TB usable each):       ~325 nodes                             |
|  With headroom (60% util):       ~540 nodes                             |
|                                                                         |
|  Memory for Bloom filters:        ~10 GB total cluster                  |
|  Memory for key index:            ~100 GB total cluster                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 3.3 NETWORK ESTIMATES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Incoming (writes):               200K/s x 10KB = 2 GB/s                |
|  Outgoing (reads):                800K/s x 10KB = 8 GB/s                |
|  Replication traffic:             2 GB/s x 2 (replicas) = 4 GB/s        |
|  Anti-entropy / repair:           ~500 MB/s (background)                |
|                                                                         |
|  Total network:                   ~14.5 GB/s cluster-wide               |
|  Per-node average (540 nodes):    ~27 MB/s per node                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4: HIGH-LEVEL ARCHITECTURE

### 4.1 SYSTEM OVERVIEW

```
+--------------------------------------------------------------------------+
|                  DISTRIBUTED KEY-VALUE STORE ARCHITECTURE                |
+--------------------------------------------------------------------------+
|                                                                          |
|   +----------+     +-----------+                                         |
|   |  Client  |---->|   Load    |                                         |
|   |  (SDK)   |     |  Balancer |                                         |
|   +----------+     +-----+-----+                                         |
|                          |                                               |
|          +---------------+---------------+                               |
|          |               |               |                               |
|    +-----v-----+  +-----v-----+  +------v----+                           |
|    |  Node A   |  |  Node B   |  |  Node C   |                           |
|    |           |  |           |  |           |                           |
|    | Coordinator  | Coordinator  | Coordinator|                          |
|    | layer     |  | layer     |  | layer     |                           |
|    |           |  |           |  |           |                           |
|    | Storage   |  | Storage   |  | Storage   |                           |
|    | Engine    |  | Engine    |  | Engine    |                           |
|    +-----------+  +-----------+  +-----------+                           |
|          |               |               |                               |
|    +-----v-----+  +-----v-----+  +------v----+                           |
|    | Disk      |  | Disk      |  | Disk      |                           |
|    | (SSTables)|  | (SSTables)|  | (SSTables)|                           |
|    +-----------+  +-----------+  +-----------+                           |
|                                                                          |
|   All nodes are equal (no master). Any node can serve any request.       |
|   Gossip protocol for cluster membership and failure detection.          |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 4.2 SINGLE NODE ARCHITECTURE

```
+--------------------------------------------------------------------------+
|                      SINGLE NODE ARCHITECTURE                            |
+--------------------------------------------------------------------------+
|                                                                          |
|  +---------------------------------------------------------------+       |
|  |  Request Handler (Coordinator)                                 |      |
|  |  - Route requests to correct nodes                             |      |
|  |  - Manage quorum reads/writes                                  |      |
|  +---------------------------------------------------------------+       |
|                          |                                               |
|  +---------------------------------------------------------------+       |
|  |  Storage Engine                                                |      |
|  |  +-----------------------------------------------------+      |       |
|  |  |  MemTable (In-Memory, Write Buffer)                  |      |      |
|  |  |  - Red-Black Tree or Skip List                       |      |      |
|  |  |  - Sorted by key                                     |      |      |
|  |  |  - Size: 64 MB - 256 MB                              |      |      |
|  |  +-----------------------------------------------------+      |       |
|  |                        |                                       |      |
|  |  +-----------------------------------------------------+      |       |
|  |  |  Write-Ahead Log (WAL)                               |      |      |
|  |  |  - Append-only, for crash recovery                   |      |      |
|  |  +-----------------------------------------------------+      |       |
|  |                        |                                       |      |
|  |  +-----------------------------------------------------+      |       |
|  |  |  SSTables (Sorted String Tables) on Disk             |      |      |
|  |  |  - Immutable, sorted by key                          |      |      |
|  |  |  - Multiple levels (L0, L1, L2, ...)                 |      |      |
|  |  |  - Each has a Bloom filter for fast lookups          |      |      |
|  |  +-----------------------------------------------------+      |       |
|  +---------------------------------------------------------------+       |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 5: DETAILED DESIGN

### 5.1 WRITE PATH

```
+--------------------------------------------------------------------------+
|                          WRITE PATH                                      |
+--------------------------------------------------------------------------+
|                                                                          |
|  Client: put("user:123", {name: "Alice", age: 30})                       |
|                                                                          |
|  Step 1: Coordinator receives request                                    |
|  +--------------------------------------------------------------------+  |
|  | - Hash key "user:123" -> position on consistent hash ring          |  |
|  | - Determine N replica nodes (e.g., nodes A, B, C)                  |  |
|  +--------------------------------------------------------------------+  |
|                          |                                               |
|  Step 2: Send to replicas (in parallel)                                  |
|  +--------------------------------------------------------------------+  |
|  |  Node A        Node B        Node C                                |  |
|  |  (primary)     (replica 1)   (replica 2)                           |  |
|  |     |              |              |                                |  |
|  |     v              v              v                                |  |
|  |  Append WAL     Append WAL    Append WAL                           |  |
|  |     |              |              |                                |  |
|  |     v              v              v                                |  |
|  |  Insert into    Insert into   Insert into                          |  |
|  |  MemTable       MemTable      MemTable                             |  |
|  |     |              |              |                                |  |
|  |     v              v              v                                |  |
|  |  ACK             ACK           ACK                                 |  |
|  +--------------------------------------------------------------------+  |
|                          |                                               |
|  Step 3: Wait for W acknowledgments                                      |
|  +--------------------------------------------------------------------+  |
|  | - W=2: Wait for 2 of 3 replicas to ACK (quorum write)              |  |
|  | - Return success to client after W ACKs received                   |  |
|  +--------------------------------------------------------------------+  |
|                          |                                               |
|  Step 4: Background flush (when MemTable is full)                        |
|  +--------------------------------------------------------------------+  |
|  | - Flush MemTable to disk as immutable SSTable                      |  |
|  | - Delete corresponding WAL entries                                 |  |
|  | - Trigger compaction if needed                                     |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 5.2 READ PATH

```
+-------------------------------------------------------------------------+
|                           READ PATH                                     |
+-------------------------------------------------------------------------+
|                                                                         |
|  Client: get("user:123")                                                |
|                                                                         |
|  Step 1: Coordinator determines replicas                                |
|  +-------------------------------------------------------------------+  |
|  | - Hash "user:123" -> same ring position as write                  |  |
|  | - Send read to R replica nodes (R=2 for quorum)                   |  |
|  +-------------------------------------------------------------------+  |
|                          |                                              |
|  Step 2: Each replica performs local read                               |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  1. Check MemTable (in-memory)         -> O(log n)                |  |
|  |     Found? Return. Not found? Continue.                           |  |
|  |                                                                   |  |
|  |  2. Check Bloom filters for each SSTable                          |  |
|  |     "Definitely not in SSTable-3" -> skip                         |  |
|  |     "Maybe in SSTable-1" -> check it                              |  |
|  |                                                                   |  |
|  |  3. Search SSTables (newest to oldest)                            |  |
|  |     - Binary search within SSTable (sorted keys)                  |  |
|  |     - Use sparse index to narrow search range                     |  |
|  |     - Found? Return with timestamp/version.                       |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                          |                                              |
|  Step 3: Coordinator resolves conflicts                                 |
|  +-------------------------------------------------------------------+  |
|  | - Compare versions from R replicas                                |  |
|  | - Return most recent version (by timestamp or vector clock)       |  |
|  | - If conflict detected: resolve or return both to client          |  |
|  | - Trigger read repair if replicas had stale data                  |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6: CONSISTENT HASHING

### 6.1 BASIC CONSISTENT HASHING

```
+-------------------------------------------------------------------------+
|                      CONSISTENT HASHING                                 |
+-------------------------------------------------------------------------+
|                                                                         |
|  Hash Ring (0 to 2^128 - 1):                                            |
|                                                                         |
|                        Node A                                           |
|                          *                                              |
|                      /       \                                          |
|                    /           \                                        |
|           Node D *               * Node B                               |
|                    \           /                                        |
|                      \       /                                          |
|                          *                                              |
|                        Node C                                           |
|                                                                         |
|  Key placement:                                                         |
|  * Hash(key) -> position on ring                                        |
|  * Walk clockwise to find first node -> that's the owner                |
|  * key "user:123" hashes between Node A and Node B -> owned by B        |
|                                                                         |
|  Adding a node:                                                         |
|  * Only keys between the new node and its predecessor move              |
|  * Minimal data redistribution: ~K/N keys move (K=total keys, N=nodes)  |
|                                                                         |
|  Problem: Uneven distribution with few nodes                            |
|  Solution: Virtual nodes                                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 6.2 VIRTUAL NODES (VNODES)

```
+--------------------------------------------------------------------------+
|                        VIRTUAL NODES                                     |
+--------------------------------------------------------------------------+
|                                                                          |
|  Each physical node maps to multiple positions on the ring:              |
|                                                                          |
|              A3    A1                                                    |
|               *    *                                                     |
|             /        \                                                   |
|           B2*          *B1                                               |
|           /              \                                               |
|         C1*               *A2                                            |
|           \              /                                               |
|           B3*          *C3                                               |
|             \        /                                                   |
|               *    *                                                     |
|              C2    B4                                                    |
|                                                                          |
|  Node A has vnodes: A1, A2, A3                                           |
|  Node B has vnodes: B1, B2, B3, B4                                       |
|  Node C has vnodes: C1, C2, C3                                           |
|                                                                          |
|  Benefits:                                                               |
|  +--------------------------------------------------------------------+  |
|  |  1. More uniform data distribution                                 |  |
|  |  2. Heterogeneous hardware: powerful nodes get more vnodes         |  |
|  |  3. When a node fails, its load is spread across many nodes        |  |
|  |     (not just the next node on the ring)                           |  |
|  |  4. Rebalancing is smoother when adding/removing nodes             |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
|  Typical: 100-256 virtual nodes per physical node                        |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 7: DATA REPLICATION

```
+--------------------------------------------------------------------------+
|                       DATA REPLICATION                                   |
+--------------------------------------------------------------------------+
|                                                                          |
|  Replication Factor N = 3 (store each key on 3 nodes):                   |
|                                                                          |
|  Key "user:123" hashes to position P on ring                             |
|  Walk clockwise: first 3 DISTINCT physical nodes = replicas              |
|  (skip vnodes of same physical node)                                     |
|                                                                          |
|                         P (key position)                                 |
|                         |                                                |
|                         v                                                |
|  ... ---[Node A]---[Node B]---[Node C]---[Node D]--- ...                 |
|          replica1    replica2    replica3                                |
|                                                                          |
|  Replication Strategies:                                                 |
|  +--------------------------------------------------------------------+  |
|  |                                                                    |  |
|  |  Synchronous Replication:                                          |  |
|  |  - Write to all N replicas before ACK                              |  |
|  |  - Pro: Strong consistency                                         |  |
|  |  - Con: Slow (limited by slowest replica), lower availability      |  |
|  |                                                                    |  |
|  |  Asynchronous Replication:                                         |  |
|  |  - Write to 1 node, async propagate to others                      |  |
|  |  - Pro: Fast writes, high availability                             |  |
|  |  - Con: May lose data if primary fails before propagation          |  |
|  |                                                                    |  |
|  |  Quorum-Based (Preferred):                                         |  |
|  |  - Write succeeds when W replicas ACK                              |  |
|  |  - Read succeeds when R replicas respond                           |  |
|  |  - Guarantee: W + R > N ensures overlap                            |  |
|  |                                                                    |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
|  Rack/DC-Aware Replication:                                              |
|  * Place replicas in different racks/availability zones                  |
|  * Survives rack failure or entire AZ outage                             |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 8: CONSISTENCY AND QUORUM

### 8.1 QUORUM CONFIGURATIONS

```
+-------------------------------------------------------------------------+
|                     QUORUM CONFIGURATIONS                               |
+-------------------------------------------------------------------------+
|                                                                         |
|  N = Total replicas per key                                             |
|  W = Write quorum (ACKs needed for write success)                       |
|  R = Read quorum (replicas read from)                                   |
|                                                                         |
|  Rule: W + R > N  =>  Strong consistency guarantee                      |
|                                                                         |
|  Common Configurations (N=3):                                           |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Config 1: W=2, R=2 (Balanced)                                    |  |
|  |  - Strong consistency (2+2 > 3)                                   |  |
|  |  - Tolerates 1 node failure for both reads and writes             |  |
|  |  - Good default choice                                            |  |
|  |                                                                   |  |
|  |  Config 2: W=3, R=1 (Write-heavy consistency)                     |  |
|  |  - Strong consistency (3+1 > 3)                                   |  |
|  |  - Fast reads, slow writes                                        |  |
|  |  - Write fails if any 1 node is down                              |  |
|  |                                                                   |  |
|  |  Config 3: W=1, R=3 (Read-heavy consistency)                      |  |
|  |  - Strong consistency (1+3 > 3)                                   |  |
|  |  - Fast writes, slow reads                                        |  |
|  |  - Good for write-heavy workloads                                 |  |
|  |                                                                   |  |
|  |  Config 4: W=1, R=1 (Eventual consistency)                        |  |
|  |  - NOT strongly consistent (1+1 = 2, NOT > 3)                     |  |
|  |  - Fastest reads and writes                                       |  |
|  |  - Risk of reading stale data                                     |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 8.2 CONSISTENCY LEVELS (CASSANDRA-STYLE)

```
+-------------------------------------------------------------------------+
|                     CONSISTENCY LEVELS                                  |
+-------------------------------------------------------------------------+
|                                                                         |
|  ONE:                                                                   |
|  * Write/Read from 1 replica                                            |
|  * Fastest, least consistent                                            |
|  * Use: Logging, metrics, non-critical data                             |
|                                                                         |
|  QUORUM:                                                                |
|  * Write/Read from floor(N/2) + 1 replicas                              |
|  * Strong consistency when used for both reads and writes               |
|  * Use: User profiles, account data                                     |
|                                                                         |
|  ALL:                                                                   |
|  * Write/Read from all N replicas                                       |
|  * Strongest consistency, lowest availability                           |
|  * Use: Financial transactions (rare in KV stores)                      |
|                                                                         |
|  LOCAL_QUORUM:                                                          |
|  * Quorum within the local datacenter only                              |
|  * Cross-DC replication is async                                        |
|  * Use: Multi-DC deployments, low-latency with local consistency        |
|                                                                         |
|  EACH_QUORUM:                                                           |
|  * Quorum in every datacenter                                           |
|  * Strongest multi-DC consistency                                       |
|  * Use: Critical data in multi-DC setups                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 9: VECTOR CLOCKS

```
+--------------------------------------------------------------------------+
|                        VECTOR CLOCKS                                     |
+--------------------------------------------------------------------------+
|                                                                          |
|  Purpose: Track causality and detect conflicts between replicas.         |
|                                                                          |
|  Each write carries a vector clock: {NodeA: 2, NodeB: 1, NodeC: 3}       |
|  Meaning: Node A has seen 2 writes, B seen 1, C seen 3.                  |
|                                                                          |
|  Example Scenario:                                                       |
|  +--------------------------------------------------------------------+  |
|  |                                                                    |  |
|  |  1. Client writes key "X" to Node A                                |  |
|  |     VC = {A:1}                                                     |  |
|  |                                                                    |  |
|  |  2. Client reads "X" from Node A, updates, writes to Node A        |  |
|  |     VC = {A:2}                                                     |  |
|  |                                                                    |  |
|  |  3. Network partition! Two clients update concurrently:            |  |
|  |     Client 1 writes to Node A: VC = {A:3}                          |  |
|  |     Client 2 writes to Node B: VC = {A:2, B:1}                     |  |
|  |                                                                    |  |
|  |  4. After partition heals, Node reads both:                        |  |
|  |     {A:3} vs {A:2, B:1}                                            |  |
|  |     Neither dominates the other -> CONFLICT!                       |  |
|  |     Both versions returned to client for resolution.               |  |
|  |                                                                    |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
|  Comparison Rules:                                                       |
|  +--------------------------------------------------------------------+  |
|  |  VC1 dominates VC2 if ALL components of VC1 >= VC2                 |  |
|  |  and at least one is strictly >                                    |  |
|  |                                                                    |  |
|  |  {A:3, B:2} dominates {A:2, B:1}  -> VC1 is newer, no conflict     |  |
|  |  {A:3} vs {A:2, B:1}              -> CONFLICT (concurrent writes)  |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
|  Alternative: Last-Write-Wins (LWW)                                      |
|  * Use wall-clock timestamps instead of vector clocks                    |
|  * Simpler but can lose writes (clock skew issues)                       |
|  * Cassandra uses LWW by default                                         |
|  * Dynamo uses vector clocks                                             |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 10: MERKLE TREES

```
+--------------------------------------------------------------------------+
|                        MERKLE TREES                                      |
+--------------------------------------------------------------------------+
|                                                                          |
|  Purpose: Efficiently detect and synchronize differences between         |
|  replicas (anti-entropy repair).                                         |
|                                                                          |
|  Structure: Binary tree of hashes                                        |
|                                                                          |
|                     Root Hash                                            |
|                    H(H12 + H34)                                          |
|                    /          \                                          |
|                  H12          H34                                        |
|               H(H1+H2)    H(H3+H4)                                       |
|               /    \       /    \                                        |
|             H1     H2    H3     H4                                       |
|             |      |     |      |                                        |
|           [K1,V1][K2,V2][K3,V3][K4,V4]                                   |
|                                                                          |
|  Each leaf = hash of a key range's data                                  |
|  Each internal node = hash of its children's hashes                      |
|                                                                          |
|  Anti-Entropy Sync Process:                                              |
|  +--------------------------------------------------------------------+  |
|  |                                                                    |  |
|  |  Node A and Node B each maintain a Merkle tree for shared data.    |  |
|  |                                                                    |  |
|  |  1. Compare root hashes                                            |  |
|  |     Root match? -> Replicas are in sync. Done.                     |  |
|  |     Root differs? -> Traverse children.                            |  |
|  |                                                                    |  |
|  |  2. Compare left child hashes                                      |  |
|  |     Match? -> Left subtree is in sync. Skip it.                    |  |
|  |     Differ? -> Recurse into left subtree.                          |  |
|  |                                                                    |  |
|  |  3. Compare right child hashes                                     |  |
|  |     Same logic as step 2.                                          |  |
|  |                                                                    |  |
|  |  4. At leaf level: exchange the actual key-value pairs that differ |  |
|  |                                                                    |  |
|  |  Efficiency: Only transfer O(log N) hashes to find differences     |  |
|  |  vs O(N) for full comparison                                       |  |
|  |                                                                    |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
|  Key Property:                                                           |
|  * Changing ANY key changes hashes all the way up to root                |
|  * Can detect even a single bit flip                                     |
|  * Commonly used in: Cassandra, Dynamo, Git, Bitcoin                     |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 11: GOSSIP PROTOCOL

```
+-------------------------------------------------------------------------+
|                       GOSSIP PROTOCOL                                   |
+-------------------------------------------------------------------------+
|                                                                         |
|  Purpose: Decentralized failure detection and cluster membership.       |
|  No master node needed.                                                 |
|                                                                         |
|  How it works:                                                          |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  1. Every T seconds (e.g., T=1s), each node picks a random node   |  |
|  |     and sends its membership list with heartbeat counters.        |  |
|  |                                                                   |  |
|  |  2. Membership list:                                              |  |
|  |     +--------------------------------------------------+          |  |
|  |     | Node  | Heartbeat | Timestamp    | Status        |          |  |
|  |     +--------------------------------------------------+          |  |
|  |     | A     | 42        | 1708000001   | ALIVE         |          |  |
|  |     | B     | 38        | 1708000000   | ALIVE         |          |  |
|  |     | C     | 15        | 1707999500   | SUSPECT       |          |  |
|  |     | D     | 55        | 1708000002   | ALIVE         |          |  |
|  |     +--------------------------------------------------+          |  |
|  |                                                                   |  |
|  |  3. Recipient merges incoming list with its own                   |  |
|  |     (keep higher heartbeat counts)                                |  |
|  |                                                                   |  |
|  |  4. If heartbeat for a node hasn't increased for T_fail seconds:  |  |
|  |     Mark as SUSPECT                                               |  |
|  |                                                                   |  |
|  |  5. If still no update after T_cleanup:                           |  |
|  |     Mark as DEAD, remove from membership                          |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Properties:                                                            |
|  * Eventually consistent: information spreads in O(log N) rounds        |
|  * Scalable: each node communicates with constant number of peers       |
|  * Fault tolerant: no single point of failure                           |
|  * Convergent: all nodes eventually reach same view                     |
|                                                                         |
|  Variants:                                                              |
|  * SWIM (Scalable Weakly-consistent Infection-style Membership)         |
|  * Uses direct probes + indirect probes for faster failure detection    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 12: HINTED HANDOFF

```
+-------------------------------------------------------------------------+
|                       HINTED HANDOFF                                    |
+-------------------------------------------------------------------------+
|                                                                         |
|  Purpose: Handle temporary node failures without violating              |
|  availability requirements.                                             |
|                                                                         |
|  Scenario:                                                              |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Key "X" should be stored on nodes [A, B, C]                      |  |
|  |  Node C is temporarily down.                                      |  |
|  |                                                                   |  |
|  |  Without hinted handoff:                                          |  |
|  |  - Write fails if W=3 (need all replicas)                         |  |
|  |  - Or write succeeds with W=2 but C has stale data later          |  |
|  |                                                                   |  |
|  |  With hinted handoff:                                             |  |
|  |  - Node D (next on ring after C) accepts write for C              |  |
|  |  - D stores it as a "hint": {key:X, value:V, intended_for:C}      |  |
|  |  - When C comes back online, D sends the hint to C                |  |
|  |  - D then deletes the hint                                        |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Flow:                                                                  |
|                                                                         |
|  +--------+      +--------+      +--------+      +--------+             |
|  | Node A |      | Node B |      | Node C |      | Node D |             |
|  |  (OK)  |      |  (OK)  |      | (DOWN) |      | (Hint  |             |
|  |        |      |        |      |        |      | holder)|             |
|  +---+----+      +---+----+      +--------+      +---+----+             |
|      |               |                                |                 |
|      | write X       | write X                        | hint for C      |
|      |<-----------+  |<-----------+        +--------->|                 |
|      |            |  |            |        |          |                 |
|      |       Coordinator          |        |          |                 |
|      |            |               |        |          |                 |
|      +            +               +        +          +                 |
|                                                                         |
|  When C recovers: D -> sends hint -> C stores data -> D deletes hint    |
|                                                                         |
|  Limitation: Hints have a TTL (e.g., 3 hours). If C is down longer,     |
|  anti-entropy repair via Merkle trees is needed.                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 13: READ REPAIR AND ANTI-ENTROPY

```
+-------------------------------------------------------------------------+
|                   READ REPAIR & ANTI-ENTROPY                            |
+-------------------------------------------------------------------------+
|                                                                         |
|  READ REPAIR (Foreground):                                              |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  During a read with R > 1:                                        |  |
|  |  1. Coordinator reads from R replicas                             |  |
|  |  2. Compares values and versions                                  |  |
|  |  3. Returns latest version to client                              |  |
|  |  4. If any replica had stale data:                                |  |
|  |     -> Send latest value to stale replica(s) in background        |  |
|  |                                                                   |  |
|  |  Example:                                                         |  |
|  |  - Read "key X" from nodes A, B                                   |  |
|  |  - A returns V2 (latest), B returns V1 (stale)                    |  |
|  |  - Return V2 to client                                            |  |
|  |  - Background: send V2 to B                                       |  |
|  |                                                                   |  |
|  |  Pros: Fixes inconsistencies during normal reads                  |  |
|  |  Cons: Only repairs data that is actually read                    |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ANTI-ENTROPY (Background):                                             |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Periodic background process using Merkle trees:                  |  |
|  |  1. Pairs of replicas compare their Merkle trees                  |  |
|  |  2. Identify divergent key ranges                                 |  |
|  |  3. Exchange and reconcile differing keys                         |  |
|  |                                                                   |  |
|  |  Frequency: Every few hours (configurable)                        |  |
|  |  Repairs ALL data, not just recently read data                    |  |
|  |                                                                   |  |
|  |  Combined with read repair:                                       |  |
|  |  - Read repair: fast, but partial coverage                        |  |
|  |  - Anti-entropy: slow, but complete coverage                      |  |
|  |  - Together: strong eventual consistency guarantee                |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 14: BLOOM FILTERS

```
+-------------------------------------------------------------------------+
|                        BLOOM FILTERS                                    |
+-------------------------------------------------------------------------+
|                                                                         |
|  Purpose: Quickly determine if a key MIGHT exist in an SSTable          |
|  without reading it from disk.                                          |
|                                                                         |
|  How it works:                                                          |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Bit Array: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  (m bits)              |  |
|  |                                                                   |  |
|  |  Insert "user:123":                                               |  |
|  |  - hash1("user:123") % m = 2  -> set bit 2                        |  |
|  |  - hash2("user:123") % m = 5  -> set bit 5                        |  |
|  |  - hash3("user:123") % m = 8  -> set bit 8                        |  |
|  |                                                                   |  |
|  |  Bit Array: [0, 0, 1, 0, 0, 1, 0, 0, 1, 0]                        |  |
|  |                                                                   |  |
|  |  Lookup "user:456":                                               |  |
|  |  - hash1 % m = 2 -> bit is 1 (OK)                                 |  |
|  |  - hash2 % m = 7 -> bit is 0 (STOP!)                              |  |
|  |  -> DEFINITELY NOT in this SSTable                                |  |
|  |                                                                   |  |
|  |  Lookup "user:789":                                               |  |
|  |  - hash1 % m = 2 -> bit is 1                                      |  |
|  |  - hash2 % m = 5 -> bit is 1                                      |  |
|  |  - hash3 % m = 8 -> bit is 1                                      |  |
|  |  -> MIGHT be in this SSTable (check disk to confirm)              |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Properties:                                                            |
|  * False Positives: YES (says "maybe" when key doesn't exist)           |
|  * False Negatives: NO  (never says "no" when key exists)               |
|  * Space: ~10 bits per key = ~1% false positive rate                    |
|  * Lookup: O(k) where k = number of hash functions                      |
|                                                                         |
|  Impact on Read Performance:                                            |
|  * Without Bloom filter: read every SSTable on disk (slow)              |
|  * With Bloom filter: skip SSTables that definitely don't have key      |
|  * Typically eliminates 99% of unnecessary disk reads                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 15: STORAGE ENGINES (LSM-TREE VS B-TREE)

### 15.1 LSM-TREE (LOG-STRUCTURED MERGE TREE)

```
+-------------------------------------------------------------------------+
|                        LSM-TREE                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  Used by: Cassandra, HBase, RocksDB, LevelDB, ScyllaDB                  |
|                                                                         |
|  Write Path:                                                            |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  1. Append to Write-Ahead Log (WAL) on disk - sequential write    |  |
|  |  2. Insert into MemTable (in-memory sorted structure)             |  |
|  |  3. When MemTable full -> flush to disk as SSTable (immutable)    |  |
|  |  4. Compaction merges SSTables in background                      |  |
|  |                                                                   |  |
|  |  Write: O(1) amortized (sequential append)                        |  |
|  |  Very fast writes!                                                |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Read Path:                                                             |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  1. Check MemTable                                                |  |
|  |  2. Check Bloom filter for each SSTable                           |  |
|  |  3. Binary search in matching SSTables (newest first)             |  |
|  |                                                                   |  |
|  |  Read: O(log N) per SSTable, may check multiple SSTables          |  |
|  |  Slower reads than B-Tree (but Bloom filters help)                |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Structure on Disk:                                                     |
|  +-------------------------------------------------------------------+  |
|  |  Level 0: [SST-1] [SST-2] [SST-3]   (may overlap)                 |  |
|  |  Level 1: [    SST-A    ] [    SST-B    ]  (no overlap)           |  |
|  |  Level 2: [  SST-X  ] [  SST-Y  ] [  SST-Z  ]  (no overlap)       |  |
|  |                                                                   |  |
|  |  Each level is ~10x larger than previous                          |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 15.2 B-TREE

```
+-------------------------------------------------------------------------+
|                          B-TREE                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  Used by: MySQL (InnoDB), PostgreSQL, etcd (BoltDB)                     |
|                                                                         |
|  Structure:                                                             |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Balanced tree of fixed-size pages (typically 4KB - 16KB)         |  |
|  |                                                                   |  |
|  |              [  10 | 20 | 30  ]        (root page)                |  |
|  |             /    |      |     \                                   |  |
|  |  [1|5|8]  [11|15|18]  [21|25|28]  [31|35|40]   (leaf pages)       |  |
|  |                                                                   |  |
|  |  Writes: Update page in-place (random I/O)                        |  |
|  |  Reads: Traverse tree from root to leaf: O(log N)                 |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Write Path:                                                            |
|  * Find correct leaf page                                               |
|  * Update value in place (or split page if full)                        |
|  * Write = random I/O (slower on HDD, OK on SSD)                        |
|                                                                         |
|  Read Path:                                                             |
|  * Traverse from root to leaf: O(log_B N)                               |
|  * Very efficient for point lookups and range scans                     |
|  * One read per tree level (typically 3-4 levels)                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 15.3 COMPARISON

```
+-------------------------------------------------------------------------+
|                   LSM-TREE vs B-TREE COMPARISON                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  Aspect            | LSM-Tree          | B-Tree                         |
|  ------------------+-------------------+------------------------------  |
|  Write speed       | Very fast         | Moderate                       |
|                    | (sequential I/O)  | (random I/O)                   |
|  Read speed        | Moderate          | Fast                           |
|                    | (multiple levels) | (single traversal)             |
|  Write amplif.     | Higher            | Lower                          |
|                    | (compaction)      | (in-place update)              |
|  Space amplif.     | Higher            | Lower                          |
|                    | (temp duplicates) | (in-place)                     |
|  Compression       | Better            | Worse                          |
|                    | (immutable files) | (partial pages)                |
|  Concurrency       | Better            | Good                           |
|                    | (no in-place mut) | (page-level locks)             |
|  Range scans       | Good              | Excellent                      |
|  Space reclaim     | Via compaction    | Immediate (in-place)           |
|  Best for          | Write-heavy       | Read-heavy                     |
|                    | workloads         | workloads                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 16: COMPACTION STRATEGIES

```
+--------------------------------------------------------------------------+
|                     COMPACTION STRATEGIES                                |
+--------------------------------------------------------------------------+
|                                                                          |
|  SIZE-TIERED COMPACTION (STCS):                                          |
|  +--------------------------------------------------------------------+  |
|  |                                                                    |  |
|  |  Merge SSTables of similar size together.                          |  |
|  |                                                                    |  |
|  |  [1MB] [1MB] [1MB] [1MB]  -> Merge -> [4MB]                        |  |
|  |  [4MB] [4MB] [4MB] [4MB]  -> Merge -> [16MB]                       |  |
|  |                                                                    |  |
|  |  Pros:                                                             |  |
|  |  + Write-optimized (less compaction overhead)                      |  |
|  |  + Good write throughput                                           |  |
|  |                                                                    |  |
|  |  Cons:                                                             |  |
|  |  - Higher space amplification (up to 2x temporarily)               |  |
|  |  - Worse read performance (more SSTables to check)                 |  |
|  |  - Large compactions can cause I/O spikes                          |  |
|  |                                                                    |  |
|  |  Used by: Cassandra (default), HBase                               |  |
|  |                                                                    |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
|  LEVELED COMPACTION (LCS):                                               |
|  +--------------------------------------------------------------------+  |
|  |                                                                    |  |
|  |  Organize SSTables into levels with size bounds.                   |  |
|  |  Each level is ~10x the size of the previous.                      |  |
|  |  Within a level, SSTables don't overlap in key range.              |  |
|  |                                                                    |  |
|  |  L0: [SST] [SST] [SST]     (may overlap, from MemTable flushes)    |  |
|  |  L1: [SST-a] [SST-b] [SST-c]            (10 MB total, no overlap)  |  |
|  |  L2: [SST-1] [SST-2] ... [SST-10]       (100 MB, no overlap)       |  |
|  |  L3: [SST-1] [SST-2] ... [SST-100]      (1 GB, no overlap)         |  |
|  |                                                                    |  |
|  |  When L_i is full: pick an SSTable, merge with overlapping         |  |
|  |  SSTables in L_(i+1)                                               |  |
|  |                                                                    |  |
|  |  Pros:                                                             |  |
|  |  + Better read performance (fewer SSTables per level)              |  |
|  |  + Bounded space amplification (~10%)                              |  |
|  |  + More predictable read latencies                                 |  |
|  |                                                                    |  |
|  |  Cons:                                                             |  |
|  |  - Higher write amplification (~10x)                               |  |
|  |  - More background I/O from compaction                             |  |
|  |                                                                    |  |
|  |  Used by: LevelDB, RocksDB (configurable)                          |  |
|  |                                                                    |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 17: DATABASE SCHEMA / DATA MODEL

```
+--------------------------------------------------------------------------+
|                     INTERNAL DATA MODEL                                  |
+--------------------------------------------------------------------------+
|                                                                          |
|  Key-Value Record Format:                                                |
|  +--------------------------------------------------------------------+  |
|  |  +----------+--------+-------+----------+--------+------+          |  |
|  |  | Key Size | Key    | Value | Timestamp| Tombstone| CRC |         |  |
|  |  | (4 bytes)| (var)  | Size  | (8 bytes)| Flag   | (4B) |          |  |
|  |  |          |        |(4B)   |          | (1B)   |      |          |  |
|  |  +----------+--------+-------+----------+--------+------+          |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
|  SSTable Format:                                                         |
|  +--------------------------------------------------------------------+  |
|  |  +----------------------------+                                    |  |
|  |  | Data Block 1               |  Sorted key-value pairs            |  |
|  |  +----------------------------+                                    |  |
|  |  | Data Block 2               |                                    |  |
|  |  +----------------------------+                                    |  |
|  |  | ...                        |                                    |  |
|  |  +----------------------------+                                    |  |
|  |  | Data Block N               |                                    |  |
|  |  +----------------------------+                                    |  |
|  |  | Index Block                |  Sparse index: key -> block offset |  |
|  |  +----------------------------+                                    |  |
|  |  | Bloom Filter Block         |  For quick key existence check     |  |
|  |  +----------------------------+                                    |  |
|  |  | Footer                     |  Offsets to index and bloom        |  |
|  |  +----------------------------+                                    |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
|  Cluster Metadata (stored via Gossip or Zookeeper):                      |
|  +--------------------------------------------------------------------+  |
|  |  - Token ring assignments (which node owns which range)            |  |
|  |  - Node membership and health status                               |  |
|  |  - Schema/keyspace definitions                                     |  |
|  |  - Hint storage (pending handoffs)                                 |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 18: API DESIGN

```
+-------------------------------------------------------------------------+
|                          API DESIGN                                     |
+-------------------------------------------------------------------------+
|                                                                         |
|  PUT /api/v1/kv/{key}                                                   |
|  Request:                                                               |
|  {                                                                      |
|    "value": "base64_encoded_bytes",                                     |
|    "consistency": "QUORUM",                                             |
|    "ttl": 3600,                                                         |
|    "if_not_exists": false                                               |
|  }                                                                      |
|  Response: { "status": "ok", "version": "v42" }                         |
|                                                                         |
|  GET /api/v1/kv/{key}                                                   |
|  Query params: ?consistency=QUORUM                                      |
|  Response:                                                              |
|  {                                                                      |
|    "key": "user:123",                                                   |
|    "value": "base64_encoded_bytes",                                     |
|    "version": "v42",                                                    |
|    "timestamp": 1708000001,                                             |
|    "ttl_remaining": 3200                                                |
|  }                                                                      |
|                                                                         |
|  DELETE /api/v1/kv/{key}                                                |
|  Query params: ?consistency=QUORUM                                      |
|  Response: { "status": "ok" }                                           |
|  Note: Internally writes a tombstone, not actual deletion               |
|                                                                         |
|  POST /api/v1/kv/batch                                                  |
|  Request:                                                               |
|  {                                                                      |
|    "operations": [                                                      |
|      { "type": "get", "key": "user:123" },                              |
|      { "type": "get", "key": "user:456" },                              |
|      { "type": "put", "key": "user:789", "value": "..." }               |
|    ]                                                                    |
|  }                                                                      |
|                                                                         |
|  Internal RPC (node-to-node):                                           |
|  * ReplicaWrite(key, value, version, hint_target)                       |
|  * ReplicaRead(key, consistency)                                        |
|  * GossipDigest(node_states)                                            |
|  * MerkleTreeExchange(token_range, tree_hash)                           |
|  * HintedHandoff(key, value, target_node)                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 19: COMPARISON: DYNAMO VS CASSANDRA VS REDIS VS ETCD

```
+-------------------------------------------------------------------------+
|               KEY-VALUE STORE COMPARISON                                |
+-------------------------------------------------------------------------+
|                                                                         |
|  Feature        | Dynamo    | Cassandra | Redis    | etcd               |
|  ---------------+-----------+-----------+----------+------------------  |
|  Developer      | Amazon    | Apache    | Redis    | CoreOS/CNCF        |
|  Data model     | KV        | Wide-col  | KV+DS   | KV                  |
|  Consistency    | AP        | Tunable   | Varies   | CP (Raft)          |
|  Storage        | Pluggable | LSM-Tree  | In-mem   | B-Tree (bbolt)     |
|  Replication    | Quorum    | Quorum    | Async    | Raft consensus     |
|  Partitioning   | Cons hash | Cons hash | Sharding | No partitioning    |
|  Conflict res.  | Vec clock | LWW       | LWW      | N/A (strong)       |
|  Failure detect | Gossip    | Gossip    | Sentinel | Raft heartbeat     |
|  Primary use    | Shopping  | Time-     | Caching, | Config, service    |
|                 | cart,     | series,   | sessions | discovery,         |
|                 | sessions  | IoT, logs | queues   | leader election    |
|  Scale          | PB-scale  | PB-scale  | TB-scale | GB-scale           |
|  Latency        | ~5-10ms   | ~2-10ms   | <1ms     | ~2-10ms            |
|                                                                         |
+-------------------------------------------------------------------------+
```

```
+--------------------------------------------------------------------------+
|                  WHEN TO USE WHICH?                                      |
+--------------------------------------------------------------------------+
|                                                                          |
|  Use Dynamo/DynamoDB when:                                               |
|  * AWS ecosystem                                                         |
|  * Managed service preferred                                             |
|  * Simple KV with predictable workloads                                  |
|  * Need single-digit millisecond latency at any scale                    |
|                                                                          |
|  Use Cassandra when:                                                     |
|  * Write-heavy workloads (IoT, time-series, logs)                        |
|  * Need to operate across multiple datacenters                           |
|  * Wide-column data model fits (query by partition key + clustering)     |
|  * Petabyte scale with linear scalability                                |
|                                                                          |
|  Use Redis when:                                                         |
|  * Sub-millisecond latency required                                      |
|  * Data fits in memory                                                   |
|  * Caching, session store, real-time leaderboards                        |
|  * Rich data structures needed (lists, sets, sorted sets, streams)       |
|                                                                          |
|  Use etcd when:                                                          |
|  * Strong consistency required (CP system)                               |
|  * Configuration storage, service discovery                              |
|  * Leader election, distributed locking                                  |
|  * Small dataset (< few GB)                                              |
|  * Kubernetes ecosystem                                                  |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 20: MONITORING AND OBSERVABILITY

```
+-------------------------------------------------------------------------+
|                   MONITORING & OBSERVABILITY                            |
+-------------------------------------------------------------------------+
|                                                                         |
|  Node-Level Metrics:                                                    |
|  +-------------------------------------------------------------------+  |
|  |  - Read/Write latency (p50, p95, p99, p999)                       |  |
|  |  - Operations per second (QPS)                                    |  |
|  |  - Disk utilization and I/O throughput                            |  |
|  |  - MemTable size and flush frequency                              |  |
|  |  - SSTable count per level                                        |  |
|  |  - Compaction pending bytes and throughput                        |  |
|  |  - Bloom filter false positive rate                               |  |
|  |  - GC pause times (if JVM-based like Cassandra)                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Cluster-Level Metrics:                                                 |
|  +-------------------------------------------------------------------+  |
|  |  - Node count and health status                                   |  |
|  |  - Replication lag                                                |  |
|  |  - Cross-DC latency                                               |  |
|  |  - Data distribution (hotspots?)                                  |  |
|  |  - Hinted handoff queue depth                                     |  |
|  |  - Read repair rate                                               |  |
|  |  - Gossip convergence time                                        |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Alerts:                                                                |
|  +-------------------------------------------------------------------+  |
|  |  - p99 latency > 50ms                                             |  |
|  |  - Disk usage > 80%                                               |  |
|  |  - Node unreachable for > 30 seconds                              |  |
|  |  - Compaction falling behind (pending > threshold)                |  |
|  |  - Hinted handoff queue growing                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 21: FAILURE SCENARIOS AND MITIGATIONS

```
+-------------------------------------------------------------------------+
|                 FAILURE SCENARIOS & MITIGATIONS                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  Scenario 1: Single Node Failure                                        |
|  +-------------------------------------------------------------------+  |
|  |  Detection: Gossip protocol (within seconds)                      |  |
|  |  Impact: Reduced redundancy for affected key ranges               |  |
|  |  Mitigation:                                                      |  |
|  |  - Hinted handoff for in-flight writes                            |  |
|  |  - Read/write continues with remaining replicas                   |  |
|  |  - Alert ops team to replace node                                 |  |
|  |  - Once replaced: streaming repair from replicas                  |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Scenario 2: Network Partition                                          |
|  +-------------------------------------------------------------------+  |
|  |  Impact: Nodes can't communicate across partition                 |  |
|  |  AP behavior (Dynamo/Cassandra):                                  |  |
|  |  - Both sides continue serving reads and writes                   |  |
|  |  - Conflicting writes resolved after healing                      |  |
|  |  - Vector clocks or LWW for resolution                            |  |
|  |  CP behavior (etcd):                                              |  |
|  |  - Minority partition becomes read-only                           |  |
|  |  - Majority partition continues normal operation                  |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Scenario 3: Disk Corruption                                            |
|  +-------------------------------------------------------------------+  |
|  |  Detection: CRC checksums on every record                         |  |
|  |  Impact: Data loss on affected node                               |  |
|  |  Mitigation:                                                      |  |
|  |  - Merkle tree repair from healthy replicas                       |  |
|  |  - Replace corrupted SSTable files                                |  |
|  |  - Worst case: rebuild node from scratch via streaming            |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Scenario 4: Hot Key (celebrity problem)                                |
|  +-------------------------------------------------------------------+  |
|  |  Impact: Single node overwhelmed by traffic to one key            |  |
|  |  Mitigation:                                                      |  |
|  |  - Client-side caching for hot reads                              |  |
|  |  - Read from replicas (spread load)                               |  |
|  |  - Key splitting: "hot_key" -> "hot_key_1", "hot_key_2"           |  |
|  |  - Application-level caching (Redis in front)                     |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Scenario 5: Datacenter Failure                                         |
|  +-------------------------------------------------------------------+  |
|  |  Impact: Entire DC unreachable                                    |  |
|  |  Mitigation:                                                      |  |
|  |  - Multi-DC replication (NetworkTopologyStrategy)                 |  |
|  |  - LOCAL_QUORUM continues in surviving DCs                        |  |
|  |  - DNS failover for clients                                       |  |
|  |  - After DC recovery: full anti-entropy repair                    |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DETAILED WRITE/READ PATHS AND STATE MANAGEMENT

```
+-------------------------------------------------------------------------+
|                                                                        |
|  1. ENTITY STATE MACHINE (Key-Value Pair Write Path)                   |
|                                                                        |
|    [CLIENT_WRITE]                                                      |
|         |                                                              |
|         v                                                              |
|    [COORDINATOR] -- routes via consistent hashing to N replicas        |
|         |                                                              |
|         v (on each replica node)                                       |
|    [WAL_APPENDED] --> [MEMTABLE_WRITTEN] --> [ACK_TO_COORDINATOR]      |
|                            |                                           |
|              (MemTable full, threshold reached)                        |
|                            v                                           |
|                     [FLUSHED_TO_SSTABLE] --> [COMPACTED]               |
|                                                                        |
|    For deletes, a tombstone marker is written (same path).             |
|    The actual data is removed during compaction.                       |
|                                                                        |
|    Quorum state (coordinator perspective):                             |
|    [WRITE_SENT] --> [W_ACKS_RECEIVED] --> [ACK_TO_CLIENT]              |
|         |                                                              |
|         +---> [HINTED_HANDOFF] (if replica node is down,               |
|                hint stored on coordinator for later delivery)          |
|                                                                        |
|  ====================================================================  |
|                                                                        |
|  2. CRITICAL WRITE PATH (LSM-Tree: WAL -> MemTable -> SSTable)         |
|                                                                        |
|    Client: PUT /api/v1/kv/{key} { value, consistency: "QUORUM" }       |
|      |                                                                 |
|      v                                                                 |
|    Step 1: Coordinator receives request                                |
|      |     Hash(key) -> position on consistent hash ring               |
|      |     Identify N=3 replica nodes (walk ring clockwise)            |
|      |     Send write to all 3 replicas in parallel                    |
|      v                                                                 |
|    Step 2: On EACH replica node (the critical I/O path):               |
|      |                                                                 |
|      |  a) Append to Write-Ahead Log (WAL) -- sequential disk write    |
|      |     WAL entry: [key_size|key|value_size|value|timestamp|CRC]    |
|      |     fsync() to guarantee durability                             |
|      |                                                                 |
|      |  b) Insert into MemTable (in-memory sorted structure)           |
|      |     MemTable is a skip list or red-black tree                   |
|      |     Key -> { value, timestamp, tombstone_flag }                 |
|      |                                                                 |
|      |  c) Return ACK to coordinator                                   |
|      v                                                                 |
|    Step 3: Coordinator waits for W=2 ACKs (quorum)                     |
|      |     If W acks received -> return success to client              |
|      |     If replica down -> store hint for hinted handoff            |
|      v                                                                 |
|    Step 4: Background flush (when MemTable reaches threshold)          |
|      |     Freeze current MemTable, create new one                     |
|      |     Write frozen MemTable to disk as immutable SSTable:         |
|      |       [Data Blocks (sorted KV)] + [Index Block] +               |
|      |       [Bloom Filter Block] + [Footer]                           |
|      |     Delete corresponding WAL segment                            |
|      v                                                                 |
|    Step 5: Background compaction (merge SSTables)                      |
|      |     Leveled or size-tiered strategy                             |
|      |     Merge overlapping SSTables, remove tombstones               |
|      |     older than gc_grace_seconds                                 |
|                                                                        |
|    WRITE ORDER: WAL (disk) -> MemTable (memory) -> ACK                 |
|    Durability: WAL survives crashes; MemTable rebuilt from WAL         |
|                                                                        |
|  ====================================================================  |
|                                                                        |
|  3. READ PATH (MemTable -> Bloom Filter -> SSTables)                   |
|                                                                        |
|    Client: GET /api/v1/kv/{key} ?consistency=QUORUM                    |
|      |                                                                 |
|      v                                                                 |
|    Step 1: Coordinator routes to N=3 replicas                          |
|      |     Send read request to all 3 in parallel                      |
|      |     Wait for R=2 responses (quorum read)                        |
|      v                                                                 |
|    Step 2: On EACH replica (local read path):                          |
|      |                                                                 |
|      |  a) Check MemTable (current + frozen)                           |
|      |     Found? -> return immediately (freshest data)                |
|      |                                                                 |
|      |  b) Check Bloom filter for each SSTable (newest first)          |
|      |     Bloom says "definitely not here" -> skip SSTable            |
|      |     Bloom says "maybe here" -> check SSTable                    |
|      |                                                                 |
|      |  c) Binary search SSTable index block -> read data block        |
|      |     Return value with highest timestamp                         |
|      v                                                                 |
|    Step 3: Coordinator reconciles R=2 responses                        |
|      |     Compare vector clocks / timestamps                          |
|      |     Return value with latest version to client                  |
|      v                                                                 |
|    Step 4: Read repair (if versions differ)                            |
|      |     Send latest version to stale replica (async)                |
|      |     Stale replica writes the newer value via normal path        |
|                                                                        |
|    Read-repair keeps replicas converging without full anti-entropy.    |
|    Merkle tree comparison runs periodically for bulk repair.           |
|                                                                        |
|  ====================================================================  |
|                                                                        |
|  4. FAILURE SCENARIOS                                                  |
|                                                                        |
|  What Fails               | Impact & Recovery                          |
|  -------------------------+--------------------------------------------+
|  Single replica node down | Hinted handoff: coordinator stores hints.  |
|                           | Reads/writes succeed via remaining quorum  |
|                           | (W=2 of 3, R=2 of 3 still achievable).     |
|                           | On node recovery, hints replayed.          |
|  -------------------------+--------------------------------------------+
|  MemTable lost (crash     | WAL replayed on restart to rebuild         |
|  before flush)            | MemTable. No data loss because WAL is      |
|                           | fsync'd before ACK. Recovery time is       |
|                           | proportional to WAL size.                  |
|  -------------------------+--------------------------------------------+
|  Network partition         | AP system: both sides accept writes.      |
|  (split-brain)            | After partition heals, read repair and     |
|                           | anti-entropy (Merkle trees) reconcile.     |
|                           | Conflicts resolved via vector clocks       |
|                           | or last-write-wins (LWW).                  |
|  -------------------------+--------------------------------------------+
|  Compaction storm         | Too many SSTables -> reads slow down.      |
|  (compaction falls behind)| Throttle writes if L0 SSTable count >      |
|                           | threshold. Prioritize compaction threads.  |
|                           | Monitor SSTable count as key metric.       |
|  -------------------------+--------------------------------------------+
|                                                                        |
|  ====================================================================  |
|                                                                        |
|  5. CLEANUP / EXPIRY                                                   |
|                                                                        |
|    Tombstone Garbage Collection:                                       |
|      Deletes write a tombstone marker (not immediate removal)          |
|      Tombstones kept for gc_grace_seconds (default: 10 days)           |
|      During compaction, tombstones older than gc_grace are purged      |
|      CRITICAL: all replicas must participate in compaction before      |
|      gc_grace expires, or deleted data may resurrect                   |
|                                                                        |
|    TTL-Based Expiration:                                               |
|      Keys with TTL get expiration timestamp in record                  |
|      On read: if timestamp + TTL < now, treat as not found             |
|      On compaction: expired keys are dropped (same as tombstone)       |
|                                                                        |
|    Anti-Entropy (Merkle Tree Repair):                                  |
|      Periodic job (e.g., every 1 hour per token range)                 |
|      Compare Merkle tree roots between replica pairs                   |
|      Differing subtrees trigger targeted data sync                     |
|      Ensures eventual convergence even without read traffic            |
|                                                                        |
|    Hint Expiry:                                                        |
|      Hinted handoff entries expire after max_hint_window (3 hours)     |
|      If target node doesn't recover in time, rely on anti-entropy      |
|                                                                        |
+-------------------------------------------------------------------------+
```

## SECTION 22: INTERVIEW Q&A

### Q1: Why use consistent hashing instead of simple hash partitioning?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|  Simple hash: key % N_nodes. If you add/remove a node, N changes        |
|  and almost ALL keys remap -> massive data movement.                    |
|                                                                         |
|  Consistent hashing: Only K/N keys move when adding/removing a node     |
|  (K = total keys, N = total nodes). This is the minimum possible.       |
|                                                                         |
|  With virtual nodes, even this redistribution is spread evenly          |
|  across many nodes instead of burdening just one neighbor.              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q2: Explain the CAP theorem and where this system sits.

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Answer:                                                                 |
|  CAP: In a distributed system, during a network partition, you can       |
|  guarantee either Consistency OR Availability, but not both.             |
|                                                                          |
|  * Dynamo/Cassandra: AP (Available + Partition-tolerant)                 |
|    Both sides of partition continue serving requests.                    |
|    Conflicts resolved after partition heals.                             |
|                                                                          |
|  * etcd/Zookeeper: CP (Consistent + Partition-tolerant)                  |
|    Minority partition refuses writes.                                    |
|    Strong consistency guaranteed.                                        |
|                                                                          |
|  Our KV store is AP by default, with tunable consistency.                |
|  Setting W + R > N provides strong consistency during normal operation   |
|  but may sacrifice availability during partitions.                       |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Q3: What happens when you delete a key? Why tombstones?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|  You can't just remove the key -- other replicas still have it.         |
|  If you simply delete locally, read repair or anti-entropy would        |
|  "resurrect" the key from other replicas.                               |
|                                                                         |
|  Instead: Write a TOMBSTONE (a special marker saying "deleted at        |
|  timestamp T"). The tombstone is replicated like any other write.       |
|                                                                         |
|  Tombstones are garbage collected after gc_grace_seconds (default:      |
|  10 days in Cassandra). By then, all replicas should have seen the      |
|  tombstone through anti-entropy or read repair.                         |
|                                                                         |
|  Risk: If a node is down longer than gc_grace_seconds, it might         |
|  resurrect deleted data. Must run repair before bringing it back.       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q4: How do you handle a hot partition / hot key?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|  Problem: One key gets disproportionate traffic (e.g., celebrity post). |
|                                                                         |
|  Solutions:                                                             |
|  1. Application caching: Cache hot keys in Redis/Memcached              |
|  2. Key splitting: Append random suffix (key_1, key_2, ... key_10)      |
|     Read from random suffix, aggregate if needed                        |
|  3. Read replicas: Route reads to all N replicas (not just R)           |
|  4. Client-side caching with short TTL                                  |
|  5. Rate limiting per key                                               |
|  6. Detect hot keys in real-time and apply special handling             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q5: Why is W + R > N important?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|  If W + R > N, at least one node in the read quorum must have the       |
|  latest write. This guarantees the read will see the most recent data.  |
|                                                                         |
|  Example (N=3, W=2, R=2):                                               |
|  * Write goes to nodes {A, B} (W=2)                                     |
|  * Read goes to nodes {B, C} (R=2)                                      |
|  * Overlap: Node B has the latest write                                 |
|  * Coordinator picks the newest version from R responses                |
|                                                                         |
|  If W + R <= N, there could be no overlap -> stale read possible.       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q6: Explain write amplification in LSM-Trees.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|  Write amplification = total bytes written to disk / bytes written by   |
|  application.                                                           |
|                                                                         |
|  In LSM-Tree, data is written multiple times:                           |
|  1. WAL (1x)                                                            |
|  2. MemTable flush to L0 SSTable (1x)                                   |
|  3. Compaction L0 -> L1 (1x)                                            |
|  4. Compaction L1 -> L2 (1x)                                            |
|  5. Compaction L2 -> L3 (1x)                                            |
|  ...                                                                    |
|                                                                         |
|  Leveled compaction: ~10x write amplification per level                 |
|  Size-tiered: ~4x write amplification (less, but more space used)       |
|                                                                         |
|  Trade-off: High write amplification = better read performance          |
|  (data is more organized on disk after compaction)                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q7: How does a new node join the cluster?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|  1. New node contacts a seed node (well-known bootstrap node)           |
|  2. Receives cluster topology via gossip                                |
|  3. Assigned token ranges (virtual nodes on the hash ring)              |
|  4. Streaming: receives data from existing nodes that own those ranges  |
|  5. Once streaming complete, starts serving reads and writes            |
|  6. Gossip propagates the new membership to all nodes                   |
|                                                                         |
|  During streaming:                                                      |
|  * Existing nodes continue serving requests (no downtime)               |
|  * New node starts accepting writes immediately (hinted until ready)    |
|  * Process can take minutes to hours depending on data volume           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q8: Vector clocks vs Last-Write-Wins -- trade-offs?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|                                                                         |
|  Vector Clocks:                                                         |
|  + No data loss (concurrent writes both preserved)                      |
|  + Client can make intelligent merge decisions                          |
|  * Complex: vector grows with number of writers                         |
|  * Client must handle conflict resolution                               |
|  * Used by: Dynamo, Riak                                                |
|                                                                         |
|  Last-Write-Wins (LWW):                                                 |
|  + Simple implementation                                                |
|  + No client-side conflict resolution needed                            |
|  * Can silently lose writes (clock skew)                                |
|  * Depends on synchronized clocks (NTP)                                 |
|  * Used by: Cassandra (default)                                         |
|                                                                         |
|  Recommendation:                                                        |
|  * LWW for most use cases (simpler, good enough)                        |
|  * Vector clocks when every write matters (shopping carts, counters)    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q9: How do Bloom filters help read performance?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|  Without Bloom filters: To find a key, you might need to check          |
|  every SSTable on disk (could be dozens). Each check = disk I/O.        |
|                                                                         |
|  With Bloom filters: Each SSTable has an in-memory Bloom filter.        |
|  Before reading from disk, check the Bloom filter:                      |
|  * "Definitely not here" -> skip this SSTable (no disk I/O)             |
|  * "Maybe here" -> read from disk to confirm                            |
|                                                                         |
|  With 1% false positive rate (10 bits per key):                         |
|  * 99% of unnecessary disk reads are eliminated                         |
|  * Only ~1% of Bloom filter "yes" answers are false positives           |
|  * Memory cost: ~1.25 bytes per key                                     |
|                                                                         |
|  For 10 billion keys: ~12.5 GB of Bloom filters in memory               |
|  (very affordable for the massive I/O savings)                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q10: How would you implement TTL (time-to-live)?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|  1. Store expiration timestamp with each key-value record               |
|     { key, value, timestamp, ttl_expiry }                               |
|                                                                         |
|  2. On read: check if current_time > ttl_expiry                         |
|     If expired: treat as not found, return null                         |
|                                                                         |
|  3. On compaction: discard expired records                              |
|     (this is the actual deletion)                                       |
|                                                                         |
|  4. For exact TTL: background sweeper process                           |
|     * Scans for expired keys periodically                               |
|     * Removes them proactively (not just on read/compaction)            |
|                                                                         |
|  5. Optimization: TTL-based compaction                                  |
|     * Group records with similar TTLs in same SSTable                   |
|     * Drop entire SSTable when all records expired                      |
|     * Much more efficient than per-record expiry checking               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q11: How do you handle datacenter-level replication?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|  1. NetworkTopologyStrategy (Cassandra approach):                       |
|     * Specify replication factor per datacenter                         |
|     * Example: DC-East: 3, DC-West: 3 (6 total replicas)                |
|                                                                         |
|  2. Write path:                                                         |
|     * LOCAL_QUORUM: quorum in local DC only (fast)                      |
|     * Async replication to remote DC                                    |
|                                                                         |
|  3. Read path:                                                          |
|     * LOCAL_QUORUM: read from local DC only                             |
|     * Low latency (no cross-DC round trip)                              |
|                                                                         |
|  4. Conflict resolution:                                                |
|     * Cross-DC writes may conflict                                      |
|     * LWW or vector clocks resolve during read repair                   |
|                                                                         |
|  5. Benefits:                                                           |
|     * Survive entire DC failure                                         |
|     * Low-latency reads from local DC                                   |
|     * Geo-distributed for user proximity                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION N: WRAP-UP

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SUMMARY OF KEY DESIGN DECISIONS:                                       |
|                                                                         |
|  1. CONSISTENT HASHING with virtual nodes for even data distribution.   |
|  2. QUORUM-BASED REPLICATION: W + R > N for strong consistency.         |
|     Tunable per request (W=1,R=1 for speed; W=N,R=1 for durability).    |
|  3. VECTOR CLOCKS for conflict detection on concurrent writes.          |
|     Last-write-wins (LWW) as simpler alternative where acceptable.      |
|  4. GOSSIP PROTOCOL for membership and failure detection.               |
|  5. MERKLE TREES for anti-entropy (detect and repair replica drift).    |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  KEY TRADE-OFFS:                                                        |
|                                                                         |
|  * CONSISTENCY vs AVAILABILITY (CAP): Dynamo chose AP (available        |
|    under partition). Tunable quorum lets users pick their point.        |
|  * VECTOR CLOCKS vs LWW: Vector clocks detect all conflicts but         |
|    grow unbounded. LWW is simple but silently loses concurrent writes.  |
|  * GOSSIP vs CENTRALIZED MEMBERSHIP: Gossip is decentralized (no        |
|    SPOF) but convergence takes O(log N) rounds.
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 23: SUMMARY: KEY DESIGN DECISIONS

```
+--------------------------------------------------------------------------+
|                     KEY DESIGN DECISIONS                                 |
+--------------------------------------------------------------------------+
|                                                                          |
|  Decision              | Choice           | Rationale                    |
|  ----------------------+------------------+----------------------------  |
|  Partitioning          | Consistent hash  | Minimal data movement        |
|                        | + virtual nodes  | on rebalance                 |
|  Replication           | Quorum-based     | Tunable consistency          |
|                        | (N=3, W=2, R=2)  | with high availability       |
|  Conflict resolution   | Vector clocks    | No silent data loss          |
|                        | (or LWW)         | (LWW for simplicity)         |
|  Failure detection     | Gossip protocol  | Decentralized, no SPOF       |
|  Storage engine        | LSM-Tree         | Write-optimized              |
|  Anti-entropy          | Merkle trees     | Efficient diff detection     |
|  Temp failure handling | Hinted handoff   | Maintains availability       |
|  Lookup optimization   | Bloom filters    | Eliminates 99% false reads   |
|  Architecture          | Masterless       | No single point of failure   |
|                                                                          |
+--------------------------------------------------------------------------+
```

*End of Distributed Key-Value Store System Design*
