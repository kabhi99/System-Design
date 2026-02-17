# APACHE KAFKA
*Chapter 5: Interview Questions and Answers*

This chapter covers 25 commonly asked Kafka interview questions,
from fundamentals to advanced topics, with detailed answers.

## SECTION 5.1: FUNDAMENTALS (Q1-Q8)

### Q1: What is Apache Kafka and why would you use it?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Kafka is a distributed event streaming platform that acts as a         |
|  high-throughput, fault-tolerant commit log.                            |
|                                                                         |
|  USE IT WHEN YOU NEED:                                                  |
|  * Decouple producers from consumers (microservices)                    |
|  * Handle massive throughput (millions of events/sec)                   |
|  * Event replay (reprocess historical data)                             |
|  * Real-time stream processing                                         |
|  * Durable audit log / event sourcing                                   |
|                                                                         |
|  KEY DIFFERENCE FROM TRADITIONAL QUEUES:                                |
|  * Messages are NOT deleted after consumption                           |
|  * Multiple consumer groups can read the same data                      |
|  * Consumers pull data (not push)                                       |
|  * Ordering guaranteed within a partition                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q2: Explain Topics, Partitions, and Offsets.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TOPIC: A named stream of records (like a database table).              |
|         Example: "user-events", "order-created"                         |
|                                                                         |
|  PARTITION: A topic is split into partitions for parallelism.           |
|         Each partition is an ordered, immutable log.                    |
|         Partitions live on different brokers for scalability.           |
|                                                                         |
|  OFFSET: A unique sequential ID for each message in a partition.        |
|         Consumers track offsets to know where they left off.            |
|         Offsets are per-partition, not per-topic.                       |
|                                                                         |
|  EXAMPLE:                                                               |
|  Topic "orders" with 3 partitions:                                      |
|    P0: [offset0, offset1, offset2, ...]                                 |
|    P1: [offset0, offset1, ...]                                          |
|    P2: [offset0, offset1, offset2, offset3, ...]                        |
|                                                                         |
|  Each partition can be on a different broker and consumed                |
|  by a different consumer in the same group.                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q3: What is a Consumer Group?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  A set of consumers that cooperate to consume a topic.                  |
|                                                                         |
|  RULES:                                                                 |
|  * Each partition is assigned to exactly ONE consumer in the group       |
|  * One consumer can read from multiple partitions                       |
|  * If consumers > partitions, extras sit idle                           |
|  * If a consumer dies, its partitions are rebalanced to others          |
|                                                                         |
|  MULTIPLE GROUPS:                                                       |
|  * Different groups read the SAME data independently                    |
|  * Group "payments" and group "analytics" both get all messages          |
|  * This is how Kafka does pub-sub AND load balancing                    |
|                                                                         |
|  INTERVIEW TIP: "Consumer groups give you pub-sub (between groups)      |
|  and competing consumers (within a group) at the same time."            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q4: How does Kafka guarantee message ordering?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Kafka guarantees ordering WITHIN A PARTITION, not across partitions.    |
|                                                                         |
|  To ensure ordering for related messages:                               |
|  * Use the same MESSAGE KEY for related events                          |
|  * Same key = same partition = same order                               |
|                                                                         |
|  Example: All events for order-123 use key="order-123"                  |
|  They all go to the same partition and are ordered.                     |
|                                                                         |
|  GOTCHA: If you add partitions, key-to-partition mapping changes!       |
|  Existing keys may go to different partitions. Plan partition count      |
|  carefully upfront.                                                     |
|                                                                         |
|  GLOBAL ORDERING: Use a topic with 1 partition.                         |
|  But this kills parallelism. Avoid unless absolutely necessary.         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q5: What are acks=0, acks=1, and acks=all?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  acks=0: Producer does not wait for broker confirmation.                |
|          Fastest. Risk of data loss (broker may not have received it).   |
|          Use: metrics, logs where some loss is OK.                      |
|                                                                         |
|  acks=1: Producer waits for LEADER to write to its local log.           |
|          Good balance. Risk: leader dies before replicating.            |
|          Use: most applications (default).                              |
|                                                                         |
|  acks=all: Producer waits for ALL in-sync replicas to confirm.          |
|          Safest. Slowest. No data loss if >= 1 ISR alive.               |
|          Use: financial data, critical events.                          |
|          MUST pair with min.insync.replicas >= 2.                       |
|                                                                         |
|  INTERVIEW TIP: "acks=all alone is not enough. Without                  |
|  min.insync.replicas=2, if ISR shrinks to just the leader,              |
|  acks=all becomes equivalent to acks=1."                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q6: How does Kafka achieve high throughput?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. SEQUENTIAL I/O                                                      |
|     Append-only writes to disk. No random seeks.                        |
|     Sequential writes on modern disks: 600+ MB/sec.                     |
|                                                                         |
|  2. ZERO-COPY (sendfile syscall)                                        |
|     Data goes from disk to network without entering JVM heap.           |
|     Disk -> OS Page Cache -> NIC (no user-space copy).                  |
|                                                                         |
|  3. OS PAGE CACHE                                                       |
|     Kafka relies on the OS to cache recently written data in RAM.       |
|     Consumers reading recent data get it from RAM, not disk.            |
|                                                                         |
|  4. BATCHING                                                            |
|     Producer batches multiple messages into one network request.        |
|     Consumer fetches many messages in one poll().                       |
|                                                                         |
|  5. COMPRESSION                                                         |
|     Batches are compressed (lz4/zstd), reducing network I/O.           |
|     Stored compressed on disk too.                                      |
|                                                                         |
|  6. PARTITIONING                                                        |
|     Horizontal scaling. More partitions = more parallel I/O.            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q7: Kafka vs RabbitMQ -- when to use which?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  USE KAFKA WHEN:                                                        |
|  * High throughput (100K+ msg/sec)                                      |
|  * Event replay / reprocessing needed                                   |
|  * Stream processing (Kafka Streams, Flink)                             |
|  * Event sourcing / CQRS architecture                                   |
|  * Multiple consumers need the same data                                |
|  * Long retention (days/weeks of data)                                  |
|                                                                         |
|  USE RABBITMQ WHEN:                                                     |
|  * Complex routing logic (topic, fanout, header exchanges)              |
|  * Task queue pattern (each task processed once)                        |
|  * Low latency is critical (sub-ms possible)                            |
|  * Message-level acknowledgment needed                                  |
|  * Priority queues needed                                               |
|  * Smaller scale (< 10K msg/sec)                                        |
|                                                                         |
|  INTERVIEW TIP: "Kafka is a log, RabbitMQ is a broker.                  |
|  Kafka stores everything, RabbitMQ delivers and forgets.                |
|  This fundamental difference drives all trade-offs."                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q8: What is ISR and why does it matter?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ISR = In-Sync Replica set                                              |
|                                                                         |
|  The set of replicas (including leader) that are fully caught up.       |
|  A follower is removed from ISR if it falls behind by more than         |
|  replica.lag.time.max.ms (default 30 seconds).                          |
|                                                                         |
|  WHY IT MATTERS:                                                        |
|  * acks=all only waits for ISR members (not all replicas)               |
|  * If ISR shrinks to 1 (just leader), you lose safety                   |
|  * min.insync.replicas prevents writes when ISR is too small            |
|  * Leader election only picks from ISR (unless unclean enabled)         |
|                                                                         |
|  RECOMMENDED: replication.factor=3, min.insync.replicas=2               |
|  This tolerates 1 broker failure with zero data loss.                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.2: INTERMEDIATE (Q9-Q16)

