# CHAPTER 2: CAP THEOREM & CONSISTENCY MODELS
*Understanding Trade-offs in Distributed Systems*

The CAP Theorem is the most fundamental concept in distributed systems.
Understanding it helps you make informed design decisions and explain
trade-offs in interviews.

## SECTION 2.1: THE CAP THEOREM

### WHAT IS CAP?

The CAP Theorem states that in a distributed data store, you can only
guarantee TWO out of THREE properties:

```
+-------------------------------------------------------------------------+
|                                                                         |
|                         CAP THEOREM                                    |
|                                                                         |
|                           Consistency                                  |
|                               /\                                        |
|                              /  \                                       |
|                             /    \                                      |
|                            /      \                                     |
|                           /   CA   \                                    |
|                          / (single  \                                   |
|                         /   node)    \                                  |
|                        /              \                                 |
|                       /________________\                                |
|                      /\                /\                               |
|                     /  \              /  \                              |
|                    /    \            /    \                             |
|                   /  CP  \          /  AP  \                            |
|                  /        \        /        \                           |
|                 /__________\      /__________\                          |
|                                                                         |
|           Availability --------------- Partition Tolerance              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DEFINING C, A, AND P

```
+-------------------------------------------------------------------------+
|                                                                         |
|  C - CONSISTENCY (Linearizability)                                    |
|  =================================                                      |
|                                                                         |
|  Every read receives the most recent write or an error.               |
|  All nodes see the same data at the same time.                        |
|                                                                         |
|  After: write(x = 5)                                                  |
|  Any subsequent read from ANY node must return x = 5                  |
|                                                                         |
|  NOT about ACID consistency (that's a different concept!)             |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  A - AVAILABILITY                                                      |
|  =================                                                      |
|                                                                         |
|  Every request receives a (non-error) response, without              |
|  guarantee that it contains the most recent write.                    |
|                                                                         |
|  KEY: Response must be from a non-failing node                        |
|  The response might be stale, but you get a response                 |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  P - PARTITION TOLERANCE                                               |
|  ========================                                               |
|                                                                         |
|  System continues to operate despite network partitions               |
|  (messages being dropped or delayed between nodes).                   |
|                                                                         |
|  A partition means:                                                    |
|  * Node A can't talk to Node B                                       |
|  * Or messages arrive out of order                                   |
|  * Or messages are severely delayed                                  |
|                                                                         |
|  PARTITIONS ARE INEVITABLE IN DISTRIBUTED SYSTEMS!                   |
|  Network cables fail, switches die, datacenters disconnect           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHY CAN'T WE HAVE ALL THREE?

Network partitions WILL happen in distributed systems. When they do,
you must choose between Consistency and Availability.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCENARIO: NETWORK PARTITION                                           |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |              Network Partition (connection lost)               |  |
|  |                                                                 |  |
|  |     Client A                              Client B              |  |
|  |         |                                     |                 |  |
|  |         v                                     v                 |  |
|  |    +------------+         [ ] [ ] [ ] [ ]        +------------+       |  |
|  |    |  Node 1    |<---- Can't talk ---->  |  Node 2    |       |  |
|  |    | balance=100|                        | balance=100|       |  |
|  |    +------------+                        +------------+       |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  Client A: "Withdraw $50"                                             |
|  Client B: "Withdraw $50"                                             |
|                                                                         |
|  CHOICE 1: CHOOSE CONSISTENCY (CP)                                    |
|  ---------------------------------                                     |
|  Node 1 refuses to process request until it can verify with Node 2   |
|  "Sorry, service unavailable during partition"                        |
|  [x] Data is consistent                                                 |
|  [ ] System is unavailable                                              |
|                                                                         |
|  CHOICE 2: CHOOSE AVAILABILITY (AP)                                   |
|  --------------------------------                                      |
|  Both nodes process their requests independently                      |
|  Node 1: balance = 100 - 50 = 50                                      |
|  Node 2: balance = 100 - 50 = 50                                      |
|  After partition heals: balance = 50? (should be 0!)                  |
|  [x] System is available                                                |
|  [ ] Data is inconsistent                                               |
|                                                                         |
|  THERE IS NO THIRD OPTION DURING A PARTITION!                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CAP IN PRACTICE

Since network partitions are inevitable, the real choice is CP vs AP:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CP SYSTEMS (Consistency + Partition Tolerance)                       |
|  ===============================================                        |
|                                                                         |
|  During partition: Refuse some requests to maintain consistency       |
|                                                                         |
|  EXAMPLES:                                                             |
|  * MongoDB (with w:majority, j:true)                                 |
|  * HBase                                                              |
|  * Redis Cluster (in strict mode)                                    |
|  * Zookeeper                                                          |
|  * etcd                                                               |
|  * Google Spanner                                                     |
|                                                                         |
|  USE CASES:                                                            |
|  * Financial transactions                                            |
|  * Inventory systems (can't oversell)                                |
|  * Seat reservations                                                 |
|  * Leader election                                                   |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  AP SYSTEMS (Availability + Partition Tolerance)                      |
|  ================================================                       |
|                                                                         |
|  During partition: Serve possibly stale data                          |
|                                                                         |
|  EXAMPLES:                                                             |
|  * Cassandra                                                          |
|  * CouchDB                                                            |
|  * DynamoDB (default mode)                                           |
|  * Riak                                                               |
|  * DNS                                                                |
|                                                                         |
|  USE CASES:                                                            |
|  * Social media feeds                                                |
|  * Product catalogs                                                  |
|  * Shopping carts (can merge later)                                 |
|  * Analytics/metrics                                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.2: PACELC THEOREM (CAP EXTENDED)

CAP only describes behavior during partitions. PACELC extends this:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PACELC THEOREM                                                         |
|                                                                         |
|  "If there is a Partition, choose between Availability and              |
|   Consistency; Else (no partition), choose between Latency and          |
|   Consistency"                                                          |
|                                                                         |
|  +-----------------------------------------------------------------+    |
|  |                                                                 |    |
|  |              P A C E L C                                        |    |
|  |              | | | | | |                                        |    |
|  |              | | | | | +-- Consistency (normal operation)       |  |
|  |              | | | | +---- Latency                              |  |
|  |              | | | +------ Else (no partition)                  |  |
|  |              | | +-------- Consistency (during partition)     |  |
|  |              | +---------- Availability                       |  |
|  |              +------------ Partition                          |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  CLASSIFICATIONS:                                                      |
|                                                                         |
|  PA/EL - Prioritize availability and latency (sacrifice consistency) |
|  * Cassandra (default settings)                                       |
|  * DynamoDB                                                           |
|  * Riak                                                               |
|                                                                         |
|  PC/EC - Prioritize consistency always (sacrifice latency)           |
|  * RDBMS (single node)                                                |
|  * HBase                                                              |
|  * Google Spanner                                                     |
|                                                                         |
|  PA/EC - Available during partition, but consistent in normal ops    |
|  * MongoDB                                                            |
|  * PostgreSQL (with sync replication)                                |
|                                                                         |
|  PC/EL - Consistent during partition, but lower latency normally     |
|  * PNUTS (Yahoo)                                                      |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  WHY PACELC MATTERS:                                                   |
|                                                                         |
|  CAP only talks about partition scenarios                             |
|  But partitions are rare! Most of the time, there's no partition.    |
|                                                                         |
|  PACELC captures the everyday trade-off:                              |
|  "Even without partitions, synchronous replication adds latency"     |
|                                                                         |
|  EXAMPLE: Synchronous vs Asynchronous Replication                    |
|                                                                         |
|  Synchronous (EC):                                                    |
|  Client -> Write -> Primary -> Wait for replica ACK -> Return            |
|  Latency: 50ms + 20ms replication = 70ms                             |
|  [x] Strong consistency                                                 |
|                                                                         |
|  Asynchronous (EL):                                                   |
|  Client -> Write -> Primary -> Return (replica updated later)          |
|  Latency: 50ms                                                        |
|  [x] Lower latency, [ ] eventual consistency                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.3: CONSISTENCY MODELS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  STRONGEST <------------------------------------------> WEAKEST       |
|  Linearizable -> Sequential -> Causal -> Eventual                        |
|  (Slower, costly)                        (Faster, cheap)              |
|                                                                         |
|  ====================================================================  |
|                                                                         |
|  1. LINEARIZABLE (Strong Consistency)                                  |
|  -------------------------------------                                  |
|  * Once write completes, ALL subsequent reads see it (real-time order)|
|  * Every op appears atomic between its invocation and completion      |
|  * How: Single leader + sync replication, consensus (Paxos/Raft)     |
|  * Cost: High latency, lower availability, no easy geo-distribution  |
|  * Use: Bank balances, seat reservations, distributed locks          |
|  * DBs: Spanner, CockroachDB, etcd, Zookeeper                       |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. SEQUENTIAL                                                         |
|  --------------                                                         |
|  * All processes see ops in SAME order, but not necessarily           |
|    matching real-time (wall clock) order                              |
|  * Key diff from linearizable: total order required, NOT real-time   |
|  * Example: CPU memory reordering in multiprocessor systems          |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. CAUSAL                                                              |
|  ---------                                                              |
|  * Cause-effect order preserved; concurrent ops can be in any order  |
|  * Causally related = same client ops, read-then-write, transitive   |
|  * Example: Post "I love pizza!" -> Comment "Me too!"                 |
|    Everyone MUST see post before comment                              |
|    But unrelated Post 2 can appear in any position                   |
|  * How: Vector clocks / version vectors                              |
|  * Use: Social feeds, chat, comments, collaborative editing          |
|  * DBs: MongoDB (causal sessions), CockroachDB                       |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  4. EVENTUAL                                                            |
|  ------------                                                           |
|  * If no new updates, all replicas converge to same value eventually |
|  * During replication window: reads from different nodes may differ   |
|  * Lag: usually ms–seconds, can be minutes under load                |
|  * Use: Likes/views, reviews, analytics, DNS, email                  |
|  * DBs: Cassandra, DynamoDB, S3, DNS                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.4: ACID vs BASE

Two philosophies for database transactions:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ACID vs BASE                                                          |
|                                                                         |
|  +---------------------------+    +-------------------------------+   |
|  |           ACID            |    |            BASE               |   |
|  |   (Traditional RDBMS)     |    |      (NoSQL/Distributed)      |   |
|  |                           |    |                               |   |
|  | A - Atomicity            |    | BA - Basically Available     |   |
|  |     All or nothing        |    |      System works most of    |   |
|  |     Transaction succeeds  |    |      the time, even if      |   |
|  |     completely or fails   |    |      some nodes fail        |   |
|  |     completely            |    |                               |   |
|  |                           |    | S - Soft state              |   |
|  | C - Consistency          |    |     State may change over   |   |
|  |     Database moves from   |    |     time without input      |   |
|  |     one valid state to    |    |     (due to async replication)|  |
|  |     another               |    |                               |   |
|  |                           |    | E - Eventually consistent   |   |
|  | I - Isolation            |    |     System becomes          |   |
|  |     Concurrent txns don't |    |     consistent eventually   |   |
|  |     interfere             |    |                               |   |
|  |                           |    |                               |   |
|  | D - Durability           |    |                               |   |
|  |     Committed data        |    |                               |   |
|  |     survives crashes      |    |                               |   |
|  |                           |    |                               |   |
|  +---------------------------+    +-------------------------------+   |
|                                                                         |
|  ACID: Strong guarantees, harder to scale                             |
|  BASE: Weaker guarantees, easier to scale                             |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  WHEN TO USE ACID:                                                     |
|  * Financial transactions (bank transfers)                           |
|  * Inventory management (can't oversell)                             |
|  * User authentication and authorization                             |
|  * Booking/reservation systems                                       |
|  * Any data that MUST be accurate                                    |
|                                                                         |
|  WHEN TO USE BASE:                                                     |
|  * Social media feeds (showing slightly old posts is OK)            |
|  * Analytics and metrics                                              |
|  * Session data                                                       |
|  * Caching                                                            |
|  * Shopping carts (can merge conflicts)                              |
|  * Logs and events                                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.5: PRACTICAL CONSISTENCY PATTERNS

### READ-AFTER-WRITE CONSISTENCY

A practical pattern that's often needed:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  READ-AFTER-WRITE (READ-YOUR-WRITES) CONSISTENCY                      |
|                                                                         |
|  GUARANTEE:                                                            |
|  A user can immediately read their own writes.                        |
|  (Other users may still see stale data)                               |
|                                                                         |
|  SCENARIO WITHOUT READ-AFTER-WRITE:                                   |
|  -------------------------------------                                  |
|  1. User updates profile picture                                      |
|  2. User refreshes page                                               |
|  3. Old picture still shown! (read from stale replica)               |
|  4. User thinks update failed, tries again and again...             |
|                                                                         |
|  IMPLEMENTATION STRATEGIES:                                           |
|                                                                         |
|  1. READ FROM LEADER AFTER WRITE                                      |
|  ---------------------------------                                      |
|  After user writes, direct their reads to leader for N seconds       |
|                                                                         |
|  write --> Leader                                                      |
|  read  --> Leader (for next 30 seconds)                               |
|  read  --> Any replica (after 30 seconds)                             |
|                                                                         |
|  Implementation: Cookie with "last_write_timestamp"                  |
|                                                                         |
|  2. TRACK REPLICATION LAG                                             |
|  ----------------------------                                           |
|  Only read from replicas that are caught up                           |
|                                                                         |
|  Client: "My last write was at timestamp T"                           |
|  Query replica: "What's your latest applied timestamp?"              |
|  If replica.timestamp >= T: safe to read                             |
|  Else: redirect to leader or wait                                     |
|                                                                         |
|  3. CLIENT-SIDE CACHING                                               |
|  ----------------------------                                           |
|  Cache writes on client, merge with server reads                      |
|                                                                         |
|  write --> Server (async)                                             |
|  write --> Local cache (immediate)                                    |
|  read  --> Merge(local cache, server response)                       |
|                                                                         |
|  4. LOGICAL TIMESTAMPS                                                 |
|  -----------------------                                                |
|  Include logical timestamp in response                                |
|  Client sends timestamp with next request                            |
|  Server ensures response is at least as recent                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### MONOTONIC READS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MONOTONIC READS                                                       |
|                                                                         |
|  GUARANTEE:                                                            |
|  A user will never see older data after seeing newer data.           |
|  Time doesn't move backward.                                          |
|                                                                         |
|  PROBLEM WITHOUT MONOTONIC READS:                                     |
|  ----------------------------------                                     |
|                                                                         |
|  Replica A (has data up to T+10):                                     |
|  +------------------------------------------------------+             |
|  | Comments: [Alice: "Hi", Bob: "Hello", Carol: "Hey"] |             |
|  +------------------------------------------------------+             |
|                                                                         |
|  Replica B (has data up to T+5, behind):                              |
|  +------------------------------------------------------+             |
|  | Comments: [Alice: "Hi", Bob: "Hello"]               |             |
|  +------------------------------------------------------+             |
|                                                                         |
|  User refreshes: sees 3 comments (from Replica A)                     |
|  User refreshes: sees 2 comments (from Replica B)                     |
|  "Where did Carol's comment go?!"                                     |
|                                                                         |
|  SOLUTION: STICKY REPLICA                                             |
|  ---------------------------                                            |
|  Route all reads from same user to same replica.                      |
|                                                                         |
|  Implementation:                                                       |
|  replica_index = hash(user_id) % num_replicas                        |
|                                                                         |
|  Or: Track "minimum acceptable timestamp" per user                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CONSISTENCY LEVELS (Tunable Consistency)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TUNABLE CONSISTENCY (Cassandra/DynamoDB style)                       |
|                                                                         |
|  N = Total replicas                                                    |
|  W = Write acknowledgment requirement                                  |
|  R = Read acknowledgment requirement                                   |
|                                                                         |
|  RULE: W + R > N -> Strong consistency                                 |
|        (At least one node overlaps between read and write)           |
|                                                                         |
|  EXAMPLE (N=3):                                                        |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |  Configuration    |  Consistency | Availability | Latency       | |
|  +-----------------------------------------------------------------+  |
|  |  W=1, R=1        |  Weak        | High         | Low           | |
|  |  W=2, R=2        |  Strong      | Medium       | Medium        | |
|  |  W=3, R=1        |  Strong      | Low writes   | High writes   | |
|  |  W=1, R=3        |  Strong      | Low reads    | High reads    | |
|  |  W=ALL, R=ONE    |  Strong      | Low          | High          | |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  CASSANDRA CONSISTENCY LEVELS:                                        |
|                                                                         |
|  ONE        - Only one replica needs to respond                       |
|  TWO        - Two replicas must respond                               |
|  THREE      - Three replicas must respond                             |
|  QUORUM     - Majority of replicas (N/2 + 1)                         |
|  ALL        - All replicas must respond                               |
|  LOCAL_ONE  - One replica in local datacenter                        |
|  LOCAL_QUORUM - Quorum in local datacenter                           |
|  EACH_QUORUM  - Quorum in each datacenter                            |
|                                                                         |
|  COMMON PATTERNS:                                                      |
|                                                                         |
|  Write: QUORUM, Read: QUORUM                                         |
|  -> Strong consistency with good availability                         |
|                                                                         |
|  Write: LOCAL_QUORUM, Read: LOCAL_QUORUM                             |
|  -> Strong consistency within datacenter, eventually between DCs     |
|                                                                         |
|  Write: ONE, Read: ONE                                                |
|  -> Fastest, but may read stale data                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.6: CONSENSUS ALGORITHMS (OVERVIEW)

How distributed systems agree on values:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY CONSENSUS?                                                        |
|                                                                         |
|  Distributed systems need to agree on:                                |
|  * Who is the leader?                                                 |
|  * What is the current value?                                        |
|  * What is the order of operations?                                  |
|                                                                         |
|  CHALLENGES:                                                           |
|  * Nodes can fail                                                     |
|  * Network can partition                                              |
|  * Messages can be delayed or lost                                   |
|  * Clocks are not synchronized                                       |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  PAXOS                                                                 |
|  =====                                                                  |
|  * Original consensus algorithm (Lamport, 1989)                      |
|  * Proven correct but notoriously hard to understand                 |
|  * Foundation for many systems (Google Chubby)                       |
|                                                                         |
|  RAFT                                                                  |
|  ====                                                                   |
|  * "Understandable" consensus (Ongaro, 2013)                         |
|  * Same guarantees as Paxos, easier to implement                     |
|  * Used in etcd, CockroachDB, Consul, TiDB                          |
|                                                                         |
|  RAFT SIMPLIFIED:                                                      |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  STATES:                                                        |  |
|  |  * Follower: Normal state, listens to leader                   |  |
|  |  * Candidate: Tries to become leader                           |  |
|  |  * Leader: Handles all client requests                         |  |
|  |                                                                 |  |
|  |  LEADER ELECTION:                                               |  |
|  |  1. Follower times out (no heartbeat from leader)              |  |
|  |  2. Becomes candidate, requests votes                          |  |
|  |  3. Gets majority votes -> becomes leader                       |  |
|  |  4. Sends heartbeats to maintain leadership                    |  |
|  |                                                                 |  |
|  |  LOG REPLICATION:                                               |  |
|  |  1. Client sends request to leader                             |  |
|  |  2. Leader appends to local log                                |  |
|  |  3. Leader sends to followers                                  |  |
|  |  4. Majority acknowledge -> committed                           |  |
|  |  5. Leader responds to client                                  |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  ZAB (ZOOKEEPER ATOMIC BROADCAST)                                    |
|  ===============================                                        |
|  * Used by Apache Zookeeper                                          |
|  * Optimized for primary-backup systems                              |
|                                                                         |
|  VIEWSTAMPED REPLICATION                                              |
|  ======================                                                 |
|  * Similar to Raft, predates it                                      |
|  * Used by some academic systems                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.7: CLOCKS AND TIME IN DISTRIBUTED SYSTEMS

Time is surprisingly hard in distributed systems:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE CLOCK PROBLEM                                                     |
|                                                                         |
|  PHYSICAL CLOCKS:                                                      |
|  * Every computer's clock drifts differently                         |
|  * Network time sync (NTP) has milliseconds of error                 |
|  * Can't reliably order events across machines                       |
|                                                                         |
|  SCENARIO:                                                             |
|  Machine A: Clock says 10:00:00.000                                  |
|  Machine B: Clock says 10:00:00.050 (50ms ahead)                     |
|                                                                         |
|  Event on A at "10:00:00.100"                                        |
|  Event on B at "10:00:00.075" (appears earlier but happened later!)  |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  LAMPORT TIMESTAMPS (LOGICAL CLOCKS)                                  |
|  ===================================                                    |
|                                                                         |
|  RULES:                                                                |
|  1. Before each event, increment counter                             |
|  2. When sending message, include counter                            |
|  3. When receiving, set counter = max(local, received) + 1          |
|                                                                         |
|  EXAMPLE:                                                              |
|                                                                         |
|  Process A          Process B          Process C                      |
|     |                   |                   |                          |
|     1 (event)          |                    |                          |
|     |----- msg(1) ---->2                    |                          |
|     |                   |----- msg(2) ----> 3                          |
|     |                   |                   |                          |
|     |                   |                   4 (event)                  |
|     |<----------------- msg(4) -----------  |                          |
|     5                   |                   |                          |
|                                                                         |
|  PROPERTY: If A happened-before B, then timestamp(A) < timestamp(B)  |
|  (But not vice versa - can't determine causality from timestamps)   |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  VECTOR CLOCKS                                                         |
|  =============                                                          |
|                                                                         |
|  Track causality between events.                                      |
|                                                                         |
|  Each process maintains a vector of counters:                         |
|  [count_A, count_B, count_C, ...]                                    |
|                                                                         |
|  RULES:                                                                |
|  1. On local event: increment own counter                            |
|  2. On send: include current vector                                  |
|  3. On receive: take element-wise max, then increment own           |
|                                                                         |
|  COMPARING VECTORS:                                                    |
|  V1 < V2 if all(V1[i] <= V2[i]) and some V1[i] < V2[i]             |
|  V1 || V2 (concurrent) if neither V1 < V2 nor V2 < V1              |
|                                                                         |
|  EXAMPLE:                                                              |
|  A: [2,0,0]  B: [0,1,0]                                              |
|  Neither is greater -> concurrent events (potential conflict!)        |
|                                                                         |
|  Used by: DynamoDB (version vectors), Riak                           |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  GOOGLE'S TRUETIME (Spanner)                                         |
|  ============================                                           |
|                                                                         |
|  Uses atomic clocks + GPS to bound clock uncertainty                 |
|                                                                         |
|  API: TrueTime.now() returns [earliest, latest] interval             |
|  Uncertainty: typically 1-7 milliseconds                             |
|                                                                         |
|  COMMIT WAIT: After commit, wait until uncertainty passes           |
|  If uncertainty is 7ms, wait 7ms before confirming commit           |
|                                                                         |
|  Result: Globally consistent reads without consensus!                |
|  Trade-off: Latency (must wait for uncertainty to pass)             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.8: CONFLICT RESOLUTION STRATEGIES

With eventual consistency, conflicts will happen. How do we resolve them?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CONFLICT RESOLUTION STRATEGIES                                        |
|                                                                         |
|  1. LAST-WRITE-WINS (LWW)                                             |
|  --------------------------                                             |
|  The write with the latest timestamp wins.                            |
|                                                                         |
|  Node A: write(x=1, timestamp=100)                                    |
|  Node B: write(x=2, timestamp=105)                                    |
|  Resolution: x=2 (higher timestamp)                                   |
|                                                                         |
|  PROS: Simple, automatic                                              |
|  CONS: May lose valid writes, clock skew issues                      |
|                                                                         |
|  Used by: Cassandra, S3, many others                                 |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. VECTOR CLOCKS (Detect conflicts)                                  |
|  ------------------------------------                                   |
|  Track causality, detect concurrent writes.                          |
|                                                                         |
|  Vector: {Node_A: 2, Node_B: 3, Node_C: 1}                           |
|                                                                         |
|  If all elements of V1 <= V2: V1 happened before V2                  |
|  If some elements V1 > V2 and some < V2: CONFLICT!                  |
|                                                                         |
|  Used by: DynamoDB, Riak (returns all versions to client)           |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. CRDTs (Conflict-Free Replicated Data Types)                      |
|  ------------------------------------------------                       |
|  Data structures designed to be mergeable without conflicts.         |
|                                                                         |
|  G-COUNTER (Grow-only counter):                                       |
|  Each node has own counter, sum all for total                        |
|  Node A: 5, Node B: 3, Node C: 7 -> Total: 15                        |
|  Always eventually consistent!                                        |
|                                                                         |
|  G-SET (Grow-only set):                                               |
|  Only additions, merge = union                                        |
|  Node A: {apple, banana}                                              |
|  Node B: {apple, cherry}                                              |
|  Merge: {apple, banana, cherry}                                       |
|                                                                         |
|  LWW-ELEMENT-SET:                                                     |
|  Each element has add/remove timestamp                               |
|  Higher timestamp wins                                                |
|                                                                         |
|  Used by: Redis CRDT, Riak, distributed collaborative editors       |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  4. APPLICATION-LEVEL RESOLUTION                                       |
|  ---------------------------------                                      |
|  Let the application or user decide.                                  |
|                                                                         |
|  * Shopping cart: Merge all items                                    |
|  * Document edit: Show diff, ask user                                |
|  * Counter: Sum values                                               |
|                                                                         |
|  Example (Git):                                                       |
|  "Merge conflict in file.txt. Please resolve manually."             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.9: PRACTICAL TRADE-OFF DECISIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CHOOSING CONSISTENCY LEVELS BY USE CASE                              |
|                                                                         |
|  +-----------------------------+------------------------------------+ |
|  | USE CASE                    | CONSISTENCY LEVEL                  | |
|  +-----------------------------+------------------------------------+ |
|  | Bank balance               | Strong (Linearizable)              | |
|  | Seat reservation           | Strong (Linearizable)              | |
|  | Inventory count (critical) | Strong                             | |
|  | Distributed locks          | Strong (Linearizable)              | |
|  | Leader election            | Strong (Consensus)                 | |
|  | User profile updates       | Read-Your-Writes                  | |
|  | Shopping cart              | Eventual + Merge conflicts        | |
|  | Social media feed          | Eventual                          | |
|  | Like/View counters         | Eventual                          | |
|  | Comment threads            | Causal                            | |
|  | Chat messages              | Causal                            | |
|  | Analytics                  | Eventual                          | |
|  | Search index               | Eventual (seconds lag OK)         | |
|  | Recommendations            | Eventual (minutes lag OK)         | |
|  | Email                      | Eventual (minutes lag OK)         | |
|  +-----------------------------+------------------------------------+ |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  INTERVIEW FRAMEWORK FOR CONSISTENCY DECISIONS:                       |
|                                                                         |
|  1. "What's the cost of showing stale data?"                         |
|     * Financial loss? -> Strong                                       |
|     * User annoyance? -> Read-your-writes                            |
|     * Acceptable? -> Eventual                                        |
|                                                                         |
|  2. "What's the cost of being unavailable?"                          |
|     * Revenue loss per minute? -> Favor availability                 |
|     * Can users retry later? -> Favor consistency                    |
|                                                                         |
|  3. "Can we resolve conflicts automatically?"                        |
|     * Yes (counters, sets) -> Eventual with CRDTs                    |
|     * No (money transfers) -> Strong consistency                     |
|                                                                         |
|  4. "What are the latency requirements?"                             |
|     * Sub-100ms? -> May need eventual for geographic distribution    |
|     * Seconds OK? -> Strong consistency might work                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CAP THEOREM & CONSISTENCY - KEY TAKEAWAYS                            |
|                                                                         |
|  CAP THEOREM                                                           |
|  ------------                                                          |
|  * Pick 2 of 3: Consistency, Availability, Partition Tolerance       |
|  * Partitions WILL happen, so really choose between C and A         |
|  * CP: Refuse requests during partition (banks, inventory)          |
|  * AP: Serve stale data during partition (social, analytics)        |
|                                                                         |
|  PACELC                                                                |
|  ------                                                                |
|  * Extends CAP: Even without partitions, latency vs consistency     |
|  * Most systems trade latency for consistency in normal operation   |
|                                                                         |
|  CONSISTENCY MODELS (Strong -> Weak)                                   |
|  -------------------------------------                                  |
|  * Linearizable: Real-time ordering (most expensive)                 |
|  * Sequential: Total order preserved                                 |
|  * Causal: Cause-effect preserved                                    |
|  * Eventual: Will converge eventually (cheapest)                     |
|                                                                         |
|  PRACTICAL PATTERNS                                                    |
|  -------------------                                                   |
|  * Read-After-Write: User sees their own writes                      |
|  * Monotonic Reads: Time never goes backward                         |
|  * Tunable Consistency: W + R > N for strong consistency            |
|                                                                         |
|  CONSENSUS & TIME                                                      |
|  ----------------                                                      |
|  * Raft/Paxos: How nodes agree on values                            |
|  * Lamport/Vector clocks: Logical time ordering                     |
|  * TrueTime: Physical time with bounded uncertainty                 |
|                                                                         |
|  CONFLICT RESOLUTION                                                   |
|  --------------------                                                  |
|  * LWW: Simple but loses writes                                      |
|  * Vector clocks: Detect conflicts                                   |
|  * CRDTs: Conflict-free merge                                        |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  INTERVIEW TIPS                                                        |
|  --------------                                                        |
|                                                                         |
|  1. Don't say "we need strong consistency" without justification.   |
|     Always ask: "What's the cost of stale data vs unavailability?" |
|                                                                         |
|  2. Know the databases:                                               |
|     * CP: MongoDB, HBase, Spanner, etcd                             |
|     * AP: Cassandra, DynamoDB, Riak                                 |
|                                                                         |
|  3. Mention tunable consistency:                                      |
|     "We can configure read/write consistency levels to balance..."  |
|                                                                         |
|  4. Use specific examples:                                            |
|     "For the like counter, eventual consistency is fine because..." |
|     "For seat booking, we need linearizability because..."          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 2

