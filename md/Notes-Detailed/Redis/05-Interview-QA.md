# REDIS
*Chapter 5: Interview Questions and Answers*

25 commonly asked Redis interview questions, from fundamentals
to production operations and system design scenarios.

## SECTION 5.1: FUNDAMENTALS (Q1-Q8)

### Q1: What is Redis and why is it so fast?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Redis is an in-memory data structure server.                           |
|                                                                         |
|  WHY IT'S FAST:                                                         |
|  1. IN-MEMORY: All data in RAM (nanosecond access vs ms for disk)       |
|  2. SINGLE-THREADED: No locks, no context switching, no overhead        |
|  3. EFFICIENT DATA STRUCTURES: Purpose-built (skip lists, hash tables)  |
|  4. NON-BLOCKING I/O: epoll/kqueue event loop handles thousands of      |
|     concurrent connections without threads                              |
|  5. ZERO-COPY: Kernel-level optimization for sending data               |
|  6. SIMPLE PROTOCOL: RESP protocol is lightweight to parse              |
|                                                                         |
|  Result: ~200K ops/sec on a single core, < 1ms latency.                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q2: What data structures does Redis support?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CORE:                                                                  |
|  * String    -- binary-safe, up to 512 MB, counters, locks              |
|  * Hash      -- field-value map (user profiles, objects)                |
|  * List      -- ordered collection (queues, feeds)                      |
|  * Set       -- unique members (tags, social graphs)                    |
|  * Sorted Set-- scored members (leaderboards, priority queues)          |
|                                                                         |
|  SPECIAL:                                                               |
|  * Stream    -- append-only log (event streaming)                       |
|  * Bitmap    -- bit-level ops (DAU tracking, feature flags)             |
|  * HyperLogLog -- cardinality estimation (unique counts, 12KB)          |
|  * Geospatial -- lat/lng storage + radius queries                       |
|                                                                         |
|  MODULES:                                                               |
|  * RedisJSON, RediSearch, RedisTimeSeries, RedisBloom, RedisGraph       |
|                                                                         |
|  INTERVIEW TIP: "Redis is NOT just key-value. It's a data structure     |
|  server. Choosing the right structure is the key to efficient design."  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q3: Explain Redis persistence: RDB vs AOF.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RDB (Snapshots):                                                       |
|  * Full point-in-time snapshot saved to disk periodically               |
|  * Compact binary file, fast to load on restart                         |
|  * Data loss: everything since last snapshot (minutes)                  |
|  * Uses fork() + copy-on-write (background, non-blocking)               |
|                                                                         |
|  AOF (Append-Only File):                                                |
|  * Every write command appended to a log file                           |
|  * fsync every second (default) -> lose <= 1 second of data             |
|  * File grows, periodically rewritten (compacted)                       |
|  * Slower restart (replays all commands)                                |
|                                                                         |
|  RECOMMENDATION:                                                        |
|  * Cache: No persistence (or RDB for warm restarts)                     |
|  * Database: AOF (everysec) + periodic RDB for backups                  |
|  * Maximum safety: Both enabled (Redis uses AOF for recovery)           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q4: What is Redis Cluster and how does sharding work?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Redis Cluster splits data across multiple masters using hash slots.    |
|                                                                         |
|  * 16384 hash slots total                                               |
|  * Key -> CRC16(key) % 16384 -> slot number -> node                     |
|  * Each master owns a range of slots                                    |
|  * Each master has replica(s) for failover                              |
|  * Minimum: 3 masters + 3 replicas = 6 nodes                            |
|                                                                         |
|  HASH TAGS for multi-key operations:                                    |
|  {user:123}.profile and {user:123}.cart -> same slot                    |
|  (only the part in {} is hashed)                                        |
|                                                                         |
|  LIMITATION: Multi-key commands ONLY work on same slot.                 |
|  MGET key1 key2 fails if key1 and key2 are on different slots.          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q5: Sentinel vs Cluster -- when to use which?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SENTINEL:                                                              |
|  * Single master + replicas + sentinel monitors                         |
|  * All data on one server (limited by single server RAM)                |
|  * Automatic failover (promote replica if master dies)                  |
|  * Simple, all keys accessible together                                 |
|  * Use when: data fits in one server (<= 100 GB)                        |
|                                                                         |
|  CLUSTER:                                                               |
|  * Multiple masters, each holds a shard of data                         |
|  * Scales beyond single server RAM                                      |
|  * Scales writes (multiple write endpoints)                             |
|  * Multi-key ops restricted to same slot                                |
|  * Use when: data too big for one server, need write scaling            |
|                                                                         |
|  INTERVIEW TIP: "Most Redis deployments use Sentinel because            |
|  data usually fits in memory of a single large instance.                |
|  Cluster adds complexity -- only use when truly needed."                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q6: How does Redis handle eviction when memory is full?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  When maxmemory is reached, Redis applies the eviction policy:          |
|                                                                         |
|  noeviction    -- reject new writes (return error). Default.            |
|  allkeys-lru   -- evict least recently used key. BEST FOR CACHES.       |
|  allkeys-lfu   -- evict least frequently used key (Redis 4.0+).         |
|  volatile-lru  -- LRU only among keys with TTL set.                     |
|  volatile-lfu  -- LFU only among keys with TTL set.                     |
|  volatile-ttl  -- evict keys closest to expiry.                         |
|  allkeys-random-- random eviction.                                      |
|  volatile-random -- random among keys with TTL.                         |
|                                                                         |
|  HOW LRU WORKS IN REDIS:                                                |
|  * NOT exact LRU (too expensive to track access time for every key)     |
|  * Approximate LRU: sample N random keys, evict least recent            |
|  * maxmemory-samples 5 (default). Increase to 10 for better accuracy.   |
|                                                                         |
|  INTERVIEW TIP: "Redis LRU is approximate. It samples 5 keys            |
|  randomly and evicts the oldest. This is O(1) vs O(N) for exact LRU."   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q7: Explain the difference between DEL, UNLINK, and EXPIRE.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DEL key          -- synchronous delete. Blocks if key is large.        |
|                      O(N) where N = elements in collection.             |
|                      DEL a 1M-member set blocks Redis for seconds!      |
|                                                                         |
|  UNLINK key       -- asynchronous delete (Redis 4.0+).                  |
|                      Returns immediately, deletion in background.       |
|                      ALWAYS prefer UNLINK for large keys.               |
|                                                                         |
|  EXPIRE key 60    -- set key to auto-delete after 60 seconds.           |
|                      Key still exists until expiry.                     |
|                      TTL key -> remaining seconds.                      |
|                                                                         |
|  PERSIST key      -- remove expiry (make key permanent again).          |
|                                                                         |
|  INTERVIEW TIP: "A common production incident is DEL on a large         |
|  sorted set or hash with millions of entries, blocking Redis for        |
|  seconds. Always use UNLINK for potentially large keys."                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q8: What is the cache stampede problem and how do you solve it?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CACHE STAMPEDE (thundering herd):                                      |
|  A popular cache key expires, 1000 requests simultaneously hit          |
|  the database to rebuild the cache.                                     |
|                                                                         |
|  SOLUTIONS:                                                             |
|                                                                         |
|  1. DISTRIBUTED LOCK                                                    |
|     First request grabs a lock, rebuilds cache.                         |
|     Others wait or return stale data.                                   |
|                                                                         |
|  2. EARLY EXPIRATION (probabilistic)                                    |
|     Refresh cache before TTL expires.                                   |
|     Each request has a small probability of refreshing early.           |
|                                                                         |
|  3. STALE-WHILE-REVALIDATE                                              |
|     Serve stale data while refreshing in background.                    |
|     Two TTLs: soft (trigger refresh) + hard (actual expiry).            |
|                                                                         |
|  4. WARM CACHE ON STARTUP                                               |
|     Pre-populate cache before traffic arrives.                          |
|                                                                         |
|  5. NEVER EXPIRE + BACKGROUND REFRESH                                   |
|     Cache never expires. Background job updates periodically.           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.2: INTERMEDIATE (Q9-Q16)

