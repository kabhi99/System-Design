# REDIS
*Chapter 1: Fundamentals and Data Structures*

Redis (Remote Dictionary Server) is an open-source, in-memory data structure
store used as a database, cache, message broker, and streaming engine. It is
the most popular key-value store in the world.

## SECTION 1.1: WHAT IS REDIS?

```
+--------------------------------------------------------------------------+
|                                                                          |
|  REDIS IN ONE SENTENCE                                                   |
|                                                                          |
|  An in-memory data structure server that supports strings, hashes,       |
|  lists, sets, sorted sets, streams, bitmaps, HyperLogLog, and            |
|  geospatial indexes -- with optional persistence to disk.                |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  KEY TRAITS:                                                             |
|  * In-Memory    -- all data in RAM, sub-millisecond latency              |
|  * Single-Thread-- command execution is single-threaded (atomic)         |
|  * Rich Types   -- not just key-value, full data structure server        |
|  * Persistent   -- RDB snapshots + AOF append-only file                  |
|  * Replicated   -- master-replica for HA and read scaling                |
|  * Clustered    -- automatic sharding across nodes                       |
|  * Pub/Sub      -- built-in publish/subscribe messaging                  |
|  * Scripting    -- Lua scripts for atomic multi-step operations          |
|  * Extensible   -- Redis Modules (RedisJSON, RediSearch, etc.)           |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  PERFORMANCE:                                                            |
|  * ~100,000-200,000 ops/sec on a single instance                         |
|  * GET/SET latency: < 1 millisecond                                      |
|  * Pipeline: 500K+ ops/sec with batching                                 |
|  * Limited by network, NOT CPU                                           |
|                                                                          |
+--------------------------------------------------------------------------+
```

### WHY SINGLE-THREADED?

```
+---------------------------------------------------------------------------+
|                                                                           |
|  Redis executes commands on a SINGLE THREAD.                              |
|                                                                           |
|  WHY?                                                                     |
|  * No locks, no race conditions, no deadlocks                             |
|  * Every command is atomic by default                                     |
|  * Memory operations are nanoseconds (CPU is not the bottleneck)          |
|  * Network I/O is the real bottleneck                                     |
|                                                                           |
|  REDIS 6.0+ THREADING:                                                    |
|  * I/O threads handle network read/write in parallel                      |
|  * Command execution remains single-threaded                              |
|  * io-threads 4 (enable multi-threaded I/O)                               |
|  * Improves throughput ~2x for large payloads                             |
|                                                                           |
|  -------------------------------------------------------------------      |
|                                                                           |
|  MEMORY ARCHITECTURE:                                                     |
|                                                                           |
|  +-------+     +-------------------+     +-----------------+              |
|  | Client | --> | Network I/O       | --> | Event Loop      |             |
|  | Client | --> | (multi-threaded    | --> | (single thread) |            |
|  | Client | --> |  in Redis 6.0+)   | --> | Execute command  |            |
|  +-------+     +-------------------+     +--------+--------+              |
|                                                    |                      |
|                                             +------v------+               |
|                                             | In-Memory   |               |
|                                             | Hash Tables |               |
|                                             +------+------+               |
|                                                    |                      |
|                                             +------v------+               |
|                                             | Persistence |               |
|                                             | (RDB / AOF) |               |
|                                             +-------------+               |
|                                                                           |
+---------------------------------------------------------------------------+
```

### HOW IS REDIS SO FAST ON A SINGLE THREAD?

