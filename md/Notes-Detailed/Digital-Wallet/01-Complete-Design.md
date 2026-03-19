# DIGITAL WALLET SYSTEM DESIGN (PAYTM / PHONEPE)

*Complete Design: Requirements, Architecture, and Interview Guide*

## SECTION 1: UNDERSTANDING THE PROBLEM

### WHAT IS A DIGITAL WALLET

```
+-------------------------------------------------------------------------+
| a digital wallet (e-wallet) is a software-based system that securely    |
| stores users' payment information and enables electronic transactions.  |
| it functions as a virtual version of a physical wallet, allowing users  |
| to store, send, and receive money digitally.                            |
|                                                                         |
| core concepts:                                                          |
|                                                                         |
| * stored-value wallet: users load money from bank/cards into a          |
|   prepaid balance maintained by the wallet provider (e.g., paytm        |
|   wallet). the provider holds funds in an escrow/pooled account.        |
|                                                                         |
| * pass-through wallet: connects directly to user's bank account         |
|   with no stored balance. each payment triggers a real-time bank        |
|   transfer (e.g., pure UPI apps like BHIM).                             |
|                                                                         |
| * hybrid model: combines stored-value wallet with UPI/bank linking.     |
|   users can pay from wallet balance OR directly from bank account       |
|   (e.g., paytm, phonepe offer both wallet and UPI payments).            |
+-------------------------------------------------------------------------+
```

### KEY PAYMENT FLOWS

```
+-------------------------------------------------------------------------+
| payment types supported by a digital wallet system:                     |
|                                                                         |
| * P2P (peer-to-peer): send money to friends/family using phone          |
|   number, UPI ID, or QR code. use cases include splitting dinner        |
|   bills and sending money to family members.                            |
|                                                                         |
| * P2M (peer-to-merchant): pay at physical stores by scanning            |
|   merchant QR code or entering merchant UPI ID. instant settlement      |
|   enables small businesses to accept digital payments easily.           |
|                                                                         |
| * online payments: pay for e-commerce, subscriptions, utility bills,    |
|   and mobile recharges through the wallet app or SDK integration.       |
|                                                                         |
| * top-up (add money): load funds into wallet from bank account,         |
|   debit card, credit card, or net banking channels.                     |
|                                                                         |
| * withdrawal: transfer wallet balance back to linked bank account.      |
|   typically processed via NEFT/IMPS with T+0 to T+1 settlement.         |
|                                                                         |
| * UPI (unified payments interface): india's real-time inter-bank        |
|   payment system operated by NPCI. uses virtual payment addresses       |
|   (VPA) like user@paytm. works 24/7 with instant settlement.            |
+-------------------------------------------------------------------------+
```

## SECTION 2: REQUIREMENTS

### FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
| core features:                                                          |
|                                                                         |
| * user registration and KYC verification (aadhaar, PAN)                 |
| * link bank accounts and debit/credit cards                             |
| * add money to wallet from linked bank/card                             |
| * send money to contacts via phone number or UPI ID                     |
| * pay merchants via QR code scan or UPI ID                              |
| * transaction history with search and filter                            |
| * mini-statement and downloadable monthly statements                    |
| * real-time notifications (push, SMS, email) for all transactions       |
| * cashback and rewards on qualifying transactions                       |
| * request money (collect request) from other users                      |
| * auto-pay / recurring payment setup for bills                          |
| * multi-language support for regional accessibility                     |
| * refund processing for failed or disputed transactions                 |
+-------------------------------------------------------------------------+
```

### NON-FUNCTIONAL REQUIREMENTS

```
+--------------------------------------------------------------------------+
| * strong consistency: wallet balances must be exactly correct at all     |
|   times. no double-spend, no negative balances, no phantom reads.        |
|                                                                          |
| * PCI-DSS compliance: all card data must be tokenized and encrypted.     |
|   no raw card numbers stored in the system. annual audits required.      |
|                                                                          |
| * high throughput: handle 100,000+ TPS during peak events like           |
|   diwali sales, IPL matches, or new year midnight.                       |
|                                                                          |
| * low latency: P2P transfers complete in under 2 seconds end-to-end.     |
|   wallet balance queries respond in under 50ms.                          |
|                                                                          |
| * high availability: 99.99% uptime (less than 52 minutes downtime        |
|   per year). payment failures directly impact revenue and trust.         |
|                                                                          |
| * data durability: zero tolerance for lost transactions. every debit     |
|   and credit must be recorded in immutable ledger.                       |
|                                                                          |
| * fraud detection: real-time ML-based fraud scoring for every            |
|   transaction. block suspicious activity within milliseconds.            |
|                                                                          |
| * auditability: complete audit trail for every money movement.           |
|   regulatory compliance with RBI guidelines.                             |
+--------------------------------------------------------------------------+
```

## SECTION 3: BACK-OF-ENVELOPE ESTIMATION

### TRAFFIC ESTIMATES

```
+-------------------------------------------------------------------------+
| assumptions:                                                            |
|                                                                         |
| * 200 million registered users                                          |
| * 50 million daily active users (DAU)                                   |
| * average 3 transactions per DAU per day                                |
|                                                                         |
| daily transactions   = 50M * 3 = 150 million/day                        |
| average TPS          = 150M / 86400 = ~1,750 TPS                        |
| peak TPS (20x)       = 1,750 * 20 = ~35,000 TPS                         |
| flash sale peaks     = up to 100,000+ TPS (diwali, IPL)                 |
|                                                                         |
| API calls (read-heavy):                                                 |
| * balance checks: 5x transaction volume = ~8,750 TPS avg                |
| * transaction history: 2x transaction volume = ~3,500 TPS avg           |
| * total read TPS at peak: ~250,000 TPS                                  |
+-------------------------------------------------------------------------+
```

### STORAGE ESTIMATES

```
+-------------------------------------------------------------------------+
| transaction record size: ~500 bytes                                     |
| * transaction_id, sender, receiver, amount, currency, type, status,     |
|   timestamps, metadata, idempotency_key                                 |
|                                                                         |
| daily storage   = 150M * 500B = ~75 GB/day                              |
| monthly storage = 75 GB * 30 = ~2.25 TB/month                           |
| yearly storage  = 2.25 TB * 12 = ~27 TB/year                            |
|                                                                         |
| ledger entries (double-entry, 2 rows per transaction):                  |
| * 300M entries/day * 200B each = ~60 GB/day                             |
| * yearly: ~22 TB                                                        |
|                                                                         |
| wallet balances: 200M users * 100B = ~20 GB (fits in memory)            |
|                                                                         |
| total storage (3-year retention): ~150 TB                               |
| with replication factor 3: ~450 TB                                      |
+-------------------------------------------------------------------------+
```

### BANDWIDTH ESTIMATES

```
+-------------------------------------------------------------------------+
| average request size: ~2 KB (payload + headers)                         |
| average response size: ~1 KB                                            |
|                                                                         |
| ingress at peak: 100K TPS * 2 KB = ~200 MB/s                            |
| egress at peak: 100K TPS * 1 KB = ~100 MB/s                             |
|                                                                         |
| notification fanout: push + SMS for each transaction                    |
| * 150M notifications/day via push                                       |
| * 50M SMS notifications/day (high-value transactions)                   |
+-------------------------------------------------------------------------+
```

## SECTION 4: HIGH-LEVEL ARCHITECTURE

### COMPONENT OVERVIEW

```
+-------------------------------------------------------------------------+
|                                                                         |
|                      +------------------+                               |
|                      |  mobile / web    |                               |
|                      |    clients       |                               |
|                      +--------+---------+                               |
|                               |                                         |
|                      +--------v---------+                               |
|                      |   API gateway    |                               |
|                      | (rate limit,auth)|                               |
|                      +--------+---------+                               |
|                               |                                         |
|          +------------+-------+-------+------------+                    |
|          |            |               |            |                    |
|  +-------v----+ +-----v------+ +-----v-----+ +----v--------+            |
|  |    auth    | |   wallet   | |transaction| | notification|            |
|  |  service   | |  service   | |  service  | |   service   |            |
|  +-------+----+ +-----+------+ +-----+-----+ +----+--------+            |
|          |            |               |            |                    |
|          |      +-----v------+  +-----v-----+     |                     |
|          |      |   ledger   |  |  payment  |     |                     |
|          |      |  service   |  | processor |     |                     |
|          |      +-----+------+  +-----+-----+     |                     |
|          |            |               |            |                    |
|          |      +-----v------+  +-----v-----+     |                     |
|          |      | ledger DB  |  | bank/UPI  |     |                     |
|          |      | (immutable)|  |  gateway  |     |                     |
|          |      +------------+  +-----------+     |                     |
|          |                                        |                     |
|  +-------v----+                          +--------v------+              |
|  |  user DB   |                          | fraud engine  |              |
|  +------------+                          +---------------+              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMPONENT RESPONSIBILITIES

