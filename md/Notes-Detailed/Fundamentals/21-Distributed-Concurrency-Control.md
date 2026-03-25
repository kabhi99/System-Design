# CHAPTER 21: DISTRIBUTED CONCURRENCY CONTROL
*Coordination and Locking in Distributed Systems*

In distributed systems, multiple nodes may try to access shared resources
simultaneously. This chapter covers patterns for safe coordination.

## SECTION 21.1: THE PROBLEM

```
+--------------------------------------------------------------------------+
|                                                                          |
|  WHY DISTRIBUTED CONCURRENCY IS HARD                                     |
|                                                                          |
|  SINGLE MACHINE:                                                         |
|  -----------------                                                       |
|  mutex.lock()           // OS guarantees exclusivity                     |
|  critical_section()                                                      |
|  mutex.unlock()                                                          |
|                                                                          |
|  DISTRIBUTED SYSTEM:                                                     |
|  --------------------                                                    |
|  * No shared memory                                                      |
|  * Network can fail/delay                                                |
|  * Clocks are not synchronized                                           |
|  * Nodes can crash                                                       |
|                                                                          |
|  +-------------------------------------------------------------------+   |
|  |                                                                   |   |
|  |  Server A                    Server B                             |   |
|  |     |                           |                                 |   |
|  |     |---- "acquire lock" ------>| Lock Server                     |   |
|  |     |                           | (crashes!)                      |   |
|  |     |     (no response...)      |                                 |   |
|  |     |                           |                                 |   |
|  |     |  Did I get the lock?                                        |   |
|  |                                                                   |   |
|  +-------------------------------------------------------------------+   |
|                                                                          |
|  SCENARIOS REQUIRING DISTRIBUTED LOCKS:                                  |
|  * Only one server should process a payment                              |
|  * Only one pod should run a cron job                                    |
|  * Only one instance should update a resource                            |
|  * Leader election                                                       |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 21.2: DISTRIBUTED LOCKING WITH REDIS

```
+--------------------------------------------------------------------------+
|                                                                          |
|  REDIS SETNX (SET if Not eXists)                                         |
|                                                                          |
|  Basic atomic operation for locking:                                     |
|                                                                          |
|  SET lock_key unique_value NX PX 30000                                   |
|      |         |           |  |                                          |
|      |         |           |  +-- Expire in 30 seconds (auto-release)    |
|      |         |           +-- Only set if NOT exists                    |
|      |         +-- Unique value (UUID) to identify lock owner            |
|      +-- Key name (e.g., "lock:order:123")                               |
|                                                                          |
|  Returns OK if lock acquired, nil if already held                        |
|                                                                          |
+--------------------------------------------------------------------------+
|                                                                          |
|  ACQUIRE LOCK:                                                           |
|                                                                          |
|  def acquire_lock(lock_key, ttl_ms=30000):                               |
|      lock_value = str(uuid.uuid4())  # Unique per attempt                |
|      result = redis.set(                                                 |
|          lock_key,                                                       |
|          lock_value,                                                     |
|          nx=True,      # Only if not exists                              |
|          px=ttl_ms     # Auto-expire                                     |
|      )                                                                   |
|      if result:                                                          |
|          return lock_value  # Success - save this!                       |
|      return None             # Failed - someone else has it              |
|                                                                          |
+--------------------------------------------------------------------------+
|                                                                          |
|  RELEASE LOCK (MUST CHECK OWNERSHIP):                                    |
|                                                                          |
|  X WRONG - May release someone else's lock:                              |
|    redis.delete(lock_key)                                                |
|                                                                          |
|  Y CORRECT - Lua script for atomic check-and-delete:                     |
|                                                                          |
|  RELEASE_SCRIPT = """                                                    |
|  if redis.call("GET", KEYS[1]) == ARGV[1] then                           |
|      return redis.call("DEL", KEYS[1])                                   |
|  else                                                                    |
|      return 0                                                            |
|  end                                                                     |
|  """                                                                     |
|                                                                          |
|  def release_lock(lock_key, lock_value):                                 |
|      return redis.eval(RELEASE_SCRIPT, 1, lock_key, lock_value)          |
|                                                                          |
|  WHY LUA? Get + compare + delete must be ATOMIC                          |
|                                                                          |
+--------------------------------------------------------------------------+
```

### LOCK TTL AND THE SAFETY PROBLEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE TTL DILEMMA                                                        |
|                                                                         |
|  TTL too short:                                                         |
|  +------------------------------------------------------------------+   |
|  |  Client A acquires lock (TTL=5s)                                 |   |
|  |       |                                                          |   |
|  |       +---- starts work...                                       |   |
|  |       |     (GC pause / slow network)                            |   |
|  |       |                                                          |   |
|  |  [5 seconds pass - LOCK EXPIRES]                                 |   |
|  |                                                                  |   |
|  |  Client B acquires lock Y                                        |   |
|  |       |                                                          |   |
|  |       +---- starts work...                                       |   |
|  |       |                                                          |   |
|  |  Client A resumes (thinks it still has lock!)                    |   |
|  |       |                                                          |   |
|  |       +---- modifies resource X CONFLICT!                        |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  TTL too long:                                                          |
|  * Client crashes > lock held until TTL expires                         |
|  * Other clients blocked unnecessarily                                  |
|                                                                         |
|  SOLUTIONS:                                                             |
|  1. Lock renewal (extend TTL while working)                             |
|  2. Fencing tokens (see below)                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 21.3: FENCING TOKENS

```
+--------------------------------------------------------------------------+
|                                                                          |
|  FENCING TOKENS - THE DEFINITIVE SOLUTION                                |
|                                                                          |
|  Problem: Lock can expire while client thinks it owns it                 |
|  Solution: Include monotonically increasing token with every write       |
|                                                                          |
|  HOW IT WORKS:                                                           |
|                                                                          |
|  +-------------------------------------------------------------------+   |
|  |                                                                   |   |
|  |  Lock Server assigns incrementing token with each lock:           |   |
|  |                                                                   |   |
|  |  Client A acquires lock > token = 33                              |   |
|  |  Client A pauses (GC)                                             |   |
|  |  Lock expires                                                     |   |
|  |  Client B acquires lock > token = 34                              |   |
|  |  Client B writes to storage: "value=X, token=34"                  |   |
|  |  Client A resumes, tries to write: "value=Y, token=33"            |   |
|  |                                                                   |   |
|  |  Storage: "33 < 34? REJECT!" X                                    |   |
|  |                                                                   |   |
|  +-------------------------------------------------------------------+   |
|                                                                          |
|  IMPLEMENTATION:                                                         |
|                                                                          |
|  Lock Service:                                                           |
|  +---------------------------------------------------------------+       |
|  | def acquire_lock_with_token(lock_key):                         |      |
|  |     token = redis.incr("lock_token_counter")  # Atomic incr   |       |
|  |     acquired = redis.set(lock_key, token, nx=True, px=30000)  |       |
|  |     if acquired:                                               |      |
|  |         return token                                           |      |
|  |     return None                                                 |     |
|  +---------------------------------------------------------------+       |
|                                                                          |
|  Storage/Database:                                                       |
|  +---------------------------------------------------------------+       |
|  | def write(key, value, fence_token):                            |      |
|  |     current_token = get_token_for_key(key)                     |      |
|  |     if fence_token < current_token:                            |      |
|  |         raise StaleTokenError("Rejected: old token")          |       |
|  |     save(key, value, fence_token)                              |      |
|  +---------------------------------------------------------------+       |
|                                                                          |
|  REQUIREMENT: Storage must support token comparison                      |
|  (Not all systems do - may need application-level check)                 |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 21.4: REDLOCK ALGORITHM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SINGLE REDIS = SINGLE POINT OF FAILURE                                 |
|                                                                         |
|  If Redis master crashes, lock is lost.                                 |
|  Redis replication is asynchronous - failover may lose lock.            |
|                                                                         |
|  REDLOCK: Lock across N independent Redis instances (N=5 recommended)   |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |              Client wants to acquire lock                        |   |
|  |                         |                                        |   |
|  |      +------------------+------------------+                     |   |
|  |      v          v       v       v          v                     |   |
|  |  +-------+ +-------+ +-------+ +-------+ +-------+               |   |
|  |  |Redis 1| |Redis 2| |Redis 3| |Redis 4| |Redis 5|               |   |
|  |  |  Y    | |  Y    | |  Y    | |  X    | |  Y    |               |   |
|  |  +-------+ +-------+ +-------+ +-------+ +-------+               |   |
|  |                                                                  |   |
|  |  Got 4/5 = majority > LOCK ACQUIRED Y                            |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  REDLOCK ALGORITHM:                                                     |
|                                                                         |
|  1. Get current time (T1)                                               |
|                                                                         |
|  2. Try to acquire lock on ALL N Redis instances sequentially           |
|     * Same key, same random value, same TTL                             |
|     * Small timeout per instance (few ms)                               |
|                                                                         |
|  3. Get current time (T2)                                               |
|     Calculate: elapsed = T2 - T1                                        |
|     Calculate: validity = TTL - elapsed                                 |
|                                                                         |
|  4. Lock acquired IF:                                                   |
|     * Got lock on majority (N/2 + 1) instances                          |
|     * validity > 0 (still time left)                                    |
|                                                                         |
|  5. If failed: Release lock on ALL instances                            |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  REDLOCK CONTROVERSY (Martin Kleppmann's Critique):                     |
|                                                                         |
|  * Clock drift between nodes can break safety                           |
|  * GC pauses can still cause issues                                     |
|  * Adds complexity without solving fundamental problems                 |
|                                                                         |
|  RECOMMENDATION:                                                        |
|  * For efficiency (prevent duplicate work): Single Redis is fine        |
|  * For correctness (critical data): Use fencing tokens OR               |
|    consensus systems (ZooKeeper, etcd)                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 21.5: CONSENSUS-BASED LOCKING (ZOOKEEPER/ETCD)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ZOOKEEPER DISTRIBUTED LOCKS                                            |
|                                                                         |
|  ZooKeeper uses Zab consensus protocol - stronger guarantees            |
|                                                                         |
|  EPHEMERAL NODES:                                                       |
|  * Node is deleted when client session ends                             |
|  * Client crash > session timeout > lock auto-released                  |
|                                                                         |
|  SEQUENTIAL NODES:                                                      |
|  * ZooKeeper appends incrementing number to node name                   |
|  * Built-in ordering for fair queuing                                   |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |  /locks/my-resource/                                             |   |
|  |      +-- lock-0000000001  (Client A) < Holds lock                |   |
|  |      +-- lock-0000000002  (Client B) < Waiting                   |   |
|  |      +-- lock-0000000003  (Client C) < Waiting                   |   |
|  |                                                                  |   |
|  |  Client B watches lock-0000000001                                |   |
|  |  When it's deleted > Client B gets lock                          |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  ALGORITHM:                                                             |
|  1. Create ephemeral sequential node under /locks/resource/             |
|  2. Get all children, sort by sequence number                           |
|  3. If my node is lowest > I have the lock                              |
|  4. Else > Watch the node just before mine                              |
|  5. When notified > Go to step 2                                        |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  ETCD DISTRIBUTED LOCKS                                                 |
|                                                                         |
|  etcd uses Raft consensus - similar guarantees to ZooKeeper             |
|                                                                         |
|  LEASE-BASED LOCKING:                                                   |
|  * Create a lease (like TTL)                                            |
|  * Attach key to lease                                                  |
|  * Keep-alive to refresh lease                                          |
|  * Lease expires > key deleted > lock released                          |
|                                                                         |
|  # Using etcd's built-in lock                                           |
|  etcdctl lock my-lock-name                                              |
|  # Lock acquired, runs until process exits                              |
|                                                                         |
|  # Programmatic                                                         |
|  lease = client.lease(ttl=30)                                           |
|  client.put('/locks/my-resource', 'owner-id', lease=lease)              |
|  lease.refresh()  # Call periodically to keep lock                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 21.6: LEADER ELECTION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LEADER ELECTION = SPECIAL CASE OF DISTRIBUTED LOCKING                  |
|                                                                         |
|  Only ONE node should be "leader" at a time (active-passive)            |
|                                                                         |
|  USE CASES:                                                             |
|  * Job scheduler (only leader schedules jobs)                           |
|  * Database master (only leader accepts writes)                         |
|  * Cron runner (only leader runs cron tasks)                            |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |  +---------+  +---------+  +---------+                           |   |
|  |  | Node A  |  | Node B  |  | Node C  |                           |   |
|  |  | LEADER  |  | follower|  | follower|                           |   |
|  |  |   *     |  |         |  |         |                           |   |
|  |  +----+----+  +----+----+  +----+----+                           |   |
|  |       |            |            |                                |   |
|  |       +------------+------------+                                |   |
|  |                    |                                             |   |
|  |            +-------v-------+                                     |   |
|  |            |   ZooKeeper/  |                                     |   |
|  |            |     etcd      |                                     |   |
|  |            +---------------+                                     |   |
|  |                                                                  |   |
|  |  All nodes try to acquire leadership                             |   |
|  |  Only one succeeds > becomes leader                              |   |
|  |  Leader fails > another takes over                               |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  KUBERNETES LEADER ELECTION:                                            |
|                                                                         |
|  Uses ConfigMap or Lease object for coordination:                       |
|                                                                         |
|  apiVersion: coordination.k8s.io/v1                                     |
|  kind: Lease                                                            |
|  metadata:                                                              |
|    name: my-app-leader                                                  |
|  spec:                                                                  |
|    holderIdentity: "pod-abc123"                                         |
|    leaseDurationSeconds: 15                                             |
|    renewTime: "2024-01-15T10:30:00Z"                                    |
|                                                                         |
|  client-go provides leader election library:                            |
|  * Pods compete for Lease ownership                                     |
|  * Leader renews lease periodically                                     |
|  * If leader fails to renew > another pod takes over                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 21.7: COMPARISON AND DECISION GUIDE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DISTRIBUTED LOCKING OPTIONS                                            |
|                                                                         |
|  +----------------+--------------------------------------------------+  |
|  | Approach       | When to Use                                      |  |
|  +----------------+--------------------------------------------------+  |
|  | Redis SETNX    | Simple cases, efficiency lock (not safety)       |  |
|  |                | Already have Redis, low latency needed           |  |
|  +----------------+--------------------------------------------------+  |
|  | Redlock        | Need higher availability than single Redis       |  |
|  |                | Willing to accept complexity                     |  |
|  +----------------+--------------------------------------------------+  |
|  | ZooKeeper      | Need strong correctness guarantees               |  |
|  |                | Already have ZK (Kafka, Hadoop ecosystem)        |  |
|  +----------------+--------------------------------------------------+  |
|  | etcd           | Kubernetes environments                          |  |
|  |                | Need strong consistency                          |  |
|  +----------------+--------------------------------------------------+  |
|  | Database Lock  | Simple cases, no extra infrastructure            |  |
|  |                | SELECT FOR UPDATE or advisory locks              |  |
|  +----------------+--------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  TWO TYPES OF LOCKS (Martin Kleppmann):                                 |
|                                                                         |
|  1. EFFICIENCY LOCK                                                     |
|     Purpose: Avoid duplicate work (e.g., double-sending email)          |
|     Consequence of failure: Wasted work, minor inconvenience            |
|     Solution: Simple Redis lock is fine                                 |
|                                                                         |
|  2. CORRECTNESS LOCK                                                    |
|     Purpose: Prevent data corruption (e.g., double-charging)            |
|     Consequence of failure: Data loss, financial loss                   |
|     Solution: Consensus system + fencing tokens                         |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  INTERVIEW ANSWER FRAMEWORK:                                            |
|                                                                         |
|  "For distributed locking, I'd consider:                                |
|                                                                         |
|   1. Is this for efficiency or correctness?                             |
|      - Efficiency: Redis SETNX with TTL                                 |
|      - Correctness: Add fencing tokens                                  |
|                                                                         |
|   2. What infrastructure do we have?                                    |
|      - Already have Redis > use Redis                                   |
|      - Kubernetes > use etcd/Lease                                      |
|      - Need strong guarantees > ZooKeeper/etcd                          |
|                                                                         |
|   3. Always implement:                                                  |
|      - TTL for auto-release                                             |
|      - Unique owner ID (prevent wrong release)                          |
|      - Retry with backoff                                               |
|      - Fencing tokens for critical operations"                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 21.8: QUICK REFERENCE

```
+--------------------------------------------------------------------------+
|                                                                          |
|  DISTRIBUTED CONCURRENCY CONTROL - CHEAT SHEET                           |
|                                                                          |
|  REDIS SETNX PATTERN:                                                    |
|  ----------------------                                                  |
|  Acquire: SET lock:key uuid NX PX 30000                                  |
|  Release: Lua script (check owner before delete)                         |
|  Risk: Lock expires while holding > use fencing tokens                   |
|                                                                          |
|  FENCING TOKEN:                                                          |
|  ----------------                                                        |
|  Lock server returns incrementing token                                  |
|  Storage rejects writes with stale tokens                                |
|  Solves: "zombie lock holder" problem                                    |
|                                                                          |
|  REDLOCK:                                                                |
|  --------                                                                |
|  Lock across N (5) independent Redis instances                           |
|  Need majority (3) to acquire                                            |
|  Controversial - use for efficiency, not correctness                     |
|                                                                          |
|  ZOOKEEPER/ETCD:                                                         |
|  ----------------                                                        |
|  Consensus-based, stronger guarantees                                    |
|  Ephemeral nodes (ZK) / Leases (etcd)                                    |
|  Use for correctness-critical locks                                      |
|                                                                          |
|  LEADER ELECTION:                                                        |
|  -----------------                                                       |
|  Special case of distributed lock                                        |
|  Only one leader at a time                                               |
|  K8s: Use Lease object + client-go library                               |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  KEY TAKEAWAYS:                                                          |
|                                                                          |
|  * No perfect distributed lock exists                                    |
|  * Always use TTL (prevent deadlocks)                                    |
|  * Use unique owner ID (prevent wrong release)                           |
|  * Fencing tokens for correctness                                        |
|  * Choose based on: efficiency vs correctness requirement                |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 21.9: DISTRIBUTED LOCK FOR CRON JOBS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE PROBLEM: DUPLICATE CRON EXECUTION IN DISTRIBUTED SYSTEMS           |
|                                                                         |
|  With N replicas of a service, a cron job scheduled at "every 5 min"    |
|  fires on ALL N instances simultaneously.                               |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Time T=0: Cron triggers "send-daily-report"                      |  |
|  |                                                                   |  |
|  |  Instance 1 ──► runs job ──► sends email                          |  |
|  |  Instance 2 ──► runs job ──► sends email  (DUPLICATE)             |  |
|  |  Instance 3 ──► runs job ──► sends email  (DUPLICATE)             |  |
|  |  Instance 4 ──► runs job ──► sends email  (DUPLICATE)             |  |
|  |  Instance 5 ──► runs job ──► sends email  (DUPLICATE)             |  |
|  |                                                                   |  |
|  |  User receives 5 identical emails!                                |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  CONSEQUENCES:                                                          |
|  * Duplicate work     — same email sent N times                         |
|  * Data corruption    — N instances updating same rows concurrently     |
|  * Resource waste     — N× compute for work that should happen once     |
|  * Financial risk     — N× charges in payment/billing cron jobs         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 21.9.1: SOLUTION — LOCK BEFORE EXECUTE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Before executing cron logic, each instance tries to ACQUIRE a          |
|  distributed lock. Only the winner proceeds; the rest skip.             |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Time T=0: Cron fires on all 3 instances                         |  |
|  |                                                                   |  |
|  |  Instance A ─► LOCK("daily-report") ─► SUCCESS ─► runs ─► unlock |  |
|  |  Instance B ─► LOCK("daily-report") ─► FAIL    ─► skip           |  |
|  |  Instance C ─► LOCK("daily-report") ─► FAIL    ─► skip           |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  FLOW:                                                                  |
|                                                                         |
|  Cron fires on every instance                                           |
|           |                                                             |
|           v                                                             |
|    Try acquire lock                                                     |
|    (atomic, with TTL)                                                   |
|           |                                                             |
|     +-----+-----+                                                       |
|     |           |                                                       |
|   SUCCESS     FAIL                                                      |
|     |           |                                                       |
|  Run job      Skip                                                      |
|     |                                                                   |
|  Release lock                                                           |
|                                                                         |
|  REDIS EXAMPLE:                                                         |
|                                                                         |
|  lock_key   = "lock:cron:daily-report"                                  |
|  lock_value = uuid()  (unique per instance per attempt)                 |
|  result     = SET lock_key lock_value NX PX 60000                       |
|                                                                         |
|  if result == OK:                                                       |
|      run_job()                                                          |
|      release_lock(lock_key, lock_value)  // Lua check-and-delete        |
|  else:                                                                  |
|      log("Another instance is running this job, skipping")              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 21.9.2: TTL — THE CRITICAL SAFETY NET

```
+-------------------------------------------------------------------------+
|                                                                         |
|  A lock MUST have a TTL. If the winning instance crashes mid-job        |
|  without releasing the lock, the lock would be held forever.            |
|                                                                         |
|  THE TTL TRADE-OFF:                                                     |
|                                                                         |
|  TTL too short (< job duration):                                        |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Instance A acquires lock (TTL = 10s)                             |  |
|  |       |                                                           |  |
|  |       +── starts job (takes 25s)...                               |  |
|  |       |                                                           |  |
|  |  [10 seconds: LOCK EXPIRES while job still running]               |  |
|  |                                                                   |  |
|  |  Instance B acquires lock ──► starts same job                     |  |
|  |  Instance A still running ──► BOTH executing = DUPLICATE!         |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  TTL too long (>> job duration):                                        |
|  * Instance crashes → lock held until TTL expires                       |
|  * Next scheduled run blocked → missed job execution                    |
|  * If TTL = 5min and cron = every 5min → one full cycle missed          |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  SOLUTIONS:                                                             |
|                                                                         |
|  1. SET TTL = 2-3× expected job duration                                |
|     Job takes ~10s → TTL = 30s                                          |
|     Covers slow runs, but releases reasonably fast on crash             |
|                                                                         |
|  2. LOCK RENEWAL (watchdog / heartbeat)                                 |
|     Start with moderate TTL (e.g., 30s)                                 |
|     Background thread extends TTL every TTL/3 while job runs            |
|     If instance crashes → no renewal → TTL expires → lock released      |
|     (Redisson library does this automatically)                          |
|                                                                         |
|  3. FENCING TOKEN (from Section 21.3)                                   |
|     Even if TTL expires and two instances overlap,                      |
|     fencing token prevents stale instance from corrupting data          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 21.9.3: LOCK GRANULARITY — WHAT SHOULD THE KEY BE?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  The lock key determines WHAT you're protecting and HOW.                |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  | Strategy              | Lock Key Example              | Effect   |  |
|  |-----------------------|-------------------------------|----------|  |
|  | Per job type          | lock:send-reminders           | Only one |  |
|  |                       |                               | instance |  |
|  |                       |                               | runs it  |  |
|  |-----------------------|-------------------------------|----------|  |
|  | Per job + time window | lock:send-reminders:          | Prevents |  |
|  |                       |   2026-03-25-14:00            | re-run   |  |
|  |                       |                               | in same  |  |
|  |                       |                               | window   |  |
|  |-----------------------|-------------------------------|----------|  |
|  | Per job + partition   | lock:send-reminders:shard-3   | Parallel |  |
|  |                       |                               | across   |  |
|  |                       |                               | shards   |  |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  PER JOB TYPE: "lock:send-reminders"                                    |
|  * Simplest approach                                                    |
|  * Only one instance runs the job at any given time                     |
|  * Risk: if cron fires again before last run finishes, new run skips    |
|                                                                         |
|  PER JOB + TIME WINDOW: "lock:send-reminders:2026-03-25-14:00"         |
|  * Encodes the scheduled time in the key                                |
|  * Prevents re-execution within the SAME scheduled window               |
|  * Even if job is retried or delayed, it won't double-run for          |
|    the same time slot                                                   |
|  * BEST FOR: most cron jobs — combines dedup with window awareness      |
|                                                                         |
|  PER JOB + PARTITION: "lock:send-reminders:shard-3"                     |
|  * Allows parallelism across shards/partitions                          |
|  * Each shard locked independently                                      |
|  * Instance A processes shard-1, Instance B processes shard-2           |
|  * BEST FOR: large data processing cron jobs that benefit from          |
|    parallel execution across data partitions                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 21.9.4: LEADER ELECTION — ALTERNATIVE PATTERN

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Instead of competing for a lock on every cron tick, elect a            |
|  single LEADER that is the only instance running cron jobs.             |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  LOCK-PER-TICK vs LEADER ELECTION                                 |  |
|  |                                                                   |  |
|  |  LOCK-PER-TICK:                                                   |  |
|  |  Every cron tick → all instances race for lock                    |  |
|  |  Winner runs, losers skip                                         |  |
|  |  Lock contention on every tick (every 5 min = 288 races/day)      |  |
|  |                                                                   |  |
|  |  LEADER ELECTION:                                                 |  |
|  |  One instance elected as leader (via ZK/etcd/K8s Lease)           |  |
|  |  ONLY the leader has cron enabled                                 |  |
|  |  Other instances don't even attempt the job                       |  |
|  |  Leader dies → new leader elected → cron moves to new leader      |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  WHEN TO USE EACH:                                                      |
|                                                                         |
|  Lock-per-tick:                                                         |
|  * Simple, no extra infrastructure                                      |
|  * Few cron jobs, infrequent runs                                       |
|  * OK if lock contention is low                                         |
|                                                                         |
|  Leader election:                                                       |
|  * Many cron jobs running frequently                                    |
|  * Already have ZooKeeper/etcd/Kubernetes                               |
|  * Want zero contention on every tick                                   |
|  * Prefer deterministic "one node does cron" model                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 21.9.5: IDEMPOTENCY — THE SAFETY NET

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Distributed locks are BEST-EFFORT. They reduce duplicates but          |
|  CANNOT guarantee exactly-once in all failure scenarios.                |
|                                                                         |
|  EDGE CASES WHERE LOCK ALONE FAILS:                                     |
|  * TTL expires mid-execution (GC pause, slow I/O)                       |
|  * Network partition: instance thinks it has lock, lock server says no  |
|  * Clock drift in Redlock setup                                         |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  SOLUTION: Make the cron job itself IDEMPOTENT                          |
|                                                                         |
|  TECHNIQUES:                                                            |
|                                                                         |
|  1. UNIQUE JOB RUN ID                                                   |
|     Generate: run_id = "daily-report:2026-03-25"                        |
|     Before executing: check if run_id already processed                 |
|     After executing: mark run_id as complete                            |
|                                                                         |
|     INSERT INTO job_runs (run_id, status, completed_at)                 |
|       VALUES ('daily-report:2026-03-25', 'done', NOW())                 |
|       ON CONFLICT (run_id) DO NOTHING;                                  |
|     -- Rows affected = 0 → already ran → skip                           |
|                                                                         |
|  2. CHECK BEFORE ACT                                                    |
|     Don't "send all pending reminders"                                  |
|     Instead: "send reminders where sent_at IS NULL"                     |
|     If job runs twice, second run finds nothing to send                 |
|                                                                         |
|  3. DATABASE CONSTRAINTS                                                |
|     Unique constraint prevents duplicate inserts even if                 |
|     two instances somehow both execute the job                          |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  THE TRIFECTA FOR SAFE CRON IN DISTRIBUTED SYSTEMS:                     |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  1. DISTRIBUTED LOCK  — prevents MOST duplicates                  |  |
|  |  2. TTL / RENEWAL     — prevents deadlocks on crash               |  |
|  |  3. IDEMPOTENCY       — handles edge cases lock can't prevent     |  |
|  |                                                                   |  |
|  |  Lock is the first line of defense.                               |  |
|  |  Idempotency is the last line of defense.                         |  |
|  |  Together = safe cron execution in distributed systems.           |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 21.9.6: INTERVIEW ANSWER FRAMEWORK

```
+-------------------------------------------------------------------------+
|                                                                         |
|  INTERVIEW: "How do you prevent duplicate cron job execution            |
|  across multiple instances?"                                            |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  STRUCTURED ANSWER:                                                     |
|                                                                         |
|  "When running N replicas, a cron job fires on all instances.           |
|   To ensure only one executes, I use a three-layer approach:            |
|                                                                         |
|   1. DISTRIBUTED LOCK (first line of defense)                           |
|      Before executing, each instance tries to acquire a lock            |
|      in Redis using SET lock_key uuid NX PX ttl.                        |
|      Only the winner proceeds; losers skip immediately.                 |
|                                                                         |
|   2. TTL + RENEWAL (prevent deadlocks)                                  |
|      Lock has a TTL so if the winner crashes, the lock                  |
|      auto-releases. I set TTL to 2-3× expected job duration.            |
|      For long jobs, a background thread extends the TTL.                |
|                                                                         |
|   3. IDEMPOTENT JOB (safety net)                                        |
|      The job itself is designed to be safe if run twice.                 |
|      I use a unique run ID per schedule window                          |
|      (e.g., 'job:daily-report:2026-03-25') and check                   |
|      completion status before acting.                                   |
|                                                                         |
|   For the lock key, I prefer encoding the time window:                  |
|   'lock:job-name:2026-03-25-14:00' — this prevents re-execution        |
|   within the same scheduled window even if the lock expired             |
|   and was re-acquired.                                                  |
|                                                                         |
|   If we have many cron jobs running frequently, I'd consider            |
|   leader election instead — one node is the designated cron             |
|   runner via ZooKeeper/etcd/K8s Lease, eliminating per-tick             |
|   lock contention entirely."                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 21.6: RACE CONDITIONS IN ASYNC MICROSERVICES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RACE CONDITIONS IN ASYNC MICROSERVICES                                 |
|  ======================================                                 |
|                                                                         |
|  In async systems (Kafka, SQS, event-driven), race conditions are       |
|  HARDER to spot because there's no shared thread or process —           |
|  events arrive at unpredictable times across multiple services.         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 21.6.1: OUT-OF-ORDER EVENT PROCESSING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PROBLEM: Events arrive in wrong order                                  |
|                                                                         |
|  Order Service publishes:                                               |
|    Event 1: order_created  (t=100ms)                                    |
|    Event 2: order_updated  (t=200ms)                                    |
|    Event 3: order_cancelled (t=300ms)                                   |
|                                                                         |
|  Consumer receives:                                                     |
|    Event 3: order_cancelled                                             |
|    Event 1: order_created   <-- STALE! Resurrects cancelled order       |
|                                                                         |
|  WHY IT HAPPENS:                                                        |
|  * Kafka: different partitions = no ordering guarantee                  |
|  * Retries: Event 1 fails, retried after Event 2 succeeds               |
|  * Multiple producers: Service A and B publish about same entity        |
|  * Network: messages take different paths with varying latency          |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  SOLUTIONS:                                                             |
|                                                                         |
|  1. VERSION / TIMESTAMP CHECK (most common)                             |
|                                                                         |
|     Every event carries a version or timestamp.                         |
|     Consumer only applies if event version > current version.           |
|                                                                         |
|     // Consumer logic                                                   |
|     event = consume()                                                   |
|     current = db.get(event.entity_id)                                   |
|                                                                         |
|     if event.version <= current.version:                                |
|       log("Stale event, skipping")                                      |
|       return ACK  // don't reprocess                                    |
|                                                                         |
|     db.update(event.entity_id,                                          |
|       SET data = event.data, version = event.version                    |
|       WHERE version < event.version)  // CAS guard                      |
|                                                                         |
|  2. SAME PARTITION KEY (for Kafka)                                      |
|                                                                         |
|     All events for same entity go to same partition.                    |
|     Kafka guarantees order WITHIN a partition.                          |
|                                                                         |
|     producer.send("orders", key=order_id, value=event)                  |
|     // All events for order_123 go to same partition                    |
|     // Consumer sees them in order                                      |
|                                                                         |
|  3. SEQUENCE NUMBER WITH GAP DETECTION                                  |
|                                                                         |
|     Each event has seq_no (1, 2, 3...).                                 |
|     If consumer sees seq 5 but last was 3 — hold in buffer.             |
|     Wait for seq 4, then process 4, 5 in order.                         |
|     Timeout: if seq 4 never arrives, alert + process anyway.            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 21.6.2: CONCURRENT CONSUMERS UPDATING SAME RESOURCE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PROBLEM: Two consumers process events that affect the same entity      |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Kafka Topic: "payments"                                          |  |
|  |                                                                   |  |
|  |  Consumer A gets: { order: 123, action: "charge" }               |   |
|  |  Consumer B gets: { order: 123, action: "refund" }               |   |
|  |                                                                   |  |
|  |  Both read order 123:  balance = $100                             |  |
|  |  Consumer A: balance = 100 - 50 = $50  (charge)                  |   |
|  |  Consumer B: balance = 100 + 50 = $150 (refund)                  |   |
|  |                                                                   |  |
|  |  Who writes last wins. One update is LOST.                        |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  SOLUTIONS:                                                             |
|                                                                         |
|  1. PARTITION BY ENTITY (prevent concurrency entirely)                  |
|                                                                         |
|     Route all events for same entity to same partition.                 |
|     Single consumer per partition = sequential processing.              |
|     No concurrent access to same entity. Simplest fix.                  |
|                                                                         |
|     // Kafka: key = order_id ensures same partition                     |
|     // SQS FIFO: MessageGroupId = order_id                              |
|                                                                         |
|  2. OPTIMISTIC LOCKING (DB-level guard)                                 |
|                                                                         |
|     UPDATE orders                                                       |
|       SET balance = balance - 50, version = version + 1                 |
|       WHERE id = 123 AND version = 5;                                   |
|     -- Rows affected = 0? Someone else changed it. RETRY.               |
|                                                                         |
|  3. DISTRIBUTED LOCK (Redis / Zookeeper)                                |
|                                                                         |
|     lock = redis.set("lock:order:123", owner, NX, EX=5)                 |
|     if lock acquired:                                                   |
|       process event                                                     |
|       release lock                                                      |
|     else:                                                               |
|       retry after backoff (or send to retry queue)                      |
|                                                                         |
|  4. ATOMIC DB OPERATIONS (no read-then-write)                           |
|                                                                         |
|     BAD:  balance = db.read(balance); db.write(balance - 50)            |
|     GOOD: UPDATE orders SET balance = balance - 50 WHERE id = 123       |
|           (single atomic SQL, no read-modify-write race)                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 21.6.3: CONSUMER REBALANCE RACE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PROBLEM: Kafka consumer rebalance causes duplicate processing          |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Consumer A processing message at offset 42...                    |  |
|  |                                                                   |  |
|  |  REBALANCE TRIGGERED (new consumer joins group)                   |  |
|  |                                                                   |  |
|  |  Partition reassigned: A loses partition, B gets it               |  |
|  |                                                                   |  |
|  |  But A hasn't committed offset 42 yet!                            |  |
|  |  A is still mid-processing...                                    |   |
|  |                                                                   |  |
|  |  B starts from last committed offset (41)                         |  |
|  |  B processes message 42 AGAIN                                     |  |
|  |                                                                   |  |
|  |  Meanwhile A finishes and tries to commit -> FAILS               |   |
|  |  (partition no longer assigned to A)                              |  |
|  |                                                                   |  |
|  |  Result: Message 42 processed TWICE by A and B                    |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  SOLUTIONS:                                                             |
|                                                                         |
|  1. IDEMPOTENT CONSUMERS (most important, always do this)               |
|     -- Track processed event_ids in DB                                  |
|     -- Before processing: if event_id exists -> skip                    |
|     -- After processing: INSERT event_id in same transaction            |
|                                                                         |
|     BEGIN TRANSACTION;                                                  |
|       INSERT INTO processed_events (event_id) VALUES ('evt-42');        |
|       -- if duplicate, unique constraint fails -> skip                  |
|       UPDATE orders SET status = 'confirmed' WHERE id = 123;            |
|     COMMIT;                                                             |
|                                                                         |
|  2. COOPERATIVE STICKY ASSIGNOR (Kafka 2.4+)                            |
|     -- Minimizes partition movement during rebalance                    |
|     -- Partitions stay with same consumer when possible                 |
|     -- Reduces window for duplicate processing                          |
|     partition.assignment.strategy = cooperative-sticky                  |
|                                                                         |
|  3. STATIC GROUP MEMBERSHIP (Kafka 2.3+)                                |
|     -- Assign fixed group.instance.id to each consumer                  |
|     -- Consumer restart doesn't trigger rebalance                       |
|     -- Only triggers rebalance after session.timeout.ms                 |
|     group.instance.id = "consumer-host-1"                               |
|     session.timeout.ms = 300000  // 5 min                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 21.6.4: READ-THEN-WRITE (CHECK-THEN-ACT) IN ASYNC FLOWS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PROBLEM: Service reads state, makes decision, then writes.             |
|  Between read and write, another event changes the state.               |
|                                                                         |
|  EXAMPLE: Double booking                                                |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Event A: "book_seat_A1"     Event B: "book_seat_A1"             |   |
|  |       |                           |                               |  |
|  |  Consumer 1:                 Consumer 2:                          |  |
|  |  1. Check: is A1 free? YES  1. Check: is A1 free? YES           |    |
|  |  2. Book A1                  2. Book A1                           |  |
|  |                                                                   |  |
|  |  Result: DOUBLE BOOKED! Both consumers saw "free" before         |   |
|  |  either wrote "booked".                                           |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  This is the classic TOCTOU (Time Of Check To Time Of Use) bug.         |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  SOLUTIONS:                                                             |
|                                                                         |
|  1. ATOMIC CONDITIONAL WRITE (best for DB)                              |
|                                                                         |
|     Don't check then write. Do it in ONE statement:                     |
|                                                                         |
|     UPDATE seats SET status = 'booked', user_id = 456                   |
|       WHERE seat_id = 'A1' AND status = 'available';                    |
|     -- Rows affected = 1 -> success                                     |
|     -- Rows affected = 0 -> someone else got it                         |
|                                                                         |
|  2. REDIS ATOMIC OPERATIONS                                             |
|                                                                         |
|     -- Lua script: check + reserve in one atomic operation              |
|     local status = redis.call('GET', 'seat:A1')                         |
|     if status == 'available' then                                       |
|       redis.call('SET', 'seat:A1', user_id, 'EX', 300)                  |
|       return 1                                                          |
|     end                                                                 |
|     return 0                                                            |
|                                                                         |
|  3. UNIQUE CONSTRAINT AS SAFETY NET                                     |
|                                                                         |
|     CREATE UNIQUE INDEX idx_seat_booking                                |
|       ON bookings(show_id, seat_id);                                    |
|     -- Even if app logic has a race, DB rejects duplicate               |
|                                                                         |
|  4. PESSIMISTIC LOCK (SELECT FOR UPDATE)                                |
|                                                                         |
|     BEGIN;                                                              |
|     SELECT * FROM seats WHERE seat_id = 'A1' FOR UPDATE;                |
|     -- Lock acquired. No one else can read this row.                    |
|     UPDATE seats SET status = 'booked' WHERE seat_id = 'A1';            |
|     COMMIT;                                                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 21.6.5: EVENT REPLAY / REPROCESSING OVERWRITES NEWER DATA

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PROBLEM: Replaying old events overwrites current state                 |
|                                                                         |
|  Scenarios where events get replayed:                                   |
|  * Consumer group reset to earlier offset (bug fix reprocessing)        |
|  * Dead letter queue (DLQ) messages retried hours later                 |
|  * Retry queue delivers old event after newer ones processed            |
|  * Kafka consumer seek back for reprocessing                            |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Timeline:                                                        |  |
|  |  10:00 - Event: user.email = "old@mail.com"                      |   |
|  |  10:05 - Event: user.email = "new@mail.com" (processed OK)       |   |
|  |  10:10 - REPLAY: user.email = "old@mail.com" (from DLQ retry)   |    |
|  |                                                                   |  |
|  |  Result: User's email reverts to old value!                       |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  SOLUTIONS:                                                             |
|                                                                         |
|  1. EVENT TIMESTAMP / VERSION CHECK (always do this)                    |
|                                                                         |
|     UPDATE users                                                        |
|       SET email = 'old@mail.com', updated_at = '10:00'                  |
|       WHERE id = 123 AND updated_at < '10:00';                          |
|     -- Rows affected = 0: current data is newer. Skip.                  |
|                                                                         |
|  2. MONOTONIC VERSION COLUMN                                            |
|                                                                         |
|     Every entity has a version counter.                                 |
|     Events carry the version they were created at.                      |
|     Consumer: only apply if event.version > current.version             |
|                                                                         |
|  3. IDEMPOTENCY TABLE                                                   |
|                                                                         |
|     Track every processed event_id.                                     |
|     On replay: event_id already exists -> skip entirely.                |
|     No stale data written, no side effects repeated.                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 21.6.6: DECISION GUIDE & INTERVIEW CHEAT SHEET

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RACE CONDITION DECISION GUIDE                                          |
|  ==============================                                         |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  | Problem                   | Best Solution                         |  |
|  |---------------------------|---------------------------------------|  |
|  | Out-of-order events       | Version check + partition by entity   |  |
|  | Concurrent updates        | Atomic DB ops or optimistic locking   |  |
|  | Consumer rebalance dupes  | Idempotent consumers (always!)        |  |
|  | Check-then-act / TOCTOU   | Atomic conditional write / Lua script |  |
|  | Event replay overwrites   | Timestamp/version guard on writes     |  |
|  | Two services, same entity | Partition key = entity_id             |  |
|  | Flash sale / hot resource | Redis Lua script (atomic check+book)  |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  UNIVERSAL DEFENSES (apply to ALL async microservices):                 |
|                                                                         |
|  1. IDEMPOTENT CONSUMERS                                                |
|     Every consumer must handle receiving the same event twice.          |
|     Track event_id in DB or Redis. Duplicate -> skip.                   |
|                                                                         |
|  2. PARTITION BY ENTITY                                                 |
|     Route events by entity_id (Kafka key / SQS FIFO group).             |
|     Guarantees ordering per entity. Prevents concurrent access.         |
|                                                                         |
|  3. OPTIMISTIC CONCURRENCY (version column)                             |
|     Every write checks version. Stale write rejected.                   |
|     No locks needed. Works at any scale.                                |
|                                                                         |
|  4. ATOMIC OPERATIONS (no read-modify-write)                            |
|     Prefer: UPDATE x SET val = val + 1                                  |
|     Over:   val = READ x; WRITE x = val + 1                             |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  INTERVIEW TIP:                                                         |
|  "In async microservices, I always design consumers to be               |
|   idempotent — they track processed event IDs and skip duplicates.      |
|   I use entity-based partition keys in Kafka to guarantee ordering.     |
|   For shared state updates, I use optimistic locking with version       |
|   columns. And I never do read-then-write — always atomic               |
|   conditional updates like UPDATE ... WHERE version = expected."        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 21

