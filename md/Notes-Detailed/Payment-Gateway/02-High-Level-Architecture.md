# PAYMENT GATEWAY - HIGH LEVEL DESIGN
*Part 2: High-Level Architecture*

## SECTION 2.1: SYSTEM ARCHITECTURE DIAGRAM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PAYMENT GATEWAY - HIGH LEVEL ARCHITECTURE                              |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                         CLIENTS                                   |  |
|  |  +---------+  +---------+  +---------+  +---------+               |  |
|  |  | Mobile  |  |   Web   |  |   POS   |  | Server  |               |  |
|  |  |   App   |  |   App   |  |Terminal |  |  (API)  |               |  |
|  |  +----+----+  +----+----+  +----+----+  +----+----+               |  |
|  +-------+------------+------------+------------+--------------------+  |
|          |            |            |            |                       |
|          +------------+-----+------+------------+                       |
|                             |                                           |
|                             v                                           |
|  +-------------------------------------------------------------------+  |
|  |                      CDN / WAF / DDoS                             |  |
|  |                    (Cloudflare, Akamai)                           |  |
|  +--------------------------+----------------------------------------+  |
|                             |                                           |
|                             v                                           |
|  +-------------------------------------------------------------------+  |
|  |                     API GATEWAY                                   |  |
|  |  * Authentication (API keys, OAuth)                               |  |
|  |  * Rate limiting                                                  |  |
|  |  * Request validation                                             |  |
|  |  * TLS termination                                                |  |
|  +--------------------------+----------------------------------------+  |
|                             |                                           |
|          +------------------+------------------+                        |
|          |                  |                  |                        |
|          v                  v                  v                        |
|  +--------------+  +--------------+  +--------------+                   |
|  |   Payment    |  |   Merchant   |  |   Webhook    |                   |
|  |   Service    |  |   Service    |  |   Service    |                   |
|  +------+-------+  +--------------+  +------+-------+                   |
|         |                                    |                          |
|         v                                    |                          |
|  +-------------------------------------+    |                           |
|  |       PAYMENT ORCHESTRATOR          |    |                           |
|  |                                     |    |                           |
|  |  * Idempotency handling             |    |                           |
|  |  * Payment state machine            |    |                           |
|  |  * Retry logic                      |    |                           |
|  |  * Timeout management               |    |                           |
|  +--------------+----------------------+    |                           |
|                 |                            |                          |
|    +------------+------------+               |                          |
|    |            |            |               |                          |
|    v            v            v               |                          |
|  +--------+ +--------+ +--------+           |                           |
|  |  Card  | |  UPI   | | Wallet |           |                           |
|  | Router | | Router | | Router |           |                           |
|  +---+----+ +---+----+ +---+----+           |                           |
|      |          |           |                |                          |
|      v          v           v                |                          |
|  +-------------------------------------+    |                           |
|  |      PSP / ACQUIRER CONNECTORS      |    |                           |
|  |  +------+ +------+ +------+ +-----+ |   |                            |
|  |  | Visa | |  MC  | | NPCI | |PayPal| |   |                           |
|  |  +------+ +------+ +------+ +-----+ |   |                            |
|  +--------------+----------------------+    |                           |
|                 |                            |                          |
|  ===============+============================+===================       |
|                                                                         |
|                         DATA LAYER                                      |
|                                                                         |
|  +------------+ +------------+ +------------+ +------------+            |
|  | PostgreSQL | |   Redis    | |   Kafka    | |    S3      |            |
|  | (Primary)  | |  (Cache,   | |  (Events)  | |  (Logs,    |            |
|  |            | |   Locks)   | |            | |   Audit)   |            |
|  +------------+ +------------+ +------------+ +------------+            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.2: CORE COMPONENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. API GATEWAY                                                         |
|  ==============                                                         |
|                                                                         |
|  RESPONSIBILITIES:                                                      |
|  * API key validation                                                   |
|  * Rate limiting (per merchant, per endpoint)                           |
|  * Request/response logging                                             |
|  * TLS termination                                                      |
|  * IP whitelisting                                                      |
|  * Request transformation                                               |
|                                                                         |
|  TECH: Kong, AWS API Gateway, Envoy                                     |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  2. PAYMENT SERVICE                                                     |
|  =====================                                                  |
|                                                                         |
|  Entry point for all payment operations:                                |
|                                                                         |
|  * POST /payments          - Create payment                             |
|  * GET  /payments/{id}     - Get payment status                         |
|  * POST /payments/{id}/capture - Capture authorized payment             |
|  * POST /payments/{id}/cancel  - Void authorization                     |
|  * POST /payments/{id}/refund  - Process refund                         |
|                                                                         |
|  RESPONSIBILITIES:                                                      |
|  * Request validation                                                   |
|  * Idempotency key handling                                             |
|  * Route to Payment Orchestrator                                        |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  3. PAYMENT ORCHESTRATOR                                                |
|  ===========================                                            |
|                                                                         |
|  THE BRAIN - manages payment lifecycle                                  |
|                                                                         |
|  STATE MACHINE:                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |   CREATED --> PROCESSING --> AUTHORIZED --> CAPTURED              |  |
|  |      |            |              |              |                 |  |
|  |      |            |              |              |                 |  |
|  |      v            v              v              v                 |  |
|  |   FAILED       FAILED         VOIDED       REFUNDED               |  |
|  |                               (cancel)     (partial/full)         |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  RESPONSIBILITIES:                                                      |
|  * Manage payment state transitions                                     |
|  * Ensure exactly-once semantics                                        |
|  * Handle timeouts and retries                                          |
|  * Coordinate with downstream processors                                |
|  * Emit events for each state change                                    |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  4. PAYMENT METHOD ROUTERS                                              |
|  =============================                                          |
|                                                                         |
|  Route to appropriate processor based on:                               |
|  * Payment method (card, UPI, wallet)                                   |
|  * Card network (Visa, MC, Amex)                                        |
|  * Geography                                                            |
|  * Cost optimization                                                    |
|  * Processor availability                                               |
|                                                                         |
|  SMART ROUTING:                                                         |
|  * Primary processor down? > Failover to secondary                      |
|  * High decline rate? > Try different acquirer                          |
|  * Cost optimization based on interchange fees                          |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  5. PSP/ACQUIRER CONNECTORS                                             |
|  ============================                                           |
|                                                                         |
|  Adapters for each payment processor/network:                           |
|                                                                         |
|  * Visa/MasterCard networks                                             |
|  * NPCI (UPI in India)                                                  |
|  * PayPal, Stripe (if acting as aggregator)                             |
|  * Local payment methods                                                |
|                                                                         |
|  EACH CONNECTOR HANDLES:                                                |
|  * Protocol translation (ISO 8583, JSON APIs)                           |
|  * Network-specific encryption                                          |
|  * Response code mapping                                                |
|  * Retry logic specific to processor                                    |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  6. WEBHOOK SERVICE                                                     |
|  =====================                                                  |
|                                                                         |
|  Notify merchants of payment events:                                    |
|                                                                         |
|  * payment.authorized                                                   |
|  * payment.captured                                                     |
|  * payment.failed                                                       |
|  * refund.processed                                                     |
|  * dispute.created                                                      |
|                                                                         |
|  FEATURES:                                                              |
|  * Guaranteed delivery (retry with exponential backoff)                 |
|  * Signature verification                                               |
|  * Webhook logs for debugging                                           |
|  * Multiple endpoints per merchant                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.3: DATA STORES