```
+-------------------------------------------------------------------------+
| * API gateway: rate limiting, authentication, request routing, SSL      |
|   termination, request/response logging, throttling per user.           |
|                                                                         |
| * auth service: user registration, login (OTP/PIN), session             |
|   management, device fingerprinting, token refresh.                     |
|                                                                         |
| * wallet service: manages wallet balances, handles add-money and        |
|   withdrawal. owns the wallet balance table. enforces balance           |
|   constraints (non-negative balance, daily limits).                     |
|                                                                         |
| * transaction service: orchestrates end-to-end payment flows.           |
|   coordinates between wallet, ledger, and payment processor.            |
|   handles idempotency, retries, and timeout management.                 |
|                                                                         |
| * ledger service: maintains immutable double-entry accounting           |
|   records. every money movement creates a balanced debit/credit         |
|   pair. provides audit trail and reconciliation APIs.                   |
|                                                                         |
| * payment processor: integrates with external payment rails             |
|   (UPI/NPCI, IMPS, NEFT, card networks). handles bank callbacks         |
|   and settlement reconciliation.                                        |
|                                                                         |
| * notification service: sends push notifications, SMS, and email        |
|   for transaction events. supports templating and multi-language.       |
|                                                                         |
| * fraud engine: real-time risk scoring using ML models. checks          |
|   velocity limits, device trust, geo-anomalies, amount patterns.        |
+-------------------------------------------------------------------------+
```

## SECTION 5: WALLET DATA MODEL

### USER WALLET SCHEMA

```
+--------------------------------------------------------------------------+
| table: user_wallet                                                       |
|                                                                          |
| +------------------+-------------+-----------------------------------+   |
| | column           | type        | description                       |   |
| +------------------+-------------+-----------------------------------+   |
| | wallet_id        | UUID (PK)   | unique wallet identifier          |   |
| | user_id          | UUID (FK)   | references users table            |   |
| | balance          | BIGINT      | balance in smallest currency      |   |
| |                  |             | unit (paise) to avoid floats      |   |
| | currency         | VARCHAR(3)  | ISO currency code (INR, USD)      |   |
| | status           | ENUM        | ACTIVE, FROZEN, CLOSED            |   |
| | daily_limit      | BIGINT      | max daily transaction amount      |   |
| | monthly_limit    | BIGINT      | max monthly transaction amount    |   |
| | kyc_level        | ENUM        | MIN_KYC, FULL_KYC                 |   |
| | version          | BIGINT      | optimistic locking version        |   |
| | created_at       | TIMESTAMP   | wallet creation time              |   |
| | updated_at       | TIMESTAMP   | last modification time            |   |
| +------------------+-------------+-----------------------------------+   |
|                                                                          |
| important design decisions:                                              |
|                                                                          |
| * balance stored as BIGINT in paise (1 INR = 100 paise) to avoid         |
|   floating-point precision errors. Rs 100.50 = 10050 paise.              |
| * version column enables optimistic concurrency control. every           |
|   update increments version; concurrent updates are detected.            |
| * kyc_level determines transaction limits per RBI guidelines:            |
|   MIN_KYC = Rs 10,000/month, FULL_KYC = Rs 1,00,000/month.               |
+--------------------------------------------------------------------------+
```

### DOUBLE-ENTRY LEDGER

