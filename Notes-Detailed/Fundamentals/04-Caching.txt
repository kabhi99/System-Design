================================================================================
         CHAPTER 4: CACHING
         The Art of Storing Data Closer to Where It's Needed
================================================================================

Caching is perhaps the single most impactful optimization technique in
distributed systems. It can reduce latency from milliseconds to microseconds,
cut database load by 90%, and enable systems to handle massive scale.


================================================================================
SECTION 4.1: WHAT IS CACHING?
================================================================================

THE FUNDAMENTAL PROBLEM
───────────────────────

Every time a user requests data, the system must:

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  WITHOUT CACHING                                                       │
    │                                                                         │
    │  User Request                                                          │
    │       │                                                                │
    │       ▼                                                                │
    │  Application Server                                                    │
    │       │                                                                │
    │       ▼                                                                │
    │  Database ──────► Query Processing ──────► Disk I/O                   │
    │       │              (CPU work)          (slowest!)                    │
    │       ▼                                                                │
    │  Return Data                                                           │
    │                                                                         │
    │  Time: 50-200ms per request                                           │
    │  Database handles: Every single request                                │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  WITH CACHING                                                          │
    │                                                                         │
    │  User Request                                                          │
    │       │                                                                │
    │       ▼                                                                │
    │  Application Server                                                    │
    │       │                                                                │
    │       ├──► Cache ──► HIT? ──► Return immediately (1-5ms)             │
    │       │                                                                │
    │       └──► MISS? ──► Database ──► Store in Cache ──► Return          │
    │                                                                         │
    │  Time: 1-5ms (cache hit), 50-200ms (cache miss)                       │
    │  Database handles: Only cache misses (~10% of requests)              │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


THE CACHE HIERARCHY
───────────────────

Data can be cached at multiple levels, each with different latency:

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  THE CACHE HIERARCHY (Fastest → Slowest)                              │
    │                                                                         │
    │  Level                   Latency        Size         Location          │
    │  ─────                   ───────        ────         ────────          │
    │  CPU L1 Cache            0.5 ns         64 KB        On-chip           │
    │  CPU L2 Cache            7 ns           256 KB       On-chip           │
    │  CPU L3 Cache            20 ns          8-50 MB      On-chip           │
    │  Main Memory (RAM)       100 ns         GB-TB        Server RAM        │
    │  In-Process Cache        100 ns         MB-GB        App memory        │
    │  Distributed Cache       0.5-5 ms       GB-TB        Redis/Memcached   │
    │  SSD                     100-150 µs     TB           Local disk        │
    │  HDD                     10 ms          TB           Local disk        │
    │  Database                5-100 ms       TB-PB        Database server   │
    │  Cross-Region            100-300 ms     Unlimited    Remote DC         │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  CACHING LAYERS IN WEB ARCHITECTURE:                                  │
    │                                                                         │
    │  ┌──────────────────────────────────────────────────────────────────┐ │
    │  │                                                                  │ │
    │  │  User Browser                                                    │ │
    │  │      ↓ (cache hit = no request)                                 │ │
    │  │  [1] Browser Cache (Cache-Control headers)                      │ │
    │  │      ↓                                                           │ │
    │  │  [2] CDN Cache (edge servers worldwide)                         │ │
    │  │      ↓                                                           │ │
    │  │  [3] Reverse Proxy Cache (Varnish, Nginx)                       │ │
    │  │      ↓                                                           │ │
    │  │  [4] Application Cache (in-process)                             │ │
    │  │      ↓                                                           │ │
    │  │  [5] Distributed Cache (Redis, Memcached)                       │ │
    │  │      ↓                                                           │ │
    │  │  [6] Database Query Cache                                       │ │
    │  │      ↓                                                           │ │
    │  │  [7] Database Buffer Pool                                       │ │
    │  │      ↓                                                           │ │
    │  │  [8] Disk                                                        │ │
    │  │                                                                  │ │
    │  └──────────────────────────────────────────────────────────────────┘ │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


CACHING TERMINOLOGY
───────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  KEY TERMS                                                             │
    │                                                                         │
    │  CACHE HIT                                                             │
    │  Requested data is found in cache                                     │
    │  Fast path: return immediately                                        │
    │                                                                         │
    │  CACHE MISS                                                            │
    │  Requested data is NOT in cache                                       │
    │  Slow path: fetch from source, optionally cache                       │
    │                                                                         │
    │  HIT RATE (Hit Ratio)                                                  │
    │  Percentage of requests served from cache                             │
    │  Hit Rate = Cache Hits / (Cache Hits + Cache Misses)                 │
    │  Target: 80-99% depending on use case                                │
    │                                                                         │
    │  MISS RATE                                                             │
    │  Miss Rate = 1 - Hit Rate = Cache Misses / Total Requests            │
    │                                                                         │
    │  TTL (Time To Live)                                                    │
    │  How long data stays in cache before expiring                        │
    │                                                                         │
    │  CACHE WARM / COLD                                                     │
    │  Warm: Cache is populated with frequently accessed data              │
    │  Cold: Cache is empty (after restart, new deployment)                │
    │                                                                         │
    │  CACHE WARMING                                                         │
    │  Pre-populating cache with expected data before traffic              │
    │                                                                         │
    │  EVICTION                                                              │
    │  Removing items from cache (TTL expired, cache full)                 │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 4.2: CACHE READING STRATEGIES
================================================================================

CACHE-ASIDE (LAZY LOADING)
──────────────────────────

The most common pattern. Application manages cache directly.

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  CACHE-ASIDE PATTERN                                                   │
    │                                                                         │
    │  READ FLOW:                                                            │
    │                                                                         │
    │  1. App checks cache                                                   │
    │  2. If HIT: return cached data                                        │
    │  3. If MISS: query database, store in cache, return data             │
    │                                                                         │
    │  ┌──────────────────────────────────────────────────────────────────┐ │
    │  │                                                                  │ │
    │  │  Application                                                     │ │
    │  │      │                                                           │ │
    │  │      ├───1───► Cache ───► HIT? ───► Return data                │ │
    │  │      │                      │                                    │ │
    │  │      │                     MISS                                  │ │
    │  │      │                      │                                    │ │
    │  │      │◄──────2──────────────┘                                    │ │
    │  │      │                                                           │ │
    │  │      ├───3───► Database ───► Get data                          │ │
    │  │      │                          │                                │ │
    │  │      │◄─────────────────────────┘                                │ │
    │  │      │                                                           │ │
    │  │      ├───4───► Cache ───► Store data                           │ │
    │  │      │                                                           │ │
    │  │      └───5───► Return data to user                             │ │
    │  │                                                                  │ │
    │  └──────────────────────────────────────────────────────────────────┘ │
    │                                                                         │
    │  PSEUDOCODE:                                                           │
    │  ───────────                                                           │
    │  def get_user(user_id):                                               │
    │      # 1. Check cache first                                           │
    │      cache_key = f"user:{user_id}"                                   │
    │      user = cache.get(cache_key)                                      │
    │      if user:                                                          │
    │          return user  # Cache HIT                                     │
    │                                                                         │
    │      # 2. Cache MISS - fetch from database                            │
    │      user = db.query("SELECT * FROM users WHERE id = ?", user_id)    │
    │                                                                         │
    │      # 3. Store in cache for next time                                │
    │      if user:                                                          │
    │          cache.set(cache_key, user, ttl=3600)  # 1 hour TTL         │
    │                                                                         │
    │      return user                                                       │
    │                                                                         │
    │  PROS:                                                                 │
    │  ✓ Only caches data that's actually requested                        │
    │  ✓ Cache failures don't break the system (fallback to DB)           │
    │  ✓ Simple to implement                                                │
    │  ✓ Works with any database                                           │
    │                                                                         │
    │  CONS:                                                                 │
    │  ✗ First request is always slow (cache miss)                         │
    │  ✗ Stale data possible (until TTL expires)                           │
    │  ✗ Cache stampede possible (discussed later)                         │
    │  ✗ Application must handle cache logic                               │
    │                                                                         │
    │  USE WHEN: General purpose caching, read-heavy workloads             │
    │                                                                         │
    │  USED BY: Most applications (Twitter, Facebook, Instagram)           │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


