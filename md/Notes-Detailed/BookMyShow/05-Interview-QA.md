# BOOKMYSHOW SYSTEM DESIGN
*Chapter 5: Interview Questions and Answers*

This chapter covers common interview questions about ticket booking systems
with detailed answers and talking points.

## SECTION 5.1: CORE DESIGN QUESTIONS

### Q1: HOW DO YOU PREVENT DOUBLE-BOOKING?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER FRAMEWORK                                                       |
|                                                                         |
|  "Double-booking is the #1 problem in ticket systems. I'd use a         |
|   multi-layered approach:"                                              |
|                                                                         |
|  1. FIRST LINE: REDIS DISTRIBUTED LOCK                                  |
|  -------------------------------------                                  |
|  "When user selects seats, I use Redis SET NX with TTL to               |
|   atomically lock the seats. The Lua script ensures all-or-nothing      |
|   locking for multiple seats."                                          |
|                                                                         |
|  2. SECOND LINE: DATABASE CONSTRAINT                                    |
|  ------------------------------------                                   |
|  "The database has a unique constraint on (show_id, seat_number).       |
|   Even if Redis fails, the database prevents duplicates."               |
|                                                                         |
|  3. THIRD LINE: OPTIMISTIC LOCKING                                      |
|  ----------------------------------                                     |
|  "I use a version column in the seats table. UPDATE only succeeds       |
|   if version matches, preventing concurrent modifications."             |
|                                                                         |
|  KEY CODE TO MENTION:                                                   |
|  ---------------------                                                  |
|  -- Redis atomic lock                                                   |
|  SET seat:show123:A5 reservation_abc NX EX 600                          |
|                                                                         |
|  -- Database check                                                      |
|  UPDATE show_seats SET status='LOCKED', version=version+1               |
|  WHERE show_id=123 AND seat_number='A5'                                 |
|    AND status='AVAILABLE' AND version=1;                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q2: HOW DO YOU HANDLE FLASH SALES?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCENARIO: Concert tickets go on sale at 10 AM. 1 million users.        |
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  1. VIRTUAL WAITING ROOM                                                |
|  ------------------------                                               |
|  "I'd implement a waiting room at the API Gateway level.                |
|   Users get a position in queue, and we let them in at a                |
|   controlled rate (e.g., 1000 users/second)."                           |
|                                                                         |
|  Implementation:                                                        |
|  - Redis sorted set with timestamp as score                             |
|  - ZADD waiting_room <timestamp> <user_id>                              |
|  - Periodically remove oldest N entries and grant access                |
|                                                                         |
|  2. RATE LIMITING                                                       |
|  ----------------                                                       |
|  "Aggressive rate limiting per user and per IP.                         |
|   Token bucket algorithm with Redis."                                   |
|                                                                         |
|  3. PRE-COMPUTED SEAT COUNTS                                            |
|  -----------------------------                                          |
|  "Before flash sale, I'd compute available seat count.                  |
|   If count = 0, immediately reject without hitting DB."                 |
|                                                                         |
|  4. CIRCUIT BREAKER                                                     |
|  -------------------                                                    |
|  "If downstream services are overwhelmed, circuit breaker               |
|   opens and returns 'try again later' instead of cascading failure."    |
|                                                                         |
|  5. AUTO-SCALING                                                        |
|  ----------------                                                       |
|  "Pre-scale infrastructure before announced sale time.                  |
|   Use Kubernetes HPA for auto-scaling during the event."                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q3: WHAT IF PAYMENT SUCCEEDS BUT BOOKING CONFIRMATION FAILS?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  "This is a distributed transaction problem. I'd handle it with:"       |
|                                                                         |
|  1. SAGA PATTERN WITH COMPENSATION                                      |
|  ---------------------------------                                      |
|  If booking confirmation fails after payment:                           |
|  - Log the failure with full context                                    |
|  - Trigger automatic refund via payment gateway                         |
|  - Notify user of the issue                                             |
|                                                                         |
|  2. IDEMPOTENCY KEYS                                                    |
|  ---------------------                                                  |
|  "Every payment has an idempotency key. If confirmation                 |
|   fails and user retries, I check the key and resume                    |
|   from where it failed, not recharge."                                  |
|                                                                         |
|  3. RECONCILIATION JOB                                                  |
|  ----------------------                                                 |
|  "A background job runs every 5 minutes to find:                        |
|   - Payments with status=SUCCESS but no booking                         |
|   - It either completes the booking or initiates refund"                |
|                                                                         |
|  4. TRANSACTIONAL OUTBOX                                                |
|  -------------------------                                              |
|  "I write both booking and payment event to outbox table                |
|   in same DB transaction. A relay reads outbox and                      |
|   publishes to Kafka, ensuring at-least-once delivery."                 |
|                                                                         |
|  CODE EXAMPLE:                                                          |
|  --------------                                                         |
|  BEGIN TRANSACTION;                                                     |
|    INSERT INTO bookings (...);                                          |
|    INSERT INTO outbox (event_type, payload) VALUES                      |
|      ('BOOKING_CONFIRMED', {...});                                      |
|  COMMIT;                                                                |
|  -- Even if Kafka publish fails, event is in outbox                     |
|  -- Relay will retry until published                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q4: HOW DO YOU HANDLE SEAT SELECTION UI IN REAL-TIME?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  "I'd use a combination of initial load and real-time updates:"         |
|                                                                         |
|  1. INITIAL LOAD                                                        |
|  ----------------                                                       |
|  "When user opens seat map, I fetch current availability from           |
|   Redis (bitmap of seat status). This is O(1) lookup."                  |
|                                                                         |
|  2. REAL-TIME UPDATES VIA WEBSOCKET                                     |
|  ---------------------------------                                      |
|  "Client establishes WebSocket connection to Booking Service.           |
|   When any seat status changes (locked/booked), I publish               |
|   to a Redis Pub/Sub channel for that show. All connected               |
|   clients receive the update."                                          |
|                                                                         |
|  Flow:                                                                  |
|  User A books seat A5                                                   |
|     v                                                                   |
|  Booking Service updates Redis                                          |
|     v                                                                   |
|  Publishes to channel: show:123:updates                                 |
|     v                                                                   |
|  WebSocket server receives, broadcasts to all clients viewing show 123  |
|     v                                                                   |
|  User B's UI updates seat A5 to "locked"                                |
|                                                                         |
|  3. OPTIMISTIC UI                                                       |
|  -----------------                                                      |
|  "When user clicks seat, I immediately show it as 'selected'            |
|   on their UI while the lock request is in progress.                    |
|   If lock fails, I show an error and revert."                           |
|                                                                         |
|  4. POLLING FALLBACK                                                    |
|  ------------------                                                     |
|  "For clients that can't use WebSocket, I fall back to                  |
|   polling every 5 seconds."                                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.2: FOLLOW-UP QUESTIONS

