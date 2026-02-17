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