### Q9: How would you implement a rate limiter with Redis?

```
+--------------------------------------------------------------------------+
|                                                                          |
|  SLIDING WINDOW with Sorted Set:                                         |
|                                                                          |
|  function isAllowed(userId, limit, windowSec):                           |
|      key = "ratelimit:" + userId                                         |
|      now = currentTimestamp()                                            |
|      windowStart = now - windowSec                                       |
|                                                                          |
|      MULTI                                                               |
|        ZREMRANGEBYSCORE key 0 windowStart   // remove old entries        |
|        ZADD key now requestId               // add current request       |
|        ZCARD key                            // count in window           |
|        EXPIRE key windowSec                 // cleanup safety            |
|      EXEC                                                                |
|                                                                          |
|      return count <= limit                                               |
|                                                                          |
|  For better performance, use Lua script (single round trip).             |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Q10: How does Redis replication work? Is it synchronous?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ASYNCHRONOUS by default:                                               |
|  * Master writes to local memory, responds to client                    |
|  * Master sends write to replicas asynchronously                        |
|  * Replica may lag behind (eventual consistency)                        |
|                                                                         |
|  SEMI-SYNCHRONOUS (optional):                                           |
|  WAIT 1 5000  -- wait for at least 1 replica to ack, 5s timeout         |
|  min-replicas-to-write 1    -- reject writes if < 1 replica alive       |
|  min-replicas-max-lag 10    -- reject if replica > 10s behind           |
|                                                                         |
|  REPLICATION PROCESS:                                                   |
|  1. Initial: Master does BGSAVE (RDB), sends to replica                 |
|  2. Ongoing: Master streams write commands to replica                   |
|  3. Short disconnect: Partial sync (from backlog buffer)                |
|  4. Long disconnect: Full sync again (new RDB)                          |
|                                                                         |
|  IMPORTANT: Replication is at the command level, not data level.        |
|  Non-deterministic commands (RANDOMKEY, TIME) are replaced with         |
|  deterministic equivalents before replicating.                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q11: What is the big-O complexity of Redis operations?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  STRINGS:                                                               |
|  GET, SET, INCR, SETNX           O(1)                                   |
|  MGET, MSET (N keys)             O(N)                                   |
|                                                                         |
|  HASHES:                                                                |
|  HGET, HSET, HDEL                O(1)                                   |
|  HGETALL (N fields)              O(N)   <-- avoid on large hashes!      |
|                                                                         |
|  LISTS:                                                                 |
|  LPUSH, RPUSH, LPOP, RPOP        O(1)                                   |
|  LINDEX                          O(N)   <-- linked list traversal       |
|  LRANGE                          O(S+N) where S=offset, N=count         |
|                                                                         |
|  SETS:                                                                  |
|  SADD, SREM, SISMEMBER           O(1)                                   |
|  SMEMBERS                        O(N)   <-- avoid on large sets!        |
|  SINTER, SUNION                  O(N*M) <-- can be slow!                |
|                                                                         |
|  SORTED SETS:                                                           |
|  ZADD, ZREM, ZSCORE              O(log N)                               |
|  ZRANGE, ZREVRANGE               O(log N + M)                           |
|  ZRANGEBYSCORE                   O(log N + M)                           |
|  ZRANK                           O(log N)                               |
|                                                                         |
|  DANGER COMMANDS (avoid in production):                                 |
|  KEYS *                          O(N) -- scans ALL keys, blocks Redis   |
|  Use SCAN instead                O(1) per iteration, cursor-based       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q12: How do you handle hot keys in Redis?

```
+--------------------------------------------------------------------------+
|                                                                          |
|  HOT KEY = One key receiving disproportionate traffic.                   |
|  Example: trending product page, viral tweet, flash sale item.           |
|                                                                          |
|  PROBLEMS:                                                               |
|  * Single Redis node overloaded (all requests to one shard)              |
|  * Network bottleneck on that node                                       |
|  * Uneven load across cluster                                            |
|                                                                          |
|  SOLUTIONS:                                                              |
|                                                                          |
|  1. LOCAL CACHE (L1 cache in app server)                                 |
|     Cache hot key in app memory (Guava, Caffeine) with short TTL.        |
|     Reduces Redis calls by 90%+.                                         |
|                                                                          |
|  2. READ REPLICAS                                                        |
|     Read from replicas to distribute load.                               |
|     Works for read-heavy hot keys.                                       |
|                                                                          |
|  3. KEY SPLITTING                                                        |
|     Split hot key into N sub-keys: product:123:0, product:123:1, ...     |
|     Client randomly picks one. Read all and merge.                       |
|     Distributes load across cluster slots.                               |
|                                                                          |
|  4. RATE LIMITING                                                        |
|     Limit requests to the hot key per client.                            |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Q13: What are Redis Streams and how do they compare to Kafka?

