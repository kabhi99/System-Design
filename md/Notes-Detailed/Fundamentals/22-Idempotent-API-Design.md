# CHAPTER 22: IDEMPOTENT API DESIGN
*Making POST/PUT Operations Safe to Retry*

Idempotency is critical for building reliable distributed systems.
This chapter consolidates patterns for making non-idempotent operations safe.

## SECTION 22.1: UNDERSTANDING IDEMPOTENCY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS IDEMPOTENCY?                                                  |
|                                                                         |
|  An operation is idempotent if calling it multiple times              |
|  produces the same result as calling it once.                         |
|                                                                         |
|  Mathematically: f(f(x)) = f(x)                                       |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  NATURALLY IDEMPOTENT:                                         |  |
|  |                                                                 |  |
|  |  GET /users/123           -> Always returns same user          |  |
|  |  PUT /users/123 {name}    -> Sets name to same value           |  |
|  |  DELETE /users/123        -> User gone (already gone = same)   |  |
|  |                                                                 |  |
|  |  NOT NATURALLY IDEMPOTENT:                                     |  |
|  |                                                                 |  |
|  |  POST /orders             -> Creates NEW order each time!      |  |
|  |  POST /payments           -> Charges card each time!           |  |
|  |  POST /emails/send        -> Sends duplicate emails!           |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  HTTP METHOD IDEMPOTENCY:                                              |
|  +---------------------------------------------------------------+    |
|  | Method | Idempotent | Safe | Notes                           |    |
|  +--------+------------+------+---------------------------------+    |
|  | GET    | Yes        | Yes  | Read-only                       |    |
|  | HEAD   | Yes        | Yes  | Read-only                       |    |
|  | PUT    | Yes        | No   | Full replacement                |    |
|  | DELETE | Yes        | No   | Delete (already deleted = ok)   |    |
|  | POST   | NO         | No   | Creates new resource            |    |
|  | PATCH  | NO         | No   | Depends on operation            |    |
|  +---------------------------------------------------------------+    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHY IDEMPOTENCY MATTERS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE NETWORK IS UNRELIABLE                                             |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  SCENARIO: Payment request                                     |  |
|  |                                                                 |  |
|  |  Client ---- POST /payments ----> Server                       |  |
|  |     |                               |                           |  |
|  |     |                               | (processes payment [x])    |  |
|  |     |                               |                           |  |
|  |     | <---- TIMEOUT --------------- | (response lost!)        |  |
|  |     |                                                           |  |
|  |  Client thinks: "Failed, let me retry"                         |  |
|  |                                                                 |  |
|  |  Client ---- POST /payments ----> Server                       |  |
|  |                                       |                         |  |
|  |                                       | (charges AGAIN! 💸)    |  |
|  |                                                                 |  |
|  |  RESULT: Customer charged twice! 😱                           |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  FAILURE MODES THAT CAUSE RETRIES:                                    |
|  * Network timeout                                                     |
|  * Load balancer retry                                                |
|  * Client retry (mobile app reconnect)                               |
|  * Message queue redelivery                                          |
|  * Kubernetes pod restart mid-request                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 22.2: IDEMPOTENCY KEY PATTERN

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE SOLUTION: IDEMPOTENCY KEYS                                        |
|                                                                         |
|  Client sends a unique key with each logical operation.               |
|  Server uses this key to detect and deduplicate retries.              |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  REQUEST 1:                                                     |  |
|  |  POST /payments                                                 |  |
|  |  Idempotency-Key: ord_123_pay_1                                |  |
|  |  { "amount": 100, "card": "..." }                              |  |
|  |                                                                 |  |
|  |  Server: Key not seen -> Process payment -> Return 200           |  |
|  |                                                                 |  |
|  |  ----------------------------------------------------------    |  |
|  |                                                                 |  |
|  |  REQUEST 2 (retry, same key):                                  |  |
|  |  POST /payments                                                 |  |
|  |  Idempotency-Key: ord_123_pay_1  <- SAME KEY                    |  |
|  |  { "amount": 100, "card": "..." }                              |  |
|  |                                                                 |  |
|  |  Server: Key exists -> Return cached 200 (no reprocessing!)    |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### IMPLEMENTATION FLOW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  IDEMPOTENCY KEY HANDLING FLOW                                         |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Request arrives with Idempotency-Key header                   |  |
|  |         |                                                       |  |
|  |         v                                                       |  |
|  |  +---------------------------------------------------------+  |  |
|  |  | Step 1: Check cache (Redis)                             |  |  |
|  |  |         GET idem:{key}                                  |  |  |
|  |  +---------------------------------------------------------+  |  |
|  |         |                                                       |  |
|  |    +----+----+                                                 |  |
|  |    |         |                                                 |  |
|  |  Found    Not Found                                            |  |
|  |    |         |                                                 |  |
|  |    v         v                                                 |  |
|  |  +-------+ +---------------------------------------------+    |  |
|  |  |Status?| | Step 2: Mark as "processing" (atomic)       |    |  |
|  |  +---+---+ |         SET idem:{key} "processing" NX EX   |    |  |
|  |      |     +---------------------------------------------+    |  |
|  |   +--+--+         |                                           |  |
|  |   |     |    +----+----+                                      |  |
|  | processing complete   |         |                              |  |
|  |   |     |          Success   Failed (race)                    |  |
|  |   v     v             |         |                              |  |
|  | Return Return      Process   Return 409                       |  |
|  |  409   cached      request   "In progress"                    |  |
|  |        response       |                                        |  |
|  |                       v                                        |  |
|  |              +---------------------------------------------+  |  |
|  |              | Step 3: Execute business logic              |  |  |
|  |              +---------------------------------------------+  |  |
|  |                       |                                        |  |
|  |              +--------+--------+                              |  |
|  |           Success           Failure                           |  |
|  |              |                 |                               |  |
|  |              v                 v                               |  |
|  |         Cache result     Delete key                           |  |
|  |         (24hr TTL)       (allow retry)                        |  |
|  |              |                 |                               |  |
|  |              v                 v                               |  |
|  |         Return 200       Return error                         |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CODE IMPLEMENTATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PYTHON IMPLEMENTATION                                                  |
|                                                                         |
|  import redis                                                           |
|  import json                                                            |
|  import uuid                                                            |
|                                                                         |
|  redis_client = redis.Redis()                                          |
|  IDEMPOTENCY_TTL = 86400  # 24 hours                                   |
|                                                                         |
|  def idempotent_handler(func):                                         |
|      def wrapper(request):                                             |
|          # Get idempotency key from header                             |
|          idem_key = request.headers.get('Idempotency-Key')            |
|          if not idem_key:                                              |
|              return 400, {"error": "Idempotency-Key required"}        |
|                                                                         |
|          cache_key = f"idem:{idem_key}"                               |
|                                                                         |
|          # Step 1: Check for existing result                          |
|          cached = redis_client.get(cache_key)                         |
|          if cached:                                                    |
|              data = json.loads(cached)                                 |
|              if data['status'] == 'processing':                       |
|                  return 409, {"error": "Request in progress"}         |
|              return data['code'], data['response']                    |
|                                                                         |
|          # Step 2: Mark as processing (atomic)                        |
|          acquired = redis_client.set(                                 |
|              cache_key,                                                |
|              json.dumps({"status": "processing"}),                    |
|              nx=True,    # Only if not exists                         |
|              ex=IDEMPOTENCY_TTL                                       |
|          )                                                              |
|                                                                         |
|          if not acquired:                                              |
|              return 409, {"error": "Request in progress"}             |
|                                                                         |
|          try:                                                          |
|              # Step 3: Execute actual logic                           |
|              code, response = func(request)                           |
|                                                                         |
|              # Step 4: Cache successful result                        |
|              if 200 <= code < 300:                                    |
|                  redis_client.set(                                    |
|                      cache_key,                                       |
|                      json.dumps({                                     |
|                          "status": "complete",                        |
|                          "code": code,                                |
|                          "response": response                         |
|                      }),                                               |
|                      ex=IDEMPOTENCY_TTL                               |
|                  )                                                     |
|              else:                                                     |
|                  # Don't cache errors - allow retry                   |
|                  redis_client.delete(cache_key)                       |
|                                                                         |
|              return code, response                                    |
|                                                                         |
|          except Exception as e:                                       |
|              # Clear key on exception - allow retry                   |
|              redis_client.delete(cache_key)                           |
|              raise                                                     |
|                                                                         |
|      return wrapper                                                    |
|                                                                         |
|  # Usage                                                                |
|  @idempotent_handler                                                   |
|  def create_payment(request):                                          |
|      # Your payment logic here                                        |
|      payment = process_payment(request.body)                          |
|      return 200, {"payment_id": payment.id}                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 22.3: IDEMPOTENCY KEY DESIGN

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT MAKES A GOOD IDEMPOTENCY KEY?                                   |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  GOOD KEYS (Tied to business intent):                          |  |
|  |                                                                 |  |
|  |  order_123_payment_1       -> Order + attempt number           |  |
|  |  cart_abc_checkout         -> Cart session                      |  |
|  |  invoice_456               -> Invoice ID                        |  |
|  |  user_789_order_20240115   -> User + date (daily limit)        |  |
|  |  txn_uuid-v4               -> Client-generated UUID            |  |
|  |                                                                 |  |
|  |  ----------------------------------------------------------    |  |
|  |                                                                 |  |
|  |  BAD KEYS:                                                      |  |
|  |                                                                 |  |
|  |  uuid-v4 (new each request) -> Defeats the purpose!            |  |
|  |  1705312345 (timestamp)     -> Not unique enough               |  |
|  |  user_123 (user ID only)    -> User has multiple orders        |  |
|  |  random_string              -> Can't correlate retries         |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  KEY PRINCIPLE:                                                        |
|  The same business intent should generate the same idempotency key   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### KEY SCOPING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  IDEMPOTENCY KEY SCOPE                                                 |
|                                                                         |
|  Keys are typically scoped to:                                        |
|                                                                         |
|  1. API KEY / MERCHANT                                                 |
|     Same key from different merchants = different operations          |
|                                                                         |
|     Cache key: idem:{api_key}:{idempotency_key}                      |
|                                                                         |
|  2. ENDPOINT                                                           |
|     Same key on different endpoints = different operations            |
|                                                                         |
|     Cache key: idem:{endpoint}:{idempotency_key}                     |
|                                                                         |
|  3. TIME WINDOW                                                        |
|     Keys expire after TTL (24 hours typical)                          |
|     After expiry, same key = new operation                            |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  FULL CACHE KEY FORMAT:                                        |  |
|  |                                                                 |  |
|  |  idem:{merchant_id}:{endpoint_hash}:{idempotency_key}         |  |
|  |                                                                 |  |
|  |  Example:                                                       |  |
|  |  idem:merch_abc:payments_create:ord_123_pay_1                  |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 22.4: WHAT TO CACHE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RESPONSE CACHING RULES                                                |
|                                                                         |
|  +----------------------------------------------------------------+   |
|  |                                                                |   |
|  |  First Request Result    |  Retry Behavior                    |   |
|  |  -----------------------------------------------------------  |   |
|  |                                                                |   |
|  |  200 Success            |  Return cached 200 [x]               |   |
|  |  201 Created            |  Return cached 201 [x]               |   |
|  |                                                                |   |
|  |  400 Bad Request        |  Process again (fix and retry)     |   |
|  |  401 Unauthorized       |  Process again                     |   |
|  |  422 Validation Error   |  Process again (fix input)         |   |
|  |                                                                |   |
|  |  500 Server Error       |  Process again (transient)         |   |
|  |  502 Bad Gateway        |  Process again (transient)         |   |
|  |  503 Service Unavail.   |  Process again (transient)         |   |
|  |                                                                |   |
|  |  In Progress (409)      |  Wait and retry                    |   |
|  |                                                                |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
|  RULE: Only cache SUCCESSFUL terminal states                          |
|  * Success (2xx) -> Cache                                              |
|  * Client error (4xx) -> Don't cache (let them fix and retry)         |
|  * Server error (5xx) -> Don't cache (transient, retry may work)      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHAT TO STORE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CACHED VALUE STRUCTURE                                                |
|                                                                         |
|  {                                                                      |
|    "status": "complete",           // or "processing"                 |
|    "code": 200,                    // HTTP status code                |
|    "response": {                   // Full response body              |
|      "payment_id": "pay_xyz",                                         |
|      "amount": 10000,                                                  |
|      "status": "succeeded"                                            |
|    },                                                                   |
|    "request_hash": "abc123...",    // Optional: verify same request  |
|    "created_at": "2024-01-15T..."  // For debugging                  |
|  }                                                                      |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  OPTIONAL: REQUEST PARAMETER VALIDATION                                |
|                                                                         |
|  Store hash of request parameters with idempotency key.               |
|  On retry, verify parameters match.                                   |
|                                                                         |
|  Retry with SAME key but DIFFERENT parameters?                        |
|  -> Return 422 "Idempotency key reused with different parameters"     |
|                                                                         |
|  def check_params(idem_key, request_body):                            |
|      stored_hash = redis.hget(f"idem:{idem_key}", "request_hash")    |
|      current_hash = hash(json.dumps(request_body, sort_keys=True))   |
|      if stored_hash and stored_hash != current_hash:                  |
|          return 422, "Parameters don't match original request"       |
|      return None                                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 22.5: DATABASE-BACKED IDEMPOTENCY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REDIS + DATABASE FOR DURABILITY                                       |
|                                                                         |
|  Redis alone may lose data on restart. For critical operations,       |
|  back up with database UNIQUE constraint.                             |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  IDEMPOTENCY TABLE:                                            |  |
|  |                                                                 |  |
|  |  CREATE TABLE idempotency_keys (                               |  |
|  |      idempotency_key VARCHAR(255) PRIMARY KEY,                |  |
|  |      merchant_id VARCHAR(100) NOT NULL,                       |  |
|  |      endpoint VARCHAR(100) NOT NULL,                          |  |
|  |      status VARCHAR(20) NOT NULL,  -- processing/complete     |  |
|  |      request_hash VARCHAR(64),                                 |  |
|  |      response_code INT,                                        |  |
|  |      response_body JSONB,                                      |  |
|  |      created_at TIMESTAMP DEFAULT NOW(),                      |  |
|  |      expires_at TIMESTAMP NOT NULL,                           |  |
|  |                                                                 |  |
|  |      UNIQUE(merchant_id, endpoint, idempotency_key)           |  |
|  |  );                                                             |  |
|  |                                                                 |  |
|  |  -- Index for cleanup job                                      |  |
|  |  CREATE INDEX idx_expires ON idempotency_keys(expires_at);    |  |
|  |                                                                 |  |
|  |  -- Cleanup expired keys                                       |  |
|  |  DELETE FROM idempotency_keys WHERE expires_at < NOW();       |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  TWO-LAYER APPROACH:                                                   |
|                                                                         |
|  1. Check Redis first (fast path)                                     |
|  2. On Redis miss, check database                                     |
|  3. On database miss, insert with UNIQUE constraint                   |
|  4. If insert fails (duplicate), another request won                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### HANDLING CONCURRENT REQUESTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RACE CONDITION: Two requests with same key arrive simultaneously     |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Request A                      Request B                      |  |
|  |     |                              |                            |  |
|  |     | Check Redis                  | Check Redis                |  |
|  |     | (not found)                  | (not found)                |  |
|  |     |                              |                            |  |
|  |     | SET NX (success)             | SET NX (FAILS!)           |  |
|  |     |                              |                            |  |
|  |     | Process...                   | Return 409 Conflict       |  |
|  |     |                              |                            |  |
|  |     | Done!                                                     |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  The NX (Not eXists) flag ensures only ONE request proceeds.         |
|                                                                         |
|  DATABASE FALLBACK:                                                    |
|                                                                         |
|  BEGIN;                                                                 |
|  INSERT INTO idempotency_keys (key, status, ...)                      |
|  VALUES ('abc', 'processing', ...)                                    |
|  ON CONFLICT (key) DO NOTHING;                                        |
|                                                                         |
|  -- Check if WE inserted (row_count = 1) or lost race (row_count = 0)|
|  COMMIT;                                                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 22.6: EXTERNAL SERVICE IDEMPOTENCY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FORWARDING IDEMPOTENCY TO EXTERNAL SERVICES                          |
|                                                                         |
|  Your system is idempotent, but what about external APIs?             |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Your API ------> Payment Gateway (Stripe)                     |  |
|  |                                                                 |  |
|  |  If YOU retry to Stripe, Stripe might charge twice!           |  |
|  |                                                                 |  |
|  |  SOLUTION: Forward your idempotency key to Stripe             |  |
|  |                                                                 |  |
|  |  stripe.PaymentIntent.create(                                  |  |
|  |      amount=10000,                                              |  |
|  |      currency='usd',                                            |  |
|  |      idempotency_key='ord_123_pay_1'  <- Same key!             |  |
|  |  )                                                               |  |
|  |                                                                 |  |
|  |  Now if your retry hits Stripe again, Stripe returns           |  |
|  |  the cached result instead of charging again.                  |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  SERVICES THAT SUPPORT IDEMPOTENCY KEYS:                              |
|  * Stripe (Idempotency-Key header)                                   |
|  * Braintree                                                          |
|  * PayPal                                                              |
|  * Twilio                                                              |
|  * AWS (client tokens)                                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 22.7: ALTERNATIVE PATTERNS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  OTHER WAYS TO ACHIEVE IDEMPOTENCY                                    |
|                                                                         |
|  1. NATURAL IDEMPOTENCY (PUT instead of POST)                        |
|  -------------------------------------------                           |
|  Instead of:  POST /orders { ... }                                   |
|  Use:         PUT /orders/ord_123 { ... }                            |
|                                                                         |
|  PUT is naturally idempotent (sets to same state)                    |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. CLIENT-GENERATED IDs                                               |
|  ------------------------                                               |
|  Client generates UUID, server rejects duplicates                     |
|                                                                         |
|  POST /orders                                                          |
|  { "order_id": "uuid-from-client", ... }                             |
|                                                                         |
|  Server: INSERT with UNIQUE constraint on order_id                   |
|  Duplicate? Return existing order instead of error                   |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. CONDITIONAL REQUESTS (ETags)                                       |
|  ---------------------------------                                      |
|  PUT /users/123                                                        |
|  If-Match: "etag_abc"    <- Only update if version matches            |
|                                                                         |
|  Prevents lost updates from concurrent modifications                 |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  4. DATABASE CONSTRAINTS                                               |
|  ------------------------                                               |
|  Natural unique business key prevents duplicates                      |
|                                                                         |
|  CREATE TABLE orders (                                                 |
|      id SERIAL PRIMARY KEY,                                           |
|      user_id INT,                                                      |
|      cart_id VARCHAR(100),                                            |
|      UNIQUE(user_id, cart_id)  <- One order per cart                  |
|  );                                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 22.8: QUICK REFERENCE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  IDEMPOTENT API DESIGN - CHEAT SHEET                                  |
|                                                                         |
|  THE PATTERN:                                                          |
|  ------------                                                           |
|  1. Client sends Idempotency-Key header                               |
|  2. Server checks Redis: key exists?                                  |
|     * Yes + complete -> Return cached response                        |
|     * Yes + processing -> Return 409 Conflict                         |
|     * No -> SET NX, process, cache result                             |
|                                                                         |
|  KEY DESIGN:                                                           |
|  ------------                                                           |
|  * Tied to business intent (order_id, cart_id)                       |
|  * Scoped to: merchant + endpoint + time                             |
|  * TTL: 24 hours typical                                              |
|                                                                         |
|  CACHING RULES:                                                        |
|  ---------------                                                        |
|  * 2xx -> Cache (success is terminal)                                 |
|  * 4xx -> Don't cache (let client fix and retry)                     |
|  * 5xx -> Don't cache (transient, retry may work)                    |
|                                                                         |
|  IMPLEMENTATION:                                                       |
|  ----------------                                                       |
|  * Redis: SET key value NX EX 86400                                  |
|  * Database: UNIQUE constraint backup                                |
|  * External: Forward key to Stripe/etc.                              |
|                                                                         |
|  ====================================================================  |
|                                                                         |
|  INTERVIEW ANSWER:                                                     |
|                                                                         |
|  "To make POST idempotent, I'd use the Idempotency-Key pattern:      |
|                                                                         |
|   1. Client sends unique key tied to business intent                 |
|   2. Server checks Redis with SETNX (atomic)                         |
|   3. If key exists: return cached response or 409                    |
|   4. If new: process, cache successful result                        |
|   5. Use DB UNIQUE constraint as backup                              |
|   6. Forward key to external services (Stripe)                       |
|   7. Only cache 2xx responses, allow retry on errors"                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 22