```
+---------------------------------------------------------------------------+
|                                                                           |
|  The intuition "single thread = slow" comes from CPU-heavy workloads.     |
|  Redis is different — its bottleneck is NEVER the CPU.                    |
|                                                                           |
|  -------------------------------------------------------------------      |
|  REASON 1: EVERYTHING IS IN RAM                                           |
|  -------------------------------------------------------------------      |
|                                                                           |
|  Disk read (HDD):     ~10,000,000 ns   (10 ms)                            |
|  SSD read:               ~100,000 ns   (0.1 ms)                           |
|  RAM read:                   ~100 ns   (0.0001 ms)                        |
|                                                                           |
|  A GET key is a hash table lookup in RAM — ~100 nanoseconds.              |
|  PostgreSQL for the same: parse SQL, check buffer cache, plan query,      |
|  possibly read from disk. Redis skips ALL of that.                        |
|                                                                           |
|  At 100ns per command, one thread can theoretically do 10M ops/sec.       |
|  The real limit (~300K ops/sec) is the network, not the CPU.              |
|                                                                           |
|  -------------------------------------------------------------------      |
|  REASON 2: ZERO MULTI-THREADING OVERHEAD                                  |
|  -------------------------------------------------------------------      |
|                                                                           |
|                          PostgreSQL/MySQL         Redis                   |
|                          ----------------         -----                   |
|  Lock acquisition        ~500ns per row lock      0 (no locks)            |
|  Context switching       ~5,000ns per switch      0 (one thread)          |
|  Cache line bouncing     frequent (shared data)   0 (no sharing)          |
|  Memory barriers         on every lock/unlock     0                       |
|  Thread coordination     mutex, semaphore, etc.   0                       |
|                                                                           |
|  A multi-threaded system doing 100K ops/sec might spend 30-40% of CPU     |
|  time on lock contention and context switches. Redis spends 0%.           |
|                                                                           |
|  -------------------------------------------------------------------      |
|  REASON 3: OPTIMIZED DATA STRUCTURES                                      |
|  -------------------------------------------------------------------      |
|                                                                           |
|  Hash (small):    ziplist — contiguous memory, CPU cache friendly         |
|  Hash (large):    hash table — O(1) lookup                                |
|  Sorted Set:      skip list — O(log n), simpler than B-tree               |
|  List (small):    ziplist — compact, sequential scan fast in cache        |
|  List (large):    quicklist — linked list of ziplists                     |
|                                                                           |
|  WHY THIS MATTERS: Modern CPUs are 100x faster accessing data in          |
|  L1/L2 cache vs RAM. A MySQL B-tree node is ~16KB spread across           |
|  memory. A Redis ziplist for a small hash is ~64 bytes sitting in         |
|  L1 cache. Cache-friendly = fast.                                         |
|                                                                           |
|  -------------------------------------------------------------------      |
|  REASON 4: NO PARSING OVERHEAD                                            |
|  -------------------------------------------------------------------      |
|                                                                           |
|  MySQL:   "SELECT value FROM table WHERE key = 'user:123'"                |
|           -> parse SQL -> build AST -> optimize plan -> execute           |
|           -> cost: ~50,000 ns just for parsing                            |
|                                                                           |
|  Redis:   "GET user:123"                                                  |
|           -> read command name -> lookup in command table -> call fn      |
|           -> cost: ~200 ns (RESP protocol is pre-structured)              |
|                                                                           |
|  -------------------------------------------------------------------      |
|  REASON 5: I/O MULTIPLEXING (see next section for deep dive)              |
|  -------------------------------------------------------------------      |
|                                                                           |
|  One thread handles 10,000+ concurrent connections using epoll/kqueue.    |
|  Never blocks waiting for a slow client. Only processes clients that      |
|  already have data ready to read.                                         |
|                                                                           |
|  -------------------------------------------------------------------      |
|  WHERE THE TIME ACTUALLY GOES (single GET key, p99)                       |
|  -------------------------------------------------------------------      |
|                                                                           |
|  Network: client -> Redis           ~50,000 ns   (50 us)                  |
|  Protocol parsing (RESP)               ~200 ns                            |
|  Command lookup                        ~100 ns                            |
|  Hash table lookup in RAM              ~100 ns                            |
|  Build response                        ~100 ns                            |
|  Network: Redis -> client           ~50,000 ns   (50 us)                  |
|  -------------------------------------------------------                  |
|  Total                             ~100,500 ns   (~100 us)                |
|                                                                           |
|  CPU work (actual Redis code):         ~500 ns   <-- 0.5% of total        |
|  Network round-trip:               ~100,000 ns   <-- 99.5% of total       |
|                                                                           |
|  Adding more threads for ~500ns of CPU work gains almost nothing.         |
|  The bottleneck is the NETWORK, not the CPU.                              |
|                                                                           |
+---------------------------------------------------------------------------+
```

### I/O MULTIPLEXING DEEP DIVE (EPOLL / KQUEUE)

