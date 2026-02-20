# Design a Distributed Task Scheduler

## Table of Contents

1. Requirements
2. Scale Estimation
3. High-Level Architecture
4. Detailed Design
5. Task Lifecycle & State Machine
6. Scheduling Strategies
7. Task Queue Design
8. Worker Management & Execution
9. Exactly-Once Execution & Idempotency
10. Priority & Fairness
11. Rate Limiting & Throttling
12. Dead Letter Queue & Retry Policies
13. Cron Scheduling & Time Zones
14. Database Schema / Data Model
15. API Design
16. Comparison: Celery vs Temporal vs Airflow vs Custom
17. Monitoring and Observability
18. Failure Scenarios and Mitigations
19. Interview Q&A
20. Summary

---

## 1. Requirements

### 1.1 Functional Requirements

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Core Operations:                                                        |
|  - submit(task)          : Submit a task for execution                   |
|  - schedule(task, time)  : Schedule a task for future execution          |
|  - cancel(task_id)       : Cancel a pending/scheduled task               |
|  - status(task_id)       : Query current status of a task                |
|  - result(task_id)       : Retrieve the result of a completed task       |
|                                                                          |
|  Scheduling Types:                                                       |
|  - Immediate execution (fire-and-forget)                                 |
|  - Delayed execution (run at a specific time)                            |
|  - Recurring / Cron (run on a schedule, e.g., every 5 min)               |
|  - Workflow / DAG execution (task B runs after task A completes)         |
|                                                                          |
|  Task Characteristics:                                                   |
|  - Tasks are idempotent (safe to retry)                                  |
|  - Tasks have a type/handler, payload, priority, and TTL                 |
|  - Tasks can have dependencies (DAG execution)                           |
|  - Tasks produce a result or side-effect                                 |
|  - Max execution time (timeout) per task                                 |
|                                                                          |
|  Additional Features:                                                    |
|  - Task deduplication (prevent duplicate submissions)                    |
|  - Callback / webhook on completion                                      |
|  - Task grouping and batch operations                                    |
|  - Pause / resume task queues                                            |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 1.2 Non-Functional Requirements

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Reliability:                                                           |
|  - At-least-once execution guarantee                                    |
|  - No task silently dropped (durable persistence)                       |
|  - Exactly-once semantics where possible (with idempotency)             |
|  - Survive node failures without losing tasks                           |
|                                                                         |
|  Availability:                                                          |
|  - 99.99% uptime for task submission                                    |
|  - Graceful degradation under overload                                  |
|  - No single point of failure                                           |
|                                                                         |
|  Performance:                                                           |
|  - Task dispatch latency: < 100ms for immediate tasks                   |
|  - Scheduling accuracy: within 1 second of target time                  |
|  - Support 100K+ task submissions per second                            |
|  - Support 50K+ concurrent task executions                              |
|                                                                         |
|  Scalability:                                                           |
|  - Horizontal scaling of schedulers and workers                         |
|  - Handle millions of pending tasks                                     |
|  - Scale workers independently per task type                            |
|                                                                         |
|  Observability:                                                         |
|  - Real-time metrics (queue depth, latency, failure rate)               |
|  - Full task execution history and audit trail                          |
|  - Alerting on SLA breaches                                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 2. Scale Estimation

### 2.1 Traffic Estimates

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Task submissions per second:      100,000 (100K TPS)                    |
|  Immediate tasks:                  60,000 (60%)                          |
|  Delayed / scheduled tasks:        30,000 (30%)                          |
|  Recurring / cron tasks:           10,000 (10%)                          |
|  Peak TPS (3x):                    300,000                               |
|                                                                          |
|  Average task execution time:      2 seconds                             |
|  Concurrent executions needed:     100K TPS x 2s = 200,000               |
|  With headroom (1.5x):            300,000 concurrent workers             |
|                                                                          |
|  Tasks per day:                    100K/s x 86400 = ~8.6 billion         |
|  Task retention (30 days):         ~260 billion task records             |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 2.2 Storage Estimates

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Average task record size:          1 KB (metadata + payload)           |
|  Daily task data:                   8.6B x 1KB = ~8.6 TB/day            |
|  30-day retention:                  8.6 TB x 30 = ~258 TB               |
|  With indexes and replicas (3x):   258 TB x 3 = ~774 TB                 |
|                                                                         |
|  Active / pending task store:                                           |
|  - Max pending tasks:              10 million                           |
|  - Pending data:                   10M x 1KB = ~10 GB                   |
|  - Fits comfortably in memory for fast scheduling                       |
|                                                                         |
|  Result store:                                                          |
|  - Average result size:            5 KB                                 |
|  - Daily results:                  8.6B x 5KB = ~43 TB/day              |
|  - Results TTL: 7 days -> ~301 TB                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 2.3 Compute Estimates

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Workers needed (2s avg execution):                                     |
|  - Steady state: 100K/s x 2s = 200K concurrent tasks                    |
|  - At 80% utilization: 200K / 0.8 = 250K worker slots                   |
|  - Workers per machine (8 cores): ~16 concurrent tasks                  |
|  - Machines needed: 250K / 16 = ~15,625 worker machines                 |
|                                                                         |
|  Scheduler nodes:                                                       |
|  - Each scheduler handles ~10K scheduling decisions/s                   |
|  - Schedulers needed: 100K / 10K = ~10 scheduler nodes                  |
|  - With redundancy: ~15 scheduler nodes                                 |
|                                                                         |
|  API servers:                                                           |
|  - Each handles ~10K req/s                                              |
|  - API servers needed: 100K / 10K = ~10                                 |
|  - With redundancy: ~15 API servers                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 3. High-Level Architecture

### 3.1 System Overview

```
+---------------------------------------------------------------------------+
|                  DISTRIBUTED TASK SCHEDULER ARCHITECTURE                  |
+---------------------------------------------------------------------------+
|                                                                           |
|   +----------+     +-----------+     +----------------+                   |
|   |  Client  |---->|   API     |---->|  Task Store    |                   |
|   |  (SDK)   |     |  Gateway  |     |  (Database)    |                   |
|   +----------+     +-----+-----+     +-------+--------+                   |
|                          |                    |                           |
|                          v                    v                           |
|                    +-----+--------+    +------+--------+                  |
|                    |  Task Queue  |    |   Scheduler   |                  |
|                    |  (Priority   |<---|   Service     |                  |
|                    |   Queue)     |    | (Timer-based) |                  |
|                    +------+-------+    +---------------+                  |
|                           |                                               |
|           +---------------+---------------+                               |
|           |               |               |                               |
|     +-----v-----+  +-----v-----+  +------v----+                           |
|     | Worker     |  | Worker    |  | Worker    |                          |
|     | Pool A     |  | Pool B   |  | Pool C    |                           |
|     | (email)    |  | (image)  |  | (payment) |                           |
|     +-----------+  +-----------+  +-----------+                           |
|                                                                           |
|   Components:                                                             |
|   - API Gateway: receives task submissions, queries                       |
|   - Task Store: durable persistence of all tasks (MySQL/PostgreSQL)       |
|   - Scheduler Service: moves delayed tasks to queue at trigger time       |
|   - Task Queue: priority queue for ready-to-execute tasks (Redis/Kafka)   |
|   - Worker Pools: execute tasks, grouped by task type                     |
|                                                                           |
+---------------------------------------------------------------------------+
```

### 3.2 Component Interaction Flow

```
+---------------------------------------------------------------------------+
|                      TASK SUBMISSION FLOW                                 |
+---------------------------------------------------------------------------+
|                                                                           |
|  1. Client submits task via API                                           |
|     POST /api/v1/tasks { type: "send_email", payload: {...} }             |
|                                                                           |
|  2. API Gateway:                                                          |
|     - Validates request                                                   |
|     - Generates unique task_id (UUID / Snowflake)                         |
|     - Persists task to Task Store (status = PENDING)                      |
|     - Returns task_id to client immediately                               |
|                                                                           |
|  3. For immediate tasks:                                                  |
|     - API enqueues task directly into the Task Queue                      |
|     - Task status updated to QUEUED                                       |
|                                                                           |
|  4. For delayed / scheduled tasks:                                        |
|     - Task stays in Task Store with execute_at timestamp                  |
|     - Scheduler Service polls for due tasks and enqueues them             |
|                                                                           |
|  5. Worker picks up task from queue:                                      |
|     - Marks task as RUNNING                                               |
|     - Executes the task handler                                           |
|     - On success: marks as COMPLETED, stores result                       |
|     - On failure: marks as FAILED, schedules retry if applicable          |
|                                                                           |
+---------------------------------------------------------------------------+
```

---

## 4. Detailed Design

### 4.1 API Gateway

