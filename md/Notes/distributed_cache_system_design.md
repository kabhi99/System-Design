# DISTRIBUTED CACHE SYSTEM DESIGN
*(Building Something Like Redis)*

### Table of Contents

Part 1: Introduction & Why Distributed Cache
Part 2: Core Architecture
Part 3: Caching Mechanisms (Read/Write Patterns)
Part 4: Cache Eviction Policies
Part 5: Partitioning & Sharding
Part 6: Replication & High Availability
Part 7: Consistency Models & CAP Theorem
Part 8: Cache Invalidation Strategies
Part 9: Data Structures
Part 10: Persistence Options
Part 11: Common Challenges & Solutions
Part 12: Comparison with Alternatives
Part 13: Interview Deep-Dives
Part 14: Theoretical Foundations
14.1 CAP Theorem for Caching
14.2 Consistency Models in Caching
14.3 Eviction Policies
14.4 Consistent Hashing
14.5 Caching Patterns Deep Dive
14.6 Cache Stampede & Thundering Herd
14.7 Redis Data Structures
14.8 Redis Persistence
14.9 Redis Cluster vs Sentinel
14.10 Distributed Cache Best Practices

## PART 1: INTRODUCTION & WHY DISTRIBUTED CACHE

### 1.1 WHAT IS A DISTRIBUTED CACHE?

```
+-------------------------------------------------------------------------+
|                    DEFINITION                                          |
|                                                                         |
|  A distributed cache is:                                               |
|  * An IN-MEMORY data store                                             |
|  * Spread across MULTIPLE NODES                                        |
|  * Provides FAST access to frequently used data                        |
|  * Sits BETWEEN application and database                               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|                     Without Cache                                      |
|                                                                         |
|      App ----------------------------------> Database                  |
|            Every request hits database                                 |
|            Slow (disk I/O), expensive                                  |
|                                                                         |
|                     With Cache                                         |
|                                                                         |
|      App ----> Cache ---------------------> Database                   |
|            ^                                                           |
|         Hit!                                                           |
|         Fast (memory), cheap                                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 1.2 WHY DO WE NEED IT?

```
+-------------------------------------------------------------------------+
|                    THE SPEED PROBLEM                                   |
|                                                                         |
|  STORAGE LATENCY COMPARISON:                                           |
|                                                                         |
|  +--------------------+----------------+----------------------------+  |
|  | Storage Type       | Latency        | Operations/Second          |  |
|  +--------------------+----------------+----------------------------+  |
|  | L1 CPU Cache       | 1 ns           | 1,000,000,000              |  |
|  | L2 CPU Cache       | 4 ns           | 250,000,000                |  |
|  | RAM                | 100 ns         | 10,000,000                 |  |
|  | SSD                | 100,000 ns     | 10,000                     |  |
|  | HDD                | 10,000,000 ns  | 100                        |  |
|  | Network (local)    | 500,000 ns     | 2,000                      |  |
|  | Network (cross-DC) | 50,000,000 ns  | 20                         |  |
|  +--------------------+----------------+----------------------------+  |
|                                                                         |
|  RAM is 1000x faster than SSD!                                        |
|  This is why caching works.                                           |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    BENEFITS OF DISTRIBUTED CACHE                       |
|                                                                         |
|  1. REDUCED LATENCY                                                    |
|     * Database query: 10-100ms                                        |
|     * Cache lookup: 0.1-1ms                                           |
|     * 100x faster!                                                    |
|                                                                         |
|  2. REDUCED DATABASE LOAD                                              |
|     * Cache absorbs repeated queries                                  |
|     * Database handles only unique/write queries                      |
|     * Can reduce DB load by 90%+                                      |
|                                                                         |
|  3. SCALABILITY                                                        |
|     * Add more cache nodes to handle more load                        |
|     * Easier to scale than databases                                  |
|     * Memory is cheaper than database scaling                         |
|                                                                         |
|  4. COST REDUCTION                                                     |
|     * Fewer database replicas needed                                  |
|     * Smaller database instances sufficient                           |
|     * RAM is cheaper per operation than DB compute                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 1.3 LOCAL VS DISTRIBUTED CACHE

```
+-------------------------------------------------------------------------+
|                    LOCAL CACHE (In-Process)                            |
|                                                                         |
|  +-----------------+  +-----------------+  +-----------------+         |
|  |   App Server 1  |  |   App Server 2  |  |   App Server 3  |         |
|  |  +-----------+  |  |  +-----------+  |  |  +-----------+  |         |
|  |  |   Cache   |  |  |  |   Cache   |  |  |  |   Cache   |  |         |
|  |  |  (Local)  |  |  |  |  (Local)  |  |  |  |  (Local)  |  |         |
|  |  +-----------+  |  |  +-----------+  |  |  +-----------+  |         |
|  +-----------------+  +-----------------+  +-----------------+         |
|                                                                         |
|  PROBLEMS:                                                             |
|  * Each server has its own cache (duplication)                        |
|  * Inconsistency: Server 1 has different data than Server 2           |
|  * Memory waste: Same data cached N times                             |
|  * Cache invalidation: Must notify all servers                        |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    DISTRIBUTED CACHE (Shared)                          |
|                                                                         |
|  +-----------------+  +-----------------+  +-----------------+         |
|  |   App Server 1  |  |   App Server 2  |  |   App Server 3  |         |
|  +--------+--------+  +--------+--------+  +--------+--------+         |
|           |                    |                    |                   |
|           +--------------------+--------------------+                   |
|                                |                                        |
|                                v                                        |
|           +----------------------------------------+                   |
|           |         DISTRIBUTED CACHE CLUSTER       |                   |
|           |  +--------+  +--------+  +--------+    |                   |
|           |  | Node 1 |  | Node 2 |  | Node 3 |    |                   |
|           |  +--------+  +--------+  +--------+    |                   |
|           +----------------------------------------+                   |
|                                                                         |
|  BENEFITS:                                                             |
|  * Single source of truth                                             |
|  * No duplication                                                     |
|  * Consistent view for all app servers                                |
|  * Easier invalidation                                                |
|  * Scales independently from app                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 1.4 USE CASES

```
+-------------------------------------------------------------------------+
|                    COMMON USE CASES                                    |
|                                                                         |
|  1. SESSION STORAGE                                                    |
|     * User sessions across multiple app servers                       |
|     * Shopping cart data                                              |
|     * Authentication tokens                                           |
|                                                                         |
|  2. DATABASE QUERY CACHING                                             |
|     * Frequently accessed records                                     |
|     * Expensive query results                                         |
|     * Reference data (countries, categories)                          |
|                                                                         |
|  3. API RESPONSE CACHING                                               |
|     * Third-party API responses                                       |
|     * Computed results                                                |
|     * Aggregated data                                                 |
|                                                                         |
|  4. RATE LIMITING                                                      |
|     * Track request counts per user                                   |
|     * Sliding window counters                                         |
|     * Distributed locks                                               |
|                                                                         |
|  5. LEADERBOARDS & RANKINGS                                            |
|     * Sorted sets for real-time rankings                              |
|     * Game scores                                                     |
|     * Trending items                                                  |
|                                                                         |
|  6. MESSAGE QUEUES / PUB-SUB                                           |
|     * Real-time notifications                                         |
|     * Event broadcasting                                              |
|     * Simple task queues                                              |
|                                                                         |
|  7. DISTRIBUTED LOCKING                                                |
|     * Mutex across servers                                            |
|     * Leader election                                                 |
|     * Resource coordination                                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 2: CORE ARCHITECTURE

### 2.1 SINGLE NODE ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                    SINGLE CACHE NODE                                   |
|                                                                         |
|  +----------------------------------------------------------------+    |
|  |                       CACHE NODE                                |    |
|  |                                                                 |    |
|  |  +----------------------------------------------------------+  |    |
|  |  |                    NETWORK LAYER                          |  |    |
|  |  |  * TCP connections from clients                          |  |    |
|  |  |  * Connection pooling                                    |  |    |
|  |  |  * Protocol parsing (RESP for Redis)                     |  |    |
|  |  +----------------------------------------------------------+  |    |
|  |                           |                                    |    |
|  |                           v                                    |    |
|  |  +----------------------------------------------------------+  |    |
|  |  |                   COMMAND PROCESSOR                       |  |    |
|  |  |  * Parse commands (GET, SET, DEL, etc.)                  |  |    |
|  |  |  * Validate arguments                                    |  |    |
|  |  |  * Execute operations                                    |  |    |
|  |  +----------------------------------------------------------+  |    |
|  |                           |                                    |    |
|  |                           v                                    |    |
|  |  +----------------------------------------------------------+  |    |
|  |  |                   IN-MEMORY STORE                         |  |    |
|  |  |  * Hash table for key-value storage                      |  |    |
|  |  |  * Specialized data structures                           |  |    |
|  |  |  * TTL tracking                                          |  |    |
|  |  +----------------------------------------------------------+  |    |
|  |                           |                                    |    |
|  |                           v                                    |    |
|  |  +----------------------------------------------------------+  |    |
|  |  |                   PERSISTENCE (Optional)                  |  |    |
|  |  |  * Snapshots (RDB)                                       |  |    |
|  |  |  * Append-only log (AOF)                                 |  |    |
|  |  +----------------------------------------------------------+  |    |
|  |                                                                 |    |
|  +----------------------------------------------------------------+    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 2.2 DISTRIBUTED ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                    DISTRIBUTED CACHE CLUSTER                           |
|                                                                         |
|                         +-------------+                                |
|                         |   CLIENT    |                                |
|                         +------+------+                                |
|                                |                                        |
|                                v                                        |
|                    +-----------------------+                           |
|                    |   CLIENT LIBRARY /    |                           |
|                    |   PROXY (optional)    |                           |
|                    +-----------+-----------+                           |
|                                |                                        |
|         +----------------------+----------------------+                |
|         |                      |                      |                 |
|         v                      v                      v                 |
|  +-------------+       +-------------+       +-------------+           |
|  |  SHARD 1    |       |  SHARD 2    |       |  SHARD 3    |           |
|  |  (a-f keys) |       |  (g-m keys) |       |  (n-z keys) |           |
|  |             |       |             |       |             |           |
|  |  +-------+  |       |  +-------+  |       |  +-------+  |           |
|  |  |Primary|  |       |  |Primary|  |       |  |Primary|  |           |
|  |  +---+---+  |       |  +---+---+  |       |  +---+---+  |           |
|  |      |      |       |      |      |       |      |      |           |
|  |  +---+---+  |       |  +---+---+  |       |  +---+---+  |           |
|  |  |Replica|  |       |  |Replica|  |       |  |Replica|  |           |
|  |  +-------+  |       |  +-------+  |       |  +-------+  |           |
|  +-------------+       +-------------+       +-------------+           |
|                                                                         |
|  KEY COMPONENTS:                                                       |
|  * Shards: Data partitioned across nodes                              |
|  * Primary: Handles writes for its shard                              |
|  * Replica: Copy of primary for fault tolerance                       |
|  * Client Library: Routes requests to correct shard                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 2.3 IN-MEMORY DATA STORAGE

