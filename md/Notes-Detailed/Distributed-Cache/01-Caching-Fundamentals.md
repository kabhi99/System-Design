# DISTRIBUTED CACHE SYSTEM DESIGN
*Chapter 1: Caching Fundamentals*

Caching is one of the most effective techniques for improving system
performance. This chapter covers the fundamentals of caching, why it
works, and when to use it.

## SECTION 1.1: WHAT IS CACHING?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CACHING DEFINITION                                                    |
|                                                                         |
|  A cache is a high-speed data storage layer that stores a subset     |
|  of data, typically transient, so that future requests for that      |
|  data are served faster than accessing the primary storage.          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WITHOUT CACHE                            WITH CACHE                   |
|  ==============                            ==========                   |
|                                                                         |
|  Client -----------> Database             Client                       |
|         <----------- (50-100ms)               |                        |
|                                               v                        |
|  Every request hits database.             +-------+                    |
|  Database under heavy load.               | Cache | <-- Hit: <1ms     |
|                                           +---+---+                    |
|                                               | Miss                   |
|                                               v                        |
|                                           Database (50ms)              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WHY CACHING WORKS                                                     |
|                                                                         |
|  1. LOCALITY OF REFERENCE                                              |
|     * Temporal: Recently accessed data is likely to be accessed again|
|     * Spatial: Data near recently accessed data likely to be accessed|
|                                                                         |
|  2. PARETO PRINCIPLE (80/20 Rule)                                      |
|     * 20% of data serves 80% of requests                             |
|     * Cache the hot data, ignore the cold                            |
|                                                                         |
|  3. READ/WRITE RATIO                                                   |
|     * Most applications are read-heavy                               |
|     * Read: 95-99% of operations                                     |
|     * Cache benefits reads the most                                   |
|                                                                         |
|  CACHE HIT vs MISS                                                     |
|  =================                                                      |
|                                                                         |
|  Cache Hit: Data found in cache > return immediately                 |
|  Cache Miss: Data not in cache > fetch from source, store in cache  |
|                                                                         |
|  Hit Rate = Cache Hits / (Cache Hits + Cache Misses)                 |
|                                                                         |
|  Target: 90%+ hit rate for effective caching                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.2: CACHE ACCESS PATTERNS

### PATTERN 1: CACHE-ASIDE (Lazy Loading)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CACHE-ASIDE                                                           |
|                                                                         |
|  Application manages cache directly.                                  |
|  Most common pattern.                                                  |
|                                                                         |
|  READ FLOW:                                                            |
|  -----------                                                            |
|                                                                         |
|  1. Application checks cache                                          |
|  2. If hit: return cached data                                       |
|  3. If miss: read from DB, store in cache, return                   |
|                                                                         |
|       App                Cache              Database                   |
|        |   GET key         |                   |                      |
|        |------------------>|                   |                      |
|        |   Hit? Return     |                   |                      |
|        |<------------------|                   |                      |
|        |                   |                   |                      |
|   OR (miss):               |                   |                      |
|        |   Miss            |                   |                      |
|        |<------------------|                   |                      |
|        |                   |   SELECT          |                      |
|        |-------------------------------------->|                      |
|        |<--------------------------------------|                      |
|        |   SET key         |                   |                      |
|        |------------------>|                   |                      |
|        |                   |                   |                      |
|                                                                         |
|  WRITE FLOW:                                                           |
|  ------------                                                           |
|  1. Write to database                                                 |
|  2. Invalidate cache (delete key)                                    |
|                                                                         |
|  def get_user(user_id):                                               |
|      # Try cache first                                                |
|      cached = cache.get(f"user:{user_id}")                           |
|      if cached:                                                        |
|          return cached                                                 |
|                                                                         |
|      # Cache miss - get from database                                |
|      user = db.query("SELECT * FROM users WHERE id = ?", user_id)   |
|                                                                         |
|      # Store in cache for next time                                   |
|      cache.set(f"user:{user_id}", user, ttl=3600)                    |
|                                                                         |
|      return user                                                       |
|                                                                         |
|  def update_user(user_id, data):                                      |
|      db.execute("UPDATE users SET ... WHERE id = ?", user_id, data)  |
|      cache.delete(f"user:{user_id}")  # Invalidate cache            |
|                                                                         |
|  PROS:                                                                 |
|  Y Only requested data is cached                                     |
|  Y Cache failures don't break the system                            |
|  Y Simple to implement                                               |
|                                                                         |
|  CONS:                                                                 |
|  X First request is always slow (cache miss)                        |
|  X Stale data possible if invalidation fails                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### PATTERN 2: READ-THROUGH