```
+--------------------------------------------------------------------------+
|                          API GATEWAY                                     |
+--------------------------------------------------------------------------+
|                                                                          |
|  Responsibilities:                                                       |
|  - Authentication and authorization                                      |
|  - Rate limiting per tenant / API key                                    |
|  - Request validation and sanitization                                   |
|  - Task deduplication (idempotency key check)                            |
|  - Persisting task to database                                           |
|  - Returning task_id for async tracking                                  |
|                                                                          |
|  Deduplication Flow:                                                     |
|  +--------------------------------------------------------------------+  |
|  |                                                                    |  |
|  |  Client sends: { idempotency_key: "order-123-email" }              |  |
|  |                                                                    |  |
|  |  1. Check Redis: EXISTS idemp:order-123-email                      |  |
|  |     -> If exists: return existing task_id (no duplicate)           |  |
|  |     -> If not: proceed to create task                              |  |
|  |                                                                    |  |
|  |  2. SET idemp:order-123-email task_id EX 86400 (24h TTL)           |  |
|  |                                                                    |  |
|  |  3. Persist task and enqueue                                       |  |
|  |                                                                    |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
|  Stateless: multiple instances behind a load balancer                    |
|  Each API server: ~10K requests/s                                        |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 4.2 Task Store (Database)

```
+---------------------------------------------------------------------------+
|                          TASK STORE                                       |
+---------------------------------------------------------------------------+
|                                                                           |
|  Purpose: Durable, queryable record of all tasks                          |
|                                                                           |
|  Technology choices:                                                      |
|  +---------------------------------------------------------------------+  |
|  |                                                                     |  |
|  |  PostgreSQL / MySQL (primary choice):                               |  |
|  |  + ACID transactions for task state changes                         |  |
|  |  + Rich queries (filter by status, type, time range)                |  |
|  |  + Well-understood, battle-tested                                   |  |
|  |  - Sharding needed at high scale                                    |  |
|  |                                                                     |  |
|  |  Cassandra (for very high write throughput):                        |  |
|  |  + Write-optimized, handles billions of records                     |  |
|  |  + Natural time-series partitioning                                 |  |
|  |  - Eventual consistency (harder state transitions)                  |  |
|  |  - Limited query flexibility                                        |  |
|  |                                                                     |  |
|  +---------------------------------------------------------------------+  |
|                                                                           |
|  Sharding Strategy (for SQL):                                             |
|  - Shard by task_id (hash-based) for write distribution                   |
|  - Secondary index on (status, execute_at) for scheduler queries          |
|  - Partition by date for efficient history cleanup                        |
|                                                                           |
|  Hot / Cold Separation:                                                   |
|  - Hot store: active tasks (PENDING, QUEUED, RUNNING) -- fast SSD         |
|  - Cold store: completed tasks (COMPLETED, FAILED) -- cheaper storage     |
|  - Move to cold after task completes + result TTL expires                 |
|                                                                           |
+---------------------------------------------------------------------------+
```

### 4.3 Scheduler Service

```
+--------------------------------------------------------------------------+
|                        SCHEDULER SERVICE                                 |
+--------------------------------------------------------------------------+
|                                                                          |
|  Purpose: Move delayed/scheduled tasks to the queue at trigger time      |
|                                                                          |
|  Architecture:                                                           |
|  +--------------------------------------------------------------------+  |
|  |                                                                    |  |
|  |  Option A: Polling-based                                           |  |
|  |  +---------------------------------------------------------+       |  |
|  |  |                                                         |       |  |
|  |  |  Every 1 second:                                        |       |  |
|  |  |  SELECT * FROM tasks                                    |       |  |
|  |  |  WHERE status = 'PENDING'                               |       |  |
|  |  |    AND execute_at <= NOW()                               |      |  |
|  |  |  ORDER BY priority DESC, execute_at ASC                 |       |  |
|  |  |  LIMIT 1000                                             |       |  |
|  |  |  FOR UPDATE SKIP LOCKED;                                |       |  |
|  |  |                                                         |       |  |
|  |  |  - Update status to QUEUED                              |       |  |
|  |  |  - Push to task queue                                   |       |  |
|  |  |                                                         |       |  |
|  |  +---------------------------------------------------------+       |  |
|  |                                                                    |  |
|  |  Option B: Timer Wheel (in-memory, for low-latency scheduling)     |  |
|  |  +---------------------------------------------------------+       |  |
|  |  |                                                         |       |  |
|  |  |  Hierarchical Timer Wheel:                              |       |  |
|  |  |                                                         |       |  |
|  |  |  Level 1: 1-second slots (60 slots = 1 minute)         |        |  |
|  |  |  Level 2: 1-minute slots (60 slots = 1 hour)           |        |  |
|  |  |  Level 3: 1-hour slots  (24 slots = 1 day)             |        |  |
|  |  |  Level 4: 1-day slots   (30 slots = 1 month)           |        |  |
|  |  |                                                         |       |  |
|  |  |  Tasks cascade down levels as time approaches.          |       |  |
|  |  |  When slot fires: enqueue all tasks in that slot.       |       |  |
|  |  |                                                         |       |  |
|  |  +---------------------------------------------------------+       |  |
|  |                                                                    |  |
|  |  Option C: Redis Sorted Set (ZRANGEBYSCORE)                        |  |
|  |  +---------------------------------------------------------+       |  |
|  |  |                                                         |       |  |
|  |  |  ZADD delayed_tasks <execute_at_epoch> <task_id>        |       |  |
|  |  |                                                         |       |  |
|  |  |  Every second:                                          |       |  |
|  |  |  ZRANGEBYSCORE delayed_tasks 0 <now> LIMIT 0 1000      |        |  |
|  |  |  ZREM delayed_tasks <task_id>   (atomic pop)            |       |  |
|  |  |  -> Enqueue into task queue                             |       |  |
|  |  |                                                         |       |  |
|  |  |  Pros: Simple, fast, atomic operations                  |       |  |
|  |  |  Cons: Single Redis = SPOF, limited to memory size      |       |  |
|  |  |  Fix: Redis Cluster with hash tags                      |       |  |
|  |  |                                                         |       |  |
|  |  +---------------------------------------------------------+       |  |
|  |                                                                    |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
|  Leader Election for Scheduler:                                          |
|  - Only ONE scheduler instance should fire a given task                  |
|  - Use distributed lock (Redis SETNX or ZooKeeper/etcd lease)            |
|  - Or partition scheduled tasks by time range across schedulers          |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 5. Task Lifecycle & State Machine

### 5.1 Task States

```
+---------------------------------------------------------------------------+
|                        TASK STATE MACHINE                                 |
+---------------------------------------------------------------------------+
|                                                                           |
|                          +----------+                                     |
|                          | CREATED  |                                     |
|                          +----+-----+                                     |
|                               |                                           |
|                               | (persisted to DB)                         |
|                               v                                           |
|                          +----+-----+                                     |
|         +--------------->| PENDING  |<--------------+                     |
|         |                +----+-----+               |                     |
|         |                     |                     |                     |
|         |    (execute_at <= now OR immediate)        |                    |
|         |                     v                     |                     |
|         |                +----+-----+               |                     |
|         |                | QUEUED   |               |                     |
|         |                +----+-----+               |                     |
|         |                     |                     |                     |
|         |         (worker picks up task)             |                    |
|         |                     v                     |                     |
|         |                +----+-----+               |                     |
|         |                | RUNNING  |               |                     |
|         |                +----+-----+               |                     |
|         |                /    |     \                |                    |
|         |               /     |      \               |                    |
|         |              v      v       v              |                    |
|         |    +-------+ +------+--+ +------+----+     |                    |
|         |    |COMPLTD| |  FAILED | |  TIMED   |     |                     |
|         |    +-------+ +----+----+ |   OUT    |     |                     |
|         |                   |      +----+-----+     |                     |
|         |                   |           |           |                     |
|         |                   +-----------+           |                     |
|         |                   | (retries left?)       |                     |
|         |                   v                       |                     |
|         |            +------+------+                |                     |
|         +------------|  RETRYING   |                |                     |
|          (re-enqueue)+------+------+                |                     |
|                             |                       |                     |
|                             | (max retries exceeded)                      |
|                             v                       |                     |
|                      +------+------+                |                     |
|                      | DEAD_LETTER |                |                     |
|                      +-------------+                |                     |
|                                                                           |
|  Additional transitions:                                                  |
|  - Any state except COMPLETED -> CANCELLED (via cancel API)               |
|  - RUNNING -> PENDING (if worker crashes, detected by heartbeat)          |
|                                                                           |
+---------------------------------------------------------------------------+
```

### 5.2 State Transition Rules

