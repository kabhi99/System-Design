# SYSTEM DESIGN MASTERY ROADMAP
*From Fundamentals to Production-Grade Architectures*

This roadmap provides a structured learning path for mastering system design.
Whether you're preparing for interviews or building real systems, follow this
sequence for optimal understanding.

ESTIMATED TOTAL TIME: 10-14 weeks (2-3 hours/day)

## LEARNING PATH OVERVIEW

```
+-------------------------------------------------------------------------+
|                                                                         |
|                THE COMPLETE SYSTEM DESIGN JOURNEY                      |
|                                                                         |
|  PHASE 1: FUNDAMENTALS (Week 1-3)                                      |
|  =================================                                      |
|  +-- Scalability Basics                                                |
|  +-- CAP Theorem & Consistency Models                                  |
|  +-- Load Balancing                                                    |
|  +-- Caching Strategies                                                |
|  +-- Database Fundamentals (SQL vs NoSQL)                             |
|  +-- Sharding & Replication                                           |
|  +-- Message Queues & Async Processing                                |
|                                                                         |
|                          v                                              |
|                                                                         |
|  PHASE 2: BUILDING BLOCKS (Week 3-5)                                   |
|  =====================================                                  |
|  +-- API Design (REST, GraphQL, gRPC)                                 |
|  +-- Authentication & Authorization                                   |
|  +-- Rate Limiting & Throttling                                       |
|  +-- CDN & Edge Computing                                             |
|  +-- Search Systems (Elasticsearch)                                   |
|  +-- Distributed Locking                                              |
|  +-- Event-Driven Architecture                                        |
|                                                                         |
|                          v                                              |
|                                                                         |
|  PHASE 3: DATA SYSTEMS (Week 5-7)                                      |
|  ==================================                                     |
|  +-- Distributed Databases                                            |
|  +-- Distributed Cache (Redis, Memcached)                             |
|  +-- Time-Series Databases                                            |
|  +-- Data Lakes & Warehouses                                          |
|  +-- Stream Processing (Kafka, Flink)                                |
|  +-- ACID vs BASE Transactions                                        |
|                                                                         |
|                          v                                              |
|                                                                         |
|  PHASE 4: PATTERNS & PRACTICES (Week 7-9)                              |
|  ===========================================                            |
|  +-- Microservices Architecture                                       |
|  +-- SAGA Pattern & Distributed Transactions                          |
|  +-- CQRS & Event Sourcing                                            |
|  +-- Circuit Breaker & Bulkhead                                       |
|  +-- Idempotency & Exactly-Once Delivery                              |
|  +-- Eventual Consistency Patterns                                    |
|                                                                         |
|                          v                                              |
|                                                                         |
|  PHASE 5: REAL-WORLD SYSTEMS (Week 9-12)                               |
|  =========================================                              |
|  +-- Ticket Booking System (BookMyShow)                               |
|  +-- E-Commerce Platform                                              |
|  +-- Ride-Sharing System (Uber)                                       |
|  +-- Social Media Feed                                                |
|  +-- URL Shortener                                                    |
|  +-- Chat System                                                      |
|                                                                         |
|                          v                                              |
|                                                                         |
|  PHASE 6: ADVANCED TOPICS (Week 12-14)                                 |
|  =======================================                                |
|  +-- Global Scale Distribution                                        |
|  +-- Multi-Region Active-Active                                       |
|  +-- Chaos Engineering                                                |
|  +-- Cost Optimization                                                |
|  +-- Security at Scale                                                |
|  +-- Observability & Monitoring                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PHASE 1: FUNDAMENTALS (Week 1-3)

### WHAT YOU'LL LEARN

Before designing any system, you must understand the fundamental concepts
that govern distributed systems. These concepts appear in EVERY system design.

READ IN THIS ORDER:

1. Fundamentals/01-Scalability.txt
- Vertical vs Horizontal scaling
- Stateless vs Stateful services
- Scale cube

2. Fundamentals/02-CAP-And-Consistency.txt
- CAP Theorem explained
- Consistency models (Strong, Eventual, Causal)
- Trade-offs in distributed systems

3. Fundamentals/03-Load-Balancing.txt
- Load balancer types
- Algorithms (Round Robin, Least Connections, etc.)
- Health checks and failover

4. Fundamentals/04-Caching.txt
- Cache strategies (Cache-Aside, Write-Through, etc.)
- Cache invalidation
- Distributed caching

5. Fundamentals/05-Databases.txt
- SQL vs NoSQL
- ACID properties
- Indexing and query optimization

6. Fundamentals/06-Sharding-And-Replication.txt
- Sharding strategies
- Master-Slave replication
- Consistency in replicated systems

7. Fundamentals/07-Message-Queues.txt
- Synchronous vs Asynchronous
- Message queue patterns
- Exactly-once, At-least-once, At-most-once

## THE SYSTEM DESIGN INTERVIEW FRAMEWORK

Every system design discussion should follow this framework:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE SYSTEM DESIGN FRAMEWORK                                           |
|                                                                         |
|  STEP 1: REQUIREMENTS CLARIFICATION (5 minutes)                        |
|  ================================================                       |
|  * Functional requirements (What should it do?)                        |
|  * Non-functional requirements (How well should it do it?)            |
|  * Scale requirements (How big?)                                       |
|  * Constraints and assumptions                                        |
|                                                                         |
|  STEP 2: BACK-OF-ENVELOPE CALCULATIONS (5 minutes)                     |
|  ====================================================                   |
|  * Users (DAU, MAU)                                                    |
|  * Traffic (QPS, peak traffic)                                        |
|  * Storage (data growth, retention)                                   |
|  * Bandwidth                                                          |
|                                                                         |
|  STEP 3: HIGH-LEVEL DESIGN (10 minutes)                                |
|  =======================================                                |
|  * Core components                                                     |
|  * Data flow                                                          |
|  * API design                                                         |
|  * Database schema                                                    |
|                                                                         |
|  STEP 4: DETAILED DESIGN (15 minutes)                                  |
|  ======================================                                 |
|  * Deep dive into 2-3 components                                      |
|  * Algorithm choices                                                  |
|  * Data structures                                                    |
|  * Trade-off discussions                                              |
|                                                                         |
|  STEP 5: BOTTLENECKS & SCALE (10 minutes)                              |
|  =========================================                              |
|  * Identify bottlenecks                                               |
|  * How to scale each component                                        |
|  * Failure scenarios and mitigation                                   |
|  * Monitoring and alerting                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## NUMBERS EVERY ENGINEER SHOULD KNOW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LATENCY NUMBERS                                                       |
|  ---------------                                                       |
|  L1 cache reference                           0.5 ns                   |
|  L2 cache reference                           7   ns                   |
|  Main memory reference                       100   ns                   |
|  SSD random read                         150,000   ns = 150 µs         |
|  HDD disk seek                        10,000,000   ns = 10 ms          |
|  Network round trip (same datacenter)    500,000   ns = 0.5 ms         |
|  Network round trip (cross-continent) 150,000,000   ns = 150 ms        |
|                                                                         |
|  THROUGHPUT NUMBERS                                                    |
|  ------------------                                                    |
|  Sequential read from SSD                500 MB/s                      |
|  Sequential read from HDD                100 MB/s                      |
|  Network bandwidth (1 Gbps)              125 MB/s                      |
|  Network bandwidth (10 Gbps)            1250 MB/s                      |
|                                                                         |
|  CAPACITY NUMBERS                                                      |
|  ----------------                                                      |
|  Characters in a URL                     ~100 bytes                    |
|  Characters in a tweet                   ~300 bytes                    |
|  Average web page                        ~2 MB                         |
|  Average photo                           ~200 KB - 5 MB                |
|  Average video (1 minute, 1080p)         ~100 MB                       |
|                                                                         |
|  QUICK CALCULATIONS                                                    |
|  -----------------                                                     |
|  Seconds per day                         86,400 ≈ ~100K                |
|  Seconds per month                       2.6M ≈ ~2.5M                  |
|  Seconds per year                        31M ≈ ~30M                    |
|                                                                         |
|  1 Million requests/day = ~12 QPS                                     |
|  1 Billion requests/day = ~12,000 QPS                                 |
|                                                                         |
|  1 KB = 1,000 bytes                                                   |
|  1 MB = 1,000 KB = 1,000,000 bytes                                    |
|  1 GB = 1,000 MB = 1,000,000,000 bytes                                |
|  1 TB = 1,000 GB = 1,000,000,000,000 bytes                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## FOLDER STRUCTURE

```
/Notes-Detailed/
|
+-- 00-SYSTEM-DESIGN-ROADMAP.txt (This file)
|
+-- Fundamentals/
|   +-- 01-Scalability.txt
|   +-- 02-CAP-And-Consistency.txt
|   +-- 03-Load-Balancing.txt
|   +-- 04-Caching.txt
|   +-- 05-Databases.txt
|   +-- 06-Sharding-And-Replication.txt
|   +-- 07-Message-Queues.txt
|   +-- 08-Distributed-Transactions.txt
|
+-- BookMyShow/
|   +-- 01-Requirements-And-Scale.txt
|   +-- 02-High-Level-Architecture.txt
|   +-- 03-Database-Design.txt
|   +-- 04-Booking-Flow-And-Concurrency.txt
|   +-- 05-Payment-Integration.txt
|   +-- 06-Search-And-Discovery.txt
|   +-- 07-Interview-QA.txt
|
+-- E-Commerce/
|   +-- 01-Requirements-And-Scale.txt
|   +-- 02-High-Level-Architecture.txt
|   +-- 03-Catalog-And-Search.txt
|   +-- 04-Shopping-Cart.txt
|   +-- 05-Checkout-And-Orders.txt
|   +-- 06-Inventory-Management.txt
|   +-- 07-Payment-Processing.txt
|   +-- 08-Interview-QA.txt
|
+-- Uber/
|   +-- 01-Requirements-And-Scale.txt
|   +-- 02-High-Level-Architecture.txt
|   +-- 03-Location-And-Geospatial.txt
|   +-- 04-Matching-Algorithm.txt
|   +-- 05-Real-Time-Tracking.txt
|   +-- 06-Pricing-And-Surge.txt
|   +-- 07-Interview-QA.txt
|
+-- Distributed-Cache/
    +-- 01-Cache-Fundamentals.txt
    +-- 02-Cache-Strategies.txt
    +-- 03-Distributed-Cache-Architecture.txt
    +-- 04-Redis-Deep-Dive.txt
    +-- 05-Cache-Consistency.txt
    +-- 06-Interview-QA.txt
```

## INTERVIEW TIPS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DO's                                                                  |
|  ----                                                                  |
|  Y Clarify requirements before designing                              |
|  Y Think out loud - explain your reasoning                            |
|  Y Draw diagrams as you explain                                       |
|  Y Discuss trade-offs for every decision                              |
|  Y Start simple, then add complexity                                  |
|  Y Consider failure scenarios                                         |
|  Y Mention monitoring and observability                               |
|                                                                         |
|  DON'Ts                                                                |
|  ------                                                                |
|  X Don't jump into solution immediately                               |
|  X Don't ignore scale requirements                                    |
|  X Don't over-engineer for small scale                                |
|  X Don't forget about data consistency                                |
|  X Don't ignore security considerations                               |
|  X Don't give one-sided solutions without trade-offs                  |
|                                                                         |
|  KEYWORDS TO USE                                                       |
|  ---------------                                                       |
|  "Let me clarify the requirements..."                                 |
|  "The trade-off here is..."                                           |
|  "If we had to scale this to..."                                      |
|  "One potential bottleneck is..."                                     |
|  "We could optimize this by..."                                       |
|  "Let's consider the failure scenario..."                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF ROADMAP