```
+---------------------------------------------------------------------------+
|                                                                           |
|  Redis Streams: append-only log with consumer groups.                     |
|                                                                           |
|  +-------------------+----------------------------+--------------------+  |
|  | Feature           | Redis Streams              | Kafka              |  |
|  +-------------------+----------------------------+--------------------+  |
|  | Storage           | In-memory (+persistence)   | Disk (log)         |  |
|  | Throughput         | ~100K msg/sec              | Millions/sec      |  |
|  | Retention          | Memory-limited             | Disk-limited      |  |
|  | Partitioning       | No (single stream)         | Yes (partitions)  |  |
|  | Consumer groups    | Yes                        | Yes               |  |
|  | Ordering           | Global (single stream)     | Per-partition     |  |
|  | Persistence        | Optional (AOF/RDB)         | Always (disk)     |  |
|  | Cluster support    | Hash slot based             | Native           |  |
|  +-------------------+----------------------------+--------------------+  |
|                                                                           |
|  USE STREAMS: < 100K msg/sec, want simplicity, already have Redis.        |
|  USE KAFKA: High throughput, partitioning, long retention, replay.        |
|                                                                           |
+---------------------------------------------------------------------------+
```

### Q14: How do you handle cache invalidation?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. TTL (simplest)                                                      |
|     SET key value EX 300                                                |
|     Data may be stale for up to TTL duration.                           |
|     Good for: product catalog, user profiles (soft real-time).          |
|                                                                         |
|  2. EXPLICIT INVALIDATION                                               |
|     On DB write: DEL cache:user:123                                     |
|     Next read rebuilds cache from DB.                                   |
|     Good for: data that MUST be fresh.                                  |
|                                                                         |
|  3. PUB/SUB BROADCAST                                                   |
|     DB write -> PUBLISH invalidate "user:123"                           |
|     All app servers subscribe and delete local cache.                   |
|     Good for: multi-instance deployments.                               |
|                                                                         |
|  4. CDC (Change Data Capture)                                           |
|     Debezium reads DB binlog -> Kafka -> Consumer invalidates cache.    |
|     Most reliable, no app code changes for invalidation.                |
|     Good for: microservices where writer doesn't know all caches.       |
|                                                                         |
|  5. VERSIONED KEYS                                                      |
|     cache:v3:user:123 -- change version on update.                      |
|     Old versions expire naturally via TTL.                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q15: Explain Redis pipelining and when to use it.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Pipeline sends multiple commands without waiting for each reply.       |
|  All replies returned at once.                                          |
|                                                                         |
|  WITHOUT: 100 commands x 1ms RTT = 100ms                                |
|  WITH PIPELINE: 100 commands, 1 round trip = 1ms                        |
|  SPEEDUP: 100x for latency, ~10x for throughput (50K -> 500K ops/sec)   |
|                                                                         |
|  IMPORTANT:                                                             |
|  * NOT atomic -- other clients can interleave between commands          |
|  * For atomicity: use MULTI/EXEC or Lua scripts                         |
|  * Don't pipeline 10K+ commands at once (memory buffer on server)       |
|  * Sweet spot: 50-1000 commands per pipeline                            |
|                                                                         |
|  USE WHEN:                                                              |
|  * Bulk reads (MGET alternative for different key types)                |
|  * Batch writes (bulk data loading)                                     |
|  * Operations where individual results don't affect next command        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q16: What happens when Redis master fails with Sentinel?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FAILOVER TIMELINE:                                                     |
|                                                                         |
|  1. Master stops responding                                             |
|  2. Each sentinel marks master as SUBJECTIVELY DOWN (SDOWN)             |
|     after down-after-milliseconds (default 30s)                         |
|  3. When quorum sentinels agree -> OBJECTIVELY DOWN (ODOWN)             |
|  4. Sentinels elect a leader sentinel                                   |
|  5. Leader picks best replica (most data, lowest lag)                   |
|  6. Leader sends REPLICAOF NO ONE to chosen replica (promotes it)       |
|  7. Other replicas reconfigure to follow new master                     |
|  8. Clients query sentinel for new master address                       |
|                                                                         |
|  TOTAL TIME: 30-60 seconds (dominated by detection timeout)             |
|                                                                         |
|  DATA LOSS: Possible! Async replication means some writes to            |
|  old master may not have reached the promoted replica.                  |
|  Mitigate: min-replicas-to-write 1 + min-replicas-max-lag 10            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.3: ADVANCED (Q17-Q25)

