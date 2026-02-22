# System Design — Interview Preparation

Complete system design notes organized by **interview probability**.

> Start from Priority 1 and work down. Priority 1 + 2 covers ~80% of system design interviews.

## Interview-Ready Quick Notes

| Resource | Description |
|----------|-------------|
| **[INTERVIEW-READY-NOTES.md](INTERVIEW-READY-NOTES.md)** | All topics condensed into one file with probability rankings, decision tables, and power moves |

---

## Priority 1 — Core Fundamentals (90%+ Probability)

These concepts appear in **every** system design interview. You cannot design any system without them.

| # | Topic | What You Must Know | File |
|---|-------|--------------------|------|
| 1 | Scalability | Horizontal vs vertical, stateless services, Little's Law | [01-Scalability](Fundamentals/01-Scalability.md) |
| 2 | Databases | SQL vs NoSQL, indexing, isolation levels, MVCC | [05-Databases](Fundamentals/05-Databases.md) |
| 3 | Caching | Cache-aside, stampede/penetration/avalanche, Redis | [04-Caching](Fundamentals/04-Caching.md) |
| 4 | Load Balancing | L4 vs L7, algorithms, SSL termination, HA | [03-Load-Balancing](Fundamentals/03-Load-Balancing.md) |
| 5 | Sharding & Replication | Consistent hashing, shard key selection, sync vs async | [06-Sharding-And-Replication](Fundamentals/06-Sharding-And-Replication.md) |
| 6 | CAP Theorem | CP vs AP, PACELC, tunable consistency, quorum | [02-CAP-And-Consistency](Fundamentals/02-CAP-And-Consistency.md) |
| 7 | Message Queues | Kafka vs RabbitMQ, delivery guarantees, outbox pattern | [07-Message-Queues](Fundamentals/07-Message-Queues.md) |
| 8 | API Design | REST vs gRPC vs GraphQL, pagination, rate limiting | [08-API-Design](Fundamentals/08-API-Design.md) |
| 9 | Distributed Transactions | SAGA (orchestration/choreography), 2PC, TCC, outbox | [09-Distributed-Transactions](Fundamentals/09-Distributed-Transactions.md) |
| 10 | Idempotency | Idempotency-key pattern, Redis SETNX, caching rules | [22-Idempotent-API-Design](Fundamentals/22-Idempotent-API-Design.md) |

---

## Priority 2 — Most Asked System Designs (70%+ Probability)

The **top 8 most frequently asked** system design questions. Master at least 5-6 of these.

| # | System | Why It's Asked | Key Challenge | Files |
|---|--------|---------------|---------------|-------|
| 1 | **URL Shortener** | Tests fundamentals — hashing, caching, DB choice | Short code generation, 100:1 read/write | [URL-Shortener/](URL-Shortener/) |
| 2 | **Chat System (WhatsApp)** | Tests real-time, stateful connections, ordering | WebSocket routing, message ordering, group fan-out | [Chat-System/](Chat-System/) |
| 3 | **News Feed (Twitter)** | Tests fan-out — classic push vs pull problem | Hybrid fan-out, celebrity problem | [News-Feed-System/](News-Feed-System/) |
| 4 | **Rate Limiter** | Tests algorithms + distributed systems | Sliding window counter, Redis atomic ops | [Rate-Limiter/](Rate-Limiter/) |
| 5 | **E-Commerce / Booking** | Tests distributed transactions, concurrency | SAGA checkout, double-booking prevention | [E-Commerce/](E-Commerce/), [BookMyShow/](BookMyShow/) |
| 6 | **Uber / Ride-Hailing** | Tests geospatial, real-time matching | S2/Geohash indexing, driver reservation race condition | [Uber/](Uber/) |
| 7 | **Notification System** | Tests multi-channel delivery, reliability | Priority queues, provider fallback, DLQ | [Notification-System/](Notification-System/) |
| 8 | **Key-Value Store** | Tests distributed systems fundamentals | Consistent hashing, quorum, LSM-tree, Bloom filters | [Key-Value-Store/](Key-Value-Store/) |

---

## Priority 3 — Commonly Asked (40-70% Probability)

These come up frequently but less predictably. Know the key ideas and tradeoffs.

