# DISTRIBUTED CACHE SYSTEM DESIGN
*Chapter 5: Interview Questions and Answers*

This chapter provides detailed answers to common interview questions
about distributed caching and Redis.

## SECTION 5.1: FUNDAMENTAL QUESTIONS

### Q1: DESIGN A DISTRIBUTED CACHE SYSTEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REQUIREMENTS (Clarify first)                                           |
|  * Read-heavy or write-heavy?                                           |
|  * Consistency requirements?                                            |
|  * Data size? (determines if single node or distributed)                |
|  * Latency requirements? (sub-millisecond typical)                      |
|                                                                         |
|  HIGH-LEVEL DESIGN                                                      |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Clients (App Servers)                                            |  |
|  |       |                                                           |  |
|  |       | GET/SET                                                   |  |
|  |       v                                                           |  |
|  |  +-------------------------------------------------------------+  |  |
|  |  |                Cache Client Library                         |  |  |
|  |  |  - Consistent hashing                                       |  |  |
|  |  |  - Connection pooling                                       |  |  |
|  |  |  - Retry logic                                              |  |  |
|  |  +-------------------------------------------------------------+  |  |
|  |       |                                                           |  |
|  |       | Route to correct node                                     |  |
|  |       v                                                           |  |
|  |  +----------+  +----------+  +----------+                         |  |
|  |  | Cache    |  | Cache    |  | Cache    |                         |  |
|  |  | Node 1   |  | Node 2   |  | Node 3   |                         |  |
|  |  |          |  |          |  |          |                         |  |
|  |  | Replica  |  | Replica  |  | Replica  |                         |  |
|  |  +----------+  +----------+  +----------+                         |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  KEY COMPONENTS                                                         |
|  --------------                                                         |
|  1. Data Distribution: Consistent hashing with virtual nodes            |
|  2. Replication: Leader-follower for HA                                 |
|  3. Eviction: LRU with memory limits                                    |
|  4. Persistence: RDB + AOF for durability                               |
|  5. Failover: Automatic master election (Sentinel/Cluster)              |
|                                                                         |
|  TRADE-OFFS TO DISCUSS                                                  |
|  ----------------------                                                 |
|  * Consistency vs Availability (async replication = eventual)           |
|  * Memory vs Disk (in-memory fast, but limited/expensive)               |
|  * Single node vs Cluster (complexity vs scale)                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q2: EXPLAIN CONSISTENT HASHING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER                                                                 |
|                                                                         |
|  PROBLEM WITH MODULO HASHING                                            |
|  ----------------------------                                           |
|  node = hash(key) % N                                                   |
|                                                                         |
|  If N changes (add/remove node), almost all keys remap.                 |
|  Massive cache invalidation. Bad!                                       |
|                                                                         |
|  CONSISTENT HASHING SOLUTION                                            |
|  ----------------------------                                           |
|                                                                         |
|  1. Imagine a circular ring (0 to 2^32)                                 |
|  2. Hash nodes onto the ring                                            |
|  3. Hash keys onto the ring                                             |
|  4. Key belongs to first node clockwise                                 |
|                                                                         |
|  When node added/removed:                                               |
|  * Only keys between affected nodes move                                |
|  * On average, only 1/N keys move                                       |
|                                                                         |
|  VIRTUAL NODES                                                          |
|  -------------                                                          |
|  Each physical node gets multiple positions on ring.                    |
|  Ensures even distribution even with few nodes.                         |
|  Typical: 100-200 virtual nodes per physical node.                      |
|                                                                         |
|  COMPLEXITY                                                             |
|  ----------                                                             |
|  * Add/remove node: O(K/N) keys move (K=total keys, N=nodes)            |
|  * Lookup: O(log N) with binary search                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q3: HOW DO YOU HANDLE CACHE STAMPEDE?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER                                                                 |
|                                                                         |
|  THE PROBLEM                                                            |
|  -----------                                                            |
|  Popular cache key expires.                                             |
|  Many requests see cache miss.                                          |
|  All query database simultaneously.                                     |
|  Database overloaded.                                                   |
|                                                                         |
|  SOLUTIONS                                                              |
|  ---------                                                              |
|                                                                         |
|  1. LOCKING                                                             |
|     * First request acquires lock                                       |
|     * Others wait for cache to populate                                 |
|     * Only one DB query                                                 |
|                                                                         |
|     if cache.setnx("lock:key", 1, ttl=10):                              |
|         value = db.get(key)                                             |
|         cache.set(key, value)                                           |
|         cache.delete("lock:key")                                        |
|     else:                                                               |
|         wait_and_retry()                                                |
|                                                                         |
|  2. EARLY/PROBABILISTIC REFRESH                                         |
|     * Refresh cache BEFORE expiration                                   |
|     * Random chance to refresh as TTL approaches                        |
|     * Only one request likely to refresh                                |
|                                                                         |
|  3. STALE-WHILE-REVALIDATE                                              |
|     * Return stale data immediately                                     |
|     * Refresh in background                                             |
|     * Fast response, eventually consistent                              |
|                                                                         |
|  RECOMMENDATION                                                         |
|  --------------                                                         |
|  Use locking for critical data.                                         |
|  Use stale-while-revalidate for less critical data.                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.2: REDIS-SPECIFIC QUESTIONS

