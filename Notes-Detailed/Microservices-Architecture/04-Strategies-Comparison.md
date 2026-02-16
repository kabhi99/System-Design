================================================================================
MICROSERVICES ARCHITECTURE - STRATEGIES & COMPARISONS
================================================================================

CHAPTER 4: RETRY, CONCURRENCY, ROLLBACK, FEATURE FLAG & DEPLOYMENT STRATEGIES
================================================================================


================================================================================
SECTION 1: RETRY STRATEGIES
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  WHY RETRY?                                                            │
    │                                                                         │
    │  Many failures are transient:                                          │
    │  • Network glitch (packet loss, timeout)                               │
    │  • Service temporarily overloaded                                      │
    │  • Database connection pool exhausted                                  │
    │  • Temporary DNS resolution failure                                    │
    │                                                                         │
    │  These often succeed on retry. But naive retries can cause:            │
    │  • Thundering herd (all clients retry at same time)                   │
    │  • Amplified load on already stressed service                         │
    │  • Duplicate operations (non-idempotent requests)                     │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 1: IMMEDIATE RETRY (No Delay)                                     │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Request → Fail → Retry → Fail → Retry → Success/Give Up             │ │
│  │                                                                        │ │
│  │  Timing: Retry 1 at 0ms, Retry 2 at 0ms, Retry 3 at 0ms              │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Fast recovery for very transient failures                               │
│  ✓ Simple to implement                                                      │
│  ✓ Low latency when retry succeeds immediately                             │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Can overwhelm already failing service                                   │
│  ✗ Thundering herd problem                                                 │
│  ✗ Wastes resources if failure is persistent                              │
│  ✗ No time for service to recover                                         │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Connection reset (TCP RST)                                               │
│  • Single retry for idempotent read operations                             │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 2: FIXED DELAY RETRY                                              │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Request → Fail → Wait 2s → Retry → Fail → Wait 2s → Retry           │ │
│  │                                                                        │ │
│  │  Timing: Retry 1 at 2s, Retry 2 at 4s, Retry 3 at 6s                 │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Simple to understand and implement                                      │
│  ✓ Gives service time to recover                                           │
│  ✓ Predictable retry timing                                                │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Synchronized retries (all clients retry at same intervals)             │
│  ✗ Fixed delay may be too short or too long                               │
│  ✗ Doesn't adapt to severity of failure                                   │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Known recovery time (e.g., leader election takes ~5s)                   │
│  • Simple use cases with low traffic                                        │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 3: EXPONENTIAL BACKOFF                                            │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  delay = base_delay × 2^attempt                                       │ │
│  │                                                                        │ │
│  │  Timing: Retry 1 at 1s, Retry 2 at 2s, Retry 3 at 4s, Retry 4 at 8s  │ │
│  │                                                                        │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │  │                                                                 │  │ │
│  │  │  Attempt    Delay                                               │  │ │
│  │  │  ────────────────────                                           │  │ │
│  │  │  1          1 second                                            │  │ │
│  │  │  2          2 seconds                                           │  │ │
│  │  │  3          4 seconds                                           │  │ │
│  │  │  4          8 seconds                                           │  │ │
│  │  │  5          16 seconds                                          │  │ │
│  │  │  6          32 seconds (capped at max_delay)                   │  │ │
│  │  │                                                                 │  │ │
│  │  └─────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Reduces load on failing service over time                               │
│  ✓ Handles both short and long outages                                     │
│  ✓ Industry standard approach                                              │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Still synchronized (all clients double at same time)                   │
│  ✗ Can become very slow for extended outages                              │
│  ✗ First retries still happen together                                    │
│                                                                              │
│  USE WHEN:                                                                   │
│  • General purpose retrying                                                 │
│  • Unknown failure duration                                                 │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 4: EXPONENTIAL BACKOFF WITH JITTER (RECOMMENDED)                  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  delay = base_delay × 2^attempt + random(0, base_delay × 2^attempt)  │ │
│  │                                                                        │ │
│  │  Or: delay = random(0, base_delay × 2^attempt)  [Full Jitter]        │ │
│  │                                                                        │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │  │                                                                 │  │ │
│  │  │  WITHOUT JITTER:                                                │  │ │
│  │  │                                                                 │  │ │
│  │  │  Client A: ─────────────┬───────────────┬───────────────────── │  │ │
│  │  │  Client B: ─────────────┬───────────────┬───────────────────── │  │ │
│  │  │  Client C: ─────────────┬───────────────┬───────────────────── │  │ │
│  │  │                         │               │                       │  │ │
│  │  │                      1s burst        2s burst                  │  │ │
│  │  │                                                                 │  │ │
│  │  │  WITH JITTER:                                                   │  │ │
│  │  │                                                                 │  │ │
│  │  │  Client A: ────────┬──────────────────────┬─────────────────── │  │ │
│  │  │  Client B: ──────────────┬─────────────┬────────────────────── │  │ │
│  │  │  Client C: ──────────────────┬────────────────┬─────────────── │  │ │
│  │  │                              │                │                 │  │ │
│  │  │                         Spread out                              │  │ │
│  │  │                                                                 │  │ │
│  │  └─────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  JITTER TYPES:                                                               │
│                                                                              │
│  Full Jitter:        delay = random(0, base × 2^attempt)                   │
│  Equal Jitter:       delay = (base × 2^attempt)/2 + random(0, half)        │
│  Decorrelated:       delay = random(base, prev_delay × 3)                  │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Prevents thundering herd                                                │
│  ✓ Spreads load evenly                                                     │
│  ✓ Best for high-concurrency systems                                       │
│  ✓ AWS, Google, Netflix recommended                                        │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Slightly more complex to implement                                      │
│  ✗ Less predictable timing (harder to debug)                              │
│                                                                              │
│  USE WHEN:                                                                   │
│  • High traffic systems                                                     │
│  • Distributed systems with many clients                                    │
│  • Default choice for most scenarios                                        │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 5: LINEAR BACKOFF                                                  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  delay = base_delay × attempt                                         │ │
│  │                                                                        │ │
│  │  Timing: Retry 1 at 1s, Retry 2 at 2s, Retry 3 at 3s, Retry 4 at 4s  │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ More gradual increase than exponential                                  │
│  ✓ Doesn't grow as aggressively                                           │
│  ✓ Predictable                                                             │
│                                                                              │
│  CONS:                                                                       │
│  ✗ May not back off fast enough for severe outages                        │
│  ✗ Synchronized retries without jitter                                    │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Failures expected to resolve quickly                                     │
│  • Don't want long delays                                                  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 6: FIBONACCI BACKOFF                                               │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  delay = fibonacci(attempt) × base_delay                              │ │
│  │                                                                        │ │
│  │  Timing: 1s, 1s, 2s, 3s, 5s, 8s, 13s, 21s...                         │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Growth rate between linear and exponential                              │
│  ✓ More gradual than exponential                                           │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Less common, unusual choice                                             │
│  ✗ Still synchronized without jitter                                       │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Want slower growth than exponential                                      │
│  • Specific timing requirements                                             │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  RETRY STRATEGIES COMPARISON TABLE                                           │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Strategy              Delay Pattern         Best For                  │ │
│  │  ──────────────────────────────────────────────────────────────────── │ │
│  │                                                                        │ │
│  │  Immediate             0, 0, 0               Connection resets        │ │
│  │                                                                        │ │
│  │  Fixed Delay           2s, 2s, 2s            Known recovery time      │ │
│  │                                                                        │ │
│  │  Linear                1s, 2s, 3s            Gradual backoff          │ │
│  │                                                                        │ │
│  │  Exponential           1s, 2s, 4s, 8s        General purpose          │ │
│  │                                                                        │ │
│  │  Exponential+Jitter    ~1s, ~2s, ~4s         High traffic (DEFAULT)   │ │
│  │                        (randomized)                                    │ │
│  │                                                                        │ │
│  │  Fibonacci             1s, 1s, 2s, 3s, 5s    Moderate growth          │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  RECOMMENDATION: Exponential Backoff with Full Jitter                        │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 2: CONCURRENCY HANDLING STRATEGIES
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  CONCURRENCY CHALLENGES                                                │
    │                                                                         │
    │  • Race conditions (two requests modify same resource)                 │
    │  • Lost updates (second write overwrites first)                        │
    │  • Double processing (same request processed twice)                    │
    │  • Resource contention (too many concurrent requests)                  │
    │  • Deadlocks (circular waiting)                                        │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 1: OPTIMISTIC LOCKING (Version-Based)                             │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Read resource with version → Modify → Write with version check       │ │
