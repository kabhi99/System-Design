# DIGITAL WALLET SYSTEM DESIGN (PAYTM / PHONEPE)
*Complete Design: Requirements, Architecture, and Interview Guide*

A digital wallet (e-wallet) is a software-based system that securely stores users'
payment information and enables electronic transactions. It functions as a virtual
version of a physical wallet, allowing users to store, send, and receive money
digitally. The core challenge is guaranteeing exact balance correctness at millions
of TPS while maintaining a complete, immutable audit trail (double-entry ledger)
across distributed database shards.

## SECTION 1: SCOPING THE PROBLEM WITH THE INTERVIEWER

```
+-------------------------------------------------------------------------+
|                                                                         |
|  INTERVIEWER-CANDIDATE DIALOGUE                                         |
|  (establishing scope before diving into design)                         |
|                                                                         |
|  CANDIDATE: Are we designing a stored-value wallet (prepaid             |
|    balance like Paytm), a pass-through system (UPI only,                |
|    no stored balance), or a hybrid?                                     |
|                                                                         |
|  INTERVIEWER: Hybrid. Users can hold a stored balance AND               |
|    link bank accounts for direct UPI payments. Focus on the             |
|    stored-value wallet for the core design.                             |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: What payment types should we support? P2P                   |
|    transfers, merchant payments, top-up, withdrawal?                    |
|                                                                         |
|  INTERVIEWER: All four. P2P and merchant payments are the               |
|    most critical. Top-up and withdrawal can be simpler.                 |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: What's the scale we're targeting? How many                  |
|    users and transactions per second?                                   |
|                                                                         |
|  INTERVIEWER: 200M registered users, 50M DAU, peak TPS                  |
|    around 100K during festivals like Diwali or IPL matches.             |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: For the balance, what consistency guarantee do              |
|    we need? Can we tolerate eventual consistency, or must               |
|    balances be strongly consistent at all times?                        |
|                                                                         |
|  INTERVIEWER: Strong consistency for balances. Zero tolerance           |
|    for double-spend or negative balances. This is a financial           |
|    system - correctness is non-negotiable.                              |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: Do we need a full double-entry ledger, or just              |
|    a transaction log?                                                   |
|                                                                         |
|  INTERVIEWER: Full double-entry bookkeeping. Every debit                |
|    has a matching credit. Regulators require a complete audit           |
|    trail. This is a core differentiator from toy designs.               |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: Should I handle the external bank/UPI integration           |
|    in detail, or treat it as an external service?                       |
|                                                                         |
|  INTERVIEWER: Cover the UPI architecture at a high level since          |
|    it's India-specific. For the core design, treat the bank             |
|    gateway as an external dependency.                                   |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: What about compliance? PCI-DSS, KYC, fraud?                 |
|                                                                         |
|  INTERVIEWER: Cover them briefly. Focus your deep dive on               |
|    the transaction flow and consistency guarantees.                     |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  AGREED SCOPE:                                                          |
|                                                                         |
|  * Hybrid wallet: stored balance + UPI bank linking                     |
|  * P2P, P2M, top-up, withdrawal payment flows                           |
|  * 200M users, 50M DAU, 100K peak TPS                                   |
|  * Strong consistency on balances (zero double-spend)                   |
|  * Double-entry ledger (immutable, append-only)                         |
|  * Bank/UPI gateway as external service                                 |
|  * Deep dive: transaction flow, consistency, distributed txns           |
|  * Brief coverage: UPI architecture, PCI-DSS, KYC, fraud                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2: UNDERSTANDING THE PROBLEM

### WHAT IS A DIGITAL WALLET

```
+-------------------------------------------------------------------------+
|                                                                         |
|  A digital wallet (e-wallet) is a software-based system that            |
|  securely stores users' payment information and enables                 |
|  electronic transactions. It functions as a virtual version of          |
|  a physical wallet, allowing users to store, send, and receive          |
|  money digitally.                                                       |
|                                                                         |
|  CORE CONCEPTS:                                                         |
|                                                                         |
|  * STORED-VALUE WALLET: Users load money from bank/cards into           |
|    a prepaid balance maintained by the wallet provider (e.g.,           |
|    Paytm wallet). The provider holds funds in an escrow/pooled          |
|    account.                                                             |
|                                                                         |
|  * PASS-THROUGH WALLET: Connects directly to user's bank                |
|    account with no stored balance. Each payment triggers a              |
|    real-time bank transfer (e.g., pure UPI apps like BHIM).             |
|                                                                         |
|  * HYBRID MODEL: Combines stored-value wallet with UPI/bank             |
|    linking. Users can pay from wallet balance OR directly from          |
|    bank account (e.g., Paytm, PhonePe offer both wallet and             |
|    UPI payments).                                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### KEY PAYMENT FLOWS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Payment types supported by a digital wallet system:                    |
|                                                                         |
|  * P2P (PEER-TO-PEER): Send money to friends/family using               |
|    phone number, UPI ID, or QR code. Use cases include                  |
|    splitting dinner bills and sending money to family members.          |
|                                                                         |
|  * P2M (PEER-TO-MERCHANT): Pay at physical stores by scanning           |
|    merchant QR code or entering merchant UPI ID. Instant                |
|    settlement enables small businesses to accept digital                |
|    payments easily.                                                     |
|                                                                         |
|  * ONLINE PAYMENTS: Pay for e-commerce, subscriptions, utility          |
|    bills, and mobile recharges through the wallet app or SDK            |
|    integration.                                                         |
|                                                                         |
|  * TOP-UP (ADD MONEY): Load funds into wallet from bank                 |
|    account, debit card, credit card, or net banking channels.           |
|                                                                         |
|  * WITHDRAWAL: Transfer wallet balance back to linked bank              |
|    account. Typically processed via NEFT/IMPS with T+0 to T+1           |
|    settlement.                                                          |
|                                                                         |
|  * UPI (UNIFIED PAYMENTS INTERFACE): India's real-time                  |
|    inter-bank payment system operated by NPCI. Uses virtual             |
|    payment addresses (VPA) like user@paytm. Works 24/7 with             |
|    instant settlement.                                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3: REQUIREMENTS

### FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CORE FEATURES:                                                         |
|                                                                         |
|  * User registration and KYC verification (Aadhaar, PAN)                |
|  * Link bank accounts and debit/credit cards                            |
|  * Add money to wallet from linked bank/card                            |
|  * Send money to contacts via phone number or UPI ID                    |
|  * Pay merchants via QR code scan or UPI ID                             |
|  * Transaction history with search and filter                           |
|  * Mini-statement and downloadable monthly statements                   |
|  * Real-time notifications (push, SMS, email) for all txns              |
|  * Cashback and rewards on qualifying transactions                      |
|  * Request money (collect request) from other users                     |
|  * Auto-pay / recurring payment setup for bills                         |
|  * Multi-language support for regional accessibility                    |
|  * Refund processing for failed or disputed transactions                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### NON-FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  * STRONG CONSISTENCY: Wallet balances must be exactly correct          |
|    at all times. No double-spend, no negative balances, no              |
|    phantom reads.                                                       |
|                                                                         |
|  * PCI-DSS COMPLIANCE: All card data must be tokenized and              |
|    encrypted. No raw card numbers stored. Annual audits required.       |
|                                                                         |
|  * HIGH THROUGHPUT: Handle 100,000+ TPS during peak events like         |
|    Diwali sales, IPL matches, or New Year midnight.                     |
|                                                                         |
|  * LOW LATENCY: P2P transfers complete in under 2 seconds               |
|    end-to-end. Wallet balance queries respond in under 50ms.            |
|                                                                         |
|  * HIGH AVAILABILITY: 99.99% uptime (less than 52 minutes               |
|    downtime per year). Payment failures directly impact revenue.        |
|                                                                         |
|  * DATA DURABILITY: Zero tolerance for lost transactions. Every         |
|    debit and credit must be recorded in immutable ledger.               |
|                                                                         |
|  * FRAUD DETECTION: Real-time ML-based fraud scoring for every          |
|    transaction. Block suspicious activity within milliseconds.          |
|                                                                         |
|  * AUDITABILITY: Complete audit trail for every money movement.         |
|    Regulatory compliance with RBI guidelines.                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4: KEY TERMINOLOGY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LEDGER                                                                 |
|    An immutable, append-only record of every financial transaction.     |
|    Serves as the single source of truth for all money movements         |
|    and is used for auditing, reconciliation, and dispute resolution.    |
|                                                                         |
|  DOUBLE-ENTRY BOOKKEEPING                                               |
|    Every transaction creates exactly two entries: a debit from one      |
|    account and a credit to another. The sum of all debits always        |
|    equals the sum of all credits, ensuring mathematical correctness.    |
|                                                                         |
|  IDEMPOTENCY KEY                                                        |
|    A unique client-generated token sent with each payment request.      |
|    If the same key is seen again (retry/duplicate), the system          |
|    returns the original result without re-executing the transaction.    |
|                                                                         |
|  SETTLEMENT                                                             |
|    The actual movement of funds between bank accounts after a           |
|    transaction is authorized. Can be real-time (UPI/IMPS) or            |
|    batched (NEFT, card networks settle T+1 or T+2).                     |
|                                                                         |
|  FLOAT                                                                  |
|    Money sitting in the wallet provider's escrow/pooled account         |
|    that has been loaded by users but not yet spent. The interest        |
|    earned on float can be a significant revenue source.                 |
|                                                                         |
|  TRANSACTION                                                            |
|    A single atomic money movement (P2P transfer, merchant payment,      |
|    top-up, withdrawal). Has a lifecycle: initiated -> processing ->     |
|    success/failed/reversed.                                             |
|                                                                         |
|  BALANCE                                                                |
|    The current available amount in a user's wallet. Maintained as       |
|    a derived value from ledger entries and must be strongly             |
|    consistent to prevent double-spending.                               |
|                                                                         |
|  DEBIT / CREDIT                                                         |
|    Debit = money going out of an account (reduces balance).             |
|    Credit = money coming into an account (increases balance).           |
|    Every wallet transaction has one debit and one credit side.          |
|                                                                         |
|  RECONCILIATION                                                         |
|    The process of comparing internal ledger records against             |
|    external bank/payment gateway statements to detect and resolve       |
|    discrepancies (missing settlements, duplicate charges, etc.).        |
|                                                                         |
|  PAYMENT GATEWAY                                                        |
|    A third-party service that connects the wallet to external           |
|    payment rails (card networks, UPI/NPCI, net banking). Handles        |
|    authorization, capture, and settlement with acquiring banks.         |
|                                                                         |
|  KYC (KNOW YOUR CUSTOMER)                                               |
|    Regulatory-mandated identity verification (Aadhaar, PAN, etc.)       |
|    required before users can transact. Minimum KYC allows small         |
|    limits; full KYC unlocks higher transaction and balance limits.      |
|                                                                         |
|  ESCROW                                                                 |
|    A pooled bank account held by the wallet provider where user         |
|    funds are parked. Regulated by RBI guidelines to ensure user         |
|    money is segregated from the company's operating funds.              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5: BACK-OF-ENVELOPE ESTIMATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TRAFFIC ESTIMATES (QPS funnel):                                        |
|                                                                         |
|  Registered users: 200 million                                          |
|  Daily active users (DAU): 50 million                                   |
|  Average transactions per DAU per day: 3                                |
|                                                                         |
|  Daily transactions:                                                    |
|    50M * 3 = 150,000,000 transactions/day                               |
|                                                                         |
|  Average TPS:                                                           |
|    150,000,000 / 86,400 = ~1,750 TPS                                    |
|                                                                         |
|  Peak TPS (20x average, during festivals):                              |
|    1,750 * 20 = ~35,000 TPS                                             |
|                                                                         |
|  Flash sale / Diwali midnight peak:                                     |
|    Up to 100,000+ TPS                                                   |
|                                                                         |
|  Read API calls (balance + history are read-heavy):                     |
|  * Balance checks: ~5x transaction volume = 8,750 TPS avg               |
|  * Transaction history: ~2x transaction volume = 3,500 TPS avg          |
|  * Total read TPS at peak (20x): ~250,000 TPS                           |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  STORAGE ESTIMATES:                                                     |
|                                                                         |
|  Transaction record size: ~500 bytes                                    |
|    (txn_id, sender, receiver, amount, currency, type, status,           |
|     timestamps, metadata, idempotency_key)                              |
|                                                                         |
|  Daily storage:                                                         |
|    150M * 500 B = ~75 GB/day                                            |
|                                                                         |
|  Monthly storage:                                                       |
|    75 GB * 30 = ~2.25 TB/month                                          |
|                                                                         |
|  Yearly storage:                                                        |
|    2.25 TB * 12 = ~27 TB/year                                           |
|                                                                         |
|  Ledger entries (double-entry, 2 rows per transaction):                 |
|    300M entries/day * 200 B each = ~60 GB/day                           |
|    Yearly: ~22 TB                                                       |
|                                                                         |
|  Wallet balances:                                                       |
|    200M users * 100 B = ~20 GB (fits entirely in memory)                |
|                                                                         |
|  Total storage (3-year retention):                                      |
|    (27 + 22) * 3 + 20 = ~167 TB                                         |
|    With replication factor 3: ~500 TB                                   |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  BANDWIDTH ESTIMATES:                                                   |
|                                                                         |
|  Average request size: ~2 KB (payload + headers)                        |
|  Average response size: ~1 KB                                           |
|                                                                         |
|  Ingress at peak:                                                       |
|    100K TPS * 2 KB = ~200 MB/s                                          |
|                                                                         |
|  Egress at peak:                                                        |
|    100K TPS * 1 KB = ~100 MB/s                                          |
|                                                                         |
|  Notification fanout: push + SMS for each transaction                   |
|    150M push notifications/day                                          |
|    50M SMS notifications/day (high-value transactions)                  |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  NODE COUNT DERIVATION:                                                 |
|                                                                         |
|  DB shards (wallet balance writes):                                     |
|    Peak 100K TPS; PostgreSQL handles ~5K TPS per shard                  |
|    100K / 5K = 20 shards minimum                                        |
|    With headroom: 32 shards (+ 2 replicas each = 96 DB nodes)           |
|                                                                         |
|  Application servers:                                                   |
|    Assume 500 req/sec per app server (stateless)                        |
|    Peak total: 100K (writes) + 250K (reads) = 350K req/sec              |
|    350K / 500 = 700 app servers                                         |
|    In practice: ~200 (auto-scale pool, not all at 100% peak)            |
|                                                                         |
|  Redis nodes (idempotency cache + balance cache):                       |
|    20 GB balance data + idempotency keys = ~50 GB                       |
|    50 GB / 25 GB per Redis node = 2 masters + 2 replicas                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6: API DESIGN

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REST API ENDPOINTS                                                     |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  1. WALLET APIs                                                         |
|                                                                         |
|  +--------+---------------------------+----------------------------+    |
|  | Method | Path                      | Description                |    |
|  +--------+---------------------------+----------------------------+    |
|  | GET    | /v1/wallets/{wallet_id}   | Get wallet balance +       |    |
|  |        |                           |   status + limits.         |    |
|  +--------+---------------------------+----------------------------+    |
|  | POST   | /v1/wallets/{wallet_id}   | Add money from linked      |    |
|  |        |   /top-up                 |   bank account or card.    |    |
|  +--------+---------------------------+----------------------------+    |
|  | POST   | /v1/wallets/{wallet_id}   | Withdraw to linked bank.   |    |
|  |        |   /withdraw               |                            |    |
|  +--------+---------------------------+----------------------------+    |
|                                                                         |
|  Balance response:                                                      |
|  {                                                                      |
|    "wallet_id": "w_abc123",                                             |
|    "balance": 1050000,           // Rs 10,500.00 in paise               |
|    "currency": "INR",                                                   |
|    "status": "ACTIVE",                                                  |
|    "kyc_level": "FULL_KYC",                                             |
|    "daily_limit_remaining": 9000000                                     |
|  }                                                                      |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  2. TRANSFER APIs                                                       |
|                                                                         |
|  +--------+---------------------------+----------------------------+    |
|  | Method | Path                      | Description                |    |
|  +--------+---------------------------+----------------------------+    |
|  | POST   | /v1/transfers             | P2P transfer from wallet   |    |
|  |        |                           |   to another user.         |    |
|  +--------+---------------------------+----------------------------+    |
|  | POST   | /v1/payments              | Pay a merchant via wallet  |    |
|  |        |                           |   balance or UPI.          |    |
|  +--------+---------------------------+----------------------------+    |
|  | GET    | /v1/transactions          | Transaction history with   |    |
|  |        |   ?wallet_id=w_abc123     |   pagination and filters.  |    |
|  |        |   &type=P2P               |                            |    |
|  |        |   &cursor=xyz             |                            |    |
|  +--------+---------------------------+----------------------------+    |
|  | GET    | /v1/transactions/{txn_id} | Single transaction detail. |    |
|  +--------+---------------------------+----------------------------+    |
|                                                                         |
|  Transfer request body:                                                 |
|  {                                                                      |
|    "sender_wallet_id": "w_abc123",                                      |
|    "receiver": "user@paytm",          // VPA or phone number            |
|    "amount": 50000,                    // Rs 500.00 in paise            |
|    "currency": "INR",                                                   |
|    "note": "Dinner split",                                              |
|    "idempotency_key": "cli_uuid_789"                                    |
|  }                                                                      |
|                                                                         |
|  Transfer response:                                                     |
|  {                                                                      |
|    "transaction_id": "txn_def456",                                      |
|    "status": "COMPLETED",                                               |
|    "amount": 50000,                                                     |
|    "sender_balance_after": 1000000,                                     |
|    "created_at": "2024-12-20T10:30:00Z"                                 |
|  }                                                                      |
|                                                                         |
|  IDEMPOTENCY NOTE: Every write API accepts an idempotency_key.          |
|  If the same key is sent again, the server returns the original         |
|  response without re-processing. Stored in Redis (TTL 24h) +            |
|  DB UNIQUE constraint as durable backup.                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7: DATABASE SCHEMA WITH SAMPLE DATA

