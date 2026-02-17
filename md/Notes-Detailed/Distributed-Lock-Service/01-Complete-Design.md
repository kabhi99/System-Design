# Distributed Lock Service - Complete System Design

## Table of Contents

1. Introduction & Motivation
2. Requirements
3. Scale Estimation
4. High-Level Architecture
5. Detailed Design: Redis-Based Locks
6. Detailed Design: ZooKeeper-Based Locks
7. Detailed Design: etcd-Based Locks
8. Fencing Tokens
9. Lock Granularity
10. Deadlock Detection & Prevention
11. Leader Election Using Distributed Locks
12. Performance Comparison
13. Common Pitfalls
14. Real-World Use Cases
15. Martin Kleppmann's Critique of Redlock
16. Trade-offs Summary
17. Interview Q&A

---

## 1. Introduction & Motivation

### Why Distributed Locks Are Needed

In a single-process application, threads can coordinate using in-memory mutexes or
semaphores. In a distributed system with multiple processes running on multiple
machines, we need a fundamentally different mechanism for mutual exclusion.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE CORE PROBLEM                                                       |
|                                                                         |
|  Process A (Machine 1)       Shared Resource       Process B (Machine 2)|
|       |                      (e.g., Database)            |              |
|       |---- write X=10 ----------->|                     |              |
|       |                            |<------- write X=20 -|              |
|       |                            |                     |              |
|  Without coordination, both processes can write                         |
|  simultaneously, leading to data corruption, race                       |
|  conditions, and inconsistent state.                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Scenarios Where Distributed Locks Are Essential

```
+--------------------------------------------------------------------------+
|                                                                          |
|  1. EFFICIENCY (Avoiding Duplicate Work)                                 |
|     - Multiple workers processing a job queue                            |
|     - Only one worker should process each job                            |
|     - Cost: duplicate work wastes compute resources                      |
|                                                                          |
|  2. CORRECTNESS (Preventing Data Corruption)                             |
|     - Two processes updating the same bank account                       |
|     - Must serialize writes to maintain balance consistency              |
|     - Cost: financial loss, data corruption                              |
|                                                                          |
|  3. COORDINATION (Ordering Operations)                                   |
|     - Database schema migrations across microservices                    |
|     - Only one service should run migrations at a time                   |
|     - Cost: schema corruption, failed deployments                        |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 2. Requirements

### Functional Requirements

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FUNCTIONAL REQUIREMENTS                                                |
|                                                                         |
|  FR1: Acquire Lock                                                      |
|       - Client can request a lock on a named resource                   |
|       - Returns success/failure                                         |
|       - Should support blocking (wait) and non-blocking (try) modes     |
|                                                                         |
|  FR2: Release Lock                                                      |
|       - Client can explicitly release a held lock                       |
|       - Only the lock holder should be able to release                  |
|                                                                         |
|  FR3: Time-To-Live (TTL)                                                |
|       - Locks auto-expire after a configurable duration                 |
|       - Prevents deadlocks from crashed clients                         |
|                                                                         |
|  FR4: Lock Renewal (Heartbeat)                                          |
|       - Holder can extend TTL while still working                       |
|       - Prevents premature expiration during long operations            |
|                                                                         |
|  FR5: Fairness                                                          |
|       - Optional FIFO ordering for waiting clients                      |
|       - Prevents starvation of long-waiting clients                     |
|                                                                         |
|  FR6: Re-entrancy                                                       |
|       - Same client/thread can acquire the same lock multiple times     |
|       - Must release the same number of times                           |
|                                                                         |
|  FR7: Fencing                                                           |
|       - Provide monotonically increasing tokens to detect stale holders |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Non-Functional Requirements

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NON-FUNCTIONAL REQUIREMENTS                                            |
|                                                                         |
|  NFR1: Safety (Mutual Exclusion)                                        |
|        - At most one client holds the lock at any time                  |
|        - This is the MOST CRITICAL property                             |
|                                                                         |
|  NFR2: Liveness (Deadlock Freedom)                                      |
|        - Even if a lock holder crashes, the lock is eventually released |
|        - System makes progress                                          |
|                                                                         |
|  NFR3: Fault Tolerance                                                  |
|        - Lock service remains available if some nodes fail              |
|        - No single point of failure                                     |
|                                                                         |
|  NFR4: Low Latency                                                      |
|        - Lock acquire/release in < 10ms for local operations            |
|        - < 50ms for cross-datacenter operations                         |
|                                                                         |
|  NFR5: High Throughput                                                  |
|        - Support 100K+ lock operations per second                       |
|                                                                         |
|  NFR6: Scalability                                                      |
|        - Handle millions of concurrent locks across the cluster         |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 3. Scale Estimation

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCALE NUMBERS                                                          |
|                                                                         |
|  Concurrent lock holders:        ~1M                                    |
|  Lock operations per second:     ~100K                                  |
|  Average lock hold time:         ~500ms                                 |
|  Average lock data size:         ~200 bytes (key + metadata)            |
|                                                                         |
|  STORAGE:                                                               |
|    1M locks x 200 bytes = 200 MB (easily fits in memory)                |
|                                                                         |
|  BANDWIDTH:                                                             |
|    100K ops/sec x 200 bytes = 20 MB/sec                                 |
|                                                                         |
|  NETWORK:                                                               |
|    Round-trip per lock op: ~1ms (same DC), ~50ms (cross-DC)             |
|    At 100K ops/sec, need connection pooling + pipelining                |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 4. High-Level Architecture

```
+--------------------------------------------------------------------------+
|                           DISTRIBUTED LOCK SERVICE                       |
+--------------------------------------------------------------------------+
|                                                                          |
|   +-------------+    +-------------+    +-------------+                  |
|   |  Service A  |    |  Service B  |    |  Service C  |                  |
|   |  (Client)   |    |  (Client)   |    |  (Client)   |                  |
|   +------+------+    +------+------+    +------+------+                  |
|          |                  |                  |                         |
|          v                  v                  v                         |
|   +-------------------------------------------------------------+        |
|   |              Lock Client Library / SDK                       |       |
|   |  - Acquire, Release, Renew                                   |       |
|   |  - Automatic heartbeat / renewal                             |       |
|   |  - Retry logic with backoff                                  |       |
|   |  - Fencing token management                                  |       |
|   +------------------------------+------------------------------+        |
|                                  |                                       |
|                                  v                                       |
|   +-------------------------------------------------------------+        |
|   |                    LOCK SERVICE CLUSTER                      |       |
|   |                                                              |       |
|   |   +-----------+    +-----------+    +-----------+            |       |
|   |   |  Node 1   |    |  Node 2   |    |  Node 3   |            |       |
|   |   | (Leader)  |<-->| (Follower)|<-->| (Follower)|            |       |
|   |   +-----------+    +-----------+    +-----------+            |       |
|   |                                                              |       |
|   |   Consensus: Raft / ZAB / Paxos                             |        |
|   |   Data: Lock state replicated across majority               |        |
|   +-------------------------------------------------------------+        |
|                                  |                                       |
|                                  v                                       |
|   +-------------------------------------------------------------+        |
|   |                    SHARED RESOURCES                          |       |
|   |                                                              |       |
|   |   +----------+  +----------+  +-----------+  +----------+   |        |
|   |   | Database |  | File     |  | Message   |  | External |   |        |
|   |   | Records  |  | System   |  | Queue     |  | API      |   |        |
|   |   +----------+  +----------+  +-----------+  +----------+   |        |
|   +-------------------------------------------------------------+        |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Lock Lifecycle