│  │                                                                        │ │
│  │  Example:                                                              │ │
│  │  1. Read: { id: 1, balance: 100, version: 5 }                        │ │
│  │  2. Modify: balance = 100 - 20 = 80                                  │ │
│  │  3. Write: UPDATE accounts SET balance=80, version=6                 │ │
│  │            WHERE id=1 AND version=5                                   │ │
│  │  4. If rows_affected = 0 → Conflict! Retry from step 1               │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ No locks held during processing                                         │
│  ✓ High throughput under low contention                                    │
│  ✓ No deadlock risk                                                        │
│  ✓ Works well for read-heavy workloads                                     │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Retries under high contention                                           │
│  ✗ Starvation possible (same request keeps losing)                        │
│  ✗ Requires version column in schema                                       │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Low to medium contention                                                 │
│  • Read-heavy workloads                                                     │
│  • Web applications (users editing same document)                           │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 2: PESSIMISTIC LOCKING (Exclusive Locks)                          │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Acquire lock → Read → Modify → Write → Release lock                  │ │
│  │                                                                        │ │
│  │  Example (Database):                                                   │ │
│  │  SELECT * FROM accounts WHERE id=1 FOR UPDATE;  -- Lock row          │ │
│  │  UPDATE accounts SET balance = balance - 20 WHERE id=1;              │ │
│  │  COMMIT;  -- Release lock                                             │ │
│  │                                                                        │ │
│  │  Example (Distributed - Redis):                                       │ │
│  │  SET lock:account:1 <unique_id> NX EX 30   -- Acquire                │ │
│  │  ... do work ...                                                      │ │
│  │  DEL lock:account:1                         -- Release               │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Guarantees exclusive access                                             │
│  ✓ No retry loops                                                          │
│  ✓ Predictable behavior                                                    │
│  ✓ Better under high contention                                            │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Reduced throughput (blocking)                                           │
│  ✗ Deadlock risk if multiple resources locked                             │
│  ✗ Lock management complexity                                              │
│  ✗ Lock holder crash leaves lock held (needs TTL)                         │
│                                                                              │
│  USE WHEN:                                                                   │
│  • High contention scenarios                                                │
│  • Critical sections that must not have conflicts                          │
│  • Financial transactions                                                   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 3: SEMAPHORE / RATE LIMITING                                       │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Limit concurrent operations to N at a time                           │ │
│  │                                                                        │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │  │                                                                 │  │ │
│  │  │  Semaphore (permits = 10)                                      │  │ │
│  │  │                                                                 │  │ │
│  │  │  Request 1 → Acquire permit ✓ → Process → Release             │  │ │
│  │  │  Request 2 → Acquire permit ✓ → Process → Release             │  │ │
│  │  │  ...                                                            │  │ │
│  │  │  Request 10 → Acquire permit ✓ → Process                      │  │ │
│  │  │  Request 11 → Wait (no permits available)                      │  │ │
│  │  │                                                                 │  │ │
│  │  └─────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Protects downstream services from overload                              │
│  ✓ Predictable resource usage                                              │
│  ✓ Simple to implement                                                     │
│  ✓ Graceful degradation under load                                         │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Artificial limitation on throughput                                     │
│  ✗ Queuing adds latency                                                    │
│  ✗ Need to tune the limit                                                  │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Protecting limited resources (DB connections, external APIs)            │
│  • Bulkhead pattern implementation                                          │
│  • Rate limiting                                                            │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 4: IDEMPOTENCY KEYS                                                │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Client provides unique key; server processes only once               │ │
│  │                                                                        │ │
│  │  Request: POST /payments                                              │ │
│  │           Idempotency-Key: uuid-abc-123                               │ │
│  │                                                                        │ │
│  │  First request:                                                       │ │
│  │  1. Check: Is "uuid-abc-123" in idempotency store? No               │ │
│  │  2. Process payment                                                   │ │
│  │  3. Store: idempotency["uuid-abc-123"] = { result: success }        │ │
│  │  4. Return result                                                     │ │
│  │                                                                        │ │
│  │  Duplicate request (same key):                                        │ │
│  │  1. Check: Is "uuid-abc-123" in store? YES                          │ │
│  │  2. Return cached result (no reprocessing)                           │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Safe retries for non-idempotent operations                              │
│  ✓ Handles network failures gracefully                                     │
│  ✓ Client controls deduplication scope                                     │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Requires idempotency store (Redis/DB)                                   │
│  ✗ Storage for idempotency records                                         │
│  ✗ Client must generate and manage keys                                    │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Payment processing                                                       │
│  • Any mutation that shouldn't happen twice                                │
│  • Webhook delivery                                                         │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 5: QUEUE-BASED SEQUENTIAL PROCESSING                               │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Route related work to same queue/partition for ordering              │ │
│  │                                                                        │ │
│  │  Requests for Account A → Queue/Partition A → Single consumer        │ │
│  │  Requests for Account B → Queue/Partition B → Single consumer        │ │
│  │                                                                        │ │
│  │  Kafka Example:                                                       │ │
│  │  Partition key = account_id                                          │ │
│  │  All operations for same account go to same partition                │ │
│  │  Single consumer per partition → Sequential processing               │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Guaranteed ordering per entity                                          │
│  ✓ No locks needed                                                         │
│  ✓ Scales horizontally (more partitions)                                   │
│  ✓ Natural load distribution                                               │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Introduces latency (async)                                              │
│  ✗ Hot partitions if uneven distribution                                   │
│  ✗ Single consumer bottleneck per partition                               │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Event sourcing                                                           │
│  • Order-sensitive operations                                               │
│  • Can tolerate async processing                                            │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 6: COMPARE-AND-SWAP (CAS)                                          │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Atomic: "Set value to X only if current value is Y"                  │ │
│  │                                                                        │ │
│  │  Redis Example:                                                       │ │
│  │  WATCH account:balance                                                │ │
│  │  current = GET account:balance                                        │ │
│  │  MULTI                                                                │ │
│  │  SET account:balance (current - 20)                                  │ │
│  │  EXEC   -- Fails if value changed between WATCH and EXEC            │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Lock-free                                                               │
│  ✓ Very fast                                                               │
│  ✓ No blocking                                                             │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Requires retry on conflict                                              │
│  ✗ ABA problem possible                                                    │
│  ✗ Limited to single value/record                                          │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Counters, balances                                                       │
│  • Simple atomic updates                                                    │
│  • High-performance systems                                                 │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  CONCURRENCY STRATEGIES COMPARISON TABLE                                     │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Strategy           Throughput   Consistency   Complexity   Best For   │ │
│  │  ────────────────────────────────────────────────────────────────────  │ │
│  │                                                                        │ │
│  │  Optimistic Lock    High         Strong        Low          Low        │ │
│  │                     (low cont.)                              contention │ │
│  │                                                                        │ │
│  │  Pessimistic Lock   Medium       Strong        Medium       High       │ │
│  │                                                              contention │ │
│  │                                                                        │ │
│  │  Semaphore          Controlled   N/A           Low          Resource   │ │
│  │                                                              protection │ │
│  │                                                                        │ │
│  │  Idempotency Key    High         Strong        Medium       Payments,  │ │
│  │                                                              mutations  │ │
│  │                                                                        │ │
│  │  Queue-based        High         Eventual      Medium       Event      │ │
│  │                                                              ordering   │ │
│  │                                                                        │ │
│  │  CAS                Very High    Strong        Low          Counters,  │ │
│  │                                                              atomics    │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 3: ROLLBACK STRATEGIES
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  WHEN ROLLBACK IS NEEDED                                               │
    │                                                                         │
    │  • Deployment introduces bugs                                          │
    │  • Performance regression                                              │
    │  • Database migration failure                                          │
    │  • Configuration change breaks service                                 │
    │  • Integration with external service fails                             │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 1: VERSION ROLLBACK (Redeploy Previous Version)                   │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Current: v2.1 (buggy)                                                │ │
