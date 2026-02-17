# APACHE KAFKA
*Chapter 2: Architecture Deep Dive*

Understanding Kafka's internals is essential for designing reliable,
high-performance event-driven systems. This chapter covers how Kafka
stores data, replicates it, and handles failures.

## SECTION 2.1: CLUSTER ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KAFKA CLUSTER OVERVIEW                                                 |
|                                                                         |
|  +-------------------------------+                                      |
|  |      Controller (KRaft)       |  Metadata management                 |
|  |  (or ZooKeeper in older ver)  |  Leader election                     |
|  +-------------------------------+  Config storage                      |
|       |           |          |                                          |
|       v           v          v                                          |
|  +---------+ +---------+ +---------+                                    |
|  | Broker 0| | Broker 1| | Broker 2|                                    |
|  |         | |         | |         |                                    |
|  | Part-0  | | Part-1  | | Part-2  |  <-- Leaders                       |
|  | Part-1* | | Part-2* | | Part-0* |  <-- Followers (replicas)          |
|  | Part-2* | | Part-0* | | Part-1* |  <-- Followers (replicas)          |
|  +---------+ +---------+ +---------+                                    |
|       ^           ^          ^                                          |
|       |           |          |                                          |
|  Producers write to leaders only                                        |
|  Consumers read from leaders (or followers in 2.4+)                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.2: ZOOKEEPER vs KRAFT

```
+--------------------------------------------------------------------------+
|                                                                          |
|  ZOOKEEPER MODE (Legacy, before Kafka 3.3)                               |
|                                                                          |
|  +------------+     +------------------------------------------+         |
|  | ZooKeeper  | <-> |          Kafka Brokers                   |         |
|  | Ensemble   |     |                                          |         |
|  | (3-5 nodes)|     | Broker 0 | Broker 1 | Broker 2           |         |
|  +------------+     +------------------------------------------+         |
|                                                                          |
|  ZooKeeper responsibilities:                                             |
|  * Broker registration and liveness                                      |
|  * Controller election                                                   |
|  * Topic/partition metadata                                              |
|  * ACLs and quotas                                                       |
|                                                                          |
|  Problems: extra cluster to manage, scaling bottleneck,                  |
|  split-brain risk, slower metadata operations.                           |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  KRAFT MODE (Kafka 3.3+, production ready in 3.6+)                       |
|                                                                          |
|  +------------------------------------------+                            |
|  |          Kafka Cluster (self-managed)     |                           |
|  |                                          |                            |
|  | Controller 0 | Controller 1 | Controller 2|  <-- Raft quorum          |
|  | Broker 0     | Broker 1     | Broker 2    |                           |
|  +------------------------------------------+                            |
|                                                                          |
|  * No external dependency (no ZooKeeper)                                 |
|  * Metadata stored in an internal Kafka topic (__cluster_metadata)       |
|  * Faster controller failover (seconds vs minutes)                       |
|  * Can support millions of partitions (vs ~200K with ZK)                 |
|  * Simplified deployment and operations                                  |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 2.3: TOPIC PARTITIONING STRATEGIES

```
+--------------------------------------------------------------------------+
|                                                                          |
|  PARTITIONING STRATEGIES                                                 |
|                                                                          |
|  1. ROUND-ROBIN (default when no key)                                    |
|     ----------------------------------                                   |
|     Messages distributed evenly across partitions.                       |
|     Best for: maximum throughput, no ordering needed.                    |
|                                                                          |
|     msg1 -> P0, msg2 -> P1, msg3 -> P2, msg4 -> P0, ...                  |
|                                                                          |
|  2. KEY-BASED (default when key is set)                                  |
|     ----------------------------------------                             |
|     hash(key) % num_partitions -> target partition                       |
|     Same key ALWAYS goes to same partition.                              |
|     Best for: ordering per entity (user, order, device).                 |
|                                                                          |
|     key="user-A" -> always P1                                            |
|     key="user-B" -> always P0                                            |
|     key="user-C" -> always P2                                            |
|                                                                          |
|  3. CUSTOM PARTITIONER                                                   |
|     -----------------------                                              |
|     Implement Partitioner interface for special logic.                   |
|     Example: route VIP customers to a dedicated partition.               |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  HOW MANY PARTITIONS?                                                    |
|                                                                          |
|  Rule of thumb:                                                          |
|  * Target throughput / throughput-per-partition                          |
|  * If target = 1 GB/sec and each partition handles 10 MB/sec             |
|    then you need ~100 partitions                                         |
|  * More partitions = more parallelism but more overhead                  |
|  * Start with: max(expected consumers, target_MB / 10)                   |
|  * Typical: 6-30 partitions per topic                                    |
|                                                                          |
|  WARNING: You can ADD partitions but CANNOT reduce them.                 |
|  Adding partitions breaks key-based ordering for existing keys.          |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 2.4: REPLICATION