```
+--------------------------------------------------------------------------+
|                                                                          |
|  LOCK STATE MACHINE                                                      |
|                                                                          |
|  +----------+   acquire()   +-----------+   release()   +------------+   |
|  |          |  ---------->  |           |  ---------->  |            |   |
|  |   FREE   |               |   HELD    |               |   FREE     |   |
|  |          |  <----------  |           |  <----------  |            |   |
|  +----------+   TTL expire  +-----------+   TTL expire  +------------+   |
|       ^                          |                                       |
|       |                          | renew()                               |
|       |                          v                                       |
|       |                    +-----------+                                 |
|       +----TTL expire------| HELD      |                                 |
|                            | (renewed) |                                 |
|                            +-----------+                                 |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 5. Detailed Design: Redis-Based Locks

### 5.1 Simple Redis Lock (Single Instance)

The simplest approach uses Redis SET with NX (Not eXists) and EX (Expiry):

```
+--------------------------------------------------------------------------+
|                                                                          |
|  ACQUIRE LOCK:                                                           |
|    SET resource_name my_random_value NX EX 30                            |
|                                                                          |
|    - NX: Only set if key does not exist (atomic check-and-set)           |
|    - EX 30: Auto-expire after 30 seconds                                 |
|    - my_random_value: Unique ID to identify the lock holder              |
|                                                                          |
|  RELEASE LOCK (Lua script for atomicity):                                |
|    if redis.call("GET", KEYS[1]) == ARGV[1] then                         |
|        return redis.call("DEL", KEYS[1])                                 |
|    else                                                                  |
|        return 0                                                          |
|    end                                                                   |
|                                                                          |
|  WHY Lua? GET + DEL must be atomic. Without Lua:                         |
|    1. Client A does GET -> sees its own value                            |
|    2. Lock expires                                                       |
|    3. Client B acquires lock                                             |
|    4. Client A does DEL -> deletes Client B's lock!                      |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 5.2 Problems With Single-Instance Redis Lock

```
+--------------------------------------------------------------------------+
|                                                                          |
|  PROBLEM: Single Point of Failure                                        |
|                                                                          |
|  Client A acquires lock on Redis Master                                  |
|       |                                                                  |
|       v                                                                  |
|  Redis Master crashes BEFORE replicating to Replica                      |
|       |                                                                  |
|       v                                                                  |
|  Redis Replica gets promoted to Master                                   |
|       |                                                                  |
|       v                                                                  |
|  Client B acquires the SAME lock (it was never replicated)               |
|       |                                                                  |
|       v                                                                  |
|  BOTH Client A and Client B think they hold the lock!                    |
|  --> MUTUAL EXCLUSION VIOLATED                                           |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 5.3 Redlock Algorithm (Multi-Instance)

Proposed by Salvatore Sanfilippo (antirez), Redlock uses N independent Redis
instances (typically N=5) to achieve stronger safety guarantees.

```
+--------------------------------------------------------------------------+
|                                                                          |
|  REDLOCK ALGORITHM                                                       |
|                                                                          |
|  Setup: 5 independent Redis masters (no replication between them)        |
|                                                                          |
|  +--------+  +--------+  +--------+  +--------+  +--------+              |
|  |Redis 1 |  |Redis 2 |  |Redis 3 |  |Redis 4 |  |Redis 5 |              |
|  +--------+  +--------+  +--------+  +--------+  +--------+              |
|                                                                          |
|  ACQUIRE STEPS:                                                          |
|                                                                          |
|  Step 1: Record current time T1                                          |
|                                                                          |
|  Step 2: Try to acquire the lock on ALL N instances                      |
|          sequentially, with a small timeout per instance                 |
|          (e.g., 5-50ms)                                                  |
|                                                                          |
|  Step 3: Record current time T2                                          |
|          Elapsed = T2 - T1                                               |
|                                                                          |
|  Step 4: Lock is acquired IF AND ONLY IF:                                |
|          a) Client got the lock on majority (>= N/2 + 1 = 3)             |
|          b) Total elapsed time < lock TTL                                |
|                                                                          |
|  Step 5: Effective TTL = initial_TTL - elapsed_time                      |
|                                                                          |
|  Step 6: If lock acquisition FAILS, release on ALL instances             |
|          (even ones where it succeeded)                                  |
|                                                                          |
|  RELEASE: Send DEL to ALL N instances                                    |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 5.4 Redlock Timing Diagram

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Timeline:                                                               |
|                                                                          |
|  T1 (start)                                                              |
|  |                                                                       |
|  |---> SET on Redis1 (OK)    ~2ms                                        |
|  |---> SET on Redis2 (OK)    ~3ms                                        |
|  |---> SET on Redis3 (FAIL)  ~50ms (timeout)                             |
|  |---> SET on Redis4 (OK)    ~2ms                                        |
|  |---> SET on Redis5 (OK)    ~4ms                                        |
|  |                                                                       |
|  T2 (end)                                                                |
|                                                                          |
|  Elapsed = ~61ms                                                         |
|  Successes = 4 out of 5 (>= 3 majority) --> PASS                         |
|  Lock TTL = 30s, Effective TTL = 30s - 61ms ~= 29.9s --> PASS            |
|                                                                          |
|  RESULT: Lock acquired with effective TTL of 29.9 seconds                |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 6. Detailed Design: ZooKeeper-Based Locks