| # | System | Key Concept to Know | Files |
|---|--------|-------------------|-------|
| 1 | **Payment Gateway** | Idempotency, state machine, double-entry bookkeeping | [Payment-Gateway/](Payment-Gateway/) |
| 2 | **Video Streaming** | Transcoding pipeline, ABR, CDN, storage tiers | [Video-Streaming/](Video-Streaming/) |
| 3 | **Search Engine / Typeahead** | Inverted index, BM25, trie with top-K | [Search-Engine-Typeahead/](Search-Engine-Typeahead/) |
| 4 | **Food Delivery** | Three-sided marketplace, location tracking, ETA | [Food-Delivery-App/](Food-Delivery-App/) |
| 5 | **Real-Time Messaging** | 100M connections, E2E encryption, Signal Protocol | [Real-Time-Messaging/](Real-Time-Messaging/) |
| 6 | **Video Conferencing** | SFU architecture, WebRTC, simulcast | [Video-Conferencing-Zoom/](Video-Conferencing-Zoom/) |
| 7 | **Social Media Platform** | Hybrid fan-out, Snowflake IDs, thundering herd | [Social-Media-Platform/](Social-Media-Platform/) |

---

## Priority 4 — Deep-Dive Topics (20-40% Probability)

Specialized knowledge. Asked for specific roles or as follow-ups to deepen the conversation.

### Infrastructure Deep Dives

| Topic | Key Concept | Files |
|-------|------------|-------|
| **Kafka** | Partitions, acks=all, exactly-once, KRaft | [Kafka/](Kafka/) |
| **Redis** | Data structures per use case, persistence, clustering | [Redis/](Redis/) |
| **Distributed Cache** | Cache patterns, stampede prevention, consistent hashing | [Distributed-Cache/](Distributed-Cache/) |
| **Microservices** | Service mesh, circuit breaker, SAGA, strangler fig | [Microservices-Architecture/](Microservices-Architecture/) |
| **API Gateway** | Auth, rate limiting, routing, virtual waiting room | [API-Gateway/](API-Gateway/) |

### Specialized Systems

| Topic | Key Concept | Files |
|-------|------------|-------|
| **Distributed Lock** | Redis SETNX, fencing tokens, Redlock controversy | [Distributed-Lock-Service/](Distributed-Lock-Service/) |
| **Distributed File System** | Chunk-based, master metadata, 3x replication | [Distributed-File-System/](Distributed-File-System/) |
| **Recommendation System** | Two-tower model, candidate → ranking → re-ranking | [Recommendation-System/](Recommendation-System/) |
| **Stock Trading** | Single-threaded matching engine, order book, event sourcing | [Stock-Trading-System/](Stock-Trading-System/) |
| **Time-Series DB** | Gorilla compression, downsampling, high cardinality | [Time-Series-Database/](Time-Series-Database/) |
| **Task/Job Scheduler** | Redis sorted set, exactly-once execution, DLQ | [Task-Scheduler/](Task-Scheduler/), [Distributed-Job-Scheduler/](Distributed-Job-Scheduler/) |
| **File Storage** | Chunking, dedup, erasure coding | [File-Storage-System/](File-Storage-System/) |
| **CDN & Edge** | Edge caching, origin shielding, cache invalidation | [CDN-Edge-Computing/](CDN-Edge-Computing/) |
| **Distributed Tracing** | Trace/span model, sampling, OpenTelemetry | [Distributed-Tracing/](Distributed-Tracing/) |

### Fundamentals Deep Dives (Reference)

| Topic | When to Read | File |
|-------|-------------|------|
| Observability | When asked about monitoring/alerting | [10-Observability](Fundamentals/10-Observability.md) |
| Networking | When asked about protocols, HTTP/2/3 | [11-Networking](Fundamentals/11-Networking.md) |
| Security | When asked about auth, encryption, attacks | [12-Security](Fundamentals/12-Security.md) |
| Reverse Proxy & Event-Driven | When asked about EDA, stream processing | [13-Reverse-Proxy-And-Processing-Patterns](Fundamentals/13-Reverse-Proxy-And-Processing-Patterns.md) |
| Additional Networking | OSI model, CIDR, NAT | [14-Additional-Networking](Fundamentals/14-Additional-Networking.md) |
| Architectural Patterns | Serverless, P2P, gossip protocol | [15-Architectural-Patterns](Fundamentals/15-Architectural-Patterns.md) |
| Disaster Recovery & CDC | RTO/RPO, DR strategies, Debezium | [16-Disaster-Recovery-And-CDC](Fundamentals/16-Disaster-Recovery-And-CDC.md) |
| System Design Tradeoffs | Stateful vs stateless, push vs pull | [17-System-Design-Tradeoffs](Fundamentals/17-System-Design-Tradeoffs.md) |
| Backend Communication | HTTP/2 multiplexing, sidecar pattern | [18-Backend-Communication-Patterns](Fundamentals/18-Backend-Communication-Patterns.md) |
| Protocols Deep Dive | TCP, QUIC, gRPC streaming, WebRTC | [19-Protocols-Deep-Dive](Fundamentals/19-Protocols-Deep-Dive.md) |
| Database Internals | B+Tree, row vs column, UUIDv7, EXPLAIN | [20-Database-Internals-Deep-Dive](Fundamentals/20-Database-Internals-Deep-Dive.md) |
| Distributed Concurrency | Redis locks, fencing tokens, Redlock | [21-Distributed-Concurrency-Control](Fundamentals/21-Distributed-Concurrency-Control.md) |
| Interview Follow-Up Questions | Question banks by system type | [23-Interview-Followup-Questions](Fundamentals/23-Interview-Followup-Questions.md) |
| **Production Issues & Solutions** | Real-world war stories — DB, cache, cascading failures, zero-downtime migration | [24-Production-Issues-And-Solutions](Fundamentals/24-Production-Issues-And-Solutions.md) |

