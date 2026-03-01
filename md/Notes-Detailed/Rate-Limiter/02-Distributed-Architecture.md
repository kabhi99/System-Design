# RATE LIMITER SYSTEM DESIGN

CHAPTER 2: DISTRIBUTED RATE LIMITER ARCHITECTURE
## TABLE OF CONTENTS
*-----------------*
*1. High-Level Architecture*
*2. Where to Place Rate Limiter*
*3. Distributed Challenges*
*4. Storage Options*
*5. Scaling Strategies*

## SECTION 2.1: HIGH-LEVEL ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RATE LIMITER COMPONENTS                                                |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |                        +------------------+                       |  |
|  |                        |   Rate Limiter   |                       |  |
|  |   Client               |     Service      |      Backend          |  |
|  |     |                  |                  |        |              |  |
|  |     |  1. Request      |  +------------+ |        |               |  |
|  |     | ------------->   |  |   Rules    | |        |               |  |
|  |     |                  |  |   Config   | |        |               |  |
|  |     |                  |  +-----+------+ |        |               |  |
|  |     |                  |        |        |        |               |  |
|  |     |  2. Check limit  |        v        |        |               |  |
|  |     |                  |  +------------+ |        |               |  |
|  |     |                  |  | Algorithm  | |        |               |  |
|  |     |                  |  |  (Token/   | |        |               |  |
|  |     |                  |  |  Sliding)  | |        |               |  |
|  |     |                  |  +-----+------+ |        |               |  |
|  |     |                  |        |        |        |               |  |
|  |     |                  |        v        |        |               |  |
|  |     |                  |  +------------+ |        |               |  |
|  |     |                  |  |   Cache    | |        |               |  |
|  |     |                  |  |  (Redis)   | |        |               |  |
|  |     |                  |  +------------+ |        |               |  |
|  |     |                  |        |        |        |               |  |
|  |     |  3a. ALLOW       |        |        |   4. Forward           |  |
|  |     | <---------------+--------+--------+--------------->         |  |
|  |     |                  |        |        |                        |  |
|  |     |  3b. DENY (429)  |        |        |                        |  |
|  |     | <---------------+--------+        |                         |  |
|  |     |                  |                  |                       |  |
|  |                        +------------------+                       |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  KEY COMPONENTS                                                         |
|                                                                         |
|  1. RULES ENGINE                                                        |
|     * Define rate limit rules                                           |
|     * Dynamic configuration (no redeploy)                               |
|     * Per endpoint, user tier, IP rules                                 |
|                                                                         |
|  2. RATE LIMITING ALGORITHM                                             |
|     * Token bucket / Sliding window / etc.                              |
|     * Implements the core logic                                         |
|                                                                         |
|  3. COUNTER STORAGE                                                     |
|     * Store request counts / tokens                                     |
|     * Fast read/write (in-memory)                                       |
|     * Usually Redis                                                     |
|                                                                         |
|  4. RULES STORAGE                                                       |
|     * Persist configuration                                             |
|     * Database or config file                                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.2: WHERE TO PLACE RATE LIMITER