```
+-------------------------------------------------------------------------+
| table: ledger_entry                                                     |
|                                                                         |
| +------------------+-------------+----------------------------------+   |
| | column           | type        | description                      |   |
| +------------------+-------------+----------------------------------+   |
| | entry_id         | UUID (PK)   | unique entry identifier          |   |
| | transaction_id   | UUID (FK)   | links debit/credit pair          |   |
| | wallet_id        | UUID (FK)   | affected wallet                  |   |
| | entry_type       | ENUM        | DEBIT or CREDIT                  |   |
| | amount           | BIGINT      | amount in paise (always > 0)     |   |
| | balance_after    | BIGINT      | wallet balance after this entry  |   |
| | description      | VARCHAR     | human-readable description       |   |
| | created_at       | TIMESTAMP   | immutable creation timestamp     |   |
| +------------------+-------------+----------------------------------+   |
|                                                                         |
| double-entry accounting rules:                                          |
|                                                                         |
| * every transaction creates exactly two entries: one DEBIT and one      |
|   CREDIT. the sum of all debits must equal the sum of all credits.      |
|                                                                         |
| * example: user A sends Rs 500 to user B                                |
|   entry 1: DEBIT  wallet_A  50000 paise  (balance decreases)            |
|   entry 2: CREDIT wallet_B  50000 paise  (balance increases)            |
|                                                                         |
| * entries are immutable (append-only). corrections are made by          |
|   creating new reversal entries, never by modifying existing ones.      |
|                                                                         |
| * balance_after field provides point-in-time balance reconstruction     |
|   without scanning the full history.                                    |
+-------------------------------------------------------------------------+
```

### INDEXES AND PARTITIONING

```
+-------------------------------------------------------------------------+
| indexes:                                                                |
|                                                                         |
| * user_wallet: PRIMARY(wallet_id), UNIQUE(user_id, currency)            |
| * ledger_entry: PRIMARY(entry_id), INDEX(transaction_id),               |
|   INDEX(wallet_id, created_at) for history queries                      |
| * transaction: PRIMARY(txn_id), INDEX(sender_id, created_at),           |
|   UNIQUE(idempotency_key) for deduplication                             |
|                                                                         |
| partitioning strategy:                                                  |
|                                                                         |
| * ledger_entry: range-partitioned by created_at (monthly partitions).   |
|   old partitions archived to cold storage. hot partition on SSD.        |
| * transaction: range-partitioned by created_at. recent 90 days on       |
|   hot storage, older data on warm/cold tiers.                           |
| * user_wallet: hash-partitioned by wallet_id for even distribution      |
|   across database shards.                                               |
+-------------------------------------------------------------------------+
```

## SECTION 6: TRANSACTION FLOW

### P2P TRANSFER FLOW

```
+-------------------------------------------------------------------------+
| user A sends Rs 500 to user B:                                          |
|                                                                         |
| step 1: client submits transfer request with idempotency_key            |
|         POST /api/v1/transfer                                           |
|         { receiver: "userB@upi", amount: 50000, idem_key: "abc123" }    |
|                                                                         |
| step 2: API gateway authenticates user, checks rate limits              |
|                                                                         |
| step 3: transaction service checks idempotency_key in cache/DB          |
|         if duplicate -> return original response                        |
|                                                                         |
| step 4: fraud engine scores the transaction in real-time (~50ms)        |
|         checks velocity limits, device trust, amount anomalies          |
|         if fraud_score > threshold -> reject transaction                |
|                                                                         |
| step 5: wallet service executes atomic balance transfer:                |
|         BEGIN TRANSACTION (SERIALIZABLE)                                |
|           SELECT balance, version FROM user_wallet                      |
|             WHERE wallet_id = A FOR UPDATE                              |
|           verify balance >= 50000                                       |
|           UPDATE user_wallet SET balance = balance - 50000,             |
|             version = version + 1 WHERE wallet_id = A                   |
|           UPDATE user_wallet SET balance = balance + 50000,             |
|             version = version + 1 WHERE wallet_id = B                   |
|           INSERT INTO ledger_entry (DEBIT for A)                        |
|           INSERT INTO ledger_entry (CREDIT for B)                       |
|         COMMIT                                                          |
|                                                                         |
| step 6: notification service sends push/SMS to both parties             |
|                                                                         |
| step 7: return success response with transaction_id to client           |
+-------------------------------------------------------------------------+
```

### MERCHANT PAYMENT FLOW

```
+-------------------------------------------------------------------------+
| user scans merchant QR code and pays Rs 200:                            |
|                                                                         |
| step 1: app decodes QR to extract merchant_id, UPI ID, amount           |
|         (static QR has no amount; dynamic QR includes amount)           |
|                                                                         |
| step 2: user confirms payment and enters wallet PIN or UPI PIN          |
|                                                                         |
| step 3: transaction service creates payment record with status          |
|         INITIATED. generates unique transaction_id.                     |
|                                                                         |
| step 4: if paying from wallet balance:                                  |
|         -> same atomic debit/credit as P2P (wallet to merchant)         |
|         if paying via UPI:                                              |
|         -> forward to payment processor -> NPCI -> merchant bank        |
|         -> await callback with success/failure                          |
|                                                                         |
| step 5: on success, update transaction status to COMPLETED              |
|         create ledger entries for the money movement                    |
|                                                                         |
| step 6: evaluate cashback rules (async via event queue)                 |
|         if eligible -> credit cashback to user wallet                   |
|                                                                         |
| step 7: notify user and merchant of successful payment                  |
+-------------------------------------------------------------------------+
```

### ADD MONEY FLOW

```
+-------------------------------------------------------------------------+
| user adds Rs 1000 to wallet from bank account:                          |
|                                                                         |
| step 1: user selects bank account and amount in app                     |
|                                                                         |
| step 2: payment processor initiates debit from user's bank              |
|         via UPI / net banking / card payment gateway                    |
|                                                                         |
| step 3: transaction created with status PENDING                         |
|         money has NOT yet been credited to wallet                       |
|                                                                         |
| step 4: bank processes debit and sends callback to our system           |
|         callback includes bank_reference_id for reconciliation          |
|                                                                         |
| step 5: on SUCCESS callback:                                            |
|         -> credit wallet balance atomically                             |
|         -> create ledger entries (DEBIT bank_pool, CREDIT user)         |
|         -> update transaction status to COMPLETED                       |
|                                                                         |
| step 6: on FAILURE callback:                                            |
|         -> update transaction status to FAILED                          |
|         -> no balance change needed                                     |
|         -> notify user of failure with reason                           |
|                                                                         |
| step 7: if no callback within timeout (e.g., 5 minutes):                |
|         -> mark as PENDING_VERIFICATION                                 |
|         -> reconciliation job checks with bank later                    |
+-------------------------------------------------------------------------+
```

### IDEMPOTENCY