```
+---------------------------------------------------------------------------+
|                                                                           |
|  THE PROBLEM: 1 thread, 10,000 clients. How?                              |
|                                                                           |
|  -------------------------------------------------------------------      |
|  APPROACH 1: BLOCKING I/O (naive, doesn't work)                           |
|  -------------------------------------------------------------------      |
|                                                                           |
|  Analogy: A waiter stands at ONE table until they order.                  |
|                                                                           |
|  Thread calls read(client_A_socket)                                       |
|    -> BLOCKS until Client A sends data                                    |
|    -> Client A is slow (bad network)... waits 30ms                        |
|    -> finally reads, processes, responds                                  |
|  Thread calls read(client_B_socket)                                       |
|    -> BLOCKS again...                                                     |
|                                                                           |
|  Meanwhile Clients C through 10,000 are starving.                         |
|  Result: 1 client served at a time. Useless at scale.                     |
|                                                                           |
|  -------------------------------------------------------------------      |
|  APPROACH 2: THREAD-PER-CLIENT (expensive, doesn't scale)                 |
|  -------------------------------------------------------------------      |
|                                                                           |
|  Analogy: Hire 10,000 waiters — one per table.                            |
|                                                                           |
|  Spawn a new thread for each client connection.                           |
|  Each thread blocks on its own socket — that's fine.                      |
|                                                                           |
|  BUT:                                                                     |
|  * 10,000 threads = ~80 GB stack memory (8 MB per thread)                 |
|  * OS spends all its time CONTEXT SWITCHING between threads               |
|    instead of doing real work                                             |
|  * At 50,000 connections, the system collapses                            |
|  * This is the C10K problem (handling 10K concurrent connections)         |
|                                                                           |
|  -------------------------------------------------------------------      |
|  APPROACH 3: I/O MULTIPLEXING — WHAT REDIS DOES                           |
|  -------------------------------------------------------------------      |
|                                                                           |
|  Analogy: One waiter stands in the CENTER of the restaurant.              |
|  Shouts "anyone ready to order?" The host (OS kernel) instantly           |
|  tells them which tables have their hands up. Waiter only visits          |
|  tables that are ALREADY READY. Never waits at any table.                 |
|                                                                           |
|  HOW IT WORKS:                                                            |
|                                                                           |
|  while (true) {                                                           |
|      // Ask OS: "which of my 10,000 sockets have data RIGHT NOW?"         |
|      ready_sockets = epoll_wait(all_10000_sockets);                       |
|                                                                           |
|      // Only loop over clients that ALREADY have data waiting             |
|      for (socket in ready_sockets) {                                      |
|          data = read(socket);        // instant — data already there      |
|          result = process(data);     // ~100ns — hash table lookup        |
|          write(socket, result);      // buffer the response               |
|      }                                                                    |
|  }                                                                        |
|                                                                           |
|  THE MAGIC: epoll_wait() is a single OS call that says "tell me           |
|  which sockets have data ready to read." The kernel maintains this        |
|  list using interrupts from the network card. When the call returns,      |
|  Redis knows EXACTLY which clients to serve — no guessing, no waiting.    |
|                                                                           |
|  -------------------------------------------------------------------      |
|  EVOLUTION OF I/O MULTIPLEXING                                            |
|  -------------------------------------------------------------------      |
|                                                                           |
|  +------------------------------------------------------------------+     |
|  | API       | Year | How it works             | Performance        |     |
|  +-----------+------+--------------------------+--------------------+     |
|  | select()  | 1983 | Scans ALL sockets every  | O(n) per call,     |     |
|  |           |      | time to find ready ones   | max 1024 sockets   |    |
|  +-----------+------+--------------------------+--------------------+     |
|  | poll()    | 1997 | Same as select, removes   | O(n) per call,     |    |
|  |           |      | 1024 limit                | no socket limit    |    |
|  +-----------+------+--------------------------+--------------------+     |
|  | epoll()   | 2002 | Kernel tracks changes,    | O(ready) per call, |    |
|  |  (Linux)  |      | returns ONLY ready ones   | handles 100K+      |    |
|  +-----------+------+--------------------------+--------------------+     |
|  | kqueue()  | 2000 | Same idea as epoll         | O(ready) per call  |   |
|  |  (macOS)  |      | Used on macOS/BSD          | handles 100K+      |   |
|  +-----------+------+--------------------------+--------------------+     |
|                                                                           |
|  THE KEY DIFFERENCE:                                                      |
|                                                                           |
|  10,000 connections, 5 are ready:                                         |
|                                                                           |
|  select/poll:  scan all 10,000 -> find 5 ready       O(10,000)            |
|  epoll:        kernel hands you the 5 ready ones      O(5)                |
|                                                                           |
|  This is why epoll replaced select for high-connection servers.           |
|                                                                           |
|  -------------------------------------------------------------------      |
|  REDIS EVENT LOOP — PUTTING IT ALL TOGETHER                               |
|  -------------------------------------------------------------------      |
|                                                                           |
|  +------------------+                                                     |
|  | 10,000 clients   |                                                     |
|  | connected via    |                                                     |
|  | TCP sockets      |                                                     |
|  +--------+---------+                                                     |
|           |                                                               |
|           v                                                               |
|  +------------------+     "which sockets     +------------------+         |
|  |   epoll_wait()   | --> have data ready? -->| OS Kernel        |        |
|  |   (single call)  | <-- returns: [7,42,891] | (tracks sockets) |        |
|  +--------+---------+                        +------------------+         |
|           |                                                               |
|           v                                                               |
|  +------------------+                                                     |
|  | Process socket 7 |  GET user:123  -> hash lookup -> "Alice"            |
|  | Process socket 42|  INCR counter  -> increment   -> 1001               |
|  | Process socket 891| SET key val   -> store       -> OK                 |
|  +------------------+                                                     |
|  (all 3 processed in ~300ns total — then back to epoll_wait)              |
|                                                                           |
|  The thread is NEVER idle:                                                |
|  * If clients have data -> process commands                               |
|  * If no clients ready -> epoll_wait blocks efficiently (OS sleeps        |
|    the thread, wakes it on next network interrupt — zero CPU usage)       |
|                                                                           |
|  -------------------------------------------------------------------      |
|  SUMMARY FOR INTERVIEWS                                                   |
|  -------------------------------------------------------------------      |
|                                                                           |
|  Q: "How does Redis handle 300K ops/sec on a single thread?"              |
|                                                                           |
|  A: Five reasons:                                                         |
|  1. All data in RAM — ~100ns per operation, CPU is never the bottleneck   |
|  2. I/O multiplexing via epoll — one thread monitors 10K+ sockets,        |
|     only processes clients with data ready, never blocks                  |
|  3. No lock overhead — single thread means no mutexes, no contention,     |
|     no context switching tax that multi-threaded DBs pay                  |
|  4. Optimized data structures — ziplist, skip list, etc. are CPU          |
|     cache friendly (64 bytes in L1 vs 16KB B-tree nodes)                  |
|  5. Simple protocol (RESP) — no SQL parsing, no query planning,           |
|     command dispatch in ~200ns vs ~50,000ns for SQL                       |
|                                                                           |
|  The actual CPU work per command is ~500ns. The remaining 99.5% of        |
|  request time is network round-trip. Adding more threads to do 500ns      |
|  of work would gain almost nothing.                                       |
|                                                                           |
+---------------------------------------------------------------------------+
```