### USER WALLET SCHEMA

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TABLE: user_wallet                                                     |
|                                                                         |
|  +------------------+-------------+---------------------------------+   |
|  | Column           | Type        | Description                     |   |
|  +------------------+-------------+---------------------------------+   |
|  | wallet_id        | UUID (PK)   | Unique wallet identifier        |   |
|  | user_id          | UUID (FK)   | References users table          |   |
|  | balance          | BIGINT      | Balance in smallest currency    |   |
|  |                  |             | unit (paise) to avoid floats    |   |
|  | currency         | VARCHAR(3)  | ISO currency code (INR, USD)    |   |
|  | status           | ENUM        | ACTIVE, FROZEN, CLOSED          |   |
|  | daily_limit      | BIGINT      | Max daily transaction amount    |   |
|  | monthly_limit    | BIGINT      | Max monthly transaction amount  |   |
|  | kyc_level        | ENUM        | MIN_KYC, FULL_KYC               |   |
|  | version          | BIGINT      | Optimistic locking version      |   |
|  | created_at       | TIMESTAMP   | Wallet creation time            |   |
|  | updated_at       | TIMESTAMP   | Last modification time          |   |
|  +------------------+-------------+---------------------------------+   |
|                                                                         |
|  Sample rows:                                                           |
|  +----------+--------+-----------+-----+--------+----------+-----+      |
|  | wallet   | user   | balance   | cur | status | kyc      | ver |      |
|  +----------+--------+-----------+-----+--------+----------+-----+      |
|  | w_abc123 | u_001  | 1050000   | INR | ACTIVE | FULL_KYC |  42 |      |
|  | w_def456 | u_002  |   75000   | INR | ACTIVE | MIN_KYC  |  17 |      |
|  | w_ghi789 | u_003  | 3200000   | INR | FROZEN | FULL_KYC | 108 |      |
|  | w_plat01 | sys    | 920050000 | INR | ACTIVE | N/A      | 999 |      |
|  +----------+--------+-----------+-----+--------+----------+-----+      |
|  (w_plat01 is the platform/fee collection wallet)                       |
|                                                                         |
|  KEY DESIGN DECISIONS:                                                  |
|                                                                         |
|  * Balance stored as BIGINT in paise (1 INR = 100 paise) to avoid       |
|    floating-point precision errors. Rs 10,500.00 = 1050000 paise.       |
|  * Version column enables optimistic concurrency control. Every         |
|    update increments version; concurrent updates are detected.          |
|  * KYC level determines transaction limits per RBI guidelines:          |
|    MIN_KYC = Rs 10,000/month, FULL_KYC = Rs 1,00,000/month.             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DOUBLE-ENTRY LEDGER

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TABLE: ledger_entry                                                    |
|                                                                         |
|  +------------------+-------------+---------------------------------+   |
|  | Column           | Type        | Description                     |   |
|  +------------------+-------------+---------------------------------+   |
|  | entry_id         | UUID (PK)   | Unique entry identifier         |   |
|  | transaction_id   | UUID (FK)   | Links debit/credit pair         |   |
|  | wallet_id        | UUID (FK)   | Affected wallet                 |   |
|  | entry_type       | ENUM        | DEBIT or CREDIT                 |   |
|  | amount           | BIGINT      | Amount in paise (always > 0)    |   |
|  | balance_after    | BIGINT      | Wallet balance after this entry |   |
|  | description      | VARCHAR     | Human-readable description      |   |
|  | created_at       | TIMESTAMP   | Immutable creation timestamp    |   |
|  +------------------+-------------+---------------------------------+   |
|                                                                         |
|  Sample rows (User A sends Rs 500 to User B with Rs 5 fee):             |
|  +----------+----------+----------+--------+-------+-----------+        |
|  | entry_id | txn_id   | wallet   | type   | amt   | bal_after |        |
|  +----------+----------+----------+--------+-------+-----------+        |
|  | e_001    | txn_5001 | w_abc123 | DEBIT  | 50500 | 999500    |        |
|  | e_002    | txn_5001 | w_def456 | CREDIT | 50000 | 125000    |        |
|  | e_003    | txn_5001 | w_plat01 | CREDIT |   500 | 920050500 |        |
|  +----------+----------+----------+--------+-------+-----------+        |
|                                                                         |
|  Total debits  = 50500                                                  |
|  Total credits = 50000 + 500 = 50500  (BALANCED)                        |
|                                                                         |
|  RULES:                                                                 |
|  * Entries are IMMUTABLE (append-only). Corrections are made by         |
|    creating new reversal entries, never by modifying existing ones.     |
|  * balance_after provides point-in-time balance reconstruction          |
|    without scanning full history.                                       |
|  * SUM(debits) must equal SUM(credits) for every transaction_id.        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### TRANSACTION TABLE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TABLE: transaction                                                     |
|                                                                         |
|  +------------------+-------------+---------------------------------+   |
|  | Column           | Type        | Description                     |   |
|  +------------------+-------------+---------------------------------+   |
|  | transaction_id   | UUID (PK)   | Unique transaction identifier   |   |
|  | sender_wallet_id | UUID (FK)   | Source wallet                   |   |
|  | receiver_wallet_id| UUID (FK)  | Destination wallet              |   |
|  | amount           | BIGINT      | Amount in paise                 |   |
|  | fee              | BIGINT      | Platform fee in paise           |   |
|  | type             | ENUM        | P2P, P2M, TOPUP, WITHDRAW       |   |
|  | status           | VARCHAR(20) | INITIATED/PROCESSING/COMPLETED  |   |
|  | idempotency_key  | VARCHAR (UQ)| Client dedup key                |   |
|  | metadata         | JSONB       | Additional context              |   |
|  | created_at       | TIMESTAMP   | Transaction creation time       |   |
|  | updated_at       | TIMESTAMP   | Last status change              |   |
|  +------------------+-------------+---------------------------------+   |
|                                                                         |
|  UNIQUE INDEX on idempotency_key (prevents duplicate processing)        |
|  INDEX on (sender_wallet_id, created_at) for sender history             |
|  INDEX on (receiver_wallet_id, created_at) for receiver history         |
|  INDEX on (status, created_at) for stuck-txn cleanup jobs               |
|                                                                         |
|  WHY THESE INDEXES?                                                     |
|  * idempotency_key UNIQUE: mobile networks are unreliable. Users        |
|    tap "pay" multiple times. Without this, duplicate charges occur.     |
|  * (wallet_id, created_at): powers transaction history page.            |
|    Covering index enables cursor-based pagination efficiently.          |
|  * (status, created_at): reconciliation job finds txns in               |
|    PENDING_VERIFICATION older than 5 min for bank status check.         |
|                                                                         |
|  Sample rows:                                                           |
|  +----------+----------+----------+-------+------+------+-----------+   |
|  | txn_id   | sender   | receiver | amt   | fee  | type | status    |   |
|  +----------+----------+----------+-------+------+------+-----------+   |
|  | txn_5001 | w_abc123 | w_def456 | 50000 |  500 | P2P  | COMPLETED |   |
|  | txn_5002 | w_abc123 | w_merch1 | 20000 |    0 | P2M  | COMPLETED |   |
|  | txn_5003 | w_bank01 | w_abc123 |100000 |    0 | TOPUP| PENDING   |   |
|  +----------+----------+----------+-------+------+------+-----------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### INDEXES AND PARTITIONING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  INDEXES:                                                               |
|                                                                         |
|  * user_wallet: PRIMARY(wallet_id), UNIQUE(user_id, currency)           |
|  * ledger_entry: PRIMARY(entry_id), INDEX(transaction_id),              |
|    INDEX(wallet_id, created_at) for history queries                     |
|  * transaction: PRIMARY(txn_id), INDEX(sender_wallet_id, created_at),   |
|    UNIQUE(idempotency_key) for deduplication                            |
|                                                                         |
|  PARTITIONING STRATEGY:                                                 |
|                                                                         |
|  * ledger_entry: range-partitioned by created_at (monthly).             |
|    Old partitions archived to cold storage. Hot partition on SSD.       |
|  * transaction: range-partitioned by created_at. Recent 90 days on      |
|    hot storage, older data on warm/cold tiers.                          |
|  * user_wallet: hash-partitioned by wallet_id for even distribution     |
|    across database shards.                                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8: HIGH-LEVEL ARCHITECTURE

### COMPONENT OVERVIEW

