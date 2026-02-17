# APACHE KAFKA
*Chapter 3: Producers and Consumers In Depth*

Mastering Kafka means understanding how producers and consumers work
internally -- batching, acknowledgments, offset management, and
rebalancing determine your system's delivery guarantees and performance.

## SECTION 3.1: PRODUCER INTERNALS

```
+--------------------------------------------------------------------------+
|                                                                          |
|  PRODUCER ARCHITECTURE                                                   |
|                                                                          |
|  Application Thread                                                      |
|       |                                                                  |
|       v                                                                  |
|  +----------+     +-----------+     +-----------+                        |
|  | Serialize | --> | Partition | --> | Record    |                       |
|  | Key+Value |     | (choose   |     | Accumul-  |                       |
|  |           |     |  target   |     | ator      |                       |
|  +----------+     |  partition)|     | (batching)|                       |
|                    +-----------+     +-----+-----+                       |
|                                            |                             |
|                                    +-------v-------+                     |
|                                    | Sender Thread |                     |
|                                    | (background)  |                     |
|                                    +-------+-------+                     |
|                                            |                             |
|                              +-------------+-------------+               |
|                              |             |             |               |
|                              v             v             v               |
|                          Broker 0      Broker 1      Broker 2            |
|                                                                          |
+--------------------------------------------------------------------------+
```

### BATCHING AND COMPRESSION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BATCHING (critical for throughput)                                     |
|                                                                         |
|  The producer accumulates messages into batches BEFORE sending.         |
|                                                                         |
|  KEY CONFIGS:                                                           |
|                                                                         |
|  batch.size = 16384 (16KB default)                                      |
|    Max bytes per batch. Batch is sent when this is full.                |
|                                                                         |
|  linger.ms = 0 (default)                                                |
|    How long to wait for more messages before sending a batch.           |
|    Set to 5-100ms for higher throughput (more batching).                |
|                                                                         |
|  buffer.memory = 33554432 (32MB default)                                |
|    Total memory for unsent messages. If full, send() blocks.            |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  COMPRESSION (applied per batch):                                       |
|                                                                         |
|  compression.type = none | gzip | snappy | lz4 | zstd                   |
|                                                                         |
|  +----------+--------+--------+----------+                              |
|  | Type     | Ratio  | Speed  | CPU      |                              |
|  +----------+--------+--------+----------+                              |
|  | none     | 1x     | -      | none     |                              |
|  | gzip     | best   | slow   | high     |                              |
|  | snappy   | good   | fast   | low      |                              |
|  | lz4      | good   | fastest| lowest   |                              |
|  | zstd     | best   | fast   | medium   |                              |
|  +----------+--------+--------+----------+                              |
|                                                                         |
|  RECOMMENDATION: Use lz4 or zstd for most workloads.                    |
|  Compression saves network bandwidth AND disk space.                    |
|  Broker stores compressed batches as-is (no re-compression).            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### ACKNOWLEDGMENTS (acks)

```
+--------------------------------------------------------------------------+
|                                                                          |
|  acks SETTING = How many replicas must confirm before success            |
|                                                                          |
|  acks=0 (FIRE AND FORGET)                                                |
|  ========================                                                |
|  Producer does not wait for any acknowledgment.                          |
|  Fastest. Risk: messages may be lost.                                    |
|                                                                          |
|  Producer --> Broker (no response waited)                                |
|                                                                          |
|  Use case: metrics, logs where some loss is acceptable.                  |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  acks=1 (LEADER ONLY)                                                    |
|  =====================                                                   |
|  Leader writes to its local log and responds.                            |
|  Followers may not have the data yet.                                    |
|  Risk: data loss if leader dies before followers replicate.              |
|                                                                          |
|  Producer --> Leader (ack) --> Followers (async)                         |
|                                                                          |
|  Use case: default for most applications. Good balance.                  |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  acks=all (or acks=-1) (FULL REPLICATION)                                |
|  ==========================================                              |
|  Leader waits for ALL in-sync replicas (ISR) to acknowledge.             |
|  Slowest but safest. No data loss as long as >= 1 ISR alive.             |
|                                                                          |
|  Producer --> Leader --> All ISR Followers --> (ack)                     |
|                                                                          |
|  Use case: financial transactions, critical events.                      |
|  MUST combine with min.insync.replicas >= 2.                             |
|                                                                          |
+--------------------------------------------------------------------------+
```