### Q17: Design a distributed rate limiter using Redis.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REQUIREMENTS: 100K+ users, 1000 req/min per user, multi-server.        |
|                                                                         |
|  APPROACH: Sliding window counter (Lua script for atomicity)            |
|                                                                         |
|  -- Lua script: sliding window rate limiter                             |
|  local key = KEYS[1]                                                    |
|  local window = tonumber(ARGV[1])  -- window in seconds                 |
|  local limit = tonumber(ARGV[2])   -- max requests                      |
|  local now = tonumber(ARGV[3])     -- current timestamp (ms)            |
|                                                                         |
|  -- Remove entries outside window                                       |
|  redis.call('ZREMRANGEBYSCORE', key, 0, now - window * 1000)            |
|  -- Count current window                                                |
|  local count = redis.call('ZCARD', key)                                 |
|  if count < limit then                                                  |
|      redis.call('ZADD', key, now, now .. math.random())                 |
|      redis.call('EXPIRE', key, window)                                  |
|      return 1  -- allowed                                               |
|  end                                                                    |
|  return 0  -- rate limited                                              |
|                                                                         |
|  SCALE: Atomic per user (Lua runs on one key's node in cluster).        |
|  Each user's counter is ~1KB. 100K users = ~100MB.                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q18: How would you design a leaderboard for 10M players?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DATA STRUCTURE: Sorted Set                                             |
|                                                                         |
|  ZADD leaderboard {score} {player_id}                                   |
|  ZINCRBY leaderboard {points} {player_id}                               |
|  ZREVRANK leaderboard {player_id}    -- rank (0-indexed)                |
|  ZREVRANGE leaderboard 0 99 WITHSCORES  -- top 100                      |
|                                                                         |
|  MEMORY: 10M members ~= 600-800 MB                                      |
|  PERFORMANCE: O(log N) for all operations = O(log 10M) = ~23 ops        |
|                                                                         |
|  SHARDED LEADERBOARD (if too big for one instance):                     |
|  * Shard by score range: shard1 (0-1M), shard2 (1M-2M), ...             |
|  * Or shard by region: leaderboard:us, leaderboard:eu                   |
|  * Merge: ZUNIONSTORE for cross-shard queries                           |
|                                                                         |
|  TIME-BASED:                                                            |
|  * Daily: leaderboard:2024-01-15 (EXPIRE 86400)                         |
|  * Weekly: ZUNIONSTORE week day1 day2 ... day7                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q19: Explain the Redlock algorithm.

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Redlock = Distributed lock across N independent Redis instances.        |
|                                                                          |
|  ALGORITHM:                                                              |
|  1. Get current time T1                                                  |
|  2. Try SET lock {uuid} NX EX {ttl} on all N instances (N=5)             |
|  3. Lock acquired if majority (>= 3/5) succeed AND                       |
|     elapsed time (T2 - T1) < lock TTL                                    |
|  4. Actual lock validity = TTL - elapsed acquisition time                |
|  5. If failed: DEL lock on ALL instances (even failed ones)              |
|                                                                          |
|  WHY 5 INSTANCES?                                                        |
|  * Tolerates up to 2 failures (majority = 3)                             |
|  * Must be independent (not replicas of each other!)                     |
|  * Can be on same physical servers (different ports)                     |
|                                                                          |
|  CONTROVERSY (Martin Kleppmann):                                         |
|  * GC pauses can cause lock to expire during processing                  |
|  * Clock drift between servers can invalidate assumptions                |
|  * Solution: fencing tokens (monotonic ID checked by resource)           |
|                                                                          |
|  PRAGMATIC ADVICE:                                                       |
|  * For most systems: single Redis lock + idempotent operations           |
|  * For critical systems: Redlock + fencing tokens                        |
|  * For strongest guarantees: ZooKeeper or etcd                           |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Q20: How do you troubleshoot a slow Redis instance?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  STEP 1: CHECK LATENCY                                                  |
|  redis-cli --latency              (measure round-trip)                  |
|  redis-cli --latency-history      (over time)                           |
|  redis-cli --intrinsic-latency 5  (baseline system latency)             |
|                                                                         |
|  STEP 2: FIND SLOW COMMANDS                                             |
|  CONFIG SET slowlog-log-slower-than 10000  (log cmds > 10ms)            |
|  SLOWLOG GET 10                   (last 10 slow commands)               |
|                                                                         |
|  STEP 3: CHECK FOR BIG KEYS                                             |
|  redis-cli --bigkeys              (scan for large keys)                 |
|  MEMORY USAGE key                 (bytes for specific key)              |
|                                                                         |
|  STEP 4: CHECK MEMORY                                                   |
|  INFO memory                      (used_memory, fragmentation)          |
|  If fragmentation > 1.5: restart Redis or enable active-defrag          |
|                                                                         |
|  STEP 5: CHECK CONNECTIONS                                              |
|  INFO clients                     (connected_clients)                   |
|  CLIENT LIST                      (per-client details)                  |
|                                                                         |
|  COMMON CULPRITS:                                                       |
|  * KEYS * in production (blocks, scans all keys) -> use SCAN            |
|  * DEL on huge key (millions of members) -> use UNLINK                  |
|  * HGETALL on huge hash -> use HSCAN                                    |
|  * Lua script too long -> blocks everything                             |
|  * AOF rewrite under load -> increases latency                          |
|  * Swapping (Redis using disk swap) -> increase RAM or reduce data      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q21: How do you handle Redis in a microservices architecture?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PATTERNS:                                                              |
|                                                                         |
|  1. SHARED REDIS (simple, small teams)                                  |
|     All services use one Redis cluster.                                 |
|     Use key prefixes: svc-order:cache:123, svc-user:session:abc         |
|     Risk: noisy neighbor, blast radius.                                 |
|                                                                         |
|  2. REDIS PER SERVICE (recommended)                                     |
|     Each service owns its Redis instance.                               |
|     Full isolation, independent scaling.                                |
|     Cost: more instances to manage.                                     |
|                                                                         |
|  3. HYBRID                                                              |
|     Shared Redis for cross-service data (sessions, rate limits).        |
|     Dedicated Redis for service-specific caches.                        |
|                                                                         |
|  BEST PRACTICES:                                                        |
|  * Never let one service read another service's Redis directly          |
|  * Use pub/sub or events for cross-service cache invalidation           |
|  * Set maxmemory + eviction policy on every instance                    |
|  * Monitor per-instance: memory, connections, latency, hit rate         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q22: What is Redis memory fragmentation and how to fix it?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FRAGMENTATION RATIO = used_memory_rss / used_memory                    |
|                                                                         |
|  ratio < 1.0: Redis using swap (BAD, very slow)                         |
|  ratio 1.0-1.5: Normal, healthy                                         |
|  ratio > 1.5: High fragmentation (wasted memory)                        |
|  ratio > 2.0: Severe fragmentation                                      |
|                                                                         |
|  CAUSES:                                                                |
|  * Frequent create/delete of different-sized keys                       |
|  * Many small objects allocated and freed                               |
|  * Memory allocator (jemalloc) keeps freed pages                        |
|                                                                         |
|  FIXES:                                                                 |
|  * Restart Redis (fresh allocation, defragmented)                       |
|  * Active defragmentation (Redis 4.0+):                                 |
|    activedefrag yes                                                     |
|    active-defrag-threshold-lower 10   (start if > 10% fragmented)       |
|    active-defrag-threshold-upper 100  (max effort if > 100%)            |
|  * Use consistent key sizes where possible                              |
|  * Avoid heavy churn of variable-size keys                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q23: How do you migrate from one Redis instance to another?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. RDB SNAPSHOT (simplest, offline)                                    |
|     BGSAVE on source -> copy dump.rdb -> load on target                 |
|     Downtime required for consistency.                                  |
|                                                                         |
|  2. REPLICATION (zero-downtime)                                         |
|     Make target a replica of source (REPLICAOF src_host src_port)       |
|     Wait for sync to complete                                           |
|     Promote target (REPLICAOF NO ONE)                                   |
|     Switch clients to target                                            |
|                                                                         |
|  3. REDIS-SHAKE / RIOT (tools for migration)                            |
|     Support cross-version, cross-cluster, filtered migration.           |
|                                                                         |
|  4. DUAL WRITE (application-level)                                      |
|     Write to both old and new Redis.                                    |
|     Gradually move reads to new.                                        |
|     Verify consistency.                                                 |
|     Stop writing to old.                                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q24: What is the difference between SCAN and KEYS?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KEYS pattern:                                                          |
|  * Scans ALL keys in one shot                                           |
|  * O(N) -- blocks Redis for the entire duration                         |
|  * NEVER use in production (can block for seconds/minutes)              |
|                                                                         |
|  SCAN cursor [MATCH pattern] [COUNT hint]:                              |
|  * Iterates keys incrementally using a cursor                           |
|  * O(1) per iteration, non-blocking                                     |
|  * Returns cursor=0 when done                                           |
|  * May return duplicates (idempotent processing needed)                 |
|  * COUNT is a hint (not guaranteed exact count per iteration)           |
|                                                                         |
|  VARIANTS:                                                              |
|  HSCAN key cursor   -- iterate hash fields                              |
|  SSCAN key cursor   -- iterate set members                              |
|  ZSCAN key cursor   -- iterate sorted set members                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q25: Capacity estimation -- how much Redis do you need?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FORMULA:                                                               |
|  Total memory = num_keys x (key_size + value_size + overhead)           |
|                                                                         |
|  OVERHEAD PER KEY:                                                      |
|  * Key pointer + expiry + type info = ~70-100 bytes per key             |
|  * String value < 44 bytes: ~90 bytes total per key-value               |
|  * Hash with 5 small fields: ~200 bytes                                 |
|  * Sorted set member: ~80 bytes per member                              |
|                                                                         |
|  EXAMPLE:                                                               |
|  10M user sessions, each 1 KB value:                                    |
|  * Payload: 10M x 1 KB = 10 GB                                          |
|  * Overhead: 10M x 100 bytes = 1 GB                                     |
|  * Total: ~11 GB + 30% buffer = ~15 GB                                  |
|                                                                         |
|  SIZING:                                                                |
|  * Set maxmemory to 75% of physical RAM (leave room for fork/AOF)       |
|  * For replication: double the memory (master + replica)                |
|  * Monitor actual usage with INFO memory                                |
|                                                                         |
|  INSTANCE SIZING GUIDE:                                                 |
|  * < 25 GB: Single Sentinel setup                                       |
|  * 25-100 GB: Large instance + Sentinel                                 |
|  * > 100 GB: Redis Cluster (shard across masters)                       |
|                                                                         |
+-------------------------------------------------------------------------+
```