```
+-------------------------------------------------------------------------+
|                                                                         |
|                      +------------------+                               |
|                      |  Mobile / Web    |                               |
|                      |    Clients       |                               |
|                      +--------+---------+                               |
|                               |                                         |
|                      +--------v---------+                               |
|                      |   API Gateway    |                               |
|                      | (rate limit,auth)|                               |
|                      +--------+---------+                               |
|                               |                                         |
|          +------------+-------+-------+------------+                    |
|          |            |               |            |                    |
|  +-------v----+ +-----v------+ +-----v-----+ +----v--------+            |
|  |    Auth    | |   Wallet   | |Transaction| | Notification|            |
|  |  Service   | |  Service   | |  Service  | |   Service   |            |
|  +-------+----+ +-----+------+ +-----+-----+ +----+--------+            |
|          |            |               |            |                    |
|          |      +-----v------+  +-----v-----+     |                     |
|          |      |   Ledger   |  |  Payment  |     |                     |
|          |      |  Service   |  | Processor |     |                     |
|          |      +-----+------+  +-----+-----+     |                     |
|          |            |               |            |                    |
|          |      +-----v------+  +-----v-----+     |                     |
|          |      | Ledger DB  |  | Bank/UPI  |     |                     |
|          |      | (immutable)|  |  Gateway  |     |                     |
|          |      +------------+  +-----------+     |                     |
|          |                                        |                     |
|  +-------v----+                          +--------v------+              |
|  |  User DB   |                          | Fraud Engine  |              |
|  +------------+                          +---------------+              |
|                                                                         |
|  WHY SEPARATE WALLET AND LEDGER SERVICES?                               |
|  Wallet service owns the mutable balance (hot path, low latency).       |
|  Ledger service owns the immutable append-only audit trail (cold        |
|  path, high durability). Separating them lets each scale and            |
|  optimize independently. Balance reads don't compete with ledger        |
|  writes for DB resources.                                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMPONENT RESPONSIBILITIES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  * API GATEWAY: Rate limiting, authentication, request routing,         |
|    SSL termination, request/response logging, throttling per user.      |
|                                                                         |
|  * AUTH SERVICE: User registration, login (OTP/PIN), session            |
|    management, device fingerprinting, token refresh.                    |
|                                                                         |
|  * WALLET SERVICE: Manages wallet balances, handles add-money and       |
|    withdrawal. Owns the wallet balance table. Enforces balance          |
|    constraints (non-negative balance, daily limits).                    |
|                                                                         |
|  * TRANSACTION SERVICE: Orchestrates end-to-end payment flows.          |
|    Coordinates between wallet, ledger, and payment processor.           |
|    Handles idempotency, retries, and timeout management.                |
|                                                                         |
|  * LEDGER SERVICE: Maintains immutable double-entry accounting          |
|    records. Every money movement creates a balanced debit/credit        |
|    pair. Provides audit trail and reconciliation APIs.                  |
|                                                                         |
|  * PAYMENT PROCESSOR: Integrates with external payment rails            |
|    (UPI/NPCI, IMPS, NEFT, card networks). Handles bank callbacks        |
|    and settlement reconciliation.                                       |
|                                                                         |
|  * NOTIFICATION SERVICE: Sends push notifications, SMS, and email       |
|    for transaction events. Supports templating and multi-language.      |
|                                                                         |
|  * FRAUD ENGINE: Real-time risk scoring using ML models. Checks         |
|    velocity limits, device trust, geo-anomalies, amount patterns.       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 9: DEEP DIVE - DISTRIBUTED TRANSACTION APPROACHES (THE HARD PROBLEM)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THIS IS THE CORE INTERVIEW DISCUSSION TOPIC.                           |
|                                                                         |
|  The "hard problem" in digital wallets: how to transfer money           |
|  between two wallets that may live on DIFFERENT database shards         |
|  while guaranteeing zero double-spend and a balanced ledger.            |
|                                                                         |
|  We show 3 approaches with progressive interviewer pushback.            |
|                                                                         |
|  =================================================================      |
|                                                                         |
|  THE PROBLEM: CROSS-SHARD P2P TRANSFER                                  |
|                                                                         |
|  User A (shard 1) sends Rs 500 to User B (shard 3).                     |
|  We need to:                                                            |
|    1. Debit A's balance by 500  (shard 1)                               |
|    2. Credit B's balance by 500 (shard 3)                               |
|    3. Write 2 ledger entries     (shard 1 + shard 3)                    |
|    4. All-or-nothing: partial execution = money lost or created         |
|                                                                         |
|  =================================================================      |
|                                                                         |
|  APPROACH 1: SINGLE-DB TRANSACTION (NAIVE / SAME-SHARD ONLY)            |
|                                                                         |
|  BEGIN TRANSACTION (SERIALIZABLE);                                      |
|    SELECT balance, version FROM user_wallet                             |
|      WHERE wallet_id = :A FOR UPDATE;                                   |
|    -- verify balance >= 50000                                           |
|    UPDATE user_wallet SET balance = balance - 50000,                    |
|      version = version + 1 WHERE wallet_id = :A;                        |
|    UPDATE user_wallet SET balance = balance + 50000,                    |
|      version = version + 1 WHERE wallet_id = :B;                        |
|    INSERT INTO ledger_entry (DEBIT for A);                              |
|    INSERT INTO ledger_entry (CREDIT for B);                             |
|  COMMIT;                                                                |
|                                                                         |
|  +------------------+-----------------------------------------+         |
|  | Pros             | Cons                                    |         |
|  +------------------+-----------------------------------------+         |
|  | Simplest to code | Only works if A and B on same shard     |         |
|  | ACID guaranteed  | Cannot scale beyond one DB node         |         |
|  | Easy to reason   | Contention under high concurrency       |         |
|  +------------------+-----------------------------------------+         |
|                                                                         |
|  INTERVIEWER PUSHBACK: "This doesn't work when A and B are              |
|  on different shards, which is the common case at 200M users.           |
|  How would you handle cross-shard transfers?"                           |
|                                                                         |
|  =================================================================      |
|                                                                         |
|  APPROACH 2: TRY-CONFIRM/CANCEL (TC/C) PATTERN                          |
|                                                                         |
|  Also known as "two-phase business transaction."                        |
|  Three phases: TRY > CONFIRM > (or CANCEL on failure)                   |
|                                                                         |
|  PHASE 1 - TRY (reserve resources):                                     |
|  +------------------+    +------------------+                           |
|  | Shard 1 (A)      |    | Shard 3 (B)      |                           |
|  | DEBIT A by 500   |    | (nothing yet)    |                           |
|  | A.status = TRYING|    |                  |                           |
|  | Hold 500 in      |    |                  |                           |
|  |   escrow account |    |                  |                           |
|  +------------------+    +------------------+                           |
|                                                                         |
|  Money moves: A's wallet -> escrow (intermediate holding account)       |
|                                                                         |
|  PHASE 2 - CONFIRM (commit the transfer):                               |
|  +------------------+    +------------------+                           |
|  | Shard 1 (A)      |    | Shard 3 (B)      |                           |
|  | Mark A's debit   |    | CREDIT B by 500  |                           |
|  | as CONFIRMED     |    | Move from escrow |                           |
|  |                  |    | to B's wallet    |                           |
|  +------------------+    +------------------+                           |
|                                                                         |
|  Money moves: escrow -> B's wallet                                      |
|                                                                         |
|  PHASE 2 (ALT) - CANCEL (on failure):                                   |
|  +------------------+    +------------------+                           |
|  | Shard 1 (A)      |    | Shard 3 (B)      |                           |
|  | REVERSE: credit  |    | (no action, B    |                           |
|  | A back from      |    |  was never       |                           |
|  | escrow account   |    |  credited)       |                           |
|  +------------------+    +------------------+                           |
|                                                                         |
|  +------------------+-----------------------------------------+         |
|  | Pros             | Cons                                    |         |
|  +------------------+-----------------------------------------+         |
|  | Each phase is a  | Requires an escrow/intermediate account |         |
|  |   local txn      | More complex than single-DB txn         |         |
|  | No distributed   | "Trying" state is visible to user (A    |         |
|  |   lock needed    |   balance drops before B receives)      |         |
|  | Naturally idem-  | Must handle stuck TRY states (cleanup)  |         |
|  |   potent phases  |                                         |         |
|  +------------------+-----------------------------------------+         |
|                                                                         |
|  INTERVIEWER PUSHBACK: "TC/C works but requires an escrow               |
|  account and two-phase coordination. At 100K TPS, the                   |
|  coordinator becomes a bottleneck. Is there a more scalable             |
|  approach?"                                                             |
|                                                                         |
|  =================================================================      |
|                                                                         |
|  APPROACH 3: EVENT SOURCING + CQRS (MOST SCALABLE)                      |
|                                                                         |
|  Instead of updating mutable balances, make the EVENT LOG the           |
|  source of truth. Balances are derived by replaying events.             |
|                                                                         |
|  ARCHITECTURE:                                                          |
|                                                                         |
|  +------------------+    +------------------+    +---------------+      |
|  | Client sends     | -> | Append event to  | -> | Event Store   |      |
|  | transfer request |    | event store      |    | (append-only) |      |
|  +------------------+    +------------------+    +-------+-------+      |
|                                                          |              |
|                                                          v              |
|                                                  +-------+-------+      |
|                                                  | Event Processor|     |
|                                                  | (consumer)     |     |
|                                                  +-------+-------+      |
|                                                          |              |
|                                      +-------------------+---+          |
|                                      |                       |          |
|                                      v                       v          |
|                               +------+-------+    +---------+----+      |
|                               | Balance View | -> | Ledger View  |      |
|                               | (materialized|    | (materialized|      |
|                               |  wallet bal) |    |  audit trail) |     |
|                               +--------------+    +--------------+      |
|                                                                         |
|  EVENTS (immutable, ordered):                                           |
|  +------+------------+----------+----------+--------+--------+          |
|  | seq  | event_type | txn_id   | wallet   | amount | status |          |
|  +------+------------+----------+----------+--------+--------+          |
|  | 1001 | DEBIT      | txn_5001 | w_abc123 | 50500  | OK     |          |
|  | 1002 | CREDIT     | txn_5001 | w_def456 | 50000  | OK     |          |
|  | 1003 | CREDIT     | txn_5001 | w_plat01 |   500  | OK     |          |
|  +------+------------+----------+----------+--------+--------+          |
|                                                                         |
|  BALANCE = replay all events for a wallet:                              |
|    SUM(CREDIT amounts) - SUM(DEBIT amounts) = current balance           |
|                                                                         |
|  In practice, a materialized balance view is maintained (updated        |
|  by the event processor) so we don't replay from scratch.               |
|                                                                         |
|  +------------------+-----------------------------------------+         |
|  | Pros             | Cons                                    |         |
|  +------------------+-----------------------------------------+         |
|  | Append-only is   | Eventually consistent balance view      |         |
|  |   fast + durable | (small delay before balance reflects)   |         |
|  | Natural audit    | More complex architecture               |         |
|  |   trail          | Replaying events at scale is non-trivial|         |
|  | No distributed   | Need snapshots to avoid replaying all   |         |
|  |   locks          |   events from the beginning             |         |
|  | Horizontal scale | Read-your-own-write requires special    |         |
|  |   (partition by  |   handling (read from event store, not  |         |
|  |   wallet_id)     |   materialized view, for current txn)   |         |
|  +------------------+-----------------------------------------+         |
|                                                                         |
|  INTERVIEWER PUSHBACK: "How do you prevent double-spend if              |
|  balance is eventually consistent?"                                     |
|                                                                         |
|  The event store itself checks the balance constraint at write          |
|  time. Before appending a DEBIT event, the store reads the              |
|  current snapshot + any uncommitted events for that wallet to           |
|  verify sufficient balance. This check is LOCAL to one partition        |
|  (wallet_id), so it's a single-shard read + append operation.           |
|  The materialized view lag only affects read queries, not the           |
|  correctness of writes.                                                 |
|                                                                         |
|  =================================================================      |
|                                                                         |
|  COMPARISON: TC/C VS SAGA VS EVENT SOURCING                             |
|                                                                         |
|  +-------------------+----------+-----------+------------------+        |
|  | Dimension         | TC/C     | Saga      | Event Sourcing   |        |
|  +-------------------+----------+-----------+------------------+        |
|  | Consistency       | Strong   | Eventual  | Eventual (read)  |        |
|  |                   |          |           | Strong (write)   |        |
|  | Coordination      | Central  | Orchestr. | None (partitioned|        |
|  |                   | coord.   | or choreo | event log)       |        |
|  | Scalability       | Medium   | Medium    | High (partition  |        |
|  |                   |          |           | per wallet)      |        |
|  | Complexity        | Medium   | High      | High             |        |
|  | Audit trail       | Extra    | Extra     | Built-in (events |        |
|  |                   | work     | work      | ARE the ledger)  |        |
|  | Recovery          | CANCEL   | Compens.  | Replay events    |        |
|  |                   | phase    | txns      | from any point   |        |
|  +-------------------+----------+-----------+------------------+        |
|                                                                         |
|  SAGA PATTERN (for reference):                                          |
|  A sequence of local transactions where each step has a                 |
|  compensating action. If step N fails, steps 1..N-1 are                 |
|  reversed by running their compensations in reverse order.              |
|                                                                         |
|  Saga for P2P transfer:                                                 |
|  Step 1: Debit sender's wallet                                          |
|    Compensation: Credit sender back                                     |
|  Step 2: Credit receiver's wallet                                       |
|    Compensation: Debit receiver back                                    |
|  Step 3: Write ledger entries                                           |
|    Compensation: Write reversal entries                                 |
|                                                                         |
|  Risk: Between step 1 and step 2, sender is debited but                 |
|  receiver hasn't been credited. This intermediate state is              |
|  visible. Acceptable for wallet transfers (user sees                    |
|  "processing") but not for some use cases.                              |
|                                                                         |
|  RECOMMENDED STRATEGY:                                                  |
|  * Same-shard transfers: Single ACID transaction (Approach 1)           |
|  * Cross-shard transfers: TC/C pattern (Approach 2) for                 |
|    strong consistency, or Event Sourcing (Approach 3) at                |
|    extreme scale where TC/C coordinator becomes bottleneck.             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 10: CQRS - COMMAND QUERY RESPONSIBILITY SEGREGATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY CQRS FOR A WALLET SYSTEM?                                          |
|                                                                         |
|  The wallet has two very different access patterns:                     |
|                                                                         |
|  WRITES (commands): Debit/credit operations. Must be strongly           |
|    consistent. Low volume (1,750 avg TPS). Touches wallet               |
|    balance + ledger in a transaction.                                   |
|                                                                         |
|  READS (queries): Balance checks, transaction history, statements.      |
|    Can tolerate slight staleness. Very high volume (250K TPS peak).     |
|    Read-to-write ratio: ~140:1.                                         |
|                                                                         |
|  Trying to optimize one DB for both patterns is a losing game.          |
|  CQRS separates them into independent models that scale separately.     |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  ARCHITECTURE:                                                          |
|                                                                         |
|  COMMAND SIDE (write model):                                            |
|  +-----------+    +-----------+    +-----------+                        |
|  | Transfer  | -> | Wallet DB | -> | Kafka     |                        |
|  | Service   |    | (primary) |    | (events)  |                        |
|  | (debit +  |    | Sharded   |    |           |                        |
|  |  credit)  |    | by wallet |    |           |                        |
|  +-----------+    +-----------+    +-----+-----+                        |
|                                          |                              |
|  QUERY SIDE (read model):                |                              |
|                                          v                              |
|  +-----------+    +-----------+    +-----+-----+                        |
|  | Balance   | <- | Read DB   | <- | Event     |                        |
|  | History   |    | (replica  |    | Consumer  |                        |
|  | APIs      |    |  optimized|    | (updates  |                        |
|  +-----------+    |  for reads)|   |  read DB) |                        |
|                   +-----------+    +-----------+                        |
|                                                                         |
|  * Write model: sharded PostgreSQL, optimized for transactional         |
|    consistency. Only handles debit/credit operations.                   |
|  * Read model: denormalized read replicas (or separate read DB),        |
|    optimized for balance lookups and history queries. Updated           |
|    asynchronously via Kafka events.                                     |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  BALANCE READ PATH (with CQRS):                                         |
|                                                                         |
|  FAST PATH (95% of requests):                                           |
|    Client -> Redis cache (TTL 5s) -> return cached balance              |
|                                                                         |
|  MISS PATH:                                                             |
|    Client -> Read replica -> return balance + refresh cache             |
|                                                                         |
|  STRONG-READ PATH (after own transfer):                                 |
|    Client -> Write DB primary -> return authoritative balance           |
|    (used when user just completed a transfer and needs                  |
|     to see the updated balance immediately)                             |
|                                                                         |
|  The "read-your-own-write" problem is solved by routing the             |
|  requesting user to the primary for a brief window (5 seconds)          |
|  after they make a write.                                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 11: TRANSACTION FLOW

### P2P TRANSFER FLOW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  User A sends Rs 500 to User B:                                         |
|                                                                         |
|  Step 1: Client submits transfer request with idempotency_key           |
|          POST /v1/transfers                                             |
|          { receiver: "userB@upi", amount: 50000, idem_key: "abc123" }   |
|                                                                         |
|  Step 2: API gateway authenticates user, checks rate limits             |
|                                                                         |
|  Step 3: Transaction service checks idempotency_key in cache/DB         |
|          If duplicate -> return original response                       |
|                                                                         |
|  Step 4: Fraud engine scores the transaction in real-time (~50ms)       |
|          Checks velocity limits, device trust, amount anomalies         |
|          If fraud_score > threshold -> reject transaction               |
|                                                                         |
|  Step 5: Wallet service executes atomic balance transfer:               |
|          BEGIN TRANSACTION (SERIALIZABLE)                               |
|            SELECT balance, version FROM user_wallet                     |
|              WHERE wallet_id = A FOR UPDATE                             |
|            Verify balance >= 50000                                      |
|            UPDATE user_wallet SET balance = balance - 50000,            |
|              version = version + 1 WHERE wallet_id = A                  |
|            UPDATE user_wallet SET balance = balance + 50000,            |
|              version = version + 1 WHERE wallet_id = B                  |
|            INSERT INTO ledger_entry (DEBIT for A)                       |
|            INSERT INTO ledger_entry (CREDIT for B)                      |
|          COMMIT                                                         |
|                                                                         |
|  Step 6: Notification service sends push/SMS to both parties            |
|                                                                         |
|  Step 7: Return success response with transaction_id to client          |
|                                                                         |
|  ORDERING: Lock wallets in deterministic order (lower wallet_id         |
|  first) to prevent deadlocks in P2P transfers.                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### MERCHANT PAYMENT FLOW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  User scans merchant QR code and pays Rs 200:                           |
|                                                                         |
|  Step 1: App decodes QR to extract merchant_id, UPI ID, amount          |
|          (static QR has no amount; dynamic QR includes amount)          |
|                                                                         |
|  Step 2: User confirms payment and enters wallet PIN or UPI PIN         |
|                                                                         |
|  Step 3: Transaction service creates payment record with status         |
|          INITIATED. Generates unique transaction_id.                    |
|                                                                         |
|  Step 4: If paying from wallet balance:                                 |
|          -> Same atomic debit/credit as P2P (wallet to merchant)        |
|          If paying via UPI:                                             |
|          -> Forward to payment processor -> NPCI -> merchant bank       |
|          -> Await callback with success/failure                         |
|                                                                         |
|  Step 5: On success, update transaction status to COMPLETED             |
|          Create ledger entries for the money movement                   |
|                                                                         |
|  Step 6: Evaluate cashback rules (async via event queue)                |
|          If eligible -> credit cashback to user wallet                  |
|                                                                         |
|  Step 7: Notify user and merchant of successful payment                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### ADD MONEY FLOW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  User adds Rs 1000 to wallet from bank account:                         |
|                                                                         |
|  Step 1: User selects bank account and amount in app                    |
|                                                                         |
|  Step 2: Payment processor initiates debit from user's bank             |
|          via UPI / net banking / card payment gateway                   |
|                                                                         |
|  Step 3: Transaction created with status PENDING                        |
|          Money has NOT yet been credited to wallet                      |
|                                                                         |
|  Step 4: Bank processes debit and sends callback to our system          |
|          Callback includes bank_reference_id for reconciliation         |
|                                                                         |
|  Step 5: On SUCCESS callback:                                           |
|          -> Credit wallet balance atomically                            |
|          -> Create ledger entries (DEBIT bank_pool, CREDIT user)        |
|          -> Update transaction status to COMPLETED                      |
|                                                                         |
|  Step 6: On FAILURE callback:                                           |
|          -> Update transaction status to FAILED                         |
|          -> No balance change needed                                    |
|          -> Notify user of failure with reason                          |
|                                                                         |
|  Step 7: If no callback within timeout (e.g., 5 minutes):               |
|          -> Mark as PENDING_VERIFICATION                                |
|          -> Reconciliation job checks with bank later                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### IDEMPOTENCY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Idempotency ensures that retrying a request produces the same          |
|  result as the original request, preventing duplicate charges.          |
|                                                                         |
|  IMPLEMENTATION:                                                        |
|                                                                         |
|  * Client generates a unique idempotency_key (UUID v4) per request      |
|  * Server stores mapping: idempotency_key -> response in Redis          |
|    with TTL of 24 hours                                                 |
|  * On duplicate key: return cached response without re-processing       |
|                                                                         |
|  * Database also has UNIQUE constraint on idempotency_key in            |
|    transaction table as a secondary safeguard                           |
|                                                                         |
|  * Flow:                                                                |
|    1. Check Redis for idempotency_key -> if found, return cached        |
|    2. Check DB for idempotency_key -> if found, return stored           |
|    3. Process transaction normally                                      |
|    4. Store result in both Redis (fast) and DB (durable)                |
|                                                                         |
|  This is critical because mobile networks are unreliable and users      |
|  often tap "pay" multiple times when the app appears unresponsive.      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 12: CONSISTENCY AND DOUBLE-SPEND PREVENTION

### THE DOUBLE-SPEND PROBLEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Double-spend occurs when a user spends the same money twice due        |
|  to concurrent transactions or race conditions.                         |
|                                                                         |
|  Example scenario:                                                      |
|                                                                         |
|  * User A has Rs 500 balance                                            |
|  * User A initiates two payments of Rs 400 simultaneously               |
|  * Without proper locking:                                              |
|                                                                         |
|    Thread 1: read balance(500) -> 500 >= 400 -> debit -> balance=100    |
|    Thread 2: read balance(500) -> 500 >= 400 -> debit -> balance=100    |
|                                                                         |
|    Result: Rs 800 debited from Rs 500 balance (double-spend!)           |
|                                                                         |
|  This is the most critical correctness issue in any wallet system.      |
|  Financial systems demand zero tolerance for such errors.               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SOLUTIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  APPROACH 1: SERIALIZABLE TRANSACTIONS (database-level)                 |
|                                                                         |
|  * Use SERIALIZABLE isolation level in the database                     |
|  * The DB engine detects conflicting concurrent transactions and        |
|    aborts one of them, which the application then retries               |
|  * Pros: simplest to implement, correctness guaranteed by DB            |
|  * Cons: high contention under load, frequent aborts, lower TPS         |
|                                                                         |
|  APPROACH 2: OPTIMISTIC LOCKING (version-based)                         |
|                                                                         |
|  * Each wallet row has a version column                                 |
|  * UPDATE user_wallet SET balance = balance - amount,                   |
|      version = version + 1                                              |
|    WHERE wallet_id = X AND version = expected_version                   |
|      AND balance >= amount                                              |
|  * If affected_rows = 0 -> concurrent modification -> retry             |
|  * Pros: no explicit locks, good read performance                       |
|  * Cons: retries under high contention, starvation possible             |
|                                                                         |
|  APPROACH 3: PESSIMISTIC LOCKING (SELECT FOR UPDATE)                    |
|                                                                         |
|  * Acquire row-level lock before reading balance                        |
|  * SELECT balance FROM user_wallet WHERE wallet_id = X FOR UPDATE       |
|  * Other transactions block until lock is released                      |
|  * Pros: guarantees ordering, no retries needed                         |
|  * Cons: lock contention, potential deadlocks, lower concurrency        |
|                                                                         |
|  APPROACH 4: DISTRIBUTED LOCK (Redis/ZooKeeper)                         |
|                                                                         |
|  * Acquire distributed lock on wallet_id before processing              |
|  * Use Redis SETNX with TTL or ZooKeeper ephemeral nodes                |
|  * Pros: works across multiple DB shards                                |
|  * Cons: added latency, lock service becomes critical dependency        |
|                                                                         |
|  RECOMMENDED: Use optimistic locking as primary mechanism with          |
|  distributed lock as fallback for cross-shard transactions.             |
|  The atomic check-and-debit pattern combines balance check with         |
|  debit in a single SQL statement to prevent TOCTOU races.               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 13: LEDGER AND RECONCILIATION

### IMMUTABLE APPEND-ONLY LEDGER

```
+-------------------------------------------------------------------------+
|                                                                         |
|  The ledger is the single source of truth for all money movements.      |
|  It follows principles from traditional accounting systems.             |
|                                                                         |
|  KEY PROPERTIES:                                                        |
|                                                                         |
|  * APPEND-ONLY: Rows are never updated or deleted. Corrections are      |
|    made by adding reversal entries. This creates a complete audit       |
|    trail that satisfies regulatory requirements.                        |
|                                                                         |
|  * IMMUTABLE: Once written, a ledger entry cannot be modified.          |
|    Achieved via database permissions (no UPDATE/DELETE grants)          |
|    and application-level enforcement.                                   |
|                                                                         |
|  * SEQUENCED: Entries have monotonically increasing sequence            |
|    numbers within each wallet, enabling gap detection and ordering.     |
|                                                                         |
|  * TIMESTAMPED: Server-generated timestamps (not client) ensure         |
|    consistent ordering. Use database-generated timestamps to avoid      |
|    clock skew issues across application servers.                        |
|                                                                         |
|  * CRYPTOGRAPHIC CHAINING (optional): Each entry includes a hash        |
|    of the previous entry, creating a blockchain-like tamper-evident     |
|    chain. Useful for high-security requirements.                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### BALANCED ENTRIES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Every transaction must produce balanced entries where total debits     |
|  equal total credits. This is the fundamental accounting equation.      |
|                                                                         |
|  Example: User A sends Rs 500 to User B with Rs 5 platform fee          |
|                                                                         |
|  +-------+----------+-----------+--------+---------+                    |
|  | entry | wallet   | type      | amount | balance |                    |
|  +-------+----------+-----------+--------+---------+                    |
|  |   1   | user_A   | DEBIT     | 50500  | 49500   |                    |
|  |   2   | user_B   | CREDIT    | 50000  | 150000  |                    |
|  |   3   | platform | CREDIT    |   500  | 920500  |                    |
|  +-------+----------+-----------+--------+---------+                    |
|                                                                         |
|  Total debits  = 50500                                                  |
|  Total credits = 50000 + 500 = 50500  (BALANCED)                        |
|                                                                         |
|  Validation: a background job periodically scans all transactions       |
|  and verifies SUM(debits) = SUM(credits) for each transaction_id.       |
|  Any imbalance triggers an immediate alert to the finance team.         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DAILY BANK RECONCILIATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Reconciliation ensures our internal ledger matches bank records.       |
|                                                                         |
|  PROCESS:                                                               |
|                                                                         |
|  * Step 1: Bank provides daily settlement file (MT940/CSV) listing      |
|    all credits and debits to the escrow/pooled account.                 |
|                                                                         |
|  * Step 2: Our system generates matching internal report from ledger    |
|    entries grouped by bank reference numbers.                           |
|                                                                         |
|  * Step 3: Automated reconciliation engine compares both files:         |
|    * Matched: bank record matches internal record exactly               |
|    * Unmatched (bank only): money received but no internal record       |
|    * Unmatched (internal only): internal record with no bank entry      |
|    * Amount mismatch: same transaction but different amounts            |
|                                                                         |
|  * Step 4: Unmatched items flagged for manual investigation.            |
|    Common causes: network timeouts, delayed settlement (T+1),           |
|    refund processing timing differences.                                |
|                                                                         |
|  * Step 5: Auto-correct where possible (e.g., credit wallets for        |
|    confirmed bank debits without callbacks). Escalate others.           |
|                                                                         |
|  Reconciliation runs daily and must show zero unresolved                |
|  discrepancies within T+2 days.                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 14: UPI ARCHITECTURE

