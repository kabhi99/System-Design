# Production Issues & Solutions — Interview Ready

> These are real-world production scenarios that interviewers love to ask:
> "Tell me about a production issue you've debugged" or "What would you do if X happens?"
> Organized by category. Each issue follows: **Symptom → Root Cause → Solution → Prevention**.

---

# 1. DATABASE ISSUES

---

## 1.1 Database Connection Pool Exhaustion

**Symptom**: API latency spikes from 50ms to 10s+, then 5xx errors. DB shows "too many connections". Some requests succeed, most time out.

**Root Cause**: A slow downstream service (e.g., payment gateway) caused request threads to hang for 30s each. Each hanging thread held a DB connection. Pool of 50 connections exhausted in seconds. New requests queued, waiting for a connection → cascading timeout.

**Timeline**:
```
Payment API slows from 200ms → 30s
  → Request threads hold DB connections for 30s instead of 50ms
  → 50 connections × 30s = only 1.6 req/sec throughput (was 1000 req/sec)
  → Connection pool exhausted in seconds
  → All new requests fail with "unable to acquire connection"
  → Entire service goes down, even endpoints that don't use payments
```

**Solution (Immediate)**:
1. Restart application servers (releases connections)
2. Add circuit breaker on payment calls (fail fast at 2s instead of hanging for 30s)
3. Increase connection pool temporarily

**Solution (Permanent)**:
```
1. Circuit Breaker: Open after 5 failures in 10s → fail fast for 30s → half-open test
2. Separate connection pools per use case:
   - Read pool: 30 connections (for product listings, search)
   - Write pool: 15 connections (for orders, payments)
   - If write pool exhausts, reads still work
3. Connection timeout: 3s max wait for connection (fail fast, don't queue forever)
4. Bulkhead pattern: Isolate thread pools per downstream service
```

**Prevention**: Monitor `active_connections / max_connections` ratio. Alert at 70%.

---

## 1.2 Slow Query Takes Down the Database

**Symptom**: CPU at 100% on DB primary. All queries slow. Application-wide latency spike.

**Root Cause**: A developer deployed a new report query without proper indexing. Query did a full table scan on a 500M row table. Held locks, consumed all CPU, starved every other query.

**The Query**:
```sql
-- BEFORE (no index on status + created_at)
SELECT * FROM orders WHERE status = 'pending' AND created_at > '2025-01-01'
-- Full table scan: 500M rows, 45 minutes, locks entire table
```

**Solution (Immediate)**:
1. `SELECT pg_terminate_backend(pid)` — kill the runaway query
2. Identify the query: `SELECT * FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC`

**Solution (Permanent)**:
```sql
-- Add composite index (leftmost prefix matches the WHERE clause)
CREATE INDEX CONCURRENTLY idx_orders_status_created ON orders(status, created_at);

-- AFTER: Index scan, 200ms, no locks
```

**Prevention**:
- `statement_timeout = '30s'` — auto-kill queries exceeding 30s
- Query review in PR process — EXPLAIN ANALYZE required for new queries
- Read replicas for analytics/reports — never run heavy queries on primary
- `pg_stat_statements` to track slowest queries continuously

---

## 1.3 Deadlock Between Two Services

**Symptom**: Two API endpoints intermittently hang for exactly 30s (deadlock timeout), then return 500. Happens more during peak traffic.

**Root Cause**: Order service and Inventory service update the same rows in opposite order.

```
Transaction A (Checkout):          Transaction B (Inventory Sync):
1. Lock order #123                 1. Lock product #456
2. Lock product #456  ← WAITS     2. Lock order #123  ← WAITS
   (held by B)                        (held by A)
         ↓                                  ↓
      DEADLOCK — both waiting for each other
```