READ-THROUGH CACHE
──────────────────

Cache is responsible for loading data from database.

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  READ-THROUGH PATTERN                                                  │
    │                                                                         │
    │  ┌──────────────────────────────────────────────────────────────────┐ │
    │  │                                                                  │ │
    │  │  Application                                                     │ │
    │  │      │                                                           │ │
    │  │      ├───1───► Cache                                            │ │
    │  │      │            │                                              │ │
    │  │      │            ├───► HIT? ───► Return data ──────────────┐  │ │
    │  │      │            │                                          │  │ │
    │  │      │            └───► MISS? ───► Load from Database       │  │ │
    │  │      │                               │                       │  │ │
    │  │      │                               ▼                       │  │ │
    │  │      │                         Store in cache              │  │ │
    │  │      │                               │                       │  │ │
    │  │      │◄──────────────────────────────┴───────────────────────┘  │ │
    │  │                                                                  │ │
    │  └──────────────────────────────────────────────────────────────────┘ │
    │                                                                         │
    │  DIFFERENCE FROM CACHE-ASIDE:                                         │
    │  • Application only talks to cache                                    │
    │  • Cache handles database communication internally                   │
    │  • Application code is simpler                                       │
    │                                                                         │
    │  PROS:                                                                 │
    │  ✓ Simpler application code                                          │
    │  ✓ Consistent data loading logic (in cache library)                 │
    │  ✓ Cache handles complexity                                          │
    │                                                                         │
    │  CONS:                                                                 │
    │  ✗ Cache must know how to load data (coupled to schema)             │
    │  ✗ First request still slow                                          │
    │  ✗ More complex cache implementation                                 │
    │  ✗ Less control over loading behavior                               │
    │                                                                         │
    │  IMPLEMENTATIONS:                                                      │
    │  • Hibernate L2 Cache                                                │
    │  • AWS DAX (DynamoDB Accelerator)                                   │
    │  • NCache, Apache Ignite                                             │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 4.3: CACHE WRITING STRATEGIES
================================================================================

WRITE-THROUGH
─────────────

Write to cache AND database synchronously.

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  WRITE-THROUGH PATTERN                                                 │
    │                                                                         │
    │  ┌──────────────────────────────────────────────────────────────────┐ │
    │  │                                                                  │ │
    │  │  Application                                                     │ │
    │  │      │                                                           │ │
    │  │      ├───Write───► Cache                                        │ │
    │  │      │               │                                          │ │
    │  │      │               ├───Write───► Database                    │ │
    │  │      │               │                 │                        │ │
    │  │      │               │◄────────────────┘                        │ │
    │  │      │               │                                          │ │
    │  │      │◄──────────────┘                                          │ │
    │  │      │        (wait for both to complete)                       │ │
    │  │                                                                  │ │
    │  └──────────────────────────────────────────────────────────────────┘ │
    │                                                                         │
    │  PSEUDOCODE:                                                           │
    │  def update_user(user_id, data):                                      │
    │      # Write to database first                                        │
    │      db.update("UPDATE users SET ... WHERE id = ?", user_id)         │
    │                                                                         │
    │      # Then update cache                                              │
    │      cache.set(f"user:{user_id}", data, ttl=3600)                   │
    │                                                                         │
    │      return data                                                       │
    │                                                                         │
    │  PROS:                                                                 │
    │  ✓ Cache and database always consistent                              │
    │  ✓ No stale data                                                     │
    │  ✓ Read-after-write consistency                                      │
    │  ✓ Simple mental model                                               │
    │                                                                         │
    │  CONS:                                                                 │
    │  ✗ Higher write latency (must wait for both)                         │
    │  ✗ If database fails, write fails                                    │
    │  ✗ May cache data that's never read                                  │
    │  ✗ Write amplification (every write hits both)                      │
    │                                                                         │
    │  USE WHEN: Data consistency is critical, reads are frequent          │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


WRITE-BEHIND (WRITE-BACK)
─────────────────────────

Write to cache immediately, database asynchronously.

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  WRITE-BEHIND PATTERN                                                  │
    │                                                                         │
    │  ┌──────────────────────────────────────────────────────────────────┐ │
    │  │                                                                  │ │
    │  │  Application                                                     │ │
    │  │      │                                                           │ │
    │  │      ├───Write───► Cache ───► Return immediately (fast!)       │ │
    │  │      │               │                                           │ │
    │  │      │               └──► [Async Queue]                         │ │
    │  │      │                        │                                  │ │
    │  │      │                        ▼ (batched, delayed)              │ │
    │  │      │                     Database                             │ │
    │  │                                                                  │ │
    │  └──────────────────────────────────────────────────────────────────┘ │
    │                                                                         │
    │  HOW IT WORKS:                                                         │
    │  1. Write to cache, return success                                   │
    │  2. Cache queues write for database                                  │
    │  3. Background process flushes to database                          │
    │     (batched, with retries)                                          │
    │                                                                         │
    │  PROS:                                                                 │
    │  ✓ Very fast writes (no database wait)                               │
    │  ✓ Can batch writes to database (efficiency)                        │
    │  ✓ Absorbs write spikes                                              │
    │  ✓ Reduces database load                                             │
    │                                                                         │
    │  CONS:                                                                 │
    │  ✗ Risk of data loss if cache fails before DB write                  │
    │  ✗ Complex failure handling and recovery                             │
    │  ✗ Eventual consistency (database lags behind)                      │
    │  ✗ Complex to implement correctly                                    │
    │                                                                         │
    │  USE WHEN:                                                             │
    │  • Write performance is critical                                     │
    │  • Some data loss acceptable                                         │
    │  • High write throughput needed                                      │
    │                                                                         │
    │  EXAMPLES:                                                             │
    │  • Write-behind SSDs (OS page cache)                                 │
    │  • Database buffer pools                                             │
    │  • Redis with RDB persistence                                        │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


WRITE-AROUND
────────────