```
+--------------------------------------------------------------------------+
|                                                                          |
|  PRIMARY DATABASE (PostgreSQL)                                           |
|  =================================                                       |
|                                                                          |
|  WHY POSTGRES?                                                           |
|  * ACID transactions (critical for payments)                             |
|  * Strong consistency                                                    |
|  * Mature, battle-tested                                                 |
|  * Rich querying for reports                                             |
|                                                                          |
|  TABLES:                                                                 |
|  +-------------------------------------------------------------------+   |
|  |                                                                   |   |
|  |  payments                                                         |   |
|  |  +-- id (UUID, PK)                                                |   |
|  |  +-- idempotency_key (unique)                                     |   |
|  |  +-- merchant_id                                                  |   |
|  |  +-- amount, currency                                             |   |
|  |  +-- status (created/processing/authorized/captured/failed)       |   |
|  |  +-- payment_method_type                                          |   |
|  |  +-- card_token                                                   |   |
|  |  +-- processor_response                                           |   |
|  |  +-- created_at, updated_at                                       |   |
|  |  +-- version (optimistic locking)                                 |   |
|  |                                                                   |   |
|  |  payment_events (immutable audit log)                             |   |
|  |  +-- id, payment_id                                               |   |
|  |  +-- event_type                                                   |   |
|  |  +-- old_status, new_status                                       |   |
|  |  +-- metadata (JSON)                                              |   |
|  |  +-- created_at                                                   |   |
|  |                                                                   |   |
|  |  refunds                                                          |   |
|  |  +-- id, payment_id                                               |   |
|  |  +-- amount, status                                               |   |
|  |  +-- reason, created_at                                           |   |
|  |                                                                   |   |
|  |  merchants                                                        |   |
|  |  +-- id, name, email                                              |   |
|  |  +-- api_key_hash                                                 |   |
|  |  +-- webhook_url                                                  |   |
|  |  +-- settlement_config                                            |   |
|  |                                                                   |   |
|  |  card_tokens                                                      |   |
|  |  +-- token (PK)                                                   |   |
|  |  +-- customer_id                                                  |   |
|  |  +-- last_four, brand, expiry                                     |   |
|  |  +-- vault_reference (HSM reference)                              |   |
|  |                                                                   |   |
|  +-------------------------------------------------------------------+   |
|                                                                          |
|  REDIS                                                                   |
|  =======                                                                 |
|                                                                          |
|  * Idempotency cache (24-hour TTL)                                       |
|  * Rate limiting counters                                                |
|  * Distributed locks (prevent double processing)                         |
|  * Session cache                                                         |
|                                                                          |
|  KAFKA                                                                   |
|  =======                                                                 |
|                                                                          |
|  Topics:                                                                 |
|  * payment.events (state changes)                                        |
|  * webhook.delivery (webhook tasks)                                      |
|  * settlement.batch (end of day settlements)                             |
|  * audit.log (compliance logging)                                        |
|                                                                          |
|  OBJECT STORAGE (S3)                                                     |
|  =====================                                                   |
|                                                                          |
|  * Audit logs (7+ year retention)                                        |
|  * Settlement files                                                      |
|  * Reports and exports                                                   |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 2.4: SECURITY ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PCI-DSS COMPLIANCE ZONES                                               |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  +-------------------------------------------------------------+  |  |
|  |  |                     PUBLIC ZONE                             |  |  |
|  |  |                                                             |  |  |
|  |  |  * CDN, WAF                                                 |  |  |
|  |  |  * API Gateway                                              |  |  |
|  |  |  * No card data stored                                      |  |  |
|  |  |                                                             |  |  |
|  |  +-------------------------+-----------------------------------+  |  |
|  |                            |                                      |  |
|  |                            v                                      |  |
|  |  +-------------------------------------------------------------+  |  |
|  |  |                  APPLICATION ZONE                           |  |  |
|  |  |                                                             |  |  |
|  |  |  * Payment Service                                          |  |  |
|  |  |  * Merchant Service                                         |  |  |
|  |  |  * Orchestrator                                             |  |  |
|  |  |  * Only card TOKENS (not raw PAN)                           |  |  |
|  |  |                                                             |  |  |
|  |  +-------------------------+-----------------------------------+  |  |
|  |                            |                                      |  |
|  |                            v                                      |  |
|  |  +-------------------------------------------------------------+  |  |
|  |  |               CARDHOLDER DATA ZONE (CDE)                    |  |  |
|  |  |                                                             |  |  |
|  |  |  +--------------------------------------------------------+ |  |  |
|  |  |  |               TOKENIZATION VAULT                       | |  |  |
|  |  |  |                                                        | |  |  |
|  |  |  |  * HSM (Hardware Security Module)                      | |  |  |
|  |  |  |  * Encrypted card storage                              | |  |  |
|  |  |  |  * PCI-DSS Level 1 certified                           | |  |  |
|  |  |  |  * Air-gapped from internet                            | |  |  |
|  |  |  |                                                        | |  |  |
|  |  |  +--------------------------------------------------------+ |  |  |
|  |  |                                                             |  |  |
|  |  |  +--------------------------------------------------------+ |  |  |
|  |  |  |           PSP CONNECTORS                               | |  |  |
|  |  |  |                                                        | |  |  |
|  |  |  |  * Direct connection to card networks                  | |  |  |
|  |  |  |  * Mutual TLS authentication                           | |  |  |
|  |  |  |  * Network-level encryption                            | |  |  |
|  |  |  |                                                        | |  |  |
|  |  |  +--------------------------------------------------------+ |  |  |
|  |  |                                                             |  |  |
|  |  +-------------------------------------------------------------+  |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### TOKENIZATION FLOW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CARD TOKENIZATION                                                      |
|                                                                         |
|  Raw card number NEVER stored in application databases                  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  1. Customer enters card: 4111-1111-1111-1111                     |  |
|  |                                                                   |  |
|  |  2. Client-side (Stripe.js/Razorpay.js):                          |  |
|  |     * Card data sent DIRECTLY to tokenization vault               |  |
|  |     * Merchant server never sees raw card number                  |  |
|  |                                                                   |  |
|  |  3. Vault returns token: tok_abc123xyz                            |  |
|  |                                                                   |  |
|  |  4. Merchant server receives only:                                |  |
|  |     {                                                             |  |
|  |       token: "tok_abc123xyz",                                     |  |
|  |       last_four: "1111",                                          |  |
|  |       brand: "visa",                                              |  |
|  |       expiry: "12/25"                                             |  |
|  |     }                                                             |  |
|  |                                                                   |  |
|  |  5. For payment: merchant sends token, vault decrypts             |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  BENEFIT: Merchant app never handles raw card data                      |
|  > Reduced PCI scope (SAQ A vs SAQ D)                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF PART 2