**Solution**:
```
1. Consistent lock ordering: ALWAYS lock in the same order
   - Rule: Lock by table name alphabetically, then by ID ascending
   - Both transactions: Lock order first, then product

2. Advisory locks with timeout:
   SELECT pg_advisory_xact_lock(hashtext('order_123'));
   -- If can't acquire in 5s, abort and retry

3. Optimistic locking (preferred for low contention):
   UPDATE orders SET status = 'confirmed', version = version + 1
   WHERE id = 123 AND version = 5;
   -- If 0 rows updated → someone else changed it → retry
```

**Prevention**: Monitor `pg_stat_activity` for `wait_event = 'Lock'`. Alert on deadlock count > 0 per minute.

---

## 1.4 Replication Lag Causes Stale Reads

**Symptom**: User creates an order, gets redirected to order details page, sees "Order not found" (404). Refreshing 2 seconds later works fine.

**Root Cause**: Write goes to primary, but the read-after-write hits a replica that hasn't received the change yet (replication lag = 500ms-2s).

```
User: POST /orders → Primary (writes order #789)
User: GET /orders/789 → Replica (hasn't replicated yet) → 404!
User: refreshes → Replica (now has it) → 200 OK
```

**Solution**:
```
1. Read-your-writes consistency:
   - After a write, set a cookie/header with the write timestamp
   - On next read, if timestamp < replication_lag, route to primary
   - Otherwise, safe to read from replica

2. Sticky reads for critical flows:
   - POST /orders returns the order data directly (no redirect + GET)
   - Or: route the immediate GET to primary for 5 seconds after write

3. Synchronous replication for critical tables:
   - Orders, payments: sync replication (wait for 1 replica ACK)
   - Analytics, logs: async replication (lag is OK)

4. Causal consistency tokens:
   - Write returns a LSN (Log Sequence Number)
   - Read sends LSN → replica waits until it reaches that LSN before responding
```

**Prevention**: Monitor replication lag. Alert at > 1s. Grafana dashboard showing lag per replica.

---

## 1.5 Database Disk Full — Writes Fail

**Symptom**: All writes fail with "No space left on device". Reads still work. Service partially down.

**Root Cause**: Forgot to set up log rotation on WAL (Write-Ahead Log). Also, a large table had no partition pruning — old data never cleaned up.

**Solution (Immediate)**:
1. Delete old WAL files / archived logs to free space
2. `VACUUM FULL` on bloated tables (but this locks the table — use off-peak)
3. Expand disk (cloud: resize EBS volume, takes 1 minute)

**Solution (Permanent)**:
```
1. Partition tables by date:
   CREATE TABLE orders PARTITION BY RANGE (created_at);
   -- Drop old partitions: ALTER TABLE orders DETACH PARTITION orders_2023;

2. WAL archiving + cleanup:
   - Archive WAL to S3 for point-in-time recovery
   - Delete local WAL older than 24 hours

3. Autovacuum tuning:
   - autovacuum_vacuum_scale_factor = 0.01 (vacuum after 1% changes, not default 20%)
   - Track dead tuple count

4. Disk usage monitoring:
   - Alert at 70% disk usage
   - Auto-expand disk at 80%
```

---

# 2. CACHE ISSUES

---

## 2.1 Cache Stampede (Thundering Herd)

**Symptom**: Every few hours, database CPU spikes to 100% for 30 seconds, then returns to normal. Correlates with TTL expiry of popular cache keys.

**Root Cause**: A hot cache key (e.g., homepage product list, viewed by 10K users/sec) expires. All 10K requests simultaneously miss cache and hit the database.

```
Normal:     Cache HIT → Redis → 1ms response (10K req/sec, 0 DB load)
TTL expires: Cache MISS → 10,000 concurrent requests → DB → 💥
```