```
+--------------------------------------------------------------------------+
|                                                                          |
|  REPLICATION MODEL                                                       |
|                                                                          |
|  Every partition has:                                                    |
|  * 1 LEADER replica   -- handles all reads and writes                    |
|  * N FOLLOWER replicas -- passively replicate the leader                 |
|                                                                          |
|  replication-factor = 3 means 1 leader + 2 followers                     |
|                                                                          |
|  Topic "orders", Partition 0, replication-factor=3:                      |
|                                                                          |
|  +------------+    +------------+    +------------+                      |
|  |  Broker 0  |    |  Broker 1  |    |  Broker 2  |                      |
|  |            |    |            |    |            |                      |
|  |  P0 LEADER | -> |  P0 FOLLOW | -> |  P0 FOLLOW |                      |
|  |            |    |            |    |            |                      |
|  +------------+    +------------+    +------------+                      |
|                                                                          |
|  * Producer writes to Leader only                                        |
|  * Followers fetch data from leader continuously                         |
|  * If leader dies, a follower is promoted to new leader                  |
|                                                                          |
+--------------------------------------------------------------------------+
```

### IN-SYNC REPLICAS (ISR)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ISR = Set of replicas that are fully caught up with the leader         |
|                                                                         |
|  Leader offset:    [0] [1] [2] [3] [4] [5] [6] [7]                      |
|  Follower 1:       [0] [1] [2] [3] [4] [5] [6]       <-- in ISR         |
|  Follower 2:       [0] [1] [2] [3]                    <-- OUT of ISR    |
|                                                                         |
|  Follower 2 is lagging too far behind (> replica.lag.time.max.ms)       |
|  It is removed from ISR until it catches up.                            |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  WHY ISR MATTERS:                                                       |
|                                                                         |
|  * acks=all means "all replicas IN THE ISR must acknowledge"            |
|  * If ISR shrinks to just the leader, acks=all = acks=1                 |
|  * min.insync.replicas=2 prevents writes if ISR < 2                     |
|    (protects against data loss)                                         |
|                                                                         |
|  RECOMMENDED PRODUCTION SETTINGS:                                       |
|  * replication.factor = 3                                               |
|  * min.insync.replicas = 2                                              |
|  * acks = all                                                           |
|  --> Tolerates 1 broker failure without data loss or downtime           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.5: STORAGE INTERNALS

### COMMIT LOG

```
+--------------------------------------------------------------------------+
|                                                                          |
|  KAFKA STORES EVERYTHING AS AN APPEND-ONLY LOG                           |
|                                                                          |
|  Each partition = a directory on disk:                                   |
|                                                                          |
|  /kafka-data/orders-0/                                                   |
|    00000000000000000000.log      <-- segment file (actual messages)      |
|    00000000000000000000.index    <-- offset index                        |
|    00000000000000000000.timeindex<-- timestamp index                     |
|    00000000000005242880.log      <-- next segment                        |
|    00000000000005242880.index                                            |
|    ...                                                                   |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  LOG SEGMENTS:                                                           |
|  * Each segment holds messages up to segment.bytes (default 1GB)         |
|  * Only the ACTIVE segment is being written to                           |
|  * Old segments are immutable                                            |
|  * Segment filename = base offset of first message in it                 |
|                                                                          |
|  FINDING A MESSAGE BY OFFSET:                                            |
|  1. Binary search segment files to find correct segment                  |
|  2. Use .index file (sparse index) to find approximate position          |
|  3. Sequential scan from there to exact offset                           |
|                                                                          |
+--------------------------------------------------------------------------+
```

