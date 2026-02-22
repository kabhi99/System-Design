# System Design Interview Notes - Prioritized by Probability

> **How to use**: Topics are ranked by interview probability. Tier 1 concepts appear in **every** interview. Tier 2 systems are the most commonly asked designs. Master Tier 1+2 first, then expand.

---

# TIER 1 — CORE FUNDAMENTALS (Asked in 90%+ Interviews)

These concepts are **not optional**. Every system design interview touches multiple Tier 1 topics. You won't design a system without discussing scaling, databases, caching, and load balancing.

---

## 1. Scalability [P: 95%]

**One-liner**: Horizontal scaling + stateless services = the foundation of every design.

### Must-Know

| Concept | Key Point |
|---------|-----------|
| **Vertical vs Horizontal** | Vertical = bigger machine (has a ceiling). Horizontal = more machines (infinite but adds complexity) |
| **Stateless Services** | Externalize state to Redis/DB. Any request → any server. JWTs for stateless auth |
| **AKF Scale Cube** | X-axis = clone (LB), Y-axis = split by function (microservices), Z-axis = split by data (sharding) |
| **Little's Law** | `Concurrent users = Arrival rate × Latency`. 5× latency spike = 5× more servers needed |

### Interview Power Moves
- "We'll keep services stateless and externalize session state to Redis for horizontal scaling"
- "Based on Little's Law, at 10K req/sec with 100ms latency, we need capacity for 1000 concurrent connections"
- When asked "how do you scale this?" → always think: **read replicas → caching → sharding → microservices**

---

## 2. Databases: SQL vs NoSQL [P: 95%]

**One-liner**: SQL for relationships + ACID. NoSQL for scale + flexible schema. This decision shapes everything.

### Decision Framework

| Choose SQL (PostgreSQL/MySQL) When | Choose NoSQL When |
|---|---|
| Complex relationships, JOINs needed | Simple access patterns (key-value, document) |
| ACID transactions required | Massive write throughput (100K+ writes/sec) |
| Data integrity is critical (payments) | Flexible/evolving schema |
| Moderate scale (<10TB single node) | Horizontal scale required from day one |

### SQL Essentials

| Topic | What to Say |
|-------|-------------|
| **Isolation Levels** | Read Committed (PG default) → Repeatable Read (MySQL default) → Serializable. Know: dirty reads, phantom reads, lost updates |
| **Indexing** | B-tree index speeds reads, slows writes. Composite indexes follow leftmost prefix rule. Covering index = no table lookup |
| **MVCC** | Readers don't block writers (PostgreSQL, MySQL InnoDB). Each transaction sees a consistent snapshot |
| **Optimistic vs Pessimistic Locking** | Optimistic = version column, detect conflict at commit (low contention). Pessimistic = lock early, prevent conflict (high contention) |

### NoSQL Categories — Know When to Pick Each

| Type | DB | Best For |
|------|-----|----------|
| Key-Value | Redis, DynamoDB | Sessions, caching, counters |
| Document | MongoDB | Product catalogs, CMS, flexible schema |
| Wide-Column | Cassandra | Time-series, IoT, high-volume writes |
| Graph | Neo4j | Social networks, recommendation engines |

### Interview Power Moves
- "For the order service I'd use PostgreSQL for ACID guarantees. For the product catalog, MongoDB gives us schema flexibility across different product categories"
- "We'll add a composite index on `(user_id, created_at)` to support the 'get recent orders' query efficiently"
- **Random UUIDs are terrible for B+Trees** — use UUIDv7/ULID/Snowflake IDs (time-ordered, sequential inserts)

---

## 3. Caching [P: 95%]

**One-liner**: Cache = 100x faster reads. Cache-aside + Redis is your default answer.

### Caching Strategies — Pick the Right One

| Strategy | How It Works | When to Use |
|----------|-------------|-------------|
| **Cache-Aside** (Lazy) | App checks cache → miss → fetch DB → populate cache | Most common. Read-heavy workloads |
| **Write-Through** | Write to cache AND DB synchronously | Need strong consistency. Accept write latency |
| **Write-Behind/Back** | Write to cache, async flush to DB | Max write speed. Accept risk of data loss |
| **Write-Around** | Write to DB, invalidate cache | Write-heavy, reads are infrequent |

### Cache Problems — Interviewers Love These

| Problem | What Happens | Solution |
|---------|-------------|----------|
| **Cache Stampede** | Hot key expires → 1000 requests hit DB simultaneously | Locking (one fetcher), staggered TTL, background refresh |
| **Cache Penetration** | Queries for non-existent data always miss cache | Bloom filter (reject impossible keys) or cache null with short TTL |
| **Cache Avalanche** | Many keys expire simultaneously → DB overload | Random TTL jitter (base ± random), staggered expiry |
| **Hot Key** | One key gets disproportionate traffic | Replicate hot key across multiple Redis nodes, local L1 cache |

### Interview Power Moves
- "We'll use cache-aside with Redis. 80/20 rule means caching 20% of data serves 80% of reads"
- "To prevent cache stampede on popular items, we'll use a mutex — only one request fetches from DB, others wait"
- **Redis stats**: 100K+ ops/sec, <1ms latency, single-threaded (every command is atomic)

---

## 4. Load Balancing [P: 90%]

**One-liner**: L4 at edge for raw speed, L7 for intelligent routing. Always mention in your architecture.

### L4 vs L7 — The Key Distinction