│  │  Rollback: Redeploy v2.0                                              │ │
│  │                                                                        │ │
│  │  Kubernetes:                                                          │ │
│  │  kubectl rollout undo deployment/my-service                          │ │
│  │  kubectl rollout undo deployment/my-service --to-revision=3          │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Simple and straightforward                                              │
│  ✓ Built into most deployment tools                                        │
│  ✓ Proven stable version                                                   │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Takes time to redeploy                                                  │
│  ✗ May not handle schema changes                                           │
│  ✗ Requires keeping old artifacts                                          │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Code bug discovered                                                      │
│  • No database schema changes                                               │
│  • Standard deployment pipeline                                             │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 2: BLUE-GREEN INSTANT SWITCH                                       │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Both versions running simultaneously                                 │ │
│  │                                                                        │ │
│  │  Load Balancer                                                        │ │
│  │       │                                                               │ │
│  │       ├──► Blue (v1) [100% traffic] ◄─── Rollback: Switch here       │ │
│  │       │                                                               │ │
│  │       └──► Green (v2) [0%] ◄─── Current deployment                   │ │
│  │                                                                        │ │
│  │  Rollback: Just change load balancer routing back to Blue            │ │
│  │  Time: < 1 second                                                     │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Instant rollback (DNS/LB switch)                                        │
│  ✓ No redeployment needed                                                  │
│  ✓ Can test new version before switch                                      │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Requires 2x infrastructure                                              │
│  ✗ Database compatibility needed for both versions                        │
│  ✗ Cost of running two environments                                        │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Zero-downtime requirements                                               │
│  • Instant rollback is critical                                             │
│  • Can afford double infrastructure                                         │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 3: FEATURE FLAG DISABLE                                            │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  New code deployed but behind feature flag                            │ │
│  │                                                                        │ │
│  │  if feature_flag("new_checkout_flow"):                               │ │
│  │      return new_checkout()                                            │ │
│  │  else:                                                                │ │
│  │      return old_checkout()                                            │ │
│  │                                                                        │ │
│  │  Rollback: Disable flag in feature flag service                       │ │
│  │  Time: Seconds (propagation delay)                                    │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Instant rollback without deployment                                     │
│  ✓ Granular control (disable specific features)                           │
│  ✓ No infrastructure duplication                                           │
│  ✓ Can rollback per user/segment                                           │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Requires feature flag infrastructure                                    │
│  ✗ Code complexity (branching logic)                                       │
│  ✗ Technical debt if flags not cleaned up                                  │
│  ✗ Both code paths must be maintained                                      │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Risky features                                                           │
│  • Gradual rollouts                                                         │
│  • A/B testing                                                              │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 4: CANARY ABORT                                                    │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Canary at 5% → Detect issues → Abort and route 100% to stable       │ │
│  │                                                                        │ │
│  │  Before: 5% → v2 (canary), 95% → v1                                  │ │
│  │  Problem detected!                                                    │ │
│  │  After: 0% → v2, 100% → v1                                           │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Limited blast radius (only 5% affected)                                 │
│  ✓ Quick rollback (just routing change)                                    │
│  ✓ Automatic rollback with metrics (Argo Rollouts, Flagger)               │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Some users already impacted                                             │
│  ✗ Requires traffic splitting infrastructure                               │
│  ✗ Metrics/monitoring required for detection                               │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Progressive delivery                                                     │
│  • Production validation                                                    │
│  • Good observability in place                                              │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 5: DATABASE ROLLBACK (Schema/Data)                                 │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  APPROACH A: Backward-Compatible Migrations                           │ │
│  │                                                                        │ │
│  │  1. Add new column (nullable)                                        │ │
│  │  2. Deploy code that writes to both old and new                      │ │
│  │  3. Migrate existing data                                            │ │
│  │  4. Deploy code that reads from new                                  │ │
│  │  5. Remove old column (separate migration)                           │ │
│  │                                                                        │ │
│  │  Rollback: Just rollback code, schema still compatible               │ │
│  │                                                                        │ │
│  │  ──────────────────────────────────────────────────────────────────  │ │
│  │                                                                        │ │
│  │  APPROACH B: Point-in-Time Recovery                                   │ │
│  │                                                                        │ │
│  │  Restore database to timestamp before migration                      │ │
│  │  ⚠️ WARNING: Loses all data written after that point!               │ │
│  │                                                                        │ │
│  │  ──────────────────────────────────────────────────────────────────  │ │
│  │                                                                        │ │
│  │  APPROACH C: Compensating Migration                                   │ │
│  │                                                                        │ │
│  │  Write a new migration that undoes the previous one                  │ │
│  │  Forward migration: Add column, migrate data                         │ │
│  │  Rollback migration: Reverse the changes                             │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Backward-compatible: Safe, no data loss                                 │
│  ✓ Compensating: Explicit undo logic                                       │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Complex migration process                                               │
│  ✗ Point-in-time loses data                                                │
│  ✗ Compensating migrations can be complex                                  │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Always use backward-compatible migrations                                │
│  • PITR only for disaster recovery                                          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 6: SAGA COMPENSATION                                               │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  For distributed transactions, undo previous steps                    │ │
│  │                                                                        │ │
│  │  Forward:                                                             │ │
│  │  1. Create Order ✓                                                   │ │
│  │  2. Reserve Inventory ✓                                              │ │
│  │  3. Process Payment ✗ (failed!)                                      │ │
│  │                                                                        │ │
│  │  Compensate (rollback):                                               │ │
│  │  1. Release Inventory (undo step 2)                                  │ │
│  │  2. Cancel Order (undo step 1)                                       │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Works across services                                                   │
│  ✓ No distributed transactions needed                                      │
│  ✓ Each service handles its own rollback                                   │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Compensating logic for every action                                     │
│  ✗ Eventual consistency during rollback                                    │
│  ✗ Complex failure handling                                                │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Multi-service transactions                                               │
│  • Order processing, booking systems                                        │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  ROLLBACK STRATEGIES COMPARISON TABLE                                        │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Strategy           Speed       Complexity   Data Safety   Best For    │ │
│  │  ────────────────────────────────────────────────────────────────────  │ │
│  │                                                                        │ │
│  │  Version Rollback   Minutes     Low          Safe          Code bugs   │ │
│  │                                                                        │ │
│  │  Blue-Green Switch  Seconds     Medium       Safe          Zero-down   │ │
│  │                                                                        │ │
│  │  Feature Flag       Seconds     Medium       Safe          Features    │ │
│  │                                                                        │ │
│  │  Canary Abort       Seconds     Medium       Safe          Progressive │ │
│  │                                                                        │ │
│  │  DB Backward-Compat Minutes     High         Safe          Schema      │ │
│  │                                                                        │ │
│  │  DB Point-in-Time   Minutes     Low          DATA LOSS!    Disaster    │ │
│  │                                                                        │ │
│  │  Saga Compensation  Varies      High         Safe          Distributed │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 4: FEATURE FLAG STRATEGIES
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  FEATURE FLAGS (aka Feature Toggles)                                   │
    │                                                                         │
    │  Decouple deployment from release.                                     │
    │  Deploy code → Enable flag → Feature is live                           │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 1: BOOLEAN ON/OFF FLAG                                             │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Simple toggle: Feature is either ON or OFF for everyone              │ │