**Solution**:
```
1. Mutex / distributed lock (most common):
   if cache.miss(key):
       if redis.set(key + ":lock", "1", NX, EX=5):  # only 1 winner
           value = db.query()
           cache.set(key, value, TTL=3600)
           redis.del(key + ":lock")
       else:
           sleep(50ms)  # wait for the winner to populate cache
           retry()

2. Staggered TTL (prevent synchronized expiry):
   TTL = base_ttl + random(0, 300)  # 1 hour ± 5 minutes
   
3. Background refresh (best for hot keys):
   - TTL = 1 hour, but refresh in background at 50 minutes
   - Cache never actually expires — always warm
   - Requires a refresh scheduler

4. Probabilistic early expiry (XFetch):
   remaining_ttl = cache.ttl(key)
   if remaining_ttl < DELTA * log(random()):
       refresh_in_background()
```

**Prevention**: Track cache hit rate. Identify hot keys. Pre-warm cache after deployments.

---

## 2.2 Cache Penetration (Non-Existent Keys)

**Symptom**: Database load high despite low traffic. Cache hit rate is 0% for certain request patterns. Logs show millions of lookups for IDs that don't exist.

**Root Cause**: Attacker (or bug) sends requests for user IDs that don't exist (e.g., `user_-1`, `user_999999999`). Cache always misses (nothing to cache), every request hits DB.

```
GET /user/999999999 → Cache MISS → DB query → NULL → don't cache → repeat
GET /user/999999998 → Cache MISS → DB query → NULL → repeat
... millions of these → DB overloaded
```

**Solution**:
```
1. Cache null results with short TTL:
   value = db.get(user_id)
   if value is None:
       cache.set(f"user:{user_id}", "NULL", TTL=60)  # cache "not found" for 1 min
   
2. Bloom filter (for massive scale):
   - Maintain a Bloom filter of all valid user IDs
   - Check Bloom filter BEFORE cache/DB
   - If "definitely not in set" → return 404 immediately, no cache/DB hit
   - False positive rate: ~1% at 10 bits per element
   
3. Input validation:
   - Reject obviously invalid IDs at API gateway (negative, too large, wrong format)
   - Rate limit per IP for 404 responses
```

**Prevention**: Monitor 404 rate per endpoint. Spike in 404s = likely attack or bug.

---

## 2.3 Hot Key Problem

**Symptom**: One Redis node at 100% CPU while others are idle. That node's latency spikes, affecting all keys on that shard.

**Root Cause**: A viral celebrity tweet stored on one Redis shard. 500K reads/sec on a single key overwhelming one node.

**Solution**:
```
1. Local L1 cache (in-memory, per app server):
   - Cache hot keys in process memory (Go map, Java ConcurrentHashMap)
   - TTL = 1-5 seconds (very short, but absorbs 99% of reads)
   - 50 app servers × 1 local cache each = 50x load reduction on Redis

2. Key replication (read from random replica):
   - Store as: celebrity_tweet:1, celebrity_tweet:2, ... celebrity_tweet:10
   - Read from: celebrity_tweet:{random(1,10)}
   - Spreads load across 10 Redis slots/nodes

3. Request coalescing (singleflight pattern):
   - 1000 concurrent requests for same key → only 1 fetches from Redis
   - Other 999 wait and get the same result
   - Go: sync.SingleFlight. Java: custom with CompletableFuture
```

---

## 2.4 Cache Avalanche (Mass Expiry)

**Symptom**: Database overwhelmed at exactly midnight every day. Correlates with cache warm-up after a deployment or mass TTL expiry.

**Root Cause**: All cache keys set with same TTL (e.g., 24 hours) at the same time. They all expire simultaneously.

**Solution**:
```
1. Jittered TTL:
   TTL = base_ttl + random(0, base_ttl * 0.1)  # ±10% randomization
   
2. Staggered warm-up after deployment:
   - Don't invalidate all keys at once
   - Warm cache gradually (10% of keys every minute)

3. Multi-layer cache:
   - L1: Local (5s TTL) → L2: Redis (1hr TTL) → DB
   - Even if Redis cache expires, L1 absorbs the spike
   
4. Rate limiting DB queries:
   - If cache misses exceed threshold, queue the DB queries
   - Serve stale data for a few seconds while backfilling
```

