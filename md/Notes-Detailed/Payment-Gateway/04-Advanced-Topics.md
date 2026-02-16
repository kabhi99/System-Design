# PAYMENT GATEWAY - HIGH LEVEL DESIGN
*Part 4: Advanced Topics*

## SECTION 4.1: FRAUD DETECTION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FRAUD DETECTION PIPELINE                                              |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Payment Request                                                |  |
|  |       |                                                         |  |
|  |       v                                                         |  |
|  |  +---------------------------------------------------------+  |  |
|  |  |              FRAUD DETECTION ENGINE                     |  |  |
|  |  |                                                         |  |  |
|  |  |  +-------------------------------------------------+   |  |  |
|  |  |  | RULE-BASED CHECKS                               |   |  |  |
|  |  |  |                                                 |   |  |  |
|  |  |  | * Velocity limits (5 txns in 10 min)           |   |  |  |
|  |  |  | * Amount thresholds (>$10K needs review)       |   |  |  |
|  |  |  | * Geographic anomalies (USA -> Nigeria)         |   |  |  |
|  |  |  | * Known fraud patterns                         |   |  |  |
|  |  |  | * BIN (card issuer) blacklists                |   |  |  |
|  |  |  | * IP reputation                                |   |  |  |
|  |  |  +-------------------------------------------------+   |  |  |
|  |  |                        |                                |  |  |
|  |  |                        v                                |  |  |
|  |  |  +-------------------------------------------------+   |  |  |
|  |  |  | ML-BASED SCORING                                |   |  |  |
|  |  |  |                                                 |   |  |  |
|  |  |  | Features:                                       |   |  |  |
|  |  |  | * Device fingerprint                           |   |  |  |
|  |  |  | * Behavioral patterns                          |   |  |  |
|  |  |  | * Historical transaction graph                 |   |  |  |
|  |  |  | * Time of day patterns                         |   |  |  |
|  |  |  |                                                 |   |  |  |
|  |  |  | Output: Risk Score (0-100)                     |   |  |  |
|  |  |  +-------------------------------------------------+   |  |  |
|  |  |                        |                                |  |  |
|  |  |                        v                                |  |  |
|  |  |  +-------------------------------------------------+   |  |  |
|  |  |  | DECISION ENGINE                                 |   |  |  |
|  |  |  |                                                 |   |  |  |
|  |  |  | Risk < 30  -> APPROVE                          |   |  |  |
|  |  |  | Risk 30-70 -> CHALLENGE (3DS, OTP)             |   |  |  |
|  |  |  | Risk > 70  -> DECLINE                          |   |  |  |
|  |  |  |                                                 |   |  |  |
|  |  |  +-------------------------------------------------+   |  |  |
|  |  |                                                         |  |  |
|  |  +---------------------------------------------------------+  |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  LATENCY REQUIREMENT: < 100ms (inline with payment processing)        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 3D SECURE (3DS)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  3D SECURE 2.0 (Verified by Visa, Mastercard SecureCode)              |
|                                                                         |
|  Additional authentication layer for online payments                  |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  FLOW:                                                          |  |
|  |                                                                 |  |
|  |  1. Payment initiated                                          |  |
|  |  2. Gateway sends transaction to 3DS server                    |  |
|  |  3. 3DS server communicates with issuer (ACS)                 |  |
|  |  4. Issuer decides: Frictionless or Challenge                 |  |
|  |                                                                 |  |
|  |  FRICTIONLESS (Low risk):                                      |  |
|  |  * Issuer approves silently based on risk data               |  |
|  |  * No customer interaction                                    |  |
|  |  * ~90% of transactions                                       |  |
|  |                                                                 |  |
|  |  CHALLENGE (Higher risk):                                      |  |
|  |  * Customer redirected to bank's page                        |  |
|  |  * OTP, biometric, or app approval                           |  |
|  |  * ~10% of transactions                                       |  |
|  |                                                                 |  |
|  |  BENEFITS:                                                      |  |
|  |  * Liability shift to issuer for fraud                       |  |
|  |  * Lower fraud rates                                          |  |
|  |  * Required by regulations (PSD2 in EU, RBI in India)        |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.2: WEBHOOK DELIVERY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RELIABLE WEBHOOK DELIVERY                                             |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Payment                Webhook              Merchant           |  |
|  |  Service                Service              Server             |  |
|  |     |                      |                    |               |  |
|  |     |--1. Event----------->|                    |               |  |
|  |     |   (payment.captured) |                    |               |  |
|  |     |                      |                    |               |  |
|  |     |                      |--2. POST webhook-->|               |  |
|  |     |                      |                    |               |  |
|  |     |                      |<-3. 200 OK --------|               |  |
|  |     |                      |                    |               |  |
|  |     |                      |   IF FAILS:        |               |  |
|  |     |                      |   Retry with backoff               |  |
|  |     |                      |   5s, 30s, 2m, 10m, 1h, 4h, 24h   |  |
|  |     |                      |                    |               |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  WEBHOOK PAYLOAD:                                                       |
|  {                                                                     |
|    "id": "evt_abc123",                                                |
|    "type": "payment.captured",                                        |
|    "created": 1704067200,                                             |
|    "data": {                                                          |
|      "payment_id": "pay_xyz789",                                     |
|      "amount": 10000,                                                 |
|      "currency": "USD",                                               |
|      "status": "captured"                                            |
|    }                                                                   |
|  }                                                                     |
|                                                                         |
|  SIGNATURE VERIFICATION:                                                |
|  Header: X-Webhook-Signature: sha256=abc123...                        |
|                                                                         |
|  Merchant verifies:                                                    |
|  expected = HMAC-SHA256(webhook_secret, request_body)                 |
|  if signature != expected: reject                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WEBHOOK DELIVERY GUARANTEES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  AT-LEAST-ONCE DELIVERY                                                |
|                                                                         |
|  Webhooks may be delivered multiple times:                            |
|  * Network failure after merchant received                            |
|  * Merchant returned 200 but we didn't receive it                    |
|  * Retry triggered                                                     |
|                                                                         |
|  MERCHANT MUST HANDLE IDEMPOTENTLY:                                    |
|  * Use event ID to dedupe                                             |
|  * Store processed event IDs                                          |
|                                                                         |
|  def handle_webhook(event):                                           |
|      if already_processed(event['id']):                               |
|          return 200  # Acknowledge duplicate                          |
|      process_event(event)                                             |
|      mark_processed(event['id'])                                      |
|      return 200                                                        |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  ORDERING                                                               |
|                                                                         |
|  Webhooks may arrive out of order:                                    |
|  * payment.captured might arrive before payment.created              |
|                                                                         |
|  SOLUTION:                                                              |
|  * Include timestamp in event                                        |
|  * Merchant reconciles based on timestamp                            |
|  * Or: Always fetch latest state via API                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.3: SCALING AND HIGH AVAILABILITY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MULTI-REGION ARCHITECTURE                                             |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |                      GLOBAL LOAD BALANCER                      |  |
|  |                     (Route by latency/geo)                     |  |
|  |                             |                                   |  |
|  |          +------------------+------------------+               |  |
|  |          |                  |                  |                |  |
|  |          v                  v                  v                |  |
|  |   +-----------+      +-----------+      +-----------+         |  |
|  |   |  US-EAST  |      |  EU-WEST  |      | AP-SOUTH  |         |  |
|  |   |           |      |           |      |           |         |  |
|  |   | +-------+ |      | +-------+ |      | +-------+ |         |  |
|  |   | | API   | |      | | API   | |      | | API   | |         |  |
|  |   | |Gateway| |      | |Gateway| |      | |Gateway| |         |  |
|  |   | +---+---+ |      | +---+---+ |      | +---+---+ |         |  |
|  |   |     |     |      |     |     |      |     |     |         |  |
|  |   | +---v---+ |      | +---v---+ |      | +---v---+ |         |  |
|  |   | |Payment| |      | |Payment| |      | |Payment| |         |  |
|  |   | |Service| |      | |Service| |      | |Service| |         |  |
|  |   | +---+---+ |      | +---+---+ |      | +---+---+ |         |  |
|  |   |     |     |      |     |     |      |     |     |         |  |
|  |   | +---v---+ |      | +---v---+ |      | +---v---+ |         |  |
|  |   | |Postgres| |      | |Postgres| |      | |Postgres| |         |  |
|  |   | |Primary | |<---->| |Replica | |<---->| |Replica | |         |  |
|  |   | +-------+ |      | +-------+ |      | +-------+ |         |  |
|  |   +-----------+      +-----------+      +-----------+         |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  WRITE PATH: All writes go to primary (US-East)                       |
|  READ PATH: Read from nearest replica                                 |
|                                                                         |
|  CONSIDERATIONS:                                                        |
|  * Payment writes need strong consistency (go to primary)            |
|  * Dashboard reads can use replicas (slight lag OK)                  |
|  * Failover: Promote replica if primary fails                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### HANDLING TRAFFIC SPIKES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FLASH SALE SCENARIO: 10x normal traffic                              |
|                                                                         |
|  STRATEGIES:                                                            |
|                                                                         |
|  1. AUTO-SCALING                                                       |
|     * Kubernetes HPA (Horizontal Pod Autoscaler)                     |
|     * Scale based on CPU, request queue depth                        |
|     * Pre-scale before known events                                  |
|                                                                         |
|  2. RATE LIMITING                                                      |
|     * Per-merchant limits                                             |
|     * Global limits to protect infrastructure                        |
|     * Graceful degradation (queue instead of reject)                 |
|                                                                         |
|  3. CIRCUIT BREAKER                                                    |
|     * If downstream processor overloaded, fail fast                  |
|     * Don't waste resources on doomed requests                       |
|                                                                         |
|  4. QUEUING                                                            |
|     * Non-critical operations async (webhooks, emails)               |
|     * Kafka absorbs spikes                                            |
|                                                                         |
|  5. DATABASE OPTIMIZATION                                              |
|     * Connection pooling (PgBouncer)                                 |
|     * Read replicas for queries                                      |
|     * Caching (Redis) for merchant configs                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.4: LEDGER AND DOUBLE-ENTRY BOOKKEEPING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DOUBLE-ENTRY BOOKKEEPING                                              |
|                                                                         |
|  Every transaction has TWO entries that balance:                       |
|  DEBIT + CREDIT = 0                                                    |
|                                                                         |
|  EXAMPLE: $100 payment captured                                        |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Entry 1 (Debit):                                              |  |
|  |    Account: customer_liability                                 |  |
|  |    Amount: +$100 (we owe customer money we collected)         |  |
|  |                                                                 |  |
|  |  Entry 2 (Credit):                                             |  |
|  |    Account: payment_processor_receivable                      |  |
|  |    Amount: -$100 (processor will send us this money)          |  |
|  |                                                                 |  |
|  |  Net: +$100 - $100 = $0 [x]                                     |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  WHEN SETTLED TO MERCHANT:                                             |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Entry 1: customer_liability -$100 (discharged)               |  |
|  |  Entry 2: merchant_payable +$97 (net after fees)              |  |
|  |  Entry 3: fee_revenue +$3 (our cut)                           |  |
|  |                                                                 |  |
|  |  Net: -$100 + $97 + $3 = $0 [x]                                 |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  WHY DOUBLE-ENTRY?                                                      |
|  * Self-auditing (totals must balance)                               |
|  * Clear money flow trail                                             |
|  * Catch bugs immediately (imbalance = error)                        |
|  * Regulatory compliance                                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.5: INTERVIEW DISCUSSION POINTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  COMMON INTERVIEW QUESTIONS                                            |
|                                                                         |
|  Q: How do you ensure no duplicate charges?                           |
|  A: Idempotency keys + distributed locks + state machine              |
|     - Idempotency key in Redis (24hr TTL)                            |
|     - Distributed lock before processing                              |
|     - State machine prevents invalid transitions                      |
|                                                                         |
|  Q: What if card network times out?                                   |
|  A: Mark as PENDING_VERIFICATION, async reconciliation                |
|     - Store intent in WAL before calling processor                   |
|     - Query processor for actual status                              |
|     - Reconcile based on response                                    |
|                                                                         |
|  Q: How do you handle PCI compliance?                                 |
|  A: Tokenization + Network segmentation                               |
|     - Raw card data never enters application zone                    |
|     - HSM for encryption                                              |
|     - Only tokens in database                                        |
|                                                                         |
|  Q: How do you scale for flash sales?                                 |
|  A: Pre-scaling + Rate limiting + Async processing                    |
|     - Pre-scale known events                                          |
|     - Per-merchant rate limits                                        |
|     - Queue non-critical work                                        |
|                                                                         |
|  Q: How do you ensure consistency between systems?                    |
|  A: Event sourcing + Reconciliation                                   |
|     - Immutable event log (source of truth)                          |
|     - Daily reconciliation with processors                           |
|     - Double-entry bookkeeping                                       |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  KEY TRADEOFFS TO DISCUSS                                              |
|                                                                         |
|  1. SYNC vs ASYNC PROCESSING                                          |
|     Sync: Lower latency, simpler error handling                      |
|     Async: Better throughput, complex failure recovery               |
|     -> Use sync for authorization, async for settlements              |
|                                                                         |
|  2. STRONG vs EVENTUAL CONSISTENCY                                    |
|     Strong: Required for payment status                              |
|     Eventual: OK for dashboards, analytics                           |
|                                                                         |
|  3. BUILD vs BUY TOKENIZATION                                         |
|     Build: Full control, massive compliance burden                   |
|     Buy: Use Stripe/Adyen vault (reduces PCI scope)                  |
|                                                                         |
|  4. SINGLE vs MULTI-PROCESSOR                                         |
|     Single: Simpler, single point of failure                        |
|     Multi: Redundancy, smart routing, complex reconciliation        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### API DESIGN

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PAYMENT GATEWAY API                                                   |
|                                                                         |
|  CREATE PAYMENT                                                         |
|  ------------------                                                     |
|  POST /v1/payments                                                     |
|  Headers:                                                               |
|    Authorization: Bearer sk_live_xxx                                  |
|    Idempotency-Key: order_123                                         |
|                                                                         |
|  Request:                                                               |
|  {                                                                     |
|    "amount": 10000,           // cents                                |
|    "currency": "USD",                                                 |
|    "payment_method": "tok_xxx",                                      |
|    "capture": true,           // false for auth-only                 |
|    "description": "Order #123",                                      |
|    "metadata": { "order_id": "123" }                                 |
|  }                                                                     |
|                                                                         |
|  Response (201 Created):                                               |
|  {                                                                     |
|    "id": "pay_xyz789",                                                |
|    "status": "captured",      // or "authorized", "failed"           |
|    "amount": 10000,                                                   |
|    "currency": "USD",                                                 |
|    "created_at": "2024-01-01T00:00:00Z"                              |
|  }                                                                     |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  GET PAYMENT                                                            |
|  -------------                                                          |
|  GET /v1/payments/{id}                                                 |
|                                                                         |
|  CAPTURE PAYMENT                                                        |
|  ----------------                                                       |
|  POST /v1/payments/{id}/capture                                        |
|  { "amount": 10000 }  // Can be less than authorized                 |
|                                                                         |
|  REFUND PAYMENT                                                         |
|  --------------                                                         |
|  POST /v1/payments/{id}/refunds                                        |
|  { "amount": 5000, "reason": "customer_request" }                    |
|                                                                         |
|  LIST PAYMENTS                                                          |
|  -------------                                                          |
|  GET /v1/payments?status=captured&created_after=2024-01-01            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.6: SUMMARY ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PAYMENT GATEWAY - COMPLETE PICTURE                                    |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  +---------+                                                   |  |
|  |  | Client  |--> CDN/WAF --> API Gateway --> Rate Limiter      |  |
|  |  +---------+                                    |              |  |
|  |                                                 v              |  |
|  |  +----------------------------------------------------------+ |  |
|  |  |                  PAYMENT SERVICE                         | |  |
|  |  |                                                          | |  |
|  |  |  Idempotency --> State Machine --> Router --> Connector | |  |
|  |  |       |              |               |            |      | |  |
|  |  |       v              v               |            v      | |  |
|  |  |    Redis         PostgreSQL         |      Card Network | |  |
|  |  |  (cache/lock)   (transactions)      |         /Processor| |  |
|  |  |                      |              |                    | |  |
|  |  |                      v              |                    | |  |
|  |  |                   Kafka ------------+---> Webhook Service| |  |
|  |  |                   (events)                       |       | |  |
|  |  |                                                  v       | |  |
|  |  |                                           Merchant Server| |  |
|  |  +----------------------------------------------------------+ |  |
|  |                                                                 |  |
|  |  SECURITY ZONES:                                               |  |
|  |  * Public: CDN, API Gateway                                   |  |
|  |  * Application: Payment Service, Webhook Service              |  |
|  |  * CDE: Token Vault (HSM), Processor Connectors              |  |
|  |                                                                 |  |
|  |  KEY GUARANTEES:                                               |  |
|  |  * Exactly-once charging (idempotency)                        |  |
|  |  * PCI-DSS compliance (tokenization)                          |  |
|  |  * 99.99% availability (multi-region)                        |  |
|  |  * < 2s authorization latency                                 |  |
|  |  * Complete audit trail                                       |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF PAYMENT GATEWAY HLD

