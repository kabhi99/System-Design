# REDIS
*Chapter 4: Redis in System Design*

Redis appears in almost every system design interview. This chapter covers
the most common patterns and real-world use cases with implementation details.

## SECTION 4.1: CACHING PATTERNS

```
+--------------------------------------------------------------------------+
|                                                                          |
|  CACHE-ASIDE (LAZY LOADING) -- most common                               |
|                                                                          |
|  1. App checks cache                                                     |
|  2. Cache HIT -> return data                                             |
|  3. Cache MISS -> read from DB -> store in cache -> return               |
|                                                                          |
|  Client --> Cache (miss) --> DB --> Cache (store) --> Client             |
|                                                                          |
|  PROS: Only requested data is cached, cache failure is not fatal         |
|  CONS: Cache miss penalty (3 trips), stale data possible                 |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  WRITE-THROUGH                                                           |
|                                                                          |
|  Every write goes to cache AND database together.                        |
|                                                                          |
|  Client --> Cache + DB (write both)                                      |
|                                                                          |
|  PROS: Cache always up-to-date, no stale reads                           |
|  CONS: Higher write latency, cache filled with unused data               |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  WRITE-BEHIND (WRITE-BACK)                                               |
|                                                                          |
|  Write to cache immediately, async write to DB later.                    |
|                                                                          |
|  Client --> Cache (immediate) --> DB (async, batched)                    |
|                                                                          |
|  PROS: Very fast writes, batch DB updates                                |
|  CONS: Data loss risk if cache crashes before DB write                   |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  CACHE INVALIDATION STRATEGIES:                                          |
|                                                                          |
|  * TTL (Time-To-Live): Auto-expire after N seconds                       |
|  * Event-driven: Invalidate on DB change (CDC, pub/sub)                  |
|  * Versioned keys: cache:v2:user:123 (new version = new key)             |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 4.2: RATE LIMITING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. FIXED WINDOW COUNTER                                                |
|                                                                         |
|  Key: ratelimit:{user}:{minute}                                         |
|  INCR + EXPIRE                                                          |
|                                                                         |
|  INCR ratelimit:user123:202401151030                                    |
|  if count == 1: EXPIRE key 60                                           |
|  if count > 100: reject request                                         |
|                                                                         |
|  Problem: burst at window boundary (200 requests in 1 second)           |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  2. SLIDING WINDOW LOG (sorted set)                                     |
|                                                                         |
|  ZADD ratelimit:user123 {timestamp} {request-id}                        |
|  ZREMRANGEBYSCORE ratelimit:user123 0 {now - window}                    |
|  ZCARD ratelimit:user123                                                |
|  if count > limit: reject                                               |
|                                                                         |
|  Accurate but memory-heavy (stores every request timestamp).            |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  3. SLIDING WINDOW COUNTER (best balance)                               |
|                                                                         |
|  Weighted average of current + previous window counts.                  |
|                                                                         |
|  rate = prev_count * overlap_pct + current_count                        |
|                                                                         |
|  Memory-efficient (2 counters per window) + smooth behavior.            |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  4. TOKEN BUCKET (Lua script)                                           |
|                                                                         |
|  local tokens = redis.call('GET', KEYS[1]) or MAX_TOKENS                |
|  local last = redis.call('GET', KEYS[2]) or now                         |
|  local elapsed = now - last                                             |
|  tokens = min(MAX, tokens + elapsed * REFILL_RATE)                      |
|  if tokens >= 1 then                                                    |
|      tokens = tokens - 1                                                |
|      redis.call('SET', KEYS[1], tokens)                                 |
|      redis.call('SET', KEYS[2], now)                                    |
|      return 1 -- allowed                                                |
|  end                                                                    |
|  return 0 -- rejected                                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.3: SESSION MANAGEMENT

```
+--------------------------------------------------------------------------+
|                                                                          |
|  REDIS AS SESSION STORE                                                  |
|                                                                          |
|  Why Redis over sticky sessions / DB sessions:                           |
|  * Stateless app servers (any server can handle any request)             |
|  * Sub-ms session reads (vs 5-50ms DB)                                   |
|  * Auto-expiry via TTL (no cleanup jobs)                                 |
|  * Shared across multiple app instances                                  |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  IMPLEMENTATION:                                                         |
|                                                                          |
|  Login:                                                                  |
|  session_id = generate_uuid()                                            |
|  SET session:{session_id} "{user_id, roles, ...}" EX 3600                |
|  Set-Cookie: sid={session_id}                                            |
|                                                                          |
|  Every request:                                                          |
|  session_data = GET session:{cookie.sid}                                 |
|  if nil: redirect to login                                               |
|  else: extend TTL, serve request                                         |
|                                                                          |
|  Logout:                                                                 |
|  DEL session:{session_id}                                                |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  USE HASH FOR RICH SESSIONS:                                             |
|  HSET session:abc user_id 123 role admin cart_size 3                     |
|  HGET session:abc role  > "admin"                                        |
|  HINCRBY session:abc cart_size 1                                         |
|  EXPIRE session:abc 3600                                                 |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 4.4: LEADERBOARDS AND RANKINGS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Sorted sets make leaderboards trivial.                                 |
|                                                                         |
|  ADD/UPDATE SCORE:                                                      |
|  ZADD game:leaderboard 1500 "player:alice"                              |
|  ZINCRBY game:leaderboard 50 "player:alice"  (won a game)               |
|                                                                         |
|  TOP 10:                                                                |
|  ZREVRANGE game:leaderboard 0 9 WITHSCORES                              |
|                                                                         |
|  MY RANK:                                                               |
|  ZREVRANK game:leaderboard "player:alice"  > 3 (4th place)              |
|                                                                         |
|  PLAYERS AROUND ME:                                                     |
|  rank = ZREVRANK ... "player:alice"                                     |
|  ZREVRANGE game:leaderboard (rank-5) (rank+5) WITHSCORES                |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  TIME-SCOPED LEADERBOARDS:                                              |
|  * Daily: ZADD leaderboard:2024-01-15 score player                      |
|  * Weekly: ZUNIONSTORE leaderboard:week dest 7                          |
|            leaderboard:day1 leaderboard:day2 ...                        |
|  * Expire old keys: EXPIRE leaderboard:2024-01-15 604800                |
|                                                                         |
|  SCALE: Sorted set with 1M members: ~100 MB RAM                         |
|  ZREVRANGE O(log(N)+M): fast even with millions of members              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.5: DISTRIBUTED LOCKING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  USE CASE: Only one service instance processes order-456 at a time.     |
|                                                                         |
|  ACQUIRE:                                                               |
|  SET lock:order:456 {uuid} NX EX 30                                     |
|  * NX: only if not exists                                               |
|  * EX 30: auto-release in 30s (prevent deadlocks)                       |
|  * uuid: identify the owner (for safe release)                          |
|                                                                         |
|  RELEASE (Lua -- atomic check + delete):                                |
|  if GET(lock:order:456) == my_uuid then DEL(lock:order:456)             |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  PITFALLS:                                                              |
|                                                                         |
|  1. LOCK EXPIRY WHILE STILL PROCESSING                                  |
|     Process takes > 30s, lock expires, another process grabs it.        |
|     Fix: Use lock extension (watchdog thread renews TTL).               |
|     Libraries: Redisson (Java), redis-lock (Node), Redsync (Go).        |
|                                                                         |
|  2. CLOCK DRIFT                                                         |
|     EX relies on Redis server clock.                                    |
|     Usually fine. For critical systems, use fencing tokens.             |
|                                                                         |
|  3. REDIS FAILOVER                                                      |
|     Master dies, replica promoted, but lock not yet replicated!         |
|     Fix: Redlock algorithm (lock across 5 independent Redis).           |
|     Or: Accept rare double-processing, make operations idempotent.      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.6: REAL-TIME ANALYTICS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  COUNTING:                                                              |
|  * Page views: INCR pageviews:homepage:2024-01-15                       |
|  * API calls:  INCR api:calls:user:123:2024-01-15-10 (hourly)           |
|                                                                         |
|  UNIQUE COUNTING (HyperLogLog):                                         |
|  * Unique visitors: PFADD uv:homepage:2024-01-15 user_id                |
|  * Unique IPs:      PFADD unique-ips:api ip_address                     |
|  * Count:           PFCOUNT uv:homepage:2024-01-15                      |
|  * 12 KB per counter, ~0.81% error, perfect for dashboards              |
|                                                                         |
|  REAL-TIME TRENDING (sorted sets):                                      |
|  * ZINCRBY trending:articles 1 "article:789"                            |
|  * Decay: periodically multiply all scores by 0.9                       |
|  * Top trending: ZREVRANGE trending:articles 0 9                        |
|                                                                         |
|  TIME-SERIES (streams or sorted sets):                                  |
|  * XADD metrics:cpu * value 45.2 host server1                           |
|  * XRANGE metrics:cpu {5min-ago} +                                      |
|  * Or use RedisTimeSeries module for aggregation                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.7: MESSAGE QUEUES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SIMPLE QUEUE (Lists):                                                  |
|                                                                         |
|  Producer: LPUSH queue:emails "{to: user@email, body: ...}"             |
|  Consumer: BRPOP queue:emails 30  (blocking pop, 30s timeout)           |
|                                                                         |
|  For reliable processing:                                               |
|  BRPOPLPUSH queue:emails queue:processing                               |
|  (atomically pop from queue, push to processing list)                   |
|  On success: LREM queue:processing 1 message                            |
|  On failure: message stays in processing list for retry                 |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  RELIABLE QUEUE (Streams -- recommended):                               |
|                                                                         |
|  Producer: XADD emails * to "user@email" subject "Welcome"              |
|  Consumer group:                                                        |
|    XGROUP CREATE emails email-workers $ MKSTREAM                        |
|    XREADGROUP GROUP email-workers worker-1 COUNT 1 STREAMS emails >     |
|    XACK emails email-workers {message-id}                               |
|                                                                         |
|  Advantages over Lists:                                                 |
|  * Consumer groups (load balancing across workers)                      |
|  * Acknowledgment (unacked messages can be re-claimed)                  |
|  * Message persistence with IDs                                         |
|  * XPENDING to find stuck messages                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.8: COMMON ARCHITECTURE PATTERNS