---

# 3. SERVICE & API ISSUES

---

## 3.1 Cascading Failure (One Service Takes Down Everything)

**Symptom**: Payment service goes down. Then order service slows. Then product service. Then API gateway. Entire platform is down.

**Root Cause**: Order service calls payment service synchronously with 30s timeout. Payment is down → order threads hang for 30s each → thread pool exhausted → order service can't serve ANY request (even those that don't need payment) → services that depend on order service also fail → cascade.

```
Payment ✗ → Order hangs → Product hangs → API Gateway hangs → User sees 503
```

**Solution**:
```
1. Circuit Breaker (stop calling the dead service):
   CLOSED → [5 failures in 10s] → OPEN (fail instantly for 30s)
   OPEN → [30s passes] → HALF-OPEN (allow 1 test request)
   HALF-OPEN → [success] → CLOSED  /  [failure] → OPEN again
   
   Result: Payment is down but order service returns graceful error in 1ms instead of hanging 30s

2. Bulkhead (isolate failure):
   - Separate thread pool for payment calls (10 threads)
   - Separate thread pool for inventory calls (10 threads)  
   - Separate thread pool for everything else (30 threads)
   - Payment exhausts its 10 threads → other pools unaffected

3. Timeout + Retry with backoff:
   - Connection timeout: 1s (don't wait forever to connect)
   - Read timeout: 3s (don't wait forever for response)
   - Retry: 3 attempts with exponential backoff (1s, 2s, 4s) + jitter
   - Total budget: 10s max per external call

4. Graceful degradation:
   - Payment down? Accept order, process payment async later
   - Recommendation service down? Show popular items instead
   - Search down? Show category browsing
   - NEVER let a non-critical service take down the critical path
```

**Prevention**: Dependency map showing which services call which. Chaos engineering (Netflix Chaos Monkey) to test failure handling.

---

## 3.2 Thundering Herd After Service Restart

**Symptom**: Service crashes, auto-restarts, immediately crashes again. Restart loop.

**Root Cause**: Service goes down for 2 minutes. During that time, 100K requests queue up at the load balancer. When service restarts, all 100K requests hit it simultaneously → OOM → crash → repeat.

**Solution**:
```
1. Load balancer: Slow start / ramp-up
   - New server starts with weight 0
   - Gradually increase to full weight over 60 seconds
   - Prevents immediate flood

2. Rate limiting on startup:
   - Accept only 100 req/sec for first 30 seconds
   - Gradually increase to full capacity
   
3. Health check grace period:
   - Don't mark server as healthy until warmup complete
   - JVM needs time for JIT compilation, connection pool setup, cache warmup
   
4. Retry storm prevention:
   - Clients should use exponential backoff with jitter
   - Without jitter, all clients retry at the exact same time
   
   BAD:  retry at 1s, 2s, 4s (all clients synchronized)
   GOOD: retry at 1s±0.5s, 2s±1s, 4s±2s (clients spread out)
```

---

## 3.3 Memory Leak — Slow Death Over Days

**Symptom**: Service works fine after deploy. Latency gradually increases over 3-5 days. Memory usage grows linearly. Eventually OOM kill.

**Root Cause**: Event listeners registered but never deregistered. Or: unbounded in-memory cache without eviction. Or: connection objects created but never closed.

**Common Causes**:
```
1. Unbounded cache: map grows forever (no TTL, no max size)
   FIX: Use LRU cache with max size, or cache library with eviction

2. Connection leak: DB/HTTP connections opened but not closed on error path
   FIX: try-with-resources (Java), defer conn.Close() (Go), context manager (Python)

3. Event listener leak: Register listener on every request, never unregister
   FIX: Register once at startup, or weak references

4. Large object in session: Storing full user profile (with image) in HTTP session
   FIX: Store only user_id in session, fetch profile from cache/DB
```

