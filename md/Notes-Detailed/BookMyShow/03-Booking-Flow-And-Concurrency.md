# BOOKMYSHOW SYSTEM DESIGN
*Chapter 3: Booking Flow and Concurrency Control*

This is the MOST CRITICAL chapter. The booking flow must prevent double-booking
while handling thousands of concurrent users. We'll explore the complete
flow, race conditions, and locking strategies.

## SECTION 3.1: THE COMPLETE BOOKING FLOW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BOOKING FLOW OVERVIEW                                                  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  STEP 1: VIEW SEATS                                               |  |
|  |  -------------------                                              |  |
|  |  User sees available seats for a show                             |  |
|  |  Real-time updates via WebSocket                                  |  |
|  |                                                                   |  |
|  |                    v                                              |  |
|  |                                                                   |  |
|  |  STEP 2: SELECT SEATS                                             |  |
|  |  ----------------------                                           |  |
|  |  User selects 2 seats (A5, A6)                                    |  |
|  |  Clicks "Proceed to Pay"                                          |  |
|  |                                                                   |  |
|  |                    v                                              |  |
|  |                                                                   |  |
|  |  STEP 3: LOCK SEATS (Reservation)                                 |  |
|  |  ---------------------------------                                |  |
|  |  System locks seats for 10 minutes                                |  |
|  |  Creates reservation record                                       |  |
|  |  Other users see seats as "locked"                                |  |
|  |                                                                   |  |
|  |                    v                                              |  |
|  |                                                                   |  |
|  |  STEP 4: PAYMENT                                                  |  |
|  |  ----------------                                                 |  |
|  |  User completes payment                                           |  |
|  |  Timer running (10 minutes)                                       |  |
|  |                                                                   |  |
|  |                    v                                              |  |
|  |                                                                   |  |
|  |  STEP 5: CONFIRM BOOKING                                          |  |
|  |  -------------------------                                        |  |
|  |  Payment successful > Confirm booking                             |  |
|  |  Mark seats as "booked"                                           |  |
|  |  Generate ticket                                                  |  |
|  |                                                                   |  |
|  |                    v                                              |  |
|  |                                                                   |  |
|  |  STEP 6: NOTIFICATION                                             |  |
|  |  --------------------                                             |  |
|  |  Send confirmation email/SMS                                      |  |
|  |  E-ticket with QR code                                            |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### RESERVATION TIMELINE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RESERVATION LIFECYCLE                                                  |
|                                                                         |
|  Time ------------------------------------------------------------->    |
|                                                                         |
|  |                                                                      |
|  |  Seats      +--------------------------------------+                 |
|  |  A5, A6     |           LOCKED (10 min)            |                 |
|  |             |                                      |                 |
|  |  -----------+--------------------------------------+------------     |
|  |             |                                      |                 |
|  |  T=0        T=0                                  T=10min             |
|  |  Select     Lock                                 Expire              |
|  |  Seats      Seats                                or                  |
|  |                                                  Confirm             |
|  |                                                                      |
|  |  ================================================================    |
|  |                                                                      |
|  |  SCENARIO A: Payment successful at T=5min                            |
|  |  -------------------------------------------                         |
|  |  > Convert reservation to booking                                    |
|  |  > Seats permanently marked as "booked"                              |
|  |                                                                      |
|  |  SCENARIO B: Payment fails or user abandons                          |
|  |  ------------------------------------------                          |
|  |  > At T=10min, reservation expires                                   |
|  |  > Seats released back to "available"                                |
|  |  > Other users can now book them                                     |
|  |                                                                      |
+-------------------------------------------------------------------------+
```

## SECTION 3.2: THE RACE CONDITION PROBLEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE DOUBLE-BOOKING PROBLEM                                             |
|                                                                         |
|  SCENARIO: Two users try to book the same seat simultaneously           |
|                                                                         |
|  Timeline:                                                              |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Time     User A                         User B                         |
|  -----------------------------------------------------------------      |
|  T=0      SELECT * FROM seats            SELECT * FROM seats            |
|           WHERE id = 'A5'                WHERE id = 'A5'                |
|           > status = 'available'         > status = 'available'         |
|                                                                         |
|  T=1      (sees available)               (sees available)               |
|           Decides to book                Decides to book                |
|                                                                         |
|  T=2      UPDATE seats                   UPDATE seats                   |
|           SET status = 'booked'          SET status = 'booked'          |
|           WHERE id = 'A5'                WHERE id = 'A5'                |
|                                                                         |
|  T=3      > Success!                     > Success! (PROBLEM!)          |
|                                                                         |
|  RESULT: Both users think they booked the seat!                         |
|          Both get charged!                                              |
|          Only one can actually sit there!                               |
|                                                                         |
|  THIS IS A RACE CONDITION                                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHY DOES THIS HAPPEN?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE READ-MODIFY-WRITE PROBLEM                                          |
|                                                                         |
|  Without proper locking, the operation is:                              |
|                                                                         |
|  1. READ:   Check if seat is available                                  |
|  2. DECIDE: If available, proceed with booking                          |
|  3. WRITE:  Mark seat as booked                                         |
|                                                                         |
|  Between READ and WRITE, another transaction can:                       |
|  - Also READ (sees available)                                           |
|  - Also WRITE (marks as booked)                                         |
|                                                                         |
|  Both transactions see "available" because neither has committed yet.   |
|                                                                         |
|  WE NEED ATOMIC CHECK-AND-RESERVE OPERATION                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.3: LOCKING STRATEGIES

### STRATEGY 1: PESSIMISTIC LOCKING (DATABASE)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PESSIMISTIC LOCKING WITH SELECT FOR UPDATE                             |
|                                                                         |
|  "Lock the rows BEFORE reading them"                                    |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  -- Transaction A                                                 |  |
|  |  BEGIN;                                                           |  |
|  |  SELECT * FROM seats                                              |  |
|  |  WHERE show_id = 123 AND seat_id IN ('A5', 'A6')                  |  |
|  |  FOR UPDATE;  -- < Locks these rows!                              |  |
|  |                                                                   |  |
|  |  -- Rows are now locked                                           |  |
|  |  -- Check if all seats are available                              |  |
|  |  -- If yes, update status                                         |  |
|  |                                                                   |  |
|  |  UPDATE seats SET status = 'locked', locked_by = 'user_A'         |  |
|  |  WHERE show_id = 123 AND seat_id IN ('A5', 'A6');                 |  |
|  |                                                                   |  |
|  |  COMMIT;  -- < Releases locks                                     |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  -- Transaction B (runs at same time)                             |  |
|  |  BEGIN;                                                           |  |
|  |  SELECT * FROM seats                                              |  |
|  |  WHERE show_id = 123 AND seat_id IN ('A5', 'A6')                  |  |
|  |  FOR UPDATE;                                                      |  |
|  |                                                                   |  |
|  |  -- BLOCKS! Waits for Transaction A to commit                     |  |
|  |  -- ...                                                           |  |
|  |  -- Transaction A commits                                         |  |
|  |  -- Transaction B continues, sees status = 'locked'               |  |
|  |  -- Transaction B aborts (seats not available)                    |  |
|  |                                                                   |  |
|  |  ROLLBACK;                                                        |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  HOW IT WORKS:                                                          |
|  1. SELECT FOR UPDATE acquires row-level lock                           |
|  2. Other transactions wait for lock release                            |
|  3. Ensures sequential access to same rows                              |
|                                                                         |
|  PROS:                                                                  |
|  Y Simple to implement                                                  |
|  Y Database handles locking                                             |
|  Y ACID guarantees                                                      |
|                                                                         |
|  CONS:                                                                  |
|  X Holds database connection during lock                                |
|  X Can cause contention with many concurrent users                      |
|  X Deadlock risk (if locks acquired in different order)                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### STRATEGY 2: OPTIMISTIC LOCKING (VERSION CHECK)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  OPTIMISTIC LOCKING WITH VERSION COLUMN                                 |
|                                                                         |
|  "Don't lock, but check before committing"                              |
|                                                                         |
|  TABLE SCHEMA:                                                          |
|  +------------------------------------------------------------------+   |
|  | seats                                                            |   |
|  | -------------------------------------------------------------    |   |
|  | id         | show_id | status    | version | updated_at          |   |
|  | -------------------------------------------------------------    |   |
|  | A5         | 123     | available | 1       | 2024-01-15 10:00    |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  ALGORITHM:                                                             |
|                                                                         |
|  1. READ seat with current version                                      |
|     seat = SELECT * FROM seats WHERE id = 'A5';                         |
|     -- seat.version = 1                                                 |
|                                                                         |
|  2. UPDATE with version check                                           |
|     UPDATE seats                                                        |
|     SET status = 'locked', version = version + 1                        |
|     WHERE id = 'A5'                                                     |
|       AND status = 'available'                                          |
|       AND version = 1;  -- < Check version hasn't changed               |
|                                                                         |
|  3. CHECK rows affected                                                 |
|     If rows_affected = 1 > Success!                                     |
|     If rows_affected = 0 > Someone else modified, RETRY                 |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  RACE SCENARIO:                                                         |
|                                                                         |
|  User A: READ seat (version=1)                                          |
|  User B: READ seat (version=1)                                          |
|  User A: UPDATE WHERE version=1 > Success! (version now 2)              |
|  User B: UPDATE WHERE version=1 > Fails! (version is now 2)             |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  PROS:                                                                  |
|  Y No blocking, better throughput                                       |
|  Y Works well with low contention                                       |
|  Y No deadlocks                                                         |
|                                                                         |
|  CONS:                                                                  |
|  X Requires retry logic                                                 |
|  X Poor performance under high contention (many retries)                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### STRATEGY 3: REDIS DISTRIBUTED LOCKING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REDIS LOCK FOR SEAT RESERVATION                                        |
|                                                                         |
|  WHY REDIS?                                                             |
|  * Faster than database locks                                           |
|  * Built-in expiry (auto-release abandoned locks)                       |
|  * Reduces database load                                                |
|                                                                         |
|  BASIC REDIS LOCK:                                                      |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |  // Acquire lock                                                 |   |
|  |  SET seat:123:A5 user_a_reservation_id NX EX 600                 |   |
|  |      |              |                    |  |                    |   |
|  |      |              |                    |  +- Expire in 600s    |   |
|  |      |              |                    +---- Only if Not eXists |  |
|  |      |              +------------------------- Value (owner)     |   |
|  |      +---------------------------------------- Key               |   |
|  |                                                                  |   |
|  |  Returns:                                                        |   |
|  |  * "OK" > Lock acquired                                          |   |
|  |  * nil  > Lock already held by someone else                      |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  SAFE LOCK RELEASE (Lua Script):                                        |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |  -- Only release if we own the lock                              |   |
|  |  if redis.call('GET', KEYS[1]) == ARGV[1] then                   |   |
|  |      return redis.call('DEL', KEYS[1])                           |   |
|  |  else                                                            |   |
|  |      return 0                                                    |   |
|  |  end                                                             |   |
|  |                                                                  |   |
|  |  -- KEYS[1] = seat:123:A5                                        |   |
|  |  -- ARGV[1] = user_a_reservation_id                              |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  WHY LUA SCRIPT?                                                        |
|  Without it:                                                            |
|  1. GET key > returns "my_id"                                           |
|  2. IF matches, DEL key                                                 |
|  PROBLEM: Between 1 and 2, lock could expire and be acquired            |
|  by someone else. We'd delete THEIR lock!                               |
|                                                                         |
|  Lua script is ATOMIC - no race condition.                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### STRATEGY 4: ATOMIC MULTI-SEAT LOCKING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MULTI-SEAT ATOMIC RESERVATION                                          |
|                                                                         |
|  PROBLEM: User wants to book seats A5, A6, A7 together                  |
|  If A5 and A6 lock but A7 fails > Partial lock (bad UX)                 |
|  We need ALL-OR-NOTHING semantics                                       |
|                                                                         |
|  SOLUTION: Lua Script for Atomic Multi-Key Operation                    |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |  -- Atomic multi-seat reservation                                |   |
|  |  -- KEYS = seat keys to lock                                     |   |
|  |  -- ARGV[1] = reservation_id                                     |   |
|  |  -- ARGV[2] = TTL in milliseconds                                |   |
|  |                                                                  |   |
|  |  -- First, check if ALL seats are available                      |   |
|  |  for i = 1, #KEYS do                                             |   |
|  |      if redis.call('EXISTS', KEYS[i]) == 1 then                  |   |
|  |          return 0  -- At least one seat is taken                 |   |
|  |      end                                                         |   |
|  |  end                                                             |   |
|  |                                                                  |   |
|  |  -- All available, lock them all                                 |   |
|  |  for i = 1, #KEYS do                                             |   |
|  |      redis.call('SET', KEYS[i], ARGV[1], 'PX', ARGV[2])          |   |
|  |  end                                                             |   |
|  |                                                                  |   |
|  |  return 1  -- Success                                            |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  JAVA CODE:                                                             |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |  public boolean reserveSeats(                                    |   |
|  |      Long showId,                                                |   |
|  |      List<String> seatIds,                                       |   |
|  |      String reservationId,                                       |   |
|  |      Duration ttl                                                |   |
|  |  ) {                                                             |   |
|  |      List<String> keys = seatIds.stream()                        |   |
|  |          .map(s -> "seat:" + showId + ":" + s)                   |   |
|  |          .toList();                                              |   |
|  |                                                                  |   |
|  |      Long result = redisTemplate.execute(                        |   |
|  |          MULTI_SEAT_LOCK_SCRIPT,                                 |   |
|  |          keys,                                                   |   |
|  |          reservationId,                                          |   |
|  |          String.valueOf(ttl.toMillis())                          |   |
|  |      );                                                          |   |
|  |                                                                  |   |
|  |      return result == 1L;                                        |   |
|  |  }                                                               |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.4: THE COMPLETE RESERVATION FLOW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  COMPLETE SEAT RESERVATION FLOW                                         |
|                                                                         |
|  User A: Reserve seats A5, A6 for show 123                              |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |  +------+    +------------+    +------------+    +-------------+ |   |
|  |  |Client|    |API Gateway |    |Booking Svc |    |  Redis      | |   |
|  |  +--+---+    +-----+------+    +-----+------+    +----+--------+ |   |
|  |     |              |                 |                 |         |   |
|  |     | POST /reservations             |                 |         |   |
|  |     | {showId:123,seats:[A5,A6]}    |                 |          |   |
|  |     |------------->|                 |                 |         |   |
|  |     |              |                 |                 |         |   |
|  |     |              | Validate token  |                 |         |   |
|  |     |              | Rate limit Y    |                 |         |   |
|  |     |              |----------------->                 |         |   |
|  |     |              |                 |                 |         |   |
|  |     |              |                 | 1. Generate     |         |   |
|  |     |              |                 |    reservationId|         |   |
|  |     |              |                 |                 |         |   |
|  |     |              |                 | 2. Try to lock  |         |   |
|  |     |              |                 |    seats in Redis         |   |
|  |     |              |                 |---------------->|         |   |
|  |     |              |                 |                 |         |   |
|  |     |              |                 |   Lua: atomic   |         |   |
|  |     |              |                 |   multi-lock    |         |   |
|  |     |              |                 |                 |         |   |
|  |     |              |                 |<----------------|         |   |
|  |     |              |                 |   Success (1)   |         |   |
|  |     |              |                 |                 |         |   |
|  |  +------+    +------------+    +------------+    +-------------+ |   |
|  |  |Client|    |API Gateway |    |Booking Svc |    |PostgreSQL   | |   |
|  |  +--+---+    +-----+------+    +-----+------+    +----+--------+ |   |
|  |     |              |                 |                 |         |   |
|  |     |              |                 | 3. Create       |         |   |
|  |     |              |                 |    reservation  |         |   |
|  |     |              |                 |    record       |         |   |
|  |     |              |                 |---------------->|         |   |
|  |     |              |                 |                 |         |   |
|  |     |              |                 |  INSERT INTO    |         |   |
|  |     |              |                 |  reservations   |         |   |
|  |     |              |                 |                 |         |   |
|  |     |              |                 |<----------------|         |   |
|  |     |              |                 |                 |         |   |
|  |     |              | 4. Return       |                 |         |   |
|  |     |              |    reservation  |                 |         |   |
|  |     |<-------------|<----------------|                 |         |   |
|  |     |              |                 |                 |         |   |
|  |     | {                              |                 |         |   |
|  |     |   reservationId: "abc123",    |                 |          |   |
|  |     |   expiresAt: "2024-01-15T10:10:00Z",           |           |   |
|  |     |   seats: ["A5", "A6"],        |                 |          |   |
|  |     |   totalAmount: 600            |                 |          |   |
|  |     | }                              |                 |         |   |
|  |     |                                |                 |         |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### HANDLING RESERVATION EXPIRY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  AUTOMATIC LOCK EXPIRY                                                  |
|                                                                         |
|  Redis keys have TTL - they expire automatically!                       |
|                                                                         |
|  SET seat:123:A5 res_abc123 EX 600                                      |
|                              ^^^^^^                                     |
|                              600 seconds = 10 minutes                   |
|                                                                         |
|  After 10 minutes:                                                      |
|  - Redis key disappears automatically                                   |
|  - Seat appears available to other users                                |
|  - No explicit cleanup needed!                                          |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  DATABASE RESERVATION CLEANUP                                           |
|                                                                         |
|  Reservation records in PostgreSQL also need cleanup.                   |
|                                                                         |
|  OPTION 1: Scheduled Job                                                |
|  +------------------------------------------------------------------+   |
|  |  @Scheduled(fixedRate = 60000)  // Every minute                  |   |
|  |  public void cleanupExpiredReservations() {                      |   |
|  |      reservationRepository.updateExpiredReservations(            |   |
|  |          Status.EXPIRED,                                         |   |
|  |          Instant.now()                                           |   |
|  |      );                                                          |   |
|  |  }                                                               |   |
|  |                                                                  |   |
|  |  -- SQL                                                          |   |
|  |  UPDATE reservations                                             |   |
|  |  SET status = 'EXPIRED'                                          |   |
|  |  WHERE status = 'PENDING'                                        |   |
|  |    AND expires_at < NOW();                                       |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  OPTION 2: Check on Access                                              |
|  When user tries to confirm, check if expired.                          |
|  If expired, reject and ask to re-reserve.                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.5: PAYMENT AND BOOKING CONFIRMATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PAYMENT > BOOKING CONFIRMATION FLOW                                    |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |  User has reservationId: "abc123"                                |   |
|  |  Timer: 8 minutes remaining                                      |   |
|  |                                                                  |   |
|  |  1. Initiate Payment                                             |   |
|  |  ---------------------                                           |   |
|  |  POST /payments                                                  |   |
|  |  { reservationId: "abc123", amount: 600, method: "UPI" }         |   |
|  |                                                                  |   |
|  |  2. Payment Gateway Processing                                   |   |
|  |  -----------------------------                                   |   |
|  |  > Redirect to gateway / UPI intent                              |   |
|  |  > User completes payment                                        |   |
|  |  > Gateway calls webhook                                         |   |
|  |                                                                  |   |
|  |  3. Payment Callback (Webhook)                                   |   |
|  |  ------------------------------                                  |   |
|  |  POST /payments/callback                                         |   |
|  |  { paymentId: "pay_xyz", status: "SUCCESS", ... }                |   |
|  |                                                                  |   |
|  |  4. Confirm Booking (CRITICAL TRANSACTION)                       |   |
|  |  ------------------------------------------                      |   |
|  |                                                                  |   |
|  |  BEGIN TRANSACTION;                                              |   |
|  |                                                                  |   |
|  |  -- Verify reservation is still valid                            |   |
|  |  SELECT * FROM reservations                                      |   |
|  |  WHERE id = 'abc123'                                             |   |
|  |    AND status = 'PENDING'                                        |   |
|  |    AND expires_at > NOW()                                        |   |
|  |  FOR UPDATE;                                                     |   |
|  |                                                                  |   |
|  |  IF NOT FOUND > Payment refund, return error                     |   |
|  |                                                                  |   |
|  |  -- Update reservation to confirmed                              |   |
|  |  UPDATE reservations SET status = 'CONFIRMED'                    |   |
|  |  WHERE id = 'abc123';                                            |   |
|  |                                                                  |   |
|  |  -- Create booking record                                        |   |
|  |  INSERT INTO bookings (reservation_id, user_id, ...)             |   |
|  |  VALUES ('abc123', 'user_A', ...);                               |   |
|  |                                                                  |   |
|  |  -- Update seat status to BOOKED (permanent)                     |   |
|  |  UPDATE show_seats SET status = 'BOOKED', booking_id = ...       |   |
|  |  WHERE show_id = 123 AND seat_id IN ('A5', 'A6');                |   |
|  |                                                                  |   |
|  |  -- Record payment                                               |   |
|  |  INSERT INTO payments (booking_id, amount, ...)                  |   |
|  |  VALUES (...);                                                   |   |
|  |                                                                  |   |
|  |  COMMIT;                                                         |   |
|  |                                                                  |   |
|  |  5. Post-Booking Actions (Async)                                 |   |
|  |  ----------------------------------                              |   |
|  |  > Publish BookingConfirmed event to Kafka                       |   |
|  |  > Delete Redis locks (cleanup)                                  |   |
|  |  > Send confirmation email/SMS                                   |   |
|  |  > Generate e-ticket                                             |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.6: HANDLING EDGE CASES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  EDGE CASE 1: Payment Success but Reservation Expired                   |
|  =======================================================                |
|                                                                         |
|  Scenario:                                                              |
|  - User reserves at 10:00, expires at 10:10                             |
|  - User starts payment at 10:08                                         |
|  - Payment completes at 10:12 (after expiry!)                           |
|                                                                         |
|  Solution:                                                              |
|  1. Check reservation validity before confirming                        |
|  2. If expired > Initiate refund                                        |
|  3. Ask user to re-reserve (if seats still available)                   |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  EDGE CASE 2: Redis Lock Expired but User Still in Payment              |
|  ===========================================================            |
|                                                                         |
|  Scenario:                                                              |
|  - Redis TTL: 10 minutes                                                |
|  - User stuck in slow payment flow                                      |
|  - Redis lock expires, another user books the seats!                    |
|                                                                         |
|  Prevention:                                                            |
|  1. Set Redis TTL slightly longer than reservation time                 |
|     (e.g., 12 minutes vs 10 minutes)                                    |
|  2. Extend lock when payment is initiated                               |
|  3. Always verify DB state before confirming                            |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  EDGE CASE 3: Payment Gateway Timeout                                   |
|  =====================================                                  |
|                                                                         |
|  Scenario:                                                              |
|  - Payment initiated, no callback received                              |
|  - Did payment succeed or fail?                                         |
|                                                                         |
|  Solution:                                                              |
|  1. Query payment gateway for status                                    |
|  2. Reconciliation job checks pending payments                          |
|  3. If SUCCESS > confirm booking                                        |
|  4. If FAILED > release reservation                                     |
|  5. If UNKNOWN > manual review + customer support                       |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  EDGE CASE 4: Duplicate Payment Callbacks                               |
|  ========================================                               |
|                                                                         |
|  Scenario:                                                              |
|  - Gateway sends webhook twice (network retry)                          |
|  - Must not double-book or double-charge                                |
|                                                                         |
|  Solution: IDEMPOTENCY                                                  |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |  // Check if already processed                                   |   |
|  |  if (paymentRepository.exists(paymentId)) {                      |   |
|  |      return existingPaymentResult;  // Idempotent response       |   |
|  |  }                                                               |   |
|  |                                                                  |   |
|  |  // Or use idempotency key in Redis                              |   |
|  |  String key = "payment:" + paymentId;                            |   |
|  |  Boolean isNew = redis.setIfAbsent(key, "processing", 1 hour);   |   |
|  |  if (!isNew) {                                                   |   |
|  |      return waitForAndReturnExistingResult(paymentId);           |   |
|  |  }                                                               |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BOOKING FLOW - KEY TAKEAWAYS                                           |
|                                                                         |
|  THE PROBLEM                                                            |
|  -----------                                                            |
|  * Race conditions lead to double-booking                               |
|  * Need atomic check-and-reserve                                        |
|  * Must handle abandoned reservations                                   |
|                                                                         |
|  LOCKING STRATEGIES                                                     |
|  -------------------                                                    |
|  * Pessimistic (SELECT FOR UPDATE): Simple, blocks others               |
|  * Optimistic (version check): No blocking, needs retries               |
|  * Redis locks: Fast, auto-expiry, distributed                          |
|                                                                         |
|  THE FLOW                                                               |
|  --------                                                               |
|  1. User selects seats                                                  |
|  2. System locks seats (Redis) + creates reservation (DB)               |
|  3. User completes payment                                              |
|  4. System confirms booking in DB transaction                           |
|  5. Async: notifications, ticket generation                             |
|                                                                         |
|  CRITICAL POINTS                                                        |
|  ---------------                                                        |
|  * Use Lua scripts for atomic multi-seat locking                        |
|  * Set appropriate TTLs for auto-cleanup                                |
|  * Always verify reservation validity before confirming                 |
|  * Implement idempotency for payment callbacks                          |
|                                                                         |
|  INTERVIEW TIP                                                          |
|  -------------                                                          |
|  This is THE most important chapter for ticket booking design.          |
|  Be ready to draw the sequence diagram and explain race conditions.     |
|  Discuss trade-offs between locking strategies.                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 3