### NPCI SWITCH

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NPCI (National Payments Corporation of India) operates the UPI         |
|  switch that routes transactions between banks in real-time.            |
|                                                                         |
|  ARCHITECTURE:                                                          |
|                                                                         |
|    +-----------+     +-----------+     +------------+                   |
|    | Payer PSP |---->| NPCI UPI  |---->| Payee Bank |                   |
|    | (Paytm)   |     |  Switch   |     | (SBI/HDFC) |                   |
|    +-----------+     +-----------+     +------------+                   |
|          ^                                    |                         |
|          |           (response)               |                         |
|          +------------------------------------+                         |
|                                                                         |
|  * PSP (Payment Service Provider): Apps like Paytm, PhonePe, GPay       |
|    that provide the user interface. Licensed by NPCI.                   |
|                                                                         |
|  * NPCI Switch: Central routing hub. Receives payment request from      |
|    payer's PSP, routes to payee's bank, returns response.               |
|                                                                         |
|  * Issuer bank: Payer's bank that actually debits the account.          |
|  * Acquirer bank: Payee's bank that credits the account.                |
|                                                                         |
|  * The PSP does NOT hold funds. Money moves directly between banks.     |
|    The PSP only facilitates the transaction through NPCI APIs.          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### VPA AND PAYMENT FLOWS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  VPA (Virtual Payment Address):                                         |
|                                                                         |
|  * A human-readable alias for a bank account (e.g., user@paytm)         |
|  * Mapped to actual bank account number + IFSC at PSP/bank level        |
|  * Users can have multiple VPAs linked to different accounts            |
|  * Format: username@psphandle (e.g., john@ybl for PhonePe)              |
|                                                                         |
|  PAY flow (push payment - sender initiates):                            |
|                                                                         |
|  1. Sender enters payee VPA and amount in PSP app                       |
|  2. Sender authenticates with UPI PIN (encrypted with device key)       |
|  3. PSP sends PAY request to NPCI with encrypted credentials            |
|  4. NPCI resolves payee VPA to bank account                             |
|  5. NPCI sends debit request to payer's bank                            |
|  6. Payer's bank validates PIN, checks balance, debits account          |
|  7. NPCI sends credit request to payee's bank                           |
|  8. Payee's bank credits account                                        |
|  9. NPCI sends response back to PSP                                     |
|  10. PSP notifies both sender and receiver                              |
|                                                                         |
|  COLLECT flow (pull payment - receiver initiates):                      |
|                                                                         |
|  1. Receiver creates collect request with payer's VPA and amount        |
|  2. Payer receives notification to approve/decline                      |
|  3. If approved, payer enters UPI PIN to authorize                      |
|  4. Remaining flow same as PAY (steps 3-10 above)                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### UPI PIN AND SECURITY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  UPI PIN SECURITY MODEL:                                                |
|                                                                         |
|  * UPI PIN is a 4 or 6 digit numeric PIN set by the user                |
|  * PIN is NEVER transmitted in plaintext                                |
|  * Encryption: PIN + device_id encrypted with bank's public key         |
|  * Only the issuer bank can decrypt and validate the PIN                |
|  * PSP app and NPCI never see the actual PIN value                      |
|                                                                         |
|  DEVICE BINDING:                                                        |
|                                                                         |
|  * UPI registration binds: phone_number + device_id + SIM + bank_acct   |
|  * Changing any of these requires re-registration                       |
|  * Device fingerprint prevents cloning the UPI app to another device    |
|                                                                         |
|  TRANSACTION LIMITS:                                                    |
|                                                                         |
|  * Per-transaction limit: Rs 1,00,000 (most banks)                      |
|  * Daily limit varies by bank (typically Rs 1-2 lakhs)                  |
|  * NPCI enforces global rate limits per VPA                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 15: SECURITY AND COMPLIANCE