### Q4: WHY IS REDIS SINGLE-THREADED? ISN'T THAT SLOW?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER                                                                 |
|                                                                         |
|  Redis IS single-threaded for command execution.                        |
|  But it's NOT slow because:                                             |
|                                                                         |
|  1. MEMORY IS FAST                                                      |
|     * RAM access: ~100 nanoseconds                                      |
|     * No disk I/O for normal operations                                 |
|     * CPU is rarely the bottleneck                                      |
|                                                                         |
|  2. NETWORK IS THE BOTTLENECK                                           |
|     * Network round-trip: ~0.5 milliseconds                             |
|     * 10,000x slower than memory                                        |
|     * Adding threads doesn't help network                               |
|                                                                         |
|  3. NO CONTEXT SWITCHING                                                |
|     * Multi-threaded = locks, contention, overhead                      |
|     * Single-threaded = simple, predictable                             |
|                                                                         |
|  4. ATOMIC OPERATIONS                                                   |
|     * All commands atomic by default                                    |
|     * No need for complex locking                                       |
|                                                                         |
|  PERFORMANCE                                                            |
|  -----------                                                            |
|  Single Redis instance: ~100,000 ops/sec                                |
|  That's usually enough! If not:                                         |
|  * Use pipelining (batch commands)                                      |
|  * Use Redis Cluster (multiple nodes)                                   |
|                                                                         |
|  REDIS 6.0+ THREADING                                                   |
|  ---------------------                                                  |
|  * I/O threads for network read/write                                   |
|  * Command execution still single-threaded                              |
|  * Helps with large values                                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q5: RDB vs AOF - WHEN TO USE WHICH?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER                                                                 |
|                                                                         |
|  RDB (Snapshots)                                                        |
|  ================                                                       |
|  * Point-in-time snapshots                                              |
|  * Compact binary format                                                |
|  * Fast restart (load entire dataset)                                   |
|  * Potential data loss (between snapshots)                              |
|                                                                         |
|  USE WHEN:                                                              |
|  * Data loss is acceptable                                              |
|  * Want fast backups                                                    |
|  * Need fast restarts                                                   |
|                                                                         |
|  AOF (Append-Only File)                                                 |
|  ========================                                               |
|  * Logs every write operation                                           |
|  * Text format (human readable)                                         |
|  * Slower restart (replay all commands)                                 |
|  * Minimal data loss (1 sec with fsync everysec)                        |
|                                                                         |
|  USE WHEN:                                                              |
|  * Durability is critical                                               |
|  * Can't afford data loss                                               |
|                                                                         |
|  RECOMMENDATION                                                         |
|  --------------                                                         |
|  Use BOTH for production:                                               |
|  * RDB for backups and fast restarts                                    |
|  * AOF for durability                                                   |
|                                                                         |
|  If just caching (data can be regenerated), RDB alone is fine.          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q6: REDIS CLUSTER vs SENTINEL - WHAT'S THE DIFFERENCE?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER                                                                 |
|                                                                         |
|  REDIS SENTINEL                                                         |
|  ================                                                       |
|  * High availability WITHOUT sharding                                   |
|  * One master, multiple replicas                                        |
|  * Sentinel processes monitor and failover                              |
|  * All data on single master (limited by one node's memory)             |
|  * Supports all Redis commands                                          |
|                                                                         |
|  USE WHEN:                                                              |
|  * Data fits on single node (<100GB typical)                            |
|  * Need simple HA                                                       |
|  * Use multi-key operations frequently                                  |
|                                                                         |
|  REDIS CLUSTER                                                          |
|  ===============                                                        |
|  * Sharding + high availability                                         |
|  * Data distributed across multiple masters                             |
|  * Each master has replicas                                             |
|  * Built-in routing (MOVED redirects)                                   |
|  * Multi-key ops only with hash tags                                    |
|                                                                         |
|  USE WHEN:                                                              |
|  * Data exceeds single node capacity                                    |
|  * Need high throughput (multiple masters)                              |
|  * Can work around multi-key limitations                                |
|                                                                         |
|  COMPARISON TABLE                                                       |
|  -----------------                                                      |
|  +----------------+----------------+----------------+                   |
|  | Feature        | Sentinel       | Cluster        |                   |
|  +----------------+----------------+----------------+                   |
|  | Sharding       | No             | Yes            |                   |
|  | Max data       | 1 node limit   | Unlimited      |                   |
|  | Multi-key ops  | Full support   | Hash tags only |                   |
|  | Complexity     | Lower          | Higher         |                   |
|  | Min nodes      | 3 (sentinels)  | 6 (3M + 3R)   |                    |
|  +----------------+----------------+----------------+                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.3: SCENARIO-BASED QUESTIONS

### Q7: HOW WOULD YOU IMPLEMENT RATE LIMITING WITH REDIS?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER                                                                 |
|                                                                         |
|  APPROACH 1: FIXED WINDOW                                               |
|  =========================                                              |
|                                                                         |
|  def is_allowed(user_id, limit=100, window=60):                         |
|      key = f"rate:{user_id}:{int(time.time() / window)}"                |
|                                                                         |
|      current = redis.incr(key)                                          |
|      if current == 1:                                                   |
|          redis.expire(key, window)                                      |
|                                                                         |
|      return current <= limit                                            |
|                                                                         |
|  PROS: Simple, memory efficient                                         |
|  CONS: Burst at window boundary (can do 2x limit)                       |
|                                                                         |
|  APPROACH 2: SLIDING WINDOW (Sorted Set)                                |
|  =========================================                              |
|                                                                         |
|  def is_allowed(user_id, limit=100, window=60):                         |
|      key = f"rate:{user_id}"                                            |
|      now = time.time()                                                  |
|      cutoff = now - window                                              |
|                                                                         |
|      # Remove old entries                                               |
|      redis.zremrangebyscore(key, 0, cutoff)                             |
|                                                                         |
|      # Count current entries                                            |
|      count = redis.zcard(key)                                           |
|                                                                         |
|      if count < limit:                                                  |
|          # Add this request                                             |
|          redis.zadd(key, {str(uuid.uuid4()): now})                      |
|          redis.expire(key, window)                                      |
|          return True                                                    |
|                                                                         |
|      return False                                                       |
|                                                                         |
|  PROS: Accurate, no burst at boundary                                   |
|  CONS: More memory, more operations                                     |
|                                                                         |
|  APPROACH 3: TOKEN BUCKET (Lua Script)                                  |
|  =====================================                                  |
|                                                                         |
|  -- Lua script for atomic token bucket                                  |
|  local key = KEYS[1]                                                    |
|  local rate = tonumber(ARGV[1])  -- tokens per second                   |
|  local capacity = tonumber(ARGV[2])                                     |
|  local now = tonumber(ARGV[3])                                          |
|  local requested = tonumber(ARGV[4])                                    |
|                                                                         |
|  local data = redis.call('HMGET', key, 'tokens', 'last_time')           |
|  local tokens = tonumber(data[1]) or capacity                           |
|  local last_time = tonumber(data[2]) or now                             |
|                                                                         |
|  -- Add tokens based on time elapsed                                    |
|  local elapsed = now - last_time                                        |
|  tokens = math.min(capacity, tokens + elapsed * rate)                   |
|                                                                         |
|  if tokens >= requested then                                            |
|      tokens = tokens - requested                                        |
|      redis.call('HMSET', key, 'tokens', tokens, 'last_time', now)       |
|      redis.call('EXPIRE', key, capacity / rate * 2)                     |
|      return 1  -- Allowed                                               |
|  end                                                                    |
|                                                                         |
|  return 0  -- Denied                                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q8: HOW DO YOU IMPLEMENT A DISTRIBUTED LOCK WITH REDIS?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER                                                                 |
|                                                                         |
|  BASIC LOCK                                                             |
|  ==========                                                             |
|                                                                         |
|  def acquire_lock(lock_name, timeout=10):                               |
|      lock_value = str(uuid.uuid4())  # Unique per lock holder           |
|                                                                         |
|      if redis.set(lock_name, lock_value, nx=True, ex=timeout):          |
|          return lock_value  # Got the lock                              |
|      return None  # Lock held by someone else                           |
|                                                                         |
|  def release_lock(lock_name, lock_value):                               |
|      # MUST check value before deleting (Lua script for atomicity)      |
|      script = """                                                       |
|      if redis.call('GET', KEYS[1]) == ARGV[1] then                      |
|          return redis.call('DEL', KEYS[1])                              |
|      end                                                                |
|      return 0                                                           |
|      """                                                                |
|      return redis.eval(script, 1, lock_name, lock_value)                |
|                                                                         |
|  WHY CHECK VALUE?                                                       |
|  -----------------                                                      |
|  Without check:                                                         |
|  1. Client A acquires lock                                              |
|  2. Client A takes too long, lock expires                               |
|  3. Client B acquires lock                                              |
|  4. Client A finishes, deletes lock (B's lock!)                         |
|  5. Client C acquires lock (B and C both think they have it!)           |
|                                                                         |
|  REDLOCK (Multiple Redis instances)                                     |
|  ===================================                                    |
|                                                                         |
|  For critical sections, use Redlock:                                    |
|  1. Get current time                                                    |
|  2. Try to acquire lock on N/2+1 instances                              |
|  3. If majority acquired AND time elapsed < TTL, lock acquired          |
|  4. If not, release all locks                                           |
|                                                                         |
|  CAVEATS                                                                |
|  -------                                                                |
|  * Redis locks are advisory (not foolproof)                             |
|  * Clock skew can cause issues                                          |
|  * For critical sections, use database locks as backup                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.4: QUICK-FIRE Q&A

Q: What eviction policy should I use?
A: LRU (allkeys-lru) for most cases. LFU if access pattern is highly skewed.

Q: How do I cache NULL values?
A: Use a sentinel value like "NULL_MARKER" with short TTL (5 min vs 1 hour).

Q: What's the maximum value size in Redis?
A: 512MB, but keep values small (<1MB) for performance.

Q: How do I handle cache warming?
A: Pre-load popular keys on deployment. Use gradual traffic shift to new nodes.

Q: Can Redis guarantee no data loss?
A: With AOF fsync=always, minimal loss. But not zero - use database for ACID.

Q: How many connections can Redis handle?
A: Default 10,000. Can increase, but use connection pooling instead.

Q: What's the difference between EXPIRE and EXPIREAT?
A: EXPIRE is relative (seconds from now). EXPIREAT is absolute (Unix timestamp).

Q: How do I debug slow Redis?
A: SLOWLOG GET, redis-cli --latency, INFO commandstats.

Q: Should I use Redis for sessions?
A: Yes! Perfect use case. Use HASH for session data, SET with TTL.

Q: How do I handle Redis failover in my app?
A: Use Sentinel-aware client, handle connection errors, implement retry logic.

## SECTION 5.5: SYSTEM DESIGN INTERVIEW TEMPLATE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  45-MINUTE CACHE DESIGN INTERVIEW                                       |
|                                                                         |
|  1. REQUIREMENTS (5 min)                                                |
|     o Data size (fits on one node or needs sharding?)                   |
|     o Read/write ratio                                                  |
|     o Consistency needs (eventual OK or strict?)                        |
|     o Durability (can regenerate data or need persistence?)             |
|     o Latency requirements                                              |
|                                                                         |
|  2. HIGH-LEVEL DESIGN (10 min)                                          |
|     o Cache-aside pattern (most common)                                 |
|     o Consistent hashing for distribution                               |
|     o Leader-follower replication for HA                                |
|                                                                         |
|  3. DEEP DIVE (20 min)                                                  |
|     o Eviction policy (LRU, LFU, TTL)                                   |
|     o Cache invalidation strategy                                       |
|     o Handling stampede/hot keys                                        |
|     o Persistence (RDB/AOF trade-offs)                                  |
|                                                                         |
|  4. SCALING (5 min)                                                     |
|     o How to add more nodes?                                            |
|     o How to handle hot keys?                                           |
|     o Redis Cluster vs Sentinel                                         |
|                                                                         |
|  5. WRAP UP (5 min)                                                     |
|     o Trade-offs discussed                                              |
|     o Monitoring and operations                                         |
|     o Questions for interviewer                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## INTERVIEW CRUX — SAY THIS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DISTRIBUTED CACHE — WHAT TO SAY IN THE INTERVIEW                       |
|                                                                         |
|  DEFAULT ANSWER (when asked "how would you design X?"):                 |
|  * Data distribution via CONSISTENT HASHING (virtual nodes to           |
|      smooth load); node add/remove moves only 1/N of keys               |
|  * Redis Cluster: 16,384 hash slots, gossip protocol, each              |
|      master has async replicas; CRC16(key) % 16384 -> slot              |
|  * Replication: primary-replica async (fast, may lose <1s of            |
|      writes on failover); can add semi-sync for critical data           |
|  * Cache-aside is the default pattern: app reads cache, on              |
|      miss reads DB and populates cache; write = update DB +             |
|      DELETE cache key                                                   |
|  * TTL on every key as safety net; jitter TTLs to avoid mass            |
|      expiry (cache avalanche)                                           |
|                                                                         |
|  IF ASKED "how do you handle X?" (~3-5 common follow-ups):              |
|  * cache stampede? SETNX lock so only one rebuilder; early              |
|      refresh at 80% TTL; jitter                                         |
|  * hot key (celebrity)? 2-tier cache (local LRU in-app +                |
|      Redis); replicate hot key across shards + random pick              |
|  * cache penetration (bots probing missing keys)? Cache NULL            |
|      with short TTL; bloom filter in front for hard 404                 |
|  * consistency with DB? Cache-aside + delete-on-write + TTL;            |
|      transactional outbox for invalidations you must not lose           |
|  * cluster vs sentinel? Sentinel = HA only (single dataset);            |
|      Cluster = HA + sharding (16K slots)                                |
|  * RDB vs AOF? RDB = periodic snapshot (fast restart, some              |
|      loss); AOF = append-only log (durable, larger disk)                |
|  * why single-threaded Redis? Avoids locks; scale via cluster           |
|      + pipelining; still 100K+ ops/sec per node                         |
|                                                                         |
|  NUMBERS TO DROP:                                                       |
|  * Redis: 100K+ ops/sec/node, < 1 ms latency                            |
|  * Target hit rate: 80-99% (< 80% = redesign)                           |
|  * Redis Cluster: 16,384 slots, up to 1000 nodes practical              |
|  * CDN edge: ~20 ms vs origin ~300 ms cross-continent                   |
|  * Consistent hashing: 100-200 virtual nodes per physical               |
|  * Cache-aside miss cost: 10-100 ms (DB) vs 1 ms (hit)                  |
|                                                                         |
|  REAL-WORLD PATTERNS TO NAME-DROP:                                      |
|  * Facebook: memcached + TAO (cache-aside at scale)                     |
|  * Twitter: Redis for timelines (write-fanout to cache)                 |
|  * Netflix: EVCache (memcached-based, multi-region replicate)           |
|  * Instagram: Redis + memcached 2-tier                                  |
|                                                                         |
|  ONE-LINE CRUX:                                                         |
|  "Consistent hashing + Redis Cluster (16K slots) + cache-aside with TTL |
|   + jitter, replicate hot keys, bloom for penetration."                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 5

