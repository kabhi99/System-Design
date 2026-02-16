# CHAPTER 1: SCALABILITY
*The Art of Handling Growth*

Scalability is the ability of a system to handle increased load by adding
resources. It's the foundation of every distributed system and the first
concept you must master.

## SECTION 1.1: WHAT IS SCALABILITY?

### DEFINING SCALABILITY

Scalability is NOT about speed. It's about maintaining performance as load
increases.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCALABILITY ILLUSTRATED                                                |
|                                                                         |
|  Response Time                                                          |
|       |                                                                 |
|       |                        / Non-scalable system                    |
|       |                      /   (response time increases rapidly)      |
|       |                    /                                            |
|       |                  /                                              |
|       |                /                                                |
|       |              /     _______________                              |
|       |            /      /               Scalable system               |
|       |          /     /                  (response time stable)        |
|       |        /    /                                                   |
|       |______/___/_________________________________________             |
|       +----------------------------------------------------> Load       |
|                                                                         |
|  A scalable system maintains consistent performance as load grows.      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SCALABILITY vs PERFORMANCE vs ELASTICITY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KEY DISTINCTIONS                                                       |
|                                                                         |
|  PERFORMANCE                                                            |
|  -----------                                                            |
|  How fast does the system respond under current load?                   |
|  Measured by: Latency, throughput at a fixed point in time              |
|                                                                         |
|  SCALABILITY                                                            |
|  -----------                                                            |
|  Can the system maintain performance as load increases?                 |
|  Measured by: How performance degrades (or doesn't) with load           |
|                                                                         |
|  ELASTICITY                                                             |
|  ----------                                                             |
|  Can the system automatically adjust resources based on demand?         |
|  Measured by: How quickly the system scales up/down                     |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  EXAMPLE:                                                               |
|                                                                         |
|  System A: Handles 1000 RPS at 50ms latency                             |
|           At 2000 RPS: 100ms latency (still good)                       |
|           At 5000 RPS: 500ms latency (degraded but functional)          |
|           > Scalable but requires manual intervention                   |
|                                                                         |
|  System B: Same as A, but                                               |
|           Automatically spins up more servers when load > 1500 RPS      |
|           Automatically scales down when load < 500 RPS                 |
|           > Scalable AND elastic                                        |
|                                                                         |
|  CLOUD-NATIVE = Scalable + Elastic + Cost-efficient                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### TYPES OF SCALING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  VERTICAL SCALING (Scale Up)                                            |
|  ===========================                                            |
|                                                                         |
|  Add more power to existing machine:                                    |
|  * More CPU cores                                                       |
|  * More RAM                                                             |
|  * Faster storage (SSD, NVMe)                                           |
|  * Better network (10G, 25G, 100G)                                      |
|                                                                         |
|  +----------------+         +------------------------+                  |
|  |    Server      |         |       Server           |                  |
|  |                |  --->   |                        |                  |
|  |  4 CPU, 8GB    |         |  32 CPU, 128GB         |                  |
|  +----------------+         +------------------------+                  |
|       Before                        After                               |
|                                                                         |
|  PROS:                                                                  |
|  Y Simple - no code changes required                                    |
|  Y No distributed system complexity                                     |
|  Y Strong consistency (single machine)                                  |
|  Y Lower operational overhead                                           |
|                                                                         |
|  CONS:                                                                  |
|  X Hardware limits (can't scale forever)                                |
|  X Single point of failure                                              |
|  X Expensive at high end (exponential cost)                             |
|  X Downtime for upgrades                                                |
|  X Diminishing returns (2x CPU ! 2x throughput)                         |
|                                                                         |
|  REAL-WORLD LIMITS:                                                     |
|  * AWS largest instance: u-24tb1.metal (448 vCPU, 24TB RAM)             |
|  * Cost: ~$218/hour = ~$160,000/month                                   |
|  * PostgreSQL on such machine: ~100K TPS (impressive but limited)       |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  HORIZONTAL SCALING (Scale Out)                                         |
|  ================================                                       |
|                                                                         |
|  Add more machines:                                                     |
|                                                                         |
|  +----------------+         +------+ +------+ +------+ +------+         |
|  |    Server      |         |Server| |Server| |Server| |Server|         |
|  |                |  --->   |      | |      | |      | |      |         |
|  |  4 CPU, 8GB    |         |4/8GB | |4/8GB | |4/8GB | |4/8GB |         |
|  +----------------+         +------+ +------+ +------+ +------+         |
|       Before                        After (4 servers)                   |
|                                                                         |
|  PROS:                                                                  |
|  Y Virtually unlimited scale                                            |
|  Y No single point of failure (with proper design)                      |
|  Y Cost-effective (commodity hardware)                                  |
|  Y Can scale incrementally                                              |
|  Y Geographic distribution possible                                     |
|                                                                         |
|  CONS:                                                                  |
|  X Application must support it (stateless design)                       |
|  X Distributed system complexity                                        |
|  X Network becomes a factor                                             |
|  X Consistency challenges (CAP theorem)                                 |
|  X Operational complexity                                               |
|                                                                         |
|  REAL-WORLD EXAMPLES:                                                   |
|  * Google: Millions of commodity servers                                |
|  * Facebook: Thousands of servers per datacenter                        |
|  * Netflix: 100,000+ AWS instances                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHEN TO USE EACH

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCALING DECISION MATRIX                                                |
|                                                                         |
|  USE VERTICAL WHEN:                                                     |
|  * Early stage startup (simplicity > scale)                             |
|  * Database servers (until you must shard)                              |
|  * Single-threaded workloads                                            |
|  * Memory-bound applications                                            |
|  * Quick fixes for immediate capacity                                   |
|  * Cost of engineering > cost of bigger machine                         |
|                                                                         |
|  USE HORIZONTAL WHEN:                                                   |
|  * Web/API servers (stateless)                                          |
|  * Microservices architecture                                           |
|  * Very high throughput requirements                                    |
|  * High availability requirements                                       |
|  * Geographic distribution needed                                       |
|  * Cost matters at scale                                                |
|                                                                         |
|  TYPICAL EVOLUTION:                                                     |
|                                                                         |
|  Phase 1: Single server (MVP)                                           |
|      v                                                                  |
|  Phase 2: Bigger server (vertical scaling)                              |
|      v                                                                  |
|  Phase 3: Add replicas for reads (horizontal for reads)                 |
|      v                                                                  |
|  Phase 4: Add app servers behind load balancer                          |
|      v                                                                  |
|  Phase 5: Shard database (horizontal for writes)                        |
|      v                                                                  |
|  Phase 6: Microservices (functional decomposition)                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.2: THE SCALE CUBE (AKF SCALE CUBE)

The Scale Cube is a model for scaling applications in three dimensions:

```
+-------------------------------------------------------------------------+
|                                                                         |
|                        THE AKF SCALE CUBE                               |
|                                                                         |
|                              Z-Axis                                     |
|                          (Data Partitioning)                            |
|                               |                                         |
|                               |                                         |
|                               |      +------------------+               |
|                               |     /                  /|               |
|                               |    /                  / |               |
|                               |   /                  /  |               |
|                               |  +------------------+   |               |
|                               |  |                  |   |               |
|                               |  |                  |   |               |
|                               |  |     SCALED       |   |               |
|                               |  |     SYSTEM       |  /                |
|                               |  |                  | /                 |
|                               |  |                  |/                  |
|                               +--+------------------+------> X-Axis     |
|                              /                                          |
|                             /            (Horizontal Cloning)           |
|                            /                                            |
|                           Y-Axis                                        |
|                      (Functional Decomposition)                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### X-AXIS SCALING: HORIZONTAL CLONING

Clone the entire application behind a load balancer.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  X-AXIS: HORIZONTAL CLONING                                             |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                      Load Balancer                                |  |
|  +-------------------------------------------------------------------+  |
|            |              |              |              |               |
|            v              v              v              v               |
|       +--------+    +--------+    +--------+    +--------+              |
|       | App 1  |    | App 2  |    | App 3  |    | App 4  |              |
|       |(clone) |    |(clone) |    |(clone) |    |(clone) |              |
|       +--------+    +--------+    +--------+    +--------+              |
|            |              |              |              |               |
|            +--------------+--------------+--------------+               |
|                                    |                                    |
|                                    v                                    |
|                           +----------------+                            |
|                           |    Database    |                            |
|                           +----------------+                            |
|                                                                         |
|  CHARACTERISTICS:                                                       |
|  * All clones are identical                                             |
|  * Each handles any request                                             |
|  * Requires stateless application design                                |
|  * Database becomes the bottleneck                                      |
|                                                                         |
|  FORMULA:                                                               |
|  If 1 server handles 1000 RPS                                           |
|  N servers handle ~N x 1000 RPS (assuming no bottleneck)                |
|                                                                         |
|  REAL-WORLD: Netflix runs 100,000+ cloned instances                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Y-AXIS SCALING: FUNCTIONAL DECOMPOSITION

Split by function (microservices).

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Y-AXIS: FUNCTIONAL DECOMPOSITION (MICROSERVICES)                       |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                       Monolith                                    |  |
|  |  +-------------------------------------------------------------+  |  |
|  |  |  Users  |  Orders  |  Payments  |  Inventory  |  Search     |  |  |
|  |  +-------------------------------------------------------------+  |  |
|  +-------------------------------------------------------------------+  |
|                              |                                          |
|                              v  Decompose by business domain            |
|                                                                         |
|  +--------+ +--------+ +----------+ +-----------+ +--------+            |
|  | User   | | Order  | | Payment  | | Inventory | | Search |            |
|  |Service | |Service | | Service  | |  Service  | |Service |            |
|  |        | |        | |          | |           | |        |            |
|  | Own DB | | Own DB | |  Own DB  | |  Own DB   | | Elastic|            |
|  +--------+ +--------+ +----------+ +-----------+ +--------+            |
|                                                                         |
|  EACH SERVICE CAN:                                                      |
|  * Scale independently (Search needs more instances)                    |
|  * Use different technologies (Search uses Elasticsearch)               |
|  * Deploy independently                                                 |
|  * Have different SLAs                                                  |
|                                                                         |
|  AMAZON EXAMPLE:                                                        |
|  Single page on Amazon.com calls 100-150 different services!            |
|  Product info, reviews, recommendations, pricing, inventory...          |
|                                                                         |
|  UBER EXAMPLE:                                                          |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |   Rider App    Driver App    Eats App    Business Portal          |  |
|  |       |             |            |              |                 |  |
|  |       +-------------+------------+--------------+                 |  |
|  |                         |                                         |  |
|  |                    API Gateway                                    |  |
|  |                         |                                         |  |
|  |    +--------------------+--------------------+                    |  |
|  |    |                    |                    |                    |  |
|  | Trip Service     User Service     Payment Service                 |  |
|  | Match Service    Pricing Service  Notification Service            |  |
|  | Map Service      Surge Service    Rating Service                  |  |
|  | ETA Service      Promo Service    Support Service                 |  |
|  |                                                                   |  |
|  | (2,000+ microservices)                                            |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Z-AXIS SCALING: DATA PARTITIONING (SHARDING)

Split data across databases.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Z-AXIS: DATA PARTITIONING (SHARDING)                                   |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                       All Data                                    |  |
|  |                    (100M users)                                   |  |
|  +-------------------------------------------------------------------+  |
|                              |                                          |
|                              v  Partition by user_id                    |
|                                                                         |
|       +--------------+  +--------------+  +--------------+              |
|       |   Shard 1    |  |   Shard 2    |  |   Shard 3    |              |
|       | Users A-H    |  | Users I-P    |  | Users Q-Z    |              |
|       |  (~33M)      |  |  (~33M)      |  |  (~33M)      |              |
|       +--------------+  +--------------+  +--------------+              |
|                                                                         |
|  EACH SHARD:                                                            |
|  * Handles subset of data                                               |
|  * Has own compute resources                                            |
|  * Can have its own replicas                                            |
|                                                                         |
|  INSTAGRAM EXAMPLE:                                                     |
|  * 12,000 PostgreSQL shards                                             |
|  * Sharded by user_id                                                   |
|  * Each shard: ~12TB                                                    |
|                                                                         |
|  FACEBOOK EXAMPLE:                                                      |
|  * User data sharded by user_id                                         |
|  * Photos sharded by photo_id                                           |
|  * Different sharding keys for different data types                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMBINING ALL THREE AXES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PRODUCTION SYSTEM USING ALL THREE AXES                                 |
|                                                                         |
|                        +----------------+                               |
|                        |   API Gateway  |                               |
|                        +----------------+                               |
|                               |                                         |
|           +-----------------+++------------------+                      |
|           v                 v v                  v                      |
|     +----------+     +----------+        +----------+                   |
|     | User     |     | Order    |        | Payment  |  Y-Axis           |
|     | Service  |     | Service  |        | Service  |  (Functional)     |
|     +----------+     +----------+        +----------+                   |
|           |                |                   |                        |
|     +-----+-----+    +-----+-----+      +-----+-----+                   |
|     v     v     v    v     v     v      v     v     v  X-Axis           |
|   [1]   [2]   [3]  [1]   [2]   [3]    [1]   [2]   [3]  (Cloning)        |
|     |     |     |    |     |     |      |     |     |                   |
|     +-----+-----+    +-----+-----+      +-----+-----+                   |
|           |                |                   |                        |
|     +-----+-----+    +-----+-----+      +-----+-----+                   |
|     v     v     v    v     v     v      v           v  Z-Axis           |
|   [S1]  [S2]  [S3] [S1]  [S2]  [S3]   [S1]        [S2]  (Sharding)      |
|                                                                         |
|  Each service:                                                          |
|  * Split by function (Y)                                                |
|  * Multiple instances (X)                                               |
|  * Sharded database (Z)                                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.3: STATELESS vs STATEFUL SERVICES

### THE STATEFULNESS PROBLEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  STATEFUL SERVICE                                                       |
|  ===================                                                    |
|                                                                         |
|  Server stores session/user state in memory:                            |
|                                                                         |
|  Request 1 --> Server A (stores session)                                |
|  Request 2 --> Server B (no session!) X FAILS                           |
|                                                                         |
|  PROBLEMS:                                                              |
|  * User must always hit the same server                                 |
|  * Server failure = lost sessions                                       |
|  * Can't easily add/remove servers                                      |
|  * Uneven load distribution                                             |
|                                                                         |
|  "STICKY SESSIONS" WORKAROUND:                                          |
|  +-------------------------------------------------------------------+  |
|  |                   Load Balancer                                   |  |
|  |         (routes User A always to Server 1)                        |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  STILL HAS PROBLEMS:                                                    |
|  X Uneven load distribution                                             |
|  X Server failure still loses sessions                                  |
|  X Scaling down is complicated (session migration)                      |
|  X Rolling updates are hard                                             |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  STATELESS SERVICE (RECOMMENDED)                                        |
|  ================================                                       |
|                                                                         |
|  Server stores NO state. State is stored externally:                    |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                    Load Balancer                                  |  |
|  +-------------------------------------------------------------------+  |
|            |              |              |              |               |
|            v              v              v              v               |
|       +--------+    +--------+    +--------+    +--------+              |
|       |Server 1|    |Server 2|    |Server 3|    |Server 4|              |
|       |(no     |    |(no     |    |(no     |    |(no     |              |
|       | state) |    | state) |    | state) |    | state) |              |
|       +--------+    +--------+    +--------+    +--------+              |
|            |              |              |              |               |
|            +--------------+--------------+--------------+               |
|                              |                                          |
|                              v                                          |
|  +-------------------------------------------------------------------+  |
|  |              External State Store (Redis Cluster)                 |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  BENEFITS:                                                              |
|  Y Any request can hit any server                                       |
|  Y Easy to scale (add/remove servers instantly)                         |
|  Y Server failure doesn't lose sessions                                 |
|  Y Even load distribution                                               |
|  Y Rolling updates are trivial                                          |
|  Y Cloud-native and container-friendly                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### MAKING SERVICES STATELESS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  STRATEGIES FOR STATELESS DESIGN                                        |
|                                                                         |
|  1. EXTERNAL SESSION STORE                                              |
|  ---------------------------                                            |
|  Store sessions in Redis or Memcached                                   |
|                                                                         |
|  # Instead of:                                                          |
|  session['user_id'] = 123  # Stored in server memory                    |
|                                                                         |
|  # Use:                                                                 |
|  redis.set(f"session:{session_id}", user_data, ex=3600)                 |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  2. JWT TOKENS (Stateless Authentication)                               |
|  ------------------------------------------                             |
|  Token contains all user info, signed by server                         |
|                                                                         |
|  JWT Token Structure:                                                   |
|  +-------------------------------------------------------------------+  |
|  |  Header:     { "alg": "HS256", "typ": "JWT" }                     |  |
|  |  Payload:    { "user_id": 123, "role": "admin", "exp": ... }      |  |
|  |  Signature:  HMAC(header + payload, secret_key)                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Server validates token signature - no session lookup needed!           |
|                                                                         |
|  PROS: Truly stateless, great for microservices                         |
|  CONS: Can't invalidate tokens easily (use short TTL + refresh)         |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  3. DATABASE-BACKED STATE                                               |
|  ----------------------------                                           |
|  User preferences, settings in database                                 |
|                                                                         |
|  SELECT preferences FROM users WHERE id = ?                             |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  4. CLIENT-SIDE STATE                                                   |
|  ------------------------                                               |
|  Client sends all needed data with each request                         |
|                                                                         |
|  POST /api/checkout                                                     |
|  {                                                                      |
|    "cart_items": [...],    // Client sends cart                         |
|    "shipping_address": {...},                                           |
|    "payment_method": {...}                                              |
|  }                                                                      |
|                                                                         |
|  PROS: Maximum statelessness                                            |
|  CONS: Larger payloads, security concerns                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### REAL-WORLD STATELESS ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NETFLIX STATELESS ARCHITECTURE                                         |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Client Device                                                    |  |
|  |  (TV, Phone, Browser)                                             |  |
|  |       |                                                           |  |
|  |       | JWT Token in header                                       |  |
|  |       v                                                           |  |
|  |  API Gateway (Zuul)                                               |  |
|  |       |                                                           |  |
|  |       v                                                           |  |
|  |  Stateless Microservices <---- NO session state                   |  |
|  |  (Hundreds of services)                                           |  |
|  |       |                                                           |  |
|  |       |                                                           |  |
|  |       +--> EVCache (Memcached cluster) <-- Session/cache          |  |
|  |       +--> Cassandra                    <-- User data             |  |
|  |       +--> MySQL                        <-- Billing               |  |
|  |                                                                   |  |
|  |  Result: Any request can be handled by any service instance       |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.4: LITTLE'S LAW & CAPACITY PLANNING

### LITTLE'S LAW

The fundamental formula connecting throughput, latency, and concurrency.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LITTLE'S LAW                                                           |
|                                                                         |
|                    L = A x W                                            |
|                                                                         |
|  Where:                                                                 |
|  L = Average number of items in system (concurrent requests)            |
|  A = Average arrival rate (requests per second)                         |
|  W = Average time in system (latency)                                   |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  EXAMPLE 1: CAPACITY PLANNING                                           |
|  -----------------------------                                          |
|                                                                         |
|  Given:                                                                 |
|  * Your service handles requests with 100ms latency (W = 0.1s)          |
|  * You need to handle 10,000 requests/second (L = 10,000)               |
|                                                                         |
|  Question: How many concurrent connections do you need?                 |
|                                                                         |
|  L = A x W = 10,000 x 0.1 = 1,000 concurrent connections                |
|                                                                         |
|  If each server handles 100 concurrent connections:                     |
|  You need: 1,000 / 100 = 10 servers                                     |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  EXAMPLE 2: IMPACT OF LATENCY                                           |
|  --------------------------------                                       |
|                                                                         |
|  If latency increases to 500ms (due to slow database):                  |
|                                                                         |
|  L = 10,000 x 0.5 = 5,000 concurrent connections                        |
|                                                                         |
|  You now need 50 servers!                                               |
|  > 5x more servers just because latency increased 5x                    |
|                                                                         |
|  LESSON: Reducing latency saves infrastructure costs!                   |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  EXAMPLE 3: THREAD POOL SIZING                                          |
|  ------------------------------                                         |
|                                                                         |
|  Your service makes HTTP calls that take 200ms                          |
|  You need to handle 500 RPS                                             |
|                                                                         |
|  Minimum threads needed:                                                |
|  L = 500 x 0.2 = 100 threads                                            |
|                                                                         |
|  Add buffer for safety: 150-200 threads                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### THE UNIVERSAL SCALABILITY LAW (USL)

Why systems don't scale linearly.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  UNIVERSAL SCALABILITY LAW                                              |
|                                                                         |
|                           N                                             |
|  Throughput(N) = -----------------------------                          |
|                   1 + s(N-1) + kN(N-1)                                  |
|                                                                         |
|  Where:                                                                 |
|  N = Number of processors/servers                                       |
|  s = Contention coefficient (serialization/locking)                     |
|  k = Coherence coefficient (communication overhead)                     |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  THROUGHPUT vs NODES GRAPH:                                             |
|                                                                         |
|  Throughput                                                             |
|       |                    . . .                                        |
|       |                  .       .  < Peak (retrograde begins)          |
|       |               .            .                                    |
|       |            .                 . < k > 0 (coherence overhead)     |
|       |         .                      .                                |
|       |       .    _____________________ < s > 0 (contention)           |
|       |     .   _/                                                      |
|       |   .  _/                                                         |
|       |  . /                                                            |
|       | /  < Linear (ideal)                                             |
|       |/                                                                |
|       +------------------------------------------------> Nodes          |
|                                                                         |
|  WHAT CAUSES CONTENTION (s):                                            |
|  * Locks (database locks, mutex)                                        |
|  * Shared resources (single database)                                   |
|  * Sequential processing                                                |
|                                                                         |
|  WHAT CAUSES COHERENCE OVERHEAD (k):                                    |
|  * Cache invalidation across nodes                                      |
|  * Consensus protocols (Paxos, Raft)                                    |
|  * Distributed locking                                                  |
|  * Data synchronization                                                 |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  PRACTICAL IMPLICATIONS:                                                |
|                                                                         |
|  1. MINIMIZE SHARED STATE                                               |
|     * Use stateless services                                            |
|     * Shard data to reduce cross-node communication                     |
|                                                                         |
|  2. REDUCE CONTENTION                                                   |
|     * Use optimistic locking instead of pessimistic                     |
|     * Design lock-free algorithms where possible                        |
|     * Avoid single points of serialization                              |
|                                                                         |
|  3. ACCEPT THAT SCALING HAS LIMITS                                      |
|     * Adding more nodes eventually has negative returns                 |
|     * Plan for architectural changes, not just adding nodes             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### AMDAHL'S LAW

The theoretical speedup limit of parallelization.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  AMDAHL'S LAW                                                           |
|                                                                         |
|                      1                                                  |
|  Speedup(N) = -----------------                                         |
|                (1 - P) + P/N                                            |
|                                                                         |
|  Where:                                                                 |
|  P = Fraction of parallelizable work                                    |
|  N = Number of processors                                               |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  EXAMPLE:                                                               |
|                                                                         |
|  Your request processing:                                               |
|  * 10% sequential (authentication, single DB write)                     |
|  * 90% parallelizable (computations, independent queries)               |
|                                                                         |
|  P = 0.9                                                                |
|                                                                         |
|  With N processors:                                                     |
|  --------------------------------------------------------------------   |
|  N = 2:    Speedup = 1 / (0.1 + 0.9/2)   = 1.82x                        |
|  N = 4:    Speedup = 1 / (0.1 + 0.9/4)   = 3.08x                        |
|  N = 10:   Speedup = 1 / (0.1 + 0.9/10)  = 5.26x                        |
|  N = 100:  Speedup = 1 / (0.1 + 0.9/100) = 9.17x                        |
|  N = ~:    Speedup = 1 / 0.1             = 10x (MAXIMUM!)               |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  VISUALIZATION:                                                         |
|                                                                         |
|  Speedup                                                                |
|       |                                                                 |
|   20 |        P=95% _________________________                           |
|       |           _/                                                    |
|   15 |         _/                                                       |
|       |       _/                                                        |
|   10 |_____/________ P=90% _________________                            |
|       |    /                                                            |
|    5 |  / _____ P=75% ______________________                            |
|       | //                                                              |
|    1 |/_____ P=50% _________________________                            |
|       +--------------------------------------------> Processors         |
|                                                                         |
|  LESSON:                                                                |
|  The sequential part LIMITS scalability.                                |
|  Focus on parallelizing or optimizing the sequential parts.             |
|  Even 10% sequential code limits you to 10x speedup max!                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.5: SLIs, SLOs, AND SLAs

Defining and measuring reliability and performance.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SLI - SERVICE LEVEL INDICATORS                                         |
|  ==============================                                         |
|                                                                         |
|  Quantitative measures of service behavior.                             |
|                                                                         |
|  COMMON SLIs:                                                           |
|                                                                         |
|  AVAILABILITY SLI                                                       |
|  ------------------                                                     |
|            Successful requests                                          |
|  SLI = ------------------------- x 100                                  |
|            Total requests                                               |
|                                                                         |
|  LATENCY SLI                                                            |
|  ---------------                                                        |
|  P50 (median): 50% of requests faster than X ms                         |
|  P95: 95% of requests faster than X ms                                  |
|  P99: 99% of requests faster than X ms                                  |
|                                                                         |
|  WHY P99 MATTERS MORE THAN AVERAGE:                                     |
|  ------------------------------------                                   |
|  Average latency: 50ms                                                  |
|  P99 latency: 2000ms                                                    |
|                                                                         |
|  With 1M daily users, 10,000 users experience 2+ second delays!         |
|  The average hides this pain.                                           |
|                                                                         |
|  THROUGHPUT SLI                                                         |
|  ----------------                                                       |
|  Requests per second (RPS)                                              |
|  Transactions per second (TPS)                                          |
|  Messages processed per second                                          |
|                                                                         |
|  ERROR RATE SLI                                                         |
|  ---------------                                                        |
|            Failed requests                                              |
|  SLI = ------------------- x 100                                        |
|         Total requests                                                  |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  SLO - SERVICE LEVEL OBJECTIVES                                         |
|  ==============================                                         |
|                                                                         |
|  Target values for SLIs. Internal goals.                                |
|                                                                         |
|  EXAMPLE SLOs:                                                          |
|  * Availability: 99.9% (three nines)                                    |
|  * P99 Latency: < 200ms                                                 |
|  * Error rate: < 0.1%                                                   |
|                                                                         |
|  THE NINES OF AVAILABILITY:                                             |
|  ----------------------------                                           |
|  +------------+-------------------------------------------------------+ |
|  | Availability | Downtime per year | Downtime per month              | |
|  +------------+-------------------------------------------------------+ |
|  | 90%        | 36.5 days         | 3 days                            | |
|  | 99%        | 3.65 days         | 7.3 hours                         | |
|  | 99.9%      | 8.76 hours        | 43.8 minutes                      | |
|  | 99.95%     | 4.38 hours        | 21.9 minutes                      | |
|  | 99.99%     | 52.6 minutes      | 4.38 minutes                      | |
|  | 99.999%    | 5.26 minutes      | 26 seconds                        | |
|  +------------+-------------------------------------------------------+ |
|                                                                         |
|  REAL-WORLD SLOs:                                                       |
|  * AWS S3: 99.9% availability (SLA), targets 99.99%+ (SLO)              |
|  * Google Cloud SQL: 99.95% (regional), 99.99% (multi-zone)             |
|  * Stripe API: P50 < 100ms, P99 < 1000ms                                |
|                                                                         |
|  ERROR BUDGETS:                                                         |
|  ----------------                                                       |
|  If SLO is 99.9%, your error budget is 0.1%                             |
|                                                                         |
|  Per month: 43.8 minutes of downtime allowed                            |
|                                                                         |
|  If you've used 40 minutes this month:                                  |
|  * Freeze risky deployments                                             |
|  * Focus on reliability over features                                   |
|  * Incident review and improvements                                     |
|                                                                         |
|  Error budget creates healthy tension between:                          |
|  * Feature velocity (Dev wants to ship)                                 |
|  * Reliability (Ops wants stability)                                    |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  SLA - SERVICE LEVEL AGREEMENT                                          |
|  =============================                                          |
|                                                                         |
|  Legal contract with consequences for missing targets.                  |
|                                                                         |
|  SLAs are typically LESS stringent than SLOs                            |
|  (Buffer for operational issues)                                        |
|                                                                         |
|  EXAMPLE (AWS RDS SLA):                                                 |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Monthly Uptime %    |  Service Credit %                          |  |
|  |  -------------------------------------------                      |  |
|  |  Less than 99.95%    |  10%                                       |  |
|  |  Less than 99.0%     |  25%                                       |  |
|  |  Less than 95.0%     |  100%                                      |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  RELATIONSHIP:                                                          |
|                                                                         |
|  SLI (what you measure) > SLO (what you aim for) > SLA (what you        |
|                                                          promise)       |
|                                                                         |
|  Example:                                                               |
|  SLI: Current availability = 99.93%                                     |
|  SLO: Target availability = 99.95%                                      |
|  SLA: Promised availability = 99.9%                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.6: IDENTIFYING AND RESOLVING BOTTLENECKS

### COMMON BOTTLENECKS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BOTTLENECK ANALYSIS                                                    |
|                                                                         |
|  1. DATABASE BOTTLENECK                                                 |
|  -------------------------                                              |
|  SYMPTOMS:                                                              |
|  * Slow queries                                                         |
|  * High database CPU                                                    |
|  * Connection pool exhaustion                                           |
|  * Replication lag                                                      |
|                                                                         |
|  SOLUTIONS:                                                             |
|  * Add read replicas (scale reads)                                      |
|  * Implement caching (reduce DB load by 90%+)                           |
|  * Optimize queries (indexes, EXPLAIN ANALYZE)                          |
|  * Shard the database (scale writes)                                    |
|  * Use connection pooling (PgBouncer, HikariCP)                         |
|  * Denormalize for read performance                                     |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  2. APPLICATION SERVER BOTTLENECK                                       |
|  ------------------------------------                                   |
|  SYMPTOMS:                                                              |
|  * High CPU/memory on app servers                                       |
|  * Long response times even with fast DB                                |
|  * Thread pool exhaustion                                               |
|  * Garbage collection pauses                                            |
|                                                                         |
|  SOLUTIONS:                                                             |
|  * Add more app servers (horizontal scale)                              |
|  * Profile and optimize code (flame graphs)                             |
|  * Async processing for heavy tasks                                     |
|  * Increase server resources (vertical scale)                           |
|  * Use async I/O (Node.js, async Python, Go)                            |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  3. NETWORK BOTTLENECK                                                  |
|  --------------------------                                             |
|  SYMPTOMS:                                                              |
|  * High network latency                                                 |
|  * Packet loss                                                          |
|  * Bandwidth saturation                                                 |
|  * TCP connection timeouts                                              |
|                                                                         |
|  SOLUTIONS:                                                             |
|  * CDN for static content                                               |
|  * Compress data (gzip, brotli)                                         |
|  * Reduce payload size (pagination, field selection)                    |
|  * Use faster network (10G, 25G)                                        |
|  * Geo-distributed deployment                                           |
|  * HTTP/2 or gRPC (multiplexing)                                        |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  4. I/O BOTTLENECK                                                      |
|  ------------------                                                     |
|  SYMPTOMS:                                                              |
|  * High disk wait time (iowait)                                         |
|  * Slow file operations                                                 |
|  * Log file growth issues                                               |
|                                                                         |
|  SOLUTIONS:                                                             |
|  * Use SSDs instead of HDDs                                             |
|  * Implement caching (memory is faster than disk)                       |
|  * Use memory-mapped files                                              |
|  * Batch I/O operations                                                 |
|  * Async writes (write-behind)                                          |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  5. EXTERNAL SERVICE BOTTLENECK                                         |
|  ---------------------------------                                      |
|  SYMPTOMS:                                                              |
|  * Slow third-party API calls                                           |
|  * Timeouts to external services                                        |
|  * Cascading failures                                                   |
|                                                                         |
|  SOLUTIONS:                                                             |
|  * Circuit breakers (fail fast)                                         |
|  * Caching external responses                                           |
|  * Async calls with queues                                              |
|  * Fallback mechanisms                                                  |
|  * Bulkhead pattern (isolation)                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SCALABILITY PATTERNS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  COMMON SCALABILITY PATTERNS                                            |
|                                                                         |
|  1. CACHING                                                             |
|     Cache frequently accessed data                                      |
|     Can reduce database load by 90%+                                    |
|     Types: CDN, application, distributed (Redis)                        |
|                                                                         |
|  2. ASYNC PROCESSING                                                    |
|     Move heavy tasks to background workers                              |
|     Use message queues (Kafka, RabbitMQ, SQS)                           |
|     Respond immediately, process later                                  |
|                                                                         |
|  3. DATABASE REPLICATION                                                |
|     Read replicas for read-heavy workloads                              |
|     Primary handles writes, replicas handle reads                       |
|     80-90% of traffic is often reads                                    |
|                                                                         |
|  4. DATABASE SHARDING                                                   |
|     Distribute data across multiple databases                           |
|     Each shard handles subset of data                                   |
|     Enables write scaling                                               |
|                                                                         |
|  5. CDN (Content Delivery Network)                                      |
|     Serve static content from edge locations                            |
|     Reduces latency and server load                                     |
|     ~50% of internet traffic goes through CDNs                          |
|                                                                         |
|  6. MICROSERVICES                                                       |
|     Split monolith into independent services                            |
|     Each service scales independently                                   |
|     Different SLAs per service                                          |
|                                                                         |
|  7. CIRCUIT BREAKERS                                                    |
|     Prevent cascading failures                                          |
|     Fail fast when downstream is unhealthy                              |
|     Auto-recovery when healthy                                          |
|                                                                         |
|  8. RATE LIMITING                                                       |
|     Protect services from overload                                      |
|     Fair resource allocation                                            |
|     Prevent abuse                                                       |
|                                                                         |
|  9. BULKHEAD PATTERN                                                    |
|     Isolate failures to prevent spread                                  |
|     Separate thread pools per service                                   |
|     Like ship compartments                                              |
|                                                                         |
|  10. GRACEFUL DEGRADATION                                               |
|      Serve reduced functionality when overloaded                        |
|      Return cached data when fresh unavailable                          |
|      Disable non-essential features                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.7: REAL-WORLD SCALING EXAMPLES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TWITTER SCALING JOURNEY                                                |
|                                                                         |
|  2006: Ruby on Rails monolith, MySQL                                    |
|        v                                                                |
|  2008: "Fail Whale" - Ruby couldn't handle load                         |
|        v                                                                |
|  2010: Rewrote in Scala, added caching                                  |
|        v                                                                |
|  2012: Timeline moved to Redis, fan-out on write                        |
|        v                                                                |
|  2015: Manhattan (distributed database) for storage                     |
|        v                                                                |
|  Now:  ~500M tweets/day, 200K+ RPS                                      |
|                                                                         |
|  KEY LESSONS:                                                           |
|  * Started simple, scaled as needed                                     |
|  * Cache heavily (Redis for timelines)                                  |
|  * Fan-out on write vs fan-out on read                                  |
|  * Custom solutions when off-the-shelf doesn't work                     |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  INSTAGRAM SCALING (1 Billion Users, 13 Engineers)                      |
|                                                                         |
|  PRINCIPLES:                                                            |
|  1. Keep it simple                                                      |
|  2. Don't reinvent the wheel                                            |
|  3. Use proven technologies                                             |
|                                                                         |
|  TECH STACK:                                                            |
|  * Python + Django (simple, productive)                                 |
|  * PostgreSQL (sharded by user_id)                                      |
|  * Redis (caching, sessions)                                            |
|  * Memcached (caching)                                                  |
|  * RabbitMQ (async tasks)                                               |
|  * Cassandra (feed storage)                                             |
|                                                                         |
|  SCALING APPROACH:                                                      |
|  * 12,000+ PostgreSQL shards                                            |
|  * Heavy caching at every layer                                         |
|  * Async processing for non-critical paths                              |
|  * Gradual migration (not big-bang rewrites)                            |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  NETFLIX SCALING                                                        |
|                                                                         |
|  ARCHITECTURE:                                                          |
|  * 100% on AWS (no own datacenters)                                     |
|  * Microservices (1000+ services)                                       |
|  * Zuul (API Gateway)                                                   |
|  * Eureka (Service Discovery)                                           |
|  * Hystrix (Circuit Breaker)                                            |
|  * EVCache (Distributed Memcached)                                      |
|                                                                         |
|  SCALE:                                                                 |
|  * 200+ million subscribers                                             |
|  * 15% of global internet bandwidth                                     |
|  * 100,000+ AWS instances                                               |
|  * ~10M device connections per region                                   |
|                                                                         |
|  KEY INNOVATIONS:                                                       |
|  * Chaos engineering (Chaos Monkey)                                     |
|  * Everything is stateless                                              |
|  * Multi-region active-active                                           |
|  * Continuous deployment                                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCALABILITY - KEY TAKEAWAYS                                            |
|                                                                         |
|  TYPES OF SCALING                                                       |
|  -----------------                                                      |
|  * Vertical: More power to one machine (simple but limited)             |
|  * Horizontal: More machines (complex but unlimited)                    |
|                                                                         |
|  SCALE CUBE                                                             |
|  ----------                                                             |
|  * X-Axis: Clone everything (horizontal scaling)                        |
|  * Y-Axis: Split by function (microservices)                            |
|  * Z-Axis: Split by data (sharding)                                     |
|                                                                         |
|  STATELESS SERVICES                                                     |
|  ------------------                                                     |
|  * Store state externally (Redis, database)                             |
|  * Any request can hit any server                                       |
|  * Easy to scale horizontally                                           |
|  * Use JWT for stateless auth                                           |
|                                                                         |
|  LAWS & FORMULAS                                                        |
|  ----------------                                                       |
|  * Little's Law: L = A x W (capacity planning)                          |
|  * Amdahl's Law: Sequential parts limit speedup                         |
|  * USL: Contention + coherence limit scaling                            |
|                                                                         |
|  SLIs/SLOs/SLAs                                                         |
|  -------------                                                          |
|  * SLI: What you measure (latency, availability)                        |
|  * SLO: Internal targets (99.9% availability)                           |
|  * SLA: Customer promise (with penalties)                               |
|  * Error budget: Acceptable failure allowance                           |
|                                                                         |
|  BOTTLENECKS                                                            |
|  -----------                                                            |
|  * Database, Application, Network, I/O, External                        |
|  * Solve: Caching, Async, Replication, Sharding, CDN                    |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  INTERVIEW TIPS                                                         |
|  --------------                                                         |
|                                                                         |
|  1. Always discuss trade-offs:                                          |
|     "We can scale this by..., but the trade-off is..."                  |
|                                                                         |
|  2. Know your numbers:                                                  |
|     * 1 server ~ 1000-10000 RPS (depends on workload)                   |
|     * Redis: 100K+ ops/sec per instance                                 |
|     * PostgreSQL: 10-50K TPS (depends on query)                         |
|                                                                         |
|  3. Start simple, scale as needed:                                      |
|     "For 100 users, we don't need this..."                              |
|     "At 1M users, we'd need to..."                                      |
|                                                                         |
|  4. Mention monitoring:                                                 |
|     "We'd track SLIs and set up alerts for..."                          |
|                                                                         |
|  5. Reference real systems:                                             |
|     "Similar to how Netflix/Uber/Twitter handles..."                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 1