| | L4 (Transport) | L7 (Application) |
|---|---|---|
| **Operates on** | IP + Port | HTTP headers, URL, cookies |
| **Speed** | Faster (no content inspection) | Slower (inspects payload) |
| **Use for** | TCP/UDP traffic, non-HTTP | Content routing, SSL termination, API gateway |
| **Examples** | AWS NLB, HAProxy (TCP) | AWS ALB, Nginx, Envoy |

### Algorithms — Know These Three

| Algorithm | When to Use |
|-----------|------------|
| **Round Robin** | Equal-capacity servers, stateless services |
| **Least Connections** | Variable request duration, long-lived connections |
| **Consistent Hashing** | Cache servers, sticky routing without sticky sessions |

### Interview Power Moves
- "We'll terminate TLS at the L7 load balancer to offload crypto from backends and enable content-based routing"
- "For WebSocket connections, we'll use consistent hashing at L4 to maintain connection affinity"
- **HA for LBs**: Active-Passive with VRRP failover, or use cloud-managed (ALB/NLB — 99.99% SLA)

---

## 5. Sharding & Replication [P: 90%]

**One-liner**: Replication = copies (read scale + HA). Sharding = partitions (write scale + storage).

### Replication

| Type | How | Tradeoff |
|------|-----|----------|
| **Sync** | Wait for all replicas to ACK | Strong consistency, higher latency |
| **Async** | Don't wait, replicate in background | Low latency, possible data loss |
| **Semi-sync** | Wait for 1 replica ACK | Best compromise (used in practice) |

### Sharding Strategies

| Strategy | How | Pros/Cons |
|----------|-----|-----------|
| **Range-based** | Shard by value range (A-M, N-Z) | Easy range queries. Risk of hot spots |
| **Hash-based** | `hash(key) % N` | Even distribution. Range queries scatter |
| **Consistent Hashing** | Hash ring with virtual nodes | Adding/removing nodes moves only K/N keys. **Use this** |

### Shard Key Selection — Critical Decision

| Good Shard Key | Bad Shard Key |
|----------------|--------------|
| `user_id` (high cardinality, even distribution) | `country` (skewed — US gets 50% of traffic) |
| `order_id` (unique per order) | `timestamp` (hot spot on latest shard) |
| `tenant_id` (multi-tenant SaaS) | `boolean` field (only 2 values) |

### Interview Power Moves
- "We'll use consistent hashing with 150 virtual nodes per server for even distribution"
- "Shard key is `user_id` — it matches our access pattern (all queries are per-user) and distributes evenly"
- **Cross-shard queries are expensive** → denormalize data or use scatter-gather pattern

---

## 6. CAP Theorem & Consistency [P: 85%]

**One-liner**: Partitions are inevitable. Choose CP (refuse stale) for money, AP (serve stale) for feeds.

### CAP in 30 Seconds
- **CP** (Consistency + Partition tolerance): System refuses to serve during partition → banks, inventory, payments
- **AP** (Availability + Partition tolerance): System serves possibly stale data → social feeds, analytics, search
- **CA doesn't exist** in distributed systems (partitions always happen)

### PACELC — The Real Framework
> Even without partitions, there's a **Latency vs Consistency** tradeoff.

| System | During Partition | Normal Operation |
|--------|-----------------|-----------------|
| PostgreSQL | PC (refuse) | EC (consistent) |
| Cassandra | PA (available) | EL (low latency) |
| DynamoDB | PA (available) | EL (tunable) |
| MongoDB | PC (refuse) | EC (consistent) |

### Consistency Spectrum (Strong → Weak)
1. **Linearizable** — most recent write always visible (expensive, slow)
2. **Sequential** — operations in some total order
3. **Causal** — cause before effect guaranteed
4. **Eventual** — will converge... eventually (cheapest, fastest)

### Tunable Consistency (Cassandra/DynamoDB)
- `W + R > N` → strong consistency (e.g., N=3, W=2, R=2)
- `W=1, R=1` → fastest but weakest (eventual)
- **QUORUM** (majority) is the sweet spot for most use cases

### Interview Power Moves
- "For the payment service, we need CP — we can't show stale balances. For the news feed, AP with eventual consistency is fine"
- "We'll use QUORUM reads and writes (W=2, R=2, N=3) to guarantee strong consistency while tolerating one node failure"

---

## 7. Message Queues & Async Processing [P: 85%]

**One-liner**: Decouple services, absorb traffic spikes, enable retry. Kafka for streaming, SQS/RabbitMQ for task queues.