```
+-------------------------------------------------------------------------+
|                                                                         |
|  State Transitions (who triggers):                                      |
|                                                                         |
|  CREATED -> PENDING       : API Gateway (after DB persist)              |
|  PENDING -> QUEUED        : Scheduler (when execute_at <= now)          |
|  QUEUED  -> RUNNING       : Worker (picks from queue)                   |
|  RUNNING -> COMPLETED     : Worker (task handler returns success)       |
|  RUNNING -> FAILED        : Worker (task handler throws exception)      |
|  RUNNING -> TIMED_OUT     : Watchdog (execution exceeds timeout)        |
|  FAILED/TIMED_OUT -> RETRYING : Retry Manager (if retries remaining)    |
|  RETRYING -> PENDING      : Retry Manager (with backoff delay)          |
|  FAILED  -> DEAD_LETTER   : Retry Manager (max retries exceeded)        |
|  * -> CANCELLED           : API Gateway (user cancellation)             |
|  RUNNING -> PENDING       : Watchdog (worker heartbeat lost)            |
|                                                                         |
|  Atomicity:                                                             |
|  - State transitions are protected by DB transactions or                |
|    compare-and-swap (UPDATE ... WHERE status = expected_status)         |
|  - Prevents race conditions between scheduler, worker, watchdog         |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 6. Scheduling Strategies

### 6.1 Immediate Execution

```
+-------------------------------------------------------------------------+
|                                                                         |
|  IMMEDIATE TASKS                                                        |
|                                                                         |
|  Flow:                                                                  |
|  Client -> API -> DB (status=QUEUED) -> Task Queue -> Worker            |
|                                                                         |
|  - No scheduling delay                                                  |
|  - Task goes directly to the queue after persistence                    |
|  - execute_at = NULL or NOW()                                           |
|                                                                         |
|  Use cases:                                                             |
|  - Send notification after user action                                  |
|  - Process uploaded file                                                |
|  - Async API call delegation                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 6.2 Delayed Execution

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DELAYED TASKS                                                          |
|                                                                         |
|  Flow:                                                                  |
|  Client -> API -> DB (status=PENDING, execute_at=T)                     |
|                        |                                                |
|                        +-> Scheduler polls at time T                    |
|                              |                                          |
|                              +-> Enqueue to Task Queue -> Worker        |
|                                                                         |
|  Implementation options:                                                |
|                                                                         |
|  1. Database polling:                                                   |
|     SELECT ... WHERE execute_at <= NOW() AND status = 'PENDING'         |
|     Pros: Simple, durable                                               |
|     Cons: Polling overhead, 1s granularity                              |
|                                                                         |
|  2. Redis sorted set:                                                   |
|     Score = execute_at timestamp                                        |
|     Pros: Sub-second accuracy, fast                                     |
|     Cons: Durability concerns                                           |
|                                                                         |
|  3. Delay queue (RabbitMQ TTL / Kafka delayed topic):                   |
|     Message TTL = delay duration                                        |
|     Pros: Built-in, no custom scheduler                                 |
|     Cons: Limited flexibility for cancellation                          |
|                                                                         |
|  Best practice: Redis sorted set backed by DB for durability            |
|  Redis is the source of truth for timing; DB is the recovery source     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 6.3 Recurring / Cron Tasks

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RECURRING TASKS (CRON)                                                 |
|                                                                         |
|  How cron scheduling works:                                             |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Cron expression:  "0 */5 * * *"  (every 5 minutes)               |  |
|  |                                                                   |  |
|  |  Cron definition stored in DB:                                    |  |
|  |  {                                                                |  |
|  |    cron_id: "cron-001",                                           |  |
|  |    cron_expr: "0 */5 * * *",                                      |  |
|  |    task_type: "cleanup_expired_sessions",                         |  |
|  |    payload: { ... },                                              |  |
|  |    timezone: "UTC",                                               |  |
|  |    next_fire_time: "2025-01-15T10:05:00Z",                        |  |
|  |    enabled: true                                                  |  |
|  |  }                                                                |  |
|  |                                                                   |  |
|  |  Scheduler logic:                                                 |  |
|  |  1. Every second, check: any cron with next_fire_time <= NOW()?   |  |
|  |  2. If yes:                                                       |  |
|  |     a. Create a new task instance from the cron template          |  |
|  |     b. Enqueue the task                                           |  |
|  |     c. Compute next_fire_time from cron expression                |  |
|  |     d. Update cron record with new next_fire_time                 |  |
|  |  3. Use SELECT ... FOR UPDATE SKIP LOCKED to prevent              |  |
|  |     multiple schedulers from firing the same cron                 |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Preventing duplicate cron fires:                                       |
|  - Unique constraint on (cron_id, fire_time)                            |
|  - Distributed lock per cron_id during fire check                       |
|  - Idempotent task handlers as safety net                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 6.4 DAG / Workflow Execution

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DAG-BASED TASK EXECUTION                                               |
|                                                                         |
|  Example workflow (video processing pipeline):                          |
|                                                                         |
|       +----------+                                                      |
|       | Upload   |                                                      |
|       | Video    |                                                      |
|       +----+-----+                                                      |
|            |                                                            |
|       +----v-----+                                                      |
|       | Extract  |                                                      |
|       | Metadata |                                                      |
|       +----+-----+                                                      |
|            |                                                            |
|      +-----+------+                                                     |
|      |            |                                                     |
|  +---v---+   +----v----+                                                |
|  |Transcode  |Generate |                                                |
|  |to 720p|   |Thumbnail|                                                |
|  +---+---+   +----+----+                                                |
|      |            |                                                     |
|      +-----+------+                                                     |
|            |                                                            |
|       +----v-----+                                                      |
|       | Notify   |                                                      |
|       | User     |                                                      |
|       +----------+                                                      |
|                                                                         |
|  DAG representation in DB:                                              |
|  +-------------------------------------------------------------------+  |
|  |  workflow_id | task_id    | depends_on                            |  |
|  |  wf-001     | upload     | []                                     |  |
|  |  wf-001     | metadata   | [upload]                               |  |
|  |  wf-001     | transcode  | [metadata]                             |  |
|  |  wf-001     | thumbnail  | [metadata]                             |  |
|  |  wf-001     | notify     | [transcode, thumbnail]                 |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Execution logic:                                                       |
|  - When a task completes, check all downstream tasks                    |
|  - A downstream task becomes QUEUED only when ALL its dependencies      |
|    are COMPLETED                                                        |
|  - Transcode and Thumbnail run in parallel (both depend on Metadata)    |
|  - Notify runs only after both Transcode and Thumbnail complete         |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 7. Task Queue Design

### 7.1 Queue Architecture

```
+---------------------------------------------------------------------------+
|                          TASK QUEUE DESIGN                                |
+---------------------------------------------------------------------------+
|                                                                           |
|  The task queue sits between the scheduler and workers.                   |
|  It must support: ordering, priority, multiple consumers, and             |
|  at-least-once delivery.                                                  |
|                                                                           |
|  Technology Options:                                                      |
|  +----------------------------------------------------------------------+ |
|  |                                                                      | |
|  |  Redis (List + Sorted Set):                                          | |
|  |  - LPUSH / BRPOP for FIFO                                            | |
|  |  - Sorted set for priority queue (score = priority)                  | |
|  |  + Very fast (sub-ms latency)                                        | |
|  |  + Simple priority support                                           | |
|  |  - Durability risk (AOF/RDB, not as strong as Kafka)                 | |
|  |  - Limited to memory size                                            | |
|  |                                                                      | |
|  |  Kafka / Pulsar:                                                     | |
|  |  - Topic per task type, partitioned                                  | |
|  |  + Durable, replicated, high throughput                              | |
|  |  + Natural partitioning and ordering                                 | |
|  |  + Consumer groups for parallel processing                           | |
|  |  - Priority not natively supported (need separate topics)            | |
|  |  - Higher latency than Redis (~5-50ms)                               | |
|  |                                                                      | |
|  |  RabbitMQ / SQS:                                                     | |
|  |  + Native priority queues                                            | |
|  |  + Dead letter exchange built-in                                     | |
|  |  + At-least-once semantics with ack                                  | |
|  |  - Lower throughput than Kafka (~50K msg/s)                          | |
|  |                                                                      | |
|  +----------------------------------------------------------------------+ |
|                                                                           |
|  Recommended: Kafka for high-throughput, Redis for low-latency            |
|  Hybrid approach: Redis for immediate tasks, Kafka for durable tasks      |
|                                                                           |
+---------------------------------------------------------------------------+
```