```
+-------------------------------------------------------------------------+
| idempotency ensures that retrying a request produces the same result    |
| as the original request, preventing duplicate charges.                  |
|                                                                         |
| implementation:                                                         |
|                                                                         |
| * client generates a unique idempotency_key (UUID v4) per request       |
| * server stores mapping: idempotency_key -> response in redis           |
|   with TTL of 24 hours                                                  |
| * on duplicate key: return cached response without re-processing        |
|                                                                         |
| * database also has UNIQUE constraint on idempotency_key in             |
|   transaction table as a secondary safeguard                            |
|                                                                         |
| * flow:                                                                 |
|   1. check redis for idempotency_key -> if found, return cached         |
|   2. check DB for idempotency_key -> if found, return stored            |
|   3. process transaction normally                                       |
|   4. store result in both redis (fast) and DB (durable)                 |
|                                                                         |
| this is critical because mobile networks are unreliable and users       |
| often tap "pay" multiple times when the app appears unresponsive.       |
+-------------------------------------------------------------------------+
```

## SECTION 7: CONSISTENCY AND DOUBLE-SPEND PREVENTION

### THE DOUBLE-SPEND PROBLEM

```
+-------------------------------------------------------------------------+
| double-spend occurs when a user spends the same money twice due to      |
| concurrent transactions or race conditions.                             |
|                                                                         |
| example scenario:                                                       |
|                                                                         |
| * user A has Rs 500 balance                                             |
| * user A initiates two payments of Rs 400 simultaneously                |
| * without proper locking:                                               |
|                                                                         |
|   thread 1: read balance(500) -> 500 >= 400 -> debit -> balance=100     |
|   thread 2: read balance(500) -> 500 >= 400 -> debit -> balance=100     |
|                                                                         |
|   result: Rs 800 debited from Rs 500 balance (double-spend!)            |
|                                                                         |
| this is the most critical correctness issue in any wallet system.       |
| financial systems demand zero tolerance for such errors.                |
+-------------------------------------------------------------------------+
```

### SOLUTIONS

```
+-------------------------------------------------------------------------+
| approach 1: SERIALIZABLE TRANSACTIONS (database-level)                  |
|                                                                         |
| * use serializable isolation level in the database                      |
| * the DB engine detects conflicting concurrent transactions and         |
|   aborts one of them, which the application then retries                |
| * pros: simplest to implement, correctness guaranteed by DB             |
| * cons: high contention under load, frequent aborts, lower throughput   |
|                                                                         |
| approach 2: OPTIMISTIC LOCKING (version-based)                          |
|                                                                         |
| * each wallet row has a version column                                  |
| * UPDATE user_wallet SET balance = balance - amount,                    |
|     version = version + 1                                               |
|   WHERE wallet_id = X AND version = expected_version                    |
|     AND balance >= amount                                               |
| * if affected_rows = 0 -> concurrent modification detected -> retry     |
| * pros: no explicit locks, good read performance                        |
| * cons: retries under high contention, starvation possible              |
|                                                                         |
| approach 3: PESSIMISTIC LOCKING (SELECT FOR UPDATE)                     |
|                                                                         |
| * acquire row-level lock before reading balance                         |
| * SELECT balance FROM user_wallet WHERE wallet_id = X FOR UPDATE        |
| * other transactions block until lock is released                       |
| * pros: guarantees ordering, no retries needed                          |
| * cons: lock contention, potential deadlocks, lower concurrency         |
|                                                                         |
| approach 4: DISTRIBUTED LOCK (redis/zookeeper)                          |
|                                                                         |
| * acquire distributed lock on wallet_id before processing               |
| * use redis SETNX with TTL or zookeeper ephemeral nodes                 |
| * pros: works across multiple DB shards                                 |
| * cons: added latency, lock service becomes critical dependency         |
|                                                                         |
| recommended: use optimistic locking as primary mechanism with           |
| distributed lock as fallback for cross-shard transactions.              |
| the atomic check-and-debit pattern combines balance check with          |
| debit in a single SQL statement to prevent TOCTOU races.                |
+-------------------------------------------------------------------------+
```

## SECTION 8: LEDGER AND RECONCILIATION

### IMMUTABLE APPEND-ONLY LEDGER

```
+--------------------------------------------------------------------------+
| the ledger is the single source of truth for all money movements.        |
| it follows principles from traditional accounting systems.               |
|                                                                          |
| key properties:                                                          |
|                                                                          |
| * append-only: rows are never updated or deleted. corrections are        |
|   made by adding reversal entries. this creates a complete audit         |
|   trail that satisfies regulatory requirements.                          |
|                                                                          |
| * immutable: once written, a ledger entry cannot be modified.            |
|   achieved via database permissions (no UPDATE/DELETE grants)            |
|   and application-level enforcement.                                     |
|                                                                          |
| * sequenced: entries have monotonically increasing sequence numbers      |
|   within each wallet, enabling gap detection and ordering.               |
|                                                                          |
| * timestamped: server-generated timestamps (not client) ensure           |
|   consistent ordering. use database-generated timestamps to avoid        |
|   clock skew issues across application servers.                          |
|                                                                          |
| * cryptographic chaining (optional): each entry includes a hash of       |
|   the previous entry, creating a blockchain-like tamper-evident          |
|   chain. useful for high-security requirements.                          |
+--------------------------------------------------------------------------+
```

### BALANCED ENTRIES

```
+--------------------------------------------------------------------------+
| every transaction must produce balanced entries where total debits       |
| equal total credits. this is the fundamental accounting equation.        |
|                                                                          |
| example: user A sends Rs 500 to user B with Rs 5 platform fee            |
|                                                                          |
| +-------+----------+-----------+--------+---------+                      |
| | entry | wallet   | type      | amount | balance |                      |
| +-------+----------+-----------+--------+---------+                      |
| |   1   | user_A   | DEBIT     | 50500  | 49500   |                      |
| |   2   | user_B   | CREDIT    | 50000  | 150000  |                      |
| |   3   | platform | CREDIT    |   500  | 920500  |                      |
| +-------+----------+-----------+--------+---------+                      |
|                                                                          |
| total debits  = 50500                                                    |
| total credits = 50000 + 500 = 50500  (balanced!)                         |
|                                                                          |
| validation: a background job periodically scans all transactions         |
| and verifies SUM(debits) = SUM(credits) for each transaction_id.         |
| any imbalance triggers an immediate alert to the finance team.           |
+--------------------------------------------------------------------------+
```