## SECTION 1.2: CORE DATA STRUCTURES

### STRINGS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  STRING = The simplest Redis type. Binary-safe (up to 512 MB).          |
|                                                                         |
|  BASIC OPERATIONS:                                                      |
|                                                                         |
|  SET key value                   -- store a value                       |
|  GET key                         -- retrieve a value                    |
|  DEL key                         -- delete a key                        |
|  EXISTS key                      -- check if key exists (1/0)           |
|                                                                         |
|  EXPIRY:                                                                |
|  SET key value EX 300            -- expire in 300 seconds               |
|  SET key value PX 5000           -- expire in 5000 milliseconds         |
|  TTL key                         -- seconds remaining (-1 = no expiry)  |
|  EXPIRE key 60                   -- set expiry on existing key          |
|                                                                         |
|  ATOMIC OPERATIONS:                                                     |
|  SETNX key value                 -- SET if Not eXists (for locks)       |
|  SET key value NX EX 30          -- SET if not exists + 30s expiry      |
|  INCR counter                    -- atomic increment by 1               |
|  INCRBY counter 5                -- atomic increment by 5               |
|  DECR counter                    -- atomic decrement by 1               |
|  APPEND key " more"              -- append to existing string           |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  USE CASES:                                                             |
|  * Session storage (SET session:abc123 "{user data}" EX 3600)           |
|  * Rate limiting (INCR + EXPIRE)                                        |
|  * Distributed locks (SET lock NX EX 30)                                |
|  * Counters (page views, API call counts)                               |
|  * Caching API responses / DB query results                             |
|                                                                         |
|  INTERNAL ENCODING:                                                     |
|  * int       -- if value is an integer (saves memory)                   |
|  * embstr    -- strings <= 44 bytes (single allocation)                 |
|  * raw       -- strings > 44 bytes (two allocations)                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### HASHES