```
+-------------------------------------------------------------------------+
|                    HASH TABLE INTERNALS                                |
|                                                                         |
|  CORE DATA STRUCTURE: Hash Table                                       |
|  ---------------------------------                                     |
|                                                                         |
|  Key > Hash Function > Bucket Index > Value                           |
|                                                                         |
|  +---------------------------------------------------------------+     |
|  |                      HASH TABLE                                |     |
|  |                                                                |     |
|  |   Bucket 0: user:123 > {name: "John", age: 30}                |     |
|  |                v                                               |     |
|  |            session:abc > {token: "xyz"}  (collision chain)    |     |
|  |                                                                |     |
|  |   Bucket 1: product:456 > {price: 99.99}                      |     |
|  |                                                                |     |
|  |   Bucket 2: (empty)                                           |     |
|  |                                                                |     |
|  |   Bucket 3: order:789 > {items: [...]}                        |     |
|  |                                                                |     |
|  |   ...                                                          |     |
|  +---------------------------------------------------------------+     |
|                                                                         |
|  TIME COMPLEXITY:                                                      |
|  * GET: O(1) average                                                  |
|  * SET: O(1) average                                                  |
|  * DEL: O(1) average                                                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  MEMORY LAYOUT (Simplified):                                           |
|  -----------------------------                                         |
|                                                                         |
|  Each entry stores:                                                    |
|  * Key (string)                                                       |
|  * Value (bytes or structured data)                                   |
|  * TTL (expiration timestamp, if set)                                 |
|  * Metadata (type, encoding, LRU info)                                |
|                                                                         |
|  Entry {                                                               |
|    key: "user:123"                                                    |
|    value: <bytes>                                                     |
|    expire_at: 1705312345  // Unix timestamp                           |
|    last_accessed: 1705300000  // For LRU                              |
|    type: STRING | HASH | LIST | SET | ZSET                            |
|  }                                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 2.4 NETWORK PROTOCOL

```
+-------------------------------------------------------------------------+
|                    REDIS PROTOCOL (RESP)                               |
|                                                                         |
|  RESP = REdis Serialization Protocol                                  |
|  Simple, text-based, easy to parse.                                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  COMMAND FORMAT:                                                       |
|  -----------------                                                     |
|  *<number of elements>\r\n                                            |
|  $<length of element 1>\r\n                                           |
|  <element 1>\r\n                                                      |
|  ...                                                                   |
|                                                                         |
|  EXAMPLE: SET user:123 "John"                                          |
|                                                                         |
|  *3\r\n           (3 elements in command)                             |
|  $3\r\n           (length of "SET")                                   |
|  SET\r\n                                                               |
|  $8\r\n           (length of "user:123")                              |
|  user:123\r\n                                                          |
|  $4\r\n           (length of "John")                                  |
|  John\r\n                                                              |
|                                                                         |
|  RESPONSE FORMAT:                                                      |
|  -----------------                                                     |
|  +OK\r\n              (simple string)                                 |
|  -ERR message\r\n     (error)                                         |
|  :42\r\n              (integer)                                       |
|  $5\r\nHello\r\n      (bulk string)                                   |
|  *2\r\n...\r\n        (array)                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 3: CACHING MECHANISMS (READ/WRITE PATTERNS)

### 3.1 CACHE-ASIDE (LAZY LOADING)

```
+-------------------------------------------------------------------------+
|                    CACHE-ASIDE PATTERN                                 |
|                                                                         |
|  APPLICATION is responsible for managing cache.                       |
|  Cache is "aside" from the data flow — not inline.                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  READ FLOW:                                                            |
|  -----------                                                           |
|                                                                         |
|      +---------+      1. GET key      +---------+                      |
|      |   App   | ------------------> |  Cache  |                      |
|      |         | <-----------------  |         |                      |
|      |         |      2. Miss/Hit     +---------+                      |
|      |         |                                                       |
|      |         |  3. If miss, query   +---------+                      |
|      |         | ------------------> |   DB    |                      |
|      |         | <-----------------  |         |                      |
|      |         |      4. Result       +---------+                      |
|      |         |                                                       |
|      |         |      5. SET key      +---------+                      |
|      |         | ------------------> |  Cache  |                      |
|      +---------+                      +---------+                      |
|                                                                         |
|  PSEUDO-CODE:                                                          |
|  -------------                                                         |
|  function getData(key):                                               |
|      value = cache.get(key)                                           |
|      if value != null:                                                |
|          return value                   // Cache hit                  |
|                                                                         |
|      value = database.get(key)          // Cache miss                 |
|      cache.set(key, value, TTL)         // Populate cache             |
|      return value                                                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WRITE FLOW:                                                           |
|  ------------                                                          |
|  1. Write to database                                                 |
|  2. Invalidate (delete) cache key                                     |
|                                                                         |
|  function updateData(key, value):                                     |
|      database.update(key, value)                                      |
|      cache.delete(key)           // Invalidate, NOT update            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PROS:                                                                 |
|  Y Only cache what's actually accessed (no waste)                     |
|  Y Cache failures don't break reads (fallback to DB)                  |
|  Y Simple to implement                                                |
|                                                                         |
|  CONS:                                                                 |
|  X First request is slow (cache miss)                                 |
|  X Stale data possible (write-invalidate race)                        |
|  X Cache stampede on popular keys                                     |
|                                                                         |
|  BEST FOR: Most general-purpose caching scenarios                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 3.2 READ-THROUGH

```
+-------------------------------------------------------------------------+
|                    READ-THROUGH PATTERN                                |
|                                                                         |
|  CACHE is responsible for loading data from database.                 |
|  Application only talks to cache.                                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  READ FLOW:                                                            |
|  -----------                                                           |
|                                                                         |
|      +---------+      1. GET key      +-------------------------+      |
|      |   App   | ------------------> |         CACHE           |      |
|      |         |                      |                         |      |
|      |         |                      |  2. If miss, load from  |      |
|      |         |                      |     database            |      |
|      |         |                      |         |               |      |
|      |         |                      |         v               |      |
|      |         |                      |   +----------+          |      |
|      |         |                      |   |    DB    |          |      |
|      |         |                      |   +----------+          |      |
|      |         |                      |                         |      |
|      |         | <-----------------  |  3. Return value        |      |
|      +---------+      (always hits)   +-------------------------+      |
|                                                                         |
|  DIFFERENCE FROM CACHE-ASIDE:                                          |
|  ------------------------------                                        |
|  * Cache-Aside: App loads from DB on miss                             |
|  * Read-Through: CACHE loads from DB on miss                          |
|                                                                         |
|  Application code is simpler:                                         |
|  function getData(key):                                               |
|      return cache.get(key)    // That's it!                           |
|                                                                         |
|  Cache configuration includes data loader:                            |
|  cache.configure({                                                    |
|      loader: (key) => database.get(key)                              |
|  })                                                                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PROS:                                                                 |
|  Y Simpler application code                                           |
|  Y Cache encapsulates loading logic                                   |
|  Y Consistent loading behavior                                        |
|                                                                         |
|  CONS:                                                                 |
|  X Cache must know about database                                     |
|  X More complex cache infrastructure                                  |
|  X First request still slow (miss)                                    |
|                                                                         |
|  BEST FOR: When you want to hide caching logic from app              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 3.3 WRITE-THROUGH

```
+-------------------------------------------------------------------------+
|                    WRITE-THROUGH PATTERN                               |
|                                                                         |
|  Every write goes through cache to database.                          |
|  Cache is always in sync with database.                               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WRITE FLOW:                                                           |
|  ------------                                                          |
|                                                                         |
|      +---------+      1. SET key      +-------------------------+      |
|      |   App   | ------------------> |         CACHE           |      |
|      |         |                      |                         |      |
|      |         |                      |  2. Write to cache      |      |
|      |         |                      |                         |      |
|      |         |                      |  3. Write to database   |      |
|      |         |                      |  (synchronously)        |      |
|      |         |                      |         |               |      |
|      |         |                      |         v               |      |
|      |         |                      |   +----------+          |      |
|      |         |                      |   |    DB    |          |      |
|      |         |                      |   +----------+          |      |
|      |         |                      |                         |      |
|      |         | <-----------------  |  4. Confirm success     |      |
|      +---------+                      +-------------------------+      |
|                                                                         |
|  SEQUENCE:                                                             |
|  1. App writes to cache                                               |
|  2. Cache writes to database (synchronous)                            |
|  3. Only when DB confirms > Cache confirms to app                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PROS:                                                                 |
|  Y Cache ALWAYS consistent with database                              |
|  Y No stale reads (cache has latest)                                  |
|  Y Simplifies read path                                               |
|                                                                         |
|  CONS:                                                                 |
|  X Write latency increased (cache + DB)                               |
|  X If DB fails, write fails (even though cache succeeded)             |
|  X May cache data that's never read                                   |
|                                                                         |
|  BEST FOR: When consistency is critical, read-heavy workloads        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 3.4 WRITE-BEHIND (WRITE-BACK)

```
+-------------------------------------------------------------------------+
|                    WRITE-BEHIND PATTERN                                |
|                                                                         |
|  Write to cache immediately, database updated LATER (async).          |
|  Fastest write performance, but risk of data loss.                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WRITE FLOW:                                                           |
|  ------------                                                          |
|                                                                         |
|      +---------+      1. SET key      +-------------------------+      |
|      |   App   | ------------------> |         CACHE           |      |
|      |         | <-----------------  |                         |      |
|      |         |   2. OK (fast!)      |  Write to memory        |      |
|      +---------+                      |                         |      |
|                                        |  3. Queue write         |      |
|                                        |         |               |      |
|                                        |         v               |      |
|                                        |  +-------------+        |      |
|                                        |  |Write Queue |        |      |
|                                        |  +------+------+        |      |
|                                        |         |               |      |
|                                        |         | Async         |      |
|                                        |         v               |      |
|                                        |   +----------+          |      |
|                                        |   |    DB    |          |      |
|                                        |   +----------+          |      |
|                                        +-------------------------+      |
|                                                                         |
|  BATCHING:                                                             |
|  * Queue collects writes for a period (e.g., 100ms)                   |
|  * Batch written to DB together (efficient)                           |
|  * Duplicate writes to same key coalesced                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PROS:                                                                 |
|  Y Extremely fast writes (memory only)                                |
|  Y Batching reduces DB load                                           |
|  Y App not blocked by slow DB                                         |
|                                                                         |
|  CONS:                                                                 |
|  X DATA LOSS RISK if cache crashes before DB write                    |
|  X Complex failure handling                                           |
|  X DB might have stale data temporarily                               |
|                                                                         |
|  BEST FOR: High write throughput, some data loss acceptable          |
|            (metrics, logs, counters)                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 3.5 COMPARISON SUMMARY

```
+-------------------------------------------------------------------------+
|                    CACHING PATTERNS COMPARISON                         |
|                                                                         |
|  +--------------+--------------+-------------+---------------------+   |
|  | Pattern      | Write Speed  | Consistency | Data Loss Risk      |   |
|  +--------------+--------------+-------------+---------------------+   |
|  | Cache-Aside  | Medium       | Eventual    | Low                 |   |
|  | Read-Through | Medium       | Eventual    | Low                 |   |
|  | Write-Through| Slow         | Strong      | None                |   |
|  | Write-Behind | Fast         | Eventual    | HIGH                |   |
|  +--------------+--------------+-------------+---------------------+   |
|                                                                         |
|  WHEN TO USE WHAT:                                                     |
|  -----------------                                                     |
|  Cache-Aside: Default choice, most flexible                           |
|  Read-Through: When you want abstracted caching                       |
|  Write-Through: When consistency is critical                          |
|  Write-Behind: When speed matters, data loss OK                       |
|                                                                         |
|  COMMON COMBINATION:                                                   |
|  Read-Through + Write-Behind = Full cache abstraction                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 4: CACHE EVICTION POLICIES

When cache is full, we must remove something. WHICH item to remove?

### 4.1 LRU (LEAST RECENTLY USED)

```
+-------------------------------------------------------------------------+
|                    LRU EVICTION                                        |
|                                                                         |
|  PRINCIPLE:                                                            |
|  Evict the item that was ACCESSED longest ago.                        |
|  "If you haven't used it recently, you probably won't soon."          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  EXAMPLE:                                                              |
|  Cache capacity = 4                                                    |
|                                                                         |
|  Access sequence: A, B, C, D, A, E                                    |
|                                                                         |
|  Step 1: Access A > Cache: [A]                                        |
|  Step 2: Access B > Cache: [A, B]                                     |
|  Step 3: Access C > Cache: [A, B, C]                                  |
|  Step 4: Access D > Cache: [A, B, C, D] (full)                        |
|  Step 5: Access A > Cache: [B, C, D, A] (A moved to end)              |
|  Step 6: Access E > Cache: [C, D, A, E] (B evicted, least recent)    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  IMPLEMENTATION:                                                       |
|  ---------------                                                       |
|  Data structure: HashMap + Doubly Linked List                         |
|                                                                         |
|  HashMap: key > node pointer (O(1) lookup)                            |
|  LinkedList: maintains access order                                   |
|                                                                         |
|       HashMap                   Doubly Linked List                     |
|    +-----+-----+              +---+  +---+  +---+  +---+              |
|    | key | ptr |             | B |<>| C |<>| D |<>| A |              |
|    +-----+-----+              +---+  +---+  +---+  +---+              |
|    |  A  | ------------------------------------------>               |
|    |  B  | --->                                                       |
|    |  C  | --------->                                                 |
|    |  D  | --------------->                                           |
|    +-----+-----+              HEAD                  TAIL              |
|                               (oldest)              (newest)           |
|                                                                         |
|  OPERATIONS:                                                           |
|  * GET: O(1) - lookup in map, move to tail                           |
|  * SET: O(1) - add to tail, evict head if full                       |
|  * Evict: O(1) - remove head                                         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PROS:                                                                 |
|  Y Simple and intuitive                                               |
|  Y Works well for most access patterns                                |
|  Y O(1) operations                                                    |
|                                                                         |
|  CONS:                                                                 |
|  X Doesn't consider frequency (scan pollution)                        |
|  X One-time access pushes out frequent items                          |
|                                                                         |
|  BEST FOR: General-purpose caching, most common choice               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 4.2 LFU (LEAST FREQUENTLY USED)