### IDEMPOTENT PRODUCER

```
+--------------------------------------------------------------------------+
|                                                                          |
|  PROBLEM: Duplicate messages on retry                                    |
|                                                                          |
|  Producer sends msg --> network timeout --> producer retries             |
|  But the broker DID receive the first one --> DUPLICATE!                 |
|                                                                          |
|  SOLUTION: enable.idempotence = true (default since Kafka 3.0)           |
|                                                                          |
|  How it works:                                                           |
|  * Each producer gets a unique Producer ID (PID)                         |
|  * Each message gets a sequence number (per partition)                   |
|  * Broker rejects duplicates with same PID + sequence number             |
|                                                                          |
|  Producer (PID=7):                                                       |
|    send(seq=0) --> Broker accepts                                        |
|    send(seq=1) --> network timeout, retry                                |
|    send(seq=1) --> Broker sees duplicate, returns success (no dup)       |
|    send(seq=2) --> Broker accepts                                        |
|                                                                          |
|  REQUIREMENTS:                                                           |
|  * acks=all (set automatically)                                          |
|  * retries > 0 (set automatically)                                       |
|  * max.in.flight.requests.per.connection <= 5                            |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 3.2: CONSUMER INTERNALS

### POLL LOOP

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE CONSUMER POLL LOOP                                                 |
|                                                                         |
|  Every Kafka consumer runs a poll loop:                                 |
|                                                                         |
|  while (true) {                                                         |
|      records = consumer.poll(Duration.ofMillis(100));                   |
|      for (record : records) {                                           |
|          process(record);                                               |
|      }                                                                  |
|  }                                                                      |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  WHAT poll() DOES INTERNALLY:                                           |
|                                                                         |
|  1. Sends heartbeat to group coordinator (I'm alive!)                   |
|  2. Fetches records from assigned partitions                            |
|  3. Auto-commits offsets (if enabled)                                   |
|  4. Handles rebalance callbacks                                         |
|                                                                         |
|  KEY CONFIGS:                                                           |
|                                                                         |
|  max.poll.records = 500                                                 |
|    Max records returned per poll() call.                                |
|                                                                         |
|  max.poll.interval.ms = 300000 (5 min)                                  |
|    Max time between poll() calls before consumer is kicked out.         |
|    If processing takes longer, increase this or process async.          |
|                                                                         |
|  fetch.min.bytes = 1                                                    |
|    Min data to return. Increase for throughput (e.g., 1MB).             |
|                                                                         |
|  fetch.max.wait.ms = 500                                                |
|    Max time broker waits to fill fetch.min.bytes.                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### OFFSET MANAGEMENT

```
+--------------------------------------------------------------------------+
|                                                                          |
|  OFFSET COMMIT STRATEGIES                                                |
|                                                                          |
|  1. AUTO-COMMIT (default)                                                |
|     ==========================                                           |
|     enable.auto.commit = true                                            |
|     auto.commit.interval.ms = 5000                                       |
|                                                                          |
|     Every 5 seconds, the consumer automatically commits                  |
|     the latest offset it has poll()'d.                                   |
|                                                                          |
|     Risk: AT-LEAST-ONCE delivery                                         |
|     * If consumer crashes AFTER poll() but BEFORE commit                 |
|       --> messages re-delivered on restart (duplicates)                  |
|     * If consumer crashes AFTER commit but BEFORE processing             |
|       --> messages LOST (already committed)                              |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  2. MANUAL COMMIT (recommended for critical systems)                     |
|     =================================================                    |
|     enable.auto.commit = false                                           |
|                                                                          |
|     a) commitSync() -- blocks until offset is committed                  |
|        Safest, but slower.                                               |
|                                                                          |
|     b) commitAsync() -- fire and forget, with callback                   |
|        Faster, but no guarantee of commit success.                       |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  DELIVERY SEMANTICS:                                                     |
|                                                                          |
|  +-------------------+--------------------------+----------------------+ |
|  | Semantic          | How                      | Risk                 | |
|  +-------------------+--------------------------+----------------------+ |
|  | At-most-once      | Commit BEFORE processing | Lost messages        | |
|  | At-least-once     | Commit AFTER processing  | Duplicate messages   | |
|  | Exactly-once      | Kafka transactions       | Complexity + cost    | |
|  +-------------------+--------------------------+----------------------+ |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 3.3: CONSUMER REBALANCING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS A REBALANCE?                                                   |
|                                                                         |
|  Reassignment of partitions to consumers within a group.                |
|                                                                         |
|  Triggered when:                                                        |
|  * A consumer joins the group                                           |
|  * A consumer leaves the group (crash or shutdown)                      |
|  * A consumer is kicked out (missed poll() deadline)                    |
|  * Partitions are added to a subscribed topic                           |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  EAGER REBALANCE (default before 2.4)                                   |
|  =====================================                                  |
|  1. ALL consumers stop reading                                          |
|  2. ALL consumers give up their partitions                              |
|  3. Coordinator reassigns all partitions                                |
|  4. All consumers get new assignments                                   |
|                                                                         |
|  Problem: "stop the world" -- ALL consumers pause briefly               |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  COOPERATIVE (INCREMENTAL) REBALANCE (2.4+)                             |
|  =============================================                          |
|  1. Only AFFECTED partitions are revoked                                |
|  2. Other consumers continue reading unaffected partitions              |
|  3. Revoked partitions are reassigned                                   |
|                                                                         |
|  Much less disruption. Set via:                                         |
|  partition.assignment.strategy =                                        |
|    org.apache.kafka.clients.consumer.CooperativeStickyAssignor          |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  STATIC GROUP MEMBERSHIP (minimize rebalances)                          |
|  ===============================================                        |
|  group.instance.id = "consumer-1"                                       |
|                                                                         |
|  * Consumer gets a fixed identity                                       |
|  * On restart, gets same partitions back (no rebalance)                 |
|  * Only triggers rebalance if gone > session.timeout.ms                 |
|  * Best for: stateful consumers, K8s rolling restarts                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.4: CONSUMER LAG MONITORING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CONSUMER LAG = latest offset - consumer's committed offset             |
|                                                                         |
|  Partition 0:                                                           |
|  [0] [1] [2] [3] [4] [5] [6] [7] [8] [9] [10] [11] [12]                 |
|                          ^                          ^                   |
|                          |                          |                   |
|                   consumer offset=5           latest offset=12          |
|                                                                         |
|                   LAG = 12 - 5 = 7 messages behind                      |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  MONITORING TOOLS:                                                      |
|  * kafka-consumer-groups.sh --describe --group my-group                 |
|  * Burrow (LinkedIn's lag monitoring tool)                              |
|  * Kafka JMX metrics (records-lag-max)                                  |
|  * Prometheus + Grafana dashboards                                      |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  WHEN LAG IS HIGH:                                                      |
|  * Consumer is too slow -> optimize processing or add consumers         |
|  * Consumer is stuck -> check for blocking I/O or deadlocks             |
|  * Spike in producer traffic -> auto-scale consumers                    |
|  * Consumer rebalancing too often -> use static membership              |
|                                                                         |
+-------------------------------------------------------------------------+
```

```bash
# Check consumer lag from CLI                                               
bin/kafka-consumer-groups.sh \                                              
    --bootstrap-server localhost:9092 \                                     
    --describe \                                                            
    --group order-service                                                   

# Output:                                                                   
# GROUP          TOPIC        PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
# order-service  orders       0          1000            1050            50 
# order-service  orders       1          2000            2005            5  
# order-service  orders       2          1500            1500            0  
```