```
+--------------------------------------------------------------------------+
|                                                                          |
|  HASH = A map of field-value pairs (like a mini document).               |
|                                                                          |
|  HSET user:123 name "John" age 30 city "NYC"                             |
|  HGET user:123 name        > "John"                                      |
|  HGETALL user:123          > name "John" age "30" city "NYC"             |
|  HDEL user:123 city        -- delete one field                           |
|  HEXISTS user:123 name     > 1                                           |
|  HINCRBY user:123 age 1    > 31  (atomic increment)                      |
|  HLEN user:123             > 2   (number of fields)                      |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  USE CASES:                                                              |
|  * User profiles (user:123 -> {name, email, age})                        |
|  * Shopping cart (cart:user123 -> {item1: qty, item2: qty})              |
|  * Configuration storage per service                                     |
|  * Partial updates without reading entire object                         |
|                                                                          |
|  WHY HASH OVER JSON STRING?                                              |
|  * Update individual fields without GET + SET entire object              |
|  * Atomic HINCRBY on numeric fields                                      |
|  * More memory-efficient for small hashes (ziplist encoding)             |
|                                                                          |
|  INTERNAL ENCODING:                                                      |
|  * listpack  -- small hashes (<= 128 fields, each <= 64 bytes)           |
|  * hashtable -- large hashes (regular hash table)                        |
|                                                                          |
+--------------------------------------------------------------------------+
```

### LISTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LIST = An ordered collection of strings (doubly linked list).          |
|                                                                         |
|  LPUSH mylist "c" "b" "a"       -- push to left: [a, b, c]              |
|  RPUSH mylist "d" "e"           -- push to right: [a, b, c, d, e]       |
|  LPOP mylist                    > "a"   [b, c, d, e]                    |
|  RPOP mylist                    > "e"   [b, c, d]                       |
|  LRANGE mylist 0 -1             > all elements                          |
|  LLEN mylist                    > number of elements                    |
|  LINDEX mylist 0                > first element                         |
|                                                                         |
|  BLOCKING OPERATIONS:                                                   |
|  BLPOP mylist 30                -- block until element available (30s)  |
|  BRPOP mylist 30                -- block pop from right                 |
|  BLMOVE src dst LEFT RIGHT 30   -- atomic move between lists            |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  USE CASES:                                                             |
|  * Message queues (LPUSH + BRPOP = simple task queue)                   |
|  * Activity feeds / timelines (latest N items)                          |
|  * Undo history (LPUSH + LPOP)                                          |
|  * Background job queues (Sidekiq, Bull, Celery use Redis lists)        |
|                                                                         |
|  INTERNAL ENCODING:                                                     |
|  * listpack   -- small lists (<= 128 elements, each <= 64 bytes)        |
|  * quicklist  -- linked list of listpack nodes (for larger lists)       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SETS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SET = Unordered collection of unique strings.                          |
|                                                                         |
|  SADD tags:post:1 "redis" "database" "nosql"                            |
|  SMEMBERS tags:post:1         > {"redis", "database", "nosql"}          |
|  SISMEMBER tags:post:1 "redis" > 1                                      |
|  SCARD tags:post:1             > 3 (count)                              |
|  SREM tags:post:1 "nosql"     -- remove member                          |
|                                                                         |
|  SET OPERATIONS:                                                        |
|  SUNION set1 set2             -- union of two sets                      |
|  SINTER set1 set2             -- intersection                           |
|  SDIFF set1 set2              -- difference (in set1, not in set2)      |
|  SRANDMEMBER tags:post:1 2    -- 2 random members                       |
|  SPOP tags:post:1             -- remove and return random member        |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  USE CASES:                                                             |
|  * Tags / labels (all tags for a post)                                  |
|  * Unique visitors (SADD visitors:2024-01-15 "user:123")                |
|  * Social: mutual friends (SINTER friends:A friends:B)                  |
|  * Fraud: IP tracking (SADD suspicious_ips "1.2.3.4")                   |
|  * Lottery / random selection (SRANDMEMBER / SPOP)                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SORTED SETS (ZSET)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SORTED SET = Set where each member has a SCORE (float).                |
|  Members are sorted by score. Unique members, duplicate scores OK.      |
|                                                                         |
|  ZADD leaderboard 100 "alice" 85 "bob" 92 "charlie"                     |
|  ZRANGE leaderboard 0 -1 WITHSCORES                                     |
|    > bob(85), charlie(92), alice(100)  (ascending)                      |
|  ZREVRANGE leaderboard 0 2 WITHSCORES                                   |
|    > alice(100), charlie(92), bob(85)  (descending, top 3)              |
|  ZSCORE leaderboard "alice"  > 100                                      |
|  ZRANK leaderboard "alice"   > 2 (0-based rank, ascending)              |
|  ZREVRANK leaderboard "alice" > 0 (rank in descending order)            |
|  ZINCRBY leaderboard 10 "bob" > 95 (atomic score increment)             |
|  ZRANGEBYSCORE leaderboard 90 100  > members with score 90-100          |
|  ZCOUNT leaderboard 90 100    > count in score range                    |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  USE CASES:                                                             |
|  * Leaderboards / rankings (game scores, top sellers)                   |
|  * Priority queues (score = priority or timestamp)                      |
|  * Rate limiting with sliding window                                    |
|  * Delayed job scheduling (score = execution timestamp)                 |
|  * Real-time trending / hot items                                       |
|  * Autocomplete (score = frequency)                                     |
|                                                                         |
|  INTERNAL ENCODING:                                                     |
|  * listpack  -- small sets (<= 128 members, each <= 64 bytes)           |
|  * skiplist  -- large sets (O(log N) insert, delete, range query)       |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  SKIP LIST (how sorted sets work internally):                           |
|                                                                         |
|  Level 3:  [HEAD] -----------------------> [95] ---------> [NIL]        |
|  Level 2:  [HEAD] ---------> [85] -------> [95] ---------> [NIL]        |
|  Level 1:  [HEAD] -> [72] -> [85] -> [92] -> [95] -> [100] -> [NIL]     |
|                                                                         |
|  * Probabilistic data structure (like a balanced BST)                   |
|  * O(log N) for insert, delete, lookup, range queries                   |
|  * Simpler to implement than red-black trees                            |
|  * Cache-friendly linked list at bottom level                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.3: SPECIAL DATA TYPES