### Q5: WHY REDIS + DATABASE? ISN'T THAT REDUNDANT?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  "They serve different purposes:"                                       |
|                                                                         |
|  REDIS:                                                                 |
|  - Speed: Sub-millisecond seat lock                                     |
|  - Ephemeral: Auto-expiry handles abandoned reservations                |
|  - Real-time: Powers live seat map updates                              |
|  - Reduces DB load                                                      |
|                                                                         |
|  DATABASE:                                                              |
|  - Source of truth: Permanent booking record                            |
|  - ACID: Transactional consistency                                      |
|  - Durability: Survives Redis failure                                   |
|  - Audit trail: Historical data                                         |
|                                                                         |
|  "Think of Redis as the fast path, database as the durable path.        |
|   If Redis fails, system still works (just slower)."                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q6: WHAT HAPPENS IF REDIS GOES DOWN?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  "I'd design for Redis failure:"                                        |
|                                                                         |
|  1. HIGH AVAILABILITY                                                   |
|  ---------------------                                                  |
|  "Use Redis Cluster with multiple replicas.                             |
|   If primary fails, replica takes over automatically."                  |
|                                                                         |
|  2. FALLBACK TO DATABASE LOCKING                                        |
|  ---------------------------------                                      |
|  "If Redis is unavailable, fall back to SELECT FOR UPDATE.              |
|   Slower but still works."                                              |
|                                                                         |
|  if (!redis.isAvailable()) {                                            |
|      // Fall back to database pessimistic lock                          |
|      SELECT * FROM show_seats WHERE ... FOR UPDATE;                     |
|  }                                                                      |
|                                                                         |
|  3. CIRCUIT BREAKER                                                     |
|  -------------------                                                    |
|  "Circuit breaker detects Redis failures and switches to                |
|   fallback path automatically, prevents cascading failures."            |
|                                                                         |
|  4. GRACEFUL DEGRADATION                                                |
|  -------------------------                                              |
|  "Maybe search/browse works, booking is temporarily slower.             |
|   Better than complete outage."                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q7: HOW WOULD YOU HANDLE CANCELLATION AND REFUNDS?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  1. CANCELLATION POLICY                                                 |
|  -----------------------                                                |
|  "First, define business rules:                                         |
|   - Full refund if cancelled 24+ hours before show                      |
|   - 50% refund if 4-24 hours before                                     |
|   - No refund within 4 hours"                                           |
|                                                                         |
|  2. CANCELLATION FLOW                                                   |
|  ---------------------                                                  |
|  a. User requests cancellation                                          |
|  b. Validate booking exists and is cancellable                          |
|  c. Calculate refund amount based on policy                             |
|  d. BEGIN TRANSACTION                                                   |
|     - Update booking status = 'CANCELLED'                               |
|     - Update show_seats status = 'AVAILABLE'                            |
|     - Create refund record                                              |
|     COMMIT                                                              |
|  e. Initiate refund via payment gateway                                 |
|  f. Send confirmation email                                             |
|                                                                         |
|  3. REFUND HANDLING                                                     |
|  -------------------                                                    |
|  "Refunds are async. I create a refund record and process               |
|   via queue. If gateway fails, retry with exponential backoff."         |
|                                                                         |
|  4. RELEASE SEATS IMMEDIATELY                                           |
|  -----------------------------                                          |
|  "Critical: seats become available immediately after                    |
|   cancellation, regardless of refund status."                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q8: HOW DO YOU DESIGN FOR MULTIPLE CITIES/REGIONS?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  1. SHARDING BY CITY                                                    |
|  --------------------                                                   |
|  "Each major city gets its own shard. Venues, shows, bookings           |
|   for Mumbai stay on Mumbai shard."                                     |
|                                                                         |
|  2. ROUTING LAYER                                                       |
|  -----------------                                                      |
|  "API Gateway determines city from request (user's selected city        |
|   or location) and routes to appropriate shard."                        |
|                                                                         |
|  3. SHARED DATA                                                         |
|  -------------                                                          |
|  "Movies catalog is global - replicated to all shards.                  |
|   Users table can be in separate shared database."                      |
|                                                                         |
|  4. GEO-DISTRIBUTED DEPLOYMENT                                          |
|  ------------------------------                                         |
|  "For global scale, deploy in multiple regions.                         |
|   Users in India hit India datacenter.                                  |
|   Users in US hit US datacenter."                                       |
|                                                                         |
|  DIAGRAM:                                                               |
|  ---------                                                              |
|  India DC                      US DC                                    |
|  +----------------+           +----------------+                        |
|  | Indian cities  |           | US cities      |                        |
|  | shards         |           | shards         |                        |
|  +----------------+           +----------------+                        |
|           |                           |                                 |
|           +---------------------------+                                 |
|                       |                                                 |
|              Movies catalog (global)                                    |
|              User database (global)                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.3: DEEP DIVE QUESTIONS

