================================================================================
         CHAPTER 9: DISTRIBUTED TRANSACTIONS
         Maintaining Consistency Across Services
================================================================================

When data spans multiple services or databases, ensuring consistency
becomes challenging. This chapter covers patterns for handling
transactions across distributed systems.


================================================================================
SECTION 9.1: THE PROBLEM
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  WHY DISTRIBUTED TRANSACTIONS ARE HARD                                │
    │                                                                         │
    │  SINGLE DATABASE:                                                      │
    │  ────────────────                                                       │
    │  BEGIN TRANSACTION;                                                    │
    │    UPDATE accounts SET balance = balance - 100 WHERE id = 1;          │
    │    UPDATE accounts SET balance = balance + 100 WHERE id = 2;          │
    │  COMMIT;                                                               │
    │                                                                         │
    │  → Either both happen or neither. ACID guarantees it.                │
    │                                                                         │
    │  DISTRIBUTED SYSTEM:                                                   │
    │  ────────────────────                                                   │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Order Service        Payment Service       Inventory Service   │  │
    │  │  (Database A)         (Database B)          (Database C)        │  │
    │  │       │                    │                      │             │  │
    │  │       ▼                    ▼                      ▼             │  │
    │  │  Create Order         Charge Card            Reserve Stock      │  │
    │  │       ✓                    ✓                      ✗             │  │
    │  │                                              (Out of stock!)    │  │
    │  │                                                                 │  │
    │  │  PROBLEM: Order created, card charged, but no stock!           │  │
    │  │  How do we undo the first two operations?                      │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  CHALLENGES:                                                           │
    │  • Network can fail between any two steps                            │
    │  • Services can crash mid-operation                                  │
    │  • No single database to rollback                                    │
    │  • Different services may use different databases                    │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 9.2: TWO-PHASE COMMIT (2PC)
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  TWO-PHASE COMMIT (2PC)                                               │
    │                                                                         │
    │  A coordinator ensures all participants commit or all abort.          │
    │                                                                         │
    │  PHASE 1: PREPARE (Voting)                                            │
    │  ───────────────────────────                                            │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │              ┌──────────────────┐                              │  │
    │  │              │   Coordinator    │                              │  │
    │  │              └────────┬─────────┘                              │  │
    │  │                       │                                         │  │
    │  │           "Can you commit?"                                    │  │
    │  │                       │                                         │  │
    │  │         ┌─────────────┼─────────────┐                          │  │
    │  │         ▼             ▼             ▼                          │  │
    │  │  ┌───────────┐ ┌───────────┐ ┌───────────┐                    │  │
    │  │  │Service A  │ │Service B  │ │Service C  │                    │  │
    │  │  │ "Yes"     │ │ "Yes"     │ │ "Yes"     │                    │  │
    │  │  └───────────┘ └───────────┘ └───────────┘                    │  │
    │  │                                                                 │  │
    │  │  Each participant:                                             │  │
    │  │  1. Executes transaction locally (but doesn't commit)         │  │
    │  │  2. Writes to WAL (can recover after crash)                   │  │
    │  │  3. Acquires locks                                            │  │
    │  │  4. Votes YES (ready) or NO (abort)                           │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  PHASE 2: COMMIT (Decision)                                           │
    │  ────────────────────────────                                           │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  IF all vote YES:                 IF any votes NO:             │  │
    │  │                                                                 │  │
    │  │  Coordinator: "COMMIT"            Coordinator: "ABORT"         │  │
    │  │         │                                │                      │  │
    │  │    ┌────┼────┐                      ┌────┼────┐                │  │
    │  │    ▼    ▼    ▼                      ▼    ▼    ▼                │  │
    │  │   A    B    C                      A    B    C                 │  │
    │  │   ✓    ✓    ✓                      ↩    ↩    ↩                │  │
    │  │                                  (rollback)                    │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  2PC PROBLEMS                                                          │
    │                                                                         │
    │  1. BLOCKING                                                           │
    │     If coordinator fails after PREPARE, participants wait forever    │
    │     Resources (locks) held until resolution                          │
    │                                                                         │
    │  2. COORDINATOR SINGLE POINT OF FAILURE                               │
    │     Coordinator crash = entire system stuck                          │
    │                                                                         │
    │  3. LATENCY                                                            │
    │     Multiple round trips: Prepare + Commit                           │
    │     All participants must respond                                    │
    │                                                                         │
    │  4. NOT PARTITION TOLERANT                                            │
    │     Network partition = blocking                                     │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  WHEN TO USE 2PC:                                                      │
    │  • Within a single datacenter                                        │
    │  • Low latency network                                               │
    │  • Strong consistency required                                       │
    │  • Limited number of participants                                    │
    │                                                                         │
    │  USED BY: XA transactions, some databases (PostgreSQL, MySQL)        │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 9.3: SAGA PATTERN
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  SAGA PATTERN                                                          │
    │                                                                         │
    │  A sequence of local transactions with compensating transactions      │
    │  for rollback. No locks held across services.                         │
    │                                                                         │
    │  KEY IDEA:                                                             │
    │  Instead of one atomic transaction across services,                   │
    │  use multiple local transactions + compensations.                     │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  E-COMMERCE ORDER SAGA                                         │  │
    │  │                                                                 │  │
    │  │  FORWARD FLOW (Happy path):                                    │  │
    │  │                                                                 │  │
    │  │  T1: Create Order (PENDING)                                    │  │
    │  │       │                                                         │  │
    │  │       ▼                                                         │  │
    │  │  T2: Reserve Inventory                                         │  │
    │  │       │                                                         │  │
    │  │       ▼                                                         │  │
    │  │  T3: Charge Payment                                            │  │
    │  │       │                                                         │  │
    │  │       ▼                                                         │  │
    │  │  T4: Update Order (CONFIRMED)                                  │  │
    │  │                                                                 │  │
    │  │  ────────────────────────────────────────────────────────────  │  │
    │  │                                                                 │  │
    │  │  COMPENSATING FLOW (If T3 fails):                             │  │
    │  │                                                                 │  │
    │  │  T3 fails: Payment declined                                    │  │
    │  │       │                                                         │  │
    │  │       ▼                                                         │  │
    │  │  C2: Release Inventory (compensate T2)                        │  │
    │  │       │                                                         │  │
    │  │       ▼                                                         │  │
    │  │  C1: Cancel Order (compensate T1)                             │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  EACH STEP HAS A COMPENSATION:                                        │
    │  ┌─────────────────────┬─────────────────────────────────────────┐   │
    │  │ Transaction         │ Compensating Transaction               │   │
    │  ├─────────────────────┼─────────────────────────────────────────┤   │
    │  │ Create Order        │ Cancel Order                            │   │
    │  │ Reserve Inventory   │ Release Inventory                       │   │
    │  │ Charge Payment      │ Refund Payment                          │   │
    │  │ Ship Order          │ Return/Refund (may not be possible!)   │   │
    │  └─────────────────────┴─────────────────────────────────────────┘   │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


SAGA EXECUTION PATTERNS
───────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  1. CHOREOGRAPHY (Event-driven)                                       │
    │  ════════════════════════════════                                       │
    │                                                                         │
    │  Services communicate via events. No central coordinator.             │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Order        Inventory       Payment        Shipping          │  │
    │  │  Service      Service         Service        Service           │  │
    │  │     │                                                           │  │
    │  │     │ OrderCreated                                             │  │
    │  │     │─────────────────►│                                       │  │
    │  │                        │ InventoryReserved                     │  │
    │  │                        │─────────────────►│                    │  │
    │  │                                           │ PaymentProcessed   │  │
    │  │                                           │────────────────►│  │  │
    │  │     │◄────────────────────────────────────────────────────────│  │
    │  │     │              OrderCompleted                              │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  PROS:                                                                 │
    │  ✓ Loosely coupled                                                   │
    │  ✓ Simple for small sagas                                            │
    │  ✓ No single point of failure                                        │
    │                                                                         │
    │  CONS:                                                                 │
    │  ✗ Hard to understand (follow the events)                           │
    │  ✗ Cyclic dependencies possible                                      │
    │  ✗ Testing is complex                                                │
    │  ✗ Hard to add new steps                                             │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  2. ORCHESTRATION (Central coordinator)                               │
    │  ═══════════════════════════════════════                                │
    │                                                                         │
    │  A saga orchestrator tells each service what to do.                  │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │               ┌────────────────────┐                           │  │
    │  │               │  Saga Orchestrator │                           │  │
    │  │               │  (Order Saga)      │                           │  │
    │  │               └────────┬───────────┘                           │  │
    │  │                        │                                        │  │
    │  │         ┌──────────────┼──────────────┐                        │  │
    │  │         ▼              ▼              ▼                        │  │
    │  │   "Reserve"       "Charge"       "Ship"                        │  │
    │  │         │              │              │                        │  │
    │  │         ▼              ▼              ▼                        │  │
    │  │  ┌───────────┐ ┌───────────┐ ┌───────────┐                    │  │
    │  │  │ Inventory │ │ Payment   │ │ Shipping  │                    │  │
    │  │  │ Service   │ │ Service   │ │ Service   │                    │  │
    │  │  └───────────┘ └───────────┘ └───────────┘                    │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ORCHESTRATOR STATE MACHINE:                                          │
    │                                                                         │
    │  PENDING ──► RESERVING_INVENTORY ──► CHARGING_PAYMENT                │
    │      │              │                       │                         │
    │      │         (fail) │                (fail) │                       │
    │      │              ▼                       ▼                         │
    │      │      RELEASING_INVENTORY   REFUNDING_PAYMENT                  │
    │      │              │                       │                         │
    │      └──────────────┴───────────────────────┴──► CANCELLED           │
    │                                                                         │
    │  PROS:                                                                 │
    │  ✓ Easy to understand (centralized logic)                           │
    │  ✓ Easy to add/modify steps                                         │
    │  ✓ Avoids cyclic dependencies                                       │
    │  ✓ Easier testing (test orchestrator)                               │
    │                                                                         │
    │  CONS:                                                                 │
    │  ✗ Orchestrator can be bottleneck                                   │
    │  ✗ More infrastructure (saga service)                               │
    │  ✗ Services coupled to orchestrator                                 │
    │                                                                         │
    │  RECOMMENDATION: Use orchestration for complex sagas                 │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


SAGA DESIGN CONSIDERATIONS
──────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  SAGA BEST PRACTICES                                                   │
    │                                                                         │
    │  1. COMPENSATIONS MUST BE IDEMPOTENT                                  │
    │  ─────────────────────────────────────                                  │
    │  May be called multiple times (retries)                               │
    │                                                                         │
    │  ✗ def release_inventory(order_id):                                  │
    │        inventory += order.quantity  # May add twice!                 │
    │                                                                         │
    │  ✓ def release_inventory(order_id):                                  │
    │        if reservation_exists(order_id):                              │
    │            inventory += order.quantity                               │
    │            delete_reservation(order_id)                              │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  2. SEMANTIC LOCKS (Countermeasure for isolation)                    │
    │  ──────────────────────────────────────────────────                     │
    │  Set a flag to indicate "in progress"                                │
    │                                                                         │
    │  Order states: PENDING → APPROVED → SHIPPED                          │
    │                                                                         │
    │  Other services check: "Is order APPROVED?"                          │
    │  If still PENDING, saga in progress, wait or reject                  │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  3. COMMUTATIVE UPDATES (When possible)                              │
    │  ─────────────────────────────────────────                              │
    │  Design operations so order doesn't matter                           │
    │                                                                         │
    │  Inventory: Reserve(5) then Reserve(3) = Reserve(3) then Reserve(5) │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  4. VERSIONING                                                         │
    │  ────────────                                                           │
    │  Include version in updates to detect stale data                     │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  5. RE-READ VALUE                                                      │
    │  ─────────────────                                                      │
    │  Re-read data before compensating to get current state               │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 9.4: TRANSACTIONAL OUTBOX PATTERN
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  THE DUAL WRITE PROBLEM                                               │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Order Service wants to:                                       │  │
    │  │  1. Save order to database                                     │  │
    │  │  2. Publish OrderCreated event to message queue               │  │
    │  │                                                                 │  │
    │  │  PROBLEM:                                                       │  │
    │  │                                                                 │  │
    │  │  def create_order(order):                                      │  │
    │  │      database.save(order)      # Step 1: Success              │  │
    │  │      message_queue.publish(    # Step 2: FAIL!                │  │
    │  │          OrderCreated(order)                                   │  │
    │  │      )                         # Crash here                    │  │
    │  │                                                                 │  │
    │  │  Result: Order in DB, but no event published!                 │  │
    │  │  Other services never know about the order.                   │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  CAN'T WE JUST SWAP THE ORDER?                                        │
    │                                                                         │
    │  def create_order(order):                                              │
    │      message_queue.publish(...)   # Step 1: Success                  │
    │      database.save(order)         # Step 2: FAIL!                    │
    │                                                                         │
    │  Now: Event published, but order not in DB!                          │
    │  Other services process an order that doesn't exist.                 │
    │                                                                         │
    │  THERE'S NO GOOD ORDER. Need transactional guarantee.                │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


OUTBOX PATTERN SOLUTION
───────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  TRANSACTIONAL OUTBOX                                                 │
    │                                                                         │
    │  Write event to an OUTBOX table in same database transaction.        │
    │  A separate process reads outbox and publishes events.               │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  1. SINGLE TRANSACTION                                         │  │
    │  │                                                                 │  │
    │  │  BEGIN TRANSACTION;                                            │  │
    │  │    INSERT INTO orders (...);                                   │  │
    │  │    INSERT INTO outbox (event_type, payload) VALUES            │  │
    │  │      ('OrderCreated', '{...}');                                │  │
    │  │  COMMIT;                                                        │  │
    │  │                                                                 │  │
    │  │  → Both writes succeed or both fail. ACID!                    │  │
    │  │                                                                 │  │
    │  │  ────────────────────────────────────────────────────────────  │  │
    │  │                                                                 │  │
    │  │  2. MESSAGE RELAY                                              │  │
    │  │                                                                 │  │
    │  │  ┌──────────────┐      ┌───────────────┐      ┌─────────────┐│  │
    │  │  │   Outbox     │ ──►  │ Message Relay │ ──► │Message Queue││  │
    │  │  │   Table      │      │ (polls/CDC)   │      │             ││  │
    │  │  └──────────────┘      └───────────────┘      └─────────────┘│  │
    │  │                                                                 │  │
    │  │  Message Relay reads outbox and publishes to queue.           │  │
    │  │  Marks events as published (or deletes them).                 │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  OUTBOX TABLE SCHEMA:                                                  │
    │                                                                         │
    │  CREATE TABLE outbox (                                                 │
    │    id UUID PRIMARY KEY,                                               │
    │    event_type VARCHAR(100),                                           │
    │    aggregate_type VARCHAR(100),  -- e.g., "Order"                    │
    │    aggregate_id VARCHAR(100),    -- e.g., order_id                   │
    │    payload JSONB,                                                      │
    │    created_at TIMESTAMP DEFAULT NOW(),                                │
    │    published_at TIMESTAMP NULL   -- NULL = not yet published         │
    │  );                                                                     │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  MESSAGE RELAY OPTIONS:                                                │
    │                                                                         │
    │  1. POLLING                                                            │
    │     SELECT * FROM outbox WHERE published_at IS NULL;                 │
    │     -- Publish each event                                             │
    │     -- UPDATE outbox SET published_at = NOW() WHERE id = ?           │
    │                                                                         │
    │     Simple but adds latency and DB load                               │
    │                                                                         │
    │  2. CHANGE DATA CAPTURE (CDC)                                         │
    │     Stream database changes to message queue                         │
    │     Tools: Debezium, Maxwell, AWS DMS                                │
    │                                                                         │
    │     ┌─────────────────────────────────────────────────────────────┐  │
    │     │ Database ──► WAL ──► Debezium ──► Kafka ──► Consumers      │  │
    │     └─────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │     PROS: Real-time, no polling overhead                             │
    │     CONS: More infrastructure                                        │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  ENSURING EXACTLY-ONCE PUBLISHING:                                    │
    │                                                                         │
    │  Message relay might crash after publish but before marking done.    │
    │  Event may be published again on retry.                               │
    │                                                                         │
    │  Solution: Make consumers idempotent (dedup by event ID)             │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 9.5: TCC (TRY-CONFIRM/CANCEL)
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  TRY-CONFIRM/CANCEL PATTERN                                           │
    │                                                                         │
    │  Variation of 2PC optimized for business transactions.                │
    │  Resources are "reserved" first, then confirmed or cancelled.         │
    │                                                                         │
    │  THREE PHASES:                                                         │
    │                                                                         │
    │  1. TRY: Reserve resources (tentative)                               │
    │     - Check business rules                                            │
    │     - Reserve but don't commit                                       │
    │     - e.g., Reserve seats, pre-auth payment                          │
    │                                                                         │
    │  2. CONFIRM: Commit all reservations                                  │
    │     - Make reservations permanent                                    │
    │     - Must be idempotent                                              │
    │                                                                         │
    │  3. CANCEL: Release all reservations                                  │
    │     - Undo tentative reservations                                    │
    │     - Must be idempotent                                              │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  FLIGHT BOOKING EXAMPLE                                        │  │
    │  │                                                                 │  │
    │  │  TRY Phase:                                                    │  │
    │  │  ┌──────────────┬──────────────┬──────────────┐               │  │
    │  │  │ Flight       │ Hotel        │ Car Rental   │               │  │
    │  │  │ Reserve seat │ Reserve room │ Reserve car  │               │  │
    │  │  │ (held 15min) │ (held 15min) │ (held 15min) │               │  │
    │  │  └──────────────┴──────────────┴──────────────┘               │  │
    │  │                                                                 │  │
    │  │  All TRY succeeded?                                            │  │
    │  │                                                                 │  │
    │  │  YES → CONFIRM Phase:                                          │  │
    │  │  ┌──────────────┬──────────────┬──────────────┐               │  │
    │  │  │ Flight       │ Hotel        │ Car Rental   │               │  │
    │  │  │ Book seat    │ Book room    │ Book car     │               │  │
    │  │  └──────────────┴──────────────┴──────────────┘               │  │
    │  │                                                                 │  │
    │  │  NO → CANCEL Phase:                                            │  │
    │  │  ┌──────────────┬──────────────┬──────────────┐               │  │
    │  │  │ Flight       │ Hotel        │ Car Rental   │               │  │
    │  │  │ Release seat │ Release room │ Release car  │               │  │
    │  │  └──────────────┴──────────────┴──────────────┘               │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  TCC vs 2PC:                                                           │
    │  • Business-level reservations, not DB locks                        │
    │  • Reservations can timeout (auto-cancel)                           │
    │  • Better availability                                               │
    │                                                                         │
    │  TCC vs SAGA:                                                          │
    │  • TCC reserves first, SAGA executes immediately                    │
    │  • TCC easier to reason about consistency                           │
    │  • SAGA may expose intermediate states                              │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
CHAPTER SUMMARY
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  DISTRIBUTED TRANSACTIONS - KEY TAKEAWAYS                             │
    │                                                                         │
    │  2PC (Two-Phase Commit)                                               │
    │  ───────────────────────                                               │
    │  • Coordinator orchestrates prepare/commit                           │
    │  • Strong consistency, ACID across services                          │
    │  • Blocking if coordinator fails                                     │
    │  • Use within datacenter, limited participants                      │
    │                                                                         │
    │  SAGA                                                                  │
    │  ────                                                                  │
    │  • Sequence of local transactions                                    │
    │  • Compensating transactions for rollback                           │
    │  • Eventually consistent                                              │
    │  • Choreography: Event-driven, decentralized                        │
    │  • Orchestration: Central coordinator (recommended)                 │
    │                                                                         │
    │  OUTBOX PATTERN                                                        │
    │  ──────────────                                                        │
    │  • Solves dual write problem                                         │
    │  • Write event to outbox in same transaction                        │
    │  • Relay process publishes to queue                                 │
    │  • Use CDC (Debezium) for real-time                                 │
    │                                                                         │
    │  TCC (Try-Confirm-Cancel)                                             │
    │  ─────────────────────────                                             │
    │  • Reserve resources in TRY phase                                    │
    │  • Confirm or Cancel based on outcome                                │
    │  • Business-level reservations (not DB locks)                       │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  DECISION GUIDE                                                        │
    │                                                                         │
    │  Need strong consistency? → 2PC (if within datacenter)              │
    │  Long-running process? → SAGA                                        │
    │  Database + message queue? → Outbox pattern                         │
    │  Resource reservation? → TCC                                         │
    │                                                                         │
    │  INTERVIEW TIP                                                         │
    │  ─────────────                                                         │
    │  When asked about transactions across services:                      │
    │  1. Acknowledge 2PC limitations                                      │
    │  2. Propose SAGA with orchestration                                  │
    │  3. Discuss compensating transactions                                │
    │  4. Mention idempotency and outbox pattern                          │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
                              END OF CHAPTER 9
================================================================================