### PCI-DSS AND TOKENIZATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PCI-DSS (Payment Card Industry Data Security Standard):                |
|                                                                         |
|  * Mandatory compliance for any system handling card data               |
|  * 12 major requirements across 6 control objectives                    |
|  * Annual audit by qualified security assessor (QSA)                    |
|                                                                         |
|  TOKENIZATION:                                                          |
|                                                                         |
|  * Replace sensitive card data with non-reversible tokens               |
|  * Actual card number stored only in isolated token vault               |
|  * Application servers only see tokens (e.g., tok_a1b2c3d4)             |
|  * Token vault is a separate PCI-compliant system with:                 |
|    * HSM (hardware security module) for encryption keys                 |
|    * Network segmentation (separate VLAN, firewall rules)               |
|    * Strict access controls and audit logging                           |
|                                                                         |
|  Benefits:                                                              |
|  * Reduced PCI scope (fewer systems handle actual card data)            |
|  * Breach impact minimized (tokens are useless to attackers)            |
|  * Simpler compliance for application layer                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### ENCRYPTION AND 2FA

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ENCRYPTION LAYERS:                                                     |
|                                                                         |
|  * In transit: TLS 1.3 for all API communication. Certificate           |
|    pinning in mobile apps to prevent MITM attacks.                      |
|                                                                         |
|  * At rest: AES-256 encryption for sensitive fields in database.        |
|    Encryption keys managed via KMS (AWS KMS / HashiCorp Vault).         |
|                                                                         |
|  * Application-level: Sensitive fields (PAN, Aadhaar) encrypted         |
|    before storage using envelope encryption pattern.                    |
|                                                                         |
|  TWO-FACTOR AUTHENTICATION (2FA):                                       |
|                                                                         |
|  * Login: phone number + OTP (SMS or in-app TOTP)                       |
|  * Transaction: wallet PIN or UPI PIN for payment authorization         |
|  * High-value transactions: additional OTP verification                 |
|  * Device change: mandatory re-verification of identity                 |
|                                                                         |
|  SESSION MANAGEMENT:                                                    |
|                                                                         |
|  * JWT tokens with short expiry (15 minutes)                            |
|  * Refresh tokens stored securely with device binding                   |
|  * Automatic session invalidation on suspicious activity                |
|  * Concurrent session limit per user (max 2 active devices)             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### FRAUD DETECTION AND KYC

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REAL-TIME FRAUD DETECTION PIPELINE:                                    |
|                                                                         |
|  * Layer 1 - RULES ENGINE: deterministic checks                         |
|    * Velocity limits (max transactions per hour per user)               |
|    * Amount thresholds (flag transactions above Rs 50,000)              |
|    * Geo-fencing (transaction from unusual location)                    |
|    * Blacklisted accounts/devices                                       |
|                                                                         |
|  * Layer 2 - ML MODEL: probabilistic risk scoring                       |
|    * Features: transaction amount, time, frequency, device,             |
|      location, recipient history, network graph                         |
|    * Model: gradient boosted trees trained on labeled fraud data        |
|    * Output: risk score 0-100, auto-block if > 90                       |
|                                                                         |
|  * Layer 3 - MANUAL REVIEW: human investigation                         |
|    * Scores between 50-90 queued for analyst review                     |
|    * 24/7 fraud ops team with investigation tools                       |
|                                                                         |
|  KYC (KNOW YOUR CUSTOMER):                                              |
|                                                                         |
|  * Minimum KYC: mobile number + OTP verification                        |
|    * Wallet limit: Rs 10,000/month, Rs 1,00,000 balance                 |
|  * Full KYC: Aadhaar + PAN + video KYC / in-person verification         |
|    * Wallet limit: Rs 1,00,000/month, Rs 2,00,000 balance               |
|  * e-KYC via Aadhaar OTP or DigiLocker APIs for digital verification    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 16: CASHBACK AND REWARDS

### EVENT-DRIVEN CASHBACK SYSTEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Cashback is processed asynchronously after a successful transaction    |
|  to avoid adding latency to the critical payment path.                  |
|                                                                         |
|  ARCHITECTURE:                                                          |
|                                                                         |
|    +----------+     +--------+     +-----------+     +---------+        |
|    |transaction|---->| event  |---->| cashback  |---->| wallet  |       |
|    | service   |     | queue  |     |  engine   |     | service |       |
|    +----------+     +--------+     +-----------+     +---------+        |
|                                          |                              |
|                                    +-----v------+                       |
|                                    | campaign   |                       |
|                                    | rules DB   |                       |
|                                    +------------+                       |
|                                                                         |
|  FLOW:                                                                  |
|                                                                         |
|  1. Transaction completes -> event published to Kafka topic             |
|  2. Cashback engine consumes event                                      |
|  3. Evaluates all active campaign rules against transaction             |
|  4. If eligible -> calculates cashback amount                           |
|  5. Checks budget (campaign-level and global daily budget)              |
|  6. If budget available -> credits cashback to user wallet              |
|  7. Sends notification: "You earned Rs 50 cashback!"                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CAMPAIGN RULES ENGINE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  The rules engine evaluates transactions against configurable           |
|  campaign definitions to determine cashback eligibility.                |
|                                                                         |
|  Campaign definition example:                                           |
|                                                                         |
|  {                                                                      |
|    "campaign_id": "DIWALI_2024",                                        |
|    "start_date": "2024-10-20",                                          |
|    "end_date": "2024-11-05",                                            |
|    "rules": {                                                           |
|      "min_amount": 20000,         (Rs 200 in paise)                     |
|      "max_amount": 500000,        (Rs 5000)                             |
|      "payment_type": ["P2M"],     (merchant payments only)              |
|      "merchant_category": ["grocery", "restaurant"],                    |
|      "user_segment": ["new_user", "dormant_30d"],                       |
|      "max_claims_per_user": 3                                           |
|    },                                                                   |
|    "reward": {                                                          |
|      "type": "percentage",                                              |
|      "value": 10,                 (10% cashback)                        |
|      "max_cashback": 10000        (max Rs 100 per transaction)          |
|    },                                                                   |
|    "budget": {                                                          |
|      "total": 50000000,           (Rs 5 lakh total budget)              |
|      "daily": 5000000             (Rs 50,000 daily cap)                 |
|    }                                                                    |
|  }                                                                      |
|                                                                         |
|  Rules are evaluated using a decision-tree approach for performance.    |
|  Campaigns are cached in memory and refreshed every 5 minutes.          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### BUDGET MANAGEMENT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Budget tracking prevents overspending on cashback campaigns:           |
|                                                                         |
|  * Redis counters track real-time spend per campaign:                   |
|    INCRBY campaign:{id}:daily:{date} {amount}                           |
|    INCRBY campaign:{id}:total {amount}                                  |
|                                                                         |
|  * Before crediting cashback, atomically check and increment:           |
|    If current_daily + cashback_amount > daily_limit -> reject           |
|    If current_total + cashback_amount > total_limit -> reject           |
|                                                                         |
|  * Use Redis MULTI/EXEC for atomic check-and-increment                  |
|                                                                         |
|  * Budget exhaustion triggers:                                          |
|    * Automatic campaign deactivation                                    |
|    * Alert to marketing team                                            |
|    * Dashboard shows real-time budget utilization                       |
|                                                                         |
|  * Eventual consistency is acceptable here: slight overshoot on         |
|    budget (few hundred rupees) is tolerable vs strict consistency       |
|    that would add latency and complexity.                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 17: SCALING