**Detection**: Monitor RSS (Resident Set Size) memory over time. If it only goes up, never down — it's a leak. Heap dump analysis (Java: jmap + MAT, Go: pprof).

---

## 3.4 Duplicate Processing (Missing Idempotency)

**Symptom**: Customer charged twice. Or inventory decremented twice. Or notification sent multiple times.

**Root Cause**: Network timeout between service and payment gateway. Service didn't get a response, so it retried. But the first request actually succeeded — now the customer is charged twice.

```
Service → Payment Gateway: "Charge $100" (request #1)
         ... network timeout (no response received) ...
Service → Payment Gateway: "Charge $100" (request #2, retry)
Gateway processes BOTH → Customer charged $200
```

**Solution**:
```
1. Idempotency key on every state-changing API:
   POST /payments
   Idempotency-Key: order_123_payment_1
   
   Server: SETNX idempotency:order_123_payment_1 → first request wins
   Retry: same key → return cached response (no reprocessing)

2. Database unique constraint as safety net:
   CREATE UNIQUE INDEX idx_payments_idempotency ON payments(idempotency_key);
   -- Even if Redis loses the key, DB prevents duplicate insert

3. Status check before retry:
   - Before retrying, check: "Did the first request actually succeed?"
   - GET /payments?order_id=123 → if exists, don't retry

4. At-least-once + deduplication:
   - Consumer tracks processed message IDs in a set
   - On receive: if message_id already processed → skip
   - Use Redis SET or DB table for tracking
```

---

# 4. INFRASTRUCTURE ISSUES

---

## 4.1 DNS Propagation Causes Partial Outage

**Symptom**: After DNS change, 80% of users reach the new service but 20% still hit the old (decommissioned) server. Issues last for hours.

**Root Cause**: DNS TTL was set to 24 hours. ISPs and client browsers cache the old IP. Even after update, cached entries take up to 24 hours to expire.

**Solution**:
```
1. Pre-migration: Lower TTL to 60 seconds, wait 24 hours for old TTL to expire
2. Make the DNS change
3. Both old AND new servers should be running during transition
4. After 24 hours: safe to decommission old server
5. Restore TTL to normal (300s-3600s)

Better approach: Use a reverse proxy / load balancer with a stable IP
- DNS always points to LB IP (never changes)
- LB routes to backend servers (change backends without DNS change)
```

---

## 4.2 SSL Certificate Expiry

**Symptom**: At 3 AM, all HTTPS traffic starts failing. Browsers show "Your connection is not private". Mobile apps crash with SSL handshake errors.

**Root Cause**: TLS certificate expired. No one noticed the renewal reminder emails.

**Solution (Immediate)**: Renew certificate manually and deploy.

**Prevention**:
```
1. Auto-renewal: Use Let's Encrypt + certbot (auto-renews 30 days before expiry)
2. AWS ACM: Fully managed certificates, auto-renews, zero effort
3. Monitoring: Alert when certificate expires in < 30 days
   - curl -s "https://yoursite.com" | openssl x509 -noout -dates
4. Multiple notification channels: Email + Slack + PagerDuty
5. Runbook: Step-by-step certificate renewal process documented
```

---

## 4.3 Noisy Neighbor (Shared Infrastructure)

**Symptom**: Service latency randomly spikes 5-10x at unpredictable times. No correlation with your traffic patterns.

**Root Cause**: Another team's batch job runs on the same database/Redis/Kafka cluster. Their heavy workload consumes shared resources (CPU, IOPS, network).

```
Your service:   ████░░░░  normal load
Batch job:      ████████████████████  starts at random times
Shared DB CPU:  ████████████████████████  100% → your queries slow
```