### DAILY BANK RECONCILIATION

```
+--------------------------------------------------------------------------+
| reconciliation ensures our internal ledger matches bank records.         |
|                                                                          |
| process:                                                                 |
|                                                                          |
| * step 1: bank provides daily settlement file (MT940/CSV) listing        |
|   all credits and debits to the escrow/pooled account.                   |
|                                                                          |
| * step 2: our system generates matching internal report from ledger      |
|   entries grouped by bank reference numbers.                             |
|                                                                          |
| * step 3: automated reconciliation engine compares both files:           |
|   * matched: bank record matches internal record exactly                 |
|   * unmatched (bank only): money received but no internal record         |
|   * unmatched (internal only): internal record with no bank entry        |
|   * amount mismatch: same transaction but different amounts              |
|                                                                          |
| * step 4: unmatched items are flagged for manual investigation.          |
|   common causes include:                                                 |
|   * network timeouts (bank debited but callback lost)                    |
|   * delayed settlement (T+1 items appearing next day)                    |
|   * refund processing timing differences                                 |
|                                                                          |
| * step 5: auto-correct where possible (e.g., credit wallets for          |
|   confirmed bank debits without callbacks). escalate others.             |
|                                                                          |
| reconciliation runs daily at end-of-day and produces a report            |
| that must show zero unresolved discrepancies within T+2 days.            |
+--------------------------------------------------------------------------+
```

## SECTION 9: UPI ARCHITECTURE

### NPCI SWITCH

```
+-------------------------------------------------------------------------+
| NPCI (national payments corporation of india) operates the UPI          |
| switch that routes transactions between banks in real-time.             |
|                                                                         |
| architecture:                                                           |
|                                                                         |
|   +-----------+     +-----------+     +------------+                    |
|   | payer PSP |---->| NPCI UPI  |---->| payee bank |                    |
|   | (paytm)   |     |  switch   |     | (SBI/HDFC) |                    |
|   +-----------+     +-----------+     +------------+                    |
|         ^                                    |                          |
|         |           (response)               |                          |
|         +------------------------------------+                          |
|                                                                         |
| * PSP (payment service provider): apps like paytm, phonepe, gpay        |
|   that provide the user interface. they are licensed by NPCI.           |
|                                                                         |
| * NPCI switch: central routing hub. receives payment request from       |
|   payer's PSP, routes to payee's bank, and returns response.            |
|                                                                         |
| * issuer bank: payer's bank that actually debits the account.           |
| * acquirer bank: payee's bank that credits the account.                 |
|                                                                         |
| * the PSP does NOT hold funds. money moves directly between banks.      |
|   the PSP only facilitates the transaction through NPCI APIs.           |
+-------------------------------------------------------------------------+
```

### VPA AND PAYMENT FLOWS

```
+-------------------------------------------------------------------------+
| VPA (virtual payment address):                                          |
|                                                                         |
| * a human-readable alias for a bank account (e.g., user@paytm)          |
| * mapped to actual bank account number + IFSC at PSP/bank level         |
| * users can have multiple VPAs linked to different accounts             |
| * format: username@psphandle (e.g., john@ybl for phonepe)               |
|                                                                         |
| PAY flow (push payment - sender initiates):                             |
|                                                                         |
| 1. sender enters payee VPA and amount in PSP app                        |
| 2. sender authenticates with UPI PIN (encrypted with device key)        |
| 3. PSP sends PAY request to NPCI with encrypted credentials             |
| 4. NPCI resolves payee VPA to bank account                              |
| 5. NPCI sends debit request to payer's bank                             |
| 6. payer's bank validates PIN, checks balance, debits account           |
| 7. NPCI sends credit request to payee's bank                            |
| 8. payee's bank credits account                                         |
| 9. NPCI sends response back to PSP                                      |
| 10. PSP notifies both sender and receiver                               |
|                                                                         |
| COLLECT flow (pull payment - receiver initiates):                       |
|                                                                         |
| 1. receiver creates collect request with payer's VPA and amount         |
| 2. payer receives notification to approve/decline                       |
| 3. if approved, payer enters UPI PIN to authorize                       |
| 4. remaining flow same as PAY (steps 3-10 above)                        |
+-------------------------------------------------------------------------+
```

### UPI PIN AND SECURITY

```
+--------------------------------------------------------------------------+
| UPI PIN security model:                                                  |
|                                                                          |
| * UPI PIN is a 4 or 6 digit numeric PIN set by the user                  |
| * PIN is NEVER transmitted in plaintext                                  |
| * encryption: PIN + device_id encrypted with bank's public key           |
| * only the issuer bank can decrypt and validate the PIN                  |
| * PSP app and NPCI never see the actual PIN value                        |
|                                                                          |
| device binding:                                                          |
|                                                                          |
| * UPI registration binds: phone_number + device_id + SIM + bank_acct     |
| * changing any of these requires re-registration                         |
| * device fingerprint prevents cloning the UPI app to another device      |
|                                                                          |
| transaction limits:                                                      |
|                                                                          |
| * per-transaction limit: Rs 1,00,000 (most banks)                        |
| * daily limit varies by bank (typically Rs 1-2 lakhs)                    |
| * NPCI enforces global rate limits per VPA                               |
+--------------------------------------------------------------------------+
```

## SECTION 10: SECURITY AND COMPLIANCE

### PCI-DSS AND TOKENIZATION

```
+--------------------------------------------------------------------------+
| PCI-DSS (payment card industry data security standard):                  |
|                                                                          |
| * mandatory compliance for any system handling card data                 |
| * 12 major requirements across 6 control objectives                      |
| * annual audit by qualified security assessor (QSA)                      |
|                                                                          |
| tokenization:                                                            |
|                                                                          |
| * replace sensitive card data with non-reversible tokens                 |
| * actual card number stored only in isolated token vault                 |
| * application servers only see tokens (e.g., tok_a1b2c3d4)               |
| * token vault is a separate PCI-compliant system with:                   |
|   * HSM (hardware security module) for encryption keys                   |
|   * network segmentation (separate VLAN, firewall rules)                 |
|   * strict access controls and audit logging                             |
|                                                                          |
| * benefits:                                                              |
|   * reduced PCI scope (fewer systems handle actual card data)            |
|   * breach impact minimized (tokens are useless to attackers)            |
|   * simpler compliance for application layer                             |
+--------------------------------------------------------------------------+
```