### 6.1 ZooKeeper Fundamentals

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ZOOKEEPER NODE TYPES                                                   |
|                                                                         |
|  1. Persistent Nodes                                                    |
|     - Survive client disconnection                                      |
|     - Must be explicitly deleted                                        |
|                                                                         |
|  2. Ephemeral Nodes                                                     |
|     - Automatically deleted when client session ends                    |
|     - Cannot have children                                              |
|     - KEY for lock implementation (auto-cleanup on crash)               |
|                                                                         |
|  3. Sequential Nodes                                                    |
|     - ZooKeeper appends a monotonically increasing counter              |
|     - Example: /locks/resource- -> /locks/resource-0000000001           |
|     - KEY for fairness (FIFO ordering)                                  |
|                                                                         |
|  4. Ephemeral Sequential Nodes                                          |
|     - Combines both properties                                          |
|     - PERFECT for distributed locks                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 6.2 ZooKeeper Lock Algorithm

```
+--------------------------------------------------------------------------+
|                                                                          |
|  FAIR LOCK USING EPHEMERAL SEQUENTIAL NODES                              |
|                                                                          |
|  ACQUIRE:                                                                |
|  1. Create ephemeral sequential node:                                    |
|     /locks/resource-/lock-  --> /locks/resource-/lock-0000000007         |
|                                                                          |
|  2. Get children of /locks/resource-/ and sort them                      |
|     [lock-0000000005, lock-0000000006, lock-0000000007]                  |
|                                                                          |
|  3. If my node is the LOWEST numbered:                                   |
|     --> Lock acquired!                                                   |
|                                                                          |
|  4. If NOT the lowest, set a WATCH on the node just before mine:         |
|     My node: lock-0000000007                                             |
|     Watch:   lock-0000000006                                             |
|                                                                          |
|  5. When lock-0000000006 is deleted (released/expired):                  |
|     --> Watch fires, go to step 2                                        |
|                                                                          |
|  RELEASE:                                                                |
|  - Delete my ephemeral sequential node                                   |
|  - OR: client disconnects -> ZK auto-deletes ephemeral node              |
|                                                                          |
|  WHY watch only the predecessor (not all children)?                      |
|  - Avoids "herd effect" (thundering herd)                                |
|  - Only the next waiter is notified, not all waiters                     |
|  - O(1) notifications instead of O(n)                                    |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 6.3 ZooKeeper Lock Visual

```
+--------------------------------------------------------------------------+
|                                                                          |
|  /locks/my-resource/                                                     |
|  |                                                                       |
|  +-- lock-0000000001  (Client A) <-- LOCK HOLDER                         |
|  +-- lock-0000000002  (Client B) <-- watches lock-0000000001             |
|  +-- lock-0000000003  (Client C) <-- watches lock-0000000002             |
|  +-- lock-0000000004  (Client D) <-- watches lock-0000000003             |
|                                                                          |
|  When Client A releases (deletes lock-0000000001):                       |
|  - Client B's watch fires                                                |
|  - Client B checks: am I lowest? YES --> Lock acquired                   |
|  - Clients C and D are NOT notified (no herd effect)                     |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 6.4 ZooKeeper Read-Write Lock

```
+--------------------------------------------------------------------------+
|                                                                          |
|  READ-WRITE LOCK EXTENSION                                               |
|                                                                          |
|  /locks/my-resource/                                                     |
|  |                                                                       |
|  +-- read-0000000001   (Client A)                                        |
|  +-- write-0000000002  (Client B)                                        |
|  +-- read-0000000003   (Client C)                                        |
|                                                                          |
|  READ LOCK:                                                              |
|  - Acquired if no WRITE node with lower sequence exists                  |
|  - Watch the nearest WRITE node with lower sequence                      |
|  - Multiple readers can hold simultaneously                              |
|                                                                          |
|  WRITE LOCK:                                                             |
|  - Acquired only if it is the lowest sequence node                       |
|  - Watch the node immediately before it                                  |
|  - Exclusive access                                                      |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 7. Detailed Design: etcd-Based Locks

### 7.1 etcd Primitives

```
+-------------------------------------------------------------------------+
|                                                                         |
|  etcd KEY CONCEPTS FOR LOCKING                                          |
|                                                                         |
|  1. Lease                                                               |
|     - A time-to-live (TTL) grant from the etcd server                   |
|     - Keys can be attached to a lease                                   |
|     - When the lease expires, all attached keys are deleted             |
|     - Client sends keep-alive to renew the lease                        |
|                                                                         |
|  2. Compare-And-Swap (Transactions)                                     |
|     - Atomic if-then-else operations                                    |
|     - IF key does not exist THEN create it ELSE fail                    |
|     - Uses revision numbers for optimistic concurrency                  |
|                                                                         |
|  3. Watch                                                               |
|     - Efficient event-driven notifications                              |
|     - Watch a key or prefix for changes                                 |
|     - Uses server-side streaming (gRPC)                                 |
|                                                                         |
|  4. Revision                                                            |
|     - Every key modification gets a global revision number              |
|     - Monotonically increasing across the cluster                       |
|     - Can be used as fencing tokens                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 7.2 etcd Lock Algorithm

```
+--------------------------------------------------------------------------+
|                                                                          |
|  etcd LOCK IMPLEMENTATION                                                |
|                                                                          |
|  ACQUIRE:                                                                |
|                                                                          |
|  1. Create a lease with TTL (e.g., 30s)                                  |
|     lease_id = etcd.LeaseGrant(TTL=30)                                   |
|                                                                          |
|  2. Create a key under the lock prefix with lease attached:              |
|     PUT /locks/resource/lease_id value=client_id lease=lease_id          |
|                                                                          |
|  3. Get all keys with prefix /locks/resource/                            |
|     Sort by create_revision (ascending)                                  |
|                                                                          |
|  4. If my key has the LOWEST create_revision:                            |
|     --> Lock acquired!                                                   |
|                                                                          |
|  5. Otherwise, WATCH the key with the next-lower create_revision         |
|     Wait for it to be deleted                                            |
|                                                                          |
|  6. Start a goroutine to send LeaseKeepAlive periodically                |
|                                                                          |
|  RELEASE:                                                                |
|  - Revoke the lease: etcd.LeaseRevoke(lease_id)                          |
|  - This deletes all keys attached to the lease                           |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 7.3 etcd Transaction Example

```
+-------------------------------------------------------------------------+
|                                                                         |
|  COMPARE-AND-SWAP LOCK (Alternative Approach)                           |
|                                                                         |
|  // Atomic transaction                                                  |
|  Txn:                                                                   |
|    IF key("/locks/my-resource") does not exist:                         |
|      THEN: PUT "/locks/my-resource" value="client-123" lease=lease_id   |
|      ELSE: (fail, lock is held by someone else)                         |
|                                                                         |
|  // Check who holds the lock                                            |
|  GET "/locks/my-resource"                                               |
|  --> Returns value="client-123", mod_revision=1042, lease=lease_id      |
|                                                                         |
|  // The mod_revision can serve as a fencing token                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 8. Fencing Tokens

