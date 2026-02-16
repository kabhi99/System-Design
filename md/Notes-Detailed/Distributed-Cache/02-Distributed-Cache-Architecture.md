# DISTRIBUTED CACHE SYSTEM DESIGN
*Chapter 2: Distributed Cache Architecture*

When a single cache server isn't enough, we need distributed caching.
This chapter covers how to distribute cache across multiple nodes while
maintaining performance and consistency.

## SECTION 2.1: WHY DISTRIBUTED CACHE?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SINGLE NODE LIMITATIONS                                               |
|                                                                         |
|  1. MEMORY LIMIT                                                       |
|     * Single server: 64-256 GB RAM typical                           |
|     * Need to cache 1 TB? Can't fit on one server                   |
|                                                                         |
|  2. THROUGHPUT LIMIT                                                   |
|     * Single Redis: ~100,000 ops/sec                                 |
|     * Need 1M ops/sec? Need more servers                            |
|                                                                         |
|  3. SINGLE POINT OF FAILURE                                            |
|     * Server crashes = all cached data lost                          |
|     * Thundering herd to database                                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  DISTRIBUTED CACHE BENEFITS                                            |
|                                                                         |
|  1. HORIZONTAL SCALING                                                 |
|     * Add more nodes for more capacity                               |
|     * 10 nodes x 64GB = 640GB total cache                           |
|                                                                         |
|  2. HIGH AVAILABILITY                                                  |
|     * Replicas survive node failures                                 |
|     * No single point of failure                                     |
|                                                                         |
|  3. GEOGRAPHIC DISTRIBUTION                                            |
|     * Cache in multiple regions                                      |
|     * Lower latency for global users                                 |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  SINGLE CACHE              DISTRIBUTED CACHE                   |  |
|  |                                                                 |  |
|  |  +-----------+             +------+ +------+ +------+         |  |
|  |  |           |             |Node 1| |Node 2| |Node 3|         |  |
|  |  |  Single   |             | 64GB | | 64GB | | 64GB |         |  |
|  |  |   Node    |      >      +------+ +------+ +------+         |  |
|  |  |  64 GB    |             +------+ +------+ +------+         |  |
|  |  |           |             |Node 4| |Node 5| |Node 6|         |  |
|  |  +-----------+             | 64GB | | 64GB | | 64GB |         |  |
|  |                            +------+ +------+ +------+         |  |
|  |  Capacity: 64GB            Capacity: 384GB                    |  |
|  |  Throughput: 100K/s        Throughput: 600K/s                |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.2: DATA DISTRIBUTION - CONSISTENT HASHING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE DISTRIBUTION PROBLEM                                             |
|                                                                         |
|  Given a key, which node stores it?                                   |
|                                                                         |
|  NAIVE APPROACH: MODULO HASHING                                       |
|  ================================                                       |
|                                                                         |
|  node_index = hash(key) % num_nodes                                   |
|                                                                         |
|  With 4 nodes:                                                         |
|  hash("user:1") % 4 = 2  > Node 2                                    |
|  hash("user:2") % 4 = 0  > Node 0                                    |
|  hash("user:3") % 4 = 1  > Node 1                                    |
|                                                                         |
|  PROBLEM: ADDING/REMOVING NODES                                       |
|  -----------------------------                                          |
|                                                                         |
|  Add a 5th node:                                                       |
|  hash("user:1") % 5 = 1  > Node 1 (was Node 2!)                      |
|  hash("user:2") % 5 = 3  > Node 3 (was Node 0!)                      |
|  hash("user:3") % 5 = 4  > Node 4 (was Node 1!)                      |
|                                                                         |
|  Almost ALL keys move to different nodes!                            |
|  Massive cache invalidation.                                        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CONSISTENT HASHING                                                    |
|  ===================                                                    |
|                                                                         |
|  Imagine a circular ring (0 to 2^32-1)                                |
|  Both nodes AND keys are hashed onto this ring.                      |
|  Each key belongs to the first node clockwise from it.               |
|                                                                         |
|                        0                                               |
|                        |                                               |
|              +---------+---------+                                     |
|              |                   |                                     |
|       Node A o        o Key 1   |                                     |
|              |                   |                                     |
|    ----------+-------------------+----------                          |
|              |                   |                                     |
|       Key 3 o         Node B o  |                                     |
|              |                   |                                     |
|              +---------+---------+                                     |
|                        |                                               |
|                o Key 2 | o Node C                                     |
|                        |                                               |
|                                                                         |
|  Key 1 > Node B (first node clockwise)                               |
|  Key 2 > Node C                                                       |
|  Key 3 > Node A                                                       |
|                                                                         |
|  ADD A NODE (D between A and B):                                      |
|  ---------------------------------                                      |
|  Only keys between A and D move to D.                                |
|  Other keys stay where they are!                                     |
|  Only ~1/N keys move (N = number of nodes).                          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  VIRTUAL NODES                                                         |
|  =============                                                          |
|                                                                         |
|  Problem: Uneven distribution with few nodes.                        |
|                                                                         |
|  Solution: Each physical node gets multiple positions on ring.       |
|                                                                         |
|  Node A > A-1, A-2, A-3, A-4 (4 virtual nodes)                       |
|  Node B > B-1, B-2, B-3, B-4                                         |
|                                                                         |
|  More virtual nodes = more even distribution.                        |
|  Typical: 100-200 virtual nodes per physical node.                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  IMPLEMENTATION                                                        |
|                                                                         |
|  class ConsistentHash:                                                 |
|      def __init__(self, nodes, virtual_nodes=150):                   |
|          self.ring = SortedDict()                                     |
|          self.virtual_nodes = virtual_nodes                           |
|                                                                         |
|          for node in nodes:                                            |
|              self.add_node(node)                                       |
|                                                                         |
|      def add_node(self, node):                                        |
|          for i in range(self.virtual_nodes):                         |
|              key = hash(f"{node}:{i}")                               |
|              self.ring[key] = node                                    |
|                                                                         |
|      def remove_node(self, node):                                     |
|          for i in range(self.virtual_nodes):                         |
|              key = hash(f"{node}:{i}")                               |
|              del self.ring[key]                                       |
|                                                                         |
|      def get_node(self, key):                                         |
|          if not self.ring:                                            |
|              return None                                               |
|          hash_key = hash(key)                                         |
|          # Find first node clockwise                                  |
|          idx = self.ring.bisect_right(hash_key)                      |
|          if idx == len(self.ring):                                   |
|              idx = 0  # Wrap around                                   |
|          return self.ring.peekitem(idx)[1]                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.3: REPLICATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY REPLICATION?                                                      |
|                                                                         |
|  Node fails > data lost > cache miss spike > database overload       |
|                                                                         |
|  With replication: Node fails > replica takes over > no data lost   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  REPLICATION STRATEGIES                                                |
|                                                                         |
|  1. LEADER-FOLLOWER (Master-Slave)                                     |
|  =================================                                      |
|                                                                         |
|  * One leader (master) handles writes                                |
|  * Followers (replicas) receive copies                               |
|  * Reads can go to any node                                          |
|                                                                         |
|       Client                                                           |
|          |                                                             |
|          | Write                                                       |
|          v                                                             |
|     +---------+                                                        |
|     | Leader  |----> Replicate ----> +----------+                     |
|     | (Write) |                       | Follower |                     |
|     +---------+----> Replicate ----> |  (Read)  |                     |
|                                       +----------+                     |
|                 ----> Replicate ----> +----------+                     |
|                                       | Follower |                     |
|                                       |  (Read)  |                     |
|                                       +----------+                     |
|                                                                         |
|  SYNC vs ASYNC REPLICATION:                                           |
|  ----------------------------                                           |
|  Sync: Leader waits for follower ack before confirming write        |
|        Pros: Strong consistency                                       |
|        Cons: Higher latency, leader blocked if follower slow        |
|                                                                         |
|  Async: Leader confirms immediately, replicates in background        |
|         Pros: Fast writes                                             |
|         Cons: Data loss possible if leader fails before replicate   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  2. LEADERLESS REPLICATION                                             |
|  ==========================                                            |
|                                                                         |
|  No single leader. Write to multiple nodes.                          |
|  Read from multiple nodes, use quorum.                               |
|                                                                         |
|  QUORUM: W + R > N                                                    |
|  * N = total replicas                                                |
|  * W = write quorum (nodes that must ack write)                     |
|  * R = read quorum (nodes to read from)                             |
|                                                                         |
|  Example: N=3, W=2, R=2                                               |
|  Write succeeds when 2 nodes ack.                                    |
|  Read from 2 nodes, at least 1 has latest.                          |
|                                                                         |
|  Used by: Cassandra, DynamoDB                                        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  REDIS REPLICATION                                                     |
|  =================                                                      |
|                                                                         |
|  Redis uses async leader-follower by default.                        |
|                                                                         |
|  # On replica                                                          |
|  REPLICAOF leader_ip leader_port                                      |
|                                                                         |
|  Replication lag: Typically <1ms, but can be seconds under load.    |
|  WAIT command for sync replication if needed.                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.4: REDIS CLUSTER

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REDIS CLUSTER                                                         |
|                                                                         |
|  Built-in sharding for Redis.                                        |
|  Automatic data distribution and failover.                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  HASH SLOTS                                                            |
|  ==========                                                            |
|                                                                         |
|  Redis Cluster uses 16,384 hash slots.                               |
|  Each key hashes to a slot: CRC16(key) % 16384                       |
|  Slots distributed across nodes.                                      |
|                                                                         |
|  With 3 nodes:                                                         |
|  * Node A: slots 0-5460                                              |
|  * Node B: slots 5461-10922                                          |
|  * Node C: slots 10923-16383                                         |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |   Node A              Node B              Node C               |  |
|  |  +--------+          +--------+          +--------+            |  |
|  |  | Slots  |          | Slots  |          | Slots  |            |  |
|  |  | 0-5460 |          |5461-   |          |10923-  |            |  |
|  |  |        |          |10922   |          |16383   |            |  |
|  |  +----+---+          +----+---+          +----+---+            |  |
|  |       |                   |                   |                |  |
|  |       v                   v                   v                |  |
|  |  +--------+          +--------+          +--------+            |  |
|  |  |Replica |          |Replica |          |Replica |            |  |
|  |  |  A1    |          |  B1    |          |  C1    |            |  |
|  |  +--------+          +--------+          +--------+            |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CLIENT ROUTING                                                        |
|  ==============                                                        |
|                                                                         |
|  Client sends command to any node.                                   |
|  If key is on that node: execute and return.                        |
|  If key is on different node: return MOVED redirect.                |
|                                                                         |
|  GET user:123                                                          |
|  > MOVED 12345 192.168.1.3:6379                                      |
|  (Key is in slot 12345, on node 192.168.1.3)                        |
|                                                                         |
|  Smart clients cache slot>node mapping to avoid redirects.          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  FAILOVER                                                              |
|  ========                                                              |
|                                                                         |
|  1. Nodes ping each other constantly                                 |
|  2. If master doesn't respond, followers vote                       |
|  3. Elected follower promoted to master                             |
|  4. Cluster updates slot mapping                                    |
|                                                                         |
|  Automatic failover: ~1-2 seconds.                                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  MULTI-KEY OPERATIONS                                                  |
|  =====================                                                  |
|                                                                         |
|  MGET key1 key2 key3                                                  |
|                                                                         |
|  Only works if all keys are on same node.                           |
|  Use hash tags to force co-location:                                 |
|                                                                         |
|  user:{123}:profile                                                    |
|  user:{123}:settings                                                   |
|  user:{123}:friends                                                    |
|                                                                         |
|  The part in {} is used for hashing.                                 |
|  All keys with {123} go to same slot.                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.5: REDIS SENTINEL (High Availability)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REDIS SENTINEL                                                        |
|                                                                         |
|  Provides high availability without full clustering.                 |
|  Good for smaller setups that need failover.                         |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |           +----------+  +----------+  +----------+             |  |
|  |           |Sentinel 1|  |Sentinel 2|  |Sentinel 3|             |  |
|  |           |  (S1)    |  |  (S2)    |  |  (S3)    |             |  |
|  |           +----+-----+  +----+-----+  +----+-----+             |  |
|  |                |             |             |                    |  |
|  |                +-------------+-------------+                    |  |
|  |                       Monitor|                                  |  |
|  |                              |                                  |  |
|  |                              v                                  |  |
|  |                        +----------+                             |  |
|  |                        |  Master  |                             |  |
|  |                        |  (M)     |                             |  |
|  |                        +----+-----+                             |  |
|  |                             | Replication                       |  |
|  |                    +--------+--------+                          |  |
|  |                    v                 v                          |  |
|  |               +----------+      +----------+                    |  |
|  |               | Replica 1|      | Replica 2|                    |  |
|  |               |  (R1)    |      |  (R2)    |                    |  |
|  |               +----------+      +----------+                    |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  SENTINEL RESPONSIBILITIES:                                           |
|  ===========================                                           |
|                                                                         |
|  1. MONITORING                                                         |
|     * Sentinels ping master and replicas                            |
|     * Detect failures                                                |
|                                                                         |
|  2. NOTIFICATION                                                       |
|     * Alert administrators                                           |
|     * Publish events via Pub/Sub                                    |
|                                                                         |
|  3. AUTOMATIC FAILOVER                                                 |
|     * If master fails, promote replica                              |
|     * Update configuration                                           |
|     * Notify clients of new master                                  |
|                                                                         |
|  4. CONFIGURATION PROVIDER                                             |
|     * Clients ask Sentinel for current master                       |
|     * No hardcoded master address in clients                        |
|                                                                         |
|  FAILOVER PROCESS:                                                     |
|  ==================                                                     |
|                                                                         |
|  1. Master stops responding to pings                                 |
|  2. After timeout, sentinel marks it as SDOWN (subjectively down)   |
|  3. If quorum sentinels agree, master is ODOWN (objectively down)  |
|  4. Sentinels vote for a leader to perform failover                 |
|  5. Leader promotes best replica to master                          |
|  6. Other replicas reconfigured to follow new master               |
|                                                                         |
|  CLIENT CONNECTION:                                                    |
|  ===================                                                    |
|                                                                         |
|  # Python example with redis-py                                       |
|  from redis.sentinel import Sentinel                                  |
|                                                                         |
|  sentinel = Sentinel([                                                 |
|      ('sentinel1.example.com', 26379),                               |
|      ('sentinel2.example.com', 26379),                               |
|      ('sentinel3.example.com', 26379)                                |
|  ])                                                                    |
|                                                                         |
|  # Get current master                                                 |
|  master = sentinel.master_for('mymaster')                            |
|  master.set('key', 'value')                                          |
|                                                                         |
|  # Get replica for reads                                              |
|  replica = sentinel.slave_for('mymaster')                            |
|  value = replica.get('key')                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.6: CLUSTER vs SENTINEL COMPARISON

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHEN TO USE WHICH?                                                    |
|                                                                         |
|  +--------------------+--------------------------------------------+  |
|  |                    |  Redis Sentinel    |  Redis Cluster       |  |
|  +--------------------+--------------------+----------------------+  |
|  | Sharding           |  No (single data   |  Yes (automatic)     |  |
|  |                    |  set)              |                      |  |
|  +--------------------+--------------------+----------------------+  |
|  | Max data size      |  Single node limit |  Unlimited (add      |  |
|  |                    |  (256GB typ.)      |  more nodes)         |  |
|  +--------------------+--------------------+----------------------+  |
|  | High availability  |  Yes (failover)    |  Yes (built-in)      |  |
|  +--------------------+--------------------+----------------------+  |
|  | Multi-key ops      |  Yes (all keys     |  Only with hash tags |  |
|  |                    |  on same node)     |                      |  |
|  +--------------------+--------------------+----------------------+  |
|  | Complexity         |  Lower             |  Higher              |  |
|  +--------------------+--------------------+----------------------+  |
|  | Use case           |  <100GB cache,     |  >100GB cache,       |  |
|  |                    |  simpler ops       |  high throughput     |  |
|  +--------------------+--------------------+----------------------+  |
|                                                                         |
|  RECOMMENDATION:                                                       |
|  ----------------                                                       |
|  * Start with Sentinel (simpler)                                     |
|  * Move to Cluster when:                                             |
|    - Data exceeds single node capacity                               |
|    - Need more than 100K ops/sec                                     |
|    - Can work around multi-key limitations                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DISTRIBUTED CACHE - KEY TAKEAWAYS                                    |
|                                                                         |
|  DATA DISTRIBUTION                                                     |
|  -----------------                                                      |
|  * Modulo hashing: Simple but bad for scaling                        |
|  * Consistent hashing: Only ~1/N keys move on changes               |
|  * Virtual nodes: Even distribution                                  |
|                                                                         |
|  REPLICATION                                                           |
|  -----------                                                           |
|  * Leader-follower: Simple, Redis default                           |
|  * Async: Fast but potential data loss                              |
|  * Sync: Consistent but slower                                       |
|                                                                         |
|  REDIS DEPLOYMENT                                                      |
|  ----------------                                                       |
|  * Sentinel: HA without sharding                                     |
|  * Cluster: HA with auto-sharding                                   |
|  * Hash slots (16384) for distribution                              |
|                                                                         |
|  INTERVIEW TIP                                                         |
|  -------------                                                         |
|  Explain consistent hashing with virtual nodes.                      |
|  Know Redis Cluster vs Sentinel trade-offs.                          |
|  Discuss replication lag implications.                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 2

