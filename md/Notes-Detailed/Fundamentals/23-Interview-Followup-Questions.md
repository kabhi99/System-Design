# CHAPTER 23: FOLLOW-UP QUESTIONS TO ASK THE INTERVIEWER
*Questions You Should Ask to Clarify Scope, Show Depth, and Drive the Design*

Asking the right questions separates senior candidates from junior ones.
Don't jump into design — first narrow the problem. These questions show you
think about tradeoffs, edge cases, and real-world constraints.

## SECTION 23.1: REQUIREMENTS CLARIFICATION (ASK FIRST)

### USERS AND SCALE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  QUESTIONS ABOUT USERS AND SCALE                                        |
|                                                                         |
|  1. How many users do we expect? DAU / MAU?                             |
|  2. What's the read-to-write ratio? (read-heavy? write-heavy?)          |
|  3. Is traffic evenly distributed or do we expect spikes?               |
|     (e.g., flash sales, events, weekday peaks)                          |
|  4. Is this a global system or single-region?                           |
|  5. Do we need to support multiple device types?                        |
|     (mobile, web, IoT, API clients)                                     |
|  6. Are there any existing systems we need to integrate with?           |
|  7. What's the expected growth rate? (10x in a year?)                   |
|                                                                         |
|  WHY ASK THESE:                                                         |
|  * Determines if you need sharding, CDN, multi-region                   |
|  * Read-heavy -> caching matters. Write-heavy -> DB choice matters      |
|  * Spiky traffic -> auto-scaling, queues, rate limiting                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### FUNCTIONAL SCOPE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  QUESTIONS ABOUT FEATURES                                               |
|                                                                         |
|  1. What are the core features vs nice-to-haves?                        |
|     "Should I focus on X, Y, Z or is there something else critical?"    |
|                                                                         |
|  2. Do users need real-time updates or is eventual ok?                  |
|     (push notifications vs polling vs WebSocket)                        |
|                                                                         |
|  3. Do we need search? If so, full-text or just filtering?              |
|                                                                         |
|  4. Do we need analytics/reporting on this data?                        |
|                                                                         |
|  5. Is there an admin interface or just user-facing?                    |
|                                                                         |
|  6. Do we need multi-tenancy?                                           |
|     (shared infra for multiple customers)                               |
|                                                                         |
|  7. What happens when the user performs [edge case action]?             |
|     * Duplicate submission?                                             |
|     * Concurrent edit by two users?                                     |
|     * Request during system maintenance?                                |
|                                                                         |
|  WHY ASK THESE:                                                         |
|  * Narrows scope — you can't design everything in 45 min                |
|  * Shows you think about edge cases before coding                       |
|  * Real-time vs eventual changes the entire architecture                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DATA CHARACTERISTICS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  QUESTIONS ABOUT DATA                                                   |
|                                                                         |
|  1. What's the size of each record/object?                              |
|     (a tweet = 280 chars vs a video = 1 GB)                             |
|                                                                         |
|  2. How long do we need to retain data?                                 |
|     (forever? 90 days? archival after 1 year?)                          |
|                                                                         |
|  3. Is the data structured, semi-structured, or unstructured?           |
|                                                                         |
|  4. What are the access patterns?                                       |
|     * Point lookups by ID?                                              |
|     * Range queries by time?                                            |
|     * Complex joins across entities?                                    |
|     * Full-text search?                                                 |
|                                                                         |
|  5. Is there a hot/cold data split?                                     |
|     (recent data accessed often, old data rarely)                       |
|                                                                         |
|  6. Do we need ACID transactions or is eventual consistency ok?         |
|                                                                         |
|  7. Are there any compliance requirements for data?                     |
|     (GDPR, HIPAA, data residency laws)                                  |
|                                                                         |
|  WHY ASK THESE:                                                         |
|  * Drives DB choice (SQL vs NoSQL vs time-series vs blob)               |
|  * Retention -> tiered storage, TTLs, archival                          |
|  * Access pattern is THE most important DB decision factor              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 23.2: NON-FUNCTIONAL REQUIREMENTS (ASK EARLY)

