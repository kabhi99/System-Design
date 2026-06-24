# PAYMENT GATEWAY - HIGH LEVEL DESIGN
*Part 3: Payment Flow and Idempotency*

## SECTION 3.1: DETAILED PAYMENT FLOW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  END-TO-END CARD PAYMENT FLOW                                           |
|                                                                         |
|  Customer   Merchant   Payment    Token     Card      Issuing           |
|  Browser    Server     Gateway    Vault     Network   Bank              |
|     |          |          |          |         |         |              |
|     |--1.Card->|          |          |         |         |              |
|     |          |          |          |         |         |              |
|     |--2.Card data------->|          |         |         |              |
|     |          |          |          |         |         |              |
|     |<-3.Token (tok_xxx)--|          |         |         |              |
|     |          |          |          |         |         |              |
|     |--4.Pay-->|          |          |         |         |              |
|     | (token)  |          |          |         |         |              |
|     |          |          |          |         |         |              |
|     |          |--5.Pay-->|          |         |         |              |
|     |          |{tok,amt} |          |         |         |              |
|     |          |          |          |         |         |              |
|     |          |          |--6.Detok>|         |         |              |
|     |          |          |          |         |         |              |
|     |          |          |<-7.PAN---|         |         |              |
|     |          |          |          |         |         |              |
|     |          |          |--8.Auth Request--->|         |              |
|     |          |          |          |         |         |              |
|     |          |          |          |         |--9.Check funds,        |
|     |          |          |          |         |    fraud rules         |
|     |          |          |          |         |         |              |
|     |          |          |<--10.Auth Response (ok/decline)             |
|     |          |          |          |         |         |              |
|     |          |<-11.Result|         |         |         |              |
|     |          |          |          |         |         |              |
|     |<-12.Redirect--------|          |         |         |              |
|     |          |          |          |         |         |              |
|     |          |--13.Webhook(async)----------->|         |              |
|     |          |          |          |         |         |              |
|                                                                         |
|  TIMELINE:                                                              |
|  Steps 1-4:  ~500ms (client-side, depends on user)                      |
|  Steps 5-11: ~1-2s (payment processing)                                 |
|  Step 13:    Async (within minutes)                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### INTERNAL PAYMENT PROCESSING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PAYMENT SERVICE INTERNAL FLOW                                          |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  1. REQUEST RECEIVED                                              |  |
|  |     POST /payments                                                |  |
|  |     {                                                             |  |
|  |       idempotency_key: "order_123_attempt_1",                     |  |
|  |       amount: 10000,  // cents                                    |  |
|  |       currency: "USD",                                            |  |
|  |       payment_method: "tok_abc123",                               |  |
|  |       capture: true                                               |  |
|  |     }                                                             |  |
|  |                                                                   |  |
|  |  2. IDEMPOTENCY CHECK                                             |  |
|  |     +-----------------------------------------------------------+ |  |
|  |     | Redis: GET idempotency:{key}                              | |  |
|  |     |                                                           | |  |
|  |     | IF EXISTS:                                                | |  |
|  |     |   Return cached response (prevent duplicate)              | |  |
|  |     |                                                           | |  |
|  |     | IF NOT EXISTS:                                            | |  |
|  |     |   SET idempotency:{key} = "processing" EX 86400           | |  |
|  |     |   Continue with payment                                   | |  |
|  |     +-----------------------------------------------------------+ |  |
|  |                                                                   |  |
|  |  3. CREATE PAYMENT RECORD                                         |  |
|  |     +-----------------------------------------------------------+ |  |
|  |     | BEGIN TRANSACTION                                         | |  |
|  |     |                                                           | |  |
|  |     | INSERT INTO payments (id, merchant_id, amount, ...)       | |  |
|  |     | VALUES (uuid, ..., 'CREATED')                             | |  |
|  |     |                                                           | |  |
|  |     | INSERT INTO payment_events                                | |  |
|  |     | VALUES (payment_id, 'CREATED', ...)                       | |  |
|  |     |                                                           | |  |
|  |     | COMMIT                                                    | |  |
|  |     +-----------------------------------------------------------+ |  |
|  |                                                                   |  |
|  |  4. ACQUIRE DISTRIBUTED LOCK                                      |  |
|  |     Redis: SET lock:payment:{id} = worker_id NX EX 30             |  |
|  |     (Prevents concurrent processing of same payment)              |  |
|  |                                                                   |  |
|  |  5. PROCESS WITH CARD NETWORK                                     |  |
|  |     * Detokenize card number                                      |  |
|  |     * Send to appropriate processor                               |  |
|  |     * Wait for response (with timeout)                            |  |
|  |                                                                   |  |
|  |  6. UPDATE PAYMENT STATUS                                         |  |
|  |     +-----------------------------------------------------------+ |  |
|  |     | BEGIN TRANSACTION                                         | |  |
|  |     |                                                           | |  |
|  |     | UPDATE payments                                           | |  |
|  |     | SET status = 'CAPTURED',                                  | |  |
|  |     |     processor_response = {...}                            | |  |
|  |     | WHERE id = ? AND version = ?                              | |  |
|  |     |                                                           | |  |
|  |     | INSERT INTO payment_events (...)                          | |  |
|  |     |                                                           | |  |
|  |     | COMMIT                                                    | |  |
|  |     +-----------------------------------------------------------+ |  |
|  |                                                                   |  |
|  |  7. CACHE RESPONSE FOR IDEMPOTENCY                                |  |
|  |     Redis: SET idempotency:{key} = {response} EX 86400            |  |
|  |                                                                   |  |
|  |  8. EMIT EVENT                                                    |  |
|  |     Kafka: payment.events > { payment_id, status: CAPTURED }      |  |
|  |                                                                   |  |
|  |  9. RELEASE LOCK                                                  |  |
|  |     Redis: DEL lock:payment:{id}                                  |  |
|  |                                                                   |  |
|  |  10. RETURN RESPONSE                                              |  |
|  |      { id: "pay_xxx", status: "captured", amount: 10000 }         |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
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
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Click 1 > POST /payments > $100 charged Y                        |  |
|  |  Click 2 > POST /payments > $100 charged Y (DUPLICATE!)           |  |
|  |                                                                   |  |
|  |  Customer charged $200 instead of $100!                           |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  WITH IDEMPOTENCY:                                                      |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Click 1 > POST /payments                                         |  |
|  |            Idempotency-Key: order_123                             |  |
|  |            > $100 charged Y                                       |  |
|  |                                                                   |  |
|  |  Click 2 > POST /payments                                         |  |
|  |            Idempotency-Key: order_123 (same key)                  |  |
|  |            > Return cached result (no duplicate charge)           |  |
|  |                                                                   |  |
|  |  Customer charged exactly $100 Y                                  |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
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
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |  First Request Result    |  Subsequent Request Returns           |   |
|  |  ------------------------------------------------------------    |   |
|  |  200 Success            |  Same 200 response (cached)            |   |
|  |  400 Bad Request        |  Process again (request was wrong)     |   |
|  |  500 Server Error       |  Process again (transient failure)     |   |
|  |  In Progress            |  409 Conflict                          |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
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
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Gateway ---- Auth Request ----> Card Network                     |  |
|  |     |                               |                             |  |
|  |     |                               | (processes payment)         |  |
|  |     |                               |                             |  |
|  |     | <-- TIMEOUT (no response) ---|                              |  |
|  |     |                                                             |  |
|  |  Payment status = UNKNOWN                                         |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
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
|  SCENARIO 2: STEP 5 SUCCEEDED, STEP 6 FAILED                            |
|  ============================================                           |
|  (THE SINGLE MOST DANGEROUS FAILURE IN PAYMENTS)                        |
|                                                                         |
|  Problem: Card network captured the funds, but our DB update failed.    |
|  Customer's card WAS charged, but our system has NO record of it.       |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Card Network state:  CAPTURED  (customer's card debited)         |  |
|  |  Our DB state:        PENDING   (we think it never happened)      |  |
|  |                                                                   |  |
|  |  Bad outcomes if mishandled:                                      |  |
|  |   - Retry blindly   -> DOUBLE CHARGE the customer                 |  |
|  |   - Mark as failed  -> customer paid, no fulfillment, chargeback  |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  KEY INSIGHT:                                                           |
|  You CANNOT do 2-phase commit across your DB and Visa/Mastercard.       |
|  Your DB is a CACHE of the card network's state.                        |
|  The card network is the SYSTEM OF RECORD.                              |
|                                                                         |
|  ============ THE 5 MECHANISMS (USED TOGETHER) ============             |
|                                                                         |
|  ----------------------------------------------------------------       |
|  MECHANISM 1: WRITE INTENT BEFORE CALLING THE NETWORK                   |
|               (WAL / Outbox pattern)                                    |
|  ----------------------------------------------------------------       |
|                                                                         |
|  Durably persist "I am about to attempt this charge" BEFORE step 5.     |
|                                                                         |
|     BEGIN TRANSACTION                                                   |
|       INSERT INTO payments (id, status, idempotency_key, amount, ...)   |
|       VALUES (?, 'PROCESSING', ?, ?, ...);                              |
|                                                                         |
|       INSERT INTO payment_events (payment_id, type)                     |
|       VALUES (?, 'AUTH_REQUESTED');                                     |
|     COMMIT;                                                             |
|                                                                         |
|     -- ONLY NOW call the card network --                                |
|                                                                         |
|  Why: if the process dies between steps 5 and 6, recovery finds the     |
|  row stuck in PROCESSING and can reconcile from the card network.       |
|  Without this row you have no evidence a charge was even attempted.     |
|                                                                         |
|  ----------------------------------------------------------------       |
|  MECHANISM 2: IDEMPOTENCY KEY ON THE CARD NETWORK CALL                  |
|  ----------------------------------------------------------------       |
|                                                                         |
|  THE mechanism that makes retries SAFE.                                 |
|                                                                         |
|     POST /charges                                                       |
|     Idempotency-Key: pay_abc123_attempt                                 |
|     { "amount": 5000, "card_token": "tok_xxx" }                         |
|                                                                         |
|  Resending the same Idempotency-Key returns the ORIGINAL response       |
|  WITHOUT re-charging the card. Stripe / Adyen / Braintree all support   |
|  this. Always pass the SAME key on every retry of the same payment.     |
|                                                                         |
|  Effect: step 5 becomes safely retryable as many times as needed.       |
|  When step 6 fails we can replay (5 + 6) as a unit, no double-charge.   |
|                                                                         |
|  ----------------------------------------------------------------       |
|  MECHANISM 3: AGGRESSIVE DURABLE RETRY ON STEP 6                        |
|  ----------------------------------------------------------------       |
|                                                                         |
|  Most DB failures are transient (failover, connection blip, restart).   |
|                                                                         |
|     try:                                                                |
|         retry_db_update(payment_id, status='CAPTURED',                  |
|                         max_attempts=5,                                 |
|                         backoff='exponential')                          |
|     except StillFailing:                                                |
|         # hand off to a durable async retry queue                       |
|         kafka.emit('payment.dlq', {                                     |
|             payment_id,                                                 |
|             idempotency_key,                                            |
|             action: 'UPDATE_STATUS_TO_CAPTURED',                        |
|             processor_response,                                         |
|         })                                                              |
|                                                                         |
|  The Kafka/SQS write IS the durable record of "unprocessed work."       |
|  An async worker drains the queue and retries until the DB recovers,    |
|  using the SAME idempotency_key so retries stay safe.                   |
|                                                                         |
|  ----------------------------------------------------------------       |
|  MECHANISM 4: RECONCILIATION JOB (THE SAFETY NET)                       |
|  ----------------------------------------------------------------       |
|                                                                         |
|  Background job that runs every ~60 seconds:                            |
|                                                                         |
|     SELECT * FROM payments                                              |
|     WHERE status = 'PROCESSING'                                         |
|       AND updated_at < NOW() - INTERVAL '2 minutes';                    |
|                                                                         |
|  For each stuck row, ASK THE CARD NETWORK FOR THE TRUTH:                |
|                                                                         |
|     GET /charges?idempotency_key=pay_abc123_attempt                     |
|                                                                         |
|     Card network response       ->  DB action                           |
|     -------------------------------------------------                   |
|     CAPTURED                    ->  UPDATE -> 'CAPTURED'                |
|     NOT_FOUND (never received)  ->  UPDATE -> 'FAILED'                  |
|     FAILED / DECLINED           ->  UPDATE -> 'FAILED'                  |
|     PENDING / authorizing       ->  retry next cycle                    |
|                                                                         |
|  Catches EVERY case where the process died between steps 5 and 6.       |
|  Also fixes drift from lost webhooks, chargebacks, manual adjustments.  |
|                                                                         |
|  ----------------------------------------------------------------       |
|  MECHANISM 5: COMPENSATING ACTION (LAST RESORT)                         |
|  ----------------------------------------------------------------       |
|                                                                         |
|  If after N hours the DB still cannot record the capture (schema        |
|  corruption, datacenter loss), do NOT strand the customer's money.      |
|                                                                         |
|  Saga-style compensation:                                               |
|    1. Issue a REFUND through the card network                           |
|       POST /refunds { charge_id: ..., idempotency_key: ... }            |
|    2. Notify customer: "transaction reversed, please try again"         |
|    3. When DB is back, mark the internal record as 'REVERSED'           |
|                                                                         |
|  This is the escape hatch when forward recovery is impossible.          |
|                                                                         |
|  ----------------------------------------------------------------       |
|  BONUS: TWO-PHASE FLOW (AUTH + CAPTURE) LIMITS THE BLAST RADIUS         |
|  ----------------------------------------------------------------       |
|                                                                         |
|  Most production systems split the card flow into two phases:           |
|                                                                         |
|     Step A: AUTH    -> hold funds on the card (NO money moves yet)      |
|     Step B: DB update (record auth_id, status='AUTHORIZED')             |
|     Step C: CAPTURE -> actually charge (only after order is ready)      |
|                                                                         |
|  If step B fails after step A: the auth simply EXPIRES in ~7 days.      |
|  No money lost, no refund needed -- safer than capture-then-DB.         |
|                                                                         |
|  ----------------------------------------------------------------       |
|  SUMMARY: HOW THE 5 MECHANISMS COMPOSE                                  |
|  ----------------------------------------------------------------       |
|                                                                         |
|   #   Mechanism              What it gives you                          |
|   ----------------------------------------------------------            |
|   1   Write intent first     "I always know I tried"                    |
|   2   Idempotency key        "Retries are free"                         |
|   3   Durable retry queue    "Crashes don't lose work"                  |
|   4   Reconciliation job     "Source of truth = card network"           |
|   5   Compensating refund    "Escape hatch when DB is dead"             |
|                                                                         |
|  GOLDEN RULE:                                                           |
|  Your DB is a CACHE of the card network's state.                        |
|  The card network is the SYSTEM OF RECORD. Design every flow            |
|  assuming the DB can disagree -- always be able to re-derive            |
|  truth from the network.                                                |
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
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  1. Acquire lock: SET lock:{payment_id} NX EX 30                  |  |
|  |                                                                   |  |
|  |  2. If can't acquire:                                             |  |
|  |     - Another worker processing                                   |  |
|  |     - Or previous worker crashed                                  |  |
|  |                                                                   |  |
|  |  3. Lock expires after 30s > next worker can take over            |  |
|  |                                                                   |  |
|  |  4. State machine ensures idempotent processing:                  |  |
|  |     IF status == 'PROCESSING':                                    |  |
|  |       Check with processor if already charged                     |  |
|  |       Continue from last known state                              |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
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
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  1. FETCH EXTERNAL RECORDS                                        |  |
|  |     * Download settlement files from each processor               |  |
|  |     * Usually available T+1 (next day)                            |  |
|  |                                                                   |  |
|  |  2. MATCH TRANSACTIONS                                            |  |
|  |     For each external transaction:                                |  |
|  |       Find matching internal record (by reference ID)             |  |
|  |       Compare: amount, status, timestamp                          |  |
|  |                                                                   |  |
|  |  3. IDENTIFY DISCREPANCIES                                        |  |
|  |                                                                   |  |
|  |     +----------------------------------------------------------+  |  |
|  |     |                                                          |  |  |
|  |     |  Type          | Internal | External | Action            |  |  |
|  |     |  --------------------------------------------------      |  |  |
|  |     |  Match         | $100     | $100     | OK                |  |  |
|  |     |  Amount diff   | $100     | $95      | Investigate       |  |  |
|  |     |  Missing       | Exists   | Missing  | Query proc        |  |  |
|  |     |  Orphan        | Missing  | Exists   | Create record     |  |  |
|  |     |  Status diff   | Captured | Declined | Reconcile         |  |  |
|  |     |                                                          |  |  |
|  |     +----------------------------------------------------------+  |  |
|  |                                                                   |  |
|  |  4. RESOLVE DISCREPANCIES                                         |  |
|  |     * Auto-resolve known patterns                                 |  |
|  |     * Flag for manual review if unclear                           |  |
|  |     * Update internal records to match truth                      |  |
|  |                                                                   |  |
|  |  5. SETTLEMENT CALCULATION                                        |  |
|  |     * Sum all captured payments                                   |  |
|  |     * Subtract refunds                                            |  |
|  |     * Subtract fees                                               |  |
|  |     * = Net settlement to merchant                                |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF PART 3