### BITMAPS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BITMAP = String treated as a bit array. Extremely memory-efficient.    |
|                                                                         |
|  SETBIT user:123:logins 0 1     -- day 0: logged in                     |
|  SETBIT user:123:logins 1 0     -- day 1: did not log in                |
|  SETBIT user:123:logins 2 1     -- day 2: logged in                     |
|  GETBIT user:123:logins 2       > 1                                     |
|  BITCOUNT user:123:logins       > 2 (days logged in)                    |
|                                                                         |
|  BITOP AND dest key1 key2       -- bitwise AND                          |
|  BITOP OR dest key1 key2        -- bitwise OR                           |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  MEMORY EFFICIENCY:                                                     |
|  100 million users * 1 bit each = ~12 MB                                |
|  Compare: 100M keys as strings = ~6 GB                                  |
|                                                                         |
|  USE CASES:                                                             |
|  * Daily active users (1 bit per user per day)                          |
|  * Feature flags (bit per user per feature)                             |
|  * Online/offline status for millions of users                          |
|  * A/B test group assignment                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### HYPERLOGLOG

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HYPERLOGLOG = Probabilistic count of unique elements.                  |
|  Uses ~12 KB regardless of number of elements!                          |
|  Error rate: ~0.81%                                                     |
|                                                                         |
|  PFADD visitors:2024-01-15 "user1" "user2" "user3" "user1"              |
|  PFCOUNT visitors:2024-01-15    > 3 (approximate unique count)          |
|  PFMERGE total visitors:day1 visitors:day2  -- merge counts             |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  USE CASES:                                                             |
|  * Unique visitor count per page/day                                    |
|  * Unique search queries                                                |
|  * Unique IP addresses                                                  |
|  * Any cardinality estimation at scale                                  |
|                                                                         |
|  MEMORY: 12 KB per HyperLogLog vs. storing all unique values            |
|  Trade-off: ~0.81% error, but uses 1000x less memory                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### STREAMS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  STREAM = Append-only log (like Kafka topics, built into Redis).        |
|                                                                         |
|  XADD mystream * sensor-id 1234 temperature 19.8                        |
|    > "1690000000000-0"  (auto-generated ID: timestamp-sequence)         |
|                                                                         |
|  XLEN mystream             > number of entries                          |
|  XRANGE mystream - +       > all entries (oldest to newest)             |
|  XREVRANGE mystream + -    > all entries (newest to oldest)             |
|  XREAD COUNT 10 BLOCK 5000 STREAMS mystream $                           |
|    > block for 5s, read new entries                                     |
|                                                                         |
|  CONSUMER GROUPS (like Kafka consumer groups):                          |
|  XGROUP CREATE mystream mygroup $ MKSTREAM                              |
|  XREADGROUP GROUP mygroup consumer1 COUNT 1 STREAMS mystream >          |
|  XACK mystream mygroup "1690000000000-0"                                |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  USE CASES:                                                             |
|  * Event streaming (lightweight alternative to Kafka)                   |
|  * Activity log / audit trail                                           |
|  * IoT sensor data ingestion                                            |
|  * Chat messages                                                        |
|                                                                         |
|  STREAMS vs KAFKA:                                                      |
|  * Streams: simpler, lower throughput, no partitions, in-memory         |
|  * Kafka: distributed, persistent, partitioned, much higher scale       |
|  * Use Streams for < 100K msg/sec, Kafka for higher                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### GEOSPATIAL