### CONSISTENCY vs AVAILABILITY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  QUESTIONS ABOUT CONSISTENCY AND AVAILABILITY                           |
|                                                                         |
|  1. What's more important — consistency or availability?                |
|     "Is it ok if two users briefly see different data?"                 |
|     "Or must everyone always see the same thing?"                       |
|                                                                         |
|  2. What consistency level do we need?                                  |
|     * Strong: bank balance, inventory count                             |
|     * Eventual: social media feed, like count                           |
|     * Read-your-writes: user sees own changes immediately               |
|                                                                         |
|  3. What's the target availability?                                     |
|     * 99.9% (8.7 hours downtime/year)                                   |
|     * 99.99% (52 min downtime/year)                                     |
|     * 99.999% (5 min downtime/year)                                     |
|                                                                         |
|  4. What happens if a component fails?                                  |
|     * Graceful degradation? (show cached data)                          |
|     * Hard failure? (show error page)                                   |
|     * Retry? (queue and process later)                                  |
|                                                                         |
|  WHY ASK THESE:                                                         |
|  * This is THE fundamental tradeoff (CAP theorem)                       |
|  * Strong consistency = synchronous replication = slower                |
|  * High availability = async replication = possible stale reads         |
|  * Shows you understand distributed systems tradeoffs                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### LATENCY AND PERFORMANCE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  QUESTIONS ABOUT LATENCY                                                |
|                                                                         |
|  1. What's the acceptable latency for the critical path?                |
|     * < 100ms (real-time: trading, gaming, video)                       |
|     * < 500ms (interactive: web apps, search)                           |
|     * < 2s (tolerable: report generation)                               |
|     * Minutes (batch: analytics, ETL)                                   |
|                                                                         |
|  2. Are there operations that can be async?                             |
|     "Does the user need to wait for this, or can we return              |
|      immediately and process in background?"                            |
|     (e.g., sending email, generating thumbnail, updating feed)          |
|                                                                         |
|  3. Is there a P99 latency requirement or just average?                 |
|     "Do we need tail latency guarantees?"                               |
|                                                                         |
|  4. Are there SLAs with downstream clients?                             |
|                                                                         |
|  WHY ASK THESE:                                                         |
|  * Async processing eliminates the biggest latency bottlenecks          |
|  * P99 vs P50 changes how you design (hedged requests, timeouts)        |
|  * Determines where you need caching, CDN, pre-computation              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### RELIABILITY AND DURABILITY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  QUESTIONS ABOUT RELIABILITY                                            |
|                                                                         |
|  1. Can we lose any data? Or must every write be durable?               |
|     * Payment data: ZERO loss                                           |
|     * Analytics event: some loss ok                                     |
|     * Chat message: depends on use case                                 |
|                                                                         |
|  2. Do we need exactly-once processing or at-least-once?                |
|     "Is it ok if the same event gets processed twice?"                  |
|     (idempotency question)                                              |
|                                                                         |
|  3. What's the disaster recovery expectation?                           |
|     * RPO (Recovery Point Objective): how much data loss?               |
|     * RTO (Recovery Time Objective): how long to recover?               |
|                                                                         |
|  4. Do we need multi-region failover?                                   |
|                                                                         |
|  WHY ASK THESE:                                                         |
|  * Durability requirement drives replication strategy                   |
|  * Exactly-once is expensive (idempotency keys, dedup)                  |
|  * Multi-region adds massive complexity — only do if required           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 23.3: DESIGN PHASE QUESTIONS (ASK DURING DEEP DIVE)

### API DESIGN QUESTIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  QUESTIONS WHEN DESIGNING APIS                                          |
|                                                                         |
|  1. REST vs gRPC vs GraphQL — any preference?                           |
|     "Are there existing services using a specific protocol?"            |
|                                                                         |
|  2. Do we need pagination? If so, cursor-based or offset?               |
|     "How many results should a single page return?"                     |
|                                                                         |
|  3. Do we need rate limiting? Per user? Per API key?                    |
|                                                                         |
|  4. Do we need versioning? (v1, v2 running simultaneously)              |
|                                                                         |
|  5. Who are the API consumers?                                          |
|     * Internal microservices only?                                      |
|     * External third-party developers?                                  |
|     * Mobile clients with intermittent connectivity?                    |
|                                                                         |
|  6. Do we need idempotency for write APIs?                              |
|     "What happens if the client retries the same request?"              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DATABASE CHOICE QUESTIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  QUESTIONS WHEN PICKING A DATABASE                                      |
|                                                                         |
|  1. Do we need transactions across multiple entities?                   |
|     YES -> SQL / NewSQL                                                 |
|     NO  -> NoSQL may be fine                                            |
|                                                                         |
|  2. What's the query pattern?                                           |
|     * Key-value lookups -> Redis, DynamoDB                              |
|     * Complex joins -> PostgreSQL                                       |
|     * Time-series -> InfluxDB, TimescaleDB                              |
|     * Full-text search -> Elasticsearch                                 |
|     * Graph traversals -> Neo4j                                         |
|                                                                         |
|  3. Write-heavy or read-heavy?                                          |
|     * Write-heavy -> Cassandra, append-only logs                        |
|     * Read-heavy -> read replicas, caching                              |
|                                                                         |
|  4. Do we need to shard? What's a good shard key?                       |
|     "What field do most queries filter on?"                             |
|                                                                         |
|  5. How big will the dataset be in 1 year? 5 years?                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CACHING QUESTIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  QUESTIONS WHEN ADDING CACHING                                          |
|                                                                         |
|  1. What's the cache hit rate we expect?                                |
|     (80/20 rule: 20% of data serves 80% of reads?)                      |
|                                                                         |
|  2. How stale can cached data be?                                       |
|     * Real-time: no caching or very short TTL                           |
|     * Seconds: session data, user profile                               |
|     * Minutes: product catalog, feed                                    |
|     * Hours: static config, feature flags                               |
|                                                                         |
|  3. What's the cache invalidation strategy?                             |
|     "When the data changes, how do we update the cache?"                |
|                                                                         |
|  4. What if cache goes down? Can we survive a cold start?               |
|     (thundering herd / cache stampede)                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### MESSAGE QUEUE QUESTIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  QUESTIONS WHEN ADDING ASYNC PROCESSING                                 |
|                                                                         |
|  1. Does ordering matter?                                               |
|     * Strict order -> Kafka with partition key                          |
|     * No order needed -> SQS, RabbitMQ                                  |
|                                                                         |
|  2. What if a consumer fails? Retry? Dead letter queue?                 |
|                                                                         |
|  3. How long should messages be retained?                               |
|     * Process and delete -> SQS                                         |
|     * Retain for replay -> Kafka                                        |
|                                                                         |
|  4. Do multiple consumers need the same message?                        |
|     * Fan-out -> SNS + SQS, Kafka consumer groups                       |
|     * Single consumer -> simple queue                                   |
|                                                                         |
|  5. What's the acceptable processing delay?                             |
|     * Near real-time (< 1s) -> Kafka, Redis Streams                     |
|     * Minutes ok -> SQS, batch processing                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 23.4: SYSTEM-SPECIFIC QUESTIONS BY DESIGN TYPE