### When to Use a Queue
- User doesn't need to wait for the result (send email, process payment notification, generate thumbnail)
- Traffic spikes need buffering (flash sales, viral content)
- Services need decoupling (order service shouldn't directly call inventory, notification, analytics)

### Kafka vs RabbitMQ vs SQS

| | Kafka | RabbitMQ | SQS |
|---|---|---|---|
| **Model** | Distributed log (retain messages) | Traditional queue (delete after consume) | Managed queue (AWS) |
| **Throughput** | Millions/sec | 10K-50K/sec | 3K-30K/sec |
| **Replay** | Yes (consumers re-read) | No | No |
| **Ordering** | Per-partition | Per-queue | Best-effort (FIFO available) |
| **Best for** | Event streaming, CDC, analytics | Task queues, routing, RPC | AWS-native, simple queues |

### Delivery Guarantees

| Guarantee | Meaning | How |
|-----------|---------|-----|
| **At-most-once** | May lose messages | Fire and forget (no ACK) |
| **At-least-once** | May duplicate messages | ACK after processing + **idempotent consumers** |
| **Exactly-once** | No loss, no duplicates | At-least-once + idempotency (practical approach) |

### The Outbox Pattern (Dual-Write Problem)
**Problem**: DB update + queue publish must both succeed or both fail. They're separate systems — no shared transaction.

**Solution**: Write event to `outbox` table in same DB transaction → CDC/poller reads outbox → publishes to Kafka.

### Interview Power Moves
- "We'll publish order events to Kafka for async processing. The notification, analytics, and inventory services each consume independently"
- "We use at-least-once delivery with idempotent consumers — each consumer checks the event ID before processing"
- "To solve the dual-write problem, we'll use the transactional outbox pattern with Debezium CDC"

---

## 8. API Design [P: 85%]

**One-liner**: REST for external, gRPC for internal, GraphQL when clients need flexibility.

### REST vs gRPC vs GraphQL

| | REST | gRPC | GraphQL |
|---|---|---|---|
| **Format** | JSON over HTTP/1.1 | Protobuf over HTTP/2 | JSON over HTTP |
| **Speed** | Baseline | 5-10x faster than REST | Similar to REST |
| **Best for** | Public APIs, CRUD | Internal microservices | Mobile apps, varied clients |
| **Streaming** | No (use WebSocket) | 4 modes (unary, server, client, bidi) | Subscriptions |

### Pagination — Always Use Cursor-Based

| Type | Pros | Cons |
|------|------|------|
| **Offset** (`?page=5&size=20`) | Simple | Slow at large offsets, inconsistent with real-time inserts |
| **Cursor** (`?after=abc123&size=20`) | Fast at any depth, consistent | Can't jump to page N |

### Rate Limiting Algorithms — Know 2-3

| Algorithm | Key Trait | Used By |
|-----------|----------|---------|
| **Token Bucket** | Allows bursts up to bucket size | AWS, Stripe, API Gateway |
| **Sliding Window Counter** | No boundary spike problem | Best default choice |
| **Fixed Window** | Simplest to implement | Has 2x burst problem at window edges |

### Interview Power Moves
- "External API is REST with cursor-based pagination. Internal services communicate via gRPC for 10x performance"
- "Rate limiting via token bucket at the API gateway — 100 req/min per user with burst allowance of 20"

---

## 9. Distributed Transactions [P: 80%]

**One-liner**: 2PC for strong consistency (rare). SAGA for microservices (common). Outbox for DB+queue atomicity.

### Decision Guide

| Pattern | When to Use | Tradeoff |
|---------|------------|----------|
| **2PC** | Strong consistency within datacenter, few participants | Blocking — coordinator failure = everyone waits |
| **SAGA (Orchestration)** | Multi-service workflows (checkout, booking) | Eventually consistent, needs compensating transactions |
| **SAGA (Choreography)** | Simple 2-3 step flows | Hard to trace, no central control |
| **Outbox** | DB change + event publish must be atomic | Extra table + CDC/poller overhead |
| **TCC** | Need resource reservation with timeout | Complex, 3 phases per participant |

### SAGA — The Go-To Pattern

```
Order Created → Reserve Inventory → Process Payment → Confirm Shipping
                     ↓ (if payment fails)
              Release Inventory ← Refund Payment
```

- **Orchestration** (recommended): Central coordinator manages the flow via state machine
- **Choreography**: Each service emits events, next service reacts
- **Every compensating transaction must be idempotent** (retries happen)

### Interview Power Moves
- "For the checkout flow, I'll use an orchestrated SAGA. The order service coordinates: reserve inventory → charge payment → confirm shipping. If payment fails, it triggers compensating actions"
- "Each SAGA step writes to its local DB + outbox table in one transaction, then CDC publishes to Kafka"

---

## 10. Consistent Hashing [P: 80%]

**One-liner**: Adding/removing a node moves only 1/N of keys. Virtual nodes fix uneven distribution.

### Why It Matters
- **Naive hashing** (`hash(key) % N`): Adding a server remaps (N-1)/N keys — cache miss storm
- **Consistent hashing**: Adding a server remaps only ~1/N keys — minimal disruption

### How It Works
1. Hash ring (0 to 2³²)
2. Servers placed on ring at `hash(server_ip)`
3. Key goes to the next server clockwise on the ring
4. **Virtual nodes** (100-200 per physical server) ensure even distribution

### Where It's Used
- Cache clusters (Memcached, Redis Cluster)
- Database sharding (DynamoDB, Cassandra)
- CDN request routing
- Load balancing (for sticky routing)

---

## 11. Idempotency [P: 80%]

**One-liner**: Same request sent twice = same result. Critical for payments, bookings, any state-changing operation.

### The Pattern
1. Client sends `Idempotency-Key` header (tied to business intent, e.g., `order_123_payment_1`)
2. Server does `SET key NX EX 86400` in Redis (atomic — only first request wins)
3. First request: process and cache the response
4. Retry: return cached response immediately

### Caching Rules
- **2xx**: Cache (terminal success state)
- **4xx**: Don't cache (let client fix and retry)
- **5xx**: Don't cache (transient failure, allow retry)

### Interview Power Moves
- "Every payment API call includes an idempotency key. Redis SETNX ensures only one request processes. Retries get the cached response"
- "We use two-layer idempotency — Redis for fast path, DB UNIQUE constraint as safety net"

---

## 12. How to Structure Your Interview [P: 100%]

### Phase 1: Requirements (First 5 Minutes) — DO NOT SKIP

| Ask About | Why It Matters |
|-----------|---------------|
| Users/Scale (DAU, peak QPS) | Determines if you need sharding, caching, CDN |
| Core features (narrow scope!) | Don't design everything — pick 3-4 features |
| Read/write ratio | Read-heavy → caching, replicas. Write-heavy → sharding, queues |
| Consistency vs availability | CP for payments. AP for feeds |
| Latency requirements | <100ms needs caching. <10ms needs in-memory |
| Data access patterns | Drives database + index + shard key choices |

### Phase 2: High-Level Design (10 Minutes)
- Draw the boxes: Client → CDN → LB → API Gateway → Services → DB/Cache/Queue
- Identify 3-4 core services
- Pick databases with justification

### Phase 3: Deep Dive (15 Minutes)
- Interviewer will pick 1-2 areas to drill into
- Go deep on data model, APIs, failure handling, scaling bottlenecks

### Phase 4: Wrap-Up (5 Minutes)
- Mention monitoring/alerting, deployment strategy, future improvements

### Senior-Level Signals
- "What's the blast radius if this service fails?"
- "How do we handle a 10x traffic spike?"
- "What metrics should we monitor? Latency p99, error rate, queue depth"
- "We can deploy with canary — 5% traffic first, watch error rates, then roll out"

---

# TIER 2 — HIGH-FREQUENCY SYSTEM DESIGNS (Asked 70%+ of the Time)

These are the **most commonly asked** system design questions. Master at least 5-6 of these.

---

## 1. URL Shortener (TinyURL / Bitly) [P: 85%]

**Why asked so often**: Tests fundamentals — hashing, DB choice, caching, scale estimation.

### Requirements
- 100M URLs/day write, 10B redirects/day read (100:1 read:write ratio)
- Short codes: 7 characters base62 = 3.5 trillion combinations
- Latency: <10ms redirect

### Core Architecture
```
Client → CDN → LB → API Gateway → URL Service → [Redis Cache → PostgreSQL/Cassandra]
```

### Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| **Short code generation** | Counter-based with pre-allocated ranges | No collisions, distributed, no coordination |
| **Redirect code** | 302 (temporary) | Enables analytics tracking (301 would bypass server) |
| **Database** | Cassandra or DynamoDB | Simple key-value access pattern, massive scale |
| **Cache** | Redis LRU | 80/20 rule — 20% of URLs get 80% of traffic |
| **Shard key** | `short_code` | Every redirect hits exactly one shard |

### What Interviewers Probe
- **How do you generate unique short codes without collisions?** → Pre-generated key DB or counter ranges
- **What if the same long URL is submitted twice?** → Different short codes (simpler, better per-user analytics)
- **How do you handle analytics?** → Async — queue click events to Kafka, never block redirect

---

## 2. Chat System (WhatsApp) [P: 80%]

**Why asked so often**: Tests real-time communication, stateful connections, ordering, and scale.

### Requirements
- 2B users, 100B messages/day
- <100ms delivery latency
- Message ordering per conversation
- Online/offline presence

### Core Architecture
```
Client ↔ WebSocket Gateway → Chat Service → [Kafka → Cassandra]
                                          → [Redis (presence, routing)]
```

### Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| **Protocol** | WebSocket (primary) + Long Polling (fallback) | Full-duplex, lowest latency |
| **Message ordering** | Per-conversation sequence numbers (Redis INCR) | Timestamps fail due to clock skew |
| **Message storage** | Cassandra (`partition: conversation_id`) | Write-optimized, time-series-like access |
| **Connection routing** | Redis HashMap (`user_id → server_id`) | Route messages to correct WebSocket server |
| **Group fan-out** | Small (<100): direct push. Large (>1000): pull on read | Prevents fan-out explosion |

### What Interviewers Probe
- **How do offline users get messages?** → Messages persist in Cassandra. On reconnect, client syncs from last sequence number
- **How do you route messages across servers?** → Redis Pub/Sub — publishing server looks up target server in Redis, sends via Pub/Sub channel
- **Read receipts at scale?** → Batch per conversation, don't fan out in large groups, query on demand

---

## 3. News Feed / Twitter Timeline [P: 80%]

**Why asked so often**: Tests fan-out strategies — the classic push vs pull problem.

### Requirements
- 500M DAU, 1B posts/day
- Feed read: <50ms (cache hit), <500ms (cache miss)

### The Core Problem: Fan-Out Strategy

| Approach | How | Good For | Bad For |
|----------|-----|----------|---------|
| **Fan-out on Write (Push)** | On post, write to every follower's feed cache | Fast reads, normal users | Celebrities (millions of followers) |
| **Fan-out on Read (Pull)** | On read, fetch posts from all followed users | Celebrities, inactive users | Slow reads, heavy compute |
| **Hybrid (The Answer)** | Push for normal users (<10K followers), Pull for celebrities | Production systems | More complex |

### Key Design Decisions
- **Feed cache**: Redis Sorted Set (post IDs sorted by timestamp)
- **Post IDs**: Snowflake IDs (time-ordered, distributed, unique)
- **Async fan-out**: Post → Kafka → Fan-out workers → write to follower feed caches
- **Celebrity detection**: Users with >10K followers flagged. Their posts merged at read time

### What Interviewers Probe
- **The celebrity problem** → Hybrid fan-out. Don't pre-compute feeds for million-follower users
- **How do you rank the feed?** → Time-based initially, then ML ranking (engagement score)
- **Pagination** → Cursor-based (not offset) because real-time inserts break offset pagination

---

## 4. Rate Limiter [P: 75%]

**Why asked so often**: Tests algorithm knowledge, distributed systems, and failure handling.

### Requirements
- 1M+ users, 100K+ req/sec
- Per-user and per-API limits
- Distributed (multiple API servers share state)

### Recommended Algorithm: Sliding Window Counter

```
Current window count + (Previous window count × overlap percentage)
Example: Limit 100/min at 12:01:15
  - Current window (12:01): 40 requests
  - Previous window (12:00): 80 requests
  - Overlap: 45/60 = 75%
  - Effective count: 40 + (80 × 0.75) = 100 → REJECT next request
```
- No boundary spike problem (unlike Fixed Window)
- O(1) memory per user (2 counters)

### Distributed Architecture
```
Client → API Gateway → Redis (atomic INCR + EXPIRE) → Backend
```
- Redis `INCR` is atomic — no race conditions
- Lua script for multi-step atomic operations
- **When Redis is down**: Local fallback (per-server limit / num_servers) — degraded but functional

### What Interviewers Probe
- **Fixed Window boundary problem** → 2x burst at window edges. Sliding Window Counter solves this
- **What if Redis fails?** → Fail-open (allow all) for non-critical APIs. Local rate limiting as fallback
- **Where to place it?** → API Gateway (centralized) + application middleware (custom logic)

---

## 5. E-Commerce / Ticket Booking (Amazon/BookMyShow) [P: 75%]

**Why asked so often**: Tests distributed transactions, inventory management, concurrency control.

### Key Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| **Double booking** | Redis `SET NX` for fast seat lock + DB unique constraint as safety net |
| **Distributed checkout** | SAGA pattern (orchestration): Reserve → Pay → Confirm. Compensate on failure |
| **Inventory at flash sale** | Redis Lua script `DECRBY` (atomic). Virtual queue to control flow |
| **Abandoned carts** | TTL on reservation (10 min). Redis auto-expiry + DB cleanup job |
| **Payment timeout** | Mark PENDING_VERIFICATION. Reconciliation job checks actual status |

### SAGA Checkout Flow
```
Create Order → Reserve Inventory → Process Payment → Confirm Shipping
     ↓ (any step fails)
Release Inventory ← Refund Payment ← Cancel Order
```
- **Every step is idempotent** (uses idempotency keys)
- **Orchestration** (recommended): Order service is the coordinator

### Database Choices

| Service | DB | Why |
|---------|-----|-----|
| Orders/Payments | PostgreSQL | ACID, strong consistency |
| Product Catalog | MongoDB | Flexible schema (different product attributes) |
| Cart/Sessions | Redis | Speed + TTL auto-expiry |
| Search | Elasticsearch | Full-text search, facets, filters |
| Events | Kafka | Async processing, decoupling |

---

## 6. Uber / Ride-Hailing [P: 70%]

**Why asked so often**: Tests geospatial indexing, real-time matching, and location tracking.

### Core Challenges

| Challenge | Solution |
|-----------|----------|
| **250K location updates/sec** | Redis GEO commands (in-memory). Geohash for efficient proximity queries |
| **Geospatial indexing** | S2 Geometry — converts 2D lat/lng to 1D cell IDs for range queries |
| **Driver matching** | Scoring: ETA (50%) + fairness (20%) + acceptance rate (20%) + rating (10%) |
| **Race condition (2 rides claim same driver)** | Redis `SETNX` — atomically reserve driver before sending ride offer |
| **ETA calculation** | Contraction Hierarchies (pre-processed graph, <1ms query) + real-time traffic tiles |
| **Surge pricing** | H3 hex grid zones, demand/supply ratio, stored in Redis with 5-min TTL |

### Architecture
```
Rider App ↔ API Gateway → Ride Service → Matching Engine
Driver App ↔ WebSocket Gateway → Location Service → Redis GEO
                                                   → Kafka (history)
```

### What Interviewers Probe
- **How do you find nearby drivers?** → Geohash/S2 cells. Query Redis GEO for drivers within radius. Expand radius if too few results
- **How do you prevent two riders from getting the same driver?** → Atomic reservation with Redis SETNX
- **How do you handle 250K location updates/sec?** → Redis (in-memory), batch writes, Kafka for durable history

---

## 7. Notification System [P: 70%]

**Why asked so often**: Tests multi-channel delivery, reliability, and priority handling.

### Architecture
```
Any Service → Kafka (priority topics) → Channel Workers → Providers
                                        ├── Push Worker → APNs/FCM
                                        ├── SMS Worker → Twilio/Nexmo
                                        ├── Email Worker → SendGrid/SES
                                        └── In-App Worker → WebSocket/DB
```

### Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| **Queue** | Kafka with priority topics (P0, P1, P2) | Independent scaling per priority and channel |
| **Delivery** | At-least-once + exponential backoff + DLQ | Messages must not be lost |
| **Provider fallback** | Multiple providers per channel (Twilio → Nexmo) | Single provider outage shouldn't block notifications |
| **Rate limiting** | 4 levels: per-user, per-service, global, provider | Prevent spam + respect provider limits |
| **Batching** | "Alice, Bob, and 8 others liked your post" | Reduces notification fatigue |

### What Interviewers Probe
- **How do you ensure notifications are delivered?** → At-least-once with retries + DLQ for persistent failures
- **How do you handle quiet hours?** → Check user timezone, defer non-critical notifications. OTPs always bypass
- **What about invalid device tokens?** → On push failure from APNs/FCM, mark token invalid, request fresh token on next app open

---

## 8. Distributed Key-Value Store (DynamoDB / Cassandra) [P: 70%]

**Why asked so often**: Tests distributed systems fundamentals — hashing, replication, consistency.

### Architecture Components

| Component | Purpose |
|-----------|---------|
| **Consistent Hashing + Virtual Nodes** | Distribute data evenly, minimal rebalancing on node changes |
| **Quorum (W + R > N)** | Tunable consistency. N=3, W=2, R=2 = strong consistency |
| **Vector Clocks / LWW** | Conflict resolution. Vector clocks preserve all; LWW is simpler but loses writes |
| **LSM-Tree + SSTables** | Write-optimized storage. Append-only memtable → flush to sorted files |
| **Bloom Filters** | Skip unnecessary SSTable reads (99% accuracy, ~1.25 bytes/key) |
| **Gossip Protocol** | Decentralized failure detection, no SPOF |
| **Merkle Trees** | Detect and sync inconsistencies between replicas |
| **Hinted Handoff** | During partition, store writes for downed node, replay when it recovers |

### Interview Power Moves
- "Reads go to R=2 of N=3 replicas. We take the most recent value based on vector clocks and do read repair on the stale replica"
- "Write path: memtable (in-memory) → WAL (durability) → flush to SSTable when full → periodic compaction"
- "Deletes use tombstones — we can't just remove the record because replicas might resurrect it during anti-entropy"

---

# TIER 3 — COMMONLY ASKED DESIGNS (40-70% Probability)

These come up frequently but less predictably. Know the key ideas and tradeoffs.

---

## 1. Payment Gateway (Stripe / Razorpay) [P: 60%]

### Must-Know Points
- **Idempotency is THE critical requirement** — Redis SETNX with 24hr TTL. Every API call has an idempotency key
- **Payment state machine**: CREATED → PROCESSING → AUTHORIZED → CAPTURED → REFUNDED
- **Network timeout handling**: Mark as PENDING_VERIFICATION, async reconciliation job queries actual status
- **Double-entry bookkeeping**: Every transaction = debit + credit entries that sum to zero (self-auditing)
- **PCI-DSS**: Card data never enters app. Client SDK (Stripe.js) → Vault → returns token. HSM for encryption

### Architecture Pattern
```
Client → API Gateway → Payment Service → [Redis (idempotency) + PostgreSQL (transactions)]
                                        → Payment Processor (Stripe/Razorpay)
                                        → Kafka → Webhook Service → Merchant
```

---

## 2. Video Streaming (YouTube / Netflix) [P: 55%]

### Must-Know Points
- **Upload**: Presigned URLs for direct-to-S3 upload (bypass app servers). Multipart + resumable for large files
- **Transcoding**: Split into 2-6s segments, transcode in parallel across 5+ quality levels (1080p, 720p, 480p, 360p, 240p)
- **Adaptive Bitrate (ABR)**: Manifest file (.m3u8) lists all quality levels. Player auto-switches based on current bandwidth
- **CDN is critical**: Video segments are immutable (long TTL). Popular content = 99%+ cache hit rate
- **Storage tiers**: Hot (all renditions, S3 + CDN), Warm (popular only, IA), Cold (original only, Glacier — re-transcode on demand)

### Key Protocol Choice
- **HLS** (Apple): Most common, 6-10s latency
- **LL-HLS**: 2-4s latency
- **WebRTC**: Sub-second (for live video calls, not streaming at scale)

---

## 3. Search Engine & Typeahead [P: 55%]

### Must-Know Points
- **Inverted Index**: `term → [doc1(tf=3, pos=[1,5,9]), doc2(tf=1, pos=[4])]` — the core data structure
- **BM25 > TF-IDF**: TF saturation (diminishing returns for repeated terms), document length normalization
- **Document-based sharding**: Each shard is a self-contained mini-search engine. Query fans out to all shards (scatter-gather)
- **Typeahead**: Trie with pre-computed top-K suggestions at each node. O(prefix_length) lookup
- **Spell correction**: Edit distance + noisy channel model. Generate candidates at distance 1-2, rank by frequency

---

## 4. Food Delivery (Zomato / DoorDash) [P: 55%]

### Must-Know Points
- **Three-sided marketplace**: Customer, Restaurant, Delivery Partner — different concerns for each
- **Location service is highest throughput**: 75K updates/sec. Redis GEO + Geohash sharding
- **Delivery assignment**: Multi-factor scoring (distance 40%, rating 20%, workload 20%, fairness 10%, acceptance 10%)
- **Order state machine**: PLACED → CONFIRMED → PREPARING → READY → PICKED_UP → DELIVERED (Kafka events at each transition)
- **ETA formula**: `Prep time + Partner→Restaurant + Pickup buffer + Restaurant→Customer`. Dynamic updates every 30s

---

## 5. Real-Time Messaging (WhatsApp Deep Dive) [P: 50%]

### Must-Know Points
- **Scale**: 100M concurrent WebSocket connections across ~2000 servers (50K each)
- **Delivery**: At-least-once + client-side dedup via unique `message_id`
- **E2E Encryption**: Signal Protocol — X3DH key exchange, Double Ratchet for forward secrecy. Server only sees encrypted blobs
- **Group encryption**: Sender Keys — sender encrypts once, all group members can decrypt (efficient)
- **DLQ pattern**: Failed messages → DLQ after max retries. Monitor, alert, manual replay

---

## 6. Video Conferencing (Zoom) [P: 50%]

### Must-Know Points
- **SFU (Selective Forwarding Unit)** is the standard — server receives one stream per participant, forwards selectively to others
- **Simulcast**: Client sends 3 quality levels (1080p/720p/360p). SFU picks best per receiver based on their bandwidth
- **WebRTC**: SDP negotiation → ICE/STUN/TURN for NAT traversal → DTLS-SRTP for encrypted media over UDP
- **Large meetings (1000+)**: SFU cascading. For webinars: transcode to HLS/DASH via CDN
- **Graceful degradation**: Reduce resolution → reduce FPS → audio-only → never drop the call

---

## 7. Social Media Platform (Instagram / Twitter) [P: 50%]

### Must-Know Points
- Same core as News Feed (hybrid push/pull fan-out)
- **Snowflake IDs** for time-ordered, distributed unique post IDs
- **Thundering herd**: Hot key detection + replication, local L1 cache, request coalescing (singleflight)
- **Write Path**: Client → API → Posts DB → Kafka → Fan-out → Feed Cache
- **Read Path**: Client → API → Feed Cache (+ celebrity pull) → Post Cache → DB

---

# TIER 4 — SPECIALIZED TOPICS (20-40% Probability)

Know these at a high level. They're asked for specific roles or as follow-ups.

---

## 1. Kafka Deep Dive [P: 40%]

### Quick-Fire Facts
- **Ordering**: Per-partition only. `hash(key) % num_partitions`
- **Production config**: `acks=all` + `min.insync.replicas=2` + `replication.factor=3` (tolerates 1 broker failure, zero data loss)
- **Why fast**: Sequential I/O, zero-copy (`sendfile`), OS page cache, batching, compression
- **Consumer groups**: Pub-sub between groups, load balancing within. 1 partition = max 1 consumer per group
- **Exactly-once**: Idempotent producer (`enable.idempotence=true`) + transactions for atomic read-process-write
- **KRaft** (3.3+): No ZooKeeper dependency. Faster failover (<5s). Supports millions of partitions

---

## 2. Redis Deep Dive [P: 40%]

### Quick-Fire Facts
- **Single-threaded** command execution — every command is atomic. No locks needed
- **Data structures for use cases**: Sorted Sets (leaderboards), Bitmaps (DAU — 12MB for 100M users), HyperLogLog (unique counts — 12KB), GEO (proximity)
- **Distributed lock**: `SET key value NX EX 30` + Lua script for safe release
- **Persistence**: RDB (snapshots) + AOF (append log). Hybrid = best of both
- **Cluster**: 16384 hash slots distributed across nodes. Auto-sharding + failover
- **Eviction**: `allkeys-lru` for caches, `noeviction` for databases

---

## 3. Microservices Architecture [P: 40%]

### Quick-Fire Concepts

| Concept | Key Point |
|---------|-----------|
| **Service Decomposition** | DDD bounded contexts. One team = one service = one DB |
| **API Gateway** | Single entry point. Auth, rate limiting, routing, SSL termination |
| **Service Mesh (Istio/Linkerd)** | Sidecar proxy handles mTLS, service discovery, circuit breaking. No code changes |
| **Circuit Breaker** | Open (fail fast) → Half-Open (test) → Closed (normal). Prevents cascade failures |
| **Bulkhead** | Isolate thread pools per dependency. One slow service doesn't consume all threads |
| **Strangler Fig** | Migrate monolith gradually. Route traffic to new service per feature, keep old running |
| **Deployment** | Blue-Green (instant switch) or Canary (5% → 25% → 100% gradual rollout) |

---

## 4. Distributed Locking [P: 35%]

### Quick-Fire Concepts
- **Two types (Kleppmann)**: Efficiency (prevent duplicate work — simple Redis lock is fine) vs Correctness (prevent data corruption — need consensus + fencing tokens)
- **Fencing tokens**: Lock server issues monotonically increasing token. Storage rejects stale tokens. Solves zombie lock holder problem
- **Redis lock**: `SET key UUID NX EX 30` + Lua script to check UUID before delete
- **Redlock controversy**: 5 Redis instances, majority lock. Kleppmann argues clock drift breaks it. Use for efficiency, not correctness
- **For correctness**: ZooKeeper/etcd ephemeral nodes + fencing tokens

---

## 5. Observability [P: 35%]

### Quick-Fire Concepts
- **Three Pillars**: Metrics (what's the error rate?), Logs (what happened?), Traces (why is this slow?)
- **Four Golden Signals**: Latency, Traffic, Errors, Saturation
- **Distributed tracing**: Propagate `trace_id` in headers. Each operation = span with timing. OpenTelemetry standard
- **Alert on symptoms, not causes**: "Error rate > 1%" not "CPU > 80%". Include runbook links
- **Structured JSON logs** with `trace_id` for cross-service correlation

---

## 6. Networking Essentials [P: 30%]

### Quick-Fire Concepts
- **HTTP/2**: Multiplexing (multiple streams, one connection), binary framing, header compression. BUT: L4 LB sees one connection → all streams go to one backend (use L7 LB)
- **HTTP/3 (QUIC)**: UDP-based, per-stream ordering (no HOL blocking), 0-1 RTT handshake, connection migration (WiFi→cellular seamless)
- **WebSocket**: Full-duplex over single TCP connection. For chat, gaming, live data. Each server handles 10K-100K connections
- **SSE**: Server-to-client only (simpler than WebSocket). Good for dashboards, notifications
- **TLS 1.3**: 1-RTT handshake (vs 2 for 1.2), 0-RTT resumption (risk: replay), mandatory forward secrecy

---

## 7. CDC (Change Data Capture) [P: 30%]

### Quick-Fire Concepts
- **Log-based CDC is gold standard**: Read WAL/binlog directly. No app changes, low overhead, captures all changes in order
- **Stack**: Debezium → Kafka → consumers
- **Use cases**: Cache invalidation, search index sync, real-time analytics, microservice data sync, audit logging
- **Challenges**: Schema evolution (Schema Registry), ordering (partition by key), initial snapshot handling

---

## 8. Other Designs (Brief Notes)

### Distributed File System (GFS/HDFS) [P: 25%]
- Large chunks (64-128MB), 3x replication (rack-aware), master stores metadata in memory
- Data flows linearly (pipeline), control through primary
- Modern alternative: S3/GCS (zero ops, exabyte scale)

### Recommendation System [P: 25%]
- Three-stage pipeline: Candidate Generation (100M→1000) → Ranking (ML model) → Re-ranking (diversity, business rules)
- Two-Tower model: user embedding + item embedding, dot product for score, ANN search (FAISS) for <10ms retrieval
- Cold start: popular/trending + demographic cohort + exploration budget

### Stock Trading System [P: 20%]
- Matching engine is single-threaded (deterministic, no locks). LMAX Disruptor = 6M orders/sec
- Order book: red-black tree for price levels, FIFO queue at each price, HashMap for O(1) lookup
- Price-Time priority. Event sourcing for full audit trail. Pre-trade risk checks < 1ms

### Time-Series Database [P: 20%]
- Why not SQL: append-only writes (B-tree waste), time-range scans, 12x specialized compression (Gorilla)
- High cardinality is #1 problem. Downsampling stores min/max/sum/count (not just avg)
- Two-dimensional sharding: by time (retention) + by series (write distribution)

### Task / Job Scheduler [P: 20%]
- Redis sorted set (score = execution timestamp). Poll for score ≤ now
- Exactly-once: pessimistic lock on job row. Idempotent job handlers
- DLQ for failed jobs. Exponential backoff with jitter

---

# QUICK REFERENCE — CROSS-CUTTING PATTERNS

## The Patterns That Appear Everywhere

| Pattern | Where It's Used |
|---------|----------------|
| **Kafka** | Every async workflow — fan-out, events, CDC, decoupling |
| **Redis** | Caching, sessions, locks, rate limits, leaderboards, presence, location |
| **Consistent Hashing** | Cache clusters, DB sharding, CDN routing |
| **Idempotency** | Payments, bookings, SAGA steps, any state-changing API |
| **SAGA Pattern** | E-Commerce checkout, booking flows, any multi-service transaction |
| **Fan-out on Write/Read** | News Feed, Social Media, Notifications, Group Chat |
| **Event Sourcing** | Stock Trading, DFS, Audit trails |
| **Bloom Filters** | Cache penetration, LSM-Tree read optimization |
| **Circuit Breaker** | Any service-to-service call in microservices |
| **Outbox Pattern** | Anywhere you need DB change + event publish atomically |

## Database Decision Cheat Sheet

| Use Case | Database | Why |
|----------|----------|-----|
| Transactions, orders, payments | PostgreSQL | ACID, strong consistency |
| Product catalog, CMS | MongoDB | Flexible schema |
| Messages, time-series, IoT | Cassandra | Write-optimized, horizontal scale |
| Sessions, cache, counters | Redis | Sub-millisecond, atomic ops |
| Full-text search | Elasticsearch | Inverted index, facets |
| Social graphs | Neo4j | Relationship traversal |
| Analytics | ClickHouse / BigQuery | Columnar, massive aggregation |
| File/media storage | S3 + CDN | Durable, scalable, cached |

## Scale Numbers to Memorize

| Metric | Value |
|--------|-------|
| Redis ops/sec | 100K+ at <1ms latency |
| Kafka throughput | Millions of messages/sec |
| WebSocket connections per server | 10K-100K |
| PostgreSQL single node | ~10TB, 10K transactions/sec |
| Cassandra single node write | 10K-50K writes/sec |
| CDN latency (edge hit) | ~20ms vs 200ms+ origin |
| DNS lookup | 20-100ms (cached: <1ms) |
| HTTP/2 vs HTTP/1.1 | Single connection vs 6 connections per domain |
| Consistent hashing: key movement on add node | ~1/N keys (vs N-1/N naive) |

## The "What Would You Monitor?" Answer

Always mention these when asked about monitoring:
1. **Latency** — p50, p95, p99 (not average!)
2. **Error rate** — 5xx rate, business error rate
3. **Throughput** — requests/sec, messages/sec
4. **Queue depth** — growing = consumers can't keep up
5. **Cache hit rate** — dropping = something changed
6. **Database connections** — pool exhaustion = cascading failure
7. **Disk/CPU/Memory** — saturation signals

---

# INTERVIEW TEMPLATES

## Template: Any System Design Answer

```
1. REQUIREMENTS (5 min)
   - Functional: "Let me clarify the core features..."
   - Non-functional: scale, latency, consistency, availability
   - Back-of-envelope: DAU, QPS, storage, bandwidth

2. HIGH-LEVEL DESIGN (10 min)
   - Client → CDN → LB → API Gateway → Services → DB/Cache/Queue
   - Core services + their responsibilities
   - Database choices with justification

3. DEEP DIVE (15 min)
   - Data model + API design for core flow
   - Handle the hard problem (concurrency, consistency, hot spots)
   - Failure scenarios and recovery

4. SCALING & WRAP-UP (5 min)
   - Bottlenecks and how to address them
   - Monitoring & alerting
   - Future improvements
```

## Template: Back-of-Envelope Estimation

```
STORAGE:
- 1 char = 1 byte, 1 int = 4 bytes, 1 long/timestamp = 8 bytes
- Average URL = 100 bytes, Average tweet = 300 bytes
- Average photo = 200 KB, Average video (1 min) = 50 MB

THROUGHPUT:
- 1 day = 86,400 sec ≈ 100K sec (for easy math)
- 1M daily requests ≈ 12 req/sec
- 100M daily requests ≈ 1,200 req/sec
- Peak = 2-3x average

SCALE:
- 1 server = 10K-100K concurrent connections (WebSocket)
- 1 Redis instance = 100K ops/sec
- 1 PostgreSQL = 10K TPS
- 1 Kafka broker = 100K-1M messages/sec
```