Write only to database, let cache expire naturally.

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  WRITE-AROUND PATTERN                                                  │
    │                                                                         │
    │  ┌──────────────────────────────────────────────────────────────────┐ │
    │  │                                                                  │ │
    │  │  Application                                                     │ │
    │  │      │                                                           │ │
    │  │      ├───Write───► Database (only)                              │ │
    │  │      │                                                           │ │
    │  │      │   Cache NOT updated (still has old data)                │ │
    │  │      │   Will serve stale until TTL expires                    │ │
    │  │      │   OR we invalidate the cache                            │ │
    │  │                                                                  │ │
    │  └──────────────────────────────────────────────────────────────────┘ │
    │                                                                         │
    │  TWO VARIANTS:                                                         │
    │                                                                         │
    │  1. WAIT FOR TTL (Simple, stale data)                                │
    │  ───────────────────────────────────                                    │
    │  def update_user(user_id, data):                                      │
    │      db.update("UPDATE users SET ...", user_id)                      │
    │      # Don't touch cache - let TTL handle it                         │
    │                                                                         │
    │  2. INVALIDATE ON WRITE (Recommended)                                │
    │  ──────────────────────────────────────                                 │
    │  def update_user(user_id, data):                                      │
    │      db.update("UPDATE users SET ...", user_id)                      │
    │      cache.delete(f"user:{user_id}")  # Invalidate                  │
    │      # Next read will reload from DB                                 │
    │                                                                         │
    │  PROS:                                                                 │
    │  ✓ Simple write path                                                 │
    │  ✓ Database is source of truth                                       │
    │  ✓ Avoids caching data that's never read                            │
    │  ✓ Good for write-heavy, read-rarely data                           │
    │                                                                         │
    │  CONS:                                                                 │
    │  ✗ Stale reads until invalidation or TTL                            │
    │  ✗ Read-after-write may return old data                              │
    │                                                                         │
    │  USE WHEN:                                                             │
    │  • Data is written frequently, read rarely                           │
    │  • Brief staleness is acceptable                                     │
    │  • Combined with cache-aside for reads                              │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


STRATEGY COMPARISON
───────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  CACHE WRITE STRATEGY COMPARISON                                      │
    │                                                                         │
    │  ┌────────────────┬────────────┬────────────┬────────────────────────┐│
    │  │ Strategy       │ Write      │ Consistency│ Use Case              ││
    │  │                │ Latency    │            │                        ││
    │  ├────────────────┼────────────┼────────────┼────────────────────────┤│
    │  │ Write-through  │ High       │ Strong     │ Critical data,        ││
    │  │                │            │            │ frequent reads        ││
    │  ├────────────────┼────────────┼────────────┼────────────────────────┤│
    │  │ Write-behind   │ Low        │ Eventual   │ High throughput,      ││
    │  │                │            │            │ loss acceptable       ││
    │  ├────────────────┼────────────┼────────────┼────────────────────────┤│
    │  │ Write-around   │ Medium     │ Eventual   │ Write-heavy,          ││
    │  │ + invalidate   │            │ (brief)    │ read-sometimes        ││
    │  └────────────────┴────────────┴────────────┴────────────────────────┘│
    │                                                                         │
    │  MOST COMMON COMBINATION:                                              │
    │  • Cache-aside for reads                                              │
    │  • Write-around with invalidation for writes                         │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 4.4: CACHE INVALIDATION
================================================================================

"There are only two hard things in Computer Science: cache invalidation
and naming things." - Phil Karlton

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  CACHE INVALIDATION STRATEGIES                                        │
    │                                                                         │
    │  1. TIME-TO-LIVE (TTL)                                                 │
    │  ─────────────────────                                                  │
    │  Data expires after a set time.                                       │
    │                                                                         │
    │  cache.set("user:123", user_data, ttl=3600)  # Expires in 1 hour    │
    │                                                                         │
    │  CHOOSING TTL:                                                         │
    │  ┌────────────────────────────┬────────────────────────────────────┐ │
    │  │ Data Type                  │ Suggested TTL                      │ │
    │  ├────────────────────────────┼────────────────────────────────────┤ │
    │  │ Session data               │ 30 min - 24 hours                  │ │
    │  │ User profile               │ 1 - 24 hours                       │ │
    │  │ Product details            │ 5 min - 1 hour                     │ │
    │  │ Stock prices               │ 1 - 60 seconds                     │ │
    │  │ Configuration              │ 5 min - 1 hour                     │ │
    │  │ Static content             │ Days to weeks                      │ │
    │  │ Search results             │ 1 - 5 minutes                      │ │
    │  │ Feed/timeline              │ 30 seconds - 5 minutes             │ │
    │  └────────────────────────────┴────────────────────────────────────┘ │
    │                                                                         │
    │  PROS: Simple, automatic cleanup                                      │
    │  CONS: Stale data during TTL window, fixed staleness                 │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  2. EVENT-BASED INVALIDATION                                          │
    │  ───────────────────────────                                            │
    │  Invalidate cache when data changes.                                  │
    │                                                                         │
    │  def update_user(user_id, new_data):                                  │
    │      # Update database                                                │
    │      db.update("UPDATE users SET ...", user_id)                      │
    │                                                                         │
    │      # Invalidate cache                                               │
    │      cache.delete(f"user:{user_id}")                                 │
    │                                                                         │
    │      # Publish event for other services                               │
    │      event_bus.publish("user.updated", {"user_id": user_id})        │
    │                                                                         │
    │  PROS: Immediate consistency, precise invalidation                   │
    │  CONS: Complex, must track all cache keys affected by change        │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  3. VERSIONING                                                         │
    │  ────────────                                                           │
    │  Include version in cache key.                                        │
    │                                                                         │
    │  # Store version in database or separate key                         │
    │  version = get_user_version(user_id)  # e.g., 7                     │
    │  cache_key = f"user:{user_id}:v{version}"                           │
    │                                                                         │
    │  # On update, increment version                                       │
    │  def update_user(user_id, data):                                      │
    │      db.update(user_id, data)                                        │
    │      increment_user_version(user_id)  # Now version 8               │
    │      # Old cache key (v7) becomes orphaned                          │
    │      # New reads use v8 key (cache miss → reload)                  │
    │                                                                         │
    │  PROS: No explicit invalidation, atomic updates                      │
    │  CONS: Orphaned data (cleaned by TTL), version storage overhead     │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  4. PUBLISH-SUBSCRIBE INVALIDATION                                    │
    │  ─────────────────────────────────                                      │
    │  Broadcast invalidation to all cache instances.                      │
    │                                                                         │
    │  ┌────────────────────────────────────────────────────────────────┐  │
    │  │  Service A updates user                                        │  │
    │  │       │                                                         │  │
    │  │       ├──► Update Database                                     │  │
    │  │       │                                                         │  │
    │  │       └──► Publish: "INVALIDATE user:123"                     │  │
    │  │                          │                                      │  │
    │  │              ┌───────────┼───────────┐                         │  │
    │  │              ▼           ▼           ▼                         │  │
    │  │           Cache 1    Cache 2    Cache 3                       │  │
    │  │           (delete)   (delete)   (delete)                      │  │
    │  └────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  Used in: Multi-server deployments, Redis Pub/Sub                    │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 4.5: CACHE PROBLEMS AND SOLUTIONS
================================================================================

CACHE STAMPEDE (THUNDERING HERD)
────────────────────────────────

