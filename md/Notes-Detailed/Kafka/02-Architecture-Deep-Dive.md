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

#### WHY ADDING PARTITIONS BREAKS KEY ORDERING

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Kafka routes keys using: partition = hash(key) % num_partitions         |
|                                                                          |
|  BEFORE (3 partitions):                                                  |
|    hash("user-A") % 3 = 0  -> Partition 0                                |
|    hash("user-B") % 3 = 1  -> Partition 1                                |
|    hash("user-C") % 3 = 2  -> Partition 2                                |
|                                                                          |
|  AFTER adding 1 partition (now 4):                                       |
|    hash("user-A") % 4 = 0  -> Partition 0   (same)                       |
|    hash("user-B") % 4 = 3  -> Partition 3   (MOVED! was P1)              |
|    hash("user-C") % 4 = 0  -> Partition 0   (MOVED! was P2)              |
|                                                                          |
|  user-B now has OLD messages in P1, NEW messages in P3.                  |
|  Ordering history is split. Consumer of P3 misses old messages.          |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  HOW TO HANDLE IT:                                                       |
|                                                                          |
|  1. OVER-PROVISION FROM THE START (Best practice)                        |
|     Start with more partitions than needed (30-100 per topic).           |
|     Unused partitions cost almost nothing.                               |
|     Avoids ever needing to repartition.                                  |
|                                                                          |
|  2. CREATE A NEW TOPIC (Clean migration)                                 |
|     Create "orders-v2" with more partitions.                             |
|     Produce to new topic, drain old topic, then switch consumers.        |
|     No split ordering. Requires coordination.                            |
|                                                                          |
|  3. ADD PARTITIONS IF NO KEY ORDERING NEEDED                             |
|     If using round-robin (no key), just add partitions.                  |
|     No harm — there was no key-based ordering to break.                  |
|                                                                          |
|  4. WAIT FOR RETENTION TO EXPIRE                                         |
|     Add partitions and accept brief split history.                       |
|     Once old messages expire (retention period), all keys are            |
|     consistently routed under the new partition count.                   |
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

### FULL REPLICATION EXAMPLE (4 Partitions, RF=3, 3 Brokers)

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Topic "orders": 4 partitions, replication.factor=3, across 3 brokers    |
|  Total replicas = 4 partitions x 3 copies = 12 replicas                  |
|                                                                          |
|  Kafka spreads leaders evenly using round-robin at creation time:        |
|                                                                          |
|  Broker 1                Broker 2                Broker 3                |
|  +------------------+    +------------------+    +------------------+    |
|  | P0 (LEADER)      |    | P0 (Follower)    |    | P0 (Follower)    |    |
|  | P1 (Follower)    |    | P1 (LEADER)      |    | P1 (Follower)    |    |
|  | P2 (Follower)    |    | P2 (Follower)    |    | P2 (LEADER)      |    |
|  | P3 (LEADER)      |    | P3 (Follower)    |    | P3 (Follower)    |    |
|  +------------------+    +------------------+    +------------------+    |
|                                                                          |
|  Leaders per broker: B1=2, B2=1, B3=1 (balanced)                         |
|  Every broker stores ALL 4 partitions (as leader or follower)            |
|  Producers and consumers only talk to the LEADER of each partition       |
|                                                                          |
+--------------------------------------------------------------------------+
```

### WHAT HAPPENS WHEN A BROKER DIES

```
+--------------------------------------------------------------------------+
|                                                                          |
|  SCENARIO: Broker 2 goes down                                            |
|                                                                          |
|  Broker 1                Broker 2 (DOWN)       Broker 3                  |
|  +------------------+    +------------------+  +------------------+      |
|  | P0 (LEADER)      |    |       X          |  | P0 (Follower)    |      |
|  | P1 (NEW LEADER)<-|    |       X          |  | P1 (Follower)    |      |
|  | P2 (Follower)    |    |       X          |  | P2 (LEADER)      |      |
|  | P3 (LEADER)      |    |       X          |  | P3 (Follower)    |      |
|  +------------------+    +------------------+  +------------------+      |
|                                                                          |
|  P1 lost its leader (was on Broker 2).                                   |
|  Controller picks a NEW leader from P1's ISR.                            |
|  Broker 1's copy of P1 was in-sync -> promoted to leader.                |
|                                                                          |
|  Now: B1 has 3 leaders, B3 has 1 leader -> UNBALANCED                    |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  AFTER BROKER 2 RECOVERS:                                                |
|                                                                          |
|  * Broker 2 rejoins the cluster                                          |
|  * Its replicas catch up by fetching missed data from leaders            |
|  * Once caught up, replicas rejoin the ISR                               |
|  * BUT P1's leader STAYS on Broker 1 (leaders don't auto-move back)      |
|                                                                          |
|  To rebalance, run PREFERRED LEADER ELECTION:                            |
|                                                                          |
|  kafka-leader-election.sh \                                              |
|      --election-type preferred \                                         |
|      --all-topic-partitions                                              |
|                                                                          |
|  "Preferred leader" = the broker that was ORIGINALLY assigned as         |
|  leader when the topic was created. This restores even distribution.     |
|                                                                          |
|  Or enable auto rebalancing:                                             |
|  auto.leader.rebalance.enable=true (checks every 5 min by default)       |
|                                                                          |
+--------------------------------------------------------------------------+
```

### LEADER ELECTION RULES

```
+---------------------------------------------------------------------------+
|                                                                           |
|  WHO CAN BECOME LEADER?                                                   |
|                                                                           |
|  +--------------------------------------------------------------------+   |
|  | Setting                          | Behavior                        |   |
|  |----------------------------------|---------------------------------|   |
|  | unclean.leader.election = false  | Only ISR members can become     |   |
|  | (DEFAULT, recommended)           | leader. If no ISR -> partition  |   |
|  |                                  | goes OFFLINE. Safe, no loss.    |   |
|  |----------------------------------|---------------------------------|   |
|  | unclean.leader.election = true   | Out-of-sync replica CAN become  |   |
|  |                                  | leader. Partition stays online  |   |
|  |                                  | but RISKS DATA LOSS (missing    |   |
|  |                                  | messages the old leader had).   |   |
|  +--------------------------------------------------------------------+   |
|                                                                           |
|  ELECTION FLOW:                                                           |
|                                                                           |
|  1. Controller detects broker failure (via heartbeat timeout)             |
|  2. For each partition that lost its leader on that broker:               |
|     a. Get the ISR list for that partition                                |
|     b. Pick the first replica in ISR as new leader                        |
|     c. If ISR is empty and unclean=false -> partition offline             |
|     d. If ISR is empty and unclean=true -> pick any alive replica         |
|  3. Controller writes new leader info to metadata                         |
|  4. Notifies all brokers of the new leader assignments                    |
|  5. Producers/consumers discover new leader via metadata refresh          |
|                                                                           |
|  TIME: Leader election takes milliseconds to low seconds.                 |
|  Producers see a brief "leader not available" error and retry.            |
|                                                                           |
+---------------------------------------------------------------------------+
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