### ENCRYPTION AND 2FA

```
+--------------------------------------------------------------------------+
| encryption layers:                                                       |
|                                                                          |
| * in transit: TLS 1.3 for all API communication. certificate             |
|   pinning in mobile apps to prevent MITM attacks.                        |
|                                                                          |
| * at rest: AES-256 encryption for sensitive fields in database.          |
|   encryption keys managed via KMS (AWS KMS / HashiCorp Vault).           |
|                                                                          |
| * application-level: sensitive fields (PAN, aadhaar) encrypted           |
|   before storage using envelope encryption pattern.                      |
|                                                                          |
| two-factor authentication (2FA):                                         |
|                                                                          |
| * login: phone number + OTP (SMS or in-app TOTP)                         |
| * transaction: wallet PIN or UPI PIN for payment authorization           |
| * high-value transactions: additional OTP verification                   |
| * device change: mandatory re-verification of identity                   |
|                                                                          |
| session management:                                                      |
|                                                                          |
| * JWT tokens with short expiry (15 minutes)                              |
| * refresh tokens stored securely with device binding                     |
| * automatic session invalidation on suspicious activity                  |
| * concurrent session limit per user (max 2 active devices)               |
+--------------------------------------------------------------------------+
```

### FRAUD DETECTION AND KYC

```
+-------------------------------------------------------------------------+
| real-time fraud detection pipeline:                                     |
|                                                                         |
| * layer 1 - rules engine: deterministic checks                          |
|   * velocity limits (max transactions per hour per user)                |
|   * amount thresholds (flag transactions above Rs 50,000)               |
|   * geo-fencing (transaction from unusual location)                     |
|   * blacklisted accounts/devices                                        |
|                                                                         |
| * layer 2 - ML model: probabilistic risk scoring                        |
|   * features: transaction amount, time, frequency, device,              |
|     location, recipient history, network graph                          |
|   * model: gradient boosted trees trained on labeled fraud data         |
|   * output: risk score 0-100, auto-block if > 90                        |
|                                                                         |
| * layer 3 - manual review: human investigation                          |
|   * scores between 50-90 queued for analyst review                      |
|   * 24/7 fraud ops team with investigation tools                        |
|                                                                         |
| KYC (know your customer):                                               |
|                                                                         |
| * minimum KYC: mobile number + OTP verification                         |
|   * wallet limit: Rs 10,000/month, Rs 1,00,000 balance                  |
| * full KYC: aadhaar + PAN + video KYC / in-person verification          |
|   * wallet limit: Rs 1,00,000/month, Rs 2,00,000 balance                |
| * e-KYC via aadhaar OTP or digilocker APIs for digital verification     |
+-------------------------------------------------------------------------+
```

## SECTION 11: CASHBACK AND REWARDS

### EVENT-DRIVEN CASHBACK SYSTEM

```
+--------------------------------------------------------------------------+
| cashback is processed asynchronously after a successful transaction      |
| to avoid adding latency to the critical payment path.                    |
|                                                                          |
| architecture:                                                            |
|                                                                          |
|   +----------+     +--------+     +-----------+     +---------+          |
|   |transaction|---->| event  |---->| cashback  |---->| wallet  |         |
|   | service   |     | queue  |     |  engine   |     | service |         |
|   +----------+     +--------+     +-----------+     +---------+          |
|                                         |                                |
|                                   +-----v------+                         |
|                                   | campaign   |                         |
|                                   | rules DB   |                         |
|                                   +------------+                         |
|                                                                          |
| flow:                                                                    |
|                                                                          |
| 1. transaction completes -> event published to kafka topic               |
| 2. cashback engine consumes event                                        |
| 3. evaluates all active campaign rules against transaction               |
| 4. if eligible -> calculates cashback amount                             |
| 5. checks budget (campaign-level and global daily budget)                |
| 6. if budget available -> credits cashback to user wallet                |
| 7. sends notification: "you earned Rs 50 cashback!"                      |
+--------------------------------------------------------------------------+
```

### CAMPAIGN RULES ENGINE

```
+-------------------------------------------------------------------------+
| the rules engine evaluates transactions against configurable            |
| campaign definitions to determine cashback eligibility.                 |
|                                                                         |
| campaign definition example:                                            |
|                                                                         |
| {                                                                       |
|   "campaign_id": "DIWALI_2024",                                         |
|   "start_date": "2024-10-20",                                           |
|   "end_date": "2024-11-05",                                             |
|   "rules": {                                                            |
|     "min_amount": 20000,         (Rs 200 in paise)                      |
|     "max_amount": 500000,        (Rs 5000)                              |
|     "payment_type": ["P2M"],     (merchant payments only)               |
|     "merchant_category": ["grocery", "restaurant"],                     |
|     "user_segment": ["new_user", "dormant_30d"],                        |
|     "max_claims_per_user": 3                                            |
|   },                                                                    |
|   "reward": {                                                           |
|     "type": "percentage",                                               |
|     "value": 10,                 (10% cashback)                         |
|     "max_cashback": 10000        (max Rs 100 per transaction)           |
|   },                                                                    |
|   "budget": {                                                           |
|     "total": 50000000,           (Rs 5 lakh total budget)               |
|     "daily": 5000000             (Rs 50,000 daily cap)                  |
|   }                                                                     |
| }                                                                       |
|                                                                         |
| rules are evaluated using a decision-tree approach for performance.     |
| campaigns are cached in memory and refreshed every 5 minutes.           |
+-------------------------------------------------------------------------+
```

### BUDGET MANAGEMENT

```
+-------------------------------------------------------------------------+
| budget tracking prevents overspending on cashback campaigns:            |
|                                                                         |
| * redis counters track real-time spend per campaign:                    |
|   INCRBY campaign:{id}:daily:{date} {amount}                            |
|   INCRBY campaign:{id}:total {amount}                                   |
|                                                                         |
| * before crediting cashback, atomically check and increment:            |
|   if current_daily + cashback_amount > daily_limit -> reject            |
|   if current_total + cashback_amount > total_limit -> reject            |
|                                                                         |
| * use redis MULTI/EXEC for atomic check-and-increment                   |
|                                                                         |
| * budget exhaustion triggers:                                           |
|   * automatic campaign deactivation                                     |
|   * alert to marketing team                                             |
|   * dashboard shows real-time budget utilization                        |
|                                                                         |
| * eventual consistency is acceptable here: slight overshoot on          |
|   budget (few hundred rupees) is tolerable vs strict consistency        |
|   that would add latency and complexity.                                |
+-------------------------------------------------------------------------+
```

