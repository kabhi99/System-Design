# REDIS
*Chapter 2: Advanced Features*

This chapter covers Redis features beyond basic data structures --
transactions, Lua scripting, pub/sub, pipelining, and modules.

## SECTION 2.1: TRANSACTIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MULTI / EXEC = Group commands into an atomic batch.                    |
|                                                                         |
|  MULTI                              -- start transaction                |
|  SET account:A 500                                                      |
|  SET account:B 300                                                      |
|  DECRBY account:A 100                                                   |
|  INCRBY account:B 100                                                   |
|  EXEC                               -- execute all atomically           |
|                                                                         |
|  * All commands between MULTI and EXEC are queued                       |
|  * EXEC runs them all atomically (no other client interleaves)          |
|  * DISCARD cancels the transaction                                      |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  WATCH = Optimistic locking                                             |
|                                                                         |
|  WATCH account:A                    -- watch for changes                |
|  val = GET account:A                -- read current value               |
|  MULTI                                                                  |
|  SET account:A (val - 100)          -- modify                           |
|  EXEC                               -- fails if account:A changed!      |
|                                                                         |
|  If another client modified account:A between WATCH and EXEC,           |
|  EXEC returns nil (transaction aborted). Retry the whole thing.         |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  LIMITATIONS:                                                           |
|  * NO rollback on command errors (partial execution possible)           |
|  * Cannot use results of one command in the next (no variables)         |
|  * For complex logic, use Lua scripts instead                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.2: LUA SCRIPTING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Lua scripts execute ATOMICALLY on the Redis server.                    |
|  No other command runs while a script is executing.                     |
|                                                                         |
|  EVAL "return redis.call('GET', KEYS[1])" 1 mykey                       |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  EXAMPLE: Rate limiter (atomic check + increment)                       |
|                                                                         |
|  local current = redis.call('INCR', KEYS[1])                            |
|  if current == 1 then                                                   |
|      redis.call('EXPIRE', KEYS[1], ARGV[1])                             |
|  end                                                                    |
|  if current > tonumber(ARGV[2]) then                                    |
|      return 0  -- rate limited                                          |
|  end                                                                    |
|  return 1  -- allowed                                                   |
|                                                                         |
|  EVAL script 1 ratelimit:user:123 60 100                                |
|  (key=ratelimit:user:123, window=60s, limit=100)                        |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  EXAMPLE: Distributed lock with safe release                            |
|                                                                         |
|  -- Only release if we own the lock (compare value)                     |
|  if redis.call('GET', KEYS[1]) == ARGV[1] then                          |
|      return redis.call('DEL', KEYS[1])                                  |
|  else                                                                   |
|      return 0                                                           |
|  end                                                                    |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  BEST PRACTICES:                                                        |
|  * Use EVALSHA (cached script hash) for repeated scripts                |
|  * Keep scripts short -- they block ALL other commands                  |
|  * Pass keys via KEYS[] (required for cluster compatibility)            |
|  * Use ARGV[] for arguments                                             |
|  * Redis Functions (7.0+) replace EVAL with persistent functions        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.3: PIPELINING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PIPELINING = Send multiple commands without waiting for each reply.    |
|                                                                         |
|  WITHOUT PIPELINE (round-trip per command):                             |
|                                                                         |
|  Client          Redis                                                  |
|    |-- SET k1 v1 -->|                                                   |
|    |<-- OK ---------|  RTT ~0.5ms                                       |
|    |-- SET k2 v2 -->|                                                   |
|    |<-- OK ---------|  RTT ~0.5ms                                       |
|    |-- SET k3 v3 -->|                                                   |
|    |<-- OK ---------|  RTT ~0.5ms                                       |
|    Total: 3 x 0.5ms = 1.5ms for 3 commands                              |
|                                                                         |
|  WITH PIPELINE (batch all, one round-trip):                             |
|                                                                         |
|  Client          Redis                                                  |
|    |-- SET k1 v1 -->|                                                   |
|    |-- SET k2 v2 -->|  (no wait)                                        |
|    |-- SET k3 v3 -->|  (no wait)                                        |
|    |<-- OK ---------|                                                   |
|    |<-- OK ---------|  All replies at once                              |
|    |<-- OK ---------|                                                   |
|    Total: 1 x 0.5ms = 0.5ms for 3 commands                              |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  THROUGHPUT:                                                            |
|  * Without pipeline: ~50K ops/sec (bottlenecked by RTT)                 |
|  * With pipeline (batch 100): ~500K ops/sec                             |
|  * 10x improvement by eliminating round-trip wait                       |
|                                                                         |
|  IMPORTANT:                                                             |
|  * Pipeline is NOT atomic (other clients can interleave)                |
|  * For atomicity, use MULTI/EXEC or Lua scripts                         |
|  * Don't pipeline too many commands (memory buffer on server)           |
|  * Batch size 100-1000 is typical sweet spot                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.4: PUB/SUB

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PUB/SUB = Publish/Subscribe messaging built into Redis.                |
|                                                                         |
|  SUBSCRIBE chat:room:1           -- subscribe to a channel              |
|  PUBLISH chat:room:1 "hello!"   -- publish to subscribers               |
|  PSUBSCRIBE chat:*               -- pattern subscribe (wildcard)        |
|                                                                         |
|  Publisher                 Redis              Subscribers               |
|     |                       |                     |                     |
|     |-- PUBLISH "hello" --->|                     |                     |
|     |                       |-- "hello" --------->| (Subscriber A)      |
|     |                       |-- "hello" --------->| (Subscriber B)      |
|     |                       |-- "hello" --------->| (Subscriber C)      |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  LIMITATIONS:                                                           |
|  * Fire-and-forget: if subscriber is offline, message is LOST           |
|  * No message persistence or replay                                     |
|  * No acknowledgment mechanism                                          |
|  * No consumer groups (every subscriber gets every message)             |
|  * Memory pressure if subscribers are slow                              |
|                                                                         |
|  FOR RELIABLE MESSAGING: Use Redis Streams instead of Pub/Sub.          |
|  Streams offer persistence, consumer groups, and acknowledgments.       |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  USE CASES FOR PUB/SUB:                                                 |
|  * Real-time notifications (if some loss is acceptable)                 |
|  * Chat rooms (ephemeral messages)                                      |
|  * Cache invalidation broadcast                                         |
|  * Config change notifications across services                          |
|  * WebSocket event distribution                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.5: DISTRIBUTED LOCKS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SIMPLE LOCK (single Redis instance):                                   |
|                                                                         |
|  ACQUIRE:                                                               |
|  SET lock:order:456 "owner-uuid" NX EX 30                               |
|  * NX = only set if not exists (atomic check-and-set)                   |
|  * EX 30 = auto-expire in 30 seconds (safety net)                       |
|  * "owner-uuid" = unique value to identify lock owner                   |
|                                                                         |
|  RELEASE (Lua script for safety):                                       |
|  if redis.call('GET', KEYS[1]) == ARGV[1] then                          |
|      return redis.call('DEL', KEYS[1])                                  |
|  end                                                                    |
|  * Only delete if WE own the lock (prevent releasing others' locks)     |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  REDLOCK (distributed lock across multiple Redis instances):            |
|                                                                         |
|  For when a single Redis instance is a SPOF:                            |
|                                                                         |
|  1. Get current time in milliseconds                                    |
|  2. Try to acquire lock on N independent Redis instances (N=5)          |
|  3. Lock acquired if: majority (>= 3/5) succeed AND                     |
|     total time < lock validity period                                   |
|  4. Actual lock validity = initial validity - acquisition time          |
|  5. Release: send DEL to ALL instances                                  |
|                                                                         |
|  +-------+ +-------+ +-------+ +-------+ +-------+                      |
|  |Redis 1| |Redis 2| |Redis 3| |Redis 4| |Redis 5|                      |
|  |  OK   | |  OK   | |  OK   | | FAIL  | | FAIL  |                      |
|  +-------+ +-------+ +-------+ +-------+ +-------+                      |
|                                                                         |
|  3/5 succeeded = lock acquired (majority)                               |
|                                                                         |
|  CONTROVERSY: Martin Kleppmann argued Redlock has flaws                 |
|  (GC pauses, clock drift). Use fencing tokens for critical systems.     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.6: REDIS MODULES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Redis Modules extend Redis with new data types and commands.           |
|                                                                         |
|  +-------------------+----------------------------------------------+   |
|  | Module            | What It Does                                 |   |
|  +-------------------+----------------------------------------------+   |
|  | RedisJSON         | Native JSON document storage and querying    |   |
|  | RediSearch        | Full-text search engine built on Redis       |   |
|  | RedisTimeSeries   | Time-series data (IoT, metrics, monitoring)  |   |
|  | RedisBloom        | Bloom filters, Cuckoo filters, Count-Min     |   |
|  | RedisGraph        | Graph database (Cypher query language)       |   |
|  | RedisAI           | Model serving (TensorFlow, PyTorch)          |   |
|  +-------------------+----------------------------------------------+   |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  REDISJSON EXAMPLE:                                                     |
|                                                                         |
|  JSON.SET user:123 $ '{"name":"John","age":30,"city":"NYC"}'            |
|  JSON.GET user:123 $.name        > "John"                               |
|  JSON.NUMINCRBY user:123 $.age 1 > 31                                   |
|                                                                         |
|  Advantages over HASH:                                                  |
|  * Nested objects and arrays                                            |
|  * JSONPath queries                                                     |
|  * Atomic partial updates on nested fields                              |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  REDISBLOOM EXAMPLE:                                                    |
|                                                                         |
|  BF.ADD myfilter "element1"     -- add to bloom filter                  |
|  BF.EXISTS myfilter "element1"  > 1 (probably exists)                   |
|  BF.EXISTS myfilter "element2"  > 0 (definitely does not exist)         |
|                                                                         |
|  Use case: Check if username is taken before querying DB.               |
|  False positive possible, false negative impossible.                    |
|                                                                         |
+-------------------------------------------------------------------------+
```