### The Fencing Token Problem

```
+--------------------------------------------------------------------------+
|                                                                          |
|  PROBLEM: STALE LOCK HOLDER                                              |
|                                                                          |
|  Timeline:                                                               |
|                                                                          |
|  Client A acquires lock (TTL = 30s)                                      |
|       |                                                                  |
|       |--- starts processing                                             |
|       |                                                                  |
|       |--- GC pause / network delay (35 seconds!)                        |
|       |                                                                  |
|       |   Lock TTL expires at T+30s                                      |
|       |   Client B acquires lock at T+31s                                |
|       |   Client B writes to storage                                     |
|       |                                                                  |
|       |--- Client A resumes at T+35s                                     |
|       |--- Client A writes to storage (STALE HOLDER!)                    |
|       |                                                                  |
|  RESULT: Both clients wrote, corrupting data                             |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Solution: Fencing Tokens

```
+--------------------------------------------------------------------------+
|                                                                          |
|  FENCING TOKEN MECHANISM                                                 |
|                                                                          |
|  Lock service provides a monotonically increasing token                  |
|  with each lock acquisition.                                             |
|                                                                          |
|  Client A acquires lock --> Token = 33                                   |
|       |                                                                  |
|       |--- GC pause (lock expires)                                       |
|       |                                                                  |
|  Client B acquires lock --> Token = 34                                   |
|  Client B writes to storage with token=34                                |
|  Storage records: last_token = 34                                        |
|       |                                                                  |
|  Client A resumes, writes with token=33                                  |
|  Storage checks: 33 < 34 (last_token)                                    |
|  Storage REJECTS the write!                                              |
|                                                                          |
|  REQUIREMENT: The storage system must support fencing                    |
|  by checking and rejecting tokens lower than the last seen token.        |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Where Do Fencing Tokens Come From?

```
+--------------------------------------------------------------------------+
|                                                                          |
|  SOURCES OF FENCING TOKENS                                               |
|                                                                          |
|  ZooKeeper: The sequential node number (lock-0000000034)                 |
|             Monotonically increasing by design                           |
|                                                                          |
|  etcd:      The create_revision or mod_revision of the key               |
|             Global monotonic counter across the cluster                  |
|                                                                          |
|  Redis:     NOT built-in. You must implement your own                    |
|             counter (e.g., INCR on a separate key).                      |
|             This is one weakness of Redis-based locks.                   |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 9. Lock Granularity

```
+-------------------------------------------------------------------------+
|                                                                         |
|  COARSE-GRAINED vs FINE-GRAINED LOCKS                                   |
|                                                                         |
|  +-----------------------------+------------------------------------+   |
|  |  Coarse-Grained             |  Fine-Grained                      |   |
|  +-----------------------------+------------------------------------+   |
|  |  Lock: /locks/database      |  Lock: /locks/db/table/row/123     |   |
|  |  Scope: entire database     |  Scope: single row                 |   |
|  |  Contention: HIGH           |  Contention: LOW                   |   |
|  |  Throughput: LOW             |  Throughput: HIGH                 |   |
|  |  Complexity: LOW             |  Complexity: HIGH                 |   |
|  |  Deadlock risk: LOW          |  Deadlock risk: HIGH              |   |
|  |  Use: rare operations        |  Use: frequent concurrent ops     |   |
|  +-----------------------------+------------------------------------+   |
|                                                                         |
|  EXAMPLES:                                                              |
|  - Coarse: Lock on "payment-service" for maintenance window             |
|  - Fine: Lock on "order:12345" to process a specific order              |
|  - Fine: Lock on "user:67890:cart" to update a user's cart              |
|                                                                         |
|  BEST PRACTICE: Lock the smallest resource necessary                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 10. Deadlock Detection & Prevention

### How Deadlocks Occur

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DEADLOCK SCENARIO (Circular Wait)                                      |
|                                                                         |
|  Client A holds Lock 1, wants Lock 2                                    |
|  Client B holds Lock 2, wants Lock 1                                    |
|                                                                         |
|       Client A                    Client B                              |
|       +--------+                  +--------+                            |
|       | Holds  |---wants Lock2--->| Holds  |                            |
|       | Lock 1 |                  | Lock 2 |                            |
|       |        |<--wants Lock1----|        |                            |
|       +--------+                  +--------+                            |
|                                                                         |
|  Both clients wait forever --> DEADLOCK                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Prevention Strategies

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DEADLOCK PREVENTION                                                    |
|                                                                         |
|  1. LOCK ORDERING                                                       |
|     - Always acquire locks in a consistent global order                 |
|     - If you need Lock A and Lock B, always acquire A first             |
|     - Prevents circular wait condition                                  |
|                                                                         |
|  2. LOCK TIMEOUT (TTL)                                                  |
|     - All locks expire after a maximum duration                         |
|     - Breaks deadlocks automatically                                    |
|     - Trade-off: too short = false expiration; too long = slow recovery |
|                                                                         |
|  3. TRY-LOCK WITH TIMEOUT                                               |
|     - Attempt to acquire lock with a deadline                           |
|     - If deadline exceeded, release all held locks and retry            |
|     - Add random jitter to retry delay (avoids livelock)                |
|                                                                         |
|  4. WAIT-DIE / WOUND-WAIT SCHEMES                                       |
|     - Assign timestamps/priorities to transactions                      |
|     - Wait-Die: older waits, younger aborts (dies)                      |
|     - Wound-Wait: older preempts (wounds) younger, younger waits        |
|                                                                         |
|  5. DEADLOCK DETECTION (WAIT-FOR GRAPH)                                 |
|     - Build a directed graph: Client -> Lock it's waiting for           |
|     - Cycle in graph = deadlock                                         |
|     - Abort one client in the cycle to break it                         |
|     - Expensive in distributed systems (need global view)               |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 11. Leader Election Using Distributed Locks

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LEADER ELECTION VIA LOCKS                                              |
|                                                                         |
|  All nodes try to acquire the same lock:                                |
|  /election/my-service-leader                                            |
|                                                                         |
|  +--------+  +--------+  +--------+                                     |
|  | Node 1 |  | Node 2 |  | Node 3 |                                     |
|  +---+----+  +---+----+  +---+----+                                     |
|      |           |           |                                          |
|      |--acquire->|           |                                          |
|      |    Lock   |--acquire->|                                          |
|      |  Service  |   Lock    |--acquire->                               |
|      |           |  Service  |   Lock                                   |
|      |           |           |  Service                                 |
|      |<--OK------|           |                                          |
|      | (LEADER)  |<--FAIL----|                                          |
|      |           | (FOLLOWER)|<--FAIL----                               |
|      |           |           | (FOLLOWER)                               |
|                                                                         |
|  Node 1 = Leader (holds the lock)                                       |
|  Nodes 2,3 = Followers (watch the lock, ready to take over)             |
|                                                                         |
|  When Node 1 crashes:                                                   |
|  - Lock TTL expires (or ephemeral node deleted)                         |
|  - Node 2 or 3 acquires lock --> new leader                             |
|                                                                         |
|  USE CASES:                                                             |
|  - Database primary election                                            |
|  - Scheduler master (only one scheduler runs cron jobs)                 |
|  - Partition leader in stream processing (Kafka consumer groups)        |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 12. Performance Comparison