### WALLET SHARDING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Sharding the wallet database across multiple instances:                |
|                                                                         |
|  * Shard key: wallet_id (hash-based sharding)                           |
|  * shard_number = hash(wallet_id) % num_shards                          |
|  * Ensures even distribution of wallets across shards                   |
|                                                                         |
|  * WHY WALLET_ID AND NOT USER_ID?                                       |
|    * wallet_id is used in all hot-path queries                          |
|    * Ensures single-shard transactions for balance operations           |
|    * Cross-shard only needed for P2P (sender and receiver on            |
|      different shards) which we handle with TC/C or saga                |
|                                                                         |
|  * Shard count: start with 32 shards, plan for 256 max                  |
|    Use consistent hashing to minimize data movement on rebalance        |
|                                                                         |
|  * Each shard: primary + 2 read replicas                                |
|    Writes go to primary, balance reads from primary (consistency)       |
|    History reads can go to replicas (slight lag acceptable)             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### LEDGER PARTITIONING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Ledger tables grow fastest and need careful partitioning:              |
|                                                                         |
|  * Time-based partitioning: one partition per month                     |
|    * Current month: SSD storage, full indexes                           |
|    * Last 3 months: SSD storage, partial indexes                        |
|    * 3-12 months: HDD storage, minimal indexes                          |
|    * 12+ months: archived to S3/Glacier, queryable via Athena           |
|                                                                         |
|  * Partition pruning: queries with date range automatically skip        |
|    irrelevant partitions. "Last 30 days" only scans 1-2 partitions.     |
|                                                                         |
|  * Separate read path: transaction history queries routed to            |
|    read replicas with eventual consistency (few seconds lag).           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### ASYNC NON-CRITICAL PATHS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CRITICAL PATH (synchronous, low-latency):                              |
|  * Balance check -> fraud check -> debit -> credit -> response          |
|                                                                         |
|  NON-CRITICAL PATHS (async via message queue):                          |
|  * Notifications (push, SMS, email)                                     |
|  * Cashback evaluation and crediting                                    |
|  * Analytics event logging                                              |
|  * Statement generation                                                 |
|  * Audit log replication                                                |
|                                                                         |
|  WHY KAFKA? Wallet transactions generate events for 5+ downstream       |
|  systems (notifications, cashback, analytics, audit, statements).       |
|  Durable log ensures no event is lost even if a consumer is down.       |
|  Ordered per partition (wallet_id key) - transactions for same user     |
|  are processed in sequence. Consumer groups scale each downstream       |
|  independently. Dead-letter queues handle poison messages.              |
|                                                                         |
|  * Separate topics for notifications, cashback, analytics               |
|  * Consumer groups for parallel processing                              |
|  * Dead-letter queues for failed message handling                       |
|  * At-least-once delivery with idempotent consumers                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### MULTI-REGION DEPLOYMENT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  For a payments system serving India, multi-region within India:        |
|                                                                         |
|  * Primary region: Mumbai (closest to banks and NPCI)                   |
|  * Secondary region: Hyderabad (disaster recovery)                      |
|                                                                         |
|  * Active-passive for writes: all wallet mutations go to primary        |
|    region. Secondary receives async replication.                        |
|                                                                         |
|  * Active-active for reads: balance queries and history served from     |
|    nearest region for lower latency.                                    |
|                                                                         |
|  * Failover: if primary goes down, promote secondary to primary.        |
|    RPO (recovery point objective): < 1 second                           |
|    RTO (recovery time objective): < 30 seconds                          |
|                                                                         |
|  * CDN for static content (QR images, merchant logos, T&C pages)        |
|  * DNS-based routing (Route53) for regional traffic management          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 18: DETAILED WRITE/READ PATHS AND STATE MANAGEMENT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. ENTITY STATE MACHINE (Transaction)                                  |
|                                                                         |
|  INITIATED --> PROCESSING --> COMPLETED                                 |
|      |              |                                                   |
|      |              +---> FAILED (insufficient balance, fraud block)    |
|      |                      |                                           |
|      |                      +---> (no retry; new txn needed)            |
|      |                                                                  |
|      +---> DUPLICATE (idempotency_key already exists)                   |
|                                                                         |
|  COMPLETED --> REVERSAL_INITIATED --> REVERSED                          |
|                     |                                                   |
|                     +---> REVERSAL_FAILED (retry with backoff)          |
|                                                                         |
|  For add-money (bank callback):                                         |
|  PENDING --> PENDING_VERIFICATION --> COMPLETED                         |
|                      |                                                  |
|                      +---> FAILED (bank confirms failure)               |
|                                                                         |
|  Transition rules:                                                      |
|  * INITIATED is created atomically with idempotency check               |
|  * PROCESSING holds the row lock on sender's wallet                     |
|  * Only COMPLETED can be REVERSED (within dispute window)               |
|  * FAILED is terminal; client must create a new transaction             |
|                                                                         |
|  =================================================================      |
|                                                                         |
|  2. CRITICAL WRITE PATH (P2P Transfer with Double-Entry)                |
|                                                                         |
|  Client            API GW        Txn Svc        Wallet Svc              |
|    |                  |              |               |                  |
|    |-- POST /transfer |              |               |                  |
|    |   {receiver,     |              |               |                  |
|    |    amount:50000,  |              |               |                 |
|    |    idem_key}      |              |               |                 |
|    |                  |              |               |                  |
|    |                  |-check idem-->|               |                  |
|    |                  | Redis GET    |               |                  |
|    |                  | idempotency_key:{key}        |                  |
|    |                  | HIT? return cached result     |                 |
|    |                  |              |               |                  |
|    |                  |--fraud svc-->| score < 90?   |                  |
|    |                  |              |               |                  |
|    |                  |              |--atomic txn-->|                  |
|    |                  |              |               |                  |
|    |                  |  BEGIN TRANSACTION (SERIALIZABLE);              |
|    |                  |    SELECT balance, version FROM user_wallet     |
|    |                  |      WHERE wallet_id = :A FOR UPDATE;           |
|    |                  |    -- verify balance >= 50000                   |
|    |                  |                                                 |
|    |                  |    UPDATE user_wallet                           |
|    |                  |      SET balance = balance - 50000,             |
|    |                  |          version = version + 1                  |
|    |                  |      WHERE wallet_id = :A;                      |
|    |                  |                                                 |
|    |                  |    UPDATE user_wallet                           |
|    |                  |      SET balance = balance + 50000,             |
|    |                  |          version = version + 1                  |
|    |                  |      WHERE wallet_id = :B;                      |
|    |                  |                                                 |
|    |                  |    INSERT INTO ledger_entry                     |
|    |                  |      (entry_id, transaction_id, wallet_id,      |
|    |                  |       entry_type, amount, balance_after)        |
|    |                  |      VALUES (:id1, :txn, :A, 'DEBIT',           |
|    |                  |              50000, :new_bal_A);                |
|    |                  |                                                 |
|    |                  |    INSERT INTO ledger_entry                     |
|    |                  |      (entry_id, transaction_id, wallet_id,      |
|    |                  |       entry_type, amount, balance_after)        |
|    |                  |      VALUES (:id2, :txn, :B, 'CREDIT',          |
|    |                  |              50000, :new_bal_B);                |
|    |                  |  COMMIT;                                        |
|    |                  |                                                 |
|    |                  |  Redis SET idempotency_key:{key} EX 86400       |
|    |                  |              |               |                  |
|    |                  |  Kafka: emit TransactionCompleted event         |
|    |                  |    -> notification svc (push + SMS)             |
|    |                  |    -> cashback engine (async eval)              |
|    |                  |    -> analytics / audit log                     |
|    |                  |              |               |                  |
|    |<-- txn_id, OK ---|              |               |                  |
|                                                                         |
|  ORDERING: Lock wallets in deterministic order (lower wallet_id         |
|  first) to prevent deadlocks in cross-shard P2P transfers.              |
|                                                                         |
|  =================================================================      |
|                                                                         |
|  3. READ PATH                                                           |
|                                                                         |
|  BALANCE CHECK:                                                         |
|    Client --> wallet service --> user_wallet primary (strong)           |
|    SELECT balance FROM user_wallet WHERE wallet_id = :id;               |
|    * Always reads from DB primary (no stale balance)                    |
|    * Redis cache for repeated reads within same session:                |
|      key: wallet_bal:{wallet_id}, TTL: 5 seconds                        |
|                                                                         |
|  TRANSACTION HISTORY:                                                   |
|    Client --> txn service --> ledger_entry read replica                 |
|    SELECT * FROM ledger_entry                                           |
|      WHERE wallet_id = :id                                              |
|      ORDER BY created_at DESC LIMIT 20;                                 |
|    * Eventual consistency OK (read replica, < 2s lag)                   |
|    * Paginated by cursor (created_at of last entry)                     |
|                                                                         |
|  IDEMPOTENCY LOOKUP:                                                    |
|    1. Redis GET idempotency_key:{key} -> HIT? return cached result      |
|    2. MISS -> DB check UNIQUE(idempotency_key) on transaction table     |
|    3. Both miss -> proceed with new transaction                         |
|                                                                         |
|  =================================================================      |
|                                                                         |
|  4. FAILURE SCENARIOS                                                   |
|                                                                         |
|  +------------------------------+-----------------------------------+   |
|  | What Fails                   | Impact & Recovery                 |   |
|  +------------------------------+-----------------------------------+   |
|  | DB commit fails mid-txn      | ACID rollback; both wallets and  |    |
|  | (crash after debit, before   | ledger entries are untouched.    |    |
|  |  credit)                     | Client retries with same idem.   |    |
|  +------------------------------+-----------------------------------+   |
|  | Cross-shard P2P: sender      | TC/C CANCEL: credit back         |    |
|  | debited, receiver shard down | sender's wallet from escrow.     |    |
|  |                              | Saga state persisted for restart.|    |
|  +------------------------------+-----------------------------------+   |
|  | Bank callback lost           | Txn stays PENDING_VERIFICATION.  |    |
|  | (add-money flow)             | Reconciliation job queries bank  |    |
|  |                              | status API every 15 min. Daily   |    |
|  |                              | bank statement as final safety.  |    |
|  +------------------------------+-----------------------------------+   |
|  | Kafka event lost after       | Transactional outbox: write event|    |
|  | COMPLETED                    | to outbox table in same DB txn.  |    |
|  |                              | Relay service polls outbox,      |    |
|  |                              | publishes to Kafka, marks sent.  |    |
|  +------------------------------+-----------------------------------+   |
|                                                                         |
|  =================================================================      |
|                                                                         |
|  5. CLEANUP / EXPIRY                                                    |
|                                                                         |
|  IDEMPOTENCY KEYS:                                                      |
|  * Redis TTL: 24 hours for fast dedup                                   |
|  * DB UNIQUE constraint as durable backup                               |
|  * DB keys older than 90 days archived                                  |
|                                                                         |
|  PENDING TRANSACTIONS:                                                  |
|  * Sweep job every 15 min: find txns in PENDING_VERIFICATION            |
|    older than 5 minutes, query bank status API                          |
|  * Txns stuck > 72 hours: escalate to ops team                          |
|                                                                         |
|  LEDGER PARTITIONING:                                                   |
|  * ledger_entry: range-partitioned by created_at (monthly)              |
|  * Current month: SSD, full indexes                                     |
|  * 3-12 months: HDD, partial indexes                                    |
|  * >12 months: archived to S3/Glacier, queryable via Athena             |
|                                                                         |
|  BALANCE RECONCILIATION:                                                |
|  * Hourly job: for each wallet, compare stored balance vs               |
|    SUM(CREDIT) - SUM(DEBIT) from ledger_entry                           |
|  * Mismatch triggers P0 alert to finance team                           |
|  * Daily bank statement reconciliation (T+1 settlement check)           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 19: WRAP-UP

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SUMMARY OF KEY DESIGN DECISIONS:                                       |
|                                                                         |
|  1. DOUBLE-ENTRY LEDGER AS SOURCE OF TRUTH                              |
|     Every money movement creates immutable, balanced debit/credit       |
|     entries. Wallet balance is a derived, cached view. This ensures     |
|     auditability and regulatory compliance.                             |
|                                                                         |
|  2. CROSS-SHARD TRANSFER: TC/C PATTERN                                  |
|     Same-shard transfers use a single ACID transaction. Cross-shard     |
|     transfers use Try-Confirm/Cancel with an escrow account. Event      |
|     sourcing considered for extreme scale (>100K TPS).                  |
|                                                                         |
|  3. CQRS FOR READ/WRITE SEPARATION                                      |
|     Write model (sharded PostgreSQL) handles transactional              |
|     consistency. Read model (replicas + Redis cache) handles            |
|     250K TPS read traffic. Read-your-own-write handled by               |
|     routing to primary for brief window after writes.                   |
|                                                                         |
|  4. SHARD BY WALLET_ID                                                  |
|     Keeps balance check + debit/credit on a single shard. Cross-shard   |
|     P2P transfers are the exception handled by TC/C or saga.            |
|     32 shards handle 100K peak TPS (3K TPS per shard).                  |
|                                                                         |
|  5. IDEMPOTENCY AT EVERY LAYER                                          |
|     Client-generated keys in Redis (fast) + DB UNIQUE constraint        |
|     (durable). Prevents duplicate charges from unreliable mobile        |
|     networks and user double-taps.                                      |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  KEY TRADE-OFFS:                                                        |
|                                                                         |
|  * CONSISTENCY VS LATENCY: Balance reads from primary DB (strong        |
|    consistency) add ~5ms vs reading from replica. Trade-off favors      |
|    correctness for financial data - cached reads (5s TTL) reduce        |
|    the primary load for repeated balance checks.                        |
|                                                                         |
|  * SINGLE-DB VS DISTRIBUTED TRANSACTIONS: Same-shard ACID is            |
|    simple and fast. Cross-shard TC/C adds latency (~50ms overhead)      |
|    and complexity. We optimize shard assignment to maximize             |
|    same-shard transfers (friends/family often in same shard).           |
|                                                                         |
|  * SYNCHRONOUS VS ASYNC: Critical path (balance transfer) is            |
|    synchronous for correctness. Non-critical paths (notifications,      |
|    cashback, analytics) are async via Kafka to keep the critical        |
|    path latency under 2 seconds.                                        |
|                                                                         |
|  * EVENT SOURCING TRADE-OFF: Offers the best scalability and            |
|    natural audit trail but introduces eventual consistency for          |
|    reads and significant architectural complexity. Recommended          |
|    only when TC/C coordinator becomes a bottleneck (>100K TPS).         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 20: INTERVIEW Q&A