```
+-------------------------------------------------------------------------+
|                    LFU EVICTION                                        |
|                                                                         |
|  PRINCIPLE:                                                            |
|  Evict the item that was accessed LEAST NUMBER of times.              |
|  "Infrequently used items are less important."                        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  EXAMPLE:                                                              |
|  Cache capacity = 4                                                    |
|                                                                         |
|  Access: A, A, A, B, C, C, D, E                                       |
|                                                                         |
|  After D: Cache = {A:3, B:1, C:2, D:1}                                |
|  Access E: Evict B or D (both count=1, pick older)                    |
|            Cache = {A:3, C:2, D:1, E:1}                               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  IMPLEMENTATION:                                                       |
|  ---------------                                                       |
|  Each entry tracks: key, value, frequency count                       |
|  Min-heap or bucket lists by frequency                                |
|                                                                         |
|       Frequency Buckets                                                |
|    +------------------------------------------+                       |
|    | Freq 1: [D] > [E]                        | < Evict from here     |
|    | Freq 2: [C]                              |                       |
|    | Freq 3: [A]                              |                       |
|    +------------------------------------------+                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PROS:                                                                 |
|  Y Protects frequently accessed "hot" items                           |
|  Y Better for skewed access patterns                                  |
|                                                                         |
|  CONS:                                                                 |
|  X More complex to implement                                          |
|  X Old popular items never evicted (cache pollution)                  |
|  X New items at disadvantage (low frequency)                          |
|                                                                         |
|  BEST FOR: When some items are much more popular than others          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 4.3 FIFO (FIRST IN FIRST OUT)

```
+-------------------------------------------------------------------------+
|                    FIFO EVICTION                                       |
|                                                                         |
|  PRINCIPLE:                                                            |
|  Evict the OLDEST item (first inserted).                              |
|  Simple queue behavior.                                               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  EXAMPLE:                                                              |
|  Insert: A, B, C, D, E                                                |
|  Capacity = 4                                                          |
|                                                                         |
|  After D: [A, B, C, D]                                                |
|  Insert E: Evict A > [B, C, D, E]                                     |
|                                                                         |
|  Even if A was accessed 1000 times, it gets evicted.                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PROS:                                                                 |
|  Y Extremely simple to implement                                      |
|  Y Predictable behavior                                               |
|  Y O(1) operations                                                    |
|                                                                         |
|  CONS:                                                                 |
|  X Ignores access patterns completely                                 |
|  X Poor hit rate for most workloads                                   |
|                                                                         |
|  BEST FOR: When all items equally likely to be accessed               |
|            (rare in practice)                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 4.4 TTL (TIME TO LIVE)

```
+-------------------------------------------------------------------------+
|                    TTL-BASED EXPIRATION                                |
|                                                                         |
|  PRINCIPLE:                                                            |
|  Each item has an expiration timestamp.                               |
|  Item removed when current time > expiration.                         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SETTING TTL:                                                          |
|  SET key value EX 3600    (expire in 3600 seconds)                    |
|  SET key value PX 5000    (expire in 5000 milliseconds)               |
|  EXPIRE key 300           (set TTL on existing key)                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  EXPIRATION STRATEGIES:                                                |
|  -------------------------                                             |
|                                                                         |
|  1. ACTIVE EXPIRATION (Periodic Cleanup)                              |
|     * Background thread runs every 100ms                              |
|     * Samples random keys, deletes expired ones                       |
|     * Doesn't check ALL keys (too slow)                               |
|                                                                         |
|  2. PASSIVE EXPIRATION (Lazy Deletion)                                |
|     * Check TTL on every GET                                          |
|     * If expired, delete and return null                              |
|     * Expired keys might linger if never accessed                     |
|                                                                         |
|  3. HYBRID (Redis approach)                                            |
|     * Passive: Always check on access                                 |
|     * Active: Periodic cleanup of random samples                      |
|     * Best of both worlds                                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  TTL vs EVICTION:                                                      |
|  ----------------                                                      |
|  TTL: Time-based, automatic, even if cache not full                  |
|  LRU/LFU: Space-based, only when cache is full                       |
|                                                                         |
|  Often used TOGETHER:                                                  |
|  * TTL ensures data freshness                                         |
|  * LRU handles memory pressure                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 4.5 RANDOM EVICTION

```
+-------------------------------------------------------------------------+
|                    RANDOM EVICTION                                     |
|                                                                         |
|  PRINCIPLE:                                                            |
|  Pick a random item and evict it.                                     |
|  Simple but surprisingly effective.                                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WHY RANDOM?                                                           |
|  * True LRU requires tracking every access (memory overhead)          |
|  * Random is O(1) with zero overhead                                  |
|  * For large caches, random performs reasonably well                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  REDIS APPROACH: APPROXIMATED LRU                                      |
|  ----------------------------------                                    |
|  Redis doesn't track access order for every key (too expensive).     |
|                                                                         |
|  Instead:                                                              |
|  1. Sample N random keys (default N=5)                                |
|  2. Among sampled keys, evict the oldest                              |
|  3. Not true LRU, but close enough                                    |
|                                                                         |
|  CONFIG: maxmemory-samples 5                                          |
|  Higher value = closer to true LRU, but slower                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 4.6 EVICTION POLICY COMPARISON

```
+-------------------------------------------------------------------------+
|                                                                         |
|  +---------+--------------------+-------------+----------------------+ |
|  | Policy  | Evicts             | Complexity  | Best For             | |
|  +---------+--------------------+-------------+----------------------+ |
|  | LRU     | Least recently     | O(1)        | General purpose      | |
|  |         | accessed           |             | Most workloads       | |
|  +---------+--------------------+-------------+----------------------+ |
|  | LFU     | Least frequently   | O(log n)    | Skewed access        | |
|  |         | accessed           | or O(1)     | Hot items protection | |
|  +---------+--------------------+-------------+----------------------+ |
|  | FIFO    | Oldest inserted    | O(1)        | Simple use cases     | |
|  |         |                    |             | Temporal data        | |
|  +---------+--------------------+-------------+----------------------+ |
|  | TTL     | Expired items      | O(1)        | Time-sensitive data  | |
|  |         |                    |             | Session storage      | |
|  +---------+--------------------+-------------+----------------------+ |
|  | Random  | Random item        | O(1)        | Large caches         | |
|  |         |                    |             | Low overhead needed  | |
|  +---------+--------------------+-------------+----------------------+ |
|                                                                         |
|  REDIS EVICTION POLICIES:                                              |
|  -------------------------                                             |
|  * volatile-lru: LRU among keys with TTL                              |
|  * allkeys-lru: LRU among all keys                                    |
|  * volatile-lfu: LFU among keys with TTL                              |
|  * allkeys-lfu: LFU among all keys                                    |
|  * volatile-random: Random among keys with TTL                        |
|  * allkeys-random: Random among all keys                              |
|  * volatile-ttl: Evict keys with shortest TTL                         |
|  * noeviction: Return error when memory full                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 5: PARTITIONING & SHARDING

When one cache node can't hold all data, we DISTRIBUTE across multiple nodes.

### 5.1 WHY PARTITION?

```
+-------------------------------------------------------------------------+
|                    SCALING LIMITS                                      |
|                                                                         |
|  SINGLE NODE LIMITS:                                                   |
|  * Memory: Single server max ~256GB-1TB                               |
|  * Network: Single NIC max ~10-100 Gbps                               |
|  * CPU: Single CPU for all operations                                 |
|                                                                         |
|  SOLUTION: Horizontal scaling                                         |
|  Split data across multiple nodes (shards).                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|          Before: Single Node                                           |
|                                                                         |
|          +----------------------------+                                |
|          |    1 TB of cache data      | < Memory limit                 |
|          |    100K ops/sec            | < CPU limit                    |
|          +----------------------------+                                |
|                                                                         |
|          After: 4 Shards                                               |
|                                                                         |
|     +----------+ +----------+ +----------+ +----------+               |
|     |  250 GB  | |  250 GB  | |  250 GB  | |  250 GB  |               |
|     |  25K ops | |  25K ops | |  25K ops | |  25K ops |               |
|     +----------+ +----------+ +----------+ +----------+               |
|                                                                         |
|     Total: 1 TB, 100K ops — same capacity, horizontally scaled        |
|            Can add more shards for more capacity                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 5.2 PARTITIONING STRATEGIES

### STRATEGY 1: RANGE-BASED PARTITIONING

```
+-------------------------------------------------------------------------+
|                    RANGE PARTITIONING                                  |
|                                                                         |
|  CONCEPT:                                                              |
|  Divide key space into ranges.                                        |
|  Each shard handles a range.                                          |
|                                                                         |
|  EXAMPLE:                                                              |
|  Shard 1: keys "a" to "f"                                             |
|  Shard 2: keys "g" to "m"                                             |
|  Shard 3: keys "n" to "z"                                             |
|                                                                         |
|  +--------------+  +--------------+  +--------------+                 |
|  |   Shard 1    |  |   Shard 2    |  |   Shard 3    |                 |
|  |   a - f      |  |   g - m      |  |   n - z      |                 |
|  |              |  |              |  |              |                 |
|  | apple        |  | grape        |  | orange       |                 |
|  | banana       |  | kiwi         |  | pear         |                 |
|  | cherry       |  | lemon        |  | quince       |                 |
|  +--------------+  +--------------+  +--------------+                 |
|                                                                         |
|  PROS:                                                                 |
|  Y Range queries possible (scan a-d)                                  |
|  Y Simple to understand                                               |
|                                                                         |
|  CONS:                                                                 |
|  X HOT SPOTS: If "user:*" keys are popular, Shard 3 overloaded       |
|  X Uneven distribution likely                                         |
|  X Rebalancing is complex                                             |
|                                                                         |
|  VERDICT: Rarely used for caches                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### STRATEGY 2: HASH-BASED PARTITIONING

```
+-------------------------------------------------------------------------+
|                    HASH PARTITIONING                                   |
|                                                                         |
|  CONCEPT:                                                              |
|  Hash the key, mod by number of shards.                               |
|  shard = hash(key) % num_shards                                       |
|                                                                         |
|  EXAMPLE:                                                              |
|  3 shards, key = "user:123"                                           |
|  hash("user:123") = 782345                                            |
|  shard = 782345 % 3 = 0  > Shard 0                                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PROS:                                                                 |
|  Y Even distribution (if hash is good)                                |
|  Y Simple calculation                                                 |
|  Y Predictable shard location                                         |
|                                                                         |
|  CONS:                                                                 |
|  X REBALANCING NIGHTMARE when adding/removing nodes                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  THE RESHARDING PROBLEM:                                               |
|  --------------------------                                            |
|                                                                         |
|  Before: 3 shards                                                     |
|  hash("key") % 3 = 0 > Shard 0                                        |
|  hash("key") % 3 = 1 > Shard 1                                        |
|  hash("key") % 3 = 2 > Shard 2                                        |
|                                                                         |
|  After: 4 shards (add one node)                                       |
|  hash("key") % 4 = ???                                                |
|                                                                         |
|  MOST keys will map to DIFFERENT shards!                              |
|  ~75% of keys need to MOVE.                                           |
|                                                                         |
|  This causes:                                                          |
|  * Massive cache misses during migration                              |
|  * Database overload (all misses hit DB)                              |
|  * Data movement storm                                                 |
|                                                                         |
|  SOLUTION: Consistent Hashing                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### STRATEGY 3: CONSISTENT HASHING (RECOMMENDED)

