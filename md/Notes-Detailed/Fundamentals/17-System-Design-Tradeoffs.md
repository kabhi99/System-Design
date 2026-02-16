# CHAPTER 17: SYSTEM DESIGN TRADEOFFS
*Key Decisions Every Architect Must Make*

Every system design involves tradeoffs. Understanding these helps you make
informed decisions and explain your choices in interviews.

## SECTION 17.1: STATEFUL vs STATELESS DESIGN

```
+-------------------------------------------------------------------------+
|                                                                         |
|  STATELESS SERVICE                                                      |
|  ==================                                                     |
|                                                                         |
|  Server doesn't store any client session data.                          |
|  Each request contains all information needed to process it.            |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Request 1 --> Server A --> Response                              |  |
|  |  Request 2 --> Server B --> Response  (different server, OK!)     |  |
|  |  Request 3 --> Server C --> Response                              |  |
|  |                                                                   |  |
|  |  Each request is independent, any server can handle it            |  |
|  |                                                                   |  |
|  |  Example: REST API with JWT token                                 |  |
|  |  +-------------------------------------------------------------+  |  |
|  |  |  GET /api/orders                                            |  |  |
|  |  |  Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6...      |  |  |
|  |  |                                                             |  |  |
|  |  |  Token contains user_id, roles, expiry                      |  |  |
|  |  |  Server validates token, doesn't need session               |  |  |
|  |  +-------------------------------------------------------------+  |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  PROS:                                                                  |
|  Y Easy to scale horizontally (add more servers)                        |
|  Y Any server can handle any request                                    |
|  Y No session synchronization needed                                    |
|  Y Better fault tolerance (server crash doesn't lose state)             |
|  Y Simpler load balancing                                               |
|                                                                         |
|  CONS:                                                                  |
|  X Larger request size (must send context each time)                    |
|  X More processing per request (validate tokens)                        |
|  X Some use cases need state (shopping cart, wizard flows)              |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  STATEFUL SERVICE                                                       |
|  =================                                                      |
|                                                                         |
|  Server maintains client session data between requests.                 |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Request 1 --> Server A --> Store session --> Response            |  |
|  |  Request 2 --> Server A --> Use session --> Response              |  |
|  |  Request 3 --> Server B --> Session not found! ERROR!             |  |
|  |                                                                   |  |
|  |  Must route same user to same server (sticky sessions)            |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  EXAMPLES:                                                              |
|  * WebSocket connections                                                |
|  * In-memory session stores                                             |
|  * Game servers (player state)                                          |
|  * Chat servers (connection state)                                      |
|                                                                         |
|  PROS:                                                                  |
|  Y Smaller requests (no repeated context)                               |
|  Y Faster (no token validation, cached session)                         |
|  Y Natural for real-time applications                                   |
|                                                                         |
|  CONS:                                                                  |
|  X Hard to scale (session affinity needed)                              |
|  X Server failure loses session                                         |
|  X Complex load balancing (sticky sessions)                             |
|  X Session synchronization overhead                                     |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  MAKING STATEFUL SYSTEMS MORE SCALABLE                                  |
|                                                                         |
|  1. EXTERNALIZE STATE                                                   |
|     Store session in Redis instead of server memory                     |
|     Any server can access session from Redis                            |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Request --> Any Server --> Redis (session) --> Response          |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  2. STICKY SESSIONS WITH FALLBACK                                       |
|     Route to same server, but have backup in Redis                      |
|                                                                         |
|  RECOMMENDATION:                                                        |
|  Default to stateless, use Redis/external store when state needed       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 17.2: PUSH vs PULL ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PULL (Polling)                                                         |
|  ===============                                                        |
|                                                                         |
|  Client periodically asks server for updates                            |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Client                                Server                     |  |
|  |     |                                     |                       |  |
|  |     |---- Any updates? ----------------->|                        |  |
|  |     |<---- No ----------------------------|                       |  |
|  |     |                                     |                       |  |
|  |     |  (wait 5 seconds)                   |                       |  |
|  |     |                                     |                       |  |
|  |     |---- Any updates? ----------------->|                        |  |
|  |     |<---- No ----------------------------|                       |  |
|  |     |                                     |                       |  |
|  |     |  (wait 5 seconds)                   |                       |  |
|  |     |                                     |                       |  |
|  |     |---- Any updates? ----------------->|                        |  |
|  |     |<---- Yes, here's data --------------|                       |  |
|  |     |                                     |                       |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  PROS:                                                                  |
|  Y Simple to implement                                                  |
|  Y Works everywhere (HTTP)                                              |
|  Y Client controls timing                                               |
|  Y Stateless server                                                     |
|                                                                         |
|  CONS:                                                                  |
|  X Wasted requests (most return empty)                                  |
|  X Delayed updates (up to polling interval)                             |
|  X Server load from frequent polling                                    |
|                                                                         |
|  USE: Email checking, news feeds, background sync                       |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  PUSH                                                                   |
|  ====                                                                   |
|                                                                         |
|  Server sends updates to client when they occur                         |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Client                                Server                     |  |
|  |     |                                     |                       |  |
|  |     |---- Subscribe -------------------->|                        |  |
|  |     |<---- Connection established --------|                       |  |
|  |     |                                     |                       |  |
|  |     |  (waiting...)                       | (event occurs)        |  |
|  |     |                                     |                       |  |
|  |     |<---- Here's update! ----------------|                       |  |
|  |     |                                     |                       |  |
|  |     |  (waiting...)                       | (event occurs)        |  |
|  |     |                                     |                       |  |
|  |     |<---- Here's update! ----------------|                       |  |
|  |     |                                     |                       |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  IMPLEMENTATIONS:                                                       |
|  * WebSockets                                                           |
|  * Server-Sent Events (SSE)                                             |
|  * Long Polling                                                         |
|  * Push Notifications (mobile)                                          |
|                                                                         |
|  PROS:                                                                  |
|  Y Real-time updates (instant)                                          |
|  Y Efficient (no wasted requests)                                       |
|  Y Lower latency                                                        |
|                                                                         |
|  CONS:                                                                  |
|  X Connection management complexity                                     |
|  X Stateful (server tracks connections)                                 |
|  X Scaling challenges                                                   |
|  X Network/firewall issues                                              |
|                                                                         |
|  USE: Chat, live sports, stock tickers, collaborative editing           |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  COMPARISON                                                             |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |  Aspect          Pull (Polling)       Push                       |   |
|  |  ------------------------------------------------------------    |   |
|  |                                                                  |   |
|  |  Latency         High (interval)      Low (instant)              |   |
|  |  Server Load     Higher (many polls)  Lower (on-demand)          |   |
|  |  Complexity      Simple               Complex                    |   |
|  |  Scalability     Easier               Harder                     |   |
|  |  Connection      Stateless            Stateful                   |   |
|  |  Real-time       No                   Yes                        |   |
|  |  Battery (mobile) Higher              Lower                      |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  HYBRID APPROACH:                                                       |
|  Use push for real-time needs, pull for initial load/sync               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 17.3: CONCURRENCY vs PARALLELISM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CONCURRENCY                                                            |
|  ===========                                                            |
|                                                                         |
|  Dealing with multiple tasks at once (structure)                        |
|  Tasks can START before others FINISH                                   |
|  May not actually run simultaneously                                    |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  SINGLE CPU (Concurrency via context switching):                  |  |
|  |                                                                   |  |
|  |  Time ----------------------------------------------------->      |  |
|  |                                                                   |  |
|  |  Task A: ####....####....####....                                 |  |
|  |  Task B: ....####....####....####                                 |  |
|  |                                                                   |  |
|  |  Only ONE task runs at any moment, but both PROGRESS              |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  EXAMPLE: Single-threaded event loop (Node.js)                          |
|  * Handle 1000 concurrent connections                                   |
|  * Only ONE executing at a time                                         |
|  * Switch when waiting for I/O                                          |
|                                                                         |
|  GOOD FOR: I/O-bound tasks (waiting for network, disk)                  |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  PARALLELISM                                                            |
|  ===========                                                            |
|                                                                         |
|  Actually executing multiple tasks simultaneously                       |
|  Requires multiple CPU cores                                            |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  MULTI CPU (True parallelism):                                    |  |
|  |                                                                   |  |
|  |  Time ----------------------------------------------------->      |  |
|  |                                                                   |  |
|  |  CPU 1 - Task A: ####################                             |  |
|  |  CPU 2 - Task B: ####################                             |  |
|  |  CPU 3 - Task C: ####################                             |  |
|  |  CPU 4 - Task D: ####################                             |  |
|  |                                                                   |  |
|  |  ALL tasks run at the SAME TIME on different cores                |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  EXAMPLE: Video encoding                                                |
|  * Split video into chunks                                              |
|  * Encode each chunk on different CPU                                   |
|  * 4 cores = ~4x faster                                                 |
|                                                                         |
|  GOOD FOR: CPU-bound tasks (computation, encoding)                      |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  KEY DIFFERENCE                                                         |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |  Concurrency: "Dealing with" multiple things                     |   |
|  |  Parallelism: "Doing" multiple things                            |   |
|  |                                                                  |   |
|  |  Concurrency is about STRUCTURE                                  |   |
|  |  Parallelism is about EXECUTION                                  |   |
|  |                                                                  |   |
|  |  You can have:                                                   |   |
|  |  * Concurrency without parallelism (single core)                 |   |
|  |  * Parallelism without concurrency (SIMD operations)             |   |
|  |  * Both (multi-threaded on multi-core)                           |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  PRACTICAL EXAMPLES:                                                    |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |  Task Type       Best Approach        Example                    |   |
|  |  ------------------------------------------------------------    |   |
|  |                                                                  |   |
|  |  I/O Bound       Concurrency          Web server handling        |   |
|  |                  (async/await)        many connections           |   |
|  |                                                                  |   |
|  |  CPU Bound       Parallelism          Image processing,          |   |
|  |                  (multi-process)      ML training                |   |
|  |                                                                  |   |
|  |  Mixed           Both                 Web server with            |   |
|  |                                       background workers         |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 17.4: SYNCHRONOUS vs ASYNCHRONOUS COMMUNICATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SYNCHRONOUS                                                            |
|  ===========                                                            |
|                                                                         |
|  Caller waits for response before continuing                            |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Service A                                Service B               |  |
|  |      |                                        |                   |  |
|  |      |-------- HTTP Request ----------------->|                   |  |
|  |      |                                        |                   |  |
|  |      |          (A is BLOCKED)                | (processing)      |  |
|  |      |                                        |                   |  |
|  |      |<------- HTTP Response -----------------|                   |  |
|  |      |                                        |                   |  |
|  |      | (A continues)                          |                   |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  PROTOCOLS: HTTP, gRPC, direct function calls                           |
|                                                                         |
|  PROS:                                                                  |
|  Y Simple to understand and implement                                   |
|  Y Immediate response                                                   |
|  Y Easy error handling                                                  |
|  Y Strong consistency (see result immediately)                          |
|                                                                         |
|  CONS:                                                                  |
|  X Caller blocked during request                                        |
|  X Tight coupling                                                       |
|  X Cascading failures                                                   |
|  X Both services must be available                                      |
|                                                                         |
|  USE: User-facing requests, queries needing immediate response          |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  ASYNCHRONOUS                                                           |
|  ============                                                           |
|                                                                         |
|  Caller continues immediately, response comes later (or never)          |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Service A             Queue              Service B               |  |
|  |      |                   |                    |                   |  |
|  |      |-- Publish msg --->|                    |                   |  |
|  |      |<-- ACK -----------|                    |                   |  |
|  |      |                   |                    |                   |  |
|  |      | (A continues      |-- Deliver msg ---->|                   |  |
|  |      |  immediately)     |                    | (processing)      |  |
|  |      |                   |                    |                   |  |
|  |      |                   |<-- ACK ------------|                   |  |
|  |      |                   |                    |                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  PROTOCOLS: Message queues (Kafka, RabbitMQ, SQS), webhooks             |
|                                                                         |
|  PROS:                                                                  |
|  Y Loose coupling                                                       |
|  Y Better fault tolerance                                               |
|  Y Handles traffic spikes (queue buffers)                               |
|  Y Services can be offline temporarily                                  |
|  Y Independent scaling                                                  |
|                                                                         |
|  CONS:                                                                  |
|  X More complex                                                         |
|  X Eventual consistency                                                 |
|  X Debugging harder                                                     |
|  X Delivery guarantees to manage                                        |
|                                                                         |
|  USE: Background jobs, notifications, event-driven workflows            |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  COMPARISON                                                             |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |  Aspect          Synchronous          Asynchronous               |   |
|  |  ------------------------------------------------------------    |   |
|  |                                                                  |   |
|  |  Coupling        Tight                Loose                      |   |
|  |  Response        Immediate            Eventually                 |   |
|  |  Complexity      Simple               Complex                    |   |
|  |  Fault Tolerance Lower                Higher                     |   |
|  |  Scalability     Limited              Better                     |   |
|  |  Consistency     Strong               Eventual                   |   |
|  |  Debugging       Easier               Harder                     |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 17.5: LATENCY vs THROUGHPUT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DEFINITIONS                                                            |
|                                                                         |
|  LATENCY: Time to complete ONE request (response time)                  |
|  THROUGHPUT: Number of requests completed per unit time                 |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  HIGHWAY ANALOGY:                                                 |  |
|  |                                                                   |  |
|  |  Latency = Time for ONE car to travel from A to B                 |  |
|  |  Throughput = Number of cars passing per hour                     |  |
|  |                                                                   |  |
|  |  You can have:                                                    |  |
|  |  * Low latency, low throughput (empty highway, drive fast)        |  |
|  |  * High latency, high throughput (traffic, many cars moving)      |  |
|  |  * High latency, low throughput (traffic jam!)                    |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  TRADEOFFS                                                              |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  OPTIMIZE FOR LATENCY:                                            |  |
|  |                                                                   |  |
|  |  * Process one request immediately                                |  |
|  |  * No batching                                                    |  |
|  |  * Keep queues short                                              |  |
|  |                                                                   |  |
|  |  Example: Real-time trading                                       |  |
|  |  - Every millisecond matters                                      |  |
|  |  - Process each trade immediately                                 |  |
|  |                                                                   |  |
|  |  ------------------------------------------------------------     |  |
|  |                                                                   |  |
|  |  OPTIMIZE FOR THROUGHPUT:                                         |  |
|  |                                                                   |  |
|  |  * Batch requests together                                        |  |
|  |  * Amortize overhead                                              |  |
|  |  * Use queues                                                     |  |
|  |                                                                   |  |
|  |  Example: Data pipeline                                           |  |
|  |  - Process 1M records/hour                                        |  |
|  |  - Individual record latency doesn't matter                       |  |
|  |  - Batch for efficiency                                           |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  LITTLE'S LAW:                                                          |
|  L = L x W                                                              |
|  (Concurrent requests = Arrival rate x Average time in system)          |
|                                                                         |
|  To handle 1000 req/sec with 100ms latency:                             |
|  Concurrent = 1000 x 0.1 = 100 concurrent connections needed            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 17.6: CONSISTENCY vs AVAILABILITY (CAP Context)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  See Chapter 2 (CAP-And-Consistency.txt) for full details               |
|                                                                         |
|  QUICK SUMMARY:                                                         |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |  STRONG CONSISTENCY (CP)                                         |   |
|  |  * All nodes see same data at same time                          |   |
|  |  * May reject requests during partition                          |   |
|  |  * Use: Banking, inventory                                       |   |
|  |  * Systems: Zookeeper, etcd, HBase                               |   |
|  |                                                                  |   |
|  |  EVENTUAL CONSISTENCY (AP)                                       |   |
|  |  * Nodes may temporarily have different data                     |   |
|  |  * Always accepts requests                                       |   |
|  |  * Use: Social media, caching                                    |   |
|  |  * Systems: Cassandra, DynamoDB, CouchDB                         |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  SPECTRUM OF CONSISTENCY:                                               |
|                                                                         |
|  Strong <--------------------------------------------> Eventual         |
|  Linearizable > Sequential > Causal > Read-your-writes > Eventual       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 17.7: SQL vs NoSQL

```
+-------------------------------------------------------------------------+
|                                                                         |
|  See Chapter 5 (Databases.txt) for full details                         |
|                                                                         |
|  QUICK COMPARISON:                                                      |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |  Aspect          SQL                  NoSQL                      |   |
|  |  ------------------------------------------------------------    |   |
|  |                                                                  |   |
|  |  Schema          Fixed, predefined    Flexible, dynamic          |   |
|  |  Relationships   JOINs, foreign keys  Denormalized, embedded     |   |
|  |  Scaling         Vertical (mainly)    Horizontal                 |   |
|  |  ACID            Yes                  Usually BASE               |   |
|  |  Query Language  SQL (standard)       Varies by database         |   |
|  |  Best For        Complex queries,     High scale, flexible       |   |
|  |                  transactions         schema, simple queries     |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  WHEN SQL:                                                              |
|  * Complex relationships, JOINs                                         |
|  * ACID transactions required                                           |
|  * Well-defined, stable schema                                          |
|  * Complex queries (analytics)                                          |
|                                                                         |
|  WHEN NoSQL:                                                            |
|  * Massive scale needed                                                 |
|  * Flexible/evolving schema                                             |
|  * Simple access patterns (key-value)                                   |
|  * Geographic distribution                                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 17.8: MONOLITH vs MICROSERVICES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  See Microservices Architecture files for full details                  |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |  Aspect          Monolith             Microservices              |   |
|  |  ------------------------------------------------------------    |   |
|  |                                                                  |   |
|  |  Deployment      Single unit          Many small units           |   |
|  |  Scaling         All or nothing       Independent                |   |
|  |  Team Size       Any                  Large, distributed         |   |
|  |  Complexity      Lower initially      Higher                     |   |
|  |  Latency         Lower (in-process)   Higher (network)           |   |
|  |  Debugging       Easier               Harder                     |   |
|  |  Tech Stack      Single               Polyglot                   |   |
|  |  Fault Isolation None                 Per-service                |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  WHEN MONOLITH:                                                         |
|  * Small team (< 10 developers)                                         |
|  * Simple domain                                                        |
|  * Startup/MVP phase                                                    |
|  * Low operational maturity                                             |
|                                                                         |
|  WHEN MICROSERVICES:                                                    |
|  * Large team, multiple squads                                          |
|  * Complex domain                                                       |
|  * Different scaling needs                                              |
|  * Frequent, independent deployments                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 17.9: ALL TRADEOFFS SUMMARY TABLE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MASTER TRADEOFFS TABLE                                                 |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |  Tradeoff              Option A           Option B               |   |
|  |  ------------------------------------------------------------    |   |
|  |                                                                  |   |
|  |  State                 Stateless          Stateful               |   |
|  |                        (scale easy)       (simpler logic)        |   |
|  |                                                                  |   |
|  |  Updates               Pull (simple)      Push (real-time)       |   |
|  |                                                                  |   |
|  |  Processing            Concurrent         Parallel               |   |
|  |                        (I/O bound)        (CPU bound)            |   |
|  |                                                                  |   |
|  |  Communication         Sync (simple)      Async (resilient)      |   |
|  |                                                                  |   |
|  |  Optimize              Latency            Throughput             |   |
|  |                        (fast response)    (high volume)          |   |
|  |                                                                  |   |
|  |  CAP                   Consistency        Availability           |   |
|  |                        (correct data)     (always respond)       |   |
|  |                                                                  |   |
|  |  Database              SQL (ACID,         NoSQL (scale,          |   |
|  |                        complex queries)   flexible schema)       |   |
|  |                                                                  |   |
|  |  Architecture          Monolith           Microservices          |   |
|  |                        (simple)           (scalable)             |   |
|  |                                                                  |   |
|  |  Data Processing       Batch              Stream                 |   |
|  |                        (high volume)      (real-time)            |   |
|  |                                                                  |   |
|  |  Cache Strategy        Read-through       Write-through          |   |
|  |                        (read heavy)       (write consistency)    |   |
|  |                                                                  |   |
|  |  Scaling               Vertical           Horizontal             |   |
|  |                        (simple, limited)  (complex, infinite)    |   |
|  |                                                                  |   |
|  |  API Style             REST (standard)    RPC (fast)             |   |
|  |                                                                  |   |
|  |  Real-time             Long Polling       WebSockets             |   |
|  |                        (simpler)          (efficient)            |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  KEY PRINCIPLE:                                                         |
|  There is no "best" choice. Every decision depends on:                  |
|  * Requirements (functional and non-functional)                         |
|  * Scale and traffic patterns                                           |
|  * Team size and expertise                                              |
|  * Budget and timeline                                                  |
|  * Operational maturity                                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 17