```
+-------------------------------------------------------------------------+
|                                                                         |
|  OPTION 1: CLIENT-SIDE                                                  |
|  ----------------------                                                 |
|                                                                         |
|  +--------------------------------------------------------------------+ |
|  |                                                                    | |
|  |  +------------+                        +---------------+           | |
|  |  |   Client   |                        |    Server     |           | |
|  |  |            |                        |               |           | |
|  |  | +--------+ |    Rate limited        |               |           | |
|  |  | | Rate   | |    requests            |               |           | |
|  |  | |Limiter | +----------------------->|               |           | |
|  |  | +--------+ |                        |               |           | |
|  |  |            |                        |               |           | |
|  |  +------------+                        +---------------+           | |
|  |                                                                    | |
|  +--------------------------------------------------------------------+ |
|                                                                         |
|  PROS: Reduces server load, saves bandwidth                             |
|  CONS: Client can bypass, not trustworthy                               |
|                                                                         |
|  USE CASE: Mobile SDK limiting API calls to save user data              |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  OPTION 2: SERVER-SIDE (Application Layer)  COMMON                      |
|  -------------------------------------------------                      |
|                                                                         |
|  +--------------------------------------------------------------------+ |
|  |                                                                    | |
|  |  +--------+    +---------------------------------+                 | |
|  |  | Client |    |           Server                |                 | |
|  |  |        |    |  +-----------+  +------------+ |                  | |
|  |  |        +----+->|   Rate    |-->|    App     | |                 | |
|  |  |        |    |  |  Limiter  |  |   Logic    | |                  | |
|  |  |        |<---+--| Middleware|<--|            | |                 | |
|  |  +--------+    |  +-----------+  +------------+ |                  | |
|  |                |                                 |                 | |
|  |                +---------------------------------+                 | |
|  |                                                                    | |
|  +--------------------------------------------------------------------+ |
|                                                                         |
|  Implementation: Middleware in your application                         |
|  PROS: Full control, access to user context                             |
|  CONS: Each service needs it, not centralized                           |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  OPTION 3: API GATEWAY / REVERSE PROXY  RECOMMENDED                     |
|  ---------------------------------------------------                    |
|                                                                         |
|  +--------------------------------------------------------------------+ |
|  |                                                                    | |
|  |  +--------+    +---------------+    +---------------------------+  | |
|  |  | Client |    |  API Gateway  |    |      Microservices        |  | |
|  |  |        |    |               |    |                           |  | |
|  |  |        |    | +-----------+ |    |  +-----+ +-----------+    |  | |
|  |  |        +----+>|   Rate    |-+----+->|Svc A| |Svc B      |    |  | |
|  |  |        |    | |  Limiter  | |    |  +-----+ +-----------+    |  | |
|  |  |        |<---+-|           |<+----+--                         |  | |
|  |  +--------+    | +-----------+ |    |  +-----+ +-----------+    |  | |
|  |                |               |    |  |Svc C| |Svc D      |    |  | |
|  |                +---------------+    |  +-----+ +-----------+    |  | |
|  |                                     +---------------------------+  | |
|  |                                                                    | |
|  +--------------------------------------------------------------------+ |
|                                                                         |
|  Examples: Kong, AWS API Gateway, NGINX, Envoy, Istio                   |
|                                                                         |
|  PROS:                                                                  |
|  * Centralized, one place for all services                              |
|  * Services don't need rate limiting code                               |
|  * Consistent policies                                                  |
|                                                                         |
|  CONS:                                                                  |
|  * Single point of failure (need HA)                                    |
|  * May not have app context (user tier)                                 |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  OPTION 4: DEDICATED RATE LIMITER SERVICE                               |
|  -----------------------------------------                              |
|                                                                         |
|  +--------------------------------------------------------------------+ |
|  |                                                                    | |
|  |  +--------+    +---------------+    +---------------------------+  | |
|  |  | Client |    |  API Gateway  |    |      Microservices        |  | |
|  |  |        |    |               |    |                           |  | |
|  |  |        |    |     |         |    |  +-----+ +-----------+    |  | |
|  |  |        +----+---->|         +----+->|Svc A| |Svc B      |    |  | |
|  |  |        |    |     |         |    |  +--+--+ +--+--------+    |  | |
|  |  |        |<---+-----|<--------+----+-----|-------|             |  | |
|  |  +--------+    |     |         |    +-----|-------|-------------+  | |
|  |                +-----+---------+          |       |                | |
|  |                      |                    |       |                | |
|  |                      |    +---------------+-------+-----------+    | |
|  |                      |    |                                   |    | |
|  |                      +--->|  Rate Limiter Service             |    | |
|  |                           |  (Centralized)                    |    | |
|  |                           |                                   |    | |
|  |                           |  +--------+ +----------------+    |    | |
|  |                           |  | Redis  | | Rules          |    |    | |
|  |                           |  | Cache  | | Engine         |    |    | |
|  |                           |  +--------+ +----------------+    |    | |
|  |                           +-----------------------------------+    | |
|  |                                                                    | |
|  +--------------------------------------------------------------------+ |
|                                                                         |
|  Services call rate limiter before processing                           |
|  Example: Envoy external authorization, custom service                  |
|                                                                         |
|  PROS:                                                                  |
|  * Most flexible                                                        |
|  * Can implement complex rules                                          |
|  * Reusable across all services                                         |
|                                                                         |
|  CONS:                                                                  |
|  * Added latency (extra network hop)                                    |
|  * Another service to maintain                                          |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  HYBRID APPROACH (Real-world)  BEST PRACTICE                            |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Layer 1: Edge (CDN / WAF)                                        |  |
|  |  +-- IP-based rate limiting, DDoS protection                      |  |
|  |                                                                   |  |
|  |  Layer 2: API Gateway                                             |  |
|  |  +-- API key / global rate limits                                 |  |
|  |                                                                   |  |
|  |  Layer 3: Application                                             |  |
|  |  +-- User-specific / business logic limits                        |  |
|  |                                                                   |  |
|  |  Example:                                                         |  |
|  |  * Cloudflare: 10,000 req/s per IP (DDoS)                         |  |
|  |  * API Gateway: 1,000 req/min per API key                         |  |
|  |  * App: 10 posts/day per user (business rule)                     |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.3: DISTRIBUTED RATE LIMITING CHALLENGES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CHALLENGE 1: MULTIPLE SERVER INSTANCES                                 |
|  ---------------------------------------                                |
|                                                                         |
|  Problem: Requests routed to different servers, each with local state   |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  User limit: 100 requests/minute                                  |  |
|  |                                                                   |  |
|  |         +----------------------------------------------------+    |  |
|  |         |              Load Balancer                         |    |  |
|  |         +------------+----------+----------+-----------------+    |  |
|  |                      |          |          |                      |  |
|  |                      v          v          v                      |  |
|  |              +-----------++-----------++-----------+              |  |
|  |              | Server 1  || Server 2  || Server 3  |              |  |
|  |              |           ||           ||           |              |  |
|  |              | count: 40 || count: 35 || count: 45 |              |  |
|  |              | (local)   || (local)   || (local)   |              |  |
|  |              +-----------++-----------++-----------+              |  |
|  |                                                                   |  |
|  |  Total actual requests: 40 + 35 + 45 = 120                        |  |
|  |  Each server thinks: "User is under limit"                        |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  SOLUTION: Centralized counter store (Redis)                            |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |         +----------------------------------------------------+    |  |
|  |         |              Load Balancer                         |    |  |
|  |         +------------+----------+----------+-----------------+    |  |
|  |                      |          |          |                      |  |
|  |                      v          v          v                      |  |
|  |              +-----------++-----------++-----------+              |  |
|  |              | Server 1  || Server 2  || Server 3  |              |  |
|  |              +-----+-----++-----+-----++-----+-----+              |  |
|  |                    |            |            |                    |  |
|  |                    +------------+------------+                    |  |
|  |                                 |                                 |  |
|  |                                 v                                 |  |
|  |                    +-------------------------+                    |  |
|  |                    |        Redis           |                     |  |
|  |                    |   user:123 > 120      |                      |  |
|  |                    |   (shared counter)    |                      |  |
|  |                    +-------------------------+                    |  |
|  |                                                                   |  |
|  |  All servers check same counter Y                                 |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  CHALLENGE 2: RACE CONDITIONS                                           |
|  -----------------------------                                          |
|                                                                         |
|  Problem: Multiple servers read/update counter simultaneously           |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Limit: 100 | Current count: 99                                   |  |
|  |                                                                   |  |
|  |  Server A                    Server B                             |  |
|  |     |                           |                                 |  |
|  |     |  1. GET count = 99        |  1. GET count = 99              |  |
|  |     |                           |                                 |  |
|  |     |  2. 99 < 100? YES         |  2. 99 < 100? YES               |  |
|  |     |     Allow request         |     Allow request               |  |
|  |     |                           |                                 |  |
|  |     |  3. SET count = 100       |  3. SET count = 100             |  |
|  |     |                           |                                 |  |
|  |                                                                   |  |
|  |  Both requests allowed, but limit exceeded!                       |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  SOLUTION: Atomic operations in Redis                                   |
|                                                                         |
|  Option A: INCR (atomic increment)                                      |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  count = redis.incr(key)    # Atomic!                             |  |
|  |  if count > limit:                                                |  |
|  |      return DENY                                                  |  |
|  |  return ALLOW                                                     |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Option B: Lua Script (complex logic, still atomic)                     |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  -- Lua script runs atomically on Redis server                    |  |
|  |  local count = redis.call('GET', KEYS[1]) or 0                    |  |
|  |  if tonumber(count) < tonumber(ARGV[1]) then                      |  |
|  |      redis.call('INCR', KEYS[1])                                  |  |
|  |      return 1  -- allowed                                         |  |
|  |  end                                                              |  |
|  |  return 0  -- denied                                              |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  CHALLENGE 3: REDIS UNAVAILABLE                                         |
|  -------------------------------                                        |
|                                                                         |
|  What happens when Redis is down?                                       |
|                                                                         |
|  STRATEGY 1: Fail Open (Allow all)                                      |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  def check_rate_limit(user_id):                                   |  |
|  |      try:                                                         |  |
|  |          return redis_check(user_id)                              |  |
|  |      except RedisConnectionError:                                 |  |
|  |          logger.warn("Redis down, allowing request")              |  |
|  |          return True  # ALLOW                                     |  |
|  |                                                                   |  |
|  |  PROS: Service stays available                                    |  |
|  |  CONS: No rate limiting during outage (abuse risk)                |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  STRATEGY 2: Fail Closed (Deny all)                                     |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  def check_rate_limit(user_id):                                   |  |
|  |      try:                                                         |  |
|  |          return redis_check(user_id)                              |  |
|  |      except RedisConnectionError:                                 |  |
|  |          logger.error("Redis down, denying request")              |  |
|  |          return False  # DENY                                     |  |
|  |                                                                   |  |
|  |  PROS: Secure, no abuse                                           |  |
|  |  CONS: Service unavailable during outage                          |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  STRATEGY 3: Local Cache Fallback  RECOMMENDED                          |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  local_cache = {}  # In-memory fallback                           |  |
|  |                                                                   |  |
|  |  def check_rate_limit(user_id):                                   |  |
|  |      try:                                                         |  |
|  |          return redis_check(user_id)                              |  |
|  |      except RedisConnectionError:                                 |  |
|  |          # Fall back to local (per-server) limiting               |  |
|  |          return local_rate_limit(user_id, limit / num_servers)    |  |
|  |                                                                   |  |
|  |  PROS: Degraded but functional rate limiting                      |  |
|  |  CONS: Not perfectly accurate during outage                       |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  CHALLENGE 4: LATENCY                                                   |
|  --------------------                                                   |
|                                                                         |
|  Problem: Redis round-trip adds latency to every request                |
|                                                                         |
|  SOLUTIONS:                                                             |
|                                                                         |
|  1. Redis in same datacenter (< 1ms latency)                            |
|                                                                         |
|  2. Local cache with async sync                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  * Check local cache first (microseconds)                         |  |
|  |  * Async update to Redis                                          |  |
|  |  * Periodic sync from Redis                                       |  |
|  |  * Slight inaccuracy for massive performance gain                 |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  3. Pipeline Redis commands                                             |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  # Instead of 3 round-trips:                                      |  |
|  |  redis.get(key)                                                   |  |
|  |  redis.incr(key)                                                  |  |
|  |  redis.expire(key, ttl)                                           |  |
|  |                                                                   |  |
|  |  # One round-trip with pipeline:                                  |  |
|  |  pipe = redis.pipeline()                                          |  |
|  |  pipe.incr(key)                                                   |  |
|  |  pipe.expire(key, ttl)                                            |  |
|  |  count, _ = pipe.execute()                                        |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  4. Lua script (single round-trip for complex logic)                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.4: STORAGE OPTIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  STORAGE COMPARISON                                                     |
|                                                                         |
|  +------------------+----------+-----------+----------+---------------+ |
|  | Storage          | Latency  | Scalable  | Durable  | Use Case      | |
|  +------------------+----------+-----------+----------+---------------+ |
|  | Local memory     | ~us      | No        | No       | Single node   | |
|  | Redis            | < 1ms    | Yes       | Optional |  Best         | |
|  | Memcached        | < 1ms    | Yes       | No       | Simple        | |
|  | Database         | ~10ms    | Yes       | Yes      | Not recom.    | |
|  +------------------+----------+-----------+----------+---------------+ |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  REDIS: THE GO-TO CHOICE                                                |
|                                                                         |
|  Why Redis?                                                             |
|  * Sub-millisecond latency                                              |
|  * Atomic operations (INCR, Lua scripts)                                |
|  * TTL support (auto-expire keys)                                       |
|  * Clustering for scale                                                 |
|  * Replication for HA                                                   |
|                                                                         |
|  REDIS CLUSTER SETUP                                                    |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |       +-------------------------------------------------+         |  |
|  |       |              Redis Cluster                      |         |  |
|  |       |                                                 |         |  |
|  |       |  +---------+  +---------+  +---------+        |           |  |
|  |       |  | Master 1|  | Master 2|  | Master 3|        |           |  |
|  |       |  | Slot    |  | Slot    |  | Slot    |        |           |  |
|  |       |  | 0-5460  |  |5461-10922| |10923-16383|       |          |  |
|  |       |  +----+----+  +----+----+  +----+----+        |           |  |
|  |       |       |            |            |              |          |  |
|  |       |  +----v----+  +----v----+  +----v----+        |           |  |
|  |       |  |Replica 1|  |Replica 2|  |Replica 3|        |           |  |
|  |       |  +---------+  +---------+  +---------+        |           |  |
|  |       |                                                 |         |  |
|  |       +-------------------------------------------------+         |  |
|  |                                                                   |  |
|  |  * Data sharded by key hash across masters                        |  |
|  |  * Each master has replica for failover                           |  |
|  |  * Client routes to correct shard automatically                   |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  REDIS DATA STRUCTURES FOR RATE LIMITING                                |
|                                                                         |
|  STRING (Counter):                                                      |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Key: "ratelimit:user:123:window:1640000000"                      |  |
|  |  Value: "42" (request count)                                      |  |
|  |  TTL: 60 seconds                                                  |  |
|  |                                                                   |  |
|  |  Commands: INCR, GET, EXPIRE, SETEX                               |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  HASH (Token bucket state):                                             |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Key: "ratelimit:user:123"                                        |  |
|  |  Fields: {                                                        |  |
|  |    "tokens": 8.5,                                                 |  |
|  |    "last_refill": 1640000000.123                                  |  |
|  |  }                                                                |  |
|  |                                                                   |  |
|  |  Commands: HMGET, HMSET                                           |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  SORTED SET (Sliding log):                                              |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Key: "ratelimit:user:123"                                        |  |
|  |  Members: {                                                       |  |
|  |    "req_uuid_1": 1640000001.123,  (score = timestamp)             |  |
|  |    "req_uuid_2": 1640000002.456,                                  |  |
|  |    "req_uuid_3": 1640000003.789                                   |  |
|  |  }                                                                |  |
|  |                                                                   |  |
|  |  Commands: ZADD, ZREMRANGEBYSCORE, ZCARD                          |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.5: SCALING STRATEGIES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCALING RATE LIMITER                                                   |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  HORIZONTAL SCALING (Application Layer)                           |  |
|  |                                                                   |  |
|  |  +------------------------------------------------------------+   |  |
|  |  |                  Load Balancer                             |   |  |
|  |  +-------+------------+------------+------------+-------------+   |  |
|  |          |            |            |            |                 |  |
|  |          v            v            v            v                 |  |
|  |     +--------+   +--------+   +--------+   +--------+             |  |
|  |     |  App   |   |  App   |   |  App   |   |  App   |             |  |
|  |     | + RL   |   | + RL   |   | + RL   |   | + RL   |             |  |
|  |     +----+---+   +----+---+   +----+---+   +----+---+             |  |
|  |          |            |            |            |                 |  |
|  |          +------------+-----+------+------------+                 |  |
|  |                             |                                     |  |
|  |                             v                                     |  |
|  |                    +------------------+                           |  |
|  |                    |  Redis Cluster   |                           |  |
|  |                    |  (Shared State)  |                           |  |
|  |                    +------------------+                           |  |
|  |                                                                   |  |
|  |  * Add more app servers as needed                                 |  |
|  |  * All share same Redis for counters                              |  |
|  |  * Stateless rate limiter in each app                             |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  REDIS SCALING                                                          |
|                                                                         |
|  Option 1: Redis Cluster (Horizontal Sharding)                          |
|  * Auto-shards by key                                                   |
|  * Scales reads and writes                                              |
|  * 16,384 hash slots                                                    |
|                                                                         |
|  Option 2: Read Replicas                                                |
|  * Reads from replicas                                                  |
|  * Writes to master                                                     |
|  * Good if reads >> writes                                              |
|                                                                         |
|  Option 3: Multiple Clusters by Region                                  |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  +-----------------+         +-----------------+                  |  |
|  |  |   US-EAST       |         |   US-WEST       |                  |  |
|  |  |                 |         |                 |                  |  |
|  |  | App -> Redis    |         | App -> Redis    |                  |  |
|  |  | Cluster         |         | Cluster         |                  |  |
|  |  |                 |         |                 |                  |  |
|  |  +-----------------+         +-----------------+                  |  |
|  |                                                                   |  |
|  |  Trade-off:                                                       |  |
|  |  * Lower latency (local Redis)                                    |  |
|  |  * But: User can get 2x limit by switching regions                |  |
|  |  * Acceptable for most use cases                                  |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  STICKY SESSIONS (Alternative)                                          |
|                                                                         |
|  Route same user to same server > local rate limiting works             |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |             +---------------------------------------+             |  |
|  |             |        Load Balancer                  |             |  |
|  |             |  (Consistent hashing by user_id)     |              |  |
|  |             +--------+---------+---------+----------+             |  |
|  |                      |         |         |                        |  |
|  |  User A -------------+---------|         |                        |  |
|  |  User B -------------|---------+---------|                        |  |
|  |  User C -------------|---------|---------+---------               |  |
|  |                      |         |         |                        |  |
|  |                      v         v         v                        |  |
|  |                 +--------++--------++--------+                    |  |
|  |                 |Server 1||Server 2||Server 3|                    |  |
|  |                 |(User A)||(User B)||(User C)|                    |  |
|  |                 |Local RL||Local RL||Local RL|                    |  |
|  |                 +--------++--------++--------+                    |  |
|  |                                                                   |  |
|  |  PROS: No Redis needed, ultra-low latency                         |  |
|  |  CONS: Server failure = rate limit reset, uneven distribution     |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

END OF CHAPTER 2