```
+-------------------------------------------------------------------------+
|                    CONSISTENT HASHING                                  |
|                                                                         |
|  CONCEPT:                                                              |
|  Hash both KEYS and NODES onto a circular ring.                       |
|  Key belongs to the first node clockwise from its position.           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  THE RING:                                                             |
|                                                                         |
|                    0 / 2^32                                            |
|                      |                                                 |
|                 -----●-----                                            |
|              /               \                                         |
|           /       Node A       \                                       |
|         ●                        ●  Node B                             |
|        /                          \                                    |
|       |     key1●                  |                                   |
|       |        v                   |                                   |
|       |   (goes to Node B)        |                                   |
|        \                          /                                    |
|         ●    ●key2               ●  Node C                             |
|           \   v   (to Node C)  /                                       |
|              \               /                                         |
|                 -----●-----                                            |
|                   Node D                                               |
|                                                                         |
|  ALGORITHM:                                                            |
|  1. Hash each node onto ring: position = hash(node_id)                |
|  2. Hash key onto ring: position = hash(key)                          |
|  3. Walk clockwise from key position to find first node               |
|  4. That node owns the key                                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  ADDING A NODE:                                                        |
|  -----------------                                                     |
|  Before: Nodes A, B, C on ring                                        |
|  Add Node D between B and C                                           |
|                                                                         |
|  Only keys between B and D need to move to D.                         |
|  Keys in other ranges: UNCHANGED!                                      |
|                                                                         |
|  With N nodes, adding 1 node moves only 1/N of keys.                  |
|  4 nodes > 25% keys move (vs 75% with simple hash mod)                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  REMOVING A NODE:                                                      |
|  -------------------                                                   |
|  Node C fails                                                         |
|  All keys that belonged to C now belong to next node (D)             |
|  Only C's keys move to D, others unchanged.                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 5.3 VIRTUAL NODES (VNODES)

```
+-------------------------------------------------------------------------+
|                    THE PROBLEM WITH BASIC CONSISTENT HASHING           |
|                                                                         |
|  With only a few physical nodes, distribution can be uneven:          |
|                                                                         |
|              -----●---------------------------●-----                   |
|           /      Node A                      Node B  \                 |
|         ●                                              ●               |
|        /                                                \              |
|       |   A covers HUGE arc                              |             |
|       |   B covers small arc                             |             |
|        \                                                /              |
|         ●                                              ●               |
|           \                                          /                 |
|              -----●---------------------------●-----                   |
|                 Node C                      Node D                     |
|                                                                         |
|  Uneven key distribution!                                              |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    SOLUTION: VIRTUAL NODES                             |
|                                                                         |
|  CONCEPT:                                                              |
|  Each physical node is represented by MULTIPLE virtual nodes.         |
|  Virtual nodes spread around the ring.                                |
|                                                                         |
|  EXAMPLE:                                                              |
|  Physical Node A has virtual nodes: A1, A2, A3, A4, A5               |
|  Physical Node B has virtual nodes: B1, B2, B3, B4, B5               |
|                                                                         |
|              -----●A1---●B2----●A3-----●B4-----                        |
|           /                                      \                     |
|         ●B1                                      ●A4                   |
|        /                                            \                  |
|       |   Now keys are evenly distributed!           |                 |
|       |   Each physical node owns ~50% of ring       |                 |
|        \                                            /                  |
|         ●A2                                      ●B3                   |
|           \                                      /                     |
|              -----●B5---●A5-----------------●-----                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  HOW MANY VNODES?                                                      |
|  ------------------                                                    |
|  * Too few: Uneven distribution                                       |
|  * Too many: More memory for ring metadata                            |
|  * Sweet spot: 100-200 vnodes per physical node                       |
|                                                                         |
|  BENEFITS:                                                             |
|  Y Even load distribution                                             |
|  Y Heterogeneous nodes (powerful nodes get more vnodes)               |
|  Y Smoother rebalancing when nodes added/removed                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 5.4 CLIENT-SIDE VS SERVER-SIDE SHARDING

```
+-------------------------------------------------------------------------+
|                    SHARDING APPROACHES                                 |
|                                                                         |
|  CLIENT-SIDE SHARDING:                                                 |
|  ---------------------                                                 |
|  Client library knows all shards.                                     |
|  Client computes which shard to talk to.                              |
|                                                                         |
|  +---------+     +---------------------+     +---------+              |
|  |  App    |---->|  Client Library     |---->| Shard 1 |              |
|  |         |     |  (knows hash ring)  |---->| Shard 2 |              |
|  |         |     |                     |---->| Shard 3 |              |
|  +---------+     +---------------------+     +---------+              |
|                                                                         |
|  Pros: No extra hop, direct connection                                |
|  Cons: Client must know cluster topology, harder to update            |
|                                                                         |
|  Examples: Redis Cluster client, Memcached                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PROXY-BASED SHARDING:                                                 |
|  ---------------------                                                 |
|  Proxy sits between client and shards.                                |
|  Proxy routes requests.                                               |
|                                                                         |
|  +---------+     +---------+     +---------+                          |
|  |  App    |---->|  Proxy  |---->| Shard 1 |                          |
|  |         |     |         |---->| Shard 2 |                          |
|  |         |     |         |---->| Shard 3 |                          |
|  +---------+     +---------+     +---------+                          |
|                                                                         |
|  Pros: Simple client, topology changes transparent                    |
|  Cons: Extra network hop, proxy is bottleneck                         |
|                                                                         |
|  Examples: Twemproxy, Redis Sentinel                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 6: REPLICATION & HIGH AVAILABILITY

### 6.1 WHY REPLICATION?

```
+-------------------------------------------------------------------------+
|                    REPLICATION GOALS                                   |
|                                                                         |
|  1. FAULT TOLERANCE                                                    |
|     * If primary fails, replica takes over                            |
|     * No data loss (if replicated in time)                            |
|     * Continuous service                                              |
|                                                                         |
|  2. READ SCALABILITY                                                   |
|     * Read from replicas (scale reads)                                |
|     * Write to primary (consistency)                                  |
|     * More replicas = more read capacity                              |
|                                                                         |
|  3. DATA LOCALITY                                                      |
|     * Replicas in different data centers                              |
|     * Users read from nearest replica                                 |
|     * Lower latency                                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 6.2 REPLICATION TOPOLOGIES

**PRIMARY-REPLICA (MASTER-SLAVE):**

```
+-------------------------------------------------------------------------+
|                    PRIMARY-REPLICA REPLICATION                         |
|                                                                         |
|                    +---------------+                                   |
|                    |   PRIMARY     |                                   |
|                    |   (Master)    |                                   |
|                    |               |                                   |
|                    |  All WRITES   |                                   |
|                    +-------+-------+                                   |
|                            |                                           |
|              +-------------+-------------+                             |
|              |             |             |                              |
|              v             v             v                              |
|        +---------+   +---------+   +---------+                         |
|        | Replica |   | Replica |   | Replica |                         |
|        |   1     |   |   2     |   |   3     |                         |
|        |         |   |         |   |         |                         |
|        | READS   |   | READS   |   | READS   |                         |
|        +---------+   +---------+   +---------+                         |
|                                                                         |
|  DATA FLOW:                                                            |
|  * Client writes to PRIMARY                                           |
|  * Primary replicates to all replicas                                 |
|  * Client reads from PRIMARY or REPLICAS                              |
|                                                                         |
|  FAILOVER:                                                             |
|  * If primary fails, one replica promoted to primary                  |
|  * Other replicas start following new primary                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 6.3 SYNCHRONOUS VS ASYNCHRONOUS REPLICATION

```
+-------------------------------------------------------------------------+
|                    SYNC VS ASYNC REPLICATION                           |
|                                                                         |
|  SYNCHRONOUS:                                                          |
|  -------------                                                         |
|  Primary waits for replica acknowledgment before confirming write.    |
|                                                                         |
|  Client --> Primary --> Replica                                       |
|    ^          |           |                                            |
|    |          |     ACK   |                                            |
|    |          |<----------|                                            |
|    |    ACK   |                                                        |
|    |<---------|                                                        |
|                                                                         |
|  Pros: No data loss if primary fails                                  |
|  Cons: Higher latency (wait for replica)                              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  ASYNCHRONOUS:                                                         |
|  --------------                                                        |
|  Primary confirms write immediately, replicates in background.        |
|                                                                         |
|  Client --> Primary ----------> Replica                               |
|    ^          |                   (later)                              |
|    |    ACK   |                                                        |
|    |<---------|                                                        |
|                                                                         |
|  Pros: Low latency                                                    |
|  Cons: Data loss if primary fails before replication                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  REDIS DEFAULT: ASYNCHRONOUS                                           |
|  * Writes are fast                                                    |
|  * Slight data loss possible on failure                               |
|  * Can configure WAIT command for sync behavior                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 6.4 FAILOVER MECHANISMS