```
+--------------------------------------------------------------------------+
|                                                                          |
|  REDIS vs ZOOKEEPER vs etcd                                              |
|                                                                          |
|  +----------------+-----------+-----------+-----------+                  |
|  | Property       | Redis     | ZooKeeper | etcd      |                  |
|  +----------------+-----------+-----------+-----------+                  |
|  | Latency        | ~1ms      | ~2-10ms   | ~2-10ms   |                  |
|  | Throughput      | ~100K/s   | ~10K/s    | ~10K/s    |                 |
|  | Consistency     | Eventual* | Strong    | Strong    |                 |
|  | Safety          | Weak**    | Strong    | Strong    |                 |
|  | Fairness        | No FIFO   | FIFO      | FIFO      |                 |
|  | Auto-release    | TTL only  | Session   | Lease     |                 |
|  | Fencing tokens  | Manual    | Built-in  | Built-in  |                 |
|  | Ops complexity  | Low       | Medium    | Low       |                 |
|  | Watch/Notify    | Pub/Sub   | Native    | Native    |                 |
|  | Consensus       | None***   | ZAB       | Raft      |                 |
|  +----------------+-----------+-----------+-----------+                  |
|                                                                          |
|  * Redis replication is async; Redlock tries to compensate               |
|  ** Redis Redlock safety is debated (see Kleppmann critique)             |
|  *** Each Redlock instance is independent, no inter-node consensus       |
|                                                                          |
|  WHEN TO USE WHAT:                                                       |
|                                                                          |
|  Redis:     Best for efficiency-focused locks where occasional           |
|             double-locking is acceptable. High performance.              |
|                                                                          |
|  ZooKeeper: Best for correctness-critical locks. Strong guarantees.      |
|             Good if you already run ZooKeeper (Kafka, Hadoop).           |
|                                                                          |
|  etcd:      Best for Kubernetes-native environments. Strong              |
|             guarantees with simpler operations than ZooKeeper.           |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 13. Common Pitfalls

### 13.1 Clock Skew

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CLOCK SKEW PROBLEM                                                     |
|                                                                         |
|  Redlock assumes bounded clock drift across machines.                   |
|                                                                         |
|  Machine A clock: 12:00:00                                              |
|  Machine B clock: 12:00:05  (5 seconds ahead!)                          |
|                                                                         |
|  If lock TTL = 10 seconds:                                              |
|  - Machine A thinks lock expires at 12:00:10                            |
|  - Machine B thinks lock expires at 12:00:05 (from A's perspective)     |
|  - Lock expires 5 seconds early on Machine B!                           |
|                                                                         |
|  MITIGATION:                                                            |
|  - Use NTP to synchronize clocks                                        |
|  - Add safety margin to TTL calculations                                |
|  - ZooKeeper/etcd avoid this: they use logical clocks (revisions)       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 13.2 GC Pauses

```
+-------------------------------------------------------------------------+
|                                                                         |
|  GARBAGE COLLECTION PAUSE PROBLEM                                       |
|                                                                         |
|  1. Client acquires lock (TTL = 30s)                                    |
|  2. Client's JVM enters full GC (stop-the-world for 40s)                |
|  3. During GC, client cannot:                                           |
|     - Send heartbeats / renewals                                        |
|     - Respond to any requests                                           |
|     - Know that time is passing                                         |
|  4. Lock TTL expires at T+30s                                           |
|  5. Another client acquires the lock                                    |
|  6. First client resumes at T+40s, still thinks it holds the lock       |
|                                                                         |
|  MITIGATION:                                                            |
|  - Use fencing tokens (described in Section 8)                          |
|  - Use lock renewal with shorter TTL (e.g., 5s TTL, renew every 2s)     |
|  - Design systems to be idempotent                                      |
|  - Consider using non-GC languages for critical lock holders            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 13.3 Network Partitions