│  │                                                                        │ │
│  │  "new_dashboard": true                                                │ │
│  │  "dark_mode": false                                                   │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Simplest to implement                                                   │
│  ✓ Easy to understand                                                      │
│  ✓ Quick kill switch                                                       │
│                                                                              │
│  CONS:                                                                       │
│  ✗ All or nothing (no gradual rollout)                                     │
│  ✗ No targeting                                                            │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Kill switches                                                            │
│  • Simple feature toggles                                                   │
│  • Internal tools                                                           │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 2: PERCENTAGE ROLLOUT                                              │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Gradually increase traffic to new feature                            │ │
│  │                                                                        │ │
│  │  "new_checkout": {                                                    │ │
│  │    "rollout_percentage": 10                                          │ │
│  │  }                                                                    │ │
│  │                                                                        │ │
│  │  Hash(user_id) % 100 < 10 → See new feature                          │ │
│  │                                                                        │ │
│  │  Day 1: 5%                                                            │ │
│  │  Day 2: 25%                                                           │ │
│  │  Day 3: 50%                                                           │ │
│  │  Day 5: 100%                                                          │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Limit blast radius                                                      │
│  ✓ Monitor metrics before full rollout                                     │
│  ✓ Consistent per user (same user always sees same version)               │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Can't target specific users                                             │
│  ✗ Random selection (might miss important segments)                       │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Safe, gradual rollouts                                                   │
│  • Performance testing at scale                                             │
│  • Canary releases                                                          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 3: USER SEGMENT TARGETING                                          │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Enable feature for specific user segments                            │ │
│  │                                                                        │ │
│  │  "new_pricing": {                                                     │ │
│  │    "enabled_for": {                                                   │ │
│  │      "countries": ["US", "UK"],                                      │ │
│  │      "subscription": ["premium"],                                    │ │
│  │      "user_ids": ["beta-user-1", "beta-user-2"]                     │ │
│  │    }                                                                  │ │
│  │  }                                                                    │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Target specific users (beta testers, employees)                        │
│  ✓ Regional rollouts                                                       │
│  ✓ Segment-based experiments                                               │
│                                                                              │
│  CONS:                                                                       │
│  ✗ More complex configuration                                              │
│  ✗ Need user context available                                             │
│  ✗ Can miss edge cases in other segments                                   │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Beta programs                                                            │
│  • Geographic rollouts                                                      │
│  • Compliance (different features per region)                              │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 4: A/B TESTING FLAGS                                               │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Split users into variants for experimentation                        │ │
│  │                                                                        │ │
│  │  "checkout_button_color": {                                           │ │
│  │    "variants": {                                                      │ │
│  │      "control": { "color": "blue", "percentage": 50 },              │ │
│  │      "treatment": { "color": "green", "percentage": 50 }            │ │
│  │    }                                                                  │ │
│  │  }                                                                    │ │
│  │                                                                        │ │
│  │  Track: conversion_rate per variant                                  │ │
│  │  Analyze: Is green button better?                                    │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Data-driven decisions                                                   │
│  ✓ Statistical significance                                                │
│  ✓ Multiple variants possible                                              │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Requires analytics integration                                          │
│  ✗ Need enough traffic for significance                                    │
│  ✗ More complex setup                                                      │
│                                                                              │
│  USE WHEN:                                                                   │
│  • UX experiments                                                           │
│  • Pricing experiments                                                      │
│  • Algorithm comparison                                                     │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 5: TIME-BASED FLAGS                                                │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Enable/disable based on schedule                                     │ │
│  │                                                                        │ │
│  │  "holiday_theme": {                                                   │ │
│  │    "start": "2024-12-20T00:00:00Z",                                  │ │
│  │    "end": "2024-12-26T00:00:00Z"                                     │ │
│  │  }                                                                    │ │
│  │                                                                        │ │
│  │  "maintenance_mode": {                                                │ │
│  │    "windows": ["Sunday 02:00-04:00 UTC"]                             │ │
│  │  }                                                                    │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Automated activation/deactivation                                       │
│  ✓ Schedule campaigns in advance                                           │
│  ✓ No manual intervention needed                                           │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Time zone complexity                                                    │
│  ✗ Less flexibility for immediate changes                                 │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Marketing campaigns                                                      │
│  • Seasonal features                                                        │
│  • Scheduled maintenance                                                    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 6: OPERATIONAL/CIRCUIT BREAKER FLAGS                               │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Control operational behavior, not features                           │ │
│  │                                                                        │ │
│  │  "cache_enabled": true           // Disable if cache corrupted       │ │
│  │  "rate_limit": 1000              // Adjust dynamically               │ │
│  │  "external_api_enabled": true    // Disable if API down              │ │
│  │  "log_level": "INFO"             // Change to DEBUG for diagnosis    │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Operational flexibility without deployment                              │
│  ✓ Quick response to incidents                                             │
│  ✓ Graceful degradation                                                    │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Can mask underlying issues                                              │
│  ✗ Need monitoring to know when to toggle                                  │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Kill switches for expensive features                                     │
│  • Incident response                                                        │
│  • Dynamic configuration                                                    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  FEATURE FLAG STRATEGIES COMPARISON TABLE                                    │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Strategy           Targeting    Complexity   Analysis     Best For    │ │
│  │  ────────────────────────────────────────────────────────────────────  │ │
│  │                                                                        │ │
│  │  Boolean On/Off     None         Low          None         Kill switch │ │
│  │                                                                        │ │
│  │  Percentage         Random       Low          Basic        Gradual     │ │
│  │                     users                                   rollout     │ │
│  │                                                                        │ │
│  │  User Segment       Attributes   Medium       Segment      Beta,       │ │
│  │                                               metrics      Regional    │ │
│  │                                                                        │ │
│  │  A/B Testing        Random +     High         Statistical  Experiments │ │
│  │                     variants                   analysis                 │ │
│  │                                                                        │ │
│  │  Time-Based         Schedule     Low          Time-based   Campaigns,  │ │
│  │                                                             seasonal    │ │
│  │                                                                        │ │
│  │  Operational        None         Low          Ops metrics  Kill switch,│ │
│  │                                                             config      │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  TOOLS: LaunchDarkly, Unleash, Split, ConfigCat, Flipt                      │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 5: DEPLOYMENT STRATEGIES
================================================================================

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 1: RECREATE (Big Bang)                                             │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Stop all v1 → Deploy all v2                                          │ │
│  │                                                                        │ │
│  │  Before:  [v1] [v1] [v1] [v1]                                        │ │
│  │                    ↓ (downtime)                                        │ │
│  │  After:   [v2] [v2] [v2] [v2]                                        │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Simple                                                                   │
│  ✓ Clean state (no version mixing)                                         │
│  ✓ No backward compatibility needed                                        │
│                                                                              │
│  CONS:                                                                       │
│  ✗ DOWNTIME during deployment                                              │
│  ✗ Risky (all-at-once)                                                     │
│  ✗ Slow rollback                                                           │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Development/staging environments                                         │
│  • Scheduled maintenance windows                                            │
│  • Non-critical services                                                    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 2: ROLLING UPDATE                                                  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Gradually replace instances one at a time                            │ │
│  │                                                                        │ │
│  │  Step 1: [v2] [v1] [v1] [v1]    (25% new)                            │ │
│  │  Step 2: [v2] [v2] [v1] [v1]    (50% new)                            │ │
│  │  Step 3: [v2] [v2] [v2] [v1]    (75% new)                            │ │
│  │  Step 4: [v2] [v2] [v2] [v2]    (100% new)                           │ │
│  │                                                                        │ │
│  │  Kubernetes default: maxUnavailable=25%, maxSurge=25%                │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Zero downtime                                                           │
│  ✓ Gradual rollout                                                         │
│  ✓ Built into Kubernetes                                                   │
│  ✓ Resource efficient                                                      │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Mixed versions during rollout                                           │
│  ✗ Requires backward-compatible APIs                                       │
│  ✗ Slow for large deployments                                              │
│  ✗ Rollback also gradual                                                   │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Most production deployments                                              │
│  • When versions are compatible                                             │
│  • Kubernetes environments                                                   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 3: BLUE-GREEN DEPLOYMENT                                           │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Two identical environments, switch traffic instantly                 │ │
│  │                                                                        │ │
│  │               Load Balancer                                           │ │
│  │                    │                                                  │ │
│  │          ┌─────────┴─────────┐                                       │ │
│  │          │                   │                                       │ │
│  │          ▼                   ▼                                       │ │
│  │    ┌──────────┐        ┌──────────┐                                 │ │
│  │    │   BLUE   │        │  GREEN   │                                 │ │
│  │    │   (v1)   │        │   (v2)   │                                 │ │
│  │    │ ACTIVE   │        │  READY   │                                 │ │
│  │    └──────────┘        └──────────┘                                 │ │
│  │                                                                        │ │
│  │  Switch: Route 100% traffic from Blue to Green                       │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Instant switch                                                          │
│  ✓ Instant rollback                                                        │
│  ✓ Test new version in production environment                              │
│  ✓ No mixed versions during traffic                                        │
│                                                                              │
│  CONS:                                                                       │
│  ✗ 2x infrastructure cost                                                  │
│  ✗ Database compatibility for both versions                               │
│  ✗ Complex stateful applications                                           │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Critical services requiring instant rollback                            │
│  • Can afford double infrastructure                                         │
│  • Stateless applications                                                   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 4: CANARY DEPLOYMENT                                               │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Release to small percentage, monitor, expand                         │ │
│  │                                                                        │ │
│  │  Stage 1:  5% → v2 (canary), 95% → v1                                │ │
│  │            Monitor: errors, latency, conversions                      │ │
│  │            ✓ Metrics OK                                              │ │
│  │                                                                        │ │
│  │  Stage 2:  25% → v2, 75% → v1                                        │ │
│  │            ✓ Metrics OK                                              │ │
│  │                                                                        │ │
│  │  Stage 3:  50% → v2, 50% → v1                                        │ │
│  │            ✓ Metrics OK                                              │ │
│  │                                                                        │ │
│  │  Stage 4:  100% → v2, retire v1                                      │ │
│  │                                                                        │ │
│  │  If any stage fails: Abort, route 100% back to v1                    │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Minimal blast radius                                                    │
│  ✓ Real production traffic testing                                         │
│  ✓ Metrics-driven promotion                                                │
│  ✓ Automatic rollback possible (Argo Rollouts, Flagger)                   │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Slower rollout                                                          │
│  ✗ Requires traffic splitting                                              │
│  ✗ Need good observability                                                 │
│  ✗ Some users hit bugs                                                     │
│                                                                              │
│  USE WHEN:                                                                   │
│  • High-risk changes                                                        │
│  • Good monitoring in place                                                 │
│  • Want data-driven rollout                                                 │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 5: A/B TESTING DEPLOYMENT                                          │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Route specific users/segments to different versions                  │ │
│  │                                                                        │ │
│  │  Criteria-based routing:                                              │ │
│  │  • user.country == "US" → v2                                         │ │
│  │  • user.subscription == "premium" → v2                               │ │
│  │  • request.header["X-Beta"] == "true" → v2                           │ │
│  │  • else → v1                                                          │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Target specific user segments                                           │
│  ✓ A/B experiments on deployments                                          │
│  ✓ Sticky routing (same user, same version)                               │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Complex routing rules                                                   │
│  ✗ Requires user context                                                   │
│  ✗ Session affinity needed                                                 │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Testing with specific users                                              │
│  • Regional rollouts                                                        │
│  • Feature experiments                                                      │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STRATEGY 6: SHADOW DEPLOYMENT (Dark Launch)                                 │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Mirror traffic to new version without serving responses              │ │
│  │                                                                        │ │
│  │                   Request                                             │ │
│  │                      │                                                │ │
│  │            ┌─────────┴─────────┐                                     │ │
│  │            │                   │                                     │ │
│  │            ▼                   ▼                                     │ │
│  │      ┌──────────┐        ┌──────────┐                               │ │
│  │      │   v1     │        │   v2     │                               │ │
│  │      │ (serves) │        │ (shadow) │                               │ │
│  │      └─────┬────┘        └──────────┘                               │ │
│  │            │                   │                                     │ │
│  │            ▼                   ▼                                     │ │
│  │       Response              Logged                                   │ │
│  │       to user              (discarded)                               │ │
│  │                                                                        │ │
│  │  Compare: v1 response vs v2 response (correctness, latency)          │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Zero user impact                                                        │
│  ✓ Test with real production traffic                                       │
│  ✓ Compare responses for correctness                                       │
│  ✓ Performance testing at scale                                            │
│                                                                              │
│  CONS:                                                                       │
│  ✗ 2x load on backend                                                      │
│  ✗ Doesn't test user-facing behavior                                       │
│  ✗ Complex for write operations                                            │
│  ✗ Data consistency issues                                                 │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Major refactoring (same API, new implementation)                        │
│  • Database migrations                                                      │
│  • Performance validation                                                   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  DEPLOYMENT STRATEGIES COMPARISON TABLE                                      │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Strategy      Downtime  Rollback   Risk       Cost       Best For     │ │
│  │  ──────────────────────────────────────────────────────────────────── │ │
│  │                                                                        │ │
│  │  Recreate      YES       Slow       High       Low        Dev/staging  │ │
│  │                                                                        │ │
│  │  Rolling       No        Gradual    Medium     Low        Default      │ │
│  │                                                                        │ │
│  │  Blue-Green    No        Instant    Low        2x         Critical     │ │
│  │                                                                        │ │
│  │  Canary        No        Quick      Low        ~1.1x      High-risk    │ │
│  │                                                                        │ │
│  │  A/B Testing   No        Instant    Low        ~1.5x      Experiments  │ │
│  │                                                                        │ │
│  │  Shadow        No        N/A        None       2x         Refactoring  │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  RECOMMENDATION BY SCENARIO:                                                 │
│                                                                              │
│  • Standard release: Rolling Update                                         │
│  • High-risk/critical: Canary with automated rollback                      │
│  • Zero-downtime required: Blue-Green                                       │
│  • Major changes: Shadow + Canary                                           │
│  • A/B experiments: A/B Testing deployment                                  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘


================================================================================
SUMMARY: STRATEGY SELECTION GUIDE
================================================================================

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  RETRY STRATEGY:          Exponential Backoff with Full Jitter              │
│                           (industry standard, prevents thundering herd)      │
│                                                                              │
│  CONCURRENCY STRATEGY:    Optimistic Locking (low contention)               │
│                           Pessimistic Locking (high contention)              │
│                           Idempotency Keys (mutations)                       │
│                                                                              │
│  ROLLBACK STRATEGY:       Feature Flags (fastest, most flexible)            │
│                           Blue-Green Switch (instant, needs infra)           │
│                           Version Rollback (simple, takes time)              │
│                                                                              │
│  FEATURE FLAG STRATEGY:   Percentage Rollout + Segment Targeting            │
│                           (balance of safety and flexibility)                │
│                                                                              │
│  DEPLOYMENT STRATEGY:     Rolling Update (default)                          │
│                           Canary (high-risk changes)                         │
│                           Blue-Green (critical services)                     │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 6: FEATURE FLAG IMPLEMENTATION STRATEGIES
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  HOW TO IMPLEMENT FEATURE FLAGS                                        │
    │                                                                         │
    │  Feature flags can be implemented at different levels with varying     │
    │  complexity, performance, and flexibility trade-offs.                  │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  IMPLEMENTATION 1: CONFIGURATION FILE (Simplest)                            │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Store flags in config file (YAML, JSON, properties)                  │ │