When cached data expires, all requests hit the database simultaneously.

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  THE STAMPEDE PROBLEM                                                  │
    │                                                                         │
    │  Timeline:                                                             │
    │  ─────────────────────────────────────────────────────────────────────│
    │  Time 0:    Cache has "popular_item", serving 10,000 RPS             │
    │  Time 3600: TTL expires, cache entry removed                          │
    │  Time 3600.001: 1000 requests arrive in next 100ms                   │
    │             → All 1000 check cache → MISS                             │
    │             → All 1000 query database simultaneously                 │
    │             → DATABASE OVERWHELMED!                                   │
    │                                                                         │
    │  ┌────────────────────────────────────────────────────────────────┐   │
    │  │                     Cache Miss!                                │   │
    │  │                          │                                     │   │
    │  │     ┌────────────────────┼────────────────────┐                │   │
    │  │     │                    │                    │                │   │
    │  │     ▼                    ▼                    ▼                │   │
    │  │  Request 1           Request 2          Request 1000          │   │
    │  │     │                    │                    │                │   │
    │  │     └────────────────────┼────────────────────┘                │   │
    │  │                          ▼                                     │   │
    │  │                     Database                                   │   │
    │  │                    💥 OVERLOAD 💥                               │   │
    │  └────────────────────────────────────────────────────────────────┘   │
    │                                                                         │
    │  SOLUTIONS:                                                            │
    │                                                                         │
    │  SOLUTION 1: LOCKING (Single flight)                                 │
    │  ─────────────────────────────────                                      │
    │  Only one request fetches from database, others wait.                 │
    │                                                                         │
    │  def get_data_with_lock(key):                                         │
    │      data = cache.get(key)                                            │
    │      if data:                                                          │
    │          return data                                                   │
    │                                                                         │
    │      lock_key = f"lock:{key}"                                         │
    │      if cache.setnx(lock_key, "1", ttl=10):  # Got the lock         │
    │          try:                                                          │
    │              data = database.query(key)                               │
    │              cache.set(key, data, ttl=3600)                          │
    │          finally:                                                      │
    │              cache.delete(lock_key)                                   │
    │          return data                                                   │
    │      else:                                                             │
    │          # Wait and retry                                             │
    │          time.sleep(0.05)                                             │
    │          return get_data_with_lock(key)                               │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  SOLUTION 2: STAGGERED TTL (Jitter)                                  │
    │  ───────────────────────────────────                                    │
    │  Add random jitter to TTL so entries don't expire at same time.      │
    │                                                                         │
    │  import random                                                         │
    │  base_ttl = 3600                                                       │
    │  jitter = random.randint(-300, 300)  # ±5 minutes                    │
    │  ttl = base_ttl + jitter                                              │
    │  cache.set(key, data, ttl=ttl)                                        │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  SOLUTION 3: BACKGROUND REFRESH (Proactive)                          │
    │  ─────────────────────────────────────────────                          │
    │  Refresh cache BEFORE it expires.                                     │
    │                                                                         │
    │  def get_data_with_early_refresh(key):                                │
    │      data, ttl_remaining = cache.get_with_ttl(key)                   │
    │                                                                         │
    │      if data:                                                          │
    │          if ttl_remaining < 300:  # Less than 5 min left            │
    │              # Trigger async refresh                                  │
    │              async_refresh(key)                                       │
    │          return data                                                   │
    │                                                                         │
    │      # Cache miss - fetch synchronously                              │
    │      return fetch_and_cache(key)                                      │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  SOLUTION 4: PROBABILISTIC EARLY EXPIRATION (XFetch)                 │
    │  ───────────────────────────────────────────────────────               │
    │  Randomly refresh before expiry based on remaining TTL               │
    │                                                                         │
    │  # As TTL approaches, probability of refresh increases               │
    │  # Formula: refresh if random() < exp(-ttl_remaining / beta)        │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


CACHE PENETRATION
─────────────────