```
+--------------------------------------------------------------------------+
|                                                                          |
|  1. READ-THROUGH CACHE                                                   |
|                                                                          |
|  Client -> Redis -> (miss) -> DB -> Redis -> Client                      |
|                                                                          |
|  2. WRITE-BEHIND + CACHE                                                 |
|                                                                          |
|  Client -> Redis (fast write) -> Async worker -> DB                      |
|                                                                          |
|  3. PUB/SUB FOR CACHE INVALIDATION                                       |
|                                                                          |
|  DB write -> PUBLISH invalidate "user:123"                               |
|  All app servers -> SUBSCRIBE invalidate -> DEL local cache              |
|                                                                          |
|  4. REDIS AS PRIMARY DATABASE                                            |
|                                                                          |
|  For use cases where sub-ms reads + limited data:                        |
|  * Session store                                                         |
|  * Feature flags                                                         |
|  * Real-time game state                                                  |
|  * Shopping cart (with AOF persistence)                                  |
|                                                                          |
|  5. SIDECAR CACHE                                                        |
|                                                                          |
|  +--------+    +-------+    +--------+                                   |
|  | App    | -> | Redis | -> | Database|                                  |
|  | Server |    | (local|    | (Postgres|                                 |
|  |        |    |  or   |    |  MySQL)  |                                 |
|  |        |    | remote)|   |          |                                 |
|  +--------+    +-------+    +--------+                                   |
|                                                                          |
|  * Local Redis: lowest latency, but inconsistent across instances        |
|  * Remote Redis: shared cache, consistent, slight network cost           |
|                                                                          |
+--------------------------------------------------------------------------+
```