│  │                                                                        │ │
│  │  feature_flags.yaml:                                                  │ │
│  │  ─────────────────────                                                │ │
│  │  features:                                                            │ │
│  │    new_checkout: true                                                 │ │
│  │    dark_mode: false                                                   │ │
│  │    beta_search: true                                                  │ │
│  │                                                                        │ │
│  │  Application reads at startup and caches                             │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Extremely simple                                                        │
│  ✓ No external dependencies                                                │
│  ✓ Version controlled                                                      │
│  ✓ Works offline                                                           │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Requires redeployment to change flags                                   │
│  ✗ No dynamic updates                                                      │
│  ✗ No targeting/segmentation                                               │
│  ✗ No audit trail                                                          │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Simple applications                                                      │
│  • Development/testing environments                                         │
│  • Flags rarely change                                                      │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  IMPLEMENTATION 2: ENVIRONMENT VARIABLES                                     │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Store flags as environment variables                                 │ │
│  │                                                                        │ │
│  │  FEATURE_NEW_CHECKOUT=true                                            │ │
│  │  FEATURE_DARK_MODE=false                                              │ │
│  │  FEATURE_BETA_SEARCH=true                                             │ │
│  │                                                                        │ │
│  │  Kubernetes ConfigMap:                                                │ │
│  │  ─────────────────────                                                │ │
│  │  apiVersion: v1                                                       │ │
│  │  kind: ConfigMap                                                      │ │
│  │  metadata:                                                            │ │
│  │    name: feature-flags                                                │ │
│  │  data:                                                                │ │
│  │    FEATURE_NEW_CHECKOUT: "true"                                      │ │
│  │    FEATURE_DARK_MODE: "false"                                        │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Simple                                                                  │
│  ✓ Environment-specific (dev/staging/prod)                                 │
│  ✓ Works with container orchestration                                      │
│  ✓ No code changes to toggle                                               │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Requires pod restart (usually)                                          │
│  ✗ No targeting/segmentation                                               │
│  ✗ Hard to manage many flags                                               │
│  ✗ No audit trail                                                          │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Container-based deployments                                              │
│  • Per-environment flags                                                    │
│  • Infrequent changes OK                                                    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  IMPLEMENTATION 3: DATABASE-BACKED                                           │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Store flags in database, application polls or uses cache             │ │
│  │                                                                        │ │
│  │  Table: feature_flags                                                 │ │
│  │  ─────────────────────                                                │ │
│  │  | name          | enabled | percentage | conditions          |      │ │
│  │  | new_checkout  | true    | 100        | null                |      │ │
│  │  | beta_search   | true    | 25         | {"country": "US"}   |      │ │
│  │  | dark_mode     | false   | 0          | null                |      │ │
│  │                                                                        │ │
│  │  Architecture:                                                        │ │
│  │                                                                        │ │
│  │  ┌───────────┐      ┌───────────┐      ┌───────────┐                 │ │
│  │  │  Service  │─────►│   Cache   │◄────►│  Database │                 │ │
│  │  │           │      │  (Redis)  │      │ (Postgres)│                 │ │
│  │  └───────────┘      └───────────┘      └───────────┘                 │ │
│  │                           │                                          │ │
│  │                           │ Poll every 30 seconds                   │ │
│  │                           │ or Push via pub/sub                     │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Dynamic updates (no restart)                                            │
│  ✓ Admin UI can modify flags                                               │
│  ✓ Supports targeting/conditions                                           │
│  ✓ Audit trail possible                                                    │
│  ✓ Self-hosted                                                             │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Need to build infrastructure                                            │
│  ✗ Cache invalidation complexity                                           │
│  ✗ Database dependency                                                     │
│  ✗ Polling latency or pub/sub complexity                                   │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Need dynamic updates                                                     │
│  • Want to self-host                                                        │
│  • Simple targeting requirements                                            │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  IMPLEMENTATION 4: DISTRIBUTED CONFIG (Consul/etcd/ZooKeeper)               │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Use distributed KV store for configuration                           │ │
│  │                                                                        │ │
│  │  Consul KV:                                                           │ │
│  │  ─────────────                                                        │ │
│  │  /config/features/new_checkout = true                                │ │
│  │  /config/features/dark_mode = false                                  │ │
│  │                                                                        │ │
│  │  Features:                                                            │ │
│  │  • Watch for changes (push-based updates)                            │ │
│  │  • Highly available                                                  │ │
│  │  • Consistent across cluster                                         │ │
│  │                                                                        │ │
│  │  ┌───────────┐                        ┌───────────┐                  │ │
│  │  │  Service  │◄──────── Watch ────────│  Consul   │                  │ │
│  │  │    A      │                        │  Cluster  │                  │ │
│  │  └───────────┘                        └───────────┘                  │ │
│  │                                             │                         │ │
│  │  ┌───────────┐                              │                         │ │
│  │  │  Service  │◄───────────────────────────┘                          │ │
│  │  │    B      │                                                        │ │
│  │  └───────────┘                                                        │ │
│  │                                                                        │ │
│  │  All services get instant updates                                    │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Instant propagation (watch/push)                                        │
│  ✓ Highly available                                                        │
│  ✓ Consistent across services                                              │
│  ✓ Already used for service discovery                                      │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Additional infrastructure                                               │
│  ✗ Limited querying capabilities                                           │
│  ✗ No built-in targeting                                                   │
│  ✗ No analytics                                                            │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Already using Consul/etcd for service discovery                         │
│  • Need instant propagation                                                 │
│  • Simple boolean flags                                                     │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  IMPLEMENTATION 5: FEATURE FLAG SERVICE (SaaS or Self-Hosted)               │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Dedicated feature flag platform                                      │ │
│  │                                                                        │ │
│  │  SaaS Options:                                                        │ │
│  │  • LaunchDarkly (most popular, enterprise)                           │ │
│  │  • Split.io (experimentation focus)                                  │ │
│  │  • ConfigCat (simple, affordable)                                    │ │
│  │  • Flagsmith (open core)                                             │ │
│  │                                                                        │ │
│  │  Self-Hosted Options:                                                 │ │
│  │  • Unleash (open source, popular)                                    │ │
│  │  • Flipt (open source, simple)                                       │ │
│  │  • Flagr (open source, by Checkr)                                    │ │
│  │                                                                        │ │
│  │  Architecture:                                                        │ │
│  │                                                                        │ │
│  │  ┌───────────────────────────────────────────────────────────────┐   │ │
│  │  │                                                               │   │ │
│  │  │  ┌───────────┐         ┌─────────────────────────────────┐   │   │ │
│  │  │  │  Service  │◄───────►│     Feature Flag Service        │   │   │ │
│  │  │  │   (SDK)   │   API   │                                 │   │   │ │
│  │  │  └───────────┘         │  • Flag configuration          │   │   │ │
│  │  │                        │  • Targeting rules              │   │   │ │
│  │  │  ┌───────────┐         │  • Percentage rollouts          │   │   │ │
│  │  │  │  Service  │◄───────►│  • A/B experiments              │   │   │ │
│  │  │  │   (SDK)   │         │  • Analytics                    │   │   │ │
│  │  │  └───────────┘         │  • Audit logs                   │   │   │ │
│  │  │                        │                                 │   │   │ │
│  │  │                        └──────────────┬──────────────────┘   │   │ │
│  │  │                                       │                      │   │ │
│  │  │                              ┌────────▼────────┐             │   │ │
│  │  │                              │    Admin UI     │             │   │ │
│  │  │                              │  (Dashboard)    │             │   │ │
│  │  │                              └─────────────────┘             │   │ │
│  │  │                                                               │   │ │
│  │  └───────────────────────────────────────────────────────────────┘   │ │
│  │                                                                        │ │
│  │  SDK Features:                                                        │ │
│  │  • Local caching                                                     │ │
│  │  • Streaming updates                                                 │ │
│  │  • Offline mode                                                      │ │
│  │  • Evaluation locally (no network per check)                        │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Full-featured (targeting, analytics, audit)                             │
│  ✓ SDKs for all languages                                                  │
│  ✓ Real-time updates                                                       │
│  ✓ A/B testing built-in                                                    │
│  ✓ Excellent UI/UX                                                         │
│  ✓ Minimal latency (local evaluation)                                      │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Cost (SaaS can be expensive at scale)                                   │
│  ✗ External dependency                                                     │
│  ✗ Vendor lock-in (SaaS)                                                   │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Need full feature management                                             │
│  • A/B testing requirements                                                 │
│  • Enterprise scale                                                         │
│  • Want managed solution                                                    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  FEATURE FLAG IMPLEMENTATION COMPARISON                                      │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Implementation    Update     Targeting  Analytics  Complexity  Cost   │ │
│  │  ────────────────────────────────────────────────────────────────────  │ │
│  │                                                                        │ │
│  │  Config File       Redeploy   No         No         Very Low    Free   │ │
│  │                                                                        │ │
│  │  Env Variables     Restart    No         No         Low         Free   │ │
│  │                                                                        │ │
│  │  Database          Seconds    Basic      Manual     Medium      Low    │ │
│  │                                                                        │ │
│  │  Consul/etcd       Instant    No         No         Medium      Low    │ │
│  │                                                                        │ │
│  │  Self-Hosted       Instant    Yes        Yes        High        Low    │ │
│  │  (Unleash)                                                             │ │
│  │                                                                        │ │
│  │  SaaS              Instant    Yes        Yes        Low         $$-$$$ │ │
│  │  (LaunchDarkly)                                                        │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 7: CUTOVER STRATEGIES
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  WHAT IS A CUTOVER?                                                    │
    │                                                                         │
    │  Transitioning from one system/version to another:                     │
    │  • Old system → New system                                             │
    │  • Legacy database → New database                                      │
    │  • Monolith → Microservices                                            │
    │  • On-prem → Cloud                                                     │
    │  • Vendor A → Vendor B                                                 │
    │                                                                         │
    │  Key concern: Minimize risk and downtime                               │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  CUTOVER 1: BIG BANG CUTOVER                                                 │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Switch everything at once during a maintenance window                │ │