---

## Study Plan

| Timeframe | What to Cover | Goal |
|-----------|--------------|------|
| **Week 1-2** | Priority 1 fundamentals (Scalability → Idempotency) | Vocabulary + core concepts |
| **Week 3-4** | Priority 2 designs (URL Shortener, Chat, News Feed, Rate Limiter) | Practice the interview framework |
| **Week 5-6** | Priority 2 designs (E-Commerce, Uber, Notification, KV Store) | Handle complex multi-service problems |
| **Week 7-8** | Priority 3 + mock interviews | Depth + time management under pressure |

---

## The Interview Framework

```
STEP 1: REQUIREMENTS (5 min)
├── Functional: core features (pick 3-4, narrow scope)
├── Non-functional: scale, latency, consistency, availability
└── Back-of-envelope: DAU, QPS, storage, bandwidth

STEP 2: HIGH-LEVEL DESIGN (10 min)
├── Client → CDN → LB → API Gateway → Services → DB/Cache/Queue
├── Core services + responsibilities
└── Database choices with justification

STEP 3: DEEP DIVE (15 min)
├── Data model + API design for core flow
├── Handle the hard problem (concurrency, consistency, hot spots)
└── Failure scenarios and recovery

STEP 4: SCALING & WRAP-UP (5 min)
├── Bottlenecks and solutions
├── Monitoring (p99 latency, error rate, queue depth)
└── Deployment strategy (canary/blue-green)
```

---

## Numbers to Memorize

| Metric | Value |
|--------|-------|
| Redis ops/sec | 100K+ at <1ms |
| Kafka throughput | Millions msg/sec |
| WebSocket per server | 10K-100K connections |
| PostgreSQL single node | ~10TB, 10K TPS |
| CDN edge latency | ~20ms vs 200ms+ origin |
| 1M requests/day | ~12 QPS |
| 1B requests/day | ~12,000 QPS |
| Seconds per day | 86,400 ≈ 100K |

| Data Size | Value |
|-----------|-------|
| URL | ~100 bytes |
| Tweet/message | ~300 bytes |
| Photo | ~200 KB |
| Video (1 min, 1080p) | ~100 MB |

---

## Folder Structure

```
Notes-Detailed/
├── 00-SYSTEM-DESIGN-ROADMAP.md    # This file
├── INTERVIEW-READY-NOTES.md       # Condensed interview notes (START HERE)
├── Fundamentals/                   # 23 core concept files
├── URL-Shortener/                  # Priority 2 designs
├── Chat-System/
├── News-Feed-System/
├── Rate-Limiter/
├── E-Commerce/
├── BookMyShow/
├── Uber/
├── Notification-System/
├── Key-Value-Store/
├── Payment-Gateway/                # Priority 3 designs
├── Video-Streaming/
├── Search-Engine-Typeahead/
├── Food-Delivery-App/
├── Real-Time-Messaging/
├── Video-Conferencing-Zoom/
├── Social-Media-Platform/
├── Kafka/                          # Priority 4 deep dives
├── Redis/
├── Distributed-Cache/
├── Microservices-Architecture/
├── API-Gateway/
├── Distributed-Lock-Service/
├── Distributed-File-System/
├── Recommendation-System/
├── Stock-Trading-System/
├── Time-Series-Database/
├── Task-Scheduler/
├── Distributed-Job-Scheduler/
├── File-Storage-System/
├── CDN-Edge-Computing/
└── Distributed-Tracing/
```