```
+--------------------------------------------------------------------------+
|                                                                          |
|  NETWORK PARTITION SCENARIO                                              |
|                                                                          |
|        +--------+                                                        |
|        |Client A|                                                        |
|        +---+----+                                                        |
|            |          PARTITION                                          |
|    ........|..........//........                                         |
|    :       v         //        :                                         |
|    : +-----------+  //  +-----------+                                    |
|    : | Redis 1,2 | //   | Redis 3,4,5|                                   |
|    : | (minority)|//    | (majority)  |                                  |
|    : +-----------+      +-----------+ :                                  |
|    :                         ^        :                                  |
|    :.........................|........:                                  |
|                              |                                           |
|                         +--------+                                       |
|                         |Client B|                                       |
|                         +--------+                                       |
|                                                                          |
|  - Client A may have locked Redis 1,2 before partition                   |
|  - Client B can now lock Redis 3,4,5 (majority) after partition          |
|  - If Client A had locked 3 of 5 before partition split them             |
|    into minority, Client A's lock may effectively be lost                |
|                                                                          |
|  ZooKeeper/etcd handle this correctly:                                   |
|  - Only the partition with majority can serve requests                   |
|  - Minority partition becomes read-only or unavailable                   |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 13.4 Split Brain

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SPLIT BRAIN                                                            |
|                                                                         |
|  Two nodes both believe they are the leader/lock holder.                |
|                                                                         |
|  Common cause: network partition + lock expiration                      |
|                                                                         |
|  Prevention:                                                            |
|  - Quorum-based decisions (majority must agree)                         |
|  - Fencing tokens on all shared resources                               |
|  - Use consensus protocols (Raft, ZAB)                                  |
|  - Implement "lease" with server-side enforcement                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 14. Real-World Use Cases

```
+--------------------------------------------------------------------------+
|                                                                          |
|  USE CASE 1: DATABASE SCHEMA MIGRATIONS                                  |
|                                                                          |
|  Problem: 10 instances of a service start simultaneously.                |
|           All try to run DB migrations.                                  |
|  Solution: Acquire lock "db-migration-v42" before migrating.             |
|            Only one instance runs the migration.                         |
|            Others wait, then skip (migration already done).              |
|                                                                          |
+--------------------------------------------------------------------------+
|                                                                          |
|  USE CASE 2: CRON JOB DEDUPLICATION                                      |
|                                                                          |
|  Problem: Multiple app servers all have the same cron schedule.          |
|           A daily report should only be generated once.                  |
|  Solution: Before running the cron job, acquire lock                     |
|            "report-2024-01-15". First to acquire runs the job.           |
|                                                                          |
+--------------------------------------------------------------------------+
|                                                                          |
|  USE CASE 3: INVENTORY / STOCK MANAGEMENT                                |
|                                                                          |
|  Problem: Flash sale - 1000 users buy the last 5 items.                  |
|           Without locking, overselling occurs.                           |
|  Solution: Lock "product:12345:stock" before decrementing.               |
|            Better: use optimistic locking (CAS) for higher throughput.   |
|                                                                          |
+--------------------------------------------------------------------------+
|                                                                          |
|  USE CASE 4: DISTRIBUTED RATE LIMITING                                   |
|                                                                          |
|  Problem: API rate limit of 100 req/min across 10 servers.               |
|           Each server does not know about others' counts.                |
|  Solution: Lock + shared counter, or use token bucket with               |
|            distributed state. Lock around counter updates.               |
|                                                                          |
+--------------------------------------------------------------------------+
|                                                                          |
|  USE CASE 5: PAYMENT PROCESSING                                          |
|                                                                          |
|  Problem: User double-clicks "Pay" button. Two requests arrive.          |
|           Must ensure payment is processed exactly once.                 |
|  Solution: Lock "payment:order:67890" with idempotency key.              |
|            First request processes; second sees lock and returns         |
|            the result of the first.                                      |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 15. Martin Kleppmann's Critique of Redlock

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KLEPPMANN'S ARGUMENT (2016)                                            |
|  "How to do distributed locking"                                        |
|                                                                         |
|  KEY POINTS:                                                            |
|                                                                         |
|  1. If you need the lock for EFFICIENCY (avoid duplicate work):         |
|     - A single Redis instance with SET NX EX is sufficient              |
|     - Occasional double-locking is acceptable                           |
|     - Redlock's complexity is overkill                                  |
|                                                                         |
|  2. If you need the lock for CORRECTNESS (prevent data corruption):     |
|     - Redlock is NOT safe enough                                        |
|     - It depends on timing assumptions (bounded clock drift,            |
|       bounded network delay, bounded process pauses)                    |
|     - In an asynchronous system, these assumptions can be violated      |
|     - Use a proper consensus system (ZooKeeper, etcd) instead           |
|                                                                         |
|  3. The GC Pause Attack:                                                |
|     a. Client 1 acquires Redlock                                        |
|     b. Client 1 enters long GC pause                                    |
|     c. Lock expires on all Redis instances                              |
|     d. Client 2 acquires Redlock                                        |
|     e. Client 1 wakes up, still thinks it has the lock                  |
|     f. Both clients act as lock holders --> UNSAFE                      |
|                                                                         |
|  4. Fencing tokens fix this, BUT:                                       |
|     - Redis Redlock has no built-in fencing token mechanism             |
|     - If you implement fencing, you don't need Redlock                  |
|       (the fencing token itself provides the safety)                    |
|                                                                         |
|  ANTIREZ'S RESPONSE:                                                    |
|  - Redlock does provide safety under reasonable timing bounds           |
|  - GC pauses of 30+ seconds are rare in practice                        |
|  - Can add fencing tokens on top of Redlock                             |
|  - The debate is about theoretical vs practical safety                  |
|                                                                         |
|  CONCLUSION:                                                            |
|  - For EFFICIENCY: Use simple Redis lock (good enough)                  |
|  - For CORRECTNESS: Use ZooKeeper/etcd (strong consensus)               |
|  - Redlock sits in an awkward middle ground                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 16. Trade-offs Summary

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KEY TRADE-OFFS IN DISTRIBUTED LOCK DESIGN                              |
|                                                                         |
|  +---------------------------+------------------------------------------+
|  | Trade-off                 | Analysis                                 |
|  +---------------------------+------------------------------------------+
|  | Safety vs Performance     | Consensus-based locks (ZK/etcd) are      |
|  |                           | safer but slower than Redis locks        |
|  +---------------------------+------------------------------------------+
|  | Short TTL vs Long TTL     | Short: faster recovery from crashes      |
|  |                           | Long: fewer false expirations            |
|  +---------------------------+------------------------------------------+
|  | Fairness vs Throughput    | FIFO ordering adds overhead but          |
|  |                           | prevents starvation                      |
|  +---------------------------+------------------------------------------+
|  | Simplicity vs Correctness | Simple Redis lock vs full Redlock        |
|  |                           | vs consensus-based lock                  |
|  +---------------------------+------------------------------------------+
|  | Fine vs Coarse Locking    | Fine: more concurrency, more complexity  |
|  |                           | Coarse: simpler, less concurrency        |
|  +---------------------------+------------------------------------------+
|  | Availability vs Safety    | During partition: serve requests         |
|  |                           | (risk split brain) vs reject requests    |
|  |                           | (maintain safety)                        |
|  +---------------------------+------------------------------------------+
|                                                                         |
+-------------------------------------------------------------------------+
```

### Re-entrancy Implementation

```
+--------------------------------------------------------------------------+
|                                                                          |
|  RE-ENTRANT LOCK DESIGN                                                  |
|                                                                          |
|  Lock metadata:                                                          |
|  {                                                                       |
|    "resource": "order:12345",                                            |
|    "holder": "client-A:thread-7",                                        |
|    "count": 3,            // acquired 3 times by same holder             |
|    "fencing_token": 42,                                                  |
|    "acquired_at": "2024-01-15T10:30:00Z",                                |
|    "ttl": 30                                                             |
|  }                                                                       |
|                                                                          |
|  ACQUIRE:                                                                |
|  - If lock free: create with count=1                                     |
|  - If lock held by SAME holder: increment count                          |
|  - If lock held by DIFFERENT holder: wait or fail                        |
|                                                                          |
|  RELEASE:                                                                |
|  - Decrement count                                                       |
|  - If count reaches 0: actually release the lock                         |
|  - If count > 0: lock still held (inner acquisition)                     |
|                                                                          |
|  USE CASE: Recursive functions that need to acquire                      |
|  the same lock at multiple levels of the call stack.                     |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 17. Interview Q&A

