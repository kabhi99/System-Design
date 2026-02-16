# PAYMENT GATEWAY - HIGH LEVEL DESIGN
*Part 3: Payment Flow and Idempotency*

## SECTION 3.1: DETAILED PAYMENT FLOW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  END-TO-END CARD PAYMENT FLOW                                           |
|                                                                         |
|  +-----------------------------------------------------------------+    |
|  |                                                                 |    |
|  |  Customer    Merchant    Payment     Token    Card      Issuing |    |
|  |  Browser     Server     Gateway     Vault    Network    Bank   |     |
|  |     |          |           |          |         |         |    |     |
|  |     |--1. Enter card-->|   |          |         |         |    |     |
|  |     |          |       |   |          |         |         |    |     |
|  |     |--2. Card data---------------->|          |         |    |      |
|  |     |          |       |   |          |         |         |    |     |
|  |     |<-3. Token--------------------|          |         |    |       |
|  |     |   (tok_xxx)      |   |          |         |         |    |     |
|  |     |          |       |   |          |         |         |    |     |
|  |     |--4. Pay-->|      |   |          |         |         |    |     |
|  |     |  (token)  |      |   |          |         |         |    |     |
|  |     |          |       |   |          |         |         |    |     |
|  |     |          |--5. Create Payment-->|        |         |    |      |
|  |     |          |  {token, amount}  |   |        |         |    |     |
|  |     |          |       |   |          |         |         |    |     |
|  |     |          |       |--6. Decrypt token-->|  |         |    |     |
|  |     |          |       |   |          |         |         |    |     |
|  |     |          |       |<-7. Card PAN-|        |         |    |      |
|  |     |          |       |   |          |         |         |    |     |
|  |     |          |       |--8. Authorization Request------>|    |      |
|  |     |          |       |   |          |         |         |    |     |
|  |     |          |       |   |          |    9. Check funds,     |     |
|  |     |          |       |   |          |       fraud rules     |      |
|  |     |          |       |   |          |         |         |    |     |
|  |     |          |       |<-10. Auth Response (approved/declined)|     |
|  |     |          |       |   |          |         |         |    |     |
|  |     |          |<-11. Payment result--|        |         |    |      |
|  |     |          |       |   |          |         |         |    |     |
|  |     |<-12. Redirect to success/fail   |        |         |    |      |
|  |     |          |       |   |          |         |         |    |     |
|  |     |          |       |--13. Webhook (async)-->|         |    |     |
|  |     |          |       |   |          |         |         |    |     |
|  |                                                                 |    |
|  +-----------------------------------------------------------------+    |
|                                                                         |
|  TIMELINE:                                                              |
|  Steps 1-4: ~500ms (client-side, depends on user)                       |
|  Steps 5-11: ~1-2s (payment processing)                                 |
|  Step 13: Async (within minutes)                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### INTERNAL PAYMENT PROCESSING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PAYMENT SERVICE INTERNAL FLOW                                          |
|                                                                         |
|  +-----------------------------------------------------------------+    |
|  |                                                                 |    |
|  |  1. REQUEST RECEIVED                                           |     |
|  |     POST /payments                                             |     |
|  |     {                                                          |     |
|  |       idempotency_key: "order_123_attempt_1",                  |     |
|  |       amount: 10000,  // cents                                 |     |
|  |       currency: "USD",                                         |     |
|  |       payment_method: "tok_abc123",                            |     |
|  |       capture: true                                            |     |
|  |     }                                                          |     |
|  |                                                                 |    |
|  |  2. IDEMPOTENCY CHECK                                          |     |
|  |     +-------------------------------------------------------+ |      |
|  |     | Redis: GET idempotency:{key}                         | |       |
|  |     |                                                       | |      |
|  |     | IF EXISTS:                                           | |       |
|  |     |   Return cached response (prevent duplicate)         | |       |
|  |     |                                                       | |      |
|  |     | IF NOT EXISTS:                                       | |       |
|  |     |   SET idempotency:{key} = "processing" EX 86400     | |        |
|  |     |   Continue with payment                              | |       |
|  |     +-------------------------------------------------------+ |      |
|  |                                                                 |    |
|  |  3. CREATE PAYMENT RECORD                                      |     |
|  |     +-------------------------------------------------------+ |      |
|  |     | BEGIN TRANSACTION                                    | |       |
|  |     |                                                       | |      |
|  |     | INSERT INTO payments (id, merchant_id, amount, ...)  | |       |
|  |     | VALUES (uuid, ..., 'CREATED')                        | |       |
|  |     |                                                       | |      |
|  |     | INSERT INTO payment_events                           | |       |
|  |     | VALUES (payment_id, 'CREATED', ...)                  | |       |
|  |     |                                                       | |      |
|  |     | COMMIT                                               | |       |
|  |     +-------------------------------------------------------+ |      |
|  |                                                                 |    |
|  |  4. ACQUIRE DISTRIBUTED LOCK                                   |     |
|  |     Redis: SET lock:payment:{id} = worker_id NX EX 30         |      |
|  |     (Prevents concurrent processing of same payment)          |      |
|  |                                                                 |    |
|  |  5. PROCESS WITH CARD NETWORK                                  |     |
|  |     * Detokenize card number                                  |      |
|  |     * Send to appropriate processor                           |      |
|  |     * Wait for response (with timeout)                        |      |
|  |                                                                 |    |
|  |  6. UPDATE PAYMENT STATUS                                      |     |
|  |     +-------------------------------------------------------+ |      |
|  |     | BEGIN TRANSACTION                                    | |       |
|  |     |                                                       | |      |
|  |     | UPDATE payments                                      | |       |
|  |     | SET status = 'CAPTURED',                             | |       |
|  |     |     processor_response = {...}                       | |       |
|  |     | WHERE id = ? AND version = ?                         | |       |
|  |     |                                                       | |      |
|  |     | INSERT INTO payment_events (...)                     | |       |
|  |     |                                                       | |      |
|  |     | COMMIT                                               | |       |
|  |     +-------------------------------------------------------+ |      |
|  |                                                                 |    |
|  |  7. CACHE RESPONSE FOR IDEMPOTENCY                            |      |
|  |     Redis: SET idempotency:{key} = {response} EX 86400        |      |
|  |                                                                 |    |
|  |  8. EMIT EVENT                                                 |     |
|  |     Kafka: payment.events > { payment_id, status: CAPTURED }  |      |
|  |                                                                 |    |
|  |  9. RELEASE LOCK                                               |     |
|  |     Redis: DEL lock:payment:{id}                              |      |
|  |                                                                 |    |
|  |  10. RETURN RESPONSE                                           |     |
|  |      { id: "pay_xxx", status: "captured", amount: 10000 }     |      |
|  |                                                                 |    |
|  +-----------------------------------------------------------------+    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.2: IDEMPOTENCY - THE CRITICAL REQUIREMENT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY IDEMPOTENCY IS CRITICAL                                            |
|                                                                         |
|  SCENARIO: Customer clicks "Pay" button twice                           |
|                                                                         |
|  WITHOUT IDEMPOTENCY:                                                   |
|  +-----------------------------------------------------------------+    |
|  |                                                                 |    |
|  |  Click 1 > POST /payments > $100 charged Y                    |      |
|  |  Click 2 > POST /payments > $100 charged Y (DUPLICATE!)       |      |
|  |                                                                 |    |
|  |  Customer charged $200 instead of $100!                       |      |
|  |                                                                 |    |
|  +-----------------------------------------------------------------+    |
|                                                                         |
|  WITH IDEMPOTENCY:                                                      |
|  +-----------------------------------------------------------------+    |
|  |                                                                 |    |
|  |  Click 1 > POST /payments                                     |      |
|  |            Idempotency-Key: order_123                         |      |
|  |            > $100 charged Y                                   |      |
|  |                                                                 |    |
|  |  Click 2 > POST /payments                                     |      |
|  |            Idempotency-Key: order_123 (same key)              |      |
|  |            > Return cached result (no duplicate charge)       |      |
|  |                                                                 |    |
|  |  Customer charged exactly $100 Y                              |      |
|  |                                                                 |    |
|  +-----------------------------------------------------------------+    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### IDEMPOTENCY IMPLEMENTATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  IDEMPOTENCY KEY HANDLING                                               |
|                                                                         |
|  def process_payment(request):                                          |
|      idempotency_key = request.headers['Idempotency-Key']               |
|                                                                         |
|      # Step 1: Check cache                                              |
|      cached = redis.get(f"idem:{idempotency_key}")                      |
|      if cached:                                                         |
|          if cached['status'] == 'processing':                           |
|              return 409, "Payment in progress"                          |
|          return 200, cached['response']                                 |
|                                                                         |
|      # Step 2: Mark as processing (atomic)                              |
|      set_result = redis.set(                                            |
|          f"idem:{idempotency_key}",                                     |
|          {"status": "processing"},                                      |
|          nx=True,  # Only if not exists                                 |
|          ex=86400  # 24 hour TTL                                        |
|      )                                                                  |
|                                                                         |
|      if not set_result:                                                 |
|          # Race condition: another request got there first              |
|          return 409, "Payment in progress"                              |
|                                                                         |
|      try:                                                               |
|          # Step 3: Process payment                                      |
|          result = actually_process_payment(request)                     |
|                                                                         |
|          # Step 4: Cache successful response                            |
|          redis.set(                                                     |
|              f"idem:{idempotency_key}",                                 |
|              {"status": "complete", "response": result},                |
|              ex=86400                                                   |
|          )                                                              |
|          return 200, result                                             |
|                                                                         |
|      except Exception as e:                                             |
|          # Clear idempotency key so retry is possible                   |
|          redis.delete(f"idem:{idempotency_key}")                        |
|          raise                                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### IDEMPOTENCY KEY BEST PRACTICES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT MAKES A GOOD IDEMPOTENCY KEY?                                     |
|                                                                         |
|  GOOD KEYS:                                                             |
|  * order_123_payment_1     (order ID + attempt)                         |
|  * cart_abc_checkout       (cart session)                               |
|  * invoice_456             (invoice ID)                                 |
|  * uuid-v4                  (client-generated UUID)                     |
|                                                                         |
|  BAD KEYS:                                                              |
|  * Random on every request (defeats purpose)                            |
|  * Timestamp only (not unique enough)                                   |
|  * User ID only (user might have multiple orders)                       |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  KEY SCOPE:                                                             |
|                                                                         |
|  Idempotency key is scoped to:                                          |
|  * Merchant (API key)                                                   |
|  * Endpoint                                                             |
|  * Time window (24 hours typical)                                       |
|                                                                         |
|  Same key for different merchants = different payments                  |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  RESPONSE CACHING RULES:                                                |
|                                                                         |
|  +----------------------------------------------------------------+     |
|  |                                                                |     |
|  |  First Request Result    |  Subsequent Request Returns        |      |
|  |  ------------------------------------------------------------ |      |
|  |  200 Success            |  Same 200 response (cached)         |      |
|  |  400 Bad Request        |  Process again (request was wrong) |       |
|  |  500 Server Error       |  Process again (transient failure) |       |
|  |  In Progress            |  409 Conflict                       |      |
|  |                                                                |     |
|  +----------------------------------------------------------------+     |
|                                                                         |
|  Only cache SUCCESSFUL terminal states, not errors                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.3: HANDLING FAILURE SCENARIOS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCENARIO 1: NETWORK TIMEOUT TO CARD NETWORK                            |
|  =============================================                          |
|                                                                         |
|  Problem: Sent authorization request, never got response                |
|  Is the payment charged or not? WE DON'T KNOW!                          |
|                                                                         |
|  +-----------------------------------------------------------------+    |
|  |                                                                 |    |
|  |  Gateway ---- Auth Request ----> Card Network                  |     |
|  |     |                               |                           |    |
|  |     |                               | (processes payment)       |    |
|  |     |                               |                           |    |
|  |     | <-- TIMEOUT (no response) ---|                           |     |
|  |     |                                                           |    |
|  |  Payment status = UNKNOWN                                      |     |
|  |                                                                 |    |
|  +-----------------------------------------------------------------+    |
|                                                                         |
|  SOLUTION:                                                              |
|  1. Mark payment as "PENDING_VERIFICATION"                              |
|  2. Schedule async verification job                                     |
|  3. Query card network for transaction status                           |
|  4. Reconcile based on response                                         |
|                                                                         |
|  def handle_timeout(payment_id):                                        |
|      update_status(payment_id, "PENDING_VERIFICATION")                  |
|      queue_verification_job(payment_id, delay=30)  # 30s delay          |
|                                                                         |
|  def verify_payment(payment_id):                                        |
|      payment = get_payment(payment_id)                                  |
|      # Query processor for actual status                                |
|      actual_status = processor.query_transaction(                       |
|          reference_id=payment.processor_reference                       |
|      )                                                                  |
|      if actual_status == "APPROVED":                                    |
|          update_status(payment_id, "CAPTURED")                          |
|      elif actual_status == "DECLINED":                                  |
|          update_status(payment_id, "FAILED")                            |
|      else:                                                              |
|          # Still unknown, retry later or escalate                       |
|          queue_verification_job(payment_id, delay=300)                  |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  SCENARIO 2: DATABASE FAILURE AFTER CHARGE                              |
|  =============================================                          |
|                                                                         |
|  Problem: Card charged but DB update failed                             |
|                                                                         |
|  +-----------------------------------------------------------------+    |
|  |                                                                 |    |
|  |  1. Card charged successfully Y                                |     |
|  |  2. UPDATE payments SET status = 'CAPTURED' > DB ERROR!       |      |
|  |  3. Transaction rolled back                                    |     |
|  |  4. Customer sees "failed" but money is gone!                 |      |
|  |                                                                 |    |
|  +-----------------------------------------------------------------+    |
|                                                                         |
|  SOLUTION: Write to WAL/Event log BEFORE processing                     |
|                                                                         |
|  def process_payment():                                                 |
|      # 1. Write intent to durable log                                   |
|      write_to_wal({                                                     |
|          type: "PAYMENT_INTENT",                                        |
|          payment_id: id,                                                |
|          amount: amount,                                                |
|          timestamp: now()                                               |
|      })                                                                 |
|                                                                         |
|      # 2. Process with card network                                     |
|      result = charge_card(...)                                          |
|                                                                         |
|      # 3. Write result to log                                           |
|      write_to_wal({                                                     |
|          type: "PAYMENT_RESULT",                                        |
|          payment_id: id,                                                |
|          result: result                                                 |
|      })                                                                 |
|                                                                         |
|      # 4. Update database (if fails, WAL has truth)                     |
|      update_database(...)                                               |
|                                                                         |
|  Recovery process reads WAL and reconciles database                     |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  SCENARIO 3: PARTIAL SYSTEM FAILURE                                     |
|  ===================================                                    |
|                                                                         |
|  Problem: Payment service crashes mid-processing                        |
|                                                                         |
|  SOLUTION: Distributed locking + state machine                          |
|                                                                         |
|  +-----------------------------------------------------------------+    |
|  |                                                                 |    |
|  |  1. Acquire lock: SET lock:{payment_id} NX EX 30               |     |
|  |                                                                 |    |
|  |  2. If can't acquire:                                          |     |
|  |     - Another worker processing                                |     |
|  |     - Or previous worker crashed                               |     |
|  |                                                                 |    |
|  |  3. Lock expires after 30s > next worker can take over        |      |
|  |                                                                 |    |
|  |  4. State machine ensures idempotent processing:               |     |
|  |     IF status == 'PROCESSING':                                 |     |
|  |       Check with processor if already charged                  |     |
|  |       Continue from last known state                           |     |
|  |                                                                 |    |
|  +-----------------------------------------------------------------+    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.4: RECONCILIATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY RECONCILIATION?                                                    |
|                                                                         |
|  Gateway's records vs Processor's records can diverge:                  |
|  * Network failures                                                     |
|  * Delayed processing                                                   |
|  * Chargebacks processed externally                                     |
|  * Manual adjustments by banks                                          |
|                                                                         |
|  DAILY RECONCILIATION PROCESS                                           |
|  +-----------------------------------------------------------------+    |
|  |                                                                 |    |
|  |  1. FETCH EXTERNAL RECORDS                                     |     |
|  |     * Download settlement files from each processor            |     |
|  |     * Usually available T+1 (next day)                        |      |
|  |                                                                 |    |
|  |  2. MATCH TRANSACTIONS                                         |     |
|  |     For each external transaction:                             |     |
|  |       Find matching internal record (by reference ID)         |      |
|  |       Compare: amount, status, timestamp                      |      |
|  |                                                                 |    |
|  |  3. IDENTIFY DISCREPANCIES                                     |     |
|  |                                                                 |    |
|  |     +------------------------------------------------------+  |      |
|  |     |                                                      |  |      |
|  |     |  Type          | Internal | External | Action       |  |       |
|  |     |  -------------------------------------------------- |  |       |
|  |     |  Match         | $100     | $100     | OK           |  |       |
|  |     |  Amount diff   | $100     | $95      | Investigate  |  |       |
|  |     |  Missing       | Exists   | Missing  | Query proc   |  |       |
|  |     |  Orphan        | Missing  | Exists   | Create record|  |       |
|  |     |  Status diff   | Captured | Declined | Reconcile    |  |       |
|  |     |                                                      |  |      |
|  |     +------------------------------------------------------+  |      |
|  |                                                                 |    |
|  |  4. RESOLVE DISCREPANCIES                                      |     |
|  |     * Auto-resolve known patterns                             |      |
|  |     * Flag for manual review if unclear                       |      |
|  |     * Update internal records to match truth                  |      |
|  |                                                                 |    |
|  |  5. SETTLEMENT CALCULATION                                     |     |
|  |     * Sum all captured payments                               |      |
|  |     * Subtract refunds                                        |      |
|  |     * Subtract fees                                           |      |
|  |     * = Net settlement to merchant                            |      |
|  |                                                                 |    |
|  +-----------------------------------------------------------------+    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF PART 3