│  │                                                                        │ │
│  │  Timeline:                                                            │ │
│  │  ───────────────────────────────────────────────────────────────────  │ │
│  │                                                                        │ │
│  │  Day 0 (Before)         Maintenance Window       Day 1 (After)       │ │
│  │                                                                        │ │
│  │  [Old System]  ────────► [Downtime] ────────► [New System]           │ │
│  │   100% traffic            Switch                 100% traffic         │ │
│  │                           (2-8 hours)                                  │ │
│  │                                                                        │ │
│  │  Steps:                                                               │ │
│  │  1. Announce maintenance window to users                             │ │
│  │  2. Stop traffic to old system                                       │ │
│  │  3. Migrate data (if needed)                                         │ │
│  │  4. Deploy new system                                                │ │
│  │  5. Verify new system                                                │ │
│  │  6. Route traffic to new system                                      │ │
│  │  7. Monitor closely                                                  │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Simple to plan and execute                                              │
│  ✓ Clean break (no dual running)                                           │
│  ✓ No data sync complexity                                                 │
│  ✓ Clear rollback point                                                    │
│                                                                              │
│  CONS:                                                                       │
│  ✗ DOWNTIME required                                                       │
│  ✗ High risk (all or nothing)                                              │
│  ✗ Long maintenance window                                                 │
│  ✗ Rollback is painful                                                     │
│  ✗ All issues found in production at once                                  │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Downtime is acceptable                                                   │
│  • Simple migration (not much data)                                         │
│  • Strong confidence in new system                                          │
│  • Non-critical systems                                                     │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  CUTOVER 2: PARALLEL RUNNING (Blue-Green)                                    │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Run both systems simultaneously, switch traffic instantly            │ │
│  │                                                                        │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │  │                                                                 │  │ │
│  │  │              Load Balancer / Router                            │  │ │
│  │  │                      │                                         │  │ │
│  │  │           ┌──────────┴──────────┐                              │  │ │
│  │  │           │                     │                              │  │ │
│  │  │           ▼                     ▼                              │  │ │
│  │  │    ┌─────────────┐       ┌─────────────┐                       │  │ │
│  │  │    │ OLD SYSTEM  │       │ NEW SYSTEM  │                       │  │ │
│  │  │    │   (Blue)    │       │  (Green)    │                       │  │ │
│  │  │    │ 100% traffic│       │ 0% traffic  │                       │  │ │
│  │  │    └──────┬──────┘       └──────┬──────┘                       │  │ │
│  │  │           │                     │                              │  │ │
│  │  │           ▼                     ▼                              │  │ │
│  │  │    ┌─────────────┐       ┌─────────────┐                       │  │ │
│  │  │    │   Old DB    │─sync─►│   New DB    │                       │  │ │
│  │  │    └─────────────┘       └─────────────┘                       │  │ │
│  │  │                                                                 │  │ │
│  │  └─────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                        │ │
│  │  Cutover: Switch load balancer from Blue → Green                     │ │
│  │                                                                        │ │
│  │  Timeline:                                                            │ │
│  │  1. Deploy new system alongside old                                  │ │
│  │  2. Set up data sync (old → new)                                    │ │
│  │  3. Verify new system works                                          │ │
│  │  4. Switch traffic (instant)                                         │ │
│  │  5. Monitor                                                           │ │
│  │  6. Decommission old system (later)                                  │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Zero/minimal downtime                                                   │
│  ✓ Instant rollback (switch back)                                          │
│  ✓ Test new system with real data                                          │
│  ✓ Confidence before cutover                                               │
│                                                                              │
│  CONS:                                                                       │
│  ✗ 2x infrastructure cost                                                  │
│  ✗ Data sync complexity                                                    │
│  ✗ Both systems must be compatible with data                              │
│  ✗ Sync lag during cutover                                                 │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Zero downtime required                                                   │
│  • Instant rollback needed                                                  │
│  • Can afford double infrastructure                                         │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  CUTOVER 3: STRANGLER FIG (Gradual Migration)                                │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Gradually replace old system piece by piece                          │ │
│  │  Named after strangler fig tree that grows around host tree           │ │
│  │                                                                        │ │
│  │  Phase 1: Intercept and Route                                        │ │
│  │  ─────────────────────────────                                        │ │
│  │                                                                        │ │
│  │         ┌─────────────────────────────────────────┐                   │ │
│  │         │            FACADE / PROXY               │                   │ │
│  │         │                                         │                   │ │
│  │         │   /users   → Old System                │                   │ │
│  │         │   /orders  → Old System                │                   │ │
│  │         │   /products→ Old System                │                   │ │
│  │         │                                         │                   │ │
│  │         └─────────────────────────────────────────┘                   │ │
│  │                                                                        │ │
│  │  Phase 2: Migrate First Feature                                      │ │
│  │  ──────────────────────────────                                       │ │
│  │                                                                        │ │
│  │         ┌─────────────────────────────────────────┐                   │ │
│  │         │            FACADE / PROXY               │                   │ │
│  │         │                                         │                   │ │
│  │         │   /users   → NEW System ✓              │                   │ │
│  │         │   /orders  → Old System                │                   │ │
│  │         │   /products→ Old System                │                   │ │
│  │         │                                         │                   │ │
│  │         └─────────────────────────────────────────┘                   │ │
│  │                                                                        │ │
│  │  Phase 3: Migrate More Features                                      │ │
│  │  ──────────────────────────────                                       │ │
│  │                                                                        │ │
│  │         ┌─────────────────────────────────────────┐                   │ │
│  │         │            FACADE / PROXY               │                   │ │
│  │         │                                         │                   │ │
│  │         │   /users   → NEW System ✓              │                   │ │
│  │         │   /orders  → NEW System ✓              │                   │ │
│  │         │   /products→ Old System                │                   │ │
│  │         │                                         │                   │ │
│  │         └─────────────────────────────────────────┘                   │ │
│  │                                                                        │ │
│  │  Phase N: Complete Migration, Remove Old                             │ │
│  │  ───────────────────────────────────────                              │ │
│  │                                                                        │ │
│  │         ┌─────────────────────────────────────────┐                   │ │
│  │         │            NEW SYSTEM                   │                   │ │
│  │         │                                         │                   │ │
│  │         │   /users   → New                       │                   │ │
│  │         │   /orders  → New                       │                   │ │
│  │         │   /products→ New                       │                   │ │
│  │         │                                         │                   │ │
│  │         └─────────────────────────────────────────┘                   │ │
│  │                                                                        │ │
│  │  Old system "strangled" and removed                                  │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Minimal risk (small changes)                                            │
│  ✓ Zero downtime                                                           │
│  ✓ Continuous delivery                                                     │
│  ✓ Learn and adapt as you go                                               │
│  ✓ Can pause or rollback any piece                                         │
│  ✓ Team can work incrementally                                             │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Long migration timeline                                                 │
│  ✗ Complexity of running both systems                                      │
│  ✗ Data sync between old and new                                           │
│  ✗ Facade/proxy adds latency                                               │
│  ✗ Feature parity pressure                                                 │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Monolith to microservices migration                                      │
│  • Legacy modernization                                                     │
│  • Can't afford big bang risk                                               │
│  • Long-term migration acceptable                                           │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  CUTOVER 4: CANARY CUTOVER                                                   │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Route small percentage of traffic to new system, gradually increase │ │
│  │                                                                        │ │
│  │  Stage 1:  5% → New System                                           │ │
│  │           95% → Old System                                            │ │
│  │           Monitor metrics...                                          │ │
│  │                                                                        │ │
│  │  Stage 2: 25% → New System                                           │ │
│  │           75% → Old System                                            │ │
│  │           Monitor metrics...                                          │ │
│  │                                                                        │ │
│  │  Stage 3: 50% → New System                                           │ │
│  │           50% → Old System                                            │ │
│  │           Monitor metrics...                                          │ │
│  │                                                                        │ │
│  │  Stage 4: 100% → New System                                          │ │
│  │             0% → Old System (standby for rollback)                   │ │
│  │                                                                        │ │
│  │  Important: Data must be synchronized between systems!               │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Low risk (small blast radius)                                           │
│  ✓ Real traffic testing                                                    │
│  ✓ Gradual confidence building                                             │
│  ✓ Quick rollback (route 100% to old)                                      │
│  ✓ Metrics-driven decisions                                                │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Data sync complexity (both systems need same data)                      │
│  ✗ Longer cutover period                                                   │
│  ✗ User experience may differ by system                                    │
│  ✗ Some users hit bugs early                                               │
│                                                                              │
│  USE WHEN:                                                                   │
│  • High-risk migration                                                      │
│  • Need production validation                                               │
│  • Can synchronize data between systems                                     │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  CUTOVER 5: DARK LAUNCH / SHADOW                                             │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Mirror traffic to new system, but don't serve responses              │ │
│  │                                                                        │ │
│  │           ┌───────────────────────────────────────────────────────┐   │ │
│  │           │                     REQUEST                           │   │ │
│  │           │                        │                              │   │ │
│  │           │                        ▼                              │   │ │
│  │           │                  ┌──────────┐                         │   │ │
│  │           │                  │  ROUTER  │                         │   │ │
│  │           │                  └────┬─────┘                         │   │ │
│  │           │                       │                               │   │ │
│  │           │          ┌────────────┴────────────┐                  │   │ │
│  │           │          │                         │                  │   │ │
│  │           │          ▼                         ▼                  │   │ │
│  │           │   ┌─────────────┐          ┌─────────────┐            │   │ │
│  │           │   │ OLD SYSTEM  │          │ NEW SYSTEM  │            │   │ │
│  │           │   │             │          │   (Shadow)  │            │   │ │
│  │           │   └──────┬──────┘          └──────┬──────┘            │   │ │
│  │           │          │                        │                   │   │ │
│  │           │          ▼                        ▼                   │   │ │
│  │           │    Response to User         Logged/Compared           │   │ │
│  │           │                             (discarded)               │   │ │
│  │           │                                                       │   │ │
│  │           └───────────────────────────────────────────────────────┘   │ │
│  │                                                                        │ │
│  │  Compare: old_response vs new_response for correctness              │ │
│  │                                                                        │ │
│  │  Once confident:                                                      │ │
│  │  • Stop shadow mode                                                  │ │
│  │  • Route real traffic to new system                                  │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Zero user impact                                                        │
│  ✓ Test with real production traffic                                       │
│  ✓ Compare old vs new responses                                            │
│  ✓ Find bugs before any user sees them                                     │
│  ✓ Performance validation                                                  │
│                                                                              │
│  CONS:                                                                       │
│  ✗ 2x load on infrastructure                                               │
│  ✗ Complex for write operations (can't actually write)                    │
│  ✗ Doesn't test user-facing behavior                                       │
│  ✗ Response comparison logic needed                                        │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Major refactoring (same API, new implementation)                        │
│  • Database migration validation                                            │
│  • Risk-averse environments                                                 │
│  • Read-heavy workloads                                                     │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  CUTOVER 6: FEATURE FLAG CUTOVER                                             │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Use feature flags to switch between old and new code paths           │ │
│  │                                                                        │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │  │                                                                 │  │ │
│  │  │  SAME CODEBASE with both implementations:                      │  │ │
│  │  │                                                                 │  │ │
│  │  │  def process_order(order):                                     │  │ │
│  │  │      if feature_flag("use_new_order_system"):                 │  │ │
│  │  │          return new_order_system.process(order)               │  │ │
│  │  │      else:                                                     │  │ │
│  │  │          return legacy_order_system.process(order)            │  │ │
│  │  │                                                                 │  │ │
│  │  └─────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                        │ │
│  │  Cutover Process:                                                     │ │
│  │                                                                        │ │
│  │  1. Deploy code with both paths (flag off)                           │ │
│  │  2. Enable flag for internal users (dogfooding)                      │ │
│  │  3. Enable for 5% of users (canary)                                  │ │
│  │  4. Gradually increase to 100%                                       │ │
│  │  5. Remove old code path (cleanup)                                   │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PROS:                                                                       │
│  ✓ Instant rollback (flip flag)                                            │
│  ✓ No infrastructure changes                                               │
│  ✓ Per-user/segment control                                                │
│  ✓ Can A/B test old vs new                                                 │
│  ✓ Gradual rollout                                                         │
│                                                                              │
│  CONS:                                                                       │
│  ✗ Both code paths must coexist                                            │
│  ✗ Technical debt (if not cleaned up)                                      │
│  ✗ Testing complexity                                                      │
│  ✗ Data model must support both                                            │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Code-level changes (not infrastructure)                                  │
│  • Can maintain both code paths                                             │
│  • Need fine-grained control                                                │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  CUTOVER STRATEGIES COMPARISON                                               │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Strategy         Downtime    Risk      Rollback   Duration   Cost     │ │
│  │  ────────────────────────────────────────────────────────────────────  │ │
│  │                                                                        │ │
│  │  Big Bang         Hours       HIGH      Hours      Fast       Low      │ │
│  │                                                                        │ │
│  │  Blue-Green       Seconds     Medium    Instant    Fast       2x       │ │
│  │                                                                        │ │
│  │  Strangler Fig    None        LOW       Easy       Months     Medium   │ │
│  │                                                                        │ │
│  │  Canary           None        LOW       Quick      Days       ~1.1x    │ │
│  │                                                                        │ │
│  │  Shadow/Dark      None        NONE      N/A        Days       2x       │ │
│  │                                                                        │ │
│  │  Feature Flag     None        LOW       Instant    Days       Low      │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  RECOMMENDATION BY SCENARIO:                                                 │
│                                                                              │
│  • Simple migration, downtime OK: Big Bang                                  │
│  • Zero downtime, quick cutover: Blue-Green                                │
│  • Monolith → Microservices: Strangler Fig                                 │
│  • Database migration: Shadow + Canary                                      │
│  • Code refactoring: Feature Flag                                           │
│  • Vendor migration: Blue-Green or Canary                                   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘


================================================================================
END OF STRATEGIES COMPARISON
================================================================================