```
+-------------------------------------------------------------------------+
|                                                                         |
|  READ-THROUGH                                                          |
|                                                                         |
|  Cache sits in front of database.                                     |
|  Cache loads data from DB on miss.                                    |
|  Application only talks to cache.                                     |
|                                                                         |
|       App                Cache              Database                   |
|        |   GET key         |                   |                      |
|        |------------------>|                   |                      |
|        |                   |  (cache checks)   |                      |
|        |                   |   Miss? Load      |                      |
|        |                   |------------------>|                      |
|        |                   |<------------------|                      |
|        |                   |  (store in cache) |                      |
|        |<------------------|                   |                      |
|        |   Return data     |                   |                      |
|                                                                         |
|  DIFFERENCE FROM CACHE-ASIDE:                                         |
|  * Cache-aside: Application fetches from DB on miss                  |
|  * Read-through: Cache fetches from DB on miss                       |
|                                                                         |
|  PROS:                                                                 |
|  Y Simpler application code                                          |
|  Y Cache handles loading logic                                       |
|                                                                         |
|  CONS:                                                                 |
|  X First request still slow                                          |
|  X Cache must understand how to load data                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### PATTERN 3: WRITE-THROUGH

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WRITE-THROUGH                                                         |
|                                                                         |
|  Data written to cache AND database synchronously.                   |
|  Ensures cache is always consistent with database.                   |
|                                                                         |
|       App                Cache              Database                   |
|        |   SET key,value   |                   |                      |
|        |------------------>|                   |                      |
|        |                   |   Write to DB     |                      |
|        |                   |------------------>|                      |
|        |                   |<------------------|                      |
|        |<------------------|                   |                      |
|        |   Ack (both done) |                   |                      |
|                                                                         |
|  PROS:                                                                 |
|  Y Cache always consistent with DB                                   |
|  Y Subsequent reads are always cache hits                           |
|                                                                         |
|  CONS:                                                                 |
|  X Higher write latency (write to both)                             |
|  X Cache fills with data that may never be read                     |
|                                                                         |
|  BEST FOR:                                                             |
|  * Data that is read immediately after write                        |
|  * When consistency is more important than write speed              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### PATTERN 4: WRITE-BEHIND (Write-Back)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WRITE-BEHIND                                                          |
|                                                                         |
|  Data written to cache immediately.                                   |
|  Cache writes to database asynchronously (later).                    |
|                                                                         |
|       App                Cache              Database                   |
|        |   SET key,value   |                   |                      |
|        |------------------>|                   |                      |
|        |<------------------|                   |                      |
|        |   Ack (immediate) |                   |                      |
|        |                   |                   |                      |
|        |                   | (async, batched)  |                      |
|        |                   |------------------>|                      |
|        |                   |                   |                      |
|                                                                         |
|  PROS:                                                                 |
|  Y Very fast writes (only cache)                                     |
|  Y Can batch writes to database                                      |
|  Y Reduces database load                                             |
|                                                                         |
|  CONS:                                                                 |
|  X Risk of data loss if cache fails before DB write                 |
|  X Eventual consistency (DB may be stale temporarily)               |
|  X More complex recovery                                             |
|                                                                         |
|  BEST FOR:                                                             |
|  * High write throughput requirements                                |
|  * When some data loss is acceptable                                 |
|  * Analytics, logging, counters                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.3: CACHE EVICTION POLICIES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY EVICTION?                                                         |
|                                                                         |
|  Cache has limited memory.                                            |
|  When full, must remove something to add new data.                   |
|  Eviction policy decides what to remove.                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  LRU (LEAST RECENTLY USED)                                            |
|  =========================                                              |
|                                                                         |
|  Evict the item that was accessed longest ago.                       |
|                                                                         |
|  Access order: A, B, C, D, E                                          |
|  Cache (size 4): [E, D, C, B]  (most recent first)                   |
|                                                                         |
|  Access A > Cache full, evict B (least recent)                       |
|  Cache: [A, E, D, C]                                                  |
|                                                                         |
|  IMPLEMENTATION:                                                       |
|  * Doubly linked list + hash map                                     |
|  * O(1) access and eviction                                          |
|                                                                         |
|  class LRUCache:                                                       |
|      def __init__(self, capacity):                                    |
|          self.capacity = capacity                                      |
|          self.cache = OrderedDict()                                   |
|                                                                         |
|      def get(self, key):                                               |
|          if key not in self.cache:                                    |
|              return None                                               |
|          self.cache.move_to_end(key)  # Mark as recently used       |
|          return self.cache[key]                                       |
|                                                                         |
|      def put(self, key, value):                                       |
|          if key in self.cache:                                        |
|              self.cache.move_to_end(key)                              |
|          self.cache[key] = value                                      |
|          if len(self.cache) > self.capacity:                         |
|              self.cache.popitem(last=False)  # Remove oldest         |
|                                                                         |
|  PROS: Simple, works well for temporal locality                      |
|  CONS: One-time accesses can pollute cache                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  LFU (LEAST FREQUENTLY USED)                                          |
|  ============================                                           |
|                                                                         |
|  Evict the item accessed least often.                                |
|                                                                         |
|  Access counts:                                                        |
|  A: 100 times, B: 50 times, C: 10 times, D: 5 times                 |
|                                                                         |
|  Need space? Evict D (lowest count)                                  |
|                                                                         |
|  PROS: Better for skewed access patterns                             |
|  CONS: Older popular items may stay forever                          |
|        New items evicted before proving popularity                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  FIFO (FIRST IN, FIRST OUT)                                           |
|  ===========================                                            |
|                                                                         |
|  Evict oldest item (by insertion time).                              |
|                                                                         |
|  PROS: Simple                                                         |
|  CONS: Ignores access patterns, often poor hit rate                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  TTL (TIME TO LIVE)                                                    |
|  ===================                                                    |
|                                                                         |
|  Items expire after a set time.                                       |
|  Not really eviction, but related.                                   |
|                                                                         |
|  cache.set("user:123", user_data, ttl=3600)  # Expires in 1 hour    |
|                                                                         |
|  Used in combination with other policies.                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  COMPARISON                                                            |
|                                                                         |
|  +-----------+----------------------------------------------------+   |
|  | Policy    | Best For                                          |   |
|  +-----------+----------------------------------------------------+   |
|  | LRU       | General purpose, good default                     |   |
|  | LFU       | Highly skewed access (few very hot items)        |   |
|  | FIFO      | Simple queues, streaming data                     |   |
|  | Random    | When access pattern is truly random               |   |
|  | TTL       | Time-sensitive data, sessions                     |   |
|  +-----------+----------------------------------------------------+   |
|                                                                         |
|  REDIS EVICTION POLICIES                                               |
|  -------------------------                                              |
|  * volatile-lru: LRU among keys with TTL                            |
|  * allkeys-lru: LRU among all keys                                  |
|  * volatile-lfu: LFU among keys with TTL                            |
|  * allkeys-lfu: LFU among all keys                                  |
|  * volatile-random: Random among keys with TTL                      |
|  * allkeys-random: Random among all keys                            |
|  * volatile-ttl: Evict keys with shortest TTL                       |
|  * noeviction: Return error when memory full                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.4: CACHE INVALIDATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  "There are only two hard things in Computer Science:                 |
|   cache invalidation and naming things."                              |
|                                  — Phil Karlton                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  THE PROBLEM                                                           |
|                                                                         |
|  When source data changes, cache becomes stale.                      |
|  Must update or delete cached copy.                                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  STRATEGY 1: TTL-BASED EXPIRATION                                     |
|  ===============================                                        |
|                                                                         |
|  Set expiration time on cached data.                                 |
|  After TTL, data automatically deleted.                              |
|                                                                         |
|  cache.set("product:123", product, ttl=300)  # 5 minutes            |
|                                                                         |
|  PROS: Simple, automatic                                              |
|  CONS: Data may be stale until TTL expires                           |
|        TTL too short = low hit rate                                  |
|        TTL too long = stale data                                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  STRATEGY 2: EXPLICIT INVALIDATION                                    |
|  ================================                                       |
|                                                                         |
|  When data changes, explicitly delete cache.                         |
|                                                                         |
|  def update_product(product_id, data):                               |
|      db.update("products", product_id, data)                         |
|      cache.delete(f"product:{product_id}")                           |
|                                                                         |
|  PROS: Immediate consistency                                          |
|  CONS: Must track all cache keys affected by a change               |
|        Complex for derived data (aggregations)                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  STRATEGY 3: WRITE-THROUGH INVALIDATION                               |
|  =======================================                                |
|                                                                         |
|  On write, update cache AND database.                                |
|                                                                         |
|  def update_product(product_id, data):                               |
|      db.update("products", product_id, data)                         |
|      updated = db.get("products", product_id)                        |
|      cache.set(f"product:{product_id}", updated, ttl=300)           |
|                                                                         |
|  PROS: Cache immediately consistent                                   |
|  CONS: Extra write latency                                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  STRATEGY 4: EVENT-BASED INVALIDATION                                 |
|  ====================================                                   |
|                                                                         |
|  Database publishes change events.                                   |
|  Cache service subscribes and invalidates.                           |
|                                                                         |
|  Database --> Kafka/CDC --> Cache Invalidator --> Cache              |
|                                                                         |
|  PROS: Decoupled, scales well                                        |
|  CONS: Eventual consistency, more infrastructure                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CACHE INVALIDATION CHALLENGES                                        |
|                                                                         |
|  1. DISTRIBUTED CACHES                                                 |
|     * Multiple cache nodes                                           |
|     * Must invalidate on all nodes                                   |
|     * Use cache invalidation channel (Redis Pub/Sub)                |
|                                                                         |
|  2. DERIVED DATA                                                       |
|     * Product changes > category listing stale                      |
|     * User changes > team membership stale                          |
|     * Track dependencies, cascade invalidations                     |
|                                                                         |
|  3. RACE CONDITIONS                                                    |
|     * Read sees old data, caches it                                 |
|     * Write invalidates, but read's cache is newer                  |
|     * Solution: Version numbers, cache locks                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CACHING FUNDAMENTALS - KEY TAKEAWAYS                                 |
|                                                                         |
|  WHY CACHE?                                                            |
|  ----------                                                            |
|  * Speed: <1ms vs 50-100ms database                                  |
|  * Scale: Reduce database load                                       |
|  * Works due to locality of reference                                |
|                                                                         |
|  ACCESS PATTERNS                                                       |
|  ---------------                                                       |
|  * Cache-aside: App manages cache (most common)                      |
|  * Read-through: Cache loads on miss                                 |
|  * Write-through: Sync write to both                                 |
|  * Write-behind: Async write to DB                                   |
|                                                                         |
|  EVICTION POLICIES                                                     |
|  -----------------                                                     |
|  * LRU: Evict least recently used (default choice)                  |
|  * LFU: Evict least frequently used                                 |
|  * TTL: Time-based expiration                                        |
|                                                                         |
|  INVALIDATION                                                          |
|  ------------                                                          |
|  * TTL: Automatic, eventual consistency                              |
|  * Explicit: Delete on write, immediate                              |
|  * Event-based: CDC/Pub-Sub, scalable                               |
|                                                                         |
|  INTERVIEW TIP                                                         |
|  -------------                                                         |
|  Know cache-aside pattern well.                                      |
|  Explain LRU implementation (linked list + hashmap).                |
|  Discuss invalidation trade-offs.                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 1

