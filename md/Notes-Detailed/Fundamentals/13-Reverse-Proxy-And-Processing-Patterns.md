# CHAPTER 13: REVERSE PROXY, EVENT-DRIVEN ARCHITECTURE,
*AND PROCESSING PATTERNS*

This chapter covers three important topics often asked in system design:
Reverse Proxy, Event-Driven Architecture, and Streaming vs Batch Processing.

## SECTION 13.1: REVERSE PROXY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FORWARD PROXY vs REVERSE PROXY                                        |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  FORWARD PROXY (acts on behalf of CLIENT)                      |  |
|  |                                                                 |  |
|  |  Client ---> Forward Proxy ---> Internet ---> Server          |  |
|  |              (hides client)                                    |  |
|  |                                                                 |  |
|  |  USE CASES:                                                    |  |
|  |  * Hide client IP (privacy)                                   |  |
|  |  * Access restricted content (VPN-like)                       |  |
|  |  * Content filtering (corporate networks)                     |  |
|  |  * Caching for clients                                        |  |
|  |                                                                 |  |
|  |  EXAMPLES: Squid, corporate proxies, VPN                      |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  REVERSE PROXY (acts on behalf of SERVER)                      |  |
|  |                                                                 |  |
|  |  Client ---> Reverse Proxy ---> Backend Servers               |  |
|  |              (hides servers)                                   |  |
|  |                                                                 |  |
|  |  USE CASES:                                                    |  |
|  |  * Hide server topology                                       |  |
|  |  * Load balancing                                             |  |
|  |  * SSL termination                                            |  |
|  |  * Caching                                                     |  |
|  |  * Compression                                                 |  |
|  |  * Security (WAF)                                             |  |
|  |                                                                 |  |
|  |  EXAMPLES: Nginx, HAProxy, Envoy, Traefik                     |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### REVERSE PROXY ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REVERSE PROXY IN A TYPICAL WEB ARCHITECTURE                           |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |               +-------------------------+                      |  |
|  |               |      REVERSE PROXY      |                      |  |
|  |               |        (Nginx)          |                      |  |
|  |               |                         |                      |  |
|  |               |  * SSL Termination      |                      |  |
|  |               |  * Compression          |                      |  |
|  |               |  * Caching              |                      |  |
|  |               |  * Rate Limiting        |                      |  |
|  |               |  * Load Balancing       |                      |  |
|  |               |  * Security Headers     |                      |  |
|  |               +-----------+-------------+                      |  |
|  |                           |                                    |  |
|  |           +---------------+---------------+                    |  |
|  |           |               |               |                    |  |
|  |           v               v               v                    |  |
|  |    +-----------+   +-----------+   +-----------+              |  |
|  |    |  App      |   |  App      |   |  App      |              |  |
|  |    | Server 1  |   | Server 2  |   | Server 3  |              |  |
|  |    +-----------+   +-----------+   +-----------+              |  |
|  |                                                                 |  |
|  |  Clients only see the reverse proxy IP!                       |  |
|  |  Backend servers are hidden from the internet.                |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### REVERSE PROXY FUNCTIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. SSL/TLS TERMINATION                                                |
|  =======================                                                |
|                                                                         |
|  Client --HTTPS--> Reverse Proxy --HTTP--> Backend                     |
|                     (decrypts)             (plain HTTP)                 |
|                                                                         |
|  WHY:                                                                   |
|  * Backend servers don't handle encryption overhead                    |
|  * Centralized certificate management                                  |
|  * Easier certificate renewal (only one place)                        |
|  * Backend servers can be simpler                                      |
|                                                                         |
|  SECURITY NOTE:                                                         |
|  Internal network between proxy and backend should be secured         |
|  (private network, mTLS for sensitive data)                           |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. LOAD BALANCING                                                      |
|  ===================                                                    |
|                                                                         |
|  Distribute requests across backend servers                            |
|                                                                         |
|  ALGORITHMS:                                                            |
|  * Round Robin: Sequential distribution                                |
|  * Least Connections: Send to least busy server                       |
|  * IP Hash: Same client always goes to same server                    |
|  * Weighted: Higher weight = more traffic                             |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. CACHING                                                             |
|  ===========                                                            |
|                                                                         |
|  Cache responses to serve repeated requests faster                     |
|                                                                         |
|  Client ---> Reverse Proxy ---> Cache HIT ---> Return (fast!)        |
|                    |                                                    |
|                    +---> Cache MISS ---> Backend ---> Cache & Return  |
|                                                                         |
|  WHAT TO CACHE:                                                         |
|  * Static files (CSS, JS, images)                                     |
|  * API responses (with proper Cache-Control)                          |
|  * HTML pages (for anonymous users)                                    |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  4. COMPRESSION                                                         |
|  ===============                                                        |
|                                                                         |
|  Compress responses before sending to client                           |
|                                                                         |
|  Backend --> Reverse Proxy --gzip/brotli--> Client                    |
|              (compresses)                    (saves bandwidth)          |
|                                                                         |
|  COMMON FORMATS:                                                        |
|  * gzip: Universal support, good compression                          |
|  * Brotli: Better compression, modern browsers                        |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  5. SECURITY                                                            |
|  ===========                                                            |
|                                                                         |
|  * Rate Limiting: Prevent abuse (429 Too Many Requests)              |
|  * WAF (Web Application Firewall): Block SQL injection, XSS         |
|  * IP Blocking/Allowlisting                                           |
|  * Security Headers: HSTS, X-Frame-Options, CSP                       |
|  * DDoS Protection: Absorb/filter malicious traffic                  |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  6. URL REWRITING / ROUTING                                            |
|  ===========================                                            |
|                                                                         |
|  /api/*        -> API servers                                           |
|  /static/*     -> Static file servers / CDN                            |
|  /admin/*      -> Admin servers (with extra auth)                       |
|  /*            -> Web servers                                            |
|                                                                         |
|  Can also rewrite URLs:                                                 |
|  /old-path -> /new-path (301 redirect)                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### REVERSE PROXY vs API GATEWAY vs LOAD BALANCER

```
+-------------------------------------------------------------------------+
|                                                                         |
|  COMPARISON                                                             |
|                                                                         |
|  +-------------------------------------------------------------------+|
|  |                                                                   ||
|  |  Feature            Reverse Proxy  API Gateway    Load Balancer  ||
|  |  ---------------------------------------------------------------  ||
|  |                                                                   ||
|  |  SSL Termination    [x]              [x]              [x]              ||
|  |  Load Balancing     [x]              [x]              [x] (primary)    ||
|  |  Caching            [x]              Sometimes      [ ]              ||
|  |  Compression        [x]              [ ]              [ ]              ||
|  |  Rate Limiting      [x]              [x]              [ ]              ||
|  |  Authentication     Basic          [x] (OAuth,JWT)  [ ]              ||
|  |  Request Transform  Basic          [x]              [ ]              ||
|  |  API Versioning     [ ]              [x]              [ ]              ||
|  |  Analytics          Basic          [x]              Basic          ||
|  |                                                                   ||
|  +-------------------------------------------------------------------+|
|                                                                         |
|  IN PRACTICE:                                                           |
|  * Small apps: Nginx (reverse proxy) does it all                      |
|  * Microservices: API Gateway + Load Balancers                        |
|  * Enterprise: All three at different layers                          |
|                                                                         |
|  COMMON TOOLS:                                                          |
|  * Reverse Proxy: Nginx, HAProxy, Traefik, Caddy                      |
|  * API Gateway: Kong, AWS API Gateway, Apigee, Zuul                   |
|  * Load Balancer: HAProxy, Nginx, AWS ALB/NLB                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 13.2: EVENT-DRIVEN ARCHITECTURE (EDA)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS EVENT-DRIVEN ARCHITECTURE?                                    |
|                                                                         |
|  A software design pattern where system behavior is determined by      |
|  events - significant changes in state.                                |
|                                                                         |
|  Instead of services calling each other directly (request-response),  |
|  services communicate by producing and consuming EVENTS.               |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  REQUEST-DRIVEN (Traditional):                                 |  |
|  |                                                                 |  |
|  |  Order Service --call--> Inventory --call--> Payment --call--> Shipping|
|  |        |                    |                  |                |
|  |        |<----- response ----+                  |                |
|  |        |<-------------- response --------------+                |
|  |        |<-------------------------- response ------------------+|
|  |                                                                 |  |
|  |  Tight coupling, synchronous, cascading failures               |  |
|  |                                                                 |  |
|  |  ------------------------------------------------------------  |  |
|  |                                                                 |  |
|  |  EVENT-DRIVEN:                                                  |  |
|  |                                                                 |  |
|  |  Order Service --> [OrderCreated event] --> Event Broker       |  |
|  |                                                |                |  |
|  |                         +----------------------+--------------+|  |
|  |                         |                      |              ||  |
|  |                         v                      v              v|  |
|  |                    Inventory              Payment         Shipping|
|  |                    (subscribes)           (subscribes)    (subscribes)|
|  |                                                                 |  |
|  |  Loose coupling, asynchronous, resilient                       |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### KEY CONCEPTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  EVENT                                                                  |
|  =====                                                                  |
|                                                                         |
|  An event represents something that happened (past tense).             |
|  Events are FACTS, they are immutable.                                 |
|                                                                         |
|  Examples:                                                              |
|  * OrderCreated                                                        |
|  * PaymentProcessed                                                    |
|  * UserSignedUp                                                        |
|  * InventoryDepleted                                                   |
|                                                                         |
|  Event Structure:                                                       |
|  {                                                                      |
|    "event_id": "uuid-123",                                             |
|    "event_type": "OrderCreated",                                       |
|    "timestamp": "2024-01-15T10:30:00Z",                                |
|    "source": "order-service",                                          |
|    "data": {                                                           |
|      "order_id": "order-456",                                         |
|      "customer_id": "cust-789",                                       |
|      "total": 99.99,                                                   |
|      "items": [...]                                                    |
|    }                                                                    |
|  }                                                                      |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  PRODUCERS (Publishers)                                                |
|  =======================                                                |
|                                                                         |
|  Services that create and emit events.                                 |
|  Producer doesn't know who will consume the event.                    |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  CONSUMERS (Subscribers)                                               |
|  ========================                                               |
|                                                                         |
|  Services that listen for and react to events.                        |
|  Consumer doesn't know who produced the event.                        |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  EVENT BROKER (Message Broker)                                         |
|  ==============================                                         |
|                                                                         |
|  Infrastructure that receives, stores, and delivers events.            |
|  Decouples producers from consumers.                                   |
|                                                                         |
|  Examples: Kafka, RabbitMQ, AWS EventBridge, Pulsar, Redis Streams    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### EVENT-DRIVEN PATTERNS

```
+------------------------------------------------------------------------------+
|                                                                              |
|  PATTERN 1: SIMPLE EVENT NOTIFICATION                                        |
|                                                                              |
|  +------------------------------------------------------------------------+ |
|  |                                                                        | |
|  |  Producer emits event, consumers react                                | |
|  |                                                                        | |
|  |  Order Service                                                        | |
|  |       |                                                                | |
|  |       | publish("OrderCreated", {order_id: 123})                     | |
|  |       |                                                                | |
|  |       v                                                                | |
|  |  +---------------------+                                              | |
|  |  |    Event Broker     |                                              | |
|  |  |                     |                                              | |
|  |  |  topic: orders      |                                              | |
|  |  +---------+-----------+                                              | |
|  |            |                                                           | |
|  |       +----+----+------------+                                        | |
|  |       v         v            v                                        | |
|  |  Notification  Analytics   Shipping                                   | |
|  |   Service       Service    Service                                    | |
|  |  (send email)  (track)    (prepare)                                  | |
|  |                                                                        | |
|  +------------------------------------------------------------------------+ |
|                                                                              |
|  CHARACTERISTIC: Light event, consumers may need to query for more data    |
|                                                                              |
+------------------------------------------------------------------------------+

+------------------------------------------------------------------------------+
|                                                                              |
|  PATTERN 2: EVENT-CARRIED STATE TRANSFER                                     |
|                                                                              |
|  +------------------------------------------------------------------------+ |
|  |                                                                        | |
|  |  Event contains all data needed, no callbacks required                | |
|  |                                                                        | |
|  |  Order Service publishes:                                             | |
|  |  {                                                                     | |
|  |    "event_type": "OrderCreated",                                      | |
|  |    "data": {                                                          | |
|  |      "order_id": "123",                                               | |
|  |      "customer": {                                                    | |
|  |        "id": "456",                                                   | |
|  |        "name": "John",                                                | |
|  |        "email": "john@example.com"  <- Full customer data             | |
|  |      },                                                               | |
|  |      "items": [...full item details...],                             | |
|  |      "shipping_address": {...}                                        | |
|  |    }                                                                   | |
|  |  }                                                                     | |
|  |                                                                        | |
|  |  Consumers have all data, no need to call other services!            | |
|  |                                                                        | |
|  +------------------------------------------------------------------------+ |
|                                                                              |
|  PROS: Decoupled, resilient, consumers self-sufficient                      |
|  CONS: Larger events, data duplication, stale data possible                |
|                                                                              |
+------------------------------------------------------------------------------+

+------------------------------------------------------------------------------+
|                                                                              |
|  PATTERN 3: EVENT SOURCING                                                   |
|                                                                              |
|  +------------------------------------------------------------------------+ |
|  |                                                                        | |
|  |  Store events as source of truth, derive state from events            | |
|  |                                                                        | |
|  |  Traditional: Store current state                                     | |
|  |  Account { balance: 150 }                                             | |
|  |                                                                        | |
|  |  Event Sourcing: Store all events                                     | |
|  |  Event Log:                                                           | |
|  |  1. AccountCreated  { initial_balance: 0 }                           | |
|  |  2. MoneyDeposited  { amount: 100 }                                  | |
|  |  3. MoneyDeposited  { amount: 100 }                                  | |
|  |  4. MoneyWithdrawn  { amount: 50 }                                   | |
|  |                                                                        | |
|  |  Current balance = replay events = 0 + 100 + 100 - 50 = 150          | |
|  |                                                                        | |
|  |  BENEFITS:                                                            | |
|  |  * Complete audit trail                                              | |
|  |  * Time travel (reconstruct state at any point)                     | |
|  |  * Debug by replaying events                                         | |
|  |  * Easy to add new projections                                       | |
|  |                                                                        | |
|  |  CHALLENGES:                                                          | |
|  |  * Event schema evolution                                            | |
|  |  * Eventual consistency                                              | |
|  |  * Replay performance for long histories                             | |
|  |                                                                        | |
|  +------------------------------------------------------------------------+ |
|                                                                              |
+------------------------------------------------------------------------------+

+------------------------------------------------------------------------------+
|                                                                              |
|  PATTERN 4: CQRS (Command Query Responsibility Segregation)                  |
|                                                                              |
|  +------------------------------------------------------------------------+ |
|  |                                                                        | |
|  |  Separate models for reading and writing                              | |
|  |                                                                        | |
|  |  +---------------------------------------------------------------+   | |
|  |  |                                                               |   | |
|  |  |  WRITE SIDE (Commands)           READ SIDE (Queries)         |   | |
|  |  |                                                               |   | |
|  |  |  CreateOrder ---> Order          GET /orders ---> Order      |   | |
|  |  |                   Service                        Query       |   | |
|  |  |                      |                           Service     |   | |
|  |  |                      |                              ^        |   | |
|  |  |                      v                              |        |   | |
|  |  |                 Write DB          <--- events --- Read DB   |   | |
|  |  |               (normalized)        (async sync)  (denormalized)|   | |
|  |  |                                                               |   | |
|  |  |  Optimized for:                   Optimized for:             |   | |
|  |  |  * Data integrity                 * Fast queries             |   | |
|  |  |  * Transactions                   * Complex joins            |   | |
|  |  |  * Business rules                 * Different views          |   | |
|  |  |                                                               |   | |
|  |  +---------------------------------------------------------------+   | |
|  |                                                                        | |
|  +------------------------------------------------------------------------+ |
|                                                                              |
|  Often combined with Event Sourcing                                         |
|                                                                              |
+------------------------------------------------------------------------------+
```

### EDA BENEFITS AND CHALLENGES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BENEFITS                                                               |
|  ========                                                               |
|                                                                         |
|  [x] LOOSE COUPLING                                                      |
|    Services don't know about each other                               |
|    Add new consumers without changing producers                        |
|                                                                         |
|  [x] SCALABILITY                                                         |
|    Consumers scale independently                                       |
|    Handle traffic spikes with buffering                               |
|                                                                         |
|  [x] RESILIENCE                                                          |
|    Failed consumer doesn't affect producer                            |
|    Events persisted, replay on recovery                               |
|                                                                         |
|  [x] FLEXIBILITY                                                         |
|    Easy to add new functionality                                      |
|    Different consumers can process same event differently             |
|                                                                         |
|  [x] AUDIT TRAIL                                                         |
|    Events provide natural history                                     |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  CHALLENGES                                                             |
|  ==========                                                             |
|                                                                         |
|  [ ] COMPLEXITY                                                          |
|    Harder to trace flow through system                                |
|    Debugging distributed events is difficult                          |
|                                                                         |
|  [ ] EVENTUAL CONSISTENCY                                                |
|    Data may be temporarily inconsistent                               |
|    Must design for this                                               |
|                                                                         |
|  [ ] EVENT ORDERING                                                      |
|    Events may arrive out of order                                     |
|    Need strategies to handle (sequence numbers, timestamps)           |
|                                                                         |
|  [ ] IDEMPOTENCY                                                         |
|    Same event may be delivered multiple times                         |
|    Consumers must handle duplicates                                   |
|                                                                         |
|  [ ] SCHEMA EVOLUTION                                                    |
|    Changing event structure is challenging                            |
|    Backward/forward compatibility needed                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 13.3: STREAMING vs BATCH PROCESSING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TWO PARADIGMS FOR DATA PROCESSING                                     |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  BATCH PROCESSING                                              |  |
|  |  ================                                               |  |
|  |                                                                 |  |
|  |  Process large volumes of data at once, periodically           |  |
|  |                                                                 |  |
|  |  +---------+                                                   |  |
|  |  | Data    |     +------------+     +---------+               |  |
|  |  | Lake/   |---->|   Batch    |---->| Results |               |  |
|  |  | Warehouse|     |   Job      |     |         |               |  |
|  |  +---------+     | (hourly/   |     +---------+               |  |
|  |                  |  daily)    |                                |  |
|  |                  +------------+                                |  |
|  |                                                                 |  |
|  |  CHARACTERISTICS:                                              |  |
|  |  * Process bounded data sets                                  |  |
|  |  * High latency (minutes to hours)                            |  |
|  |  * High throughput                                            |  |
|  |  * Runs periodically (scheduled)                              |  |
|  |                                                                 |  |
|  |  EXAMPLES: Daily reports, ETL jobs, ML training               |  |
|  |  TOOLS: Spark, Hadoop MapReduce, Hive, AWS EMR                |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  STREAM PROCESSING                                              |  |
|  |  =================                                              |  |
|  |                                                                 |  |
|  |  Process data continuously as it arrives                       |  |
|  |                                                                 |  |
|  |  +---------+     +------------+     +---------+               |  |
|  |  | Event   |---->|  Stream    |---->| Real-   |               |  |
|  |  | Stream  |     | Processor  |     | time    |               |  |
|  |  | (Kafka) |     |            |     | Output  |               |  |
|  |  +---------+     +------------+     +---------+               |  |
|  |       |                                                        |  |
|  |       | Continuous flow                                       |  |
|  |       v                                                        |  |
|  |                                                                 |  |
|  |  CHARACTERISTICS:                                              |  |
|  |  * Process unbounded data (never-ending stream)               |  |
|  |  * Low latency (milliseconds to seconds)                      |  |
|  |  * Process one record at a time (or micro-batches)           |  |
|  |  * Runs continuously                                          |  |
|  |                                                                 |  |
|  |  EXAMPLES: Real-time alerts, fraud detection, live dashboards|  |
|  |  TOOLS: Kafka Streams, Flink, Spark Streaming, Storm         |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DETAILED COMPARISON

```
+------------------------------------------------------------------------------+
|                                                                              |
|  BATCH vs STREAM COMPARISON                                                  |
|                                                                              |
|  +------------------------------------------------------------------------+ |
|  |                                                                        | |
|  |  Aspect              Batch                 Stream                      | |
|  |  --------------------------------------------------------------------  | |
|  |                                                                        | |
|  |  Data                Bounded (finite)      Unbounded (infinite)        | |
|  |                                                                        | |
|  |  Latency             High (min-hours)      Low (ms-seconds)            | |
|  |                                                                        | |
|  |  Processing          All at once           As it arrives               | |
|  |                                                                        | |
|  |  Throughput          Very high             Moderate-high               | |
|  |                                                                        | |
|  |  Resource Usage      Burst (during job)    Continuous (always on)      | |
|  |                                                                        | |
|  |  State Management    Simple (fresh start)  Complex (checkpoint)        | |
|  |                                                                        | |
|  |  Failure Recovery    Rerun entire job      Checkpoint & resume         | |
|  |                                                                        | |
|  |  Complexity          Lower                 Higher                      | |
|  |                                                                        | |
|  |  Cost Model          Pay per run           Pay for always-on           | |
|  |                                                                        | |
|  +------------------------------------------------------------------------+ |
|                                                                              |
+------------------------------------------------------------------------------+
```

USE CASES
---------

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BATCH PROCESSING USE CASES                                            |
|  ===========================                                            |
|                                                                         |
|  1. ETL (Extract, Transform, Load)                                    |
|     * Daily data warehouse loads                                      |
|     * Data migration between systems                                  |
|                                                                         |
|  2. Reporting & Analytics                                              |
|     * Daily sales reports                                             |
|     * Monthly financial summaries                                     |
|     * User behavior analytics                                         |
|                                                                         |
|  3. Machine Learning Training                                          |
|     * Model training on historical data                               |
|     * Feature engineering pipelines                                   |
|                                                                         |
|  4. Data Backfills                                                      |
|     * Reprocess historical data                                       |
|     * Schema migrations                                               |
|                                                                         |
|  5. Bulk Operations                                                     |
|     * Send millions of emails (batch campaigns)                      |
|     * Generate millions of invoices                                   |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  STREAM PROCESSING USE CASES                                           |
|  ============================                                           |
|                                                                         |
|  1. Real-time Monitoring & Alerting                                   |
|     * Server health monitoring                                        |
|     * Anomaly detection                                               |
|     * SLA breach alerts                                               |
|                                                                         |
|  2. Fraud Detection                                                     |
|     * Credit card fraud (milliseconds matter!)                       |
|     * Account takeover detection                                      |
|                                                                         |
|  3. Live Dashboards                                                     |
|     * Real-time analytics                                             |
|     * Live metrics visualization                                      |
|                                                                         |
|  4. Event-Driven Applications                                          |
|     * Order processing pipelines                                      |
|     * IoT data processing                                             |
|     * Social media feeds                                              |
|                                                                         |
|  5. Real-time Recommendations                                          |
|     * "Users also viewed" (as user browses)                          |
|     * Dynamic pricing                                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### STREAM PROCESSING CONCEPTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WINDOWING                                                              |
|  =========                                                              |
|                                                                         |
|  Group stream data into finite chunks for aggregation                  |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  TUMBLING WINDOW (fixed, non-overlapping)                      |  |
|  |                                                                 |  |
|  |  Time ----------------------------------------------------->   |  |
|  |  Events: e1 e2 e3 | e4 e5 e6 | e7 e8 e9 |                     |  |
|  |          +-----+   +-----+   +-----+                           |  |
|  |          Window 1  Window 2  Window 3                          |  |
|  |          (1 min)   (1 min)   (1 min)                           |  |
|  |                                                                 |  |
|  |  Example: Count orders per minute                              |  |
|  |                                                                 |  |
|  |  ------------------------------------------------------------  |  |
|  |                                                                 |  |
|  |  SLIDING WINDOW (overlapping)                                  |  |
|  |                                                                 |  |
|  |  Time ----------------------------------------------------->   |  |
|  |  Events: e1 e2 e3 e4 e5 e6 e7                                  |  |
|  |          +-----------+                                         |  |
|  |             +-----------+                                      |  |
|  |                +-----------+                                   |  |
|  |                                                                 |  |
|  |  Example: "Last 5 minutes" updated every 30 seconds           |  |
|  |                                                                 |  |
|  |  ------------------------------------------------------------  |  |
|  |                                                                 |  |
|  |  SESSION WINDOW (activity-based)                               |  |
|  |                                                                 |  |
|  |  Events: e1 e2 e3       e4 e5 e6 e7          e8 e9             |  |
|  |          +------+       +---------+          +---+             |  |
|  |          Session 1     Session 2           Session 3           |  |
|  |          (gap closes)  (gap closes)        (new session)       |  |
|  |                                                                 |  |
|  |  Example: User session analytics (session ends after 30min gap)|  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  TIME SEMANTICS                                                         |
|  ===============                                                        |
|                                                                         |
|  EVENT TIME:    When the event actually occurred                       |
|  PROCESSING TIME: When the system processes the event                  |
|  INGESTION TIME: When the event enters the system                      |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Event Time: 10:00:00      (in event payload)                  |  |
|  |        |                                                        |  |
|  |        v                                                        |  |
|  |  [Network Delay: 5 seconds]                                    |  |
|  |        |                                                        |  |
|  |        v                                                        |  |
|  |  Ingestion Time: 10:00:05  (enters Kafka)                      |  |
|  |        |                                                        |  |
|  |        v                                                        |  |
|  |  [Processing Delay: 2 seconds]                                 |  |
|  |        |                                                        |  |
|  |        v                                                        |  |
|  |  Processing Time: 10:00:07 (Flink processes it)                |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  EVENT TIME is preferred for accurate results but requires:           |
|  * Handling late arrivals (watermarks)                                |
|  * Out-of-order events                                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### LAMBDA vs KAPPA ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LAMBDA ARCHITECTURE                                                   |
|  ===================                                                    |
|                                                                         |
|  Combines batch and stream processing for both accuracy and speed      |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |                   +--------------------------------------+     |  |
|  |                   |          DATA SOURCE                 |     |  |
|  |                   |           (Events)                   |     |  |
|  |                   +---------------+----------------------+     |  |
|  |                                   |                            |  |
|  |                   +---------------+---------------+            |  |
|  |                   |                               |            |  |
|  |                   v                               v            |  |
|  |  +-------------------------+   +-------------------------+   |  |
|  |  |      BATCH LAYER       |   |     SPEED LAYER         |   |  |
|  |  |                         |   |                         |   |  |
|  |  |  * Process all data    |   |  * Real-time processing |   |  |
|  |  |  * Accurate results    |   |  * Approximate results  |   |  |
|  |  |  * High latency        |   |  * Low latency          |   |  |
|  |  |  * Hadoop/Spark        |   |  * Storm/Flink          |   |  |
|  |  |                         |   |                         |   |  |
|  |  +-----------+-------------+   +-----------+-------------+   |  |
|  |              |                             |                  |  |
|  |              |      SERVING LAYER          |                  |  |
|  |              |           |                 |                  |  |
|  |              +-----------+-----------------+                  |  |
|  |                          |                                    |  |
|  |                          v                                    |  |
|  |              +-------------------------+                      |  |
|  |              |    MERGED RESULTS       |                      |  |
|  |              |  (batch + speed views)  |                      |  |
|  |              +-------------------------+                      |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  PROS: Accurate + fast, handles late data, reprocessing possible      |
|  CONS: Complex (maintain two codebases), data duplication             |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  KAPPA ARCHITECTURE                                                    |
|  ===================                                                    |
|                                                                         |
|  Stream-only architecture. Batch is just replay of stream.            |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |                   +--------------------------------------+     |  |
|  |                   |          DATA SOURCE                 |     |  |
|  |                   |           (Events)                   |     |  |
|  |                   +---------------+----------------------+     |  |
|  |                                   |                            |  |
|  |                                   v                            |  |
|  |                   +--------------------------------------+     |  |
|  |                   |        EVENT LOG (Kafka)             |     |  |
|  |                   |   (stores all events forever)        |     |  |
|  |                   +---------------+----------------------+     |  |
|  |                                   |                            |  |
|  |                                   v                            |  |
|  |                   +--------------------------------------+     |  |
|  |                   |      STREAM PROCESSOR                |     |  |
|  |                   |        (Flink/KSQL)                  |     |  |
|  |                   |                                       |     |  |
|  |                   |  * Real-time: process live stream   |     |  |
|  |                   |  * Reprocess: replay from beginning |     |  |
|  |                   |    (same code!)                      |     |  |
|  |                   +---------------+----------------------+     |  |
|  |                                   |                            |  |
|  |                                   v                            |  |
|  |                   +--------------------------------------+     |  |
|  |                   |         SERVING LAYER               |     |  |
|  |                   +--------------------------------------+     |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  PROS: Simpler (one codebase), easier to maintain                     |
|  CONS: Requires replayable log (storage cost), reprocessing slow      |
|                                                                         |
|  RECOMMENDATION: Start with Kappa, add Lambda if truly needed         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### TOOLS COMPARISON

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BATCH PROCESSING TOOLS                                                |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Tool           Best For                Characteristics         |  |
|  |  -------------------------------------------------------------  |  |
|  |                                                                 |  |
|  |  Apache Spark   General batch/ML        Fast, in-memory,       |  |
|  |                                          unified API            |  |
|  |                                                                 |  |
|  |  Hadoop MR      Very large scale        Disk-based, mature,    |  |
|  |                                          fault tolerant         |  |
|  |                                                                 |  |
|  |  Hive           SQL on Hadoop           SQL interface,         |  |
|  |                                          good for analysts      |  |
|  |                                                                 |  |
|  |  AWS EMR        Cloud Hadoop/Spark      Managed, scalable,     |  |
|  |                                          pay-per-use            |  |
|  |                                                                 |  |
|  |  dbt            Data transformation     SQL-based, version     |  |
|  |                                          controlled             |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  STREAM PROCESSING TOOLS                                               |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Tool           Best For                Characteristics         |  |
|  |  -------------------------------------------------------------  |  |
|  |                                                                 |  |
|  |  Apache Flink   Complex event           True streaming,        |  |
|  |                  processing             stateful, exactly-once  |  |
|  |                                                                 |  |
|  |  Kafka Streams  Kafka-native apps       Library (not cluster), |  |
|  |                                          simple deployment      |  |
|  |                                                                 |  |
|  |  Spark Streaming Unified batch/stream   Micro-batch,           |  |
|  |                                          good if using Spark    |  |
|  |                                                                 |  |
|  |  AWS Kinesis    AWS streaming           Managed, integrates    |  |
|  |                                          with AWS ecosystem     |  |
|  |                                                                 |  |
|  |  Apache Storm   Real-time processing    Older, low latency,    |  |
|  |                                          at-least-once          |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  RECOMMENDATION:                                                        |
|  * Batch: Spark (versatile) or dbt (SQL-first)                        |
|  * Stream: Flink (powerful) or Kafka Streams (simple, Kafka-native)   |
|  * Unified: Spark with Structured Streaming                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## QUICK REFERENCE SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REVERSE PROXY                                                          |
|  * Sits between clients and servers                                    |
|  * SSL termination, load balancing, caching, compression, security    |
|  * Tools: Nginx, HAProxy, Traefik, Caddy                              |
|                                                                         |
|  EVENT-DRIVEN ARCHITECTURE                                             |
|  * Services communicate via events, not direct calls                  |
|  * Loose coupling, scalable, resilient                                |
|  * Patterns: Event Notification, Event-Carried State, Event Sourcing |
|  * Tools: Kafka, RabbitMQ, AWS EventBridge                            |
|                                                                         |
|  BATCH vs STREAM PROCESSING                                            |
|  * Batch: Large data, high latency, periodic (Spark, Hadoop)         |
|  * Stream: Continuous, low latency, real-time (Flink, Kafka Streams) |
|  * Lambda: Batch + Stream for accuracy and speed                      |
|  * Kappa: Stream-only, replay for batch                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 13