```
+-------------------------------------------------------------------------+
|                    FAILOVER APPROACHES                                 |
|                                                                         |
|  MANUAL FAILOVER:                                                      |
|  -----------------                                                     |
|  * Operator detects failure                                           |
|  * Operator promotes replica manually                                 |
|  * Slow, human error prone                                            |
|                                                                         |
|  AUTOMATIC FAILOVER (Redis Sentinel):                                  |
|  -------------------------------------                                 |
|                                                                         |
|     +-----------------------------------------------------+           |
|     |              SENTINEL CLUSTER                        |           |
|     |   +------+     +------+     +------+               |           |
|     |   | S1   |     | S2   |     | S3   |               |           |
|     |   +------+     +------+     +------+               |           |
|     |       |            |            |                   |           |
|     |       +------------+------------+                   |           |
|     |                    | Monitor                        |           |
|     |                    v                                |           |
|     +-----------------------------------------------------+           |
|                          |                                             |
|            +-------------+-------------+                              |
|            v             v             v                              |
|      +----------+  +----------+  +----------+                         |
|      | Primary  |  | Replica  |  | Replica  |                         |
|      +----------+  +----------+  +----------+                         |
|                                                                         |
|  SENTINEL RESPONSIBILITIES:                                            |
|  1. MONITORING: Continuously check if nodes are working               |
|  2. NOTIFICATION: Alert when something goes wrong                     |
|  3. AUTOMATIC FAILOVER: Promote replica if primary fails              |
|  4. CONFIGURATION PROVIDER: Tell clients where primary is             |
|                                                                         |
|  FAILOVER PROCESS:                                                     |
|  -----------------                                                     |
|  1. Sentinels detect primary is unreachable                           |
|  2. Sentinels agree (quorum) that primary is down                     |
|  3. Sentinels elect one sentinel to do failover                       |
|  4. Elected sentinel chooses best replica                             |
|  5. Replica promoted to primary                                       |
|  6. Other replicas reconfigured to follow new primary                 |
|  7. Clients notified of new primary                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 7: CONSISTENCY MODELS & CAP THEOREM

### 7.1 CAP THEOREM

```
+-------------------------------------------------------------------------+
|                    CAP THEOREM                                         |
|                                                                         |
|  In a distributed system, you can only guarantee 2 of 3:              |
|                                                                         |
|                    CONSISTENCY                                         |
|                        ●                                               |
|                       / \                                              |
|                      /   \                                             |
|                     /     \                                            |
|                    /       \                                           |
|                   /   CA    \                                          |
|                  /           \                                         |
|                 ●-------------●                                        |
|           AVAILABILITY    PARTITION                                    |
|                           TOLERANCE                                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CONSISTENCY (C):                                                      |
|  -----------------                                                     |
|  All nodes see the SAME DATA at the same time.                        |
|  Read after write returns latest value.                               |
|                                                                         |
|  AVAILABILITY (A):                                                     |
|  ------------------                                                    |
|  Every request receives a response (not error).                       |
|  System is always operational.                                        |
|                                                                         |
|  PARTITION TOLERANCE (P):                                              |
|  --------------------------                                            |
|  System continues working despite network partitions.                 |
|  Nodes can't communicate, but system doesn't stop.                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  THE REALITY:                                                          |
|  -------------                                                         |
|  Network partitions WILL happen (P is mandatory).                     |
|  So real choice is between C and A.                                   |
|                                                                         |
|  CP (Consistency + Partition Tolerance):                              |
|  * During partition, reject writes to ensure consistency              |
|  * Example: ZooKeeper, HBase                                          |
|                                                                         |
|  AP (Availability + Partition Tolerance):                             |
|  * During partition, allow writes, accept inconsistency               |
|  * Example: Cassandra, DynamoDB, Redis (default)                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 7.2 CONSISTENCY LEVELS

```
+-------------------------------------------------------------------------+
|                    CONSISTENCY SPECTRUM                                |
|                                                                         |
|  STRONG CONSISTENCY                                                    |
|  --------------------                                                  |
|  * Every read returns the most recent write                           |
|  * Linearizable                                                       |
|  * Highest latency (must sync with all replicas)                      |
|                                                                         |
|  Write(x=1) --------------------------------------> Time              |
|                        |                                               |
|       Read(x) ---------+---> Returns 1 (guaranteed)                   |
|                        |                                               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  EVENTUAL CONSISTENCY                                                  |
|  -----------------------                                               |
|  * If no new writes, eventually all reads return last write           |
|  * Temporary inconsistency allowed                                    |
|  * Lowest latency                                                     |
|                                                                         |
|  Write(x=1) --------------------------------------> Time              |
|                        |                                               |
|       Read(x) ----+----+---> May return 0 (stale)                     |
|                   |                                                    |
|       Read(x) ----+--------------------> Returns 1 (eventually)       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  READ-YOUR-WRITES                                                      |
|  ------------------                                                    |
|  * After write, YOUR subsequent reads see the write                   |
|  * Others might see stale data temporarily                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  REDIS CONSISTENCY:                                                    |
|  -------------------                                                   |
|  * Single node: Strong consistency                                    |
|  * With replicas: Eventual consistency (async replication)            |
|  * WAIT command: Can request synchronous replication                  |
|                                                                         |
|  Example:                                                              |
|  SET key value                                                        |
|  WAIT 2 5000   // Wait for 2 replicas to ACK, timeout 5000ms         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 7.3 SPLIT-BRAIN PROBLEM

```
+-------------------------------------------------------------------------+
|                    SPLIT-BRAIN SCENARIO                                |
|                                                                         |
|  Network partition divides cluster:                                   |
|                                                                         |
|    Partition A                     Partition B                         |
|  +-----------------+             +-----------------+                  |
|  |  +----------+   |             |   +----------+  |                  |
|  |  | Primary  |   |     X       |   | Replica  |  |                  |
|  |  +----------+   |     X       |   +----------+  |                  |
|  |  +----------+   |     X       |   +----------+  |                  |
|  |  | Replica  |   |     X       |   | Sentinel |  |                  |
|  |  +----------+   |             |   +----------+  |                  |
|  +-----------------+             +-----------------+                  |
|                                                                         |
|  PROBLEM:                                                              |
|  * Partition B can't reach Primary                                    |
|  * Partition B's Sentinel promotes Replica to new Primary             |
|  * Now TWO primaries exist!                                           |
|  * Both accept writes > DATA CONFLICT                                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTIONS:                                                            |
|                                                                         |
|  1. QUORUM REQUIREMENT                                                 |
|     * Majority of sentinels must agree to failover                    |
|     * 3 sentinels: need 2 to agree                                   |
|     * Prevents minority partition from promoting                     |
|                                                                         |
|  2. MIN-REPLICAS-TO-WRITE                                              |
|     * Primary rejects writes if too few replicas connected           |
|     * min-replicas-to-write 1 (at least 1 replica must ACK)          |
|     * Reduces chance of divergent data                               |
|                                                                         |
|  3. FENCING                                                            |
|     * Old primary "fenced" when new primary elected                  |
|     * Old primary becomes replica or shuts down                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 8: CACHE INVALIDATION STRATEGIES

"There are only two hard things in Computer Science: cache invalidation
and naming things." — Phil Karlton

### 8.1 TTL-BASED INVALIDATION

```
+-------------------------------------------------------------------------+
|                    TIME-TO-LIVE                                        |
|                                                                         |
|  CONCEPT:                                                              |
|  Every cache entry has an expiration time.                            |
|  After TTL, entry is automatically invalid.                           |
|                                                                         |
|  SET user:123 "{name: John}" EX 3600   // Expires in 1 hour           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CHOOSING TTL:                                                         |
|  --------------                                                        |
|                                                                         |
|  +------------------+---------------+--------------------------------+ |
|  | Data Type        | Typical TTL   | Reasoning                      | |
|  +------------------+---------------+--------------------------------+ |
|  | User session     | 24 hours      | Security vs convenience        | |
|  | Product catalog  | 15-60 min     | Prices/stock change            | |
|  | Static content   | 24+ hours     | Rarely changes                 | |
|  | API rate limits  | 1 minute      | Rolling window                 | |
|  | Search results   | 5-15 min      | Freshness matters              | |
|  | User preferences | 1-6 hours     | Moderate update frequency      | |
|  +------------------+---------------+--------------------------------+ |
|                                                                         |
|  TRADE-OFF:                                                            |
|  * Short TTL: Fresh data, more cache misses                           |
|  * Long TTL: Stale data, better hit rate                              |
|                                                                         |
|  PROS:                                                                 |
|  Y Simple — no complex invalidation logic                             |
|  Y Automatic — no application changes needed                          |
|  Y Bounded staleness — data never older than TTL                     |
|                                                                         |
|  CONS:                                                                 |
|  X Data might be stale until TTL expires                              |
|  X Cache stampede at expiry                                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 8.2 EVENT-BASED INVALIDATION

```
+-------------------------------------------------------------------------+
|                    EVENT-DRIVEN CACHE INVALIDATION                     |
|                                                                         |
|  CONCEPT:                                                              |
|  When data changes in database, publish event.                        |
|  Cache service listens and invalidates affected keys.                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|      +---------+        +----------+        +---------+               |
|      |   App   |------->| Database |------->|  Event  |               |
|      |         | Update |          | Emit   |  Bus    |               |
|      +---------+        +----------+        +----+----+               |
|                                                   |                    |
|                                                   | Subscribe          |
|                                                   v                    |
|                                             +---------+               |
|                                             |  Cache  |               |
|                                             | (delete |               |
|                                             |  key)   |               |
|                                             +---------+               |
|                                                                         |
|  IMPLEMENTATION OPTIONS:                                               |
|  -------------------------                                             |
|  * Database triggers > Message queue                                  |
|  * Change Data Capture (Debezium)                                     |
|  * Application publishes event after write                            |
|                                                                         |
|  PROS:                                                                 |
|  Y Near real-time invalidation                                        |
|  Y Only invalidate what changed                                       |
|                                                                         |
|  CONS:                                                                 |
|  X More infrastructure (message bus)                                  |
|  X Message delivery not guaranteed instantly                          |
|  X Complexity                                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 8.3 WRITE-THROUGH INVALIDATION

```
+-------------------------------------------------------------------------+
|                    INVALIDATE ON WRITE                                 |
|                                                                         |
|  CONCEPT:                                                              |
|  Application explicitly invalidates cache after database write.       |
|                                                                         |
|  function updateUser(userId, newData):                                |
|      database.update(userId, newData)                                 |
|      cache.delete("user:" + userId)     // Invalidate!               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  DELETE VS UPDATE CACHE:                                               |
|  -------------------------                                             |
|                                                                         |
|  OPTION A: Delete cache entry                                         |
|  cache.delete("user:123")                                             |
|  * Next read will fetch from DB and repopulate                        |
|  * Safer — no race condition                                          |
|                                                                         |
|  OPTION B: Update cache entry                                         |
|  cache.set("user:123", newData)                                       |
|  * No cache miss on next read                                         |
|  * Risk: Race condition if concurrent updates                         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  RACE CONDITION WITH UPDATE:                                           |
|  -----------------------------                                         |
|                                                                         |
|  Thread A                          Thread B                            |
|  ---------                         ---------                           |
|  Read user (version 1)                                                |
|                                    Read user (version 1)              |
|  Update DB (version 2)                                                |
|                                    Update DB (version 3)              |
|  Update cache (version 2)                                             |
|                                    Update cache (version 3)           |
|                                                                         |
|  Cache has version 3. But what if Thread A's cache update was slow?  |
|  Thread A's update might overwrite Thread B's > version 2 in cache!  |
|                                                                         |
|  SOLUTION: Always DELETE, never UPDATE cache on write.               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 8.4 VERSION-BASED INVALIDATION

```
+-------------------------------------------------------------------------+
|                    VERSIONED CACHE KEYS                                |
|                                                                         |
|  CONCEPT:                                                              |
|  Include version in cache key.                                        |
|  When data changes, increment version > old key becomes orphan.      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  APPROACH 1: Version in key                                           |
|                                                                         |
|  Cache keys:                                                           |
|  user:123:v1 > {data version 1}                                       |
|  user:123:v2 > {data version 2}  (after update)                       |
|                                                                         |
|  Application knows current version from DB.                           |
|  Old versions naturally expire (TTL) or get evicted (LRU).           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  APPROACH 2: Global cache version                                      |
|                                                                         |
|  Cache key: cache_version = 42                                        |
|  All keys: product:{id}:{cache_version}                               |
|                                                                         |
|  To invalidate ALL product cache:                                     |
|  INCR cache_version > 43                                              |
|                                                                         |
|  All old keys (with :42) are now orphaned.                           |
|  Next reads use :43 > cache miss > repopulate                        |
|                                                                         |
|  USEFUL FOR: "Clear all caches" scenarios                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 9: DATA STRUCTURES

### 9.1 SUPPORTED DATA STRUCTURES (REDIS)

