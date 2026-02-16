# CHAPTER 21: DISTRIBUTED CONCURRENCY CONTROL
*Coordination and Locking in Distributed Systems*

In distributed systems, multiple nodes may try to access shared resources
simultaneously. This chapter covers patterns for safe coordination.

## SECTION 21.1: THE PROBLEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY DISTRIBUTED CONCURRENCY IS HARD                                   |
|                                                                         |
|  SINGLE MACHINE:                                                        |
|  -----------------                                                       |
|  mutex.lock()           // OS guarantees exclusivity                   |
|  critical_section()                                                     |
|  mutex.unlock()                                                         |
|                                                                         |
|  DISTRIBUTED SYSTEM:                                                    |
|  --------------------                                                    |
|  * No shared memory                                                     |
|  * Network can fail/delay                                               |
|  * Clocks are not synchronized                                         |
|  * Nodes can crash                                                      |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |  Server A                    Server B                          |   |
|  |     |                           |                               |   |
|  |     |---- "acquire lock" ------>| Lock Server                  |   |
|  |     |                           | (crashes!)                    |   |
|  |     |     (no response...)      |                               |   |
|  |     |                           |                               |   |
|  |     |  Did I get the lock?                                  |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  SCENARIOS REQUIRING DISTRIBUTED LOCKS:                                |
|  * Only one server should process a payment                           |
|  * Only one pod should run a cron job                                 |
|  * Only one instance should update a resource                         |
|  * Leader election                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 21.2: DISTRIBUTED LOCKING WITH REDIS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REDIS SETNX (SET if Not eXists)                                       |
|                                                                         |
|  Basic atomic operation for locking:                                   |
|                                                                         |
|  SET lock_key unique_value NX PX 30000                                |
|      |         |           |  |                                         |
|      |         |           |  +-- Expire in 30 seconds (auto-release) |
|      |         |           +-- Only set if NOT exists                  |
|      |         +-- Unique value (UUID) to identify lock owner          |
|      +-- Key name (e.g., "lock:order:123")                             |
|                                                                         |
|  Returns OK if lock acquired, nil if already held                     |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  ACQUIRE LOCK:                                                          |
|                                                                         |
|  def acquire_lock(lock_key, ttl_ms=30000):                             |
|      lock_value = str(uuid.uuid4())  # Unique per attempt              |
|      result = redis.set(                                                |
|          lock_key,                                                      |
|          lock_value,                                                    |
|          nx=True,      # Only if not exists                            |
|          px=ttl_ms     # Auto-expire                                   |
|      )                                                                   |
|      if result:                                                         |
|          return lock_value  # Success - save this!                     |
|      return None             # Failed - someone else has it            |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  RELEASE LOCK (MUST CHECK OWNERSHIP):                                  |
|                                                                         |
|  X WRONG - May release someone else's lock:                           |
|    redis.delete(lock_key)                                               |
|                                                                         |
|  Y CORRECT - Lua script for atomic check-and-delete:                  |
|                                                                         |
|  RELEASE_SCRIPT = """                                                   |
|  if redis.call("GET", KEYS[1]) == ARGV[1] then                         |
|      return redis.call("DEL", KEYS[1])                                  |
|  else                                                                    |
|      return 0                                                            |
|  end                                                                     |
|  """                                                                     |
|                                                                         |
|  def release_lock(lock_key, lock_value):                               |
|      return redis.eval(RELEASE_SCRIPT, 1, lock_key, lock_value)        |
|                                                                         |
|  WHY LUA? Get + compare + delete must be ATOMIC                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### LOCK TTL AND THE SAFETY PROBLEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE TTL DILEMMA                                                        |
|                                                                         |
|  TTL too short:                                                         |
|  +-----------------------------------------------------------------+   |
|  |  Client A acquires lock (TTL=5s)                                |   |
|  |       |                                                          |   |
|  |       +---- starts work...                                      |   |
|  |       |     (GC pause / slow network)                           |   |
|  |       |                                                          |   |
|  |  [5 seconds pass - LOCK EXPIRES]                                |   |
|  |                                                                  |   |
|  |  Client B acquires lock Y                                       |   |
|  |       |                                                          |   |
|  |       +---- starts work...                                      |   |
|  |       |                                                          |   |
|  |  Client A resumes (thinks it still has lock!)                   |   |
|  |       |                                                          |   |
|  |       +---- modifies resource X CONFLICT!                       |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  TTL too long:                                                          |
|  * Client crashes > lock held until TTL expires                       |
|  * Other clients blocked unnecessarily                                |
|                                                                         |
|  SOLUTIONS:                                                             |
|  1. Lock renewal (extend TTL while working)                           |
|  2. Fencing tokens (see below)                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 21.3: FENCING TOKENS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FENCING TOKENS - THE DEFINITIVE SOLUTION                              |
|                                                                         |
|  Problem: Lock can expire while client thinks it owns it              |
|  Solution: Include monotonically increasing token with every write    |
|                                                                         |
|  HOW IT WORKS:                                                          |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |  Lock Server assigns incrementing token with each lock:        |   |
|  |                                                                 |   |
|  |  Client A acquires lock > token = 33                           |   |
|  |  Client A pauses (GC)                                          |   |
|  |  Lock expires                                                  |   |
|  |  Client B acquires lock > token = 34                           |   |
|  |  Client B writes to storage: "value=X, token=34"               |   |
|  |  Client A resumes, tries to write: "value=Y, token=33"         |   |
|  |                                                                 |   |
|  |  Storage: "33 < 34? REJECT!" X                                 |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  IMPLEMENTATION:                                                        |
|                                                                         |
|  Lock Service:                                                          |
|  +---------------------------------------------------------------+     |
|  | def acquire_lock_with_token(lock_key):                         |     |
|  |     token = redis.incr("lock_token_counter")  # Atomic incr   |     |
|  |     acquired = redis.set(lock_key, token, nx=True, px=30000)  |     |
|  |     if acquired:                                               |     |
|  |         return token                                           |     |
|  |     return None                                                 |     |
|  +---------------------------------------------------------------+     |
|                                                                         |
|  Storage/Database:                                                      |
|  +---------------------------------------------------------------+     |
|  | def write(key, value, fence_token):                            |     |
|  |     current_token = get_token_for_key(key)                     |     |
|  |     if fence_token < current_token:                            |     |
|  |         raise StaleTokenError("Rejected: old token")          |     |
|  |     save(key, value, fence_token)                              |     |
|  +---------------------------------------------------------------+     |
|                                                                         |
|  REQUIREMENT: Storage must support token comparison                   |
|  (Not all systems do - may need application-level check)              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 21.4: REDLOCK ALGORITHM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SINGLE REDIS = SINGLE POINT OF FAILURE                                |
|                                                                         |
|  If Redis master crashes, lock is lost.                                |
|  Redis replication is asynchronous - failover may lose lock.          |
|                                                                         |
|  REDLOCK: Lock across N independent Redis instances (N=5 recommended) |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |              Client wants to acquire lock                      |   |
|  |                         |                                       |   |
|  |      +------------------+------------------+                   |   |
|  |      v          v       v       v          v                   |   |
|  |  +-------+ +-------+ +-------+ +-------+ +-------+           |   |
|  |  |Redis 1| |Redis 2| |Redis 3| |Redis 4| |Redis 5|           |   |
|  |  |  Y    | |  Y    | |  Y    | |  X    | |  Y    |           |   |
|  |  +-------+ +-------+ +-------+ +-------+ +-------+           |   |
|  |                                                                 |   |
|  |  Got 4/5 = majority > LOCK ACQUIRED Y                         |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  REDLOCK ALGORITHM:                                                     |
|                                                                         |
|  1. Get current time (T1)                                              |
|                                                                         |
|  2. Try to acquire lock on ALL N Redis instances sequentially         |
|     * Same key, same random value, same TTL                           |
|     * Small timeout per instance (few ms)                             |
|                                                                         |
|  3. Get current time (T2)                                              |
|     Calculate: elapsed = T2 - T1                                      |
|     Calculate: validity = TTL - elapsed                               |
|                                                                         |
|  4. Lock acquired IF:                                                   |
|     * Got lock on majority (N/2 + 1) instances                        |
|     * validity > 0 (still time left)                                  |
|                                                                         |
|  5. If failed: Release lock on ALL instances                          |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  REDLOCK CONTROVERSY (Martin Kleppmann's Critique):                   |
|                                                                         |
|  * Clock drift between nodes can break safety                         |
|  * GC pauses can still cause issues                                   |
|  * Adds complexity without solving fundamental problems               |
|                                                                         |
|  RECOMMENDATION:                                                        |
|  * For efficiency (prevent duplicate work): Single Redis is fine      |
|  * For correctness (critical data): Use fencing tokens OR             |
|    consensus systems (ZooKeeper, etcd)                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 21.5: CONSENSUS-BASED LOCKING (ZOOKEEPER/ETCD)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ZOOKEEPER DISTRIBUTED LOCKS                                           |
|                                                                         |
|  ZooKeeper uses Zab consensus protocol - stronger guarantees          |
|                                                                         |
|  EPHEMERAL NODES:                                                       |
|  * Node is deleted when client session ends                           |
|  * Client crash > session timeout > lock auto-released               |
|                                                                         |
|  SEQUENTIAL NODES:                                                      |
|  * ZooKeeper appends incrementing number to node name                 |
|  * Built-in ordering for fair queuing                                 |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |  /locks/my-resource/                                           |   |
|  |      +-- lock-0000000001  (Client A) < Holds lock              |   |
|  |      +-- lock-0000000002  (Client B) < Waiting                 |   |
|  |      +-- lock-0000000003  (Client C) < Waiting                 |   |
|  |                                                                 |   |
|  |  Client B watches lock-0000000001                              |   |
|  |  When it's deleted > Client B gets lock                        |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  ALGORITHM:                                                             |
|  1. Create ephemeral sequential node under /locks/resource/           |
|  2. Get all children, sort by sequence number                         |
|  3. If my node is lowest > I have the lock                           |
|  4. Else > Watch the node just before mine                           |
|  5. When notified > Go to step 2                                      |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  ETCD DISTRIBUTED LOCKS                                                |
|                                                                         |
|  etcd uses Raft consensus - similar guarantees to ZooKeeper           |
|                                                                         |
|  LEASE-BASED LOCKING:                                                   |
|  * Create a lease (like TTL)                                          |
|  * Attach key to lease                                                 |
|  * Keep-alive to refresh lease                                        |
|  * Lease expires > key deleted > lock released                       |
|                                                                         |
|  # Using etcd's built-in lock                                          |
|  etcdctl lock my-lock-name                                              |
|  # Lock acquired, runs until process exits                            |
|                                                                         |
|  # Programmatic                                                         |
|  lease = client.lease(ttl=30)                                          |
|  client.put('/locks/my-resource', 'owner-id', lease=lease)            |
|  lease.refresh()  # Call periodically to keep lock                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 21.6: LEADER ELECTION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LEADER ELECTION = SPECIAL CASE OF DISTRIBUTED LOCKING                |
|                                                                         |
|  Only ONE node should be "leader" at a time (active-passive)          |
|                                                                         |
|  USE CASES:                                                             |
|  * Job scheduler (only leader schedules jobs)                         |
|  * Database master (only leader accepts writes)                       |
|  * Cron runner (only leader runs cron tasks)                          |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |  +---------+  +---------+  +---------+                        |   |
|  |  | Node A  |  | Node B  |  | Node C  |                        |   |
|  |  | LEADER  |  | follower|  | follower|                        |   |
|  |  |   *     |  |         |  |         |                        |   |
|  |  +----+----+  +----+----+  +----+----+                        |   |
|  |       |            |            |                               |   |
|  |       +------------+------------+                               |   |
|  |                    |                                             |   |
|  |            +-------v-------+                                    |   |
|  |            |   ZooKeeper/  |                                    |   |
|  |            |     etcd      |                                    |   |
|  |            +---------------+                                    |   |
|  |                                                                 |   |
|  |  All nodes try to acquire leadership                          |   |
|  |  Only one succeeds > becomes leader                           |   |
|  |  Leader fails > another takes over                            |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  KUBERNETES LEADER ELECTION:                                           |
|                                                                         |
|  Uses ConfigMap or Lease object for coordination:                     |
|                                                                         |
|  apiVersion: coordination.k8s.io/v1                                    |
|  kind: Lease                                                            |
|  metadata:                                                              |
|    name: my-app-leader                                                  |
|  spec:                                                                  |
|    holderIdentity: "pod-abc123"                                        |
|    leaseDurationSeconds: 15                                            |
|    renewTime: "2024-01-15T10:30:00Z"                                   |
|                                                                         |
|  client-go provides leader election library:                          |
|  * Pods compete for Lease ownership                                   |
|  * Leader renews lease periodically                                   |
|  * If leader fails to renew > another pod takes over                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 21.7: COMPARISON AND DECISION GUIDE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DISTRIBUTED LOCKING OPTIONS                                           |
|                                                                         |
|  +----------------+-------------------------------------------------+  |
|  | Approach       | When to Use                                     |  |
|  +----------------+-------------------------------------------------+  |
|  | Redis SETNX    | Simple cases, efficiency lock (not safety)     |  |
|  |                | Already have Redis, low latency needed         |  |
|  +----------------+-------------------------------------------------+  |
|  | Redlock        | Need higher availability than single Redis     |  |
|  |                | Willing to accept complexity                   |  |
|  +----------------+-------------------------------------------------+  |
|  | ZooKeeper      | Need strong correctness guarantees             |  |
|  |                | Already have ZK (Kafka, Hadoop ecosystem)      |  |
|  +----------------+-------------------------------------------------+  |
|  | etcd           | Kubernetes environments                        |  |
|  |                | Need strong consistency                        |  |
|  +----------------+-------------------------------------------------+  |
|  | Database Lock  | Simple cases, no extra infrastructure          |  |
|  |                | SELECT FOR UPDATE or advisory locks            |  |
|  +----------------+-------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  TWO TYPES OF LOCKS (Martin Kleppmann):                               |
|                                                                         |
|  1. EFFICIENCY LOCK                                                     |
|     Purpose: Avoid duplicate work (e.g., double-sending email)        |
|     Consequence of failure: Wasted work, minor inconvenience          |
|     Solution: Simple Redis lock is fine                               |
|                                                                         |
|  2. CORRECTNESS LOCK                                                    |
|     Purpose: Prevent data corruption (e.g., double-charging)          |
|     Consequence of failure: Data loss, financial loss                 |
|     Solution: Consensus system + fencing tokens                       |
|                                                                         |
|  ====================================================================  |
|                                                                         |
|  INTERVIEW ANSWER FRAMEWORK:                                           |
|                                                                         |
|  "For distributed locking, I'd consider:                              |
|                                                                         |
|   1. Is this for efficiency or correctness?                           |
|      - Efficiency: Redis SETNX with TTL                               |
|      - Correctness: Add fencing tokens                                |
|                                                                         |
|   2. What infrastructure do we have?                                  |
|      - Already have Redis > use Redis                                 |
|      - Kubernetes > use etcd/Lease                                    |
|      - Need strong guarantees > ZooKeeper/etcd                       |
|                                                                         |
|   3. Always implement:                                                 |
|      - TTL for auto-release                                           |
|      - Unique owner ID (prevent wrong release)                        |
|      - Retry with backoff                                             |
|      - Fencing tokens for critical operations"                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 21.8: QUICK REFERENCE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DISTRIBUTED CONCURRENCY CONTROL - CHEAT SHEET                        |
|                                                                         |
|  REDIS SETNX PATTERN:                                                   |
|  ----------------------                                                  |
|  Acquire: SET lock:key uuid NX PX 30000                               |
|  Release: Lua script (check owner before delete)                      |
|  Risk: Lock expires while holding > use fencing tokens               |
|                                                                         |
|  FENCING TOKEN:                                                         |
|  ----------------                                                        |
|  Lock server returns incrementing token                               |
|  Storage rejects writes with stale tokens                             |
|  Solves: "zombie lock holder" problem                                 |
|                                                                         |
|  REDLOCK:                                                               |
|  --------                                                                |
|  Lock across N (5) independent Redis instances                        |
|  Need majority (3) to acquire                                         |
|  Controversial - use for efficiency, not correctness                  |
|                                                                         |
|  ZOOKEEPER/ETCD:                                                        |
|  ----------------                                                        |
|  Consensus-based, stronger guarantees                                 |
|  Ephemeral nodes (ZK) / Leases (etcd)                                 |
|  Use for correctness-critical locks                                   |
|                                                                         |
|  LEADER ELECTION:                                                       |
|  -----------------                                                       |
|  Special case of distributed lock                                     |
|  Only one leader at a time                                            |
|  K8s: Use Lease object + client-go library                           |
|                                                                         |
|  ====================================================================  |
|                                                                         |
|  KEY TAKEAWAYS:                                                         |
|                                                                         |
|  * No perfect distributed lock exists                                 |
|  * Always use TTL (prevent deadlocks)                                 |
|  * Use unique owner ID (prevent wrong release)                        |
|  * Fencing tokens for correctness                                     |
|  * Choose based on: efficiency vs correctness requirement             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 21

