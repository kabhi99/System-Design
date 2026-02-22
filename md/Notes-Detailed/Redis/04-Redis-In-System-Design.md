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

## SECTION 4.9: DELAY QUEUE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DELAY QUEUE WITH SORTED SETS                                           |
|  =============================                                          |
|                                                                         |
|  Score = execution timestamp (epoch seconds/ms).                        |
|  Messages invisible until their timestamp arrives.                      |
|                                                                         |
|  PRODUCER (schedule for later):                                         |
|  ZADD delay_queue <future_timestamp> <message_json>                     |
|                                                                         |
|  // Cancel unpaid order after 15 min                                    |
|  ZADD delay_queue 1708701000 '{"action":"cancel","order":"ord-123"}'    |
|                                                                         |
|  // Send reminder email in 30 min                                       |
|  ZADD delay_queue 1708702000 '{"action":"remind","user":"usr-456"}'     |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  CONSUMER (poll for ready messages):                                    |
|                                                                         |
|  // Lua script: atomic fetch + remove (no race condition)               |
|  local msgs = redis.call('ZRANGEBYSCORE',                               |
|    KEYS[1], '0', ARGV[1], 'LIMIT', '0', '10')                           |
|  if #msgs > 0 then                                                      |
|    redis.call('ZREM', KEYS[1], unpack(msgs))                            |
|  end                                                                    |
|  return msgs                                                            |
|  // ARGV[1] = current timestamp                                         |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  USE CASES:                                                             |
|  * Cancel unpaid orders after timeout                                   |
|  * Retry failed API calls with exponential backoff                      |
|  * Send scheduled notifications (OTP expiry, reminders)                 |
|  * Delayed cache invalidation (wait for replication lag)                |
|  * Rate limit cooldowns (user can retry after 60s)                      |
|                                                                         |
|  WHY REDIS OVER SQS/KAFKA:                                              |
|  * SQS max delay: 15 min. Redis: unlimited.                             |
|  * Kafka: no native delay. Redis: trivial with ZSET.                    |
|  * Sub-ms polling. Can cancel scheduled messages (ZREM).                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.10: PRIORITY QUEUE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PRIORITY QUEUE WITH SORTED SETS                                        |
|  ================================                                       |
|                                                                         |
|  Score = priority (lower score = higher priority).                      |
|  ZPOPMIN always returns highest priority first.                         |
|                                                                         |
|  // Add tasks with priority                                             |
|  ZADD task_queue 0 '{"type":"otp_sms","user":"u1"}'      // P0 crit     |
|  ZADD task_queue 1 '{"type":"order_confirm","id":"o1"}'   // P1 high    |
|  ZADD task_queue 2 '{"type":"marketing","id":"m1"}'       // P2 normal  |
|                                                                         |
|  // Consumer: always gets highest priority first                        |
|  ZPOPMIN task_queue 1                                                   |
|  // Returns P0 task first, then P1, then P2                             |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  PRIORITY + FIFO (same priority = FIFO order):                          |
|                                                                         |
|  Score = priority * 10^13 + timestamp                                   |
|  // Same priority? Earlier timestamp wins (FIFO).                       |
|                                                                         |
|  // P0 at time 1000                                                     |
|  ZADD task_queue 0000001708700000 '{"task":"otp_1"}'                    |
|  // P0 at time 1001 (processed after otp_1)                             |
|  ZADD task_queue 0000001708700001 '{"task":"otp_2"}'                    |
|  // P1 at time 999 (processed after ALL P0s)                            |
|  ZADD task_queue 10000001708699999 '{"task":"order_1"}'                 |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  STARVATION PREVENTION:                                                 |
|  Low priority tasks never processed if high priority keeps coming.      |
|  Fix: Weighted polling or age-based priority boost.                     |
|  // Every 60s, boost old P2 tasks: ZINCRBY task_queue -1 <msg>          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.11: IDEMPOTENCY KEY STORE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  IDEMPOTENCY WITH REDIS SETNX                                           |
|  ==============================                                         |
|                                                                         |
|  Prevent duplicate processing of API requests / events.                 |
|                                                                         |
|  // API receives request with idempotency key                           |
|  result = SET idempotency:{key} "processing" NX EX 3600                 |
|                                                                         |
|  if result == OK:                                                       |
|    // First request — process it                                        |
|    response = process_payment(order_id, amount)                         |
|    SET idempotency:{key} response_json EX 86400  // cache 24h           |
|    return response                                                      |
|  else:                                                                  |
|    // Duplicate — return cached response                                |
|    cached = GET idempotency:{key}                                       |
|    if cached == "processing":                                           |
|      return 409, "Request in progress"                                  |
|    return cached  // previous response                                  |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  EVENT DEDUPLICATION (Kafka consumers):                                 |
|                                                                         |
|  event_id = event.headers["event_id"]                                   |
|  if not SETNX(f"processed:{event_id}", "1", EX=604800):                 |
|    return  // already processed, skip                                   |
|  process(event)                                                         |
|  // Key expires after 7 days (events older than that won't replay)      |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  USE CASES:                                                             |
|  * Payment APIs (prevent double charge)                                 |
|  * Order creation (prevent duplicate orders on retry)                   |
|  * Webhook delivery (external system retries on timeout)                |
|  * Kafka consumer dedup (at-least-once -> effectively once)             |
|                                                                         |
|  WHY REDIS: SETNX is atomic, sub-ms, auto-expires with TTL.             |
|  DB alternative: unique constraint on idempotency_key column.           |
|  Best practice: use BOTH (Redis for speed, DB as safety net).           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.12: ONLINE PRESENCE / USER STATUS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ONLINE PRESENCE TRACKING                                               |
|  =========================                                              |
|                                                                         |
|  Track who is online in real-time (chat apps, collaboration tools).     |
|                                                                         |
|  APPROACH 1: KEY + TTL HEARTBEAT                                        |
|                                                                         |
|  // User sends heartbeat every 30s                                      |
|  SET online:{user_id} "1" EX 60                                         |
|  // If no heartbeat for 60s, key expires -> user is offline             |
|                                                                         |
|  // Check if user is online                                             |
|  EXISTS online:{user_id}  // 1 = online, 0 = offline                    |
|                                                                         |
|  // Get last seen (store timestamp instead of "1")                      |
|  SET online:{user_id} "1708700000" EX 60                                |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  APPROACH 2: SET + SORTED SET (for bulk queries)                        |
|                                                                         |
|  // Heartbeat: add to sorted set with current timestamp                 |
|  ZADD online_users <now> user_id                                        |
|                                                                         |
|  // Get all online users (active in last 60s)                           |
|  ZRANGEBYSCORE online_users (now - 60) +inf                             |
|                                                                         |
|  // Cleanup: remove stale entries periodically                          |
|  ZREMRANGEBYSCORE online_users 0 (now - 60)                             |
|                                                                         |
|  // Count online users                                                  |
|  ZCOUNT online_users (now - 60) +inf                                    |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  APPROACH 3: BITMAP (millions of users, memory efficient)               |
|                                                                         |
|  // User 12345 comes online                                             |
|  SETBIT online_bitmap 12345 1                                           |
|                                                                         |
|  // User 12345 goes offline                                             |
|  SETBIT online_bitmap 12345 0                                           |
|                                                                         |
|  // Count total online users                                            |
|  BITCOUNT online_bitmap  // O(N) but very fast on bitmaps               |
|                                                                         |
|  // Check specific user                                                 |
|  GETBIT online_bitmap 12345  // 1 = online                              |
|                                                                         |
|  // 1M users = 125 KB memory. 100M users = 12.5 MB.                     |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  BROADCAST STATUS CHANGES:                                              |
|  PUBLISH presence:{user_id} "online"                                    |
|  Friends subscribe to their contacts' presence channels.                |
|  Or: batch poll (WhatsApp style) — check friend list on app open.       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.13: INVENTORY / FLASH SALE COUNTER

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ATOMIC INVENTORY WITH REDIS                                            |
|  ============================                                           |
|                                                                         |
|  Flash sale: 10,000 users want 100 items simultaneously.                |
|  Database UPDATE with WHERE stock > 0 creates hot row contention.       |
|  Redis: atomic decrement, sub-ms, handles 100K+ ops/sec.                |
|                                                                         |
|  SETUP:                                                                 |
|  SET inventory:product:123 100   // 100 items available                 |
|                                                                         |
|  PURCHASE (Lua script — atomic check + decrement):                      |
|                                                                         |
|  local stock = tonumber(redis.call('GET', KEYS[1]))                     |
|  if stock and stock > 0 then                                            |
|    redis.call('DECR', KEYS[1])                                          |
|    return 1   // success — reserved                                     |
|  end                                                                    |
|  return 0     // sold out                                               |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  WITH QUANTITY (buy multiple):                                          |
|                                                                         |
|  local stock = tonumber(redis.call('GET', KEYS[1]))                     |
|  local qty = tonumber(ARGV[1])                                          |
|  if stock and stock >= qty then                                         |
|    redis.call('DECRBY', KEYS[1], qty)                                   |
|    return 1                                                             |
|  end                                                                    |
|  return 0                                                               |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  FULL FLASH SALE FLOW:                                                  |
|                                                                         |
|  1. Pre-load: SET inventory:sku:ABC 100                                 |
|  2. User clicks "Buy":                                                  |
|     Redis Lua: atomic check + decrement                                 |
|     If success: create order in DB (async, via Kafka)                   |
|     If sold out: return 429 immediately                                 |
|  3. Order service confirms and finalizes in DB                          |
|  4. If order fails/cancels: INCR inventory:sku:ABC (restore stock)      |
|                                                                         |
|  WHY NOT JUST DB:                                                       |
|  * DB lock contention: 10K concurrent updates on one row = deadlocks    |
|  * Redis: single-threaded, Lua is atomic, no locks needed               |
|  * Response time: 0.1ms (Redis) vs 10-50ms (DB under contention)        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.14: GEOSPATIAL QUERIES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  GEOSPATIAL WITH REDIS                                                  |
|  ======================                                                 |
|                                                                         |
|  Built-in geospatial indexing using sorted sets internally.             |
|  Perfect for: nearby drivers, stores, restaurants, friends.             |
|                                                                         |
|  ADD LOCATIONS:                                                         |
|  GEOADD drivers -73.9857 40.7484 "driver:101"   // NYC                  |
|  GEOADD drivers -73.9712 40.7831 "driver:102"   // Central Park         |
|  GEOADD stores  -73.9654 40.7829 "starbucks:42"                         |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  FIND NEARBY (radius query):                                            |
|  // All drivers within 5 km of user's location                          |
|  GEOSEARCH drivers FROMLONLAT -73.98 40.75 BYRADIUS 5 km                |
|    ASC COUNT 10 WITHCOORD WITHDIST                                      |
|  // Returns: driver IDs, sorted by distance, with coordinates           |
|                                                                         |
|  DISTANCE BETWEEN TWO POINTS:                                           |
|  GEODIST drivers "driver:101" "driver:102" km                           |
|  // Returns: 3.87 (km)                                                  |
|                                                                         |
|  GET COORDINATES:                                                       |
|  GEOPOS drivers "driver:101"                                            |
|  // Returns: [-73.9857, 40.7484]                                        |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  UBER-STYLE DRIVER TRACKING:                                            |
|                                                                         |
|  // Driver sends location update every 5s                               |
|  GEOADD active_drivers <lng> <lat> "driver:{id}"                        |
|  EXPIRE active_drivers:{id}_heartbeat 30                                |
|                                                                         |
|  // Rider requests ride: find 10 nearest drivers within 3 km            |
|  GEOSEARCH active_drivers FROMLONLAT <rider_lng> <rider_lat>            |
|    BYRADIUS 3 km ASC COUNT 10                                           |
|                                                                         |
|  // Reserve best driver atomically                                      |
|  SET driver_lock:{driver_id} ride_id NX EX 30                           |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  LIMITATIONS:                                                           |
|  * No polygon queries (only radius / bounding box)                      |
|  * No altitude support (2D only)                                        |
|  * For complex geo: use PostGIS or Elasticsearch                        |
|  * Redis geospatial is best for simple "nearby" searches                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.15: BLOOM FILTERS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BLOOM FILTER (RedisBloom module)                                       |
|  =================================                                      |
|                                                                         |
|  Probabilistic data structure:                                          |
|  "Definitely NOT in set" or "PROBABLY in set"                           |
|  No false negatives. Small false positive rate (~1%).                   |
|                                                                         |
|  BF.RESERVE usernames 0.01 1000000  // 1% error, 1M items               |
|  BF.ADD usernames "john_doe"                                            |
|  BF.EXISTS usernames "john_doe"     // 1 (probably exists)              |
|  BF.EXISTS usernames "xyz_new"      // 0 (definitely doesn't exist)     |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  USE CASES:                                                             |
|                                                                         |
|  1. CACHE PENETRATION PREVENTION                                        |
|     Attacker queries for IDs that don't exist in DB.                    |
|     Every request is a cache miss -> hits DB.                           |
|     Fix: check Bloom filter first. If "not exists" -> return 404.       |
|     Only query DB if Bloom says "probably exists".                      |
|                                                                         |
|  2. USERNAME / EMAIL AVAILABILITY                                       |
|     Instant "taken" check without querying DB.                          |
|     If Bloom says "not exists" -> definitely available.                 |
|     If "probably exists" -> query DB to confirm.                        |
|                                                                         |
|  3. DEDUPLICATION (have I seen this event before?)                      |
|     BF.ADD processed_events event_id                                    |
|     Useful when maintaining a full set is too expensive.                |
|                                                                         |
|  4. RECOMMENDATION SYSTEMS                                              |
|     "Don't show content user has already seen"                          |
|     BF.EXISTS seen:user:123 article_id                                  |
|                                                                         |
|  MEMORY: ~1.2 MB for 1M items at 1% false positive rate.                |
|  Compare: storing 1M IDs in a SET = ~50-100 MB.                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.16: FEATURE FLAGS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FEATURE FLAGS WITH REDIS                                               |
|  =========================                                              |
|                                                                         |
|  Toggle features instantly without deployment.                          |
|  Redis: sub-ms reads, shared across all service instances.              |
|                                                                         |
|  SIMPLE ON/OFF:                                                         |
|  SET feature:dark_mode "true"                                           |
|  SET feature:new_checkout "false"                                       |
|                                                                         |
|  // App checks:                                                         |
|  if GET("feature:dark_mode") == "true":                                 |
|    show_dark_mode()                                                     |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  PERCENTAGE ROLLOUT:                                                    |
|  SET feature:new_checkout:rollout "25"  // 25% of users                 |
|                                                                         |
|  // App: hash(user_id) % 100 < 25 -> show new checkout                  |
|  rollout = int(GET("feature:new_checkout:rollout"))                     |
|  if hash(user_id) % 100 < rollout:                                      |
|    show_new_checkout()                                                  |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  USER-SPECIFIC FLAGS (beta testers):                                    |
|  SADD feature:new_checkout:users "user:123" "user:456"                  |
|  SISMEMBER feature:new_checkout:users "user:123"  // 1 = enabled        |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  KILL SWITCH (instant disable during incident):                         |
|  SET feature:payment_processing "false"                                 |
|  // All instances read from Redis — takes effect in < 1 second          |
|  // No deploy, no restart needed                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.17: PUB/SUB FOR REAL-TIME NOTIFICATIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PUB/SUB REAL-TIME PATTERNS                                             |
|  ===========================                                            |
|                                                                         |
|  PATTERN 1: CACHE INVALIDATION BROADCAST                                |
|                                                                         |
|  // Service updates DB                                                  |
|  UPDATE users SET name = 'new' WHERE id = 123;                          |
|  PUBLISH cache:invalidate "user:123"                                    |
|                                                                         |
|  // All app servers subscribe                                           |
|  SUBSCRIBE cache:invalidate                                             |
|  // On message: DEL from local cache                                    |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  PATTERN 2: REAL-TIME NOTIFICATIONS                                     |
|                                                                         |
|  // User subscribes to their channel (via WebSocket server)             |
|  SUBSCRIBE notifications:user:123                                       |
|                                                                         |
|  // Any service can notify                                              |
|  PUBLISH notifications:user:123 '{"type":"order_shipped"}'              |
|                                                                         |
|  // WebSocket server receives and pushes to client                      |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  PATTERN 3: INTER-SERVICE EVENTS (lightweight)                          |
|                                                                         |
|  PUBLISH config:updated '{"key":"rate_limit","value":1000}'             |
|  // All services subscribed to config:updated get instant refresh       |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  WARNING: Pub/Sub is FIRE-AND-FORGET.                                   |
|  * If subscriber is offline, message is LOST                            |
|  * No persistence, no replay, no acknowledgment                         |
|  * For reliable messaging: use Redis Streams or Kafka                   |
|  * Pub/Sub is best for: ephemeral notifications, cache invalidation,    |
|    presence updates — where losing some messages is acceptable.         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.18: DISTRIBUTED SEMAPHORE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DISTRIBUTED SEMAPHORE (limit concurrent access)                        |
|  ================================================                       |
|                                                                         |
|  Lock = only 1 can access. Semaphore = N can access concurrently.       |
|                                                                         |
|  USE CASES:                                                             |
|  * Limit to 5 concurrent API calls to a slow external service           |
|  * Max 3 parallel DB connections per service instance                   |
|  * Rate limit concurrent file uploads per user                          |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  SORTED SET APPROACH:                                                   |
|                                                                         |
|  // Acquire: add self with TTL timestamp as score                       |
|  // Max 5 concurrent holders                                            |
|                                                                         |
|  local key = KEYS[1]                                                    |
|  local limit = tonumber(ARGV[1])     // 5                               |
|  local now = tonumber(ARGV[2])                                          |
|  local ttl = tonumber(ARGV[3])       // 30 seconds                      |
|  local id = ARGV[4]                  // unique holder id                |
|                                                                         |
|  // Remove expired holders                                              |
|  redis.call('ZREMRANGEBYSCORE', key, '-inf', now)                       |
|                                                                         |
|  // Check if under limit                                                |
|  if redis.call('ZCARD', key) < limit then                               |
|    redis.call('ZADD', key, now + ttl, id)                               |
|    return 1  // acquired                                                |
|  end                                                                    |
|  return 0    // at capacity, try later                                  |
|                                                                         |
|  // Release                                                             |
|  ZREM semaphore:{resource} {holder_id}                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.19: REDIS USE CASES CHEAT SHEET

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REDIS USE CASES — COMPLETE REFERENCE                                   |
|  =====================================                                  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  | Use Case            | Data Structure  | Key Pattern               |  |
|  |---------------------|-----------------|---------------------------|  |
|  | Cache               | String/Hash     | cache:{entity}:{id}       |  |
|  | Session Store       | Hash            | session:{session_id}      |  |
|  | Rate Limiter        | String (INCR)   | rate:{ip}:{window}        |  |
|  | Distributed Lock    | String (SETNX)  | lock:{resource}           |  |
|  | Leaderboard         | Sorted Set      | leaderboard:{game}        |  |
|  | Delay Queue         | Sorted Set      | delay_queue:{type}        |  |
|  | Priority Queue      | Sorted Set      | priority:{queue}          |  |
|  | Idempotency Store   | String (SETNX)  | idempotency:{key}         |  |
|  | Online Presence     | String/Bitmap   | online:{user_id}          |  |
|  | Inventory Counter   | String (DECR)   | inventory:{sku}           |  |
|  | Geospatial Search   | Geo (ZSET)      | locations:{type}          |  |
|  | Bloom Filter        | BF (module)     | bloom:{purpose}           |  |
|  | Feature Flags       | String/Set      | feature:{flag_name}       |  |
|  | Pub/Sub Notify      | Pub/Sub         | channel:{topic}           |  |
|  | Message Queue       | Stream/List     | stream:{queue_name}       |  |
|  | Semaphore           | Sorted Set      | semaphore:{resource}      |  |
|  | Counting (unique)   | HyperLogLog     | hll:{metric}:{window}     |  |
|  | Bit flags per user  | Bitmap          | features:{user_id}        |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  INTERVIEW TIP:                                                         |
|  "Redis is my Swiss Army knife. For caching I use Strings with TTL,     |
|   for rate limiting INCR with expiry, for leaderboards Sorted Sets,     |
|   for distributed locks SETNX with TTL, for delay queues ZSET with      |
|   timestamp scores, for flash sales Lua scripts with atomic DECR,       |
|   for nearby search GEOSEARCH, and for dedup Bloom filters. The key     |
|   is matching the use case to the right Redis data structure."          |
|                                                                         |
+-------------------------------------------------------------------------+
```