```
+--------------------------------------------------------------------------+
|                                                                          |
|  GEO = Store coordinates and query by distance/radius.                   |
|  Built on sorted sets (score = geohash of lat/lng).                      |
|                                                                          |
|  GEOADD restaurants -73.985 40.748 "pizza-place"                         |
|  GEOADD restaurants -73.990 40.750 "burger-joint"                        |
|  GEOADD restaurants -73.980 40.745 "sushi-bar"                           |
|                                                                          |
|  GEODIST restaurants "pizza-place" "burger-joint" km                     |
|    > "0.5432"                                                            |
|                                                                          |
|  GEOSEARCH restaurants FROMMEMBER "pizza-place" BYRADIUS 1 km ASC        |
|    > nearby restaurants sorted by distance                               |
|                                                                          |
|  GEOPOS restaurants "pizza-place"                                        |
|    > longitude, latitude                                                 |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  USE CASES:                                                              |
|  * Find nearby restaurants, drivers, stores                              |
|  * Delivery radius check                                                 |
|  * Location-based notifications                                          |
|  * Fleet tracking (combine with EXPIRE for stale removal)                |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 1.4: KEY MANAGEMENT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KEY NAMING CONVENTIONS:                                                |
|                                                                         |
|  Use colons as separators:                                              |
|  * user:123:profile                                                     |
|  * order:456:status                                                     |
|  * cache:api:/users/123                                                 |
|  * session:abc123                                                       |
|  * lock:order:456                                                       |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  KEY EXPIRY STRATEGIES:                                                 |
|                                                                         |
|  Redis uses TWO expiry mechanisms:                                      |
|                                                                         |
|  1. PASSIVE EXPIRY                                                      |
|     Key checked when accessed. If expired, deleted and return nil.      |
|     Problem: expired keys that are never accessed waste memory.         |
|                                                                         |
|  2. ACTIVE EXPIRY (background)                                          |
|     Redis samples 20 random keys with expiry 10 times/sec.              |
|     If > 25% are expired, repeat immediately.                           |
|     Gradually cleans up expired keys.                                   |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  EVICTION POLICIES (when maxmemory is reached):                         |
|                                                                         |
|  +---------------------+--------------------------------------------+   |
|  | Policy              | Behavior                                   |   |
|  +---------------------+--------------------------------------------+   |
|  | noeviction          | Return error on writes (default)           |   |
|  | allkeys-lru         | Evict least recently used (RECOMMENDED)    |   |
|  | allkeys-lfu         | Evict least frequently used                |   |
|  | allkeys-random      | Evict random keys                          |   |
|  | volatile-lru        | LRU among keys WITH expiry only            |   |
|  | volatile-lfu        | LFU among keys with expiry only            |   |
|  | volatile-random     | Random among keys with expiry only         |   |
|  | volatile-ttl        | Evict keys with shortest TTL               |   |
|  +---------------------+--------------------------------------------+   |
|                                                                         |
|  RECOMMENDATION: allkeys-lru for caches, noeviction for databases.      |
|                                                                         |
+-------------------------------------------------------------------------+
```
