# CHAPTER 7: MESSAGE QUEUES
*Asynchronous Communication Between Services*

Message queues enable loose coupling between services, handle traffic spikes,
and make systems more resilient. They're essential for building scalable,
distributed applications.

## SECTION 7.1: SYNCHRONOUS vs ASYNCHRONOUS COMMUNICATION

### THE SYNCHRONOUS PROBLEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SYNCHRONOUS COMMUNICATION                                             |
|                                                                         |
|  +------------------------------------------------------------------+ |
|  |                                                                  | |
|  |  User Request                                                    | |
|  |      |                                                           | |
|  |      v                                                           | |
|  |  Order Service ---> Payment Service ---> Notification Service   | |
|  |      |                    |                      |               | |
|  |      |                    |                      |               | |
|  |      |               [wait 2s]              [wait 1s]           | |
|  |      |                    |                      |               | |
|  |      |<-------------------+                      |               | |
|  |      |<------------------------------------------+               | |
|  |      |                                                           | |
|  |  Total latency: 3+ seconds                                      | |
|  |  User waits for entire chain to complete                        | |
|  |                                                                  | |
|  +------------------------------------------------------------------+ |
|                                                                         |
|  PROBLEMS:                                                             |
|  * Caller blocks until response                                       |
|  * Latency adds up across services                                    |
|  * One slow service slows everything                                  |
|  * One failed service fails everything                                |
|  * Hard to handle traffic spikes                                      |
|  * Tight coupling between services                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### THE ASYNCHRONOUS SOLUTION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ASYNCHRONOUS COMMUNICATION                                            |
|                                                                         |
|  +------------------------------------------------------------------+ |
|  |                                                                  | |
|  |  User Request                                                    | |
|  |      |                                                           | |
|  |      v                                                           | |
|  |  Order Service ---> Message Queue ---> (respond immediately)    | |
|  |      |                    |                                      | |
|  |      |                    | (async processing)                   | |
|  |  Response: "Order created,+----> Payment Service               | |
|  |            processing..."  |                                     | |
|  |                           +----> Notification Service           | |
|  |                                                                  | |
|  |  Total user wait: ~100ms (just queue publish)                   | |
|  |                                                                  | |
|  +------------------------------------------------------------------+ |
|                                                                         |
|  BENEFITS:                                                             |
|  Y Fast response to user                                             |
|  Y Services work independently                                       |
|  Y Queue buffers traffic spikes                                      |
|  Y Failed service can retry later                                    |
|  Y Loose coupling                                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7.2: MESSAGE QUEUE FUNDAMENTALS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MESSAGE QUEUE ARCHITECTURE                                            |
|                                                                         |
|  +----------+        +--------------------+        +----------+       |
|  | Producer |------->|   Message Queue    |------->| Consumer |       |
|  |          |  push  |                    |  pull  |          |       |
|  +----------+        |  +--+--+--+--+--+ |        +----------+       |
|                      |  |M1|M2|M3|M4|M5| |                            |
|                      |  +--+--+--+--+--+ |                            |
|                      |     (messages)     |                            |
|                      +--------------------+                            |
|                                                                         |
|  PRODUCER: Creates and sends messages to queue                        |
|  QUEUE: Stores messages until consumed                                |
|  CONSUMER: Reads and processes messages                               |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  KEY CONCEPTS                                                          |
|                                                                         |
|  MESSAGE:                                                              |
|  ---------                                                              |
|  {                                                                     |
|    "id": "msg-123",                                                   |
|    "type": "ORDER_CREATED",                                           |
|    "payload": {                                                        |
|      "orderId": "order-456",                                          |
|      "userId": "user-789",                                            |
|      "amount": 99.99                                                  |
|    },                                                                  |
|    "timestamp": "2024-01-15T10:30:00Z"                                |
|  }                                                                     |
|                                                                         |
|  TOPIC/QUEUE:                                                          |
|  -------------                                                          |
|  Named channel for messages (e.g., "orders", "notifications")         |
|                                                                         |
|  CONSUMER GROUP:                                                       |
|  ----------------                                                       |
|  Multiple consumers that share processing of messages                 |
|  Each message goes to ONE consumer in the group                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### MESSAGE PATTERNS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. POINT-TO-POINT (QUEUE)                                            |
|  =========================                                              |
|                                                                         |
|  Each message is processed by exactly ONE consumer.                   |
|                                                                         |
|  +----------+                                      +----------+       |
|  | Producer |-->  +--+--+--+  --> Consumer A takes | Consumer |       |
|  +----------+     |M1|M2|M3|                       |    A     |       |
|                   +--+--+--+      M1              +----------+       |
|                       |                                               |
|                       |           +----------+                        |
|                       +---------->| Consumer | takes M2              |
|                                   |    B     |                        |
|                                   +----------+                        |
|                                                                         |
|  USE CASE: Task distribution, work queues                             |
|  * Email sending                                                      |
|  * Image processing                                                   |
|  * Order processing                                                   |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. PUBLISH-SUBSCRIBE (FAN-OUT)                                       |
|  =================================                                      |
|                                                                         |
|  Each message is delivered to ALL subscribers.                        |
|                                                                         |
|  +----------+                         +--------------+                |
|  | Producer |--> Topic ---------------> Subscriber A | gets message  |
|  +----------+    "orders"      |      +--------------+                |
|       |                        |      +--------------+                |
|       |    Message: ORDER_123  +----->| Subscriber B | gets message  |
|       |                        |      +--------------+                |
|       |                        |      +--------------+                |
|       |                        +----->| Subscriber C | gets message  |
|       |                               +--------------+                |
|                                                                         |
|  USE CASE: Event broadcasting, notifications                          |
|  * Notify multiple services of an event                              |
|  * Real-time updates                                                  |
|  * Event-driven architecture                                          |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. REQUEST-REPLY                                                      |
|  =================                                                      |
|                                                                         |
|  Async request with correlation ID for response matching.             |
|                                                                         |
|  +---------+    Request Queue    +----------+                        |
|  | Client  |-------------------->|  Server  |                        |
|  |         |                      |          |                        |
|  | "Reply  |    Reply Queue      |          |                        |
|  |  to me  |<--------------------|          |                        |
|  |  at..." |  (correlation_id)   +----------+                        |
|  +---------+                                                          |
|                                                                         |
|  USE CASE: RPC over messaging, async API calls                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7.3: DELIVERY GUARANTEES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MESSAGE DELIVERY GUARANTEES                                           |
|                                                                         |
|  1. AT-MOST-ONCE                                                       |
|  ===================                                                    |
|                                                                         |
|  Message may be lost, but never delivered twice.                      |
|                                                                         |
|  +----------+      +-------+      +----------+                        |
|  | Producer |--M1->| Queue |--M1->| Consumer | (might fail)          |
|  +----------+      +-------+      +----------+                        |
|                        |                |                              |
|                        +-- Message deleted before confirmed            |
|                                         |                              |
|                                      Lost! X                          |
|                                                                         |
|  HOW: Fire and forget, no acknowledgment                             |
|  USE CASE: Metrics, logs (where losing some is okay)                 |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. AT-LEAST-ONCE (Most common)                                       |
|  ===============================                                        |
|                                                                         |
|  Message may be delivered multiple times, but never lost.             |
|                                                                         |
|  +----------+      +-------+      +----------+                        |
|  | Producer |--M1->| Queue |--M1->| Consumer |                        |
|  +----------+      +-------+      +----------+                        |
|                        |                |                              |
|                        |            Process M1                         |
|                        |                |                              |
|                        |            ACK fails!                         |
|                        |                |                              |
|                        +--> Redeliver M1-> Process M1 again           |
|                                         |                              |
|                                  Duplicate! (must handle)             |
|                                                                         |
|  HOW: Require acknowledgment, retry on failure                       |
|  REQUIREMENT: Consumer must be IDEMPOTENT                             |
|                                                                         |
|  IDEMPOTENT PROCESSING:                                               |
|  -------------------------                                              |
|  Same message processed twice = same result                           |
|                                                                         |
|  def process_order(order_id):                                         |
|      # Check if already processed                                     |
|      if db.exists(f"processed:{order_id}"):                          |
|          return  # Already done, skip                                 |
|                                                                         |
|      # Process order                                                   |
|      create_order(order_id)                                           |
|                                                                         |
|      # Mark as processed                                               |
|      db.set(f"processed:{order_id}", true)                           |
|                                                                         |
|  USE CASE: Most applications (orders, payments, etc.)                 |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. EXACTLY-ONCE                                                       |
|  ===================                                                    |
|                                                                         |
|  Message delivered exactly once. The holy grail!                      |
|                                                                         |
|  REALITY CHECK: True exactly-once is very hard (or impossible)       |
|  in distributed systems due to network partitions.                    |
|                                                                         |
|  PRACTICAL EXACTLY-ONCE:                                              |
|  "Effectively once" = At-least-once + Idempotent consumer            |
|                                                                         |
|  Or use transactional messaging:                                      |
|  * Kafka transactions                                                 |
|  * Combine message processing with DB transaction                    |
|                                                                         |
|  HOW KAFKA TRANSACTIONS WORK:                                         |
|  +----------------------------------------------------------------+   |
|  | BEGIN TRANSACTION                                              |   |
|  | 1. Consume message from input topic                           |   |
|  | 2. Process message                                            |   |
|  | 3. Produce to output topic                                    |   |
|  | 4. Commit consumer offset                                     |   |
|  | COMMIT TRANSACTION                                             |   |
|  | (All or nothing - message processed exactly once)             |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7.4: MESSAGE ORDERING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MESSAGE ORDERING CHALLENGES                                           |
|                                                                         |
|  PROBLEM: With multiple consumers, messages may process out of order. |
|                                                                         |
|  Producer sends: M1, M2, M3                                           |
|  Consumer A gets M1 (takes 5 seconds)                                 |
|  Consumer B gets M2 (takes 1 second) > finishes first!               |
|  Consumer C gets M3 (takes 2 seconds)                                 |
|                                                                         |
|  Processing order: M2, M3, M1 (not M1, M2, M3!)                       |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  SOLUTION 1: SINGLE CONSUMER                                          |
|  ----------------------------                                           |
|  Only one consumer > guaranteed order                                 |
|  But: No parallelism, can't scale                                    |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  SOLUTION 2: PARTITIONING (Kafka approach)                            |
|  --------------------------------------------                           |
|  Order guaranteed WITHIN a partition, not across partitions.          |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Topic: orders                                                  |  |
|  |                                                                 |  |
|  |  +--------------------+  +--------------------+               |  |
|  |  |    Partition 0     |  |    Partition 1     |               |  |
|  |  |  [User A orders]   |  |  [User B orders]   |               |  |
|  |  |  M1 > M3 > M5      |  |  M2 > M4 > M6      |               |  |
|  |  |      v             |  |      v             |               |  |
|  |  |  Consumer 1        |  |  Consumer 2        |               |  |
|  |  |  (processes in     |  |  (processes in     |               |  |
|  |  |   order: M1,M3,M5) |  |   order: M2,M4,M6) |               |  |
|  |  +--------------------+  +--------------------+               |  |
|  |                                                                 |  |
|  |  Partition key: user_id                                        |  |
|  |  All orders for User A > Partition 0 > Same consumer          |  |
|  |  All orders for User B > Partition 1 > Same consumer          |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  CHOOSE PARTITION KEY CAREFULLY:                                      |
|  * user_id: Order per user (common for user operations)              |
|  * order_id: Order per order (for order state changes)               |
|  * entity_id: Order per entity being modified                        |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  SOLUTION 3: SEQUENCE NUMBERS                                         |
|  ------------------------------                                         |
|  Consumer tracks expected sequence, reorders if needed.              |
|                                                                         |
|  Message: { seq: 5, data: ... }                                       |
|                                                                         |
|  Consumer:                                                             |
|  - Expected: 5                                                        |
|  - Received: 7 > buffer, wait for 5 and 6                            |
|  - Received: 5 > process                                             |
|  - Received: 6 > process, then process buffered 7                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7.5: POPULAR MESSAGE QUEUE SYSTEMS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  APACHE KAFKA                                                          |
|  =============                                                          |
|                                                                         |
|  Distributed event streaming platform. The industry standard.         |
|                                                                         |
|  ARCHITECTURE:                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Topic: orders                                                  |  |
|  |  +---------------+ +---------------+ +---------------+        |  |
|  |  | Partition 0   | | Partition 1   | | Partition 2   |        |  |
|  |  | [0][1][2][3]  | | [0][1][2]     | | [0][1]        |        |  |
|  |  | ^ oldest      | |               | |           ^   |        |  |
|  |  |      newest ^ | |               | |      newest   |        |  |
|  |  +---------------+ +---------------+ +---------------+        |  |
|  |                                                                 |  |
|  |  * Messages are immutable, append-only                         |  |
|  |  * Retained for configurable time (days/weeks)                |  |
|  |  * Consumers track their own offset                           |  |
|  |  * Can replay from any point                                   |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  KEY FEATURES:                                                         |
|  Y Very high throughput (millions of messages/sec)                   |
|  Y Durable (messages persisted to disk)                              |
|  Y Scalable (add partitions and brokers)                            |
|  Y Message replay (reprocess historical data)                        |
|  Y Exactly-once semantics (with transactions)                        |
|                                                                         |
|  USE CASES:                                                            |
|  * Event sourcing                                                     |
|  * Log aggregation                                                    |
|  * Stream processing                                                  |
|  * Microservices communication                                        |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  RABBITMQ                                                              |
|  ========                                                               |
|                                                                         |
|  Traditional message broker. Easy to use.                             |
|                                                                         |
|  KEY FEATURES:                                                         |
|  Y Multiple protocols (AMQP, MQTT, STOMP)                            |
|  Y Flexible routing (exchanges, bindings)                            |
|  Y Message acknowledgment                                            |
|  Y Dead letter queues                                                |
|  Y Plugins ecosystem                                                 |
|                                                                         |
|  ROUTING TYPES:                                                        |
|  * Direct: Route to specific queue                                   |
|  * Fanout: Route to all queues                                       |
|  * Topic: Route based on pattern matching                            |
|  * Headers: Route based on message headers                           |
|                                                                         |
|  USE CASES:                                                            |
|  * Task queues                                                        |
|  * RPC                                                                |
|  * Pub/sub with complex routing                                      |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  AWS SQS (Simple Queue Service)                                       |
|  ===============================                                        |
|                                                                         |
|  Fully managed queue service.                                         |
|                                                                         |
|  KEY FEATURES:                                                         |
|  Y Fully managed (no infrastructure)                                 |
|  Y Automatic scaling                                                 |
|  Y High availability                                                 |
|  Y Standard and FIFO queues                                          |
|  Y Dead letter queues                                                |
|  Y Long polling                                                      |
|                                                                         |
|  STANDARD vs FIFO:                                                     |
|  * Standard: At-least-once, unlimited throughput                    |
|  * FIFO: Exactly-once, ordered, 300 msg/sec                        |
|                                                                         |
|  USE CASES:                                                            |
|  * Decoupling microservices on AWS                                   |
|  * Serverless architectures (Lambda triggers)                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMPARISON MATRIX

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHEN TO USE WHAT?                                                     |
|                                                                         |
|  FEATURE          | Kafka      | RabbitMQ    | AWS SQS                 |
|  ---------------------------------------------------------------------  |
|  Throughput       | Very High  | Medium      | High                    |
|  Ordering         | Partition  | Queue       | FIFO only               |
|  Replay           | Yes        | No          | No                      |
|  Exactly-once     | Yes        | No          | FIFO only               |
|  Managed          | No*        | No          | Yes                     |
|  Complexity       | High       | Medium      | Low                     |
|  Best for         | Streaming  | Tasks       | AWS integration        |
|                                                                         |
|  * AWS MSK, Confluent Cloud offer managed Kafka                       |
|                                                                         |
|  QUICK DECISION:                                                       |
|  * Need message replay? > Kafka                                       |
|  * Need complex routing? > RabbitMQ                                   |
|  * On AWS, want managed? > SQS                                        |
|  * High throughput streaming? > Kafka                                 |
|  * Simple task queue? > RabbitMQ or SQS                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7.6: DESIGN PATTERNS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DEAD LETTER QUEUE (DLQ)                                              |
|  ========================                                               |
|                                                                         |
|  Messages that fail processing go to a separate queue for inspection.|
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Main Queue ----> Consumer ----> Process                       |  |
|  |                       |                                         |  |
|  |                       | Failed 3 times?                        |  |
|  |                       v                                         |  |
|  |                 Dead Letter Queue                              |  |
|  |                       |                                         |  |
|  |                       v                                         |  |
|  |              Alert + Manual inspection                         |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  OUTBOX PATTERN                                                        |
|  ==============                                                         |
|                                                                         |
|  Ensure database update and message publish happen atomically.        |
|                                                                         |
|  PROBLEM:                                                              |
|  1. Update database  Y                                               |
|  2. Publish message  X (fails)                                       |
|  > Database updated but message never sent!                          |
|                                                                         |
|  SOLUTION:                                                             |
|  +-----------------------------------------------------------------+  |
|  |  BEGIN TRANSACTION                                             |  |
|  |    1. Update orders table                                      |  |
|  |    2. Insert into outbox table                                 |  |
|  |  COMMIT                                                        |  |
|  |                                                                 |  |
|  |  Background process:                                           |  |
|  |    1. Read from outbox table                                   |  |
|  |    2. Publish to message queue                                 |  |
|  |    3. Mark outbox entry as published                          |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  SAGA PATTERN                                                          |
|  ============                                                           |
|                                                                         |
|  Distributed transaction using compensating actions.                  |
|  (Covered in detail in Distributed Transactions chapter)             |
|                                                                         |
|  Order created > Inventory reserved > Payment charged                 |
|       v               v                    v                          |
|  (If payment fails, compensate: release inventory)                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7.7: EVENT SOURCING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  EVENT SOURCING                                                        |
|                                                                         |
|  Store state changes as a sequence of events, not current state.     |
|                                                                         |
|  TRADITIONAL APPROACH (Current State):                                |
|  +-----------------------------------------------------------------+  |
|  |  Account Table                                                  |  |
|  |  +------------+----------+                                     |  |
|  |  | account_id | balance  |   UPDATE accounts                    |  |
|  |  +------------+----------+   SET balance = 750                 |  |
|  |  | 123        | 750      |   WHERE id = 123;                   |  |
|  |  +------------+----------+                                     |  |
|  |                                                                 |  |
|  |  Previous balance lost! No history.                           |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  EVENT SOURCING APPROACH:                                             |
|  +-----------------------------------------------------------------+  |
|  |  Events Log                                                     |  |
|  |  +---------------------------------------------------------+   |  |
|  |  | 1. AccountCreated { id: 123, balance: 0 }               |   |  |
|  |  | 2. MoneyDeposited { id: 123, amount: 1000 }             |   |  |
|  |  | 3. MoneyWithdrawn { id: 123, amount: 200 }              |   |  |
|  |  | 4. MoneyWithdrawn { id: 123, amount: 50 }               |   |  |
|  |  +---------------------------------------------------------+   |  |
|  |                                                                 |  |
|  |  Current balance = replay events: 0 + 1000 - 200 - 50 = 750   |  |
|  |  Full history preserved!                                       |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  BENEFITS:                                                             |
|  Y Complete audit trail                                              |
|  Y Temporal queries ("balance at 3pm yesterday")                    |
|  Y Debug by replaying events                                        |
|  Y Rebuild state from scratch                                       |
|  Y Event replay for new features                                    |
|                                                                         |
|  CHALLENGES:                                                           |
|  X Replay can be slow (use snapshots)                               |
|  X Schema evolution (event versioning)                              |
|  X Eventual consistency                                             |
|  X More complex queries                                             |
|                                                                         |
|  SNAPSHOTS:                                                            |
|  Periodically save current state to avoid full replay                |
|  Snapshot at event 100: { balance: 500 }                            |
|  To get current: Load snapshot + replay events 101-150             |
|                                                                         |
|  USE CASES: Banking, audit-heavy systems, CQRS architectures        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7.8: CQRS (Command Query Responsibility Segregation)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CQRS PATTERN                                                          |
|                                                                         |
|  Separate models for reading and writing data.                        |
|                                                                         |
|  TRADITIONAL (Same model for reads and writes):                       |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Application --> Single Database Model --> Database            |  |
|  |                  (reads & writes)                               |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  CQRS (Separate models):                                              |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  COMMANDS (Writes)                  QUERIES (Reads)            |  |
|  |       |                                   |                     |  |
|  |       v                                   v                     |  |
|  |  +-------------+                 +-------------+               |  |
|  |  |Write Model  |                 | Read Model  |               |  |
|  |  |(Normalized) |                 |(Denormalized|               |  |
|  |  +------+------+                 | for queries)|               |  |
|  |         |                        +------^------+               |  |
|  |         v                               |                      |  |
|  |  +-------------+        Events         |                      |  |
|  |  |  Write DB   | -----------------------+                      |  |
|  |  | (Source of  |     (async sync)                             |  |
|  |  |   truth)    |                                               |  |
|  |  +-------------+                                               |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  WRITE SIDE:                                                           |
|  * Handles commands (CreateOrder, UpdateProfile)                     |
|  * Validates business rules                                          |
|  * Optimized for writes                                              |
|  * Normalized schema                                                 |
|                                                                         |
|  READ SIDE:                                                            |
|  * Handles queries (GetOrderDetails, SearchProducts)                 |
|  * Optimized for specific queries                                    |
|  * Denormalized views                                                |
|  * Can use different database (Elasticsearch, Redis)                |
|                                                                         |
|  SYNC BETWEEN SIDES:                                                   |
|  * Events published after write                                      |
|  * Read model subscribes and updates                                 |
|  * Eventual consistency (not immediate)                              |
|                                                                         |
|  BENEFITS:                                                             |
|  Y Optimize reads and writes independently                          |
|  Y Scale read and write separately                                  |
|  Y Simpler models (each does one thing)                             |
|  Y Different storage tech for different needs                       |
|                                                                         |
|  WHEN TO USE:                                                          |
|  * Read and write patterns are very different                        |
|  * High read-to-write ratio                                          |
|  * Complex queries                                                    |
|  * Need to scale reads independently                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7.9: BACKPRESSURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BACKPRESSURE                                                          |
|                                                                         |
|  What happens when producer is faster than consumer?                  |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Producer (1000 msg/s) --> Queue --> Consumer (100 msg/s)     |  |
|  |                             |                                   |  |
|  |                         GROWING!                                |  |
|  |                    [][][][][][][][][]...                       |  |
|  |                                                                 |  |
|  |  Queue grows > Memory exhausted > System crash!               |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  BACKPRESSURE STRATEGIES:                                             |
|                                                                         |
|  1. DROP MESSAGES                                                      |
|  --------------------                                                   |
|  When queue full, reject new messages.                               |
|                                                                         |
|  Producer receives error > Can retry or give up                      |
|                                                                         |
|  Good for: Non-critical data (metrics, logs)                        |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. BLOCK PRODUCER                                                     |
|  ---------------------                                                  |
|  Producer waits when queue full.                                     |
|                                                                         |
|  Synchronous: Producer blocks until space available                 |
|  Async: Producer receives "slow down" signal                        |
|                                                                         |
|  Good for: Preserving all messages                                   |
|  Risk: Can cascade failures upstream                                |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. BUFFER AND BATCH                                                   |
|  ------------------------                                               |
|  Buffer messages, process in batches.                                |
|                                                                         |
|  Batching is more efficient (amortize overhead)                     |
|  But: Increased latency                                              |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  4. SAMPLE/AGGREGATE                                                   |
|  --------------------                                                   |
|  For metrics: Sample 1% or aggregate counters                       |
|                                                                         |
|  Instead of: 1000 individual events                                 |
|  Send: { count: 1000, sum: 5000, avg: 5 }                           |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  5. SCALE CONSUMERS                                                    |
|  -------------------                                                    |
|  Add more consumers when queue depth grows.                          |
|                                                                         |
|  Monitor: Queue depth, consumer lag                                  |
|  Auto-scale: Add consumers when lag exceeds threshold               |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  KAFKA CONSUMER LAG                                                    |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |  Partition                                                      |  |
|  |  [0][1][2][3][4][5][6][7][8][9][10][11][12]                    |  |
|  |              ^                       ^                          |  |
|  |         Consumer                 Latest                        |  |
|  |         Offset (5)              Offset (12)                    |  |
|  |                                                                 |  |
|  |  LAG = 12 - 5 = 7 messages                                    |  |
|  |                                                                 |  |
|  |  ALERT IF: Lag > threshold OR lag growing consistently        |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MESSAGE QUEUES - KEY TAKEAWAYS                                       |
|                                                                         |
|  WHY USE QUEUES                                                        |
|  --------------                                                        |
|  * Decouple services                                                  |
|  * Handle traffic spikes                                              |
|  * Improve resilience                                                 |
|  * Enable async processing                                            |
|                                                                         |
|  PATTERNS                                                              |
|  --------                                                              |
|  * Point-to-Point: One consumer per message                          |
|  * Pub/Sub: All subscribers get message                              |
|  * Request-Reply: Async RPC                                          |
|                                                                         |
|  DELIVERY GUARANTEES                                                   |
|  --------------------                                                  |
|  * At-most-once: May lose messages                                   |
|  * At-least-once: May duplicate (need idempotency)                   |
|  * Exactly-once: Transactional (complex)                             |
|                                                                         |
|  ORDERING                                                              |
|  --------                                                              |
|  * Use partitions with partition key                                 |
|  * Order guaranteed within partition                                 |
|                                                                         |
|  POPULAR SYSTEMS                                                       |
|  ---------------                                                       |
|  * Kafka: Streaming, high throughput, replay                         |
|  * RabbitMQ: Task queues, routing                                    |
|  * SQS: Managed, AWS integration                                     |
|                                                                         |
|  ADVANCED PATTERNS                                                     |
|  -----------------                                                     |
|  * Event Sourcing: Store events, derive state                        |
|  * CQRS: Separate read/write models                                  |
|  * Backpressure: Handle slow consumers                               |
|                                                                         |
|  INTERVIEW TIP                                                         |
|  -------------                                                         |
|  Always mention idempotency when discussing at-least-once delivery.  |
|  Discuss trade-offs between different queue systems.                 |
|  Know when Event Sourcing/CQRS add value vs complexity.              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 7

