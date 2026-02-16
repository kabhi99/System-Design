# DISTRIBUTED CACHE SYSTEM DESIGN
*Chapter 4: Redis Deep Dive*

Redis is the most popular choice for distributed caching. This chapter
covers Redis internals, data structures, persistence, and best practices.

## SECTION 4.1: REDIS ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REDIS INTERNALS                                                        |
|                                                                         |
|  Single-threaded event loop (mostly)                                    |
|  All operations are atomic (no locks needed for single commands)        |
|  In-memory data structure store                                         |
|                                                                         |
|  +-----------------------------------------------------------------+    |
|  |                                                                 |    |
|  |   Client 1 -+                                                   |    |
|  |             |                                                   |    |
|  |   Client 2 -+--> Event Loop (epoll/kqueue) --> Execute Command |     |
|  |             |         |                             |          |     |
|  |   Client 3 -+         |                             v          |     |
|  |                       |                      +--------------+  |     |
|  |                       |                      |  In-Memory   |  |     |
|  |                       |                      |  Data Store  |  |     |
|  |                       |                      +--------------+  |     |
|  |                       |                             |          |     |
|  |                       |                             v          |     |
|  |                       |                      +--------------+  |     |
|  |                       |                      |  Persistence |  |     |
|  |                       |                      |  (RDB/AOF)   |  |     |
|  |                       |                      +--------------+  |     |
|  |                       |                                        |     |
|  +-----------------------+----------------------------------------+     |
|                                                                         |
|  WHY SINGLE-THREADED?                                                   |
|  ---------------------                                                  |
|  * Simplicity: No locks, no race conditions                             |
|  * Memory operations are fast (nanoseconds)                             |
|  * CPU is rarely the bottleneck (network is)                            |
|  * ~100,000 ops/sec on modern hardware                                  |
|                                                                         |
|  REDIS 6.0+ MULTI-THREADING                                             |
|  ----------------------------                                           |
|  * I/O threads for network read/write                                   |
|  * Command execution still single-threaded                              |
|  * Can improve throughput by 2x for large values                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.2: REDIS DATA STRUCTURES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. STRINGS                                                             |
|  ===========                                                            |
|                                                                         |
|  Basic key-value storage. Binary-safe (can store images, JSON, etc.)    |
|                                                                         |
|  SET user:123 "John Doe"                                                |
|  GET user:123  > "John Doe"                                             |
|                                                                         |
|  SET counter 0                                                          |
|  INCR counter  > 1                                                      |
|  INCRBY counter 5  > 6                                                  |
|                                                                         |
|  SETNX key value  > Set only if not exists (for locking)                |
|  SETEX key 60 value  > Set with 60 second expiry                        |
|                                                                         |
|  USE CASES:                                                             |
|  * Session storage                                                      |
|  * Cache JSON objects                                                   |
|  * Counters (page views, likes)                                         |
|  * Distributed locks                                                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  2. LISTS                                                               |
|  =========                                                              |
|                                                                         |
|  Linked list of strings. O(1) push/pop at ends.                         |
|                                                                         |
|  LPUSH mylist "world"                                                   |
|  LPUSH mylist "hello"                                                   |
|  LRANGE mylist 0 -1  > ["hello", "world"]                               |
|                                                                         |
|  RPUSH mylist "!"  > Add to right                                       |
|  LPOP mylist       > Remove from left                                   |
|  BRPOP mylist 30   > Blocking pop (wait up to 30s)                      |
|                                                                         |
|  USE CASES:                                                             |
|  * Message queues (LPUSH + BRPOP)                                       |
|  * Activity feeds                                                       |
|  * Recent items (capped with LTRIM)                                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  3. SETS                                                                |
|  ========                                                               |
|                                                                         |
|  Unordered collection of unique strings.                                |
|                                                                         |
|  SADD myset "apple"                                                     |
|  SADD myset "banana"                                                    |
|  SADD myset "apple"  > 0 (already exists)                               |
|  SMEMBERS myset  > {"apple", "banana"}                                  |
|                                                                         |
|  SISMEMBER myset "apple"  > 1 (true)                                    |
|  SINTER set1 set2  > Intersection                                       |
|  SUNION set1 set2  > Union                                              |
|                                                                         |
|  USE CASES:                                                             |
|  * Tags                                                                 |
|  * Unique visitors                                                      |
|  * Online users                                                         |
|  * Mutual friends (SINTER)                                              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  4. SORTED SETS (ZSET)                                                  |
|  =======================                                                |
|                                                                         |
|  Set with score for each member. Sorted by score.                       |
|                                                                         |
|  ZADD leaderboard 100 "player1"                                         |
|  ZADD leaderboard 200 "player2"                                         |
|  ZADD leaderboard 150 "player3"                                         |
|                                                                         |
|  ZRANGE leaderboard 0 -1 WITHSCORES                                     |
|  > [("player1", 100), ("player3", 150), ("player2", 200)]               |
|                                                                         |
|  ZREVRANGE leaderboard 0 2  > Top 3 (descending)                        |
|  ZRANK leaderboard "player3"  > 1 (0-indexed position)                  |
|  ZINCRBY leaderboard 50 "player1"  > 150                                |
|                                                                         |
|  USE CASES:                                                             |
|  * Leaderboards                                                         |
|  * Priority queues                                                      |
|  * Time-series (score = timestamp)                                      |
|  * Rate limiting (sliding window)                                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  5. HASHES                                                              |
|  ==========                                                             |
|                                                                         |
|  Maps of field-value pairs. Like objects/dictionaries.                  |
|                                                                         |
|  HSET user:123 name "John" age 30 email "john@example.com"              |
|  HGET user:123 name  > "John"                                           |
|  HGETALL user:123  > {name: "John", age: "30", ...}                     |
|                                                                         |
|  HINCRBY user:123 age 1  > 31                                           |
|  HDEL user:123 email                                                    |
|                                                                         |
|  USE CASES:                                                             |
|  * Object storage (user profiles)                                       |
|  * Counters per field                                                   |
|  * Session data                                                         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  6. GEOSPATIAL                                                          |
|  ==============                                                         |
|                                                                         |
|  Store and query geographic coordinates.                                |
|                                                                         |
|  GEOADD drivers -122.4194 37.7749 "driver1"                             |
|  GEOADD drivers -122.4094 37.7849 "driver2"                             |
|                                                                         |
|  GEORADIUS drivers -122.4194 37.7749 5 km                               |
|  > ["driver1", "driver2"]                                               |
|                                                                         |
|  GEODIST drivers "driver1" "driver2" km  > 1.23                         |
|                                                                         |
|  USE CASES:                                                             |
|  * Find nearby (drivers, restaurants, stores)                           |
|  * Location tracking                                                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  7. STREAMS (Redis 5.0+)                                                |
|  =========================                                              |
|                                                                         |
|  Append-only log data structure.                                        |
|  Like Kafka, but simpler.                                               |
|                                                                         |
|  XADD mystream * name "John" action "login"                             |
|  > "1609459200000-0" (auto-generated ID)                                |
|                                                                         |
|  XREAD COUNT 10 STREAMS mystream 0  > Read from beginning               |
|  XREAD BLOCK 5000 STREAMS mystream $  > Block, wait for new             |
|                                                                         |
|  Consumer groups for parallel processing:                               |
|  XGROUP CREATE mystream mygroup $                                       |
|  XREADGROUP GROUP mygroup consumer1 STREAMS mystream >                  |
|                                                                         |
|  USE CASES:                                                             |
|  * Event sourcing                                                       |
|  * Activity logs                                                        |
|  * Message queues (better than lists)                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.3: REDIS PERSISTENCE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY PERSISTENCE?                                                       |
|                                                                         |
|  Redis is in-memory, but we need durability:                            |
|  * Survive restarts                                                     |
|  * Recover from crashes                                                 |
|  * Backup data                                                          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  RDB (Redis Database)                                                   |
|  =====================                                                  |
|                                                                         |
|  Point-in-time snapshots at intervals.                                  |
|                                                                         |
|  # redis.conf                                                           |
|  save 900 1      # Save if 1 key changed in 900 seconds                 |
|  save 300 10     # Save if 10 keys changed in 300 seconds               |
|  save 60 10000   # Save if 10000 keys changed in 60 seconds             |
|                                                                         |
|  HOW IT WORKS:                                                          |
|  1. Redis forks child process                                           |
|  2. Child writes entire dataset to disk                                 |
|  3. Parent continues serving requests (copy-on-write)                   |
|  4. Child replaces old RDB file with new one                            |
|                                                                         |
|  PROS:                                                                  |
|  Y Compact single file                                                  |
|  Y Perfect for backups                                                  |
|  Y Fast restart (just load file)                                        |
|  Y Minimal impact on performance                                        |
|                                                                         |
|  CONS:                                                                  |
|  X Data loss between snapshots                                          |
|  X Fork can be slow with large datasets                                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  AOF (Append Only File)                                                 |
|  =======================                                                |
|                                                                         |
|  Logs every write operation.                                            |
|                                                                         |
|  # redis.conf                                                           |
|  appendonly yes                                                         |
|  appendfsync everysec   # Sync to disk every second                     |
|                                                                         |
|  AOF FILE EXAMPLE:                                                      |
|  *3                                                                     |
|  $3                                                                     |
|  SET                                                                    |
|  $5                                                                     |
|  mykey                                                                  |
|  $7                                                                     |
|  myvalue                                                                |
|                                                                         |
|  SYNC OPTIONS:                                                          |
|  * always: Sync every write (safest, slowest)                           |
|  * everysec: Sync every second (good balance)                           |
|  * no: Let OS decide (fastest, least safe)                              |
|                                                                         |
|  AOF REWRITE:                                                           |
|  * AOF grows large over time                                            |
|  * Rewrite compacts (SET key 1, SET key 2 > SET key 2)                  |
|  * Automatic or manual (BGREWRITEAOF)                                   |
|                                                                         |
|  PROS:                                                                  |
|  Y Minimal data loss (1 second with everysec)                           |
|  Y Human-readable format                                                |
|  Y Can edit/repair manually                                             |
|                                                                         |
|  CONS:                                                                  |
|  X Larger files than RDB                                                |
|  X Slower restart (replay all commands)                                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  RDB + AOF (Recommended)                                                |
|  =========================                                              |
|                                                                         |
|  Use both for best of both worlds:                                      |
|  * RDB for backups and fast restarts                                    |
|  * AOF for durability                                                   |
|                                                                         |
|  On restart:                                                            |
|  * If AOF enabled, load AOF (more complete)                             |
|  * Otherwise, load RDB                                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.4: REDIS TRANSACTIONS AND SCRIPTING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MULTI/EXEC (Transactions)                                              |
|  ==========================                                             |
|                                                                         |
|  Execute multiple commands atomically.                                  |
|                                                                         |
|  MULTI                                                                  |
|  SET key1 "value1"                                                      |
|  SET key2 "value2"                                                      |
|  INCR counter                                                           |
|  EXEC                                                                   |
|                                                                         |
|  All commands queued, executed together.                                |
|  No other client can interrupt.                                         |
|                                                                         |
|  WATCH (Optimistic Locking)                                             |
|  ---------------------------                                            |
|                                                                         |
|  WATCH mykey                                                            |
|  val = GET mykey                                                        |
|  val = val + 1                                                          |
|  MULTI                                                                  |
|  SET mykey val                                                          |
|  EXEC  > Returns nil if mykey changed since WATCH                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  LUA SCRIPTING                                                          |
|  ==============                                                         |
|                                                                         |
|  Execute Lua scripts atomically on server.                              |
|  More powerful than MULTI/EXEC.                                         |
|                                                                         |
|  EVAL "return redis.call('GET', KEYS[1])" 1 mykey                       |
|                                                                         |
|  EXAMPLE: Rate Limiting Script                                          |
|  ------------------------------                                         |
|                                                                         |
|  local current = redis.call('INCR', KEYS[1])                            |
|  if current == 1 then                                                   |
|      redis.call('EXPIRE', KEYS[1], ARGV[1])                             |
|  end                                                                    |
|  if current > tonumber(ARGV[2]) then                                    |
|      return 0  -- Rate limited                                          |
|  end                                                                    |
|  return 1  -- Allowed                                                   |
|                                                                         |
|  EVAL script 1 rate:user:123 60 100                                     |
|  > Returns 1 if under 100 requests/minute, else 0                       |
|                                                                         |
|  EXAMPLE: Safe Lock Release                                             |
|  ---------------------------                                            |
|                                                                         |
|  -- Only delete if value matches (we own the lock)                      |
|  if redis.call('GET', KEYS[1]) == ARGV[1] then                          |
|      return redis.call('DEL', KEYS[1])                                  |
|  else                                                                   |
|      return 0                                                           |
|  end                                                                    |
|                                                                         |
|  WHY LUA?                                                               |
|  * Atomic: entire script runs without interruption                      |
|  * Fast: no round trips between client and server                       |
|  * Complex logic: impossible with basic commands                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.5: REDIS BEST PRACTICES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KEY NAMING CONVENTIONS                                                 |
|  =======================                                                |
|                                                                         |
|  Use colons as separators:                                              |
|  Y user:123:profile                                                     |
|  Y product:456:inventory                                                |
|  Y session:abc123                                                       |
|                                                                         |
|  Include type/namespace:                                                |
|  Y cache:user:123                                                       |
|  Y lock:order:789                                                       |
|  Y rate:api:key:xyz                                                     |
|                                                                         |
|  Keep keys short (memory matters):                                      |
|  X this_is_a_very_long_key_name_that_wastes_memory                      |
|  Y u:123:p                                                              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  MEMORY OPTIMIZATION                                                    |
|  ====================                                                   |
|                                                                         |
|  1. Use appropriate data structures                                     |
|     * Small objects: Hash (more memory efficient)                       |
|     * Large objects: String (simpler)                                   |
|                                                                         |
|  2. Set TTL on everything                                               |
|     SET key value EX 3600  -- Always expire!                            |
|                                                                         |
|  3. Use OBJECT ENCODING to check                                        |
|     OBJECT ENCODING mykey  > "ziplist" (efficient)                      |
|                                                                         |
|  4. Monitor memory                                                      |
|     INFO memory                                                         |
|     MEMORY USAGE key                                                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  AVOID THESE PITFALLS                                                   |
|  =====================                                                  |
|                                                                         |
|  1. KEYS * in production                                                |
|     * Scans entire keyspace, blocks server                              |
|     * Use SCAN for iteration instead                                    |
|                                                                         |
|  2. Large values (>1MB)                                                 |
|     * Blocks server while processing                                    |
|     * Split into chunks or use different storage                        |
|                                                                         |
|  3. Hot keys                                                            |
|     * Single key with millions of requests                              |
|     * Use local caching or key replication                              |
|                                                                         |
|  4. No TTL                                                              |
|     * Memory fills up                                                   |
|     * Always set expiration                                             |
|                                                                         |
|  5. Forgetting about persistence                                        |
|     * Data lost on restart without RDB/AOF                              |
|     * Configure based on durability needs                               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  MONITORING COMMANDS                                                    |
|  ====================                                                   |
|                                                                         |
|  INFO                     # Server statistics                           |
|  INFO memory              # Memory usage                                |
|  INFO replication         # Replication status                          |
|  INFO clients             # Connected clients                           |
|                                                                         |
|  SLOWLOG GET 10           # Last 10 slow commands                       |
|  CLIENT LIST              # Connected clients                           |
|  MONITOR                  # Real-time command stream (debug only!)      |
|                                                                         |
|  DBSIZE                   # Number of keys                              |
|  DEBUG OBJECT key         # Internal representation                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REDIS DEEP DIVE - KEY TAKEAWAYS                                        |
|                                                                         |
|  ARCHITECTURE                                                           |
|  ------------                                                           |
|  * Single-threaded event loop                                           |
|  * Atomic operations (no locks)                                         |
|  * ~100K ops/sec per instance                                           |
|                                                                         |
|  DATA STRUCTURES                                                        |
|  ---------------                                                        |
|  * Strings: Basic KV, counters, locks                                   |
|  * Lists: Queues, feeds                                                 |
|  * Sets: Unique collections, tags                                       |
|  * Sorted Sets: Leaderboards, priority queues                           |
|  * Hashes: Object storage                                               |
|  * Geo: Location queries                                                |
|  * Streams: Event logs                                                  |
|                                                                         |
|  PERSISTENCE                                                            |
|  -----------                                                            |
|  * RDB: Snapshots, fast restart, some data loss                         |
|  * AOF: Log all writes, minimal loss, slower restart                    |
|  * Use both for production                                              |
|                                                                         |
|  TRANSACTIONS                                                           |
|  ------------                                                           |
|  * MULTI/EXEC for basic atomicity                                       |
|  * Lua scripts for complex operations                                   |
|                                                                         |
|  INTERVIEW TIP                                                          |
|  -------------                                                          |
|  Know when to use each data structure.                                  |
|  Explain RDB vs AOF trade-offs.                                         |
|  Be able to write a Lua script (rate limiting, locks).                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 4