```
+-------------------------------------------------------------------------+
|                    REDIS DATA STRUCTURES                               |
|                                                                         |
|  1. STRING                                                             |
|  -----------                                                           |
|  Simple key-value. Value can be string, number, or serialized data.  |
|                                                                         |
|  SET name "Alice"                                                      |
|  GET name > "Alice"                                                   |
|  INCR counter > 1, 2, 3...                                            |
|  SETEX session:abc 3600 "data"  // With TTL                           |
|                                                                         |
|  USE CASES: Caching, counters, session storage                        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  2. HASH                                                               |
|  ---------                                                             |
|  Key-value pairs within a key. Like a mini-hashmap.                   |
|                                                                         |
|  HSET user:123 name "Alice" age 30 city "NYC"                         |
|  HGET user:123 name > "Alice"                                         |
|  HGETALL user:123 > {name: Alice, age: 30, city: NYC}                |
|                                                                         |
|  USE CASES: Object storage, user profiles                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  3. LIST                                                               |
|  ---------                                                             |
|  Ordered collection. Linked list internally.                          |
|                                                                         |
|  LPUSH queue:tasks "task1" "task2"                                    |
|  RPOP queue:tasks > "task1"                                           |
|  LRANGE queue:tasks 0 -1 > ["task2"]                                  |
|                                                                         |
|  USE CASES: Message queues, activity feeds, recent items             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  4. SET                                                                |
|  --------                                                              |
|  Unordered collection of unique elements.                             |
|                                                                         |
|  SADD tags:article:1 "redis" "cache" "database"                       |
|  SMEMBERS tags:article:1 > {"redis", "cache", "database"}            |
|  SINTER tags:article:1 tags:article:2 > Common tags                  |
|                                                                         |
|  USE CASES: Tags, unique visitors, set operations                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  5. SORTED SET (ZSET)                                                  |
|  -----------------------                                               |
|  Set with score for each element. Ordered by score.                  |
|                                                                         |
|  ZADD leaderboard 100 "alice" 200 "bob" 150 "charlie"                |
|  ZRANGE leaderboard 0 -1 WITHSCORES                                   |
|  > [alice:100, charlie:150, bob:200]                                  |
|  ZRANK leaderboard "bob" > 2 (third place, 0-indexed)                |
|                                                                         |
|  USE CASES: Leaderboards, priority queues, time-series               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  6. BITMAP                                                             |
|  -----------                                                           |
|  String treated as array of bits.                                     |
|                                                                         |
|  SETBIT active_users:2024-01-15 12345 1   // User 12345 was active   |
|  GETBIT active_users:2024-01-15 12345 > 1                            |
|  BITCOUNT active_users:2024-01-15 > Number of active users           |
|                                                                         |
|  USE CASES: User activity tracking, feature flags                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  7. HYPERLOGLOG                                                        |
|  -----------------                                                     |
|  Probabilistic counting of unique elements.                           |
|  Very memory efficient (~12KB for billions of elements).             |
|                                                                         |
|  PFADD visitors "user1" "user2" "user3"                               |
|  PFCOUNT visitors > 3 (approximate count)                             |
|                                                                         |
|  USE CASES: Unique visitor count, cardinality estimation              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  8. STREAMS                                                            |
|  ------------                                                          |
|  Append-only log with consumer groups.                                |
|                                                                         |
|  XADD stream:orders * product "iPhone" qty 1                          |
|  XREAD STREAMS stream:orders 0                                        |
|                                                                         |
|  USE CASES: Event sourcing, message streaming, logs                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 10: PERSISTENCE OPTIONS

### 10.1 RDB (SNAPSHOTTING)

```
+-------------------------------------------------------------------------+
|                    RDB PERSISTENCE                                     |
|                                                                         |
|  CONCEPT:                                                              |
|  Periodically save entire dataset to disk as binary snapshot.         |
|  Point-in-time recovery.                                              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  HOW IT WORKS:                                                         |
|                                                                         |
|  Time 0          Time 1          Time 2          Time 3               |
|     |               |               |               |                  |
|  [Memory]       [Memory]        [Memory]        [Memory]              |
|     |               |               |               |                  |
|     +-------------->| SAVE          |               |                  |
|                     v               |               |                  |
|                 [Disk: dump.rdb]    +-------------->| SAVE            |
|                                                      v                 |
|                                                  [Disk: dump.rdb]      |
|                                                                         |
|  CONFIG:                                                               |
|  save 900 1      // Save if 1 key changed in 900 seconds             |
|  save 300 10     // Save if 10 keys changed in 300 seconds           |
|  save 60 10000   // Save if 10000 keys changed in 60 seconds         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PROS:                                                                 |
|  Y Compact single file — easy to backup                              |
|  Y Fast restart — load binary directly                               |
|  Y Good for disaster recovery                                        |
|                                                                         |
|  CONS:                                                                 |
|  X DATA LOSS: Changes since last snapshot lost on crash              |
|  X Fork overhead for large datasets                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 10.2 AOF (APPEND-ONLY FILE)

```
+-------------------------------------------------------------------------+
|                    AOF PERSISTENCE                                     |
|                                                                         |
|  CONCEPT:                                                              |
|  Log every write operation to a file.                                 |
|  Replay log to reconstruct data on restart.                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  EXAMPLE AOF FILE:                                                     |
|                                                                         |
|  *3\r\n$3\r\nSET\r\n$4\r\nname\r\n$5\r\nAlice\r\n                    |
|  *3\r\n$3\r\nSET\r\n$3\r\nage\r\n$2\r\n30\r\n                        |
|  *2\r\n$4\r\nINCR\r\n$7\r\ncounter\r\n                                |
|                                                                         |
|  Each command appended as it happens.                                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  FSYNC OPTIONS:                                                        |
|                                                                         |
|  appendfsync always    // Fsync after every write (safest, slowest)  |
|  appendfsync everysec  // Fsync every second (good balance)          |
|  appendfsync no        // OS decides when to fsync (fastest)         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  AOF REWRITE:                                                          |
|  -------------                                                         |
|  AOF file grows forever. Rewrite compacts it.                        |
|                                                                         |
|  Before rewrite (1000 INCRs):                                         |
|  INCR counter                                                         |
|  INCR counter                                                         |
|  ... (1000 lines)                                                     |
|                                                                         |
|  After rewrite:                                                        |
|  SET counter 1000      // Single line!                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PROS:                                                                 |
|  Y Minimal data loss (up to 1 second with everysec)                  |
|  Y Human-readable format                                             |
|  Y Automatic rewrite to keep file small                              |
|                                                                         |
|  CONS:                                                                 |
|  X Larger file than RDB                                              |
|  X Slower restart (replay all commands)                              |
|  X Slightly slower writes (append overhead)                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 10.3 HYBRID (RDB + AOF)

```
+-------------------------------------------------------------------------+
|                    BEST OF BOTH WORLDS                                 |
|                                                                         |
|  Redis 4.0+ supports hybrid persistence:                              |
|  * AOF file starts with RDB snapshot                                 |
|  * Followed by AOF commands since snapshot                           |
|                                                                         |
|  aof-use-rdb-preamble yes                                             |
|                                                                         |
|  FILE STRUCTURE:                                                       |
|  -----------------                                                     |
|  [RDB snapshot of data at time T]                                     |
|  [AOF commands from T to now]                                         |
|                                                                         |
|  BENEFITS:                                                             |
|  Y Fast restart (load RDB portion quickly)                           |
|  Y Minimal data loss (AOF portion)                                   |
|  Y Smaller file than pure AOF                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 11: COMMON CHALLENGES & SOLUTIONS

### 11.1 HOT KEY PROBLEM

```
+-------------------------------------------------------------------------+
|                    HOT KEY PROBLEM                                     |
|                                                                         |
|  PROBLEM:                                                              |
|  One key gets massively more traffic than others.                    |
|  That shard becomes bottleneck.                                       |
|                                                                         |
|  Example: Celebrity tweet goes viral                                  |
|  Key "tweet:12345" gets 100K requests/second                          |
|  Single shard can't handle it.                                        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTIONS:                                                            |
|                                                                         |
|  1. LOCAL CACHING                                                      |
|     * Cache hot key in application memory (L1 cache)                 |
|     * Short TTL (seconds)                                            |
|     * Reduces load on Redis                                          |
|                                                                         |
|  2. KEY REPLICATION                                                    |
|     * Replicate hot key to multiple shards                           |
|     * tweet:12345:shard1, tweet:12345:shard2, ...                    |
|     * Client randomly picks one                                       |
|                                                                         |
|  3. READ FROM REPLICAS                                                 |
|     * Route hot key reads to replicas                                |
|     * More replicas = more read capacity                             |
|                                                                         |
|  4. RATE LIMITING                                                      |
|     * Limit requests per client                                       |
|     * Protect system from overload                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 11.2 CACHE STAMPEDE

```
+-------------------------------------------------------------------------+
|                    CACHE STAMPEDE                                      |
|                                                                         |
|  Already covered in detail in BookMyShow notes!                       |
|                                                                         |
|  QUICK SUMMARY:                                                        |
|  * Cache expires, 10K requests hit database simultaneously           |
|                                                                         |
|  SOLUTIONS:                                                            |
|  1. Jittered TTL (randomized expiry)                                 |
|  2. Locking (single request rebuilds cache)                          |
|  3. Background refresh (proactive)                                   |
|  4. Stale-while-revalidate                                           |
|  5. Cache warming on startup                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 11.3 CACHE PENETRATION

```
+-------------------------------------------------------------------------+
|                    CACHE PENETRATION                                   |
|                                                                         |
|  PROBLEM:                                                              |
|  Queries for data that DOESN'T EXIST bypass cache.                   |
|  Every request hits database > database overload.                    |
|                                                                         |
|  Example:                                                              |
|  Attacker queries user:9999999 (doesn't exist)                       |
|  Cache miss > DB query > Not found > Return null                     |
|  Next request for user:9999999 > Same thing (no caching of null!)    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTIONS:                                                            |
|                                                                         |
|  1. CACHE NULL VALUES                                                  |
|     * If DB returns null, cache the null with short TTL              |
|     * SET user:9999999 "NULL" EX 60                                  |
|     * Next request hits cache, returns null without DB query         |
|                                                                         |
|  2. BLOOM FILTER                                                       |
|     * Probabilistic data structure                                    |
|     * Can tell if key DEFINITELY DOESN'T exist                       |
|     * Check bloom filter before cache/DB query                        |
|     * If bloom says "not exists" > return immediately                |
|                                                                         |
|  3. RATE LIMITING                                                      |
|     * Limit queries for non-existent keys                            |
|     * Block suspicious patterns                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 11.4 CACHE AVALANCHE

```
+-------------------------------------------------------------------------+
|                    CACHE AVALANCHE                                     |
|                                                                         |
|  PROBLEM:                                                              |
|  Cache layer fails entirely (restart, network issue).               |
|  ALL requests hit database > database crashes.                       |
|                                                                         |
|  Cascading failure:                                                   |
|  Cache down > DB overloaded > DB down > Everything down              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTIONS:                                                            |
|                                                                         |
|  1. HIGH AVAILABILITY                                                  |
|     * Redis Cluster with replicas                                    |
|     * Automatic failover                                             |
|     * Multi-zone deployment                                          |
|                                                                         |
|  2. CIRCUIT BREAKER                                                    |
|     * If cache fails, don't send ALL requests to DB                  |
|     * Fail fast for some requests                                    |
|     * Gradually restore as cache recovers                            |
|                                                                         |
|  3. FALLBACK CACHE                                                     |
|     * Local in-memory cache as backup                                |
|     * Stale data better than no data                                 |
|                                                                         |
|  4. CACHE WARMING                                                      |
|     * Pre-populate cache before accepting traffic                    |
|     * Reduce cold-start impact                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 12: COMPARISON WITH ALTERNATIVES