**Solution**:
```
1. Resource isolation:
   - Separate DB instances for OLTP (your service) and OLAP (batch jobs)
   - Dedicated Redis instances per critical service
   - Kafka: Separate topics with dedicated consumer groups + quotas

2. Resource quotas:
   - Kubernetes: resource limits per pod (CPU/memory)
   - Database: pg_bouncer with per-pool connection limits
   - Kafka: client quotas (bytes/sec per client)

3. Time-based isolation:
   - Batch jobs only run during off-peak hours (2-6 AM)
   - OR: use read replicas for batch jobs (never touch primary)

4. Rate limiting at infrastructure level:
   - DB proxy limits queries per second per service
   - Prevents any single service from monopolizing shared resources
```

---

## 4.4 Deployment Causes Outage (Bad Deploy)

**Symptom**: Immediately after deployment, error rate jumps from 0.1% to 50%. Users see errors.

**Root Cause**: New code has a bug that only manifests in production (different config, data, or traffic pattern than staging).

**Solution (Immediate)**: Rollback to previous version.

**Prevention**:
```
1. Canary deployment:
   Deploy to 1 server → watch for 10 minutes → 5% traffic → 25% → 50% → 100%
   Auto-rollback if error rate > 1% or p99 latency > 2x baseline

2. Blue-Green deployment:
   Two identical environments. Route traffic to green (new).
   If bad → instantly switch back to blue (old). Zero downtime.

3. Feature flags:
   Deploy code but keep feature disabled.
   Enable for 1% of users → monitor → gradually enable for all.
   If broken → disable flag (no redeploy needed).

4. Automated rollback:
   if error_rate > threshold OR p99_latency > 2x_baseline:
       auto_rollback()
       alert_oncall()
       
5. Database migration safety:
   - Never deploy code that REQUIRES the new schema
   - Deploy schema change first (backward compatible)
   - Then deploy code that uses new schema
   - Then remove old schema (3-step process)
```

---

# 5. DISTRIBUTED SYSTEM ISSUES

---

## 5.1 Split Brain (Two Leaders)

**Symptom**: After a network partition heals, data is inconsistent. Some users see different data depending on which server they hit. Data loss or duplicates discovered.

**Root Cause**: Network partition isolates the leader from followers. Followers elect a new leader. Now two leaders accept writes independently. When partition heals, conflicting writes exist.

```
Before partition:  Leader → Follower1, Follower2
During partition:  Leader (isolated, still accepting writes)
                   Follower1 (elected new leader, also accepting writes)
After partition:   Two different versions of data — CONFLICT
```

**Solution**:
```
1. Quorum-based writes (prevent split brain):
   - Need majority (N/2 + 1) acknowledgments to commit
   - With 3 nodes: need 2 ACKs. Isolated leader can't get quorum → stops accepting writes
   - Old leader detects it can't reach quorum → steps down to follower

2. Fencing tokens:
   - Each leader election assigns a monotonically increasing epoch number
   - Storage layer rejects writes from old epochs
   - Old leader's writes are rejected even if it doesn't know it's been replaced

3. STONITH (Shoot The Other Node In The Head):
   - When new leader is elected, forcefully shut down old leader
   - Prevents two leaders from ever coexisting
   - Used in traditional database HA (Pacemaker + DRBD)

4. Consensus protocols (Raft, Paxos):
   - Guarantee only one leader per term
   - etcd, ZooKeeper, CockroachDB use this
```

---

## 5.2 Message Queue Backlog — Consumer Can't Keep Up

**Symptom**: Kafka consumer lag growing continuously. Messages taking minutes to process instead of milliseconds. Downstream effects: delayed notifications, stale search results.

**Root Cause**: New feature increased message size 10x (added full product details instead of just product_id). Consumer processing time went from 5ms to 50ms per message. Consumer can no longer keep up with producer throughput.

```
Producer: 10,000 msg/sec
Consumer (before): 5ms/msg × 10 partitions × 1 consumer/partition = 20,000 msg/sec ✓
Consumer (after):  50ms/msg × 10 partitions × 1 consumer/partition = 2,000 msg/sec ✗
Lag grows at: 8,000 msg/sec → 480K messages behind per minute
```