### Q9: How does Kafka handle consumer failure / rebalancing?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  When a consumer in a group fails:                                      |
|                                                                         |
|  1. Consumer stops sending heartbeats                                   |
|  2. Group coordinator detects failure (session.timeout.ms)              |
|  3. Coordinator triggers a REBALANCE                                    |
|  4. Partitions from dead consumer are reassigned to others              |
|                                                                         |
|  REBALANCE STRATEGIES:                                                  |
|  * Eager: All consumers stop, all partitions reassigned (old default)   |
|  * Cooperative: Only affected partitions move (Kafka 2.4+)              |
|  * Static membership: Consumer gets fixed ID, survives restarts         |
|                                                                         |
|  MINIMIZE REBALANCES:                                                   |
|  * Use static group membership (group.instance.id)                      |
|  * Increase session.timeout.ms (e.g., 30s)                             |
|  * Process messages faster (don't exceed max.poll.interval.ms)          |
|  * Use cooperative sticky assignor                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q10: What is log compaction and when would you use it?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Log compaction keeps the LATEST value for each key and discards        |
|  older values. Unlike time-based retention, compaction is key-based.    |
|                                                                         |
|  Before: [K1=A] [K2=B] [K1=C] [K3=D] [K2=E] [K1=F]                    |
|  After:  [K3=D] [K2=E] [K1=F]                                          |
|                                                                         |
|  USE CASES:                                                             |
|  * Database changelog (CDC) -- latest state of each row                 |
|  * User profile updates -- latest profile per user                      |
|  * Configuration distribution -- latest config per service              |
|  * Kafka Streams state store changelogs                                 |
|                                                                         |
|  TOMBSTONE: A message with key + null value.                            |
|  Tells compaction to DELETE this key entirely after a grace period.      |
|                                                                         |
|  CONFIG: cleanup.policy=compact                                         |
|  Can combine: cleanup.policy=compact,delete                             |
|  (compact + delete segments older than retention.ms)                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q11: How would you handle exactly-once processing?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Three approaches:                                                      |
|                                                                         |
|  1. IDEMPOTENT PRODUCER (simplest)                                      |
|     enable.idempotence=true                                             |
|     Prevents duplicates on producer retries within a partition.          |
|     Does NOT cover consumer side.                                       |
|                                                                         |
|  2. KAFKA TRANSACTIONS (strongest)                                      |
|     Atomic read-process-write across topics.                            |
|     Consumer reads with isolation.level=read_committed.                 |
|     Covers both producer and consumer side.                             |
|     Cost: ~20% throughput overhead.                                     |
|                                                                         |
|  3. IDEMPOTENT CONSUMER (pragmatic, most common)                        |
|     Use at-least-once delivery + make processing idempotent.            |
|     Store a dedup key (message ID) in your database.                    |
|     On duplicate, skip processing.                                      |
|                                                                         |
|  INTERVIEW TIP: "In practice, most teams use at-least-once             |
|  delivery with idempotent consumers. Kafka transactions exist           |
|  but add complexity and are mainly used in Kafka-to-Kafka               |
|  stream processing pipelines."                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q12: How do you decide the number of partitions?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FORMULA:                                                               |
|  partitions = max(T/Tp, T/Tc)                                          |
|                                                                         |
|  Where:                                                                 |
|  T  = target throughput (e.g., 100 MB/sec)                              |
|  Tp = throughput per partition on producer side (~10 MB/sec)             |
|  Tc = throughput per partition on consumer side (~20 MB/sec)             |
|                                                                         |
|  Example: 100 MB/sec target, 10 MB/sec per partition                    |
|  partitions = 100/10 = 10 partitions minimum                            |
|                                                                         |
|  GUIDELINES:                                                            |
|  * Start with num_partitions >= expected max consumer count             |
|  * 6-30 partitions per topic is typical                                 |
|  * More partitions = more memory, file handles, leader elections        |
|  * Each partition adds ~10MB broker memory overhead                     |
|  * You can ADD partitions but NEVER reduce them                         |
|  * Adding partitions breaks key ordering for existing keys              |
|                                                                         |
|  RULE OF THUMB:                                                         |
|  * Low throughput topic: 6 partitions                                   |
|  * Medium throughput: 12-24 partitions                                  |
|  * High throughput: 30-100 partitions                                   |
|  * Cluster limit: ~4000 partitions per broker (with KRaft)              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q13: What happens when a Kafka broker goes down?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. Controller detects broker failure via missing heartbeat             |
|  2. For each partition where dead broker was LEADER:                    |
|     a. Controller picks new leader from ISR                             |
|     b. Notifies all brokers of new leader assignments                   |
|     c. Producers/consumers redirect to new leaders                      |
|  3. For partitions where dead broker was FOLLOWER:                      |
|     a. ISR shrinks (follower removed)                                   |
|     b. No impact on reads/writes (leader is still alive)                |
|  4. When broker recovers:                                               |
|     a. Catches up with leaders (fetches missed data)                    |
|     b. Re-joins ISR once caught up                                      |
|     c. May become leader again (preferred replica election)             |
|                                                                         |
|  FAILOVER TIME:                                                         |
|  * KRaft mode: seconds                                                  |
|  * ZooKeeper mode: 10-30 seconds (sometimes minutes)                   |
|                                                                         |
|  DATA LOSS SCENARIOS:                                                   |
|  * acks=1 + leader dies before replication = LOST MESSAGES              |
|  * acks=all + min.insync.replicas=2 = NO DATA LOSS                     |
|  * All ISR replicas dead + unclean.leader.election=true = POSSIBLE LOSS |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q14: How does Kafka differ from a database?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------------+---------------------------+--------------------+ |
|  | Feature           | Kafka                     | Database (RDBMS)   | |
|  +-------------------+---------------------------+--------------------+ |
|  | Data model        | Append-only log           | Tables with CRUD   | |
|  | Writes            | Append only               | Insert/Update/Del  | |
|  | Reads             | Sequential scan           | Random access      | |
|  | Indexes           | Offset-based only         | B-tree, hash, etc  | |
|  | Query             | No query language         | SQL                | |
|  | Retention         | Time/size based            | Indefinite         | |
|  | Transactions      | Limited (EOS)             | Full ACID          | |
|  | Throughput        | Millions/sec              | Thousands/sec      | |
|  | Primary use       | Event transport + replay  | State storage      | |
|  +-------------------+---------------------------+--------------------+ |
|                                                                         |
|  INTERVIEW TIP: "Kafka is a transportation system, not a database.      |
|  It moves data between systems. Use it alongside databases,             |
|  not instead of them."                                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q15: What is backpressure and how does Kafka handle it?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Backpressure = consumer is slower than producer.                       |
|                                                                         |
|  HOW KAFKA HANDLES IT:                                                  |
|                                                                         |
|  1. Consumer just falls behind (lag increases)                          |
|     Kafka retains messages, consumer catches up at its own pace.        |
|     No message loss, no producer slowdown.                              |
|                                                                         |
|  2. Producer-side buffer full (buffer.memory exhausted)                  |
|     producer.send() blocks for max.block.ms then throws exception.      |
|                                                                         |
|  MITIGATION STRATEGIES:                                                 |
|  * Scale consumers (add more to the group, up to partition count)       |
|  * Increase partitions (allows more parallel consumers)                 |
|  * Optimize consumer processing (batch writes, async I/O)              |
|  * Increase retention to handle temporary spikes                        |
|  * Use consumer lag alerting to detect early                            |
|                                                                         |
|  KAFKA ADVANTAGE OVER PUSH-BASED SYSTEMS:                               |
|  Since consumers pull, they naturally self-regulate. A slow consumer    |
|  doesn't slow down producers or other consumers.                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q16: Explain the difference between Kafka Streams and Flink.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------------+----------------------------+------------------+  |
|  | Feature           | Kafka Streams              | Apache Flink     |  |
|  +-------------------+----------------------------+------------------+  |
|  | Deployment        | Library (embedded in app)  | Separate cluster |  |
|  | Source/Sink        | Kafka only                 | Many (Kafka, DB) |  |
|  | State             | RocksDB (local)            | Checkpointed     |  |
|  | Exactly-once      | Yes (Kafka native)         | Yes              |  |
|  | Windowing         | Basic                      | Advanced         |  |
|  | SQL support       | ksqlDB (separate)          | Flink SQL        |  |
|  | Scaling           | Consumer group rebalance   | Task managers    |  |
|  | Ops complexity    | Low (just your app)        | High (cluster)   |  |
|  +-------------------+----------------------------+------------------+  |
|                                                                         |
|  USE KAFKA STREAMS: Simple transformations, Kafka-only pipeline,        |
|  want to avoid managing another cluster.                                |
|                                                                         |
|  USE FLINK: Complex event processing, multi-source joins,               |
|  advanced windowing, SQL over streams, large-scale aggregations.        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.3: ADVANCED (Q17-Q25)

### Q17: How would you design a Kafka-based system for 1 million events/sec?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CAPACITY ESTIMATION:                                                   |
|  * 1M events/sec, avg 1KB each = 1 GB/sec throughput                   |
|  * Each partition handles ~10 MB/sec = 100 partitions minimum           |
|  * Replication factor 3 = 3 GB/sec total disk write                     |
|  * Retention 7 days = 1 GB/sec x 86400 x 7 = ~600 TB storage           |
|                                                                         |
|  CLUSTER SIZING:                                                        |
|  * 12-20 brokers (50-100 partitions per broker)                         |
|  * Each broker: 12-core CPU, 64GB RAM, 12x 2TB SSDs (JBOD)             |
|  * Network: 10 Gbps NIC per broker                                      |
|  * JVM heap: 6GB (rest for page cache)                                  |
|                                                                         |
|  PRODUCER CONFIG:                                                       |
|  * batch.size=256KB, linger.ms=10                                       |
|  * compression.type=lz4                                                 |
|  * acks=1 (or acks=all for critical data)                               |
|  * buffer.memory=128MB                                                  |
|                                                                         |
|  CONSUMER CONFIG:                                                       |
|  * 100+ consumer instances (1 per partition)                            |
|  * fetch.min.bytes=1MB, fetch.max.wait.ms=500                           |
|  * Batch processing (write to DB in batches)                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q18: How do you prevent data loss in Kafka?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PRODUCER SIDE:                                                         |
|  * acks=all (wait for all ISR replicas)                                 |
|  * enable.idempotence=true (prevent duplicates on retry)                |
|  * retries=MAX_INT (keep retrying)                                      |
|  * max.in.flight.requests.per.connection=5                              |
|                                                                         |
|  BROKER SIDE:                                                           |
|  * replication.factor=3 (minimum)                                       |
|  * min.insync.replicas=2                                                |
|  * unclean.leader.election.enable=false                                 |
|  * default.replication.factor=3 (for auto-created topics)               |
|                                                                         |
|  CONSUMER SIDE:                                                         |
|  * enable.auto.commit=false (manual commit after processing)            |
|  * Process, THEN commit offset                                          |
|  * Make processing idempotent (handle redelivery gracefully)            |
|                                                                         |
|  OPERATIONAL:                                                           |
|  * Monitor ISR shrink alerts                                            |
|  * Monitor under-replicated partitions                                  |
|  * Regular broker health checks                                         |
|  * Test failover scenarios regularly                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q19: What is the __consumer_offsets topic?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  An internal Kafka topic that stores committed consumer offsets.         |
|                                                                         |
|  * Created automatically (50 partitions by default)                     |
|  * Key = (group.id, topic, partition)                                   |
|  * Value = committed offset + metadata + timestamp                      |
|  * Compacted (keeps only latest offset per key)                         |
|                                                                         |
|  When consumer calls commitSync() or auto-commits:                      |
|  * A message is produced to __consumer_offsets                          |
|  * Contains the offset the consumer has processed up to                 |
|                                                                         |
|  When consumer restarts:                                                |
|  * Reads its last committed offset from __consumer_offsets              |
|  * Resumes from that position                                           |
|                                                                         |
|  BEFORE KAFKA 0.9: Offsets were stored in ZooKeeper.                    |
|  This caused performance issues at scale.                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q20: How does Kafka handle schema evolution?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  USE SCHEMA REGISTRY + AVRO/PROTOBUF:                                   |
|                                                                         |
|  * Producer registers schema, gets schema ID                            |
|  * Messages contain schema ID + serialized data (not full schema)       |
|  * Consumer fetches schema by ID, deserializes                          |
|                                                                         |
|  COMPATIBILITY MODES:                                                   |
|  * BACKWARD: New schema can read old data                               |
|    (safe to add optional fields with defaults)                          |
|  * FORWARD: Old schema can read new data                                |
|    (safe to remove optional fields)                                     |
|  * FULL: Both backward and forward                                      |
|  * NONE: No checks (dangerous, avoid in prod)                           |
|                                                                         |
|  BEST PRACTICE:                                                         |
|  * Use BACKWARD compatibility (most common)                             |
|  * Always add new fields as OPTIONAL with defaults                      |
|  * Never remove or rename required fields                               |
|  * Never change field types                                             |
|  * Use schema registry in CI/CD to validate before deploy               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q21: What is the difference between KRaft and ZooKeeper?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------------+-------------------------+---------------------+  |
|  | Aspect            | ZooKeeper               | KRaft               |  |
|  +-------------------+-------------------------+---------------------+  |
|  | Architecture      | External ZK cluster     | Built into Kafka    |  |
|  | Dependencies      | Java ZK + Kafka         | Kafka only          |  |
|  | Metadata store    | ZK znodes               | Internal topic      |  |
|  | Failover speed    | 10-30 seconds           | < 5 seconds         |  |
|  | Partition limit   | ~200K per cluster       | Millions            |  |
|  | Ops complexity    | 2 clusters to manage    | 1 cluster           |  |
|  | Status            | Deprecated (Kafka 4.0)  | Default / Future    |  |
|  +-------------------+-------------------------+---------------------+  |
|                                                                         |
|  KRaft uses the Raft consensus protocol for controller election         |
|  and metadata replication. No external dependency.                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q22: How would you monitor a Kafka cluster in production?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KEY METRICS TO MONITOR:                                                |
|                                                                         |
|  BROKER:                                                                |
|  * UnderReplicatedPartitions (> 0 means trouble)                        |
|  * ActiveControllerCount (exactly 1 per cluster)                        |
|  * OfflinePartitionsCount (should be 0)                                 |
|  * RequestHandlerAvgIdlePercent (< 30% = overloaded)                    |
|  * NetworkProcessorAvgIdlePercent                                       |
|  * LogFlushRateAndTimeMs                                                |
|                                                                         |
|  PRODUCER:                                                              |
|  * record-send-rate (throughput)                                        |
|  * record-error-rate (failures)                                         |
|  * request-latency-avg                                                  |
|  * batch-size-avg                                                       |
|                                                                         |
|  CONSUMER:                                                              |
|  * records-lag-max (most critical -- consumer falling behind)           |
|  * records-consumed-rate                                                |
|  * commit-latency-avg                                                   |
|  * rebalance-rate                                                       |
|                                                                         |
|  TOOLS:                                                                 |
|  * Prometheus + Grafana (JMX exporter)                                  |
|  * Confluent Control Center (commercial)                                |
|  * Burrow (consumer lag monitoring by LinkedIn)                         |
|  * Cruise Control (cluster balancing by LinkedIn)                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q23: How do you handle poison pill messages?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Poison pill = a message that crashes the consumer every time.          |
|                                                                         |
|  If not handled, the consumer restarts, reads the same message,         |
|  crashes again -> infinite loop.                                        |
|                                                                         |
|  SOLUTIONS:                                                             |
|                                                                         |
|  1. TRY-CATCH WITH DLQ                                                  |
|     try { process(msg); } catch { sendToDLQ(msg); commitOffset(); }     |
|     Move bad message to dead letter queue, continue processing.         |
|                                                                         |
|  2. RETRY WITH BACKOFF                                                  |
|     Retry N times with exponential backoff.                             |
|     After N failures, send to DLQ.                                      |
|                                                                         |
|  3. SCHEMA VALIDATION                                                   |
|     Validate message schema BEFORE processing.                          |
|     Reject malformed messages immediately.                              |
|                                                                         |
|  4. SKIP AND LOG                                                        |
|     Log the bad message, skip it, commit offset.                        |
|     Simplest but may lose data.                                         |
|                                                                         |
|  BEST PRACTICE: Option 1 or 2 with alerting on DLQ.                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q24: Explain Kafka's exactly-once for a Kafka Streams app.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Kafka Streams processing.guarantee = "exactly_once_v2"                 |
|                                                                         |
|  WHAT IT COVERS:                                                        |
|  * Read from input topic                                                |
|  * Process / transform                                                  |
|  * Write to output topic                                                |
|  * Update state store                                                   |
|  * Commit consumer offsets                                              |
|  ALL done atomically in a single Kafka transaction.                     |
|                                                                         |
|  HOW IT WORKS:                                                          |
|  1. Kafka Streams reads a batch from input partitions                   |
|  2. Processes records, buffers output records                           |
|  3. Begins a Kafka transaction                                          |
|  4. Writes output records to output topic                               |
|  5. Writes state store changelog records                                |
|  6. Commits input consumer offsets                                      |
|  7. Commits transaction (all-or-nothing)                                |
|                                                                         |
|  COST: ~20% throughput reduction vs at_least_once.                      |
|  Worth it for: financial data, billing, inventory.                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q25: How would you migrate from RabbitMQ to Kafka?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MIGRATION STRATEGY (gradual, not big-bang):                            |
|                                                                         |
|  PHASE 1: DUAL WRITE                                                    |
|  * Producer writes to BOTH RabbitMQ and Kafka                           |
|  * Existing consumers still read from RabbitMQ                          |
|  * Verify Kafka data matches RabbitMQ                                   |
|                                                                         |
|  PHASE 2: DUAL READ                                                     |
|  * New consumers read from Kafka                                        |
|  * Old consumers still on RabbitMQ (shadow mode)                        |
|  * Compare results between old and new consumers                        |
|                                                                         |
|  PHASE 3: CUTOVER                                                       |
|  * Switch producers to Kafka only                                       |
|  * Decommission RabbitMQ consumers                                      |
|  * Monitor for issues                                                   |
|                                                                         |
|  KEY DIFFERENCES TO ADDRESS:                                            |
|  * RabbitMQ pushes, Kafka pulls (rewrite consumer loop)                 |
|  * RabbitMQ deletes after ack, Kafka retains (offset management)        |
|  * RabbitMQ per-message ack, Kafka batch commit                         |
|  * Message key strategy (for ordering in Kafka)                         |
|  * Schema format (Kafka favors Avro/Protobuf)                           |
|                                                                         |
+-------------------------------------------------------------------------+
```