### WHY KAFKA IS SO FAST

```
+--------------------------------------------------------------------------+
|                                                                          |
|  8 architectural decisions that make Kafka handle millions of msg/sec:   |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  1. SEQUENTIAL I/O (Append-only log)                                     |
|     Writes go to the end of a file, never random seeks.                  |
|     Sequential disk: ~600 MB/s vs random disk: ~100 KB/s.                |
|                                                                          |
|  2. ZERO-COPY TRANSFER (sendfile syscall)                                |
|     Data goes from disk to network without entering JVM heap.            |
|                                                                          |
|     Traditional: Disk -> Kernel -> App -> Kernel -> NIC (4 copies)       |
|     Zero-copy:   Disk -> Kernel -----------------> NIC (2 copies)        |
|                                                                          |
|     Works because Kafka stores data in the SAME format on disk           |
|     and on the wire — no serialization/deserialization needed.           |
|                                                                          |
|  3. OS PAGE CACHE (No application-level cache)                           |
|     Kafka delegates caching to the OS — recently written data            |
|     stays in RAM automatically. No GC overhead from in-process cache.    |
|     Consumers reading recent data (most common) read from RAM.           |
|                                                                          |
|  4. BATCHING EVERYWHERE                                                  |
|     Producer batches messages before sending (linger.ms + batch.size).   |
|     Broker writes entire batches in one disk I/O.                        |
|     Consumer fetches batches (fetch.min.bytes). Fewer round trips.       |
|                                                                          |
|  5. COMPRESSION AT BATCH LEVEL                                           |
|     Batches compressed together (gzip, snappy, lz4, zstd).               |
|     Better ratio than per-message. Less network, less disk.              |
|                                                                          |
|  6. PARTITIONING = PARALLELISM                                           |
|     Each partition is independently read/written.                        |
|     30 partitions = 30 parallel consumers = 30x throughput.              |
|     No global ordering lock between partitions.                          |
|                                                                          |
|  7. NO PER-MESSAGE ACKNOWLEDGMENT TRACKING                               |
|     Traditional queues track ack per message (expensive at scale).       |
|     Kafka stores one offset integer per consumer group per partition.    |
|     Consumer says "I'm at offset 5000" — no per-message bookkeeping.     |
|                                                                          |
|  8. IMMUTABLE SEGMENT FILES                                              |
|     Log split into ~1 GB segment files.                                  |
|     Old segments are immutable — no locking needed for concurrent        |
|     reads. Index files use memory-mapped I/O for fast lookups.           |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  THE COMBINATION:                                                        |
|                                                                          |
|  Producer batches 1000 msgs                                              |
|       -> compressed                                                      |
|       -> 1 network call to broker                                        |
|       -> broker does 1 sequential write to disk                          |
|       -> consumer reads batch via zero-copy from page cache              |
|       -> 1 network call back with 1000 msgs                              |
|                                                                          |
+--------------------------------------------------------------------------+
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