**Solution (Immediate)**:
```
1. Scale consumers: Add more consumer instances (up to partition count)
   - 10 partitions → max 10 consumers in one group
   - Need more? Add partitions (but can't easily reduce later)

2. Batch processing: Process messages in batches of 100 instead of one-by-one
```

**Solution (Permanent)**:
```
1. Slim messages: Send only IDs + metadata, not full payloads
   {product_id: 123, action: "updated"}  // not the entire product object
   Consumer fetches full data if needed

2. Increase partitions: More partitions = more parallelism
   Before: 10 partitions, max 10 consumers
   After: 50 partitions, max 50 consumers → 5x throughput

3. Async processing inside consumer:
   - Receive message → dispatch to thread pool → acknowledge
   - But: must handle ordering carefully

4. Backpressure: If consumer is overwhelmed, signal producer to slow down
   - Or: separate fast-lane (real-time) and slow-lane (batch) topics
```

**Prevention**: Monitor consumer lag as a first-class metric. Alert when lag > 10,000 messages or lag growing for > 5 minutes.

---

## 5.3 Clock Skew Causes Ordering Issues

**Symptom**: Chat messages appear out of order. Audit logs show events in wrong sequence. "Last write wins" conflict resolution silently drops newer writes.

**Root Cause**: Server A's clock is 5 seconds ahead of Server B. Message timestamped on Server A at 12:00:05, message on Server B at 12:00:02. But Server B's message was actually sent AFTER Server A's. LWW picks Server A's message as "latest" — wrong.

**Solution**:
```
1. NTP synchronization: Ensure all servers sync with same NTP source
   - But NTP only guarantees ~10ms accuracy, not enough for ordering

2. Logical clocks (Lamport timestamps):
   - Each event gets a counter, not a wall clock time
   - On send: counter++. On receive: counter = max(local, received) + 1
   - Guarantees causal ordering (if A happened before B, A's timestamp < B's)

3. Hybrid Logical Clocks (HLC):
   - Combines wall clock + logical counter
   - Used by CockroachDB, YugabyteDB
   - Gives you both causal ordering AND approximate real-world time

4. Sequence numbers per entity:
   - For chat: per-conversation sequence number in Redis (INCR)
   - Guaranteed ordering within a conversation regardless of clock skew
   
5. Single-writer per entity:
   - All messages for conversation X go through one server
   - That server assigns sequence numbers — no clock skew issue
```

---

## 5.4 Distributed Lock Expiry — Zombie Process

**Symptom**: Two workers process the same job simultaneously. Duplicate emails sent. Duplicate payments processed.

**Root Cause**: Worker A acquires a Redis lock (TTL = 30s). Worker A's processing takes 45s due to a GC pause or slow network call. Lock expires at 30s. Worker B acquires the now-available lock at 31s. Both A and B are now processing the same job.

```
0s:  Worker A acquires lock (TTL=30s)
0s:  Worker A starts processing...
30s: Lock expires (Worker A still processing due to GC pause)
31s: Worker B acquires lock, starts processing
45s: Worker A finishes — but Worker B is also processing!
     → Duplicate payment, duplicate email
```

**Solution**:
```
1. Fencing tokens (best solution):
   - Lock server issues token 33 to Worker A, token 34 to Worker B
   - Storage rejects writes with token < latest seen token
   - Worker A tries to write with token 33 → rejected (34 already seen)

2. Lock renewal (heartbeat):
   - Worker A renews lock every 10s (while processing)
   - If A crashes, lock expires naturally after 30s
   - If A is slow, renewal keeps the lock alive
   - Redisson (Java), Redsync (Go) do this automatically

3. Lock + lease pattern:
   - Check lock ownership BEFORE the final critical operation
   - Just before committing: "Is this lock still mine?"
   - Reduces (but doesn't eliminate) the vulnerability window

4. Idempotent operations:
   - Even if two workers process the same job, the result is the same
   - Payment: check idempotency key before charging
   - Email: check "already sent" flag before sending
```