### 7.2 Queue Per Task Type

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ISOLATED QUEUES PER TASK TYPE                                          |
|                                                                         |
|  +------------------+    +------------------+    +------------------+   |
|  | Queue: email     |    | Queue: image     |    | Queue: payment   |   |
|  | (Topic/Partition)|    | (Topic/Partition)|    | (Topic/Partition)|   |
|  |                  |    |                  |    |                  |   |
|  | Tasks: 50K/s     |    | Tasks: 10K/s     |    | Tasks: 5K/s      |   |
|  | Workers: 100     |    | Workers: 200     |    | Workers: 50      |   |
|  |                  |    |                  |    |                  |   |
|  | SLA: 30s p99     |    | SLA: 60s p99     |    | SLA: 5s p99      |   |
|  +------------------+    +------------------+    +------------------+   |
|                                                                         |
|  Benefits:                                                              |
|  - Noisy neighbor isolation (slow image tasks don't block emails)       |
|  - Independent scaling (add workers per type as needed)                 |
|  - Per-type SLA enforcement                                             |
|  - Easier debugging (queue depth per type)                              |
|                                                                         |
|  Trade-off:                                                             |
|  - More operational complexity (more queues to manage)                  |
|  - Potentially lower resource utilization (idle workers)                |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 8. Worker Management & Execution

### 8.1 Worker Architecture

```
+---------------------------------------------------------------------------+
|                        WORKER ARCHITECTURE                                |
+---------------------------------------------------------------------------+
|                                                                           |
|  +--------------------------------------------------------------------+   |
|  |  Worker Process                                                    |   |
|  |                                                                    |   |
|  |  +---------------------------+   +----------------------------+    |   |
|  |  |  Queue Consumer           |   |  Heartbeat Thread          |    |   |
|  |  |  - Poll/subscribe to queue|   |  - Send heartbeat every    |    |   |
|  |  |  - Claim task (atomic)    |   |    5 seconds               |    |   |
|  |  |  - Ack on completion      |   |  - Includes: worker_id,    |    |   |
|  |  +---------------------------+   |    task_id, progress       |    |   |
|  |              |                   +----------------------------+    |   |
|  |              v                                                     |   |
|  |  +---------------------------+                                     |   |
|  |  |  Task Handler Registry    |                                     |   |
|  |  |  {                        |                                     |   |
|  |  |   "send_email": EmailFn,  |                                     |   |
|  |  |   "resize_img": ImgFn,    |                                     |   |
|  |  |   "charge":     PayFn     |                                     |   |
|  |  |  }                        |                                     |   |
|  |  +---------------------------+                                     |   |
|  |              |                                                     |   |
|  |              v                                                     |   |
|  |  +---------------------------+                                     |   |
|  |  |  Execution Sandbox        |                                     |   |
|  |  |  - Timeout enforcement    |                                     |   |
|  |  |  - Memory limit           |                                     |   |
|  |  |  - Stdout/stderr capture  |                                     |   |
|  |  |  - Graceful shutdown hook |                                     |   |
|  |  +---------------------------+                                     |   |
|  |              |                                                     |   |
|  |              v                                                     |   |
|  |  +---------------------------+                                     |   |
|  |  |  Result Reporter          |                                     |   |
|  |  |  - Persist result to DB   |                                     |   |
|  |  |  - Ack message in queue   |                                     |   |
|  |  |  - Trigger callbacks      |                                     |   |
|  |  +---------------------------+                                     |   |
|  +--------------------------------------------------------------------+   |
|                                                                           |
+---------------------------------------------------------------------------+
```

### 8.2 Worker Scaling Strategy

```
+-------------------------------------------------------------------------+
|                                                                         |
|  AUTO-SCALING WORKERS                                                   |
|                                                                         |
|  Scaling signals:                                                       |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  1. Queue depth: If queue_depth > threshold -> scale up           |  |
|  |     e.g., email queue > 10,000 pending -> add 20 workers          |  |
|  |                                                                   |  |
|  |  2. Processing latency: If p99 latency > SLA -> scale up          |  |
|  |     e.g., payment p99 > 5s -> add workers urgently                |  |
|  |                                                                   |  |
|  |  3. Worker utilization: If CPU < 30% for 10 min -> scale down     |  |
|  |     e.g., night time low traffic -> reduce workers                |  |
|  |                                                                   |  |
|  |  4. Scheduled load: Pre-scale before known peaks                  |  |
|  |     e.g., 9 AM email blast -> pre-provision workers at 8:50 AM    |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Implementation:                                                        |
|  - Kubernetes HPA (Horizontal Pod Autoscaler) with custom metrics       |
|  - KEDA (Kubernetes Event-Driven Autoscaling) with queue triggers       |
|  - Scale-to-zero for infrequent task types                              |
|                                                                         |
|  Graceful shutdown:                                                     |
|  1. Stop accepting new tasks                                            |
|  2. Finish currently running tasks (up to timeout)                      |
|  3. Re-enqueue unfinished tasks (if timeout exceeded)                   |
|  4. Drain and terminate                                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 9. Exactly-Once Execution & Idempotency

### 9.1 The Problem

```
+--------------------------------------------------------------------------+
|                      EXACTLY-ONCE CHALLENGE                              |
+--------------------------------------------------------------------------+
|                                                                          |
|  Why is exactly-once hard?                                               |
|                                                                          |
|  Scenario: Worker executes task, sends "charge $100" to payment API      |
|                                                                          |
|  +------------------+     +------------------+     +------------------+  |
|  |  Worker charges  |---->| Payment API      |---->| Returns 200 OK   |  |
|  |  $100            |     | charges card     |     | to worker        |  |
|  +------------------+     +------------------+     +------------------+  |
|                                                           |              |
|                                        Network failure! --|              |
|                                        Worker never gets ACK             |
|                                                                          |
|  Worker thinks: "Task failed, let me retry"                              |
|  Result: Customer charged $200 (DOUBLE CHARGE!)                          |
|                                                                          |
|  ================================================================        |
|                                                                          |
|  The fundamental problem:                                                |
|  - At-most-once: Don't retry. Risk: task not executed at all.            |
|  - At-least-once: Retry on failure. Risk: duplicate execution.           |
|  - Exactly-once: Impossible in distributed systems without               |
|    cooperation from the task handler.                                    |
|                                                                          |
|  Solution: At-least-once delivery + idempotent task handlers             |
|  This gives us EFFECTIVELY exactly-once semantics.                       |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 9.2 Idempotency Patterns

```
+--------------------------------------------------------------------------+
|                                                                          |
|  IDEMPOTENCY STRATEGIES                                                  |
|                                                                          |
|  Pattern 1: Idempotency Key                                              |
|  +--------------------------------------------------------------------+  |
|  |                                                                    |  |
|  |  Each task carries an idempotency_key (e.g., "charge-order-123")   |  |
|  |                                                                    |  |
|  |  Before executing:                                                 |  |
|  |  INSERT INTO executed_tasks (idempotency_key, result)              |  |
|  |  ON CONFLICT DO NOTHING;                                           |  |
|  |                                                                    |  |
|  |  If insert succeeds -> execute task, store result                  |  |
|  |  If insert fails (conflict) -> return stored result (skip exec)    |  |
|  |                                                                    |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
|  Pattern 2: Database Transaction                                         |
|  +--------------------------------------------------------------------+  |
|  |                                                                    |  |
|  |  BEGIN TRANSACTION;                                                |  |
|  |    UPDATE tasks SET status = 'RUNNING'                             |  |
|  |      WHERE id = ? AND status = 'QUEUED';  -- CAS check             |  |
|  |    IF rows_affected = 0 THEN ROLLBACK;    -- already claimed       |  |
|  |    ... execute task ...                                            |  |
|  |    UPDATE tasks SET status = 'COMPLETED', result = ?;              |  |
|  |  COMMIT;                                                           |  |
|  |                                                                    |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
|  Pattern 3: Fencing Token                                                |
|  +--------------------------------------------------------------------+  |
|  |                                                                    |  |
|  |  Each task assignment gets a monotonic fencing_token.              |  |
|  |  External systems reject requests with stale tokens.               |  |
|  |                                                                    |  |
|  |  Worker A: fencing_token = 42, sends charge(token=42)              |  |
|  |  Worker A crashes. Task reassigned to Worker B.                    |  |
|  |  Worker B: fencing_token = 43, sends charge(token=43)              |  |
|  |                                                                    |  |
|  |  Payment API: accepts token=43, rejects late-arriving token=42     |  |
|  |                                                                    |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 10. Priority & Fairness

### 10.1 Priority Queue

```
+--------------------------------------------------------------------------+
|                        PRIORITY SCHEDULING                               |
+--------------------------------------------------------------------------+
|                                                                          |
|  Priority levels:                                                        |
|  +---------------------------------------------------------------------+ |
|  |  Priority  | Value | Example                    | SLA               | |
|  |  ----------+-------+----------------------------+----------------   | |
|  |  CRITICAL  | 0     | Payment processing          | < 1s dispatch    | |
|  |  HIGH      | 1     | User-facing notifications   | < 5s dispatch    | |
|  |  NORMAL    | 2     | Email sending               | < 30s dispatch   | |
|  |  LOW       | 3     | Analytics, reporting        | < 5m dispatch    | |
|  |  BULK      | 4     | Batch data migration        | < 1h dispatch    | |
|  +---------------------------------------------------------------------+ |
|                                                                          |
|  Implementation options:                                                 |
|                                                                          |
|  Option A: Separate queue per priority                                   |
|  +---------------------------------------------------------------------+ |
|  |                                                                     | |
|  |  Queue CRITICAL -----> [Workers always check first]                 | |
|  |  Queue HIGH     -----> [Workers check second]                       | |
|  |  Queue NORMAL   -----> [Workers check third]                        | |
|  |  Queue LOW      -----> [Workers check last]                         | |
|  |                                                                     | |
|  |  Risk: LOW tasks starved if higher queues always have work.         | |
|  |  Fix: Weighted fair queuing (70% HIGH, 20% NORMAL, 10% LOW)         | |
|  |                                                                     | |
|  +---------------------------------------------------------------------+ |
|                                                                          |
|  Option B: Redis sorted set (score = priority * 10^10 + timestamp)       |
|  +---------------------------------------------------------------------+ |
|  |                                                                     | |
|  |  Score = priority_weight * 10000000000 + enqueue_time_epoch         | |
|  |                                                                     | |
|  |  CRITICAL task at T=100: score = 0 * 10^10 + 100 = 100              | |
|  |  NORMAL task at T=50:    score = 2 * 10^10 + 50 = 20000000050       | |
|  |                                                                     | |
|  |  ZPOPMIN always gives highest priority first.                       | |
|  |  Within same priority, FIFO by timestamp.                           | |
|  |                                                                     | |
|  +---------------------------------------------------------------------+ |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 10.2 Fairness Across Tenants

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MULTI-TENANT FAIRNESS                                                  |
|                                                                         |
|  Problem: One tenant submits 1M tasks, starving other tenants.          |
|                                                                         |
|  Solution: Weighted Fair Queuing per tenant                             |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Each tenant gets a virtual queue with a weight (quota).          |  |
|  |                                                                   |  |
|  |  Tenant A (Gold):   weight = 50 (50% of capacity)                 |  |
|  |  Tenant B (Silver): weight = 30 (30% of capacity)                 |  |
|  |  Tenant C (Free):   weight = 20 (20% of capacity)                 |  |
|  |                                                                   |  |
|  |  Scheduler uses deficit round-robin:                              |  |
|  |  1. Each tenant has a "deficit" counter                           |  |
|  |  2. Each round: add weight to deficit                             |  |
|  |  3. Dequeue tasks up to deficit amount                            |  |
|  |  4. Subtract dequeued count from deficit                          |  |
|  |                                                                   |  |
|  |  Result: Tenant A gets 50% throughput, B gets 30%, C gets 20%     |  |
|  |  If A is idle, B and C get A's share proportionally               |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 11. Rate Limiting & Throttling

```
+---------------------------------------------------------------------------+
|                     RATE LIMITING & THROTTLING                            |
+---------------------------------------------------------------------------+
|                                                                           |
|  Why rate limit task execution?                                           |
|  - Downstream APIs have rate limits (e.g., email provider: 1000/min)      |
|  - Prevent resource exhaustion (DB connection pool, CPU)                  |
|  - Protect downstream services from thundering herd                       |
|                                                                           |
|  Rate Limiting Layers:                                                    |
|  +----------------------------------------------------------------------+ |
|  |                                                                      | |
|  |  Layer 1: Submission rate limiting (API Gateway)                     | |
|  |  - Token bucket per tenant per task type                             | |
|  |  - e.g., Tenant A: max 1000 email tasks/min                          | |
|  |  - Excess tasks: 429 Too Many Requests                               | |
|  |                                                                      | |
|  |  Layer 2: Execution rate limiting (Worker)                           | |
|  |  - Limit concurrent executions per downstream service                | |
|  |  - e.g., max 500 concurrent calls to payment API                     | |
|  |  - Implemented via semaphore or distributed rate limiter             | |
|  |                                                                      | |
|  |  Layer 3: Queue-level throttling (Scheduler)                         | |
|  |  - Control dequeue rate per task type                                | |
|  |  - e.g., dequeue max 100 image tasks/s (GPU-bound)                   | |
|  |  - Surplus tasks stay queued (backpressure)                          | |
|  |                                                                      | |
|  +----------------------------------------------------------------------+ |
|                                                                           |
|  Backpressure handling:                                                   |
|  - Queue depth exceeds threshold -> reject new submissions (503)          |
|  - Shed low-priority tasks first (priority-based load shedding)           |
|  - Alert operators when backpressure triggers                             |
|                                                                           |
+---------------------------------------------------------------------------+
```

---

## 12. Dead Letter Queue & Retry Policies

### 12.1 Retry Strategy

```
+--------------------------------------------------------------------------+
|                         RETRY POLICIES                                   |
+--------------------------------------------------------------------------+
|                                                                          |
|  Retry configuration per task type:                                      |
|  +---------------------------------------------------------------------+ |
|  |                                                                     | |
|  |  {                                                                  | |
|  |    "task_type": "send_email",                                       | |
|  |    "max_retries": 5,                                                | |
|  |    "retry_backoff": "exponential",                                  | |
|  |    "base_delay_ms": 1000,                                           | |
|  |    "max_delay_ms": 300000,      // 5 minutes cap                    | |
|  |    "jitter": true,              // randomized delay                 | |
|  |    "retryable_errors": ["TIMEOUT", "5XX", "CONNECTION_REFUSED"]     | |
|  |  }                                                                  | |
|  |                                                                     | |
|  +---------------------------------------------------------------------+ |
|                                                                          |
|  Backoff strategies:                                                     |
|  +---------------------------------------------------------------------+ |
|  |                                                                     | |
|  |  Constant:     delay = base_delay                                   | |
|  |  Linear:       delay = base_delay * attempt                         | |
|  |  Exponential:  delay = base_delay * 2^attempt                       | |
|  |  Exp + Jitter: delay = random(0, base_delay * 2^attempt)            | |
|  |                                                                     | |
|  |  Example (exponential + jitter, base = 1s):                         | |
|  |  Attempt 1: random(0, 2s)   -> e.g., 1.3s                           | |
|  |  Attempt 2: random(0, 4s)   -> e.g., 2.7s                           | |
|  |  Attempt 3: random(0, 8s)   -> e.g., 5.1s                           | |
|  |  Attempt 4: random(0, 16s)  -> e.g., 11.4s                          | |
|  |  Attempt 5: random(0, 32s)  -> capped at 300s -> e.g., 28.6s        | |
|  |                                                                     | |
|  +---------------------------------------------------------------------+ |
|                                                                          |
|  Non-retryable errors (fail immediately):                                |
|  - 400 Bad Request (payload invalid)                                     |
|  - 401/403 Unauthorized (credentials wrong)                              |
|  - Business logic validation errors                                      |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 12.2 Dead Letter Queue

```
+--------------------------------------------------------------------------+
|                                                                          |
|  DEAD LETTER QUEUE (DLQ)                                                 |
|                                                                          |
|  Tasks that exhaust all retries go to the DLQ.                           |
|                                                                          |
|  Flow:                                                                   |
|  Task FAILED (attempt 5/5) -> move to DLQ                                |
|                                                                          |
|  DLQ stores:                                                             |
|  +--------------------------------------------------------------------+  |
|  |  {                                                                 |  |
|  |    task_id: "task-abc-123",                                        |  |
|  |    task_type: "send_email",                                        |  |
|  |    payload: { to: "user@example.com", ... },                       |  |
|  |    error: "SMTP connection refused",                               |  |
|  |    attempts: 5,                                                    |  |
|  |    first_attempt_at: "2025-01-15T10:00:00Z",                       |  |
|  |    last_attempt_at: "2025-01-15T10:05:30Z",                        |  |
|  |    failure_history: [                                              |  |
|  |      { attempt: 1, error: "timeout", at: "..." },                  |  |
|  |      { attempt: 2, error: "timeout", at: "..." },                  |  |
|  |      ...                                                           |  |
|  |    ]                                                               |  |
|  |  }                                                                 |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
|  Operations on DLQ:                                                      |
|  - Inspect: view failed tasks and error details                          |
|  - Replay: re-submit task back to main queue (after fixing issue)        |
|  - Purge: delete tasks from DLQ (acknowledged as unrecoverable)          |
|  - Alert: trigger PagerDuty/Slack when DLQ depth exceeds threshold       |
|                                                                          |
|  DLQ is critical for operational visibility.                             |
|  Without it, failed tasks silently disappear.                            |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 13. Cron Scheduling & Time Zones

```
+--------------------------------------------------------------------------+
|                    CRON SCHEDULING DEEP DIVE                             |
+--------------------------------------------------------------------------+
|                                                                          |
|  Cron expression format:                                                 |
|  +---------------------------------------------------------------------+ |
|  |                                                                     | |
|  |  ┌───────────── second (0-59) [optional]                            | |
|  |  │ ┌─────────── minute (0-59)                                       | |
|  |  │ │ ┌───────── hour (0-23)                                         | |
|  |  │ │ │ ┌─────── day of month (1-31)                                 | |
|  |  │ │ │ │ ┌───── month (1-12)                                        | |
|  |  │ │ │ │ │ ┌─── day of week (0-6, Sunday=0)                         | |
|  |  │ │ │ │ │ │                                                        | |
|  |  * * * * * *                                                        | |
|  |                                                                     | |
|  |  Examples:                                                          | |
|  |  "0 0 * * *"       -> Every day at midnight                         | |
|  |  "*/5 * * * *"     -> Every 5 minutes                               | |
|  |  "0 9 * * 1-5"     -> Every weekday at 9 AM                         | |
|  |  "0 0 1 * *"       -> First day of every month at midnight          | |
|  |                                                                     | |
|  +---------------------------------------------------------------------+ |
|                                                                          |
|  Time Zone Handling:                                                     |
|  +---------------------------------------------------------------------+ |
|  |                                                                     | |
|  |  Problem: "Run every day at 9 AM" -- in which timezone?             | |
|  |                                                                     | |
|  |  Approach:                                                          | |
|  |  1. Store cron definitions with explicit timezone                   | |
|  |     { cron: "0 9 * * *", tz: "America/New_York" }                   | |
|  |                                                                     | |
|  |  2. Scheduler converts to UTC for next_fire_time computation        | |
|  |     - 9 AM EST = 14:00 UTC (winter)                                 | |
|  |     - 9 AM EDT = 13:00 UTC (summer, DST)                            | |
|  |                                                                     | |
|  |  3. Internally, all scheduling in UTC                               | |
|  |     - Avoids ambiguity during DST transitions                       | |
|  |     - next_fire_time always stored in UTC                           | |
|  |                                                                     | |
|  |  DST edge cases:                                                    | |
|  |  - "Spring forward": 2 AM -> 3 AM. Job at 2:30 AM is SKIPPED.       | |
|  |  - "Fall back": 2 AM occurs twice. Job runs ONCE (first time).      | |
|  |  - Document behavior; let users configure skip/run-twice policy.    | |
|  |                                                                     | |
|  +---------------------------------------------------------------------+ |
|                                                                          |
|  Missed fire policy (if scheduler was down):                             |
|  - FIRE_ONCE: fire one catch-up execution, then resume normal            |
|  - FIRE_ALL: fire all missed executions sequentially                     |
|  - SKIP: ignore missed, resume from next scheduled time                  |
|  - Most systems default to FIRE_ONCE                                     |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 14. Database Schema / Data Model

### 14.1 Core Tables

```
+--------------------------------------------------------------------------+
|                        DATABASE SCHEMA                                   |
+--------------------------------------------------------------------------+
|                                                                          |
|  Table: tasks                                                            |
|  +---------------------------------------------------------------------+ |
|  |  Column           | Type         | Notes                            | |
|  |  -----------------+--------------+-------------------------------   | |
|  |  id               | BIGINT (PK)  | Snowflake ID                     | |
|  |  idempotency_key  | VARCHAR(255) | Unique, nullable                 | |
|  |  tenant_id        | VARCHAR(64)  | For multi-tenant isolation       | |
|  |  task_type        | VARCHAR(128) | Handler identifier               | |
|  |  payload          | JSONB        | Task input data                  | |
|  |  priority         | SMALLINT     | 0=CRITICAL, 4=BULK               | |
|  |  status           | VARCHAR(20)  | Current state                    | |
|  |  execute_at       | TIMESTAMP    | When to run (UTC)                | |
|  |  created_at       | TIMESTAMP    | Submission time                  | |
|  |  started_at       | TIMESTAMP    | When worker picked it up         | |
|  |  completed_at     | TIMESTAMP    | When execution finished          | |
|  |  timeout_seconds  | INT          | Max execution duration           | |
|  |  attempt          | INT          | Current attempt number           | |
|  |  max_retries      | INT          | Max retry count                  | |
|  |  result           | JSONB        | Task output / result             | |
|  |  error            | TEXT         | Error message if failed          | |
|  |  worker_id        | VARCHAR(128) | Which worker is running it       | |
|  |  cron_id          | BIGINT (FK)  | Null for one-off tasks           | |
|  |  workflow_id      | BIGINT (FK)  | Null for standalone tasks        | |
|  |  callback_url     | VARCHAR(512) | Webhook on completion            | |
|  +---------------------------------------------------------------------+ |
|                                                                          |
|  Indexes:                                                                |
|  - (status, execute_at)  -> Scheduler query for due tasks                |
|  - (status, priority)    -> Priority-based dequeuing                     |
|  - (tenant_id, status)   -> Per-tenant task listing                      |
|  - (idempotency_key)     -> Dedup lookup (unique)                        |
|  - (cron_id)             -> Link cron instances                          |
|  - (workflow_id, status) -> DAG dependency checks                        |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 14.2 Supporting Tables

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Table: cron_schedules                                                   |
|  +---------------------------------------------------------------------+ |
|  |  Column           | Type         | Notes                            | |
|  |  -----------------+--------------+-------------------------------   | |
|  |  id               | BIGINT (PK)  | Cron definition ID               | |
|  |  tenant_id        | VARCHAR(64)  |                                  | |
|  |  name             | VARCHAR(255) | Human-readable name              | |
|  |  cron_expression   | VARCHAR(64)  | e.g., "0 */5 * * *"             | |
|  |  timezone          | VARCHAR(64)  | e.g., "America/New_York"        | |
|  |  task_type         | VARCHAR(128) | What to run                     | |
|  |  payload_template  | JSONB        | Template for each instance      | |
|  |  next_fire_time    | TIMESTAMP    | Precomputed, UTC                | |
|  |  last_fire_time    | TIMESTAMP    | When last fired                 | |
|  |  enabled           | BOOLEAN      | Pause/resume toggle             | |
|  |  missed_fire_policy| VARCHAR(20)  | FIRE_ONCE / FIRE_ALL / SKIP     | |
|  |  created_at        | TIMESTAMP    |                                 | |
|  +---------------------------------------------------------------------+ |
|                                                                          |
|  Table: workflows                                                        |
|  +---------------------------------------------------------------------+ |
|  |  Column           | Type         | Notes                            | |
|  |  -----------------+--------------+-------------------------------   | |
|  |  id               | BIGINT (PK)  | Workflow instance ID             | |
|  |  definition_id    | BIGINT       | FK to workflow_definitions       | |
|  |  status           | VARCHAR(20)  | RUNNING / COMPLETED / FAILED     | |
|  |  created_at       | TIMESTAMP    |                                  | |
|  |  completed_at     | TIMESTAMP    |                                  | |
|  +---------------------------------------------------------------------+ |
|                                                                          |
|  Table: task_dependencies                                                |
|  +---------------------------------------------------------------------+ |
|  |  Column           | Type         | Notes                            | |
|  |  -----------------+--------------+-------------------------------   | |
|  |  task_id          | BIGINT (FK)  | The dependent task               | |
|  |  depends_on_id    | BIGINT (FK)  | The task it depends on           | |
|  |  (task_id, depends_on_id) = composite PK                            | |
|  +---------------------------------------------------------------------+ |
|                                                                          |
|  Table: dead_letter_queue                                                |
|  +---------------------------------------------------------------------+ |
|  |  Column           | Type         | Notes                            | |
|  |  -----------------+--------------+-------------------------------   | |
|  |  id               | BIGINT (PK)  |                                  | |
|  |  task_id          | BIGINT (FK)  | Original task                    | |
|  |  task_type        | VARCHAR(128) |                                  | |
|  |  payload          | JSONB        |                                  | |
|  |  error            | TEXT         | Last error                       | |
|  |  attempts         | INT          | Total attempts made              | |
|  |  failure_history  | JSONB        | Array of attempt details         | |
|  |  created_at       | TIMESTAMP    | When moved to DLQ                | |
|  |  replayed_at      | TIMESTAMP    | Null until replayed              | |
|  +---------------------------------------------------------------------+ |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 15. API Design

### 15.1 REST API

```
+--------------------------------------------------------------------------+
|                           REST API DESIGN                                |
+--------------------------------------------------------------------------+
|                                                                          |
|  POST /api/v1/tasks                                                      |
|  +---------------------------------------------------------------------+ |
|  |  Request:                                                           | |
|  |  {                                                                  | |
|  |    "task_type": "send_email",                                       | |
|  |    "payload": {                                                     | |
|  |      "to": "user@example.com",                                      | |
|  |      "subject": "Welcome!",                                         | |
|  |      "body": "..."                                                  | |
|  |    },                                                               | |
|  |    "priority": "HIGH",                                              | |
|  |    "execute_at": "2025-01-15T10:00:00Z",    // optional, delayed    | |
|  |    "timeout_seconds": 30,                                           | |
|  |    "max_retries": 3,                                                | |
|  |    "idempotency_key": "welcome-email-user-123",                     | |
|  |    "callback_url": "https://myapp.com/webhook/task-done"            | |
|  |  }                                                                  | |
|  |                                                                     | |
|  |  Response: 202 Accepted                                             | |
|  |  {                                                                  | |
|  |    "task_id": "task-7f3a9b2c",                                      | |
|  |    "status": "PENDING",                                             | |
|  |    "created_at": "2025-01-15T09:30:00Z"                             | |
|  |  }                                                                  | |
|  +---------------------------------------------------------------------+ |
|                                                                          |
|  GET /api/v1/tasks/{task_id}                                             |
|  +---------------------------------------------------------------------+ |
|  |  Response: 200 OK                                                   | |
|  |  {                                                                  | |
|  |    "task_id": "task-7f3a9b2c",                                      | |
|  |    "task_type": "send_email",                                       | |
|  |    "status": "COMPLETED",                                           | |
|  |    "priority": "HIGH",                                              | |
|  |    "attempt": 1,                                                    | |
|  |    "created_at": "2025-01-15T09:30:00Z",                            | |
|  |    "started_at": "2025-01-15T10:00:01Z",                            | |
|  |    "completed_at": "2025-01-15T10:00:03Z",                          | |
|  |    "result": { "message_id": "msg-xyz" }                            | |
|  |  }                                                                  | |
|  +---------------------------------------------------------------------+ |
|                                                                          |
|  DELETE /api/v1/tasks/{task_id}                                          |
|  +---------------------------------------------------------------------+ |
|  |  Cancels a pending/queued task.                                     | |
|  |  Returns 200 if cancelled, 409 if already running/completed.        | |
|  +---------------------------------------------------------------------+ |
|                                                                          |
|  POST /api/v1/cron                                                       |
|  +---------------------------------------------------------------------+ |
|  |  Request:                                                           | |
|  |  {                                                                  | |
|  |    "name": "Session Cleanup",                                       | |
|  |    "cron_expression": "0 */5 * * *",                                | |
|  |    "timezone": "UTC",                                               | |
|  |    "task_type": "cleanup_expired_sessions",                         | |
|  |    "payload": {},                                                   | |
|  |    "missed_fire_policy": "FIRE_ONCE"                                | |
|  |  }                                                                  | |
|  |                                                                     | |
|  |  Response: 201 Created                                              | |
|  |  { "cron_id": "cron-001", "next_fire_time": "..." }                 | |
|  +---------------------------------------------------------------------+ |
|                                                                          |
|  GET /api/v1/tasks?status=FAILED&task_type=send_email&limit=50           |
|  +---------------------------------------------------------------------+ |
|  |  List tasks with filters. Supports pagination via cursor.           | |
|  +---------------------------------------------------------------------+ |
|                                                                          |
|  POST /api/v1/dlq/{task_id}/replay                                       |
|  +---------------------------------------------------------------------+ |
|  |  Re-submit a dead-lettered task back to the main queue.             | |
|  +---------------------------------------------------------------------+ |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 16. Comparison: Celery vs Temporal vs Airflow vs Custom

```
+---------------------------------------------------------------------------+
|                    TASK SCHEDULER COMPARISON                              |
+---------------------------------------------------------------------------+
|                                                                           |
|  +----------------------------------------------------------------------+ |
|  |  Feature       | Celery      | Temporal    | Airflow    | Custom     | |
|  |  --------------+-------------+-------------+------------+--------    | |
|  |  Language      | Python      | Any (SDK)   | Python     | Any        | |
|  |  Broker        | Redis/RMQ   | Built-in    | None (DB)  | Kafka/     | |
|  |                |             |             |            | Redis      | |
|  |  Scheduling    | Celery Beat | Built-in    | DAG-based  | Custom     | |
|  |  Cron support  | Yes         | Yes         | Yes (core) | Custom     | |
|  |  DAG/Workflow  | Canvas      | Native      | Core       | Custom     | |
|  |  Exactly-once  | No (ALO)    | Yes         | No (ALO)   | Custom     | |
|  |  Durability    | Broker-dep  | Strong      | DB-backed  | Custom     | |
|  |  Scalability   | Moderate    | High        | Moderate   | High       | |
|  |  Complexity    | Low         | Medium      | Medium     | High       | |
|  |  State mgmt    | Limited     | Excellent   | Excellent  | Custom     | |
|  |  Retries       | Yes         | Yes + timer | Yes        | Custom     | |
|  |  Observability | Flower      | Web UI      | Web UI     | Custom     | |
|  +----------------------------------------------------------------------+ |
|                                                                           |
|  When to use which:                                                       |
|  +----------------------------------------------------------------------+ |
|  |                                                                      | |
|  |  Celery:                                                             | |
|  |  - Python-centric applications                                       | |
|  |  - Simple task queues, moderate scale                                | |
|  |  - Quick setup, large community                                      | |
|  |  - Limitations: No strong workflow, single-language                  | |
|  |                                                                      | |
|  |  Temporal:                                                           | |
|  |  - Complex, long-running workflows                                   | |
|  |  - Need exactly-once semantics                                       | |
|  |  - Multi-language support needed                                     | |
|  |  - Mission-critical task execution (payments, orders)                | |
|  |  - Best choice for durability + workflow                             | |
|  |                                                                      | |
|  |  Airflow:                                                            | |
|  |  - Data pipelines and ETL workflows                                  | |
|  |  - Batch processing on schedules                                     | |
|  |  - DAG visualization and management                                  | |
|  |  - Not suitable for low-latency real-time tasks                      | |
|  |                                                                      | |
|  |  Custom:                                                             | |
|  |  - Extreme scale requirements (100K+ TPS)                            | |
|  |  - Specific latency / throughput guarantees                          | |
|  |  - Full control over every component                                 | |
|  |  - Willing to invest in engineering effort                           | |
|  |                                                                      | |
|  +----------------------------------------------------------------------+ |
|                                                                           |
+---------------------------------------------------------------------------+
```

---

## 17. Monitoring and Observability

```
+---------------------------------------------------------------------------+
|                    MONITORING & OBSERVABILITY                             |
+---------------------------------------------------------------------------+
|                                                                           |
|  Key Metrics:                                                             |
|  +----------------------------------------------------------------------+ |
|  |                                                                      | |
|  |  Throughput:                                                         | |
|  |  - tasks_submitted_per_second (by type, priority, tenant)            | |
|  |  - tasks_completed_per_second                                        | |
|  |  - tasks_failed_per_second                                           | |
|  |                                                                      | |
|  |  Latency:                                                            | |
|  |  - scheduling_delay: time from execute_at to worker pickup (p50,     | |
|  |    p95, p99)                                                         | |
|  |  - execution_duration: time to run the task handler                  | |
|  |  - end_to_end_latency: submit to completion                          | |
|  |                                                                      | |
|  |  Queue Health:                                                       | |
|  |  - queue_depth (by type) -- CRITICAL METRIC                          | |
|  |  - queue_age: age of oldest message in queue                         | |
|  |  - consumer_lag (if using Kafka)                                     | |
|  |                                                                      | |
|  |  Worker Health:                                                      | |
|  |  - active_workers (by type)                                          | |
|  |  - worker_utilization (%)                                            | |
|  |  - worker_errors_per_second                                          | |
|  |  - heartbeat_miss_rate                                               | |
|  |                                                                      | |
|  |  Reliability:                                                        | |
|  |  - retry_rate (retries / total tasks)                                | |
|  |  - dlq_depth (dead letter queue size) -- MUST ALERT                  | |
|  |  - task_timeout_rate                                                 | |
|  |  - success_rate (completed / total)                                  | |
|  |                                                                      | |
|  +----------------------------------------------------------------------+ |
|                                                                           |
|  Alerting Rules:                                                          |
|  +----------------------------------------------------------------------+ |
|  |                                                                      | |
|  |  CRITICAL:                                                           | |
|  |  - queue_depth > 100K for > 5 min (tasks piling up)                  | |
|  |  - dlq_depth > 1000 (many permanent failures)                        | |
|  |  - active_workers = 0 for any task type                              | |
|  |  - scheduling_delay_p99 > 60s (scheduler falling behind)             | |
|  |                                                                      | |
|  |  WARNING:                                                            | |
|  |  - retry_rate > 10% (degraded downstream)                            | |
|  |  - worker_utilization > 90% (need to scale)                          | |
|  |  - queue_age > 5 min (processing too slow)                           | |
|  |                                                                      | |
|  +----------------------------------------------------------------------+ |
|                                                                           |
|  Distributed Tracing:                                                     |
|  - Inject trace_id into task metadata at submission                       |
|  - Propagate through queue -> worker -> downstream calls                  |
|  - Visualize full task lifecycle in Jaeger / Zipkin                       |
|  - Correlate task execution with downstream service latency               |
|                                                                           |
+---------------------------------------------------------------------------+
```

---

## 18. Failure Scenarios and Mitigations

```
+--------------------------------------------------------------------------+
|                   FAILURE SCENARIOS & MITIGATIONS                        |
+--------------------------------------------------------------------------+
|                                                                          |
|  Scenario 1: Worker crashes mid-execution                                |
|  +---------------------------------------------------------------------+ |
|  |  Problem: Task stuck in RUNNING state forever.                      | |
|  |                                                                     | |
|  |  Detection: Heartbeat timeout                                       | |
|  |  - Worker sends heartbeat every 5s with (worker_id, task_id)        | |
|  |  - Watchdog service: if no heartbeat for 30s -> worker is dead      | |
|  |                                                                     | |
|  |  Recovery:                                                          | |
|  |  - Update task: status = PENDING (re-enqueue)                       | |
|  |  - Increment attempt counter                                        | |
|  |  - Worker's stale ACK (if it recovers) is rejected via              | |
|  |    CAS: UPDATE ... WHERE status = 'RUNNING' AND worker_id = ?       | |
|  |                                                                     | |
|  +---------------------------------------------------------------------+ |
|                                                                          |
|  Scenario 2: Scheduler node goes down                                    |
|  +---------------------------------------------------------------------+ |
|  |  Problem: Delayed tasks not being enqueued.                         | |
|  |                                                                     | |
|  |  Mitigation:                                                        | |
|  |  - Multiple scheduler instances with leader election                | |
|  |  - If leader dies, another takes over within seconds                | |
|  |  - Catch-up: new leader queries DB for all overdue tasks            | |
|  |  - Idempotent enqueue prevents duplicate firing                     | |
|  |                                                                     | |
|  +---------------------------------------------------------------------+ |
|                                                                          |
|  Scenario 3: Queue (Redis/Kafka) goes down                               |
|  +---------------------------------------------------------------------+ |
|  |  Problem: Tasks can't be dispatched to workers.                     | |
|  |                                                                     | |
|  |  Mitigation:                                                        | |
|  |  - Tasks are durable in the DB (source of truth)                    | |
|  |  - Queue is a delivery mechanism, not the store                     | |
|  |  - On queue recovery, scheduler re-scans DB for QUEUED tasks        | |
|  |  - Kafka replication (RF=3) makes total loss very unlikely          | |
|  |                                                                     | |
|  +---------------------------------------------------------------------+ |
|                                                                          |
|  Scenario 4: Database goes down                                          |
|  +---------------------------------------------------------------------+ |
|  |  Problem: Can't persist new tasks or update status.                 | |
|  |                                                                     | |
|  |  Mitigation:                                                        | |
|  |  - DB replication (primary + read replicas + standby)               | |
|  |  - Automatic failover (< 30s with managed DB services)              | |
|  |  - Write-ahead: buffer submissions in queue temporarily             | |
|  |  - Degrade gracefully: accept tasks (queue them), persist later     | |
|  |                                                                     | |
|  +---------------------------------------------------------------------+ |
|                                                                          |
|  Scenario 5: Thundering herd (burst of tasks)                            |
|  +---------------------------------------------------------------------+ |
|  |  Problem: Millions of tasks submitted at once (Black Friday).       | |
|  |                                                                     | |
|  |  Mitigation:                                                        | |
|  |  - Rate limiting at API layer                                       | |
|  |  - Queue absorbs burst (Kafka can handle millions/s)                | |
|  |  - Auto-scale workers based on queue depth                          | |
|  |  - Priority-based load shedding (drop BULK tasks first)             | |
|  |  - Pre-provision workers ahead of known peaks                       | |
|  |                                                                     | |
|  +---------------------------------------------------------------------+ |
|                                                                          |
|  Scenario 6: Poison pill task (always fails, causes worker crash)        |
|  +---------------------------------------------------------------------+ |
|  |  Problem: Task fails every attempt, worker keeps crashing.          | |
|  |                                                                     | |
|  |  Mitigation:                                                        | |
|  |  - Max retries limit -> DLQ after exhaustion                        | |
|  |  - Circuit breaker: if same task_type fails > X times in Y min,     | |
|  |    pause the queue for that type and alert                          | |
|  |  - Worker isolation: run task in sandbox / subprocess               | |
|  |    so crash doesn't take down the worker process                    | |
|  |                                                                     | |
|  +---------------------------------------------------------------------+ |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 19. Interview Q&A

### Q1: How do you ensure a task is not executed twice?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|  True exactly-once is impossible in distributed systems. We use         |
|  at-least-once delivery + idempotent task handlers for effectively      |
|  exactly-once semantics.                                                |
|                                                                         |
|  Mechanisms:                                                            |
|  1. Idempotency key: each task has a unique key stored in DB.           |
|     Before execution, check if key exists. If yes, skip.                |
|                                                                         |
|  2. Database CAS (Compare-And-Swap):                                    |
|     UPDATE tasks SET status='RUNNING' WHERE id=? AND status='QUEUED'    |
|     Only one worker succeeds; others get 0 rows affected.               |
|                                                                         |
|  3. Queue-level: Kafka consumer group ensures one consumer per          |
|     partition. Message acknowledged only after successful execution.    |
|                                                                         |
|  4. Fencing tokens: monotonically increasing token per assignment.      |
|     Downstream systems reject stale tokens.                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q2: How does the scheduler handle millions of delayed tasks?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|  Three-tier approach:                                                   |
|                                                                         |
|  Tier 1 (minutes away): Redis sorted set                                |
|  - Tasks due within the next 10 minutes are loaded into Redis           |
|  - ZRANGEBYSCORE polls every second for due tasks                       |
|  - Supports millions of tasks, O(log N) per operation                   |
|                                                                         |
|  Tier 2 (hours away): Database with indexed query                       |
|  - Tasks due in 10 min to 24 hours stay in DB                           |
|  - Background loader moves them to Redis as they approach trigger time  |
|  - Query: SELECT ... WHERE execute_at BETWEEN NOW() AND NOW()+10min     |
|                                                                         |
|  Tier 3 (days+ away): Cold storage in DB                                |
|  - Tasks far in the future just sit in DB                               |
|  - Periodic scan (every hour) checks for tasks entering Tier 2 range    |
|                                                                         |
|  This tiered approach keeps memory usage bounded while maintaining      |
|  sub-second scheduling accuracy for imminent tasks.                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q3: How do you prevent the scheduler from becoming a single point of failure?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|  Multiple strategies:                                                   |
|                                                                         |
|  1. Active-passive with leader election:                                |
|     - Multiple scheduler instances, one is leader (via etcd/ZK)         |
|     - Leader does the scheduling; standby monitors                      |
|     - If leader dies, standby acquires lease and takes over             |
|     - Failover time: ~5-10 seconds                                      |
|                                                                         |
|  2. Partitioned active-active:                                          |
|     - Divide tasks by hash(task_id) % N across N schedulers             |
|     - Each scheduler only processes its partition                       |
|     - If one dies, its partition is reassigned (consistent hashing)     |
|     - Higher throughput, no wasted standby capacity                     |
|                                                                         |
|  3. Database as the coordination point:                                 |
|     - SELECT ... FOR UPDATE SKIP LOCKED                                 |
|     - Multiple schedulers query the same DB                             |
|     - SKIP LOCKED ensures no duplicates (each scheduler grabs           |
|       different tasks)                                                  |
|     - Simple, no leader election needed                                 |
|     - Trade-off: DB becomes the bottleneck at extreme scale             |
|                                                                         |
|  Best practice: Approach 2 or 3 depending on scale.                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q4: How would you handle task dependencies (DAG)?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|  Store dependencies in a task_dependencies table:                       |
|  (task_id, depends_on_id)                                               |
|                                                                         |
|  When a task completes:                                                 |
|  1. Query all tasks that depend on it:                                  |
|     SELECT task_id FROM task_dependencies WHERE depends_on_id = ?       |
|                                                                         |
|  2. For each dependent task, check if ALL dependencies are met:         |
|     SELECT COUNT(*) FROM task_dependencies td                           |
|     JOIN tasks t ON td.depends_on_id = t.id                             |
|     WHERE td.task_id = ? AND t.status != 'COMPLETED'                    |
|                                                                         |
|  3. If count = 0 (all dependencies done) -> enqueue the task            |
|                                                                         |
|  Cycle detection:                                                       |
|  - At workflow submission time, run topological sort on the DAG         |
|  - If topological sort fails -> cycle detected -> reject workflow       |
|                                                                         |
|  Partial failure:                                                       |
|  - If a task in the DAG fails and exhausts retries, mark the            |
|    entire workflow as FAILED (or allow partial completion based on      |
|    configuration)                                                       |
|  - Dependent tasks are marked as CANCELLED                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q5: What happens if a cron job takes longer than its interval?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|  Example: Cron runs every 5 minutes, but execution takes 8 minutes.     |
|                                                                         |
|  Options (configurable per cron):                                       |
|                                                                         |
|  1. ALLOW_CONCURRENT (default: false)                                   |
|     - If false: skip the next fire if the previous is still running     |
|     - Check: SELECT ... FROM tasks WHERE cron_id = ? AND                |
|       status = 'RUNNING'                                                |
|     - If running: update next_fire_time, don't create new instance      |
|                                                                         |
|  2. QUEUE_NEXT                                                          |
|     - Queue the next instance; it starts when the current one finishes  |
|     - At most 1 queued + 1 running                                      |
|                                                                         |
|  3. ALLOW_PARALLEL                                                      |
|     - Let multiple instances run concurrently                           |
|     - Risk: resource contention, duplicate work                         |
|     - Only for tasks designed for parallelism                           |
|                                                                         |
|  Best practice: Default to ALLOW_CONCURRENT=false with alerting         |
|  when executions are consistently overlapping (indicates the task       |
|  needs optimization or the interval needs increasing).                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q6: How do you implement priority without starving low-priority tasks?

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Answer:                                                                 |
|  Strict priority ordering causes starvation. Solutions:                  |
|                                                                          |
|  1. Weighted Fair Queuing:                                               |
|     - Assign weights: CRITICAL=50%, HIGH=30%, NORMAL=15%, LOW=5%         |
|     - Workers pull from queues proportionally                            |
|     - Even under load, LOW gets 5% of throughput                         |
|                                                                          |
|  2. Aging:                                                               |
|     - Increase effective priority over time                              |
|     - effective_priority = base_priority - (age_seconds / 60)            |
|     - A LOW task waiting 30 minutes becomes equivalent to HIGH           |
|     - Guarantees bounded wait time for any priority                      |
|                                                                          |
|  3. Reserved capacity:                                                   |
|     - Reserve a minimum number of workers per priority level             |
|     - e.g., 5 workers always reserved for LOW priority                   |
|     - Remaining workers handle higher priorities first                   |
|                                                                          |
|  4. Separate SLAs:                                                       |
|     - LOW tasks: SLA = execute within 1 hour                             |
|     - Monitor and alert if SLA at risk                                   |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Q7: How would you handle a task that needs to make exactly one payment?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|  This is the classic "at-least-once delivery, exactly-once processing"  |
|  problem. The payment must happen exactly once even if the task is      |
|  retried.                                                               |
|                                                                         |
|  Approach:                                                              |
|  1. Generate an idempotency_key before submission:                      |
|     key = "payment-order-456-attempt-1"                                 |
|                                                                         |
|  2. Task handler:                                                       |
|     a. Check local DB: has this key been processed?                     |
|        SELECT * FROM payments WHERE idempotency_key = ?                 |
|        If yes -> return stored result (skip payment)                    |
|                                                                         |
|     b. Call payment gateway WITH the idempotency key:                   |
|        POST /charge { amount: 100, idempotency_key: "..." }             |
|        (Stripe, PayPal all support idempotency keys natively)           |
|                                                                         |
|     c. Store result in DB atomically:                                   |
|        BEGIN;                                                           |
|          INSERT INTO payments (idempotency_key, result, ...) ...;       |
|          UPDATE tasks SET status = 'COMPLETED', result = ...;           |
|        COMMIT;                                                          |
|                                                                         |
|  3. If worker crashes after payment but before DB commit:               |
|     - Retry will hit step (a) -- but key not in DB                      |
|     - Step (b) calls payment gateway again -- gateway returns           |
|       cached result (idempotency key match)                             |
|     - Step (c) stores result. No double charge.                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q8: How would you scale this to 1 million tasks per second?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|  At 1M TPS, every component needs horizontal scaling:                   |
|                                                                         |
|  1. API Gateway: 100 instances behind load balancer                     |
|     - Stateless, each handles ~10K TPS                                  |
|                                                                         |
|  2. Task Store: Sharded database                                        |
|     - 100 shards by hash(task_id) across PostgreSQL/Vitess              |
|     - Each shard handles ~10K writes/s (well within limits)             |
|     - Or use Cassandra for linear write scaling                         |
|                                                                         |
|  3. Queue: Kafka with many partitions                                   |
|     - 500+ partitions across 50+ brokers                                |
|     - Each partition: ~5K msg/s throughput                              |
|     - Topic per task type for isolation                                 |
|                                                                         |
|  4. Scheduler: Partitioned across 50 instances                          |
|     - Each handles a hash range of tasks                                |
|     - Redis cluster for in-memory timer wheel                           |
|                                                                         |
|  5. Workers: Auto-scaled on Kubernetes                                  |
|     - 1M TPS x 2s avg = 2M concurrent tasks                             |
|     - ~125K worker machines (16 tasks each)                             |
|     - Separate worker pools per task type                               |
|                                                                         |
|  Key architectural principles at this scale:                            |
|  - Everything is partitioned (no single hot path)                       |
|  - No coordination between partitions where possible                    |
|  - Async everywhere (no synchronous cross-service calls)                |
|  - Accept eventual consistency for non-critical paths                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q9: Compare database-polling vs event-driven scheduling.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|                                                                         |
|  Database Polling:                                                      |
|  +-------------------------------------------------------------------+  |
|  |  How: SELECT ... WHERE execute_at <= NOW() every N seconds        |  |
|  |                                                                   |  |
|  |  Pros:                                                            |  |
|  |  + Simple to implement and reason about                           |  |
|  |  + Database is already the source of truth                        |  |
|  |  + No extra infrastructure                                        |  |
|  |  + SKIP LOCKED prevents duplicate processing                      |  |
|  |                                                                   |  |
|  |  Cons:                                                            |  |
|  |  - Polling interval = scheduling accuracy (1s polls = 1s delay)   |  |
|  |  - Database load from repeated queries                            |  |
|  |  - Doesn't scale beyond ~100K pending tasks efficiently           |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Event-Driven (Timer Wheel / Redis Sorted Set):                         |
|  +-------------------------------------------------------------------+  |
|  |  How: In-memory timer fires exactly at execute_at time            |  |
|  |                                                                   |  |
|  |  Pros:                                                            |  |
|  |  + Sub-millisecond scheduling accuracy                            |  |
|  |  + No polling overhead                                            |  |
|  |  + Scales to millions of timers                                   |  |
|  |                                                                   |  |
|  |  Cons:                                                            |  |
|  |  - In-memory state can be lost (need DB backup)                   |  |
|  |  - More complex (timer wheel, leader election)                    |  |
|  |  - Need to reload state on restart                                |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Recommendation: Hybrid approach                                        |
|  - Event-driven for hot path (tasks due within minutes)                 |
|  - DB polling as a sweep/catch-up mechanism (every 30s)                 |
|  - DB is always the source of truth for recovery                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q10: How do you monitor and debug a task that "disappeared"?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|  Tasks should never disappear. If one does, here's the debugging        |
|  playbook:                                                              |
|                                                                         |
|  1. Check task status in DB:                                            |
|     SELECT * FROM tasks WHERE id = 'task-xxx';                          |
|     -> What state is it in? When was it last updated?                   |
|                                                                         |
|  2. If status = RUNNING but no worker activity:                         |
|     -> Worker crashed. Watchdog should have caught this.                |
|     -> Check: heartbeat logs, watchdog alerts                           |
|     -> Fix: watchdog not running or heartbeat threshold too high        |
|                                                                         |
|  3. If status = QUEUED but never picked up:                             |
|     -> No workers consuming this queue, or queue is full                |
|     -> Check: worker count, queue depth, consumer lag                   |
|     -> Fix: scale workers, check queue connectivity                     |
|                                                                         |
|  4. If status = PENDING and execute_at is in the past:                  |
|     -> Scheduler missed it                                              |
|     -> Check: scheduler logs, leader election status                    |
|     -> Fix: scheduler catch-up scan should find overdue tasks           |
|                                                                         |
|  5. If task not in DB at all:                                           |
|     -> API failed to persist (DB error during submission)               |
|     -> Check: API error logs, DB connectivity at submission time        |
|     -> Fix: client should have received an error; implement retry       |
|       at the client SDK level                                           |
|                                                                         |
|  Prevention:                                                            |
|  - Full audit log (every state transition logged with timestamp)        |
|  - Distributed tracing (trace_id from submission to completion)         |
|  - Anomaly detection: alert if task count drops unexpectedly            |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 20. Summary: Key Design Decisions

```
+---------------------------------------------------------------------------+
|                     KEY DESIGN DECISIONS                                  |
+---------------------------------------------------------------------------+
|                                                                           |
|  Decision              | Choice              | Rationale                  |
|  ----------------------+---------------------+-------------------------   |
|  Task persistence      | PostgreSQL (sharded) | ACID, queryable, proven   |
|  Task queue            | Kafka + Redis        | Durable + low-latency     |
|  Scheduling            | Redis sorted set +   | Sub-second accuracy       |
|                        | DB polling fallback  | with durability backup    |
|  Worker management     | Kubernetes + KEDA    | Auto-scaling, isolation   |
|  Exactly-once          | Idempotency keys     | At-least-once + idemp.    |
|  Priority handling     | Weighted fair queue  | No starvation             |
|  Failure detection     | Heartbeat + watchdog | Fast crash detection      |
|  Retry policy          | Exponential backoff  | Prevents thundering herd  |
|                        | + jitter             |                           |
|  Dead letter queue     | Separate DB table    | Operational visibility    |
|  Cron scheduling       | DB-backed + Redis    | Durable + precise         |
|  DAG / Workflows       | Dependency table +   | Flexible, queryable       |
|                        | completion triggers  |                           |
|  Scheduler HA          | Partitioned active-  | No wasted standby         |
|                        | active               |                           |
|  Multi-tenancy         | Deficit round-robin  | Fair resource sharing     |
|  Observability         | Prometheus + Jaeger  | Metrics + tracing         |
|                                                                           |
+---------------------------------------------------------------------------+
```

---

*End of Distributed Task Scheduler System Design*