### URL SHORTENER / KEY-VALUE SYSTEMS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  * How long should URLs persist? Forever or with expiration?            |
|  * Can the same long URL map to multiple short URLs?                    |
|  * Do we need analytics (click count, geo, referrer)?                   |
|  * Custom aliases allowed? What character set?                          |
|  * What's the expected read:write ratio? (heavily read-biased)          |
|  * Peak QPS for redirects?                                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CHAT / MESSAGING SYSTEMS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  * 1:1 only or group chats? Max group size?                             |
|  * Do we need message persistence or is ephemeral ok?                   |
|  * Read receipts? Typing indicators? Online presence?                   |
|  * Do we need end-to-end encryption?                                    |
|  * File/image sharing? Max size?                                        |
|  * Message ordering guarantees within a conversation?                   |
|  * Do we need offline message delivery?                                 |
|  * Push notifications for mobile?                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SOCIAL MEDIA / NEWS FEED

```
+-------------------------------------------------------------------------+
|                                                                         |
|  * Push model (fan-out on write) or pull model (fan-out on read)?       |
|  * How is the feed ranked? Chronological or algorithmic?                |
|  * Do celebrity users (millions of followers) need special handling?    |
|  * Do we need real-time feed updates or periodic refresh?               |
|  * What content types? (text, images, video, links)                     |
|  * Do we need content moderation?                                       |
|  * What's the average follower count? What's the max?                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### E-COMMERCE / BOOKING SYSTEMS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  * How do we handle concurrent booking of the same item/seat?           |
|    (optimistic locking? pessimistic? reservation with timeout?)         |
|  * What's the payment flow? Do we handle payments or delegate?          |
|  * What happens if payment fails after booking?                         |
|    (saga pattern? compensation transaction?)                            |
|  * Do we need inventory management? Real-time stock count?              |
|  * Flash sale / high-concurrency scenario — how many concurrent users?  |
|  * Do we need a cart? Cart expiry?                                      |
|  * Pricing consistency — can price change mid-checkout?                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### RIDE-SHARING / LOCATION SYSTEMS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  * How often do drivers send location updates? (every 3-5 sec?)         |
|  * How do we match riders to drivers? Nearest? ETA-based?               |
|  * Do we need surge/dynamic pricing?                                    |
|  * What's the acceptable matching latency?                              |
|  * How do we handle driver/rider cancellations?                         |
|  * Do we need trip tracking in real-time?                               |
|  * Geospatial indexing: geohash, quadtree, or H3?                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### NOTIFICATION SYSTEMS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  * What channels? (push, SMS, email, in-app)                            |
|  * Do we need delivery guarantees? (at-least-once?)                     |
|  * User preferences — can users opt out of certain types?               |
|  * Rate limiting per user? (don't spam)                                 |
|  * Priority levels? (critical alerts vs marketing)                      |
|  * Template support? Personalization?                                   |
|  * Do we need delivery receipts / read tracking?                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### VIDEO STREAMING / STORAGE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  * Live streaming or on-demand or both?                                 |
|  * What resolutions do we need to support? (360p to 4K?)                |
|  * Do we need adaptive bitrate streaming?                               |
|  * What's the average video size / duration?                            |
|  * Do we need transcoding? To how many formats?                         |
|  * CDN for global delivery?                                             |
|  * Content moderation / copyright detection?                            |
|  * DRM (Digital Rights Management)?                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 23.5: QUESTIONS THAT SHOW SENIOR THINKING

```
+--------------------------------------------------------------------------+
|                                                                          |
|  OPERATIONAL / PRODUCTION READINESS                                      |
|                                                                          |
|  1. "How do we deploy changes safely?"                                   |
|     -> Shows you think about blue-green, canary, feature flags           |
|                                                                          |
|  2. "What metrics should we monitor?"                                    |
|     -> Shows you think about observability (latency, errors, queues)     |
|                                                                          |
|  3. "How do we handle a sudden 10x traffic spike?"                       |
|     -> Shows you think about auto-scaling, circuit breakers, backpressure|
|                                                                          |
|  4. "What's the blast radius if this component fails?"                   |
|     -> Shows you think about fault isolation, bulkheads                  |
|                                                                          |
|  5. "How do we test this at scale before going to production?"           |
|     -> Shows you think about load testing, chaos engineering             |
|                                                                          |
|  6. "Do we need backward compatibility for API changes?"                 |
|     -> Shows you think about versioning, migration                       |
|                                                                          |
|  7. "What's the cost profile? Are we optimizing for cost or speed?"      |
|     -> Shows you think about real-world constraints                      |
|                                                                          |
|  8. "How do we handle data migration from the old system?"               |
|     -> Shows you think about brownfield, not just greenfield             |
|                                                                          |
|  9. "Do we need audit logging for compliance?"                           |
|     -> Shows you think about security, governance                        |
|                                                                          |
|  10. "What's the team size? Does that affect technology choices?"        |
|      -> Shows you understand org constraints affect architecture         |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 23.6: ANTI-PATTERNS — QUESTIONS NOT TO ASK

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DON'T ASK THESE:                                                       |
|                                                                         |
|  X "Should I use React or Vue?"                                         |
|     (Frontend framework choice is not system design)                    |
|                                                                         |
|  X "What language should I use?"                                        |
|     (Doesn't matter at this level — focus on components)                |
|                                                                         |
|  X "Should I use AWS or GCP?"                                           |
|     (Use generic terms: "object storage", "message queue")              |
|                                                                         |
|  X Overly obvious questions you should already know                     |
|     ("What is a load balancer?")                                        |
|                                                                         |
|  X Questions with no impact on the design                               |
|     (Don't ask just to fill time)                                       |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  INSTEAD, FRAME QUESTIONS AS TRADEOFFS:                                 |
|                                                                         |
|  GOOD: "Given that data is read 100x more than written, I'd lean        |
|         toward an eventually consistent cache-aside approach.           |
|         Does the business require stronger consistency here?"           |
|                                                                         |
|  GOOD: "We could do fan-out on write for the feed, but that's           |
|         expensive for celebrity users. Should we optimize for           |
|         the common case or handle celebrities specially?"               |
|                                                                         |
|  GOOD: "I'll assume 99.9% availability is sufficient. Should I          |
|         design for higher?"                                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 23.7: QUICK REFERENCE CHEAT SHEET

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PHASE 1 — REQUIREMENTS (first 5 min):                                  |
|  * Users, scale, growth?                                                |
|  * Core features? (narrow scope)                                        |
|  * Read/write ratio?                                                    |
|  * Consistency vs availability?                                         |
|  * Latency requirements?                                                |
|  * Data size, retention, access patterns?                               |
|                                                                         |
|  PHASE 2 — HIGH LEVEL (next 5-10 min):                                  |
|  * Sync vs async for each operation?                                    |
|  * SQL vs NoSQL? (based on access pattern)                              |
|  * Need caching? How stale is ok?                                       |
|  * Need a queue? Ordering matter?                                       |
|  * Need real-time? (WebSocket vs polling)                               |
|                                                                         |
|  PHASE 3 — DEEP DIVE (next 15-20 min):                                  |
|  * How to handle hot spots / hot keys?                                  |
|  * How to handle concurrent writes?                                     |
|  * What's the failure mode for each component?                          |
|  * How to scale the bottleneck?                                         |
|  * How to handle the edge case of [specific scenario]?                  |
|                                                                         |
|  PHASE 4 — WRAP UP (last 5 min):                                        |
|  * Monitoring and alerting?                                             |
|  * Deployment strategy?                                                 |
|  * Future improvements / things I'd add with more time?                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

END OF CHAPTER 23