## SECTION 12: SCALING

### WALLET SHARDING

```
+-------------------------------------------------------------------------+
| sharding the wallet database across multiple instances:                 |
|                                                                         |
| * shard key: wallet_id (hash-based sharding)                            |
| * shard_number = hash(wallet_id) % num_shards                           |
| * ensures even distribution of wallets across shards                    |
|                                                                         |
| * why wallet_id and not user_id:                                        |
|   * wallet_id is used in all hot-path queries                           |
|   * ensures single-shard transactions for balance operations            |
|   * cross-shard only needed for P2P (sender and receiver on             |
|     different shards) which we handle with 2PC or saga                  |
|                                                                         |
| * shard count: start with 16 shards, plan for 256 max                   |
|   use consistent hashing to minimize data movement on rebalance         |
|                                                                         |
| * each shard: primary + 2 read replicas                                 |
|   writes go to primary, balance reads from primary (consistency)        |
|   history reads can go to replicas (slight lag acceptable)              |
+-------------------------------------------------------------------------+
```

### LEDGER PARTITIONING

```
+--------------------------------------------------------------------------+
| ledger tables grow fastest and need careful partitioning:                |
|                                                                          |
| * time-based partitioning: one partition per month                       |
|   * current month: SSD storage, full indexes                             |
|   * last 3 months: SSD storage, partial indexes                          |
|   * 3-12 months: HDD storage, minimal indexes                            |
|   * 12+ months: archived to S3/glacier, queryable via athena             |
|                                                                          |
| * partition pruning: queries with date range automatically skip          |
|   irrelevant partitions. "last 30 days" only scans 1-2 partitions.       |
|                                                                          |
| * separate read path: transaction history queries routed to              |
|   read replicas with eventual consistency (few seconds lag).             |
+--------------------------------------------------------------------------+
```

### ASYNC NON-CRITICAL PATHS

```
+--------------------------------------------------------------------------+
| critical path (synchronous, low-latency):                                |
| * balance check -> fraud check -> debit -> credit -> response            |
|                                                                          |
| non-critical paths (async via message queue):                            |
| * notifications (push, SMS, email)                                       |
| * cashback evaluation and crediting                                      |
| * analytics event logging                                                |
| * statement generation                                                   |
| * audit log replication                                                  |
|                                                                          |
| message queue: kafka for high-throughput event streaming                 |
| WHY KAFKA? Wallet transactions generate events for 5+ downstream         |
| systems (notifications, cashback, analytics, audit, statements).         |
| Durable log ensures no event is lost even if a consumer is down.         |
| Ordered per partition (user_id key) - transactions for same user         |
| are processed in sequence. Consumer groups scale each downstream         |
| independently. Dead-letter queues handle poison messages.                |
| * separate topics for notifications, cashback, analytics                 |
| * consumer groups for parallel processing                                |
| * dead-letter queues for failed message handling                         |
| * at-least-once delivery with idempotent consumers                       |
+--------------------------------------------------------------------------+
```

### MULTI-REGION DEPLOYMENT

```
+--------------------------------------------------------------------------+
| for a payments system serving india, multi-region within india:          |
|                                                                          |
| * primary region: mumbai (closest to banks and NPCI)                     |
| * secondary region: hyderabad (disaster recovery)                        |
|                                                                          |
| * active-passive for writes: all wallet mutations go to primary          |
|   region. secondary receives async replication.                          |
|                                                                          |
| * active-active for reads: balance queries and history served from       |
|   nearest region for lower latency.                                      |
|                                                                          |
| * failover: if primary goes down, promote secondary to primary.          |
|   RPO (recovery point objective): < 1 second                             |
|   RTO (recovery time objective): < 30 seconds                            |
|                                                                          |
| * CDN for static content (QR images, merchant logos, T&C pages)          |
| * DNS-based routing (route53) for regional traffic management            |
+--------------------------------------------------------------------------+
```

## SECTION 13: INTERVIEW Q&A

### QUESTION 1

```
+-------------------------------------------------------------------------+
| Q: how would you prevent double-spending in a distributed wallet        |
|    system?                                                              |
|                                                                         |
| A: use a combination of optimistic locking and atomic SQL operations.   |
|    the wallet table has a version column. the debit operation is a      |
|    single atomic SQL: UPDATE wallet SET balance = balance - amount,     |
|    version = version + 1 WHERE id = X AND version = V AND balance >=    |
|    amount. if affected rows = 0, either the balance is insufficient     |
|    or a concurrent update changed the version. the application          |
|    retries with the new version. for cross-shard P2P transfers, use     |
|    a saga pattern with compensation (refund on partial failure).        |
|    additionally, idempotency keys prevent duplicate processing from     |
|    client retries.                                                      |
+-------------------------------------------------------------------------+
```

### QUESTION 2

```
+-------------------------------------------------------------------------+
| Q: why use a double-entry ledger instead of just updating balances?     |
|                                                                         |
| A: a double-entry ledger provides auditability, correctness, and        |
|    regulatory compliance. every money movement is recorded as paired    |
|    debit/credit entries that must balance. this means we can always     |
|    reconstruct any wallet's balance by summing its ledger entries.      |
|    if the derived balance disagrees with the stored balance, we have    |
|    detected a bug or corruption. the immutable append-only nature       |
|    ensures no entries can be silently modified, providing a complete    |
|    audit trail for regulators. it also simplifies reconciliation        |
|    with banks since every movement has a clear paper trail.             |
+-------------------------------------------------------------------------+
```

### QUESTION 3

```
+-------------------------------------------------------------------------+
| Q: how would you handle the case where a bank callback is lost          |
|    after a successful debit?                                            |
|                                                                         |
| A: transactions are created with PENDING status before initiating       |
|    the bank debit. if no callback arrives within a timeout (e.g.,       |
|    5 minutes), the transaction is marked PENDING_VERIFICATION.          |
|    a reconciliation job runs periodically (every 15 minutes) and        |
|    queries the bank's status-check API for all pending transactions.    |
|    if the bank confirms success, we credit the wallet and mark          |
|    COMPLETED. if the bank confirms failure, we mark FAILED. daily       |
|    bank statement reconciliation acts as the final safety net to        |
|    catch any missed transactions. the user sees "processing" status     |
|    during this period and can contact support if it takes too long.     |
+-------------------------------------------------------------------------+
```