### Q9: EXPLAIN REDLOCK ALGORITHM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  "Redlock is a distributed locking algorithm for Redis clusters.        |
|   It addresses the problem of single Redis instance failure."           |
|                                                                         |
|  HOW IT WORKS:                                                          |
|  ----------------                                                       |
|  1. Get current timestamp T1                                            |
|  2. Try to acquire lock on N Redis instances sequentially               |
|     (using SET NX EX)                                                   |
|  3. Get current timestamp T2                                            |
|  4. Lock is acquired if:                                                |
|     - Majority of instances (N/2 + 1) return success                    |
|     - Total time (T2 - T1) < lock TTL                                   |
|  5. If lock acquired, validity = TTL - (T2 - T1)                        |
|  6. If lock fails, unlock all instances                                 |
|                                                                         |
|  EXAMPLE WITH 5 REDIS NODES:                                            |
|  -----------------------------                                          |
|  Need 3/5 successes for lock                                            |
|                                                                         |
|  Node 1: SET lock:A5 xyz NX EX 10 > OK                                  |
|  Node 2: SET lock:A5 xyz NX EX 10 > OK                                  |
|  Node 3: SET lock:A5 xyz NX EX 10 > FAIL (already locked)               |
|  Node 4: SET lock:A5 xyz NX EX 10 > OK                                  |
|  Node 5: SET lock:A5 xyz NX EX 10 > FAIL                                |
|                                                                         |
|  Result: 3 successes > Lock acquired!                                   |
|                                                                         |
|  CAVEATS:                                                               |
|  ----------                                                             |
|  "Redlock is controversial. Martin Kleppmann wrote about its            |
|   issues with clock drift. For our use case, single-instance Redis      |
|   with database fallback is usually sufficient."                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q10: HOW DO YOU HANDLE 10X NORMAL TRAFFIC?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  "I'd prepare in multiple layers:"                                      |
|                                                                         |
|  1. INFRASTRUCTURE                                                      |
|  -----------------                                                      |
|  - Pre-scale before known events (blockbuster release)                  |
|  - Configure Kubernetes HPA for auto-scaling                            |
|  - Increase database connection pool                                    |
|  - Add more Redis cluster nodes                                         |
|                                                                         |
|  2. CACHING                                                             |
|  ----------                                                             |
|  - Cache movie details, venue info aggressively                         |
|  - Use CDN for all static content                                       |
|  - Cache show listings (invalidate on changes)                          |
|                                                                         |
|  3. RATE LIMITING                                                       |
|  ----------------                                                       |
|  - Stricter rate limits during peak                                     |
|  - Virtual waiting room for booking flow                                |
|                                                                         |
|  4. GRACEFUL DEGRADATION                                                |
|  -------------------------                                              |
|  - Disable non-essential features (recommendations)                     |
|  - Serve cached data if real-time unavailable                           |
|  - Queue non-critical operations (analytics, emails)                    |
|                                                                         |
|  5. LOAD TESTING                                                        |
|  ----------------                                                       |
|  - Regular load tests simulating 10x traffic                            |
|  - Identify bottlenecks before they hit production                      |
|  - Chaos engineering to test failure scenarios                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.4: QUICK-FIRE QUESTIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: What database would you use?                                        |
|  A: PostgreSQL for ACID compliance, row-level locking                   |
|                                                                         |
|  Q: How long should seat lock last?                                     |
|  A: 10-15 minutes (enough for payment, not too long to block others)    |
|                                                                         |
|  Q: SQL or NoSQL for this system?                                       |
|  A: SQL (PostgreSQL). Need ACID transactions for bookings.              |
|     NoSQL for cache (Redis), search (Elasticsearch)                     |
|                                                                         |
|  Q: How do you generate booking number?                                 |
|  A: BMS + Date + Sequence: BMS20240115000001                            |
|     Or UUID for distributed systems                                     |
|                                                                         |
|  Q: What if two users click same seat at exact same moment?             |
|  A: Only one Redis SET NX succeeds. Loser gets "seat unavailable"       |
|                                                                         |
|  Q: How do you handle timezone issues?                                  |
|  A: Store all times in UTC. Convert to local timezone in UI.            |
|     Show time is based on venue's timezone.                             |
|                                                                         |
|  Q: How do you sync Redis with Database?                                |
|  A: Write-through: Update Redis, then DB in transaction                 |
|     Or: Update DB, publish event, consumer updates Redis                |
|                                                                         |
|  Q: What metrics would you monitor?                                     |
|  A: - Booking success rate                                              |
|     - Seat lock success rate                                            |
|     - Payment failure rate                                              |
|     - API latency (p50, p95, p99)                                       |
|     - Redis hit rate                                                    |
|     - Database connection pool usage                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  INTERVIEW PREPARATION CHECKLIST                                        |
|                                                                         |
|  Y Understand the complete booking flow                                 |
|  Y Explain race conditions and solutions                                |
|  Y Know Redis locking with Lua scripts                                  |
|  Y Discuss database design and indexing                                 |
|  Y Handle edge cases (payment failures, timeouts)                       |
|  Y Explain scaling strategies (replicas, sharding)                      |
|  Y Real-time updates with WebSocket                                     |
|  Y Flash sale handling                                                  |
|                                                                         |
|  KEY DIFFERENTIATORS                                                    |
|  ---------------------                                                  |
|  * Multi-layer locking (Redis + DB)                                     |
|  * Idempotency for all critical operations                              |
|  * Saga pattern for distributed transactions                            |
|  * Graceful degradation under load                                      |
|                                                                         |
|  COMMON MISTAKES TO AVOID                                               |
|  -------------------------                                              |
|  X Ignoring race conditions                                             |
|  X Not discussing seat lock expiry                                      |
|  X Forgetting about payment edge cases                                  |
|  X Over-complicating when simple solution works                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 5