Queries for non-existent data bypass cache and hit database.

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  CACHE PENETRATION PROBLEM                                            │
    │                                                                         │
    │  Attacker or bug queries: GET /user/99999999 (doesn't exist)         │
    │                                                                         │
    │  1. Check cache → MISS (user doesn't exist in cache)                 │
    │  2. Query database → No results                                       │
    │  3. Nothing to cache (null result)                                   │
    │  4. Next request → Same cycle repeats!                                │
    │                                                                         │
    │  Attack: Send 10,000 requests for random non-existent IDs            │
    │  → All 10,000 hit database                                            │
    │  → DATABASE DOS ATTACK!                                               │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  SOLUTION 1: CACHE NULL RESULTS                                       │
    │  ──────────────────────────────                                         │
    │                                                                         │
    │  def get_user(user_id):                                               │
    │      cache_key = f"user:{user_id}"                                   │
    │      cached = cache.get(cache_key)                                    │
    │                                                                         │
    │      if cached == "NULL":                                             │
    │          return None  # Known to not exist                           │
    │      if cached:                                                        │
    │          return cached                                                 │
    │                                                                         │
    │      user = db.get_user(user_id)                                      │
    │      if user is None:                                                 │
    │          # Cache the "not found" with short TTL                      │
    │          cache.set(cache_key, "NULL", ttl=300)  # 5 minutes         │
    │      else:                                                             │
    │          cache.set(cache_key, user, ttl=3600)                        │
    │      return user                                                       │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  SOLUTION 2: BLOOM FILTER                                             │
    │  ────────────────────────────                                           │
    │  Probabilistic structure: "definitely not exists" or "maybe exists"  │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐ │
    │  │  Bloom Filter: Very memory efficient (1GB = billions of items) │ │
    │  │                                                                 │ │
    │  │  Properties:                                                    │ │
    │  │  • NO false negatives: If it says "not exists", 100% sure     │ │
    │  │  • Possible false positives: May say "exists" when it doesn't │ │
    │  │  • Cannot delete items (use Cuckoo filter if needed)          │ │
    │  └─────────────────────────────────────────────────────────────────┘ │
    │                                                                         │
    │  def get_user(user_id):                                               │
    │      if not bloom_filter.might_contain(user_id):                     │
    │          return None  # Definitely doesn't exist                     │
    │                                                                         │
    │      # Might exist, check cache/database                              │
    │      return cache_aside_lookup(user_id)                               │
    │                                                                         │
    │  USED BY: Google BigTable, Apache HBase, Medium                      │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


CACHE AVALANCHE
───────────────

Mass expiration causing system-wide failure.

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  CACHE AVALANCHE                                                       │
    │                                                                         │
    │  SCENARIO:                                                             │
    │  1. Cache server restarts (cold cache)                               │
    │  2. OR many keys expire simultaneously (same TTL at startup)         │
    │  3. Massive spike in database load                                   │
    │  4. Database overwhelmed, starts failing                             │
    │  5. All requests fail, system crashes                                │
    │                                                                         │
    │  SOLUTIONS:                                                            │
    │                                                                         │
    │  1. CACHE WARMING                                                     │
    │     Pre-load cache before accepting traffic                          │
    │     Script: Load top 10,000 frequently accessed items                │
    │                                                                         │
    │  2. STAGGERED TTL (Different expiration times)                       │
    │     Don't set all items with same TTL                                │
    │                                                                         │
    │  3. CIRCUIT BREAKER                                                   │
    │     If DB is overloaded, fail fast instead of queuing               │
    │                                                                         │
    │  4. RATE LIMITING                                                     │
    │     Limit concurrent DB requests during cold start                   │
    │                                                                         │
    │  5. CACHE HIGH AVAILABILITY                                           │
    │     Redis Cluster, multiple replicas                                 │
    │     Avoid single point of failure                                    │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


HOT KEY PROBLEM
───────────────

One key is accessed much more than others.

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  HOT KEY PROBLEM                                                       │
    │                                                                         │
    │  Scenario: Celebrity with 10M followers posts something               │
    │  Key: "post:celebrity:123"                                            │
    │                                                                         │
    │  All 10M followers request the same key!                              │
    │  → Single cache node handles all requests                             │
    │  → Network/CPU overwhelmed on that node                               │
    │  → Single shard becomes bottleneck                                   │
    │                                                                         │
    │  SOLUTIONS:                                                            │
    │                                                                         │
    │  SOLUTION 1: KEY REPLICATION (Hot key sharding)                      │
    │  ─────────────────────────────────────────────────                      │
    │  Store same data under multiple keys.                                 │
    │                                                                         │
    │  # Instead of one key, create N replica keys                         │
    │  NUM_REPLICAS = 10                                                    │
    │                                                                         │
    │  def set_hot_key(key, value, ttl):                                   │
    │      for i in range(NUM_REPLICAS):                                   │
    │          cache.set(f"{key}:{i}", value, ttl)                        │
    │                                                                         │
    │  def get_hot_key(key):                                                │
    │      replica_id = random.randint(0, NUM_REPLICAS - 1)                │
    │      return cache.get(f"{key}:{replica_id}")                         │
    │                                                                         │
    │  Traffic now distributed across 10 cache nodes!                      │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  SOLUTION 2: LOCAL CACHE + DISTRIBUTED CACHE                          │
    │  ─────────────────────────────────────────────                          │
    │  Cache hot data in application memory.                                │
    │                                                                         │
    │  ┌────────────────────────────────────────────────────────────────┐   │
    │  │  Request                                                       │   │
    │  │     │                                                          │   │
    │  │     ├──► Local Cache (in-process, 100ns)                      │   │
    │  │     │       │                                                  │   │
    │  │     │       └──► MISS ──► Distributed Cache (Redis, 1ms)     │   │
    │  │     │                          │                               │   │
    │  │     │                          └──► MISS ──► Database         │   │
    │  └────────────────────────────────────────────────────────────────┘   │
    │                                                                         │
    │  Hot keys stay in local cache of every app server.                   │
    │  Reduces load on distributed cache.                                   │
    │                                                                         │
    │  IMPLEMENTATION:                                                       │
    │  • Caffeine (Java)                                                   │
    │  • python-lru-cache                                                  │
    │  • node-lru-cache                                                    │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  SOLUTION 3: HOT KEY DETECTION                                        │
    │  ──────────────────────────────                                         │
    │  Automatically detect and handle hot keys                            │
    │                                                                         │
    │  • Track access frequency                                            │
    │  • When key exceeds threshold, replicate automatically              │
    │  • Redis Hot Key detection (redis-cli --hotkeys)                    │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 4.6: CACHE EVICTION POLICIES
================================================================================

When cache is full, which items do we remove?

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  CACHE EVICTION POLICIES                                              │
    │                                                                         │
    │  LRU - LEAST RECENTLY USED (Most common)                              │
    │  ─────────────────────────────────────────                              │
    │  Evict items that haven't been accessed recently.                     │
    │                                                                         │
    │  Access pattern: A, B, C, D, A, B, E (cache size = 4)                │
    │                                                                         │
    │  A → [A]                                                              │
    │  B → [A, B]                                                           │
    │  C → [A, B, C]                                                        │
    │  D → [A, B, C, D]  (full)                                            │
    │  A → [B, C, D, A]  (A accessed, moved to end)                        │
    │  B → [C, D, A, B]  (B accessed, moved to end)                        │
    │  E → [D, A, B, E]  (C evicted as least recently used)               │
    │                                                                         │
    │  PROS: Good for most workloads, locality-aware                       │
    │  CONS: Scan-resistant issue (one-time scans evict hot items)        │
    │                                                                         │
    │  USED BY: Redis (allkeys-lru), Memcached, CPU caches                 │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  LFU - LEAST FREQUENTLY USED                                          │
    │  ────────────────────────────────                                       │
    │  Evict items accessed least often (lowest count).                    │
    │                                                                         │
    │  Item A: accessed 100 times                                           │
    │  Item B: accessed 2 times   ← Evict this first                       │
    │  Item C: accessed 50 times                                            │
    │                                                                         │
    │  PROS: Better for skewed access (popular items stay)                 │
    │  CONS: New items evicted before proving useful,                     │
    │        Historical popularity beats current popularity               │
    │                                                                         │
    │  SOLUTION: LFU with aging (decay frequency over time)                │
    │  USED BY: Redis 4.0+ (allkeys-lfu), some CDNs                       │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  FIFO - FIRST IN FIRST OUT                                            │
    │  ────────────────────────────                                           │
    │  Evict oldest items regardless of access.                             │
    │                                                                         │
    │  Simple queue: new items at end, evict from front                    │
    │                                                                         │
    │  PROS: Simple, O(1) operations                                       │
    │  CONS: Ignores access patterns completely                            │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  RANDOM                                                                │
    │  ──────                                                                 │
    │  Evict random items.                                                  │
    │                                                                         │
    │  PROS: Surprisingly effective, simple, O(1)                          │
    │  CONS: Can evict hot items                                           │
    │                                                                         │
    │  USED BY: Some CPU caches, simple systems                            │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  TTL-BASED                                                             │
    │  ───────────                                                            │
    │  Evict expired items first.                                           │
    │                                                                         │
    │  Redis volatile-* policies:                                           │
    │  • volatile-lru: LRU among keys with TTL                            │
    │  • volatile-ttl: Shortest remaining TTL                              │
    │  • volatile-random: Random among keys with TTL                       │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  RECOMMENDATIONS:                                                      │
    │  • Default: LRU (works well for most cases)                          │
    │  • Highly skewed access: LFU                                         │
    │  • Simplicity: Random (surprisingly good)                            │
    │  • Redis: allkeys-lru or allkeys-lfu                                 │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 4.7: REDIS DEEP DIVE
================================================================================

Redis is the most popular distributed cache. Know it well.

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  REDIS OVERVIEW                                                        │
    │                                                                         │
    │  • In-memory data structure store                                     │
    │  • Single-threaded (mostly) - no lock contention                     │
    │  • Sub-millisecond latency                                            │
    │  • 100,000+ operations/second per instance                           │
    │  • Rich data structures                                               │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  REDIS DATA STRUCTURES                                                │
    │                                                                         │
    │  STRING                                                                │
    │  ────────                                                               │
    │  Key-value, up to 512MB per value                                    │
    │                                                                         │
    │  SET user:123:name "Alice"                                           │
    │  GET user:123:name                                                    │
    │  INCR page:views              # Atomic increment                     │
    │  SETEX session:abc 3600 "{}"  # Set with TTL                        │
    │                                                                         │
    │  Use: Caching, counters, sessions                                    │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  HASH                                                                  │
    │  ──────                                                                 │
    │  Field-value pairs under one key                                     │
    │                                                                         │
    │  HSET user:123 name "Alice" age 30 city "NYC"                       │
    │  HGET user:123 name                                                  │
    │  HGETALL user:123                                                    │
    │  HINCRBY user:123 age 1                                              │
    │                                                                         │
    │  Use: Object caching, user profiles                                  │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  LIST                                                                  │
    │  ──────                                                                 │
    │  Ordered collection, fast push/pop at ends                           │
    │                                                                         │
    │  LPUSH queue:jobs "job1" "job2"   # Push left                       │
    │  RPOP queue:jobs                   # Pop right                       │
    │  LRANGE queue:jobs 0 10            # Get range                       │
    │  BRPOP queue:jobs 30               # Blocking pop (30s timeout)     │
    │                                                                         │
    │  Use: Message queues, activity feeds, recent items                   │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  SET                                                                   │
    │  ─────                                                                  │
    │  Unordered collection of unique strings                              │
    │                                                                         │
    │  SADD tags:post:123 "tech" "redis" "caching"                        │
    │  SMEMBERS tags:post:123                                              │
    │  SISMEMBER tags:post:123 "redis"    # Check membership              │
    │  SINTER tags:post:123 tags:post:456 # Intersection                  │
    │                                                                         │
    │  Use: Tags, unique visitors, social graph                            │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  SORTED SET (ZSET)                                                    │
    │  ───────────────────                                                    │
    │  Set with score for ordering                                         │
    │                                                                         │
    │  ZADD leaderboard 100 "alice" 200 "bob" 150 "carol"                 │
    │  ZRANGE leaderboard 0 -1 WITHSCORES     # All, lowest first         │
    │  ZREVRANGE leaderboard 0 9 WITHSCORES   # Top 10                    │
    │  ZRANK leaderboard "alice"               # Get rank                  │
    │  ZINCRBY leaderboard 50 "alice"          # Increment score          │
    │                                                                         │
    │  Use: Leaderboards, rate limiting (sliding window), priority queue  │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  ADDITIONAL STRUCTURES                                                 │
    │  ────────────────────────                                               │
    │                                                                         │
    │  HyperLogLog: Cardinality estimation (unique counts)                 │
    │  PFADD visitors:today "user1" "user2" "user1"                       │
    │  PFCOUNT visitors:today  → 2 (approx unique)                        │
    │                                                                         │
    │  Bitmap: Bit operations                                               │
    │  SETBIT user:123:features 7 1   # Set bit 7                         │
    │  BITCOUNT user:123:features     # Count set bits                    │
    │                                                                         │
    │  Stream: Append-only log (like Kafka)                                │
    │  XADD stream:events * field value                                   │
    │  XREAD STREAMS stream:events 0                                       │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


REDIS CLUSTER AND HIGH AVAILABILITY
───────────────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  REDIS HIGH AVAILABILITY OPTIONS                                      │
    │                                                                         │
    │  1. REDIS SENTINEL (HA without sharding)                              │
    │  ─────────────────────────────────────────                              │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │  Sentinel 1    Sentinel 2    Sentinel 3                        │  │
    │  │      │              │              │                           │  │
    │  │      └──────────────┼──────────────┘                           │  │
    │  │                     │ (monitoring)                             │  │
    │  │                     ▼                                          │  │
    │  │  ┌─────────────────────────────────────────────────────────┐  │  │
    │  │  │  Master ◄─── replication ───► Replica 1                │  │  │
    │  │  │                              ▲                          │  │  │
    │  │  │                              └──── Replica 2           │  │  │
    │  │  └─────────────────────────────────────────────────────────┘  │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  • Sentinels monitor master health                                    │
    │  • On master failure, elect new master from replicas                 │
    │  • Provides automatic failover                                       │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  2. REDIS CLUSTER (HA + sharding)                                    │
    │  ──────────────────────────────────                                     │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │   Shard 1         Shard 2         Shard 3                      │  │
    │  │  ┌────────┐      ┌────────┐      ┌────────┐                   │  │
    │  │  │Master 1│      │Master 2│      │Master 3│                   │  │
    │  │  │slots   │      │slots   │      │slots   │                   │  │
    │  │  │0-5460  │      │5461-   │      │10923-  │                   │  │
    │  │  └────────┘      │10922   │      │16383   │                   │  │
    │  │      │           └────────┘      └────────┘                   │  │
    │  │      ▼               │               │                         │  │
    │  │  ┌────────┐      ┌────────┐      ┌────────┐                   │  │
    │  │  │Replica │      │Replica │      │Replica │                   │  │
    │  │  └────────┘      └────────┘      └────────┘                   │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  • Data sharded across masters using hash slots (16384 slots)        │
    │  • Key → slot: CRC16(key) % 16384                                    │
    │  • Each master has replicas for HA                                   │
    │  • Client redirects to correct shard                                 │
    │                                                                         │
    │  HASH TAGS for co-location:                                          │
    │  user:{123}:profile and user:{123}:settings                         │
    │  Both hash to same slot (based on {123})                            │
    │  Allows multi-key operations                                         │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  CLOUD MANAGED OPTIONS                                                │
    │  • AWS ElastiCache (Redis)                                           │
    │  • Azure Cache for Redis                                             │
    │  • Google Cloud Memorystore                                          │
    │  • Redis Enterprise Cloud                                            │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 4.8: CONTENT DELIVERY NETWORKS (CDN)
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  CDN OVERVIEW                                                          │
    │                                                                         │
    │  CDN = Network of edge servers distributed globally                   │
    │  Purpose: Serve content from location closest to user                │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Without CDN:                                                   │  │
    │  │  User in Australia → Request → US Origin Server                │  │
    │  │  Latency: 300ms+                                               │  │
    │  │                                                                 │  │
    │  │  With CDN:                                                      │  │
    │  │  User in Australia → Request → Sydney Edge Server              │  │
    │  │  Latency: 20ms                                                 │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  WHAT TO PUT ON CDN:                                                   │
    │  ✓ Images, videos, audio                                             │
    │  ✓ CSS, JavaScript, fonts                                            │
    │  ✓ HTML (for static sites)                                           │
    │  ✓ API responses (with careful cache headers)                        │
    │  ✓ Downloads, software updates                                       │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  CDN ARCHITECTURE                                                      │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │                     ┌─────────────────┐                        │  │
    │  │                     │  Origin Server  │                        │  │
    │  │                     │  (your server)  │                        │  │
    │  │                     └────────┬────────┘                        │  │
    │  │                              │                                  │  │
    │  │           ┌──────────────────┼──────────────────┐              │  │
    │  │           │                  │                  │              │  │
    │  │           ▼                  ▼                  ▼              │  │
    │  │     ┌──────────┐      ┌──────────┐      ┌──────────┐         │  │
    │  │     │ Edge US  │      │ Edge EU  │      │Edge APAC │         │  │
    │  │     │ (cache)  │      │ (cache)  │      │ (cache)  │         │  │
    │  │     └──────────┘      └──────────┘      └──────────┘         │  │
    │  │           ▲                  ▲                  ▲              │  │
    │  │           │                  │                  │              │  │
    │  │        US Users          EU Users          APAC Users         │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  FLOW:                                                                 │
    │  1. User requests image.jpg                                          │
    │  2. DNS resolves to nearest edge                                     │
    │  3. Edge checks local cache                                          │
    │  4. HIT: Return cached content                                       │
    │  5. MISS: Fetch from origin, cache, return                          │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  CACHE CONTROL HEADERS                                                │
    │                                                                         │
    │  Cache-Control: max-age=31536000, public, immutable                  │
    │  │               │               │       │                            │
    │  │               │               │       └── Don't revalidate        │
    │  │               │               └── CDN can cache                   │
    │  │               └── Cache for 1 year                                │
    │  └── HTTP header                                                      │
    │                                                                         │
    │  COMMON PATTERNS:                                                      │
    │  • Static assets: max-age=31536000, immutable                        │
    │    (Use versioned URLs: app.v123.js)                                 │
    │  • HTML: max-age=0, must-revalidate                                  │
    │    (Always check with origin)                                        │
    │  • API: private, no-store (or short max-age)                        │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  POPULAR CDN PROVIDERS                                                │
    │  • Cloudflare (also WAF, DDoS protection)                           │
    │  • AWS CloudFront                                                    │
    │  • Akamai (oldest, enterprise)                                       │
    │  • Fastly (programmable edge)                                        │
    │  • Google Cloud CDN                                                  │
    │  • Azure CDN                                                         │
    │                                                                         │
    │  NETFLIX: Uses Open Connect (own CDN)                                │
    │  - Deploys servers directly in ISP networks                         │
    │  - Handles 15%+ of global internet traffic                          │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 4.9: BLOOM FILTERS
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  WHAT IS A BLOOM FILTER?                                              │
    │                                                                         │
    │  Space-efficient probabilistic data structure that tells you:         │
    │  • "Definitely NOT in set" (100% accurate)                           │
    │  • "Probably in set" (may have false positives)                      │
    │                                                                         │
    │  NEVER has false negatives - if it says "not in set", it's true!     │
    │                                                                         │
    │  USE CASE IN CACHING:                                                  │
    │  Before hitting database, check Bloom filter:                        │
    │  "Has this user ID ever existed?"                                    │
    │  If NO → Don't query DB (save the trip!)                             │
    │  If YES → Query DB (might exist)                                     │
    │                                                                         │
    │  Perfect for cache penetration prevention!                            │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


HOW BLOOM FILTERS WORK
──────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  STRUCTURE                                                             │
    │                                                                         │
    │  1. Bit array of m bits (all initialized to 0)                       │
    │  2. k different hash functions                                        │
    │                                                                         │
    │  Bit Array (m = 10):                                                   │
    │  ┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐                          │
    │  │ 0 │ 0 │ 0 │ 0 │ 0 │ 0 │ 0 │ 0 │ 0 │ 0 │                          │
    │  └───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘                          │
    │    0   1   2   3   4   5   6   7   8   9                              │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  ADDING AN ELEMENT                                                     │
    │                                                                         │
    │  Add "apple" with k=3 hash functions:                                 │
    │                                                                         │
    │  h1("apple") = 1                                                       │
    │  h2("apple") = 4                                                       │
    │  h3("apple") = 7                                                       │
    │                                                                         │
    │  Set bits 1, 4, 7 to 1:                                               │
    │  ┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐                          │
    │  │ 0 │ 1 │ 0 │ 0 │ 1 │ 0 │ 0 │ 1 │ 0 │ 0 │                          │
    │  └───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘                          │
    │    0   1   2   3   4   5   6   7   8   9                              │
    │        ↑           ↑           ↑                                      │
    │                                                                         │
    │  Add "banana":                                                         │
    │  h1("banana") = 2                                                      │
    │  h2("banana") = 4  (already 1)                                        │
    │  h3("banana") = 9                                                      │
    │                                                                         │
    │  ┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐                          │
    │  │ 0 │ 1 │ 1 │ 0 │ 1 │ 0 │ 0 │ 1 │ 0 │ 1 │                          │
    │  └───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘                          │
    │    0   1   2   3   4   5   6   7   8   9                              │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  CHECKING MEMBERSHIP                                                   │
    │                                                                         │
    │  Check "apple":                                                        │
    │  h1("apple") = 1 → bit[1] = 1 ✓                                      │
    │  h2("apple") = 4 → bit[4] = 1 ✓                                      │
    │  h3("apple") = 7 → bit[7] = 1 ✓                                      │
    │  All bits are 1 → "Probably in set" ✓                                │
    │                                                                         │
    │  Check "cherry":                                                       │
    │  h1("cherry") = 1 → bit[1] = 1 ✓                                     │
    │  h2("cherry") = 5 → bit[5] = 0 ✗                                     │
    │  At least one bit is 0 → "Definitely NOT in set" ✓                   │
    │                                                                         │
    │  Check "grape":                                                        │
    │  h1("grape") = 2 → bit[2] = 1 ✓                                      │
    │  h2("grape") = 4 → bit[4] = 1 ✓                                      │
    │  h3("grape") = 9 → bit[9] = 1 ✓                                      │
    │  All bits are 1 → "Probably in set"                                  │
    │  BUT "grape" was never added! FALSE POSITIVE                         │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  WHY FALSE POSITIVES HAPPEN                                           │
    │                                                                         │
    │  Bits can be set by multiple elements                                │
    │  "grape" bits (2, 4, 9) happened to be set by "apple" and "banana"  │
    │                                                                         │
    │  FALSE POSITIVE RATE depends on:                                      │
    │  • m: Number of bits (more bits = fewer collisions)                  │
    │  • n: Number of elements added                                       │
    │  • k: Number of hash functions                                       │
    │                                                                         │
    │  Formula: (1 - e^(-kn/m))^k                                          │
    │                                                                         │
    │  TYPICAL: 1% false positive rate with ~10 bits per element           │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


BLOOM FILTER SIZING
───────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  SIZING GUIDELINES                                                     │
    │                                                                         │
    │  For n elements and false positive rate p:                           │
    │                                                                         │
    │  Optimal bits (m): m = -n * ln(p) / (ln(2))^2                        │
    │  Optimal hashes (k): k = (m/n) * ln(2)                               │
    │                                                                         │
    │  ┌──────────────────────────────────────────────────────────────────┐ │
    │  │ Elements (n)  │  FP Rate (p) │ Bits (m)     │ Hashes (k)        │ │
    │  ├──────────────────────────────────────────────────────────────────┤ │
    │  │ 1 million     │ 1%           │ 9.6 MB       │ 7                 │ │
    │  │ 1 million     │ 0.1%         │ 14.4 MB      │ 10                │ │
    │  │ 10 million    │ 1%           │ 96 MB        │ 7                 │ │
    │  │ 100 million   │ 1%           │ 960 MB       │ 7                 │ │
    │  └──────────────────────────────────────────────────────────────────┘ │
    │                                                                         │
    │  SPACE COMPARISON:                                                     │
    │  • Storing 1M user IDs (8 bytes each): 8 MB                         │
    │  • Bloom filter for 1M IDs (1% FP): 1.2 MB (85% savings!)           │
    │                                                                         │
    │  For 1 billion IDs:                                                   │
    │  • HashSet: ~8 GB                                                    │
    │  • Bloom filter: ~1.2 GB                                            │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


BLOOM FILTER USE CASES
──────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  REAL-WORLD APPLICATIONS                                              │
    │                                                                         │
    │  1. CACHE PENETRATION PREVENTION                                      │
    │  ─────────────────────────────────                                      │
    │  def get_user(user_id):                                                │
    │      # Check bloom filter first                                       │
    │      if not bloom_filter.might_contain(user_id):                     │
    │          return None  # Definitely doesn't exist, skip DB!          │
    │                                                                         │
    │      # Check cache                                                     │
    │      user = cache.get(user_id)                                       │
    │      if user:                                                          │
    │          return user                                                   │
    │                                                                         │
    │      # Query database (might exist, might not)                       │
    │      user = database.get(user_id)                                    │
    │      if user:                                                          │
    │          cache.set(user_id, user)                                    │
    │      return user                                                       │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  2. AVOIDING EXPENSIVE LOOKUPS                                        │
    │  ─────────────────────────────────                                      │
    │  Google Chrome: Check URL against malware blacklist                  │
    │  • 1M+ malicious URLs                                                 │
    │  • Bloom filter: 1MB in memory                                       │
    │  • If "definitely not malicious" → skip server check                │
    │  • If "maybe malicious" → verify with server                        │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  3. DATABASE QUERY OPTIMIZATION                                       │
    │  ────────────────────────────────                                       │
    │  HBase, Cassandra, RocksDB use Bloom filters:                        │
    │  "Is this key possibly in this SSTable file?"                        │
    │  If NO → skip reading the file entirely                              │
    │  If YES → read and check                                             │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  4. DUPLICATE DETECTION                                                │
    │  ─────────────────────────                                              │
    │  Web crawler: "Have I crawled this URL before?"                      │
    │  Email: "Is this email a duplicate?" (deduplication)                 │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  5. SPELL CHECKERS                                                     │
    │  ──────────────────                                                     │
    │  "Is this word in the dictionary?"                                   │
    │  Use Bloom filter with 500K words                                    │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


BLOOM FILTER VARIANTS
─────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  ADVANCED BLOOM FILTER TYPES                                          │
    │                                                                         │
    │  1. COUNTING BLOOM FILTER                                             │
    │  ──────────────────────────                                             │
    │  Use counters instead of bits → supports deletion                    │
    │                                                                         │
    │  Standard: Can't delete (would affect other elements)                │
    │  Counting: Decrement counters instead of clearing bits               │
    │                                                                         │
    │  Trade-off: 4x more space (4-bit counters vs 1 bit)                 │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  2. SCALABLE BLOOM FILTER                                             │
    │  ──────────────────────────                                             │
    │  Grows dynamically as elements are added                             │
    │                                                                         │
    │  When filter reaches capacity:                                        │
    │  • Create new, larger filter                                         │
    │  • Check all filters on query (union)                                │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  3. CUCKOO FILTER                                                      │
    │  ──────────────────                                                     │
    │  Alternative that supports deletion + better space efficiency        │
    │                                                                         │
    │  Uses fingerprints + cuckoo hashing                                  │
    │  Generally preferred over Counting Bloom Filters                     │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  BLOOM FILTER IMPLEMENTATION (Redis)                                  │
    │                                                                         │
    │  Redis has built-in Bloom filter module:                             │
    │                                                                         │
    │  # Create filter for 1M items, 1% false positive                    │
    │  BF.RESERVE user_ids 0.01 1000000                                    │
    │                                                                         │
    │  # Add elements                                                       │
    │  BF.ADD user_ids "user:123"                                          │
    │  BF.ADD user_ids "user:456"                                          │
    │                                                                         │
    │  # Check existence                                                    │
    │  BF.EXISTS user_ids "user:123"  # Returns 1 (probably exists)       │
    │  BF.EXISTS user_ids "user:999"  # Returns 0 (definitely not)        │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
CHAPTER SUMMARY
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  CACHING - KEY TAKEAWAYS                                              │
    │                                                                         │
    │  READ STRATEGIES                                                       │
    │  ────────────────                                                      │
    │  • Cache-Aside: App manages cache (most common)                      │
    │  • Read-Through: Cache handles DB loading                            │
    │                                                                         │
    │  WRITE STRATEGIES                                                      │
    │  ─────────────────                                                     │
    │  • Write-Through: Sync to cache + DB (consistent)                   │
    │  • Write-Behind: Async DB write (fast but risky)                     │
    │  • Write-Around: Only DB, invalidate cache (common)                 │
    │                                                                         │
    │  INVALIDATION                                                          │
    │  ────────────                                                          │
    │  • TTL: Simple, automatic expiration                                 │
    │  • Event-based: Invalidate on data change                            │
    │  • Versioning: Include version in key                                │
    │                                                                         │
    │  COMMON PROBLEMS                                                       │
    │  ───────────────                                                       │
    │  • Stampede: Lock/stagger TTL/background refresh                     │
    │  • Penetration: Cache nulls/Bloom filter                             │
    │  • Hot keys: Replicate keys/local cache                              │
    │  • Avalanche: Cache warming, staggered TTL                           │
    │                                                                         │
    │  BLOOM FILTER                                                          │
    │  ────────────                                                          │
    │  • Space-efficient probabilistic set membership                      │
    │  • "Definitely not" or "probably yes"                                │
    │  • Perfect for cache penetration prevention                          │
    │  • 1% false positive with ~10 bits per element                       │
    │                                                                         │
    │  EVICTION POLICIES                                                     │
    │  ─────────────────                                                     │
    │  • LRU: Evict least recently used (default choice)                   │
    │  • LFU: Evict least frequently used (skewed access)                  │
    │                                                                         │
    │  REDIS                                                                 │
    │  ─────                                                                 │
    │  • Know data structures: String, Hash, List, Set, Sorted Set        │
    │  • Sentinel for HA, Cluster for HA + sharding                       │
    │  • Use hash tags for key co-location in cluster                     │
    │                                                                         │
    │  CDN                                                                   │
    │  ───                                                                   │
    │  • Static content at edge servers                                    │
    │  • Control with Cache-Control headers                                │
    │  • ~50% of internet traffic goes through CDNs                       │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  INTERVIEW TIPS                                                        │
    │  ──────────────                                                        │
    │                                                                         │
    │  1. Always mention:                                                   │
    │     • TTL strategy                                                   │
    │     • Invalidation approach                                          │
    │     • How to handle cache failures (fallback to DB)                 │
    │                                                                         │
    │  2. Know the numbers:                                                 │
    │     • Redis: 100K+ ops/sec, <1ms latency                            │
    │     • Cache hit rate target: 80-99%                                 │
    │     • CDN: 20ms (edge) vs 300ms (cross-continent)                  │
    │                                                                         │
    │  3. Discuss problems proactively:                                    │
    │     "For hot keys like celebrity posts, we'd replicate..."          │
    │     "To prevent stampede, we'd use locking or early refresh"        │
    │                                                                         │
    │  4. Real-world examples:                                              │
    │     • Twitter: Timelines in Redis                                   │
    │     • Facebook: Memcached (TAO)                                     │
    │     • Instagram: Redis + Memcached                                  │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
                              END OF CHAPTER 4
================================================================================