```
+-------------------------------------------------------------------------+
|                    CACHE SOLUTIONS COMPARISON                          |
|                                                                         |
|  +---------------+---------------+---------------+-------------------+ |
|  | Feature       | Redis         | Memcached     | Hazelcast         | |
|  +---------------+---------------+---------------+-------------------+ |
|  | Data Types    | Many (string, | String only   | Many              | |
|  |               | hash, list..) |               |                   | |
|  +---------------+---------------+---------------+-------------------+ |
|  | Persistence   | RDB, AOF      | None          | Disk, DB          | |
|  +---------------+---------------+---------------+-------------------+ |
|  | Clustering    | Built-in      | Client-side   | Built-in          | |
|  +---------------+---------------+---------------+-------------------+ |
|  | Replication   | Async/Sync    | None          | Sync              | |
|  +---------------+---------------+---------------+-------------------+ |
|  | Transactions  | MULTI/EXEC    | CAS           | Yes               | |
|  +---------------+---------------+---------------+-------------------+ |
|  | Pub/Sub       | Yes           | No            | Yes               | |
|  +---------------+---------------+---------------+-------------------+ |
|  | Scripting     | Lua           | No            | Yes               | |
|  +---------------+---------------+---------------+-------------------+ |
|  | Use Case      | Feature-rich  | Simple cache  | Enterprise        | |
|  |               | cache         | High speed    | Java ecosystem    | |
|  +---------------+---------------+---------------+-------------------+ |
|                                                                         |
|  WHEN TO USE WHAT:                                                     |
|  -----------------                                                     |
|  REDIS: General purpose, need persistence, complex data structures   |
|  MEMCACHED: Pure caching, extreme simplicity, multi-threaded         |
|  HAZELCAST: Java-centric, need strong consistency, distributed compute|
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 13: INTERVIEW DEEP-DIVES

### 13.1 COMMON INTERVIEW QUESTIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q1: Design a distributed cache system.                                |
|  -------------------------------------                                 |
|  Key points to cover:                                                  |
|  * Hash table for O(1) lookups                                        |
|  * Consistent hashing for distribution                                |
|  * Replication for fault tolerance                                    |
|  * Eviction policies (LRU)                                            |
|  * TTL for automatic expiry                                           |
|  * CAP trade-offs (AP for caches usually)                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q2: How does Redis achieve high performance?                          |
|  ------------------------------------------                            |
|  * In-memory storage (no disk I/O for reads)                         |
|  * Single-threaded event loop (no locking overhead)                   |
|  * Efficient data structures (hash tables, skip lists)               |
|  * I/O multiplexing (epoll/kqueue)                                   |
|  * Simple binary protocol (RESP)                                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q3: Explain consistent hashing.                                       |
|  ---------------------------------                                     |
|  * Hash keys and nodes onto a ring                                   |
|  * Key belongs to first node clockwise                               |
|  * Adding/removing node affects only neighboring keys                |
|  * Virtual nodes for even distribution                               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q4: How do you handle cache stampede?                                 |
|  --------------------------------------                                |
|  * Jittered TTL (randomized expiry)                                  |
|  * Locking (only one request fetches from DB)                        |
|  * Background refresh before expiry                                  |
|  * Stale-while-revalidate                                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q5: What is cache penetration and how to prevent it?                  |
|  ----------------------------------------------------                  |
|  * Queries for non-existent data always hit DB                       |
|  * Solution: Cache null values with short TTL                        |
|  * Solution: Bloom filter to reject definitely-not-exists            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q6: When would you choose Memcached over Redis?                       |
|  -------------------------------------------------                     |
|  * Pure caching (no persistence needed)                              |
|  * Simple key-value only (no complex data types)                     |
|  * Multi-threaded (Redis is single-threaded)                         |
|  * Slightly lower memory overhead                                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q7: How does Redis handle failover?                                   |
|  -------------------------------------                                 |
|  * Redis Sentinel monitors cluster                                   |
|  * Detects when primary is down (subjective/objective down)          |
|  * Sentinels vote on failover (quorum required)                      |
|  * Best replica promoted to primary                                  |
|  * Clients notified of new primary                                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q8: How do you ensure cache consistency with database?                |
|  -----------------------------------------------------                 |
|  * Write-through: Update both atomically                             |
|  * Cache-aside: Delete cache on write, repopulate on read            |
|  * Event-driven: Listen to DB changes, invalidate cache              |
|  * TTL: Bounded staleness even if invalidation fails                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 13.2 HOMEWORK ASSIGNMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. Implement LRU Cache                                                |
|     Classic data structures problem.                                  |
|     HashMap + Doubly Linked List.                                     |
|     O(1) get, O(1) put.                                              |
|                                                                         |
|  2. Implement Consistent Hashing                                       |
|     Hash ring with virtual nodes.                                     |
|     Test key distribution with different vnode counts.               |
|                                                                         |
|  3. Design a Rate Limiter using Redis                                  |
|     Fixed window vs sliding window.                                   |
|     INCR + EXPIRE for simple implementation.                         |
|     Sorted sets for sliding window.                                  |
|                                                                         |
|  4. Design a Leaderboard using Redis                                   |
|     ZADD, ZRANK, ZRANGE operations.                                   |
|     Handle ties, pagination.                                          |
|                                                                         |
|  5. Compare RDB vs AOF                                                 |
|     Benchmark startup time with large datasets.                       |
|     Measure data loss on crash scenarios.                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 14: THEORETICAL FOUNDATIONS

### 14.1 CAP THEOREM FOR CACHING

```
+-------------------------------------------------------------------------+
|                    CAP THEOREM IN DISTRIBUTED CACHES                    |
|                                                                         |
|  CONSISTENCY (C):  All nodes see same data                             |
|  AVAILABILITY (A): System always responds                              |
|  PARTITION (P):    System works despite network failures               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  REDIS CHOICES:                                                         |
|                                                                         |
|  REDIS SENTINEL (CP):                                                   |
|  ---------------------                                                  |
|  * Strong consistency (writes go to master)                           |
|  * During failover: brief unavailability                              |
|  * Good for: Session data, rate limiting                              |
|                                                                         |
|  REDIS CLUSTER (AP-ish):                                               |
|  ------------------------                                               |
|  * Partitioned by key slots                                           |
|  * Async replication > potential data loss on failover                |
|  * Prioritizes availability and partition tolerance                   |
|  * Good for: High-scale caching                                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  MEMCACHED (AP):                                                        |
|  ---------------                                                        |
|  * No replication (client-side distribution)                          |
|  * Always available (if any node up)                                  |
|  * No consistency guarantees                                          |
|  * Good for: Pure caching (data can be regenerated)                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 14.2 CONSISTENCY MODELS IN CACHING

```
+-------------------------------------------------------------------------+
|                    CACHE-DATABASE CONSISTENCY                           |
|                                                                         |
|  STRONG CONSISTENCY:                                                    |
|  ---------------------                                                  |
|  * Cache always reflects database state                                |
|  * Write-through: Update cache + DB atomically                        |
|  * Expensive, lower throughput                                         |
|                                                                         |
|  EVENTUAL CONSISTENCY:                                                  |
|  -----------------------                                                |
|  * Cache may be stale temporarily                                      |
|  * TTL-based expiration                                               |
|  * Higher performance, simpler                                        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CACHE INVALIDATION PROBLEM:                                            |
|  "There are only two hard things in CS: cache invalidation and        |
|   naming things." - Phil Karlton                                       |
|                                                                         |
|  STRATEGIES:                                                            |
|                                                                         |
|  1. TTL (Time To Live):                                                |
|     * Set expiration time                                             |
|     * Simple but potentially stale                                    |
|     * SET key value EX 3600 (1 hour)                                  |
|                                                                         |
|  2. Write-Invalidate:                                                   |
|     * On DB write: DELETE cache key                                   |
|     * Next read populates fresh data                                  |
|     * Race condition possible (stale read)                            |
|                                                                         |
|  3. Write-Through:                                                      |
|     * On write: Update cache + DB together                            |
|     * Always consistent                                               |
|     * Higher write latency                                            |
|                                                                         |
|  4. Event-Driven:                                                       |
|     * DB publishes change events                                      |
|     * Cache subscribes and invalidates                                |
|     * Eventual consistency with low latency                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 14.3 EVICTION POLICIES

```
+-------------------------------------------------------------------------+
|                    CACHE EVICTION ALGORITHMS                            |
|                                                                         |
|  LRU (Least Recently Used):                                            |
|  ---------------------------                                            |
|  * Evict item not accessed for longest time                           |
|  * Best general-purpose policy                                         |
|  * Implementation: HashMap + Doubly Linked List                       |
|                                                                         |
|  Access pattern: A B C D E A B                                         |
|  On eviction (if full): Evict C (LRU)                                 |
|                                                                         |
|  Redis: maxmemory-policy allkeys-lru                                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  LFU (Least Frequently Used):                                          |
|  ------------------------------                                         |
|  * Evict item accessed least often                                    |
|  * Better for stable access patterns                                  |
|  * Needs frequency counter                                            |
|                                                                         |
|  Access: A A A B B C                                                   |
|  Frequencies: A=3, B=2, C=1                                           |
|  On eviction: Evict C (LFU)                                           |
|                                                                         |
|  Redis: maxmemory-policy allkeys-lfu                                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  FIFO (First In First Out):                                            |
|  ----------------------------                                           |
|  * Evict oldest item                                                  |
|  * Simple, O(1) operations                                            |
|  * Doesn't consider access patterns                                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  TTL-BASED:                                                             |
|  -----------                                                            |
|  * Evict expired items first                                          |
|  * Combined with LRU/LFU for non-expired                              |
|                                                                         |
|  Redis: maxmemory-policy volatile-lru (only keys with TTL)            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  RANDOM:                                                                |
|  --------                                                               |
|  * Random eviction                                                    |
|  * Surprisingly effective                                             |
|  * O(1), no bookkeeping                                              |
|                                                                         |
|  Redis: maxmemory-policy allkeys-random                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 14.4 CONSISTENT HASHING

```
+-------------------------------------------------------------------------+
|                    CONSISTENT HASHING EXPLAINED                         |
|                                                                         |
|  PROBLEM:                                                               |
|  ---------                                                              |
|  Simple hash: node = hash(key) % num_nodes                             |
|  Add/remove node > ALL keys remap! (cache stampede)                   |
|                                                                         |
|  SOLUTION: CONSISTENT HASHING                                           |
|  ---------------------------------                                      |
|  * Hash ring (0 to 2^32-1)                                            |
|  * Nodes placed on ring by hash(node_id)                              |
|  * Keys placed on ring by hash(key)                                   |
|  * Key belongs to next node clockwise                                 |
|                                                                         |
|        Node A                                                          |
|           ●                                                            |
|      /         \                                                       |
|     /    k1●    \    k1 > Node B (next clockwise)                     |
|    ●             ●                                                     |
|  Node D         Node B                                                 |
|     \     k2●   /    k2 > Node C (next clockwise)                     |
|      \         /                                                       |
|           ●                                                            |
|        Node C                                                          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  ADDING A NODE:                                                         |
|  ---------------                                                        |
|  * Only keys between new node and previous node move                  |
|  * ~1/N keys affected (not all!)                                      |
|                                                                         |
|  REMOVING A NODE:                                                       |
|  -----------------                                                      |
|  * Only keys on that node move to next node                           |
|  * ~1/N keys affected                                                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  VIRTUAL NODES:                                                         |
|  ---------------                                                        |
|  Problem: With few nodes, distribution uneven                          |
|  Solution: Each physical node > multiple virtual nodes on ring        |
|                                                                         |
|  Physical Node A > VNode A1, A2, A3, A4... (spread around ring)       |
|                                                                         |
|  * Better distribution                                                 |
|  * Heterogeneous nodes (powerful node = more vnodes)                  |
|  * Smoother rebalancing                                               |
|                                                                         |
|  Used in: Redis Cluster, Cassandra, DynamoDB, Memcached               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 14.5 CACHING PATTERNS DEEP DIVE

```
+-------------------------------------------------------------------------+
|                    CACHE-ASIDE (LAZY LOADING)                           |
|                                                                         |
|  READ:                                                                  |
|  1. App checks cache                                                   |
|  2. Cache miss > App queries DB                                       |
|  3. App stores result in cache                                        |
|  4. Return data                                                        |
|                                                                         |
|  +-----+  1.Get   +-------+                                           |
|  | App | -------->| Cache |                                           |
|  +--+--+  2.Miss  +-------+                                           |
|     |                                                                  |
|     | 3.Query                                                         |
|     v                                                                  |
|  +------+  4.Store +-------+                                          |
|  |  DB  | -------->| Cache |                                          |
|  +------+          +-------+                                          |
|                                                                         |
|  PROS: Only requested data cached                                      |
|  CONS: Cache miss = slow (DB + cache write)                           |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    WRITE-THROUGH                                        |
|                                                                         |
|  WRITE:                                                                 |
|  1. App writes to cache                                               |
|  2. Cache synchronously writes to DB                                  |
|  3. Return success                                                    |
|                                                                         |
|  +-----+  Write   +-------+  Write   +------+                        |
|  | App | -------->| Cache | -------->|  DB  |                        |
|  +-----+          +-------+          +------+                        |
|                                                                         |
|  PROS: Cache always consistent                                         |
|  CONS: Write latency, write-heavy = inefficient                       |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    WRITE-BEHIND (WRITE-BACK)                            |
|                                                                         |
|  WRITE:                                                                 |
|  1. App writes to cache                                               |
|  2. Return success immediately                                        |
|  3. Cache async writes to DB (batch/delayed)                         |
|                                                                         |
|  +-----+  Write   +-------+  Async   +------+                        |
|  | App | -------->| Cache | ~~~~~~~~>|  DB  |                        |
|  +-----+          +-------+  Batch   +------+                        |
|                                                                         |
|  PROS: Fast writes, batching reduces DB load                          |
|  CONS: Data loss risk if cache fails before flush                     |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    READ-THROUGH                                         |
|                                                                         |
|  READ (cache handles DB):                                               |
|  1. App reads from cache                                              |
|  2. Cache miss > Cache queries DB                                     |
|  3. Cache stores and returns                                          |
|                                                                         |
|  +-----+  Read    +-------+  Auto    +------+                        |
|  | App | -------->| Cache | -------->|  DB  |                        |
|  +-----+          +-------+  Load    +------+                        |
|                                                                         |
|  PROS: App code simpler (just talk to cache)                          |
|  CONS: Cache needs DB connection                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 14.6 CACHE STAMPEDE & THUNDERING HERD