### RETENTION AND COMPACTION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TWO CLEANUP POLICIES:                                                  |
|                                                                         |
|  1. DELETE (default)                                                    |
|     ==================                                                  |
|     Delete segments older than retention.ms (default 7 days)            |
|     or when total size exceeds retention.bytes                          |
|                                                                         |
|     Time: [--segment1--][--segment2--][--segment3--][ACTIVE]            |
|            ^-- delete when age > 7 days                                 |
|                                                                         |
|  2. COMPACT                                                             |
|     ===========                                                         |
|     Keep only the LATEST value for each key.                            |
|     Used for changelogs, snapshots, config.                             |
|                                                                         |
|     Before compaction:                                                  |
|     [K1=A] [K2=B] [K1=C] [K3=D] [K2=E] [K1=F]                           |
|                                                                         |
|     After compaction:                                                   |
|     [K3=D] [K2=E] [K1=F]   <-- only latest per key                      |
|                                                                         |
|     * Tombstone: key with null value -> key will be removed             |
|     * Used by: __consumer_offsets, Kafka Streams state stores           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### ZERO-COPY OPTIMIZATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY KAFKA IS SO FAST: ZERO-COPY                                        |
|                                                                         |
|  TRADITIONAL APPROACH (4 copies, 4 context switches):                   |
|                                                                         |
|  Disk -> OS Cache -> App Buffer -> Socket Buffer -> NIC                 |
|    copy1      copy2         copy3          copy4                        |
|                                                                         |
|  KAFKA WITH ZERO-COPY (sendfile syscall):                               |
|                                                                         |
|  Disk -> OS Cache -------> NIC                                          |
|             (data never enters JVM heap)                                |
|                                                                         |
|  * 2-4x throughput improvement                                          |
|  * Minimal CPU usage for serving consumers                              |
|  * Works because Kafka stores data in the SAME format                   |
|    on disk and on the network (no serialization needed)                 |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  OTHER PERFORMANCE TECHNIQUES:                                          |
|  * Sequential disk I/O (append-only, no random writes)                  |
|  * OS page cache (Linux caches file data in RAM automatically)          |
|  * Batching (producer batches, consumer fetches in bulk)                |
|  * Compression (gzip, snappy, lz4, zstd at batch level)                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.6: CONTROLLER AND LEADER ELECTION

```
+--------------------------------------------------------------------------+
|                                                                          |
|  CONTROLLER BROKER                                                       |
|                                                                          |
|  One broker in the cluster is elected as the CONTROLLER.                 |
|                                                                          |
|  Controller responsibilities:                                            |
|  * Assign partition leaders to brokers                                   |
|  * Detect broker failures (via heartbeats)                               |
|  * Trigger leader re-election when a broker dies                         |
|  * Manage topic creation/deletion                                        |
|  * Replicate metadata to other brokers                                   |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  LEADER ELECTION WHEN A BROKER DIES:                                     |
|                                                                          |
|  1. Broker 1 dies (was leader of Partition 0)                            |
|  2. Controller detects failure (no heartbeat)                            |
|  3. Controller picks new leader from ISR of Partition 0                  |
|  4. Controller notifies all brokers of new leader                        |
|  5. Producers/consumers redirect to new leader                           |
|                                                                          |
|  Time: typically < 5 seconds with KRaft                                  |
|        (could be minutes with ZooKeeper under load)                      |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  UNCLEAN LEADER ELECTION:                                                |
|                                                                          |
|  unclean.leader.election.enable = false (default, recommended)           |
|  * If ALL ISR replicas are dead, partition goes OFFLINE                  |
|  * No data loss, but unavailable until ISR replica recovers              |
|                                                                          |
|  unclean.leader.election.enable = true                                   |
|  * Allow out-of-sync replica to become leader                            |
|  * Partition stays available but MAY LOSE DATA                           |
|  * Use only when availability > consistency                              |
|                                                                          |
+--------------------------------------------------------------------------+
```