### QUESTION 4

```
+-------------------------------------------------------------------------+
| Q: how do you scale the system to handle 100K+ TPS during peak          |
|    events?                                                              |
|                                                                         |
| A: horizontal scaling at every layer. API gateway auto-scales           |
|    behind a load balancer. wallet DB is sharded by wallet_id (16+       |
|    shards) so each shard handles ~6K TPS which is well within           |
|    postgres/mysql limits. read-heavy operations (balance checks,        |
|    history) go to read replicas. non-critical paths (notifications,     |
|    cashback) are fully async via kafka, decoupling them from the        |
|    payment critical path. redis caches hot wallet balances for          |
|    repeated reads. connection pooling (pgbouncer) prevents DB           |
|    connection exhaustion. pre-warm capacity before known peak           |
|    events (flash sales, festivals).                                     |
+-------------------------------------------------------------------------+
```

### QUESTION 5

```
+--------------------------------------------------------------------------+
| Q: what happens if your fraud detection system goes down? do you         |
|    block all transactions?                                               |
|                                                                          |
| A: the fraud engine should be designed with a fail-open or               |
|    degraded-mode strategy. if the ML scoring service is unavailable,     |
|    fall back to the deterministic rules engine (velocity limits,         |
|    amount thresholds) which runs locally without external calls.         |
|    if even rules engine fails, allow low-risk transactions (small        |
|    amounts, known devices, existing contacts) to proceed while           |
|    blocking high-risk ones (new payee, large amount, new device).        |
|    the system should have a circuit breaker that detects fraud           |
|    service failures and activates fallback within milliseconds.          |
|    all transactions during degraded mode are flagged for retroactive     |
|    analysis once the fraud engine recovers.                              |
+--------------------------------------------------------------------------+
```

### QUESTION 6

```
+-------------------------------------------------------------------------+
| Q: how would you implement real-time transaction notifications?         |
|                                                                         |
| A: notifications are decoupled from the transaction path. after a       |
|    successful transaction, an event is published to a kafka topic.      |
|    the notification service consumes these events and fans out to       |
|    multiple channels: push notifications via FCM/APNs, SMS via          |
|    aggregator (twilio/gupshup), and email. push is attempted first      |
|    (cheapest and fastest). if push delivery fails (device offline),     |
|    fall back to SMS for critical notifications (debits). email is       |
|    sent for all transactions as a record. the notification service      |
|    maintains templates per event type and supports multi-language.      |
|    delivery status is tracked and retried with exponential backoff.     |
+-------------------------------------------------------------------------+
```

### QUESTION 7

```
+-------------------------------------------------------------------------+
| Q: how do you ensure data consistency between wallet balance and        |
|    ledger entries?                                                      |
|                                                                         |
| A: the wallet balance update and ledger entry creation happen in        |
|    the same database transaction (ACID). this ensures atomicity:        |
|    either both succeed or both roll back. as a defense-in-depth         |
|    measure, a background reconciliation job runs hourly comparing       |
|    each wallet's stored balance against the computed balance from       |
|    summing all its ledger entries (credits - debits). any mismatch      |
|    triggers an immediate P0 alert. the wallet table balance is the      |
|    operational source (used for real-time checks), while the ledger     |
|    is the canonical source (used for audits and dispute resolution).    |
+-------------------------------------------------------------------------+
```

### QUESTION 8

```
+-------------------------------------------------------------------------+
| Q: how does UPI work differently from a stored-value wallet             |
|    transaction?                                                         |
|                                                                         |
| A: in a stored-value wallet transaction, money moves between            |
|    accounts within our system. we control the entire flow: debit        |
|    sender's wallet, credit receiver's wallet, both in our database.     |
|    in UPI, money moves between bank accounts via NPCI. our role as      |
|    PSP is to: collect transaction details, encrypt the UPI PIN,         |
|    forward to NPCI, and await response. we never hold the funds.        |
|    the latency is higher (2-5 seconds vs sub-second for wallet)         |
|    because it involves NPCI routing, bank processing, and inter-bank    |
|    settlement. we must handle async callbacks, timeouts, and status     |
|    check APIs since the flow spans multiple external systems.           |
+-------------------------------------------------------------------------+
```

### QUESTION 9

```
+-------------------------------------------------------------------------+
| Q: how would you design the cashback system to be abuse-resistant?      |
|                                                                         |
| A: multiple layers of protection. first, per-user claim limits          |
|    (max N cashbacks per campaign, per day). second, device              |
|    fingerprinting to detect multiple accounts from same device.         |
|    third, graph analysis to detect circular money transfers among       |
|    colluding accounts (A sends to B, B sends to C, C sends to A         |
|    just to farm cashback). fourth, minimum time between qualifying      |
|    transactions. fifth, cashback on P2M only (not P2P) to ensure        |
|    real economic activity. sixth, delayed cashback crediting            |
|    (24-48 hours) to allow fraud review before payout. seventh,          |
|    ML model trained on historical abuse patterns to flag suspicious     |
|    claims for manual review before crediting.                           |
+-------------------------------------------------------------------------+
```

### QUESTION 10

```
+--------------------------------------------------------------------------+
| Q: how would you handle a partial failure in a cross-bank UPI            |
|    transaction where the debit succeeds but credit fails?                |
|                                                                          |
| A: UPI handles this at the NPCI level with a well-defined protocol.      |
|    if the credit leg fails, NPCI initiates an automatic reversal         |
|    (refund) to the payer's bank. the PSP receives a "DEEMED" status      |
|    indicating the outcome is uncertain. a reconciliation process         |
|    runs that queries NPCI's status API to get the final status.          |
|    if NPCI confirms credit failure, the payer's bank auto-reverses.      |
|    our system marks the transaction as FAILED/REVERSED and notifies      |
|    the user. the key design principle is that the system should          |
|    eventually reach a consistent state where either both legs            |
|    succeed or both are reversed. we maintain a "pending resolution"      |
|    queue for such transactions with automated retry and escalation.      |
+--------------------------------------------------------------------------+
```