### QUESTION 1

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How would you prevent double-spending in a distributed wallet       |
|     system?                                                             |
|                                                                         |
|  A: Use a combination of optimistic locking and atomic SQL operations.  |
|  The wallet table has a version column. The debit operation is a        |
|  single atomic SQL: UPDATE wallet SET balance = balance - amount,       |
|  version = version + 1 WHERE id = X AND version = V AND balance >=      |
|  amount. If affected rows = 0, either the balance is insufficient       |
|  or a concurrent update changed the version. The application            |
|  retries with the new version. For cross-shard P2P transfers, use       |
|  the TC/C pattern with an escrow account (debit sender first, hold      |
|  in escrow, then credit receiver). Idempotency keys prevent             |
|  duplicate processing from client retries.                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 2

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: Why use a double-entry ledger instead of just updating balances?    |
|                                                                         |
|  A: A double-entry ledger provides auditability, correctness, and       |
|  regulatory compliance. Every money movement is recorded as paired      |
|  debit/credit entries that must balance. This means we can always       |
|  reconstruct any wallet's balance by summing its ledger entries.        |
|  If the derived balance disagrees with the stored balance, we have      |
|  detected a bug or corruption. The immutable append-only nature         |
|  ensures no entries can be silently modified, providing a complete      |
|  audit trail for regulators. It also simplifies reconciliation          |
|  with banks since every movement has a clear paper trail.               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 3

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How would you handle the case where a bank callback is lost         |
|     after a successful debit?                                           |
|                                                                         |
|  A: Transactions are created with PENDING status before initiating      |
|  the bank debit. If no callback arrives within a timeout (e.g.,         |
|  5 minutes), the transaction is marked PENDING_VERIFICATION.            |
|  A reconciliation job runs periodically (every 15 minutes) and          |
|  queries the bank's status-check API for all pending transactions.      |
|  If the bank confirms success, we credit the wallet and mark            |
|  COMPLETED. If the bank confirms failure, we mark FAILED. Daily         |
|  bank statement reconciliation acts as the final safety net to          |
|  catch any missed transactions. The user sees "processing" status       |
|  during this period and can contact support if it takes too long.       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 4

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How do you scale the system to handle 100K+ TPS during peak         |
|     events?                                                             |
|                                                                         |
|  A: Horizontal scaling at every layer. API gateway auto-scales          |
|  behind a load balancer. Wallet DB is sharded by wallet_id (32+         |
|  shards) so each shard handles ~3K TPS which is well within             |
|  PostgreSQL limits. Read-heavy operations (balance checks,              |
|  history) go to read replicas via CQRS. Non-critical paths              |
|  (notifications, cashback) are fully async via Kafka, decoupling        |
|  them from the payment critical path. Redis caches hot wallet           |
|  balances for repeated reads. Connection pooling (PgBouncer)            |
|  prevents DB connection exhaustion. Pre-warm capacity before            |
|  known peak events (flash sales, festivals).                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 5

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: What happens if your fraud detection system goes down? Do you       |
|     block all transactions?                                             |
|                                                                         |
|  A: The fraud engine should be designed with a fail-open or             |
|  degraded-mode strategy. If the ML scoring service is unavailable,      |
|  fall back to the deterministic rules engine (velocity limits,          |
|  amount thresholds) which runs locally without external calls.          |
|  If even the rules engine fails, allow low-risk transactions (small     |
|  amounts, known devices, existing contacts) to proceed while            |
|  blocking high-risk ones (new payee, large amount, new device).         |
|  The system should have a circuit breaker that detects fraud            |
|  service failures and activates fallback within milliseconds.           |
|  All transactions during degraded mode are flagged for retroactive      |
|  analysis once the fraud engine recovers.                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 6

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How would you implement real-time transaction notifications?        |
|                                                                         |
|  A: Notifications are decoupled from the transaction path. After a      |
|  successful transaction, an event is published to a Kafka topic.        |
|  The notification service consumes these events and fans out to         |
|  multiple channels: push notifications via FCM/APNs, SMS via            |
|  aggregator (Twilio/Gupshup), and email. Push is attempted first        |
|  (cheapest and fastest). If push delivery fails (device offline),       |
|  fall back to SMS for critical notifications (debits). Email is         |
|  sent for all transactions as a record. The notification service        |
|  maintains templates per event type and supports multi-language.        |
|  Delivery status is tracked and retried with exponential backoff.       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 7

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How do you ensure data consistency between wallet balance and       |
|     ledger entries?                                                     |
|                                                                         |
|  A: The wallet balance update and ledger entry creation happen in       |
|  the same database transaction (ACID). This ensures atomicity:          |
|  either both succeed or both roll back. As a defense-in-depth           |
|  measure, a background reconciliation job runs hourly comparing         |
|  each wallet's stored balance against the computed balance from         |
|  summing all its ledger entries (credits - debits). Any mismatch        |
|  triggers an immediate P0 alert. The wallet table balance is the        |
|  operational source (used for real-time checks), while the ledger       |
|  is the canonical source (used for audits and dispute resolution).      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 8

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How does UPI work differently from a stored-value wallet            |
|     transaction?                                                        |
|                                                                         |
|  A: In a stored-value wallet transaction, money moves between           |
|  accounts within our system. We control the entire flow: debit          |
|  sender's wallet, credit receiver's wallet, both in our database.       |
|  In UPI, money moves between bank accounts via NPCI. Our role as        |
|  PSP is to: collect transaction details, encrypt the UPI PIN,           |
|  forward to NPCI, and await response. We never hold the funds.          |
|  The latency is higher (2-5 seconds vs sub-second for wallet)           |
|  because it involves NPCI routing, bank processing, and inter-bank      |
|  settlement. We must handle async callbacks, timeouts, and status       |
|  check APIs since the flow spans multiple external systems.             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 9

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How would you design the cashback system to be abuse-resistant?     |
|                                                                         |
|  A: Multiple layers of protection. First, per-user claim limits         |
|  (max N cashbacks per campaign, per day). Second, device                |
|  fingerprinting to detect multiple accounts from same device.           |
|  Third, graph analysis to detect circular money transfers among         |
|  colluding accounts (A sends to B, B sends to C, C sends to A           |
|  just to farm cashback). Fourth, minimum time between qualifying        |
|  transactions. Fifth, cashback on P2M only (not P2P) to ensure          |
|  real economic activity. Sixth, delayed cashback crediting              |
|  (24-48 hours) to allow fraud review before payout. Seventh,            |
|  ML model trained on historical abuse patterns to flag suspicious       |
|  claims for manual review before crediting.                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 10

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How would you handle a partial failure in a cross-bank UPI          |
|     transaction where the debit succeeds but credit fails?              |
|                                                                         |
|  A: UPI handles this at the NPCI level with a well-defined protocol.    |
|  If the credit leg fails, NPCI initiates an automatic reversal          |
|  (refund) to the payer's bank. The PSP receives a "DEEMED" status       |
|  indicating the outcome is uncertain. A reconciliation process          |
|  runs that queries NPCI's status API to get the final status.           |
|  If NPCI confirms credit failure, the payer's bank auto-reverses.       |
|  Our system marks the transaction as FAILED/REVERSED and notifies       |
|  the user. The key design principle is that the system should           |
|  eventually reach a consistent state where either both legs             |
|  succeed or both are reversed. We maintain a "pending resolution"       |
|  queue for such transactions with automated retry and escalation.       |
|                                                                         |
+-------------------------------------------------------------------------+
```