```
+-------------------------------------------------------------------------+
|                    THE PROBLEM                                          |
|                                                                         |
|  CACHE STAMPEDE:                                                        |
|  -----------------                                                      |
|  1. Popular key expires                                                |
|  2. 1000 requests hit at same time                                    |
|  3. All see cache miss                                                |
|  4. All query database simultaneously                                  |
|  5. Database overwhelmed > crash                                       |
|                                                                         |
|       Requests   Cache Miss!   Database                                |
|       ●●●●●● ---> ❌ --------> 💥                                     |
|       ●●●●●●                   (overloaded)                            |
|       ●●●●●●                                                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTIONS:                                                             |
|                                                                         |
|  1. LOCKING (Single Fetch):                                            |
|  ----------------------------                                           |
|  * First request acquires lock                                        |
|  * Other requests wait or return stale                               |
|  * Only one DB query                                                  |
|                                                                         |
|  lock = redis.setnx("lock:" + key, "1", ex=10)                        |
|  if lock:                                                              |
|      data = db.query()                                                |
|      cache.set(key, data)                                             |
|      redis.delete("lock:" + key)                                      |
|  else:                                                                 |
|      wait or return stale                                             |
|                                                                         |
|  2. PROBABILISTIC EARLY EXPIRATION:                                    |
|  -------------------------------------                                  |
|  * Refresh before actual expiration                                   |
|  * Random jitter prevents synchronized expiry                         |
|                                                                         |
|  ttl = base_ttl * (1 + random(-0.1, 0.1))  // ±10% jitter            |
|                                                                         |
|  3. BACKGROUND REFRESH:                                                |
|  -----------------------                                                |
|  * Cache never expires (infinite TTL)                                 |
|  * Background job refreshes periodically                              |
|  * Always serve from cache                                            |
|                                                                         |
|  4. CIRCUIT BREAKER:                                                   |
|  ---------------------                                                  |
|  * Limit concurrent DB queries                                        |
|  * Excess requests wait in queue                                      |
|  * Protect database from overload                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 14.7 REDIS DATA STRUCTURES

```
+-------------------------------------------------------------------------+
|                    REDIS DATA STRUCTURES & USE CASES                    |
|                                                                         |
|  STRING:                                                                |
|  ---------                                                              |
|  SET user:123 "json_data"                                              |
|  GET user:123                                                          |
|  Use: Simple caching, counters, flags                                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  HASH:                                                                  |
|  ------                                                                 |
|  HSET user:123 name "John" age 30 email "john@example.com"            |
|  HGET user:123 name                                                    |
|  HGETALL user:123                                                      |
|  Use: Object storage, partial updates                                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  LIST:                                                                  |
|  ------                                                                 |
|  LPUSH queue:tasks "task1"                                             |
|  RPOP queue:tasks                                                      |
|  Use: Message queues, recent items, activity feeds                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SET:                                                                   |
|  -----                                                                  |
|  SADD online:users "user1" "user2"                                    |
|  SISMEMBER online:users "user1"                                       |
|  SMEMBERS online:users                                                |
|  Use: Tags, unique items, membership tests                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SORTED SET:                                                            |
|  ------------                                                           |
|  ZADD leaderboard 100 "player1" 85 "player2"                          |
|  ZRANK leaderboard "player1"                                          |
|  ZRANGE leaderboard 0 9 WITHSCORES                                    |
|  Use: Leaderboards, rate limiting (sliding window), scheduling        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  STREAM:                                                                |
|  --------                                                               |
|  XADD events * action "click" user "123"                              |
|  XREAD STREAMS events 0                                               |
|  Use: Event logs, message queues with consumer groups                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  GEOSPATIAL:                                                            |
|  ------------                                                           |
|  GEOADD drivers -73.97 40.78 "driver1"                                |
|  GEORADIUS drivers -73.97 40.78 5 km                                  |
|  Use: Location-based queries (Uber, DoorDash)                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 14.8 REDIS PERSISTENCE

```
+-------------------------------------------------------------------------+
|                    RDB vs AOF                                           |
|                                                                         |
|  RDB (Redis Database Backup):                                           |
|  -----------------------------                                          |
|  * Point-in-time snapshots                                            |
|  * Binary format (compact)                                            |
|  * Fast restarts (load entire dump)                                   |
|  * Data loss: changes since last snapshot                             |
|                                                                         |
|  Config: save 900 1  (snapshot if 1+ keys changed in 900 sec)         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  AOF (Append Only File):                                                |
|  -------------------------                                              |
|  * Log of all write operations                                        |
|  * Replay to reconstruct state                                        |
|  * More durable (fsync options)                                       |
|  * Larger files, slower restart                                       |
|                                                                         |
|  Config: appendfsync everysec (sync every second)                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  COMPARISON:                                                            |
|  +------------------+-------------------+----------------------------+ |
|  | Aspect           | RDB               | AOF                        | |
|  +------------------+-------------------+----------------------------+ |
|  | Data loss        | Since last snap   | Since last fsync (1 sec)   | |
|  +------------------+-------------------+----------------------------+ |
|  | File size        | Smaller           | Larger                     | |
|  +------------------+-------------------+----------------------------+ |
|  | Restart speed    | Fast              | Slower                     | |
|  +------------------+-------------------+----------------------------+ |
|  | Write perf       | No impact         | Slight impact              | |
|  +------------------+-------------------+----------------------------+ |
|                                                                         |
|  RECOMMENDATION: Use both (hybrid)                                     |
|  * RDB for fast restarts and backups                                  |
|  * AOF for durability                                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 14.9 REDIS CLUSTER vs SENTINEL

```
+-------------------------------------------------------------------------+
|                    REDIS SENTINEL                                       |
|                                                                         |
|  PURPOSE: High availability (failover)                                  |
|                                                                         |
|  ARCHITECTURE:                                                          |
|  +----------+                                                          |
|  |  Master  |<------------------------------------ Writes             |
|  +----+-----+                                                          |
|       | Replication                                                    |
|  +----+----+                                                          |
|  |         |                                                          |
|  v         v                                                          |
|  +--------+ +--------+                                                |
|  |Replica | |Replica |<----------------------------- Reads            |
|  +--------+ +--------+                                                |
|                                                                         |
|  +--------+ +--------+ +--------+                                     |
|  |Sentinel| |Sentinel| |Sentinel|  (monitors, votes on failover)      |
|  +--------+ +--------+ +--------+                                     |
|                                                                         |
|  * All data on single master                                          |
|  * Sentinels monitor and trigger failover                             |
|  * Good for: HA without sharding needs                               |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    REDIS CLUSTER                                        |
|                                                                         |
|  PURPOSE: Horizontal scaling (sharding)                                 |
|                                                                         |
|  ARCHITECTURE:                                                          |
|  +------------+  +------------+  +------------+                       |
|  | Master 1   |  | Master 2   |  | Master 3   |                       |
|  | Slots 0-5k |  | Slots 5k-10k| | Slots 10k-16k|                      |
|  +-----+------+  +-----+------+  +-----+------+                       |
|        |               |               |                               |
|  +-----v------+  +-----v------+  +-----v------+                       |
|  |  Replica   |  |  Replica   |  |  Replica   |                       |
|  +------------+  +------------+  +------------+                       |
|                                                                         |
|  * 16384 hash slots distributed across masters                        |
|  * Key > slot: CRC16(key) % 16384                                    |
|  * Client routes to correct node                                      |
|  * Good for: Large data, high throughput                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  COMPARISON:                                                            |
|  +----------------+------------------+-----------------------------+  |
|  | Aspect         | Sentinel         | Cluster                     |  |
|  +----------------+------------------+-----------------------------+  |
|  | Scaling        | Vertical only    | Horizontal (sharding)       |  |
|  +----------------+------------------+-----------------------------+  |
|  | Data limit     | Single node RAM  | Sum of all nodes            |  |
|  +----------------+------------------+-----------------------------+  |
|  | Multi-key ops  | All keys         | Same slot only              |  |
|  +----------------+------------------+-----------------------------+  |
|  | Complexity     | Lower            | Higher                      |  |
|  +----------------+------------------+-----------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 14.10 DISTRIBUTED CACHE BEST PRACTICES

```
+-------------------------------------------------------------------------+
|                    BEST PRACTICES SUMMARY                               |
|                                                                         |
|  1. SET APPROPRIATE TTLs:                                               |
|  -------------------------                                              |
|     * Static data: Long TTL (hours/days)                              |
|     * Dynamic data: Short TTL (minutes)                               |
|     * User sessions: Balance security vs UX                           |
|                                                                         |
|  2. USE NAMESPACED KEYS:                                                |
|  -------------------------                                              |
|     Good: user:123:profile, product:456:details                       |
|     Bad: 123, profile_123                                             |
|                                                                         |
|  3. HANDLE CACHE FAILURES GRACEFULLY:                                   |
|  --------------------------------------                                 |
|     * Fall back to database                                           |
|     * Don't crash on cache timeout                                    |
|     * Monitor cache hit rates                                         |
|                                                                         |
|  4. AVOID HOT KEYS:                                                     |
|  ---------------------                                                  |
|     * Single key with millions of reads = bottleneck                  |
|     * Solution: Replicate hot data, add random suffix                 |
|     * Example: popular_item:{random(1-10)}                           |
|                                                                         |
|  5. USE APPROPRIATE DATA STRUCTURES:                                    |
|  ------------------------------------                                   |
|     * Don't store 1MB JSON as string                                  |
|     * Use HASH for objects                                            |
|     * Use SORTED SET for leaderboards                                 |
|                                                                         |
|  6. MONITOR AND ALERT:                                                  |
|  --------------------                                                   |
|     * Cache hit ratio (target: >95%)                                  |
|     * Memory usage                                                    |
|     * Eviction rate                                                   |
|     * Connection count                                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF DOCUMENT