---

# 6. SCALING ISSUES

---

## 6.1 Sudden Traffic Spike (Viral Event / Flash Sale)

**Symptom**: 10x traffic in 5 minutes. Auto-scaling too slow (takes 3-5 minutes to spin up new instances). Users see 503 errors during the ramp.

**Solution**:
```
1. Pre-scaling: If event is known (flash sale, product launch)
   - Scale up 2 hours before
   - Pre-warm caches, connection pools

2. Rate limiting + queuing:
   - API gateway enforces max req/sec
   - Excess requests get "virtual waiting room" (queue position shown to user)
   - Better UX than 503 errors

3. Static content offload:
   - Serve as much as possible from CDN (product images, JS, CSS)
   - CDN can absorb 100x spike without any backend changes

4. Graceful degradation:
   - Disable non-essential features under load
   - Disable recommendations, recently viewed, personalization
   - Show cached versions of pages instead of real-time
   
5. Auto-scaling with aggressive settings:
   - Scale-up trigger: CPU > 50% (not 80%)
   - Cool-down: 60 seconds (not 300)
   - Pre-provisioned warm pool of instances (already booted, just need to join LB)
```

---

## 6.2 Database Writes Outgrowing Single Node

**Symptom**: Write latency increasing week over week. WAL write queue growing. Approaching IOPS limits of the disk.

**Solution (Ordered by Effort)**:
```
1. Optimize writes first (cheapest):
   - Batch inserts (1000 rows per INSERT instead of 1)
   - Remove unnecessary indexes (each index = extra write)
   - Use UNLOGGED tables for non-critical data (no WAL overhead)

2. Write-behind caching:
   - Buffer writes in Redis → flush to DB in batches every 100ms
   - Great for counters, analytics, non-critical updates

3. CQRS (separate read and write models):
   - Writes go to normalized DB (optimized for write)
   - Reads go to denormalized read replicas (optimized for queries)
   - Sync via CDC or event streaming

4. Sharding (last resort — high complexity):
   - Shard by tenant_id (multi-tenant SaaS) or user_id
   - Each shard handles 1/N of total writes
   - Cross-shard queries become expensive → denormalize
```

---

# QUICK REFERENCE — INCIDENT RESPONSE TEMPLATE

```
1. DETECT (< 1 min)
   - Automated alert fires (PagerDuty / OpsGenie)
   - Metrics: error rate, latency p99, queue depth, CPU/memory

2. TRIAGE (< 5 min)
   - What's the blast radius? (one endpoint? one service? everything?)
   - When did it start? (correlate with deploys, config changes, traffic spikes)
   - Is it getting worse or stable?

3. MITIGATE (< 15 min)
   - Can we rollback? (last deploy < 1 hour ago → rollback)
   - Can we scale? (traffic spike → add instances)
   - Can we shed load? (rate limit, disable non-critical features)
   - Can we failover? (primary DB down → promote replica)

4. FIX (< 1 hour for P1)
   - Root cause analysis while mitigation holds
   - Deploy fix or permanent configuration change

5. POST-MORTEM (within 48 hours)
   - Timeline of events
   - Root cause (not "human error" — what systemic failure allowed this?)
   - Action items with owners and deadlines
   - What monitoring/alerts should we add?
```

## What Interviewers Want to Hear

| Signal | Example Statement |
|--------|-------------------|
| **Systematic debugging** | "First I'd check metrics dashboards — error rate, latency, CPU. Then correlate with recent deploys and traffic patterns" |
| **Immediate mitigation** | "Rollback first, investigate later. Restoring service is priority over finding root cause" |
| **Blast radius thinking** | "Is this affecting all users or just a segment? Can we isolate the impact?" |
| **Prevention mindset** | "After fixing, I'd add monitoring for X and a circuit breaker on Y to prevent recurrence" |
| **Blameless culture** | "The question isn't who made the mistake, but what systemic gap allowed it to reach production" |