### Q1: What happens if a lock holder crashes without releasing the lock?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  This is why TTL/lease/session mechanisms exist:                        |
|                                                                         |
|  Redis:     Lock key expires after TTL. Other clients can then acquire. |
|             Risk: if TTL is too long, others wait unnecessarily.        |
|                                                                         |
|  ZooKeeper: Ephemeral node is auto-deleted when client session ends.    |
|             Session timeout is configurable (typically 10-30s).         |
|             Other watchers are notified.                                |
|                                                                         |
|  etcd:      Lease expires when keep-alive stops. All keys attached      |
|             to the lease are deleted. Watchers are notified.            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q2: How do you choose between Redis and ZooKeeper for distributed locks?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  Choose Redis if:                                                       |
|  - You need very high throughput (100K+ ops/sec)                        |
|  - Occasional double-locking is acceptable                              |
|  - You already use Redis in your stack                                  |
|  - Lock is for efficiency, not correctness                              |
|                                                                         |
|  Choose ZooKeeper if:                                                   |
|  - Correctness is paramount (financial transactions)                    |
|  - You need FIFO fairness                                               |
|  - You need built-in fencing tokens                                     |
|  - You already run ZooKeeper (Kafka ecosystem)                          |
|                                                                         |
|  Choose etcd if:                                                        |
|  - You are in a Kubernetes environment                                  |
|  - You want strong consistency with simpler operations                  |
|  - You need built-in revision-based fencing                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q3: Explain the Redlock algorithm and its controversy.

```
+--------------------------------------------------------------------------+
|                                                                          |
|  ANSWER:                                                                 |
|                                                                          |
|  Redlock uses N (typically 5) independent Redis instances.               |
|  A lock is acquired by getting majority (3 of 5) within the TTL.         |
|                                                                          |
|  Controversy (Kleppmann vs antirez):                                     |
|  - Kleppmann: Redlock is neither efficient nor correct.                  |
|    For efficiency, single Redis is enough.                               |
|    For correctness, timing assumptions make it unsafe.                   |
|  - antirez: Practical systems have bounded timing.                       |
|    Redlock is safe under reasonable assumptions.                         |
|                                                                          |
|  In practice: Most teams use simple Redis locks for efficiency           |
|  or ZooKeeper/etcd for correctness. Redlock is rarely used.              |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Q4: What is a fencing token and why is it important?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  A fencing token is a monotonically increasing number issued            |
|  with each lock acquisition.                                            |
|                                                                         |
|  Purpose: Detect and reject operations from stale lock holders.         |
|                                                                         |
|  Example: Client A gets token 33, pauses. Lock expires.                 |
|  Client B gets token 34, writes to DB. Client A resumes,                |
|  tries to write with token 33. DB rejects (33 < 34).                    |
|                                                                         |
|  Critical: The storage layer must support fencing token checks.         |
|  Without storage-side enforcement, fencing tokens are useless.          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q5: How do you handle the "long GC pause" problem with distributed locks?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  1. Fencing tokens (primary defense)                                    |
|     - Even if lock expires during GC, stale writes are rejected         |
|                                                                         |
|  2. Short TTL + frequent renewal                                        |
|     - TTL = 5s, renew every 2s                                          |
|     - If GC > 5s, lock expires quickly and others can proceed           |
|                                                                         |
|  3. Check lock validity before critical operations                      |
|     - After GC resume, verify lock is still held before proceeding      |
|     - Race condition still exists (check-then-act is not atomic)        |
|                                                                         |
|  4. Design for idempotency                                              |
|     - Even if double-execution occurs, the result is the same           |
|                                                                         |
|  5. Avoid long-running operations under locks                           |
|     - Break work into smaller chunks, each with its own lock            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q6: How would you implement a distributed read-write lock?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  Using ZooKeeper (most natural):                                        |
|  - Readers create ephemeral sequential nodes: read-NNNN                 |
|  - Writers create ephemeral sequential nodes: write-NNNN                |
|                                                                         |
|  Read lock acquired if: no write node with lower sequence exists        |
|  Write lock acquired if: it is the lowest sequence node overall         |
|                                                                         |
|  Allows concurrent readers while writers get exclusive access.          |
|                                                                         |
|  Using Redis:                                                           |
|  - Use a counter for readers: INCR readers_count                        |
|  - Writer checks: if readers_count == 0 AND no writer lock              |
|  - More complex and less safe than ZooKeeper approach                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q7: What is the "herd effect" and how do ZooKeeper locks avoid it?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  Herd effect (thundering herd): When a lock is released, ALL            |
|  waiting clients wake up and compete for it. Only one wins;             |
|  the rest wasted CPU/network resources.                                 |
|                                                                         |
|  ZooKeeper's solution: Each waiter watches ONLY the node                |
|  immediately before it in the queue (not all nodes).                    |
|                                                                         |
|  When a lock is released:                                               |
|  - Only the NEXT waiter is notified                                     |
|  - It checks if it is now the lowest -> acquires lock                   |
|  - Other waiters are not disturbed                                      |
|  - O(1) notifications instead of O(n)                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q8: How would you handle lock service unavailability?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  1. Retry with exponential backoff + jitter                             |
|     - Don't hammer the lock service when it's struggling                |
|                                                                         |
|  2. Circuit breaker pattern                                             |
|     - After N failures, stop trying for a cooldown period               |
|     - Fall back to degraded mode                                        |
|                                                                         |
|  3. Graceful degradation                                                |
|     - If lock service is down for efficiency locks: proceed without     |
|       locking (accept some duplicate work)                              |
|     - If lock service is down for correctness locks: reject the         |
|       operation and return error to the caller                          |
|                                                                         |
|  4. Multi-lock-service setup                                            |
|     - Primary: ZooKeeper cluster                                        |
|     - Fallback: Redis-based locks (weaker guarantees but available)     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q9: How do you test a distributed lock implementation?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  1. Unit tests: Verify lock/unlock semantics, re-entrancy, TTL          |
|                                                                         |
|  2. Concurrency tests: Launch 100 threads/processes all trying to       |
|     acquire the same lock. Verify only one succeeds at a time.          |
|     Use a shared counter and verify no data races.                      |
|                                                                         |
|  3. Failure injection (Chaos testing):                                  |
|     - Kill the lock holder mid-operation                                |
|     - Partition the network (e.g., using iptables)                      |
|     - Introduce clock skew (e.g., using libfaketime)                    |
|     - Inject GC pauses (e.g., send SIGSTOP/SIGCONT)                     |
|                                                                         |
|  4. Jepsen testing:                                                     |
|     - Kyle Kingsbury's framework for testing distributed systems        |
|     - Specifically designed to find safety violations                   |
|     - Has tested Redlock, etcd, ZooKeeper                               |
|                                                                         |
|  5. Load testing: Verify performance under high contention              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q10: Compare optimistic locking vs distributed locks.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  OPTIMISTIC LOCKING (CAS / Compare-And-Swap):                           |
|  - Read value + version -> compute -> write if version unchanged        |
|  - No actual lock held; retry on conflict                               |
|  - Higher throughput when conflicts are rare                            |
|  - Lower throughput when conflicts are frequent (many retries)          |
|  - Example: UPDATE inventory SET qty=4, version=6                       |
|             WHERE id=123 AND version=5                                  |
|                                                                         |
|  DISTRIBUTED LOCKS (Pessimistic):                                       |
|  - Acquire lock -> do work -> release lock                              |
|  - Blocks other clients; no retries needed                              |
|  - Lower throughput when conflicts are rare (lock overhead)             |
|  - Predictable throughput when conflicts are frequent                   |
|  - Better for long-running operations                                   |
|                                                                         |
|  RULE OF THUMB:                                                         |
|  - Low contention -> Optimistic locking                                 |
|  - High contention -> Distributed locks                                 |
|  - Short operations -> Optimistic locking                               |
|  - Long operations -> Distributed locks                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q11: How would you design a lock service that works across multiple data centers?

```
+--------------------------------------------------------------------------+
|                                                                          |
|  ANSWER:                                                                 |
|                                                                          |
|  Option 1: Single global lock cluster (e.g., etcd across 3 DCs)          |
|  - Raft consensus across DCs                                             |
|  - Latency: 50-200ms per lock op (cross-DC round trips)                  |
|  - Strongest safety                                                      |
|                                                                          |
|  Option 2: Per-DC lock clusters with global coordination                 |
|  - Local locks are fast (~1ms)                                           |
|  - Global locks require cross-DC consensus                               |
|  - Complexity: must handle split brain between DCs                       |
|                                                                          |
|  Option 3: Hierarchical locking                                          |
|  - Local lock service per DC                                             |
|  - Global lock service for cross-DC resources                            |
|  - Acquire local lock first, then global lock                            |
|                                                                          |
|  Key consideration: Most locks are DC-local. Only cross-DC               |
|  resources need the expensive global consensus path.                     |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Q12: What metrics would you monitor for a distributed lock service?

```
+--------------------------------------------------------------------------+
|                                                                          |
|  ANSWER:                                                                 |
|                                                                          |
|  HEALTH METRICS:                                                         |
|  - Lock acquisition latency (p50, p95, p99)                              |
|  - Lock acquisition failure rate                                         |
|  - Lock wait time (time spent queued before acquiring)                   |
|  - Active locks count                                                    |
|  - Lock hold duration distribution                                       |
|                                                                          |
|  SAFETY METRICS:                                                         |
|  - TTL expiration rate (may indicate holders too slow)                   |
|  - Fencing token rejections (stale holders detected)                     |
|  - Double-acquisition detections (safety violation!)                     |
|                                                                          |
|  OPERATIONAL METRICS:                                                    |
|  - Lock service node health (CPU, memory, network)                       |
|  - Replication lag (for consensus-based systems)                         |
|  - Client connection count                                               |
|  - Lock churn rate (acquires + releases per second)                      |
|                                                                          |
|  ALERTS:                                                                 |
|  - Lock acquisition latency > 100ms (p99)                                |
|  - Lock service node down                                                |
|  - TTL expiration rate spikes (something is slow)                        |
|  - Any fencing token rejection (investigate immediately)                 |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## Quick Reference Card

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DISTRIBUTED LOCK QUICK REFERENCE                                       |
|                                                                         |
|  SAFETY PROPERTY:   At most one holder at a time                        |
|  LIVENESS PROPERTY: Lock is always eventually released                  |
|                                                                         |
|  REDIS LOCK:        SET key value NX EX ttl                             |
|  REDLOCK:           Majority of N independent Redis instances           |
|  ZK LOCK:           Ephemeral sequential nodes + watches                |
|  ETCD LOCK:         Lease + compare-and-swap + watch                    |
|                                                                         |
|  FENCING TOKEN:     Monotonic counter to reject stale operations        |
|  RE-ENTRANCY:       Same holder can re-acquire; track count             |
|  FAIRNESS:          FIFO queue (ZK/etcd); not built into Redis          |
|                                                                         |
|  FOR EFFICIENCY:    Simple Redis lock is sufficient                     |
|  FOR CORRECTNESS:   Use ZooKeeper or etcd (consensus-based)             |
|                                                                         |
|  ALWAYS:            Use TTL, use fencing tokens, handle failures        |
|  NEVER:             Assume clocks are perfectly synchronized            |
|  NEVER:             Assume GC pauses won't happen                       |
|  NEVER:             Assume the network is reliable                      |
|                                                                         |
+-------------------------------------------------------------------------+
```
