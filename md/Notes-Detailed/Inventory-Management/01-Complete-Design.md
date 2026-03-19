# INVENTORY MANAGEMENT SYSTEM DESIGN (WALMART / AMAZON)

*Complete Design: Requirements, Architecture, and Interview Guide*

## SECTION 1: UNDERSTANDING THE PROBLEM

```
+--------------------------------------------------------------------------+
|                                                                          |
|   an inventory management system tracks the quantity and location        |
|   of every product (SKU) across warehouses, retail stores, and           |
|   online channels. it must prevent overselling, enable real-time         |
|   stock visibility, and coordinate stock movements across a              |
|   complex supply chain.                                                  |
|                                                                          |
|   KEY CHALLENGES:                                                        |
|                                                                          |
|   * millions of SKUs across thousands of locations                       |
|   * concurrent orders from multiple channels (web, app, store, API)      |
|   * flash sales create extreme spike in stock decrements                 |
|   * overselling damages customer trust and causes costly refunds         |
|   * underselling (phantom stock) means lost revenue                      |
|   * stock data must reconcile across distributed systems                 |
|                                                                          |
|   CORE CONCEPTS:                                                         |
|                                                                          |
|   * SKU (stock keeping unit): unique identifier for a product variant    |
|   * location: a warehouse, store, fulfillment center, or virtual loc     |
|   * available quantity: stock that can be sold right now                 |
|   * reserved quantity: stock held for pending orders (not yet shipped)   |
|   * in-transit quantity: stock being moved between locations             |
|   * damaged/defective: stock removed from saleable pool                  |
|   * safety stock: minimum buffer to prevent stockouts                    |
|                                                                          |
|   STOCK STATES:                                                          |
|                                                                          |
|   * available: ready to sell                                             |
|   * reserved: claimed by an order, awaiting fulfillment                  |
|   * allocated: assigned to a specific order for picking                  |
|   * picked: physically retrieved from shelf                              |
|   * packed: packaged and ready for shipment                              |
|   * shipped: handed to carrier                                           |
|   * in_transit: moving between locations                                 |
|   * damaged: removed from saleable inventory                             |
|   * returned: received back, pending inspection                          |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 2: REQUIREMENTS

### FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|   STOCK MANAGEMENT:                                                     |
|                                                                         |
|   * query real-time stock level per SKU per location                    |
|   * query aggregate available stock across all locations                |
|   * reserve stock when an order is placed (atomic decrement)            |
|   * release reserved stock when an order is cancelled                   |
|   * confirm reservation when order is fulfilled (shipped)               |
|   * receive new stock from suppliers (increment available)              |
|   * transfer stock between locations (warehouse to warehouse)           |
|   * record damaged or defective stock (remove from available)           |
|                                                                         |
|   ALERTING AND AUTOMATION:                                              |
|                                                                         |
|   * low-stock alerts when available falls below safety threshold        |
|   * out-of-stock alerts to disable product listing immediately          |
|   * automatic reorder point triggers to supplier systems                |
|   * overstocking alerts for slow-moving inventory                       |
|                                                                         |
|   MULTI-CHANNEL SYNC:                                                   |
|                                                                         |
|   * synchronize stock counts across online, mobile, marketplace         |
|   * ensure in-store POS decrements reflect in online availability       |
|   * marketplace feeds (Amazon, eBay) updated within seconds             |
|   * support channel-specific inventory pools (reserve X for web)        |
|                                                                         |
|   REPORTING AND ANALYTICS:                                              |
|                                                                         |
|   * inventory turnover rate per SKU                                     |
|   * historical stock level time series                                  |
|   * shrinkage and loss tracking                                         |
|   * demand forecasting integration                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### NON-FUNCTIONAL REQUIREMENTS

```
+--------------------------------------------------------------------------+
|                                                                          |
|   CONSISTENCY:                                                           |
|                                                                          |
|   * strong consistency for all stock decrements (reserve, confirm)       |
|   * cannot sell more than available (overselling is unacceptable)        |
|   * eventual consistency acceptable for read-heavy analytics queries     |
|   * all stock changes must be recorded in an immutable audit ledger      |
|                                                                          |
|   SCALE:                                                                 |
|                                                                          |
|   * 1M+ unique SKUs in the catalog                                       |
|   * 10K+ locations (warehouses, stores, fulfillment centers)             |
|   * 100K+ stock operations per second during flash sales                 |
|   * 50M+ inventory records (SKU x location combinations)                 |
|                                                                          |
|   AVAILABILITY:                                                          |
|                                                                          |
|   * 99.99% uptime for stock reservation service                          |
|   * degraded mode: serve from cache if DB is temporarily down            |
|   * no single point of failure in the reservation path                   |
|                                                                          |
|   LATENCY:                                                               |
|                                                                          |
|   * stock query: < 50ms (p99)                                            |
|   * reserve operation: < 100ms (p99)                                     |
|   * multi-channel sync: < 5 seconds end-to-end                           |
|   * alert delivery: < 30 seconds from threshold breach                   |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 3: BACK-OF-ENVELOPE ESTIMATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|   DATA SIZE:                                                            |
|                                                                         |
|   * 1M SKUs x 10K locations = 10B potential combinations                |
|   * in practice, ~50M active inventory records (sparse matrix)          |
|   * each inventory record: ~200 bytes                                   |
|     (sku_id, location_id, available, reserved, damaged, in_transit,     |
|      safety_stock, last_updated, version)                               |
|   * total inventory data: 50M x 200 bytes = 10 GB                       |
|   * fits comfortably in memory (Redis) for hot data                     |
|                                                                         |
|   LEDGER SIZE:                                                          |
|                                                                         |
|   * every stock change is an append-only ledger entry                   |
|   * ~500K orders/day, each touching ~3 SKUs = 1.5M ledger entries/day   |
|   * plus receiving, transfers, adjustments = ~3M entries/day            |
|   * each entry: ~300 bytes                                              |
|   * daily ledger growth: 3M x 300 = 900 MB/day                          |
|   * yearly: ~330 GB (partition by month, archive after 2 years)         |
|                                                                         |
|   TRAFFIC:                                                              |
|                                                                         |
|   * normal: 10K stock operations/sec (reads + writes)                   |
|   * flash sale peak: 100K+ operations/sec (mostly reserves)             |
|   * read:write ratio = 10:1 (many stock checks per purchase)            |
|   * read QPS peak: 1M/sec (product pages showing "in stock")            |
|                                                                         |
|   INFRASTRUCTURE:                                                       |
|                                                                         |
|   * database: sharded PostgreSQL (10+ shards by SKU range)              |
|     WHY PG: Inventory is transactional - ACID prevents overselling.     |
|     CHECK constraints enforce reserved <= quantity. SELECT FOR          |
|     UPDATE for atomic reservation. Sharded by SKU for parallelism.      |
|   * cache: Redis cluster with 64 GB+ (hot SKUs, flash sale stock)       |
|     WHY REDIS: Flash sales hit 10K+ reads/sec for same SKU. Atomic      |
|     DECR for reservation without DB round-trip. Lua scripts for         |
|     check-and-decrement in single operation.                            |
|   * message broker: Kafka (20+ partitions for inventory events)         |
|     WHY KAFKA: Inventory changes fan out to search index, analytics,    |
|     alerting (low-stock). Durable log for replay on reconciliation.     |
|   * inventory service: 30+ instances (auto-scaled for flash sales)      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4: HIGH-LEVEL ARCHITECTURE

```
+--------------------------------------------------------------------------+
|                                                                          |
|   SYSTEM OVERVIEW:                                                       |
|                                                                          |
|         +-------------+  +------------+  +-----------+                   |
|         |  web / app  |  | POS system |  |marketplace|                   |
|         +------+------+  +-----+------+  +-----+-----+                   |
|                |               |               |                         |
|         +------+---------------+---------------+------+                  |
|         |              API gateway / LB               |                  |
|         +------+---------------+---------------+------+                  |
|                |               |               |                         |
|    +-----------+--+  +---------+---+  +--------+--------+                |
|    |  inventory   |  |   order     |  |    sync         |                |
|    |  service     |  |   service   |  |    service      |                |
|    +------+-------+  +------+------+  +--------+--------+                |
|           |                 |                   |                        |
|    +------+-------+  +-----+------+    +-------+-------+                 |
|    |  PostgreSQL  |  |  order DB  |    |  Kafka event  |                 |
|    |  (sharded)   |  |            |    |  bus          |                 |
|    +------+-------+  +------------+    +---+---+---+---+                 |
|           |                                |   |   |                     |
|    +------+-------+             +---------++ +-+--++ +-------+           |
|    |    Redis     |             |analytics | |alert| |report |           |
|    |   (cache)    |             |service   | |svc  | |svc    |           |
|    +--------------+             +----------+ +-----+ +-------+           |
|                                                                          |
+--------------------------------------------------------------------------+
```

### SERVICE RESPONSIBILITIES

```
+-------------------------------------------------------------------------+
|                                                                         |
|   INVENTORY SERVICE:                                                    |
|                                                                         |
|   * core service for all stock operations (query, reserve, release)     |
|   * enforces business rules (cannot go negative, safety stock)          |
|   * writes to PostgreSQL for durability, Redis for speed                |
|   * publishes every stock change to Kafka event bus                     |
|   * exposes gRPC API for internal services, REST for external           |
|                                                                         |
|   WAREHOUSE SERVICE:                                                    |
|                                                                         |
|   * manages physical warehouse operations                               |
|   * tracks bin/shelf/aisle locations within each warehouse              |
|   * coordinates pick-pack-ship workflows                                |
|   * handles receiving (supplier deliveries) and put-away                |
|   * manages cycle counting and physical inventory audits                |
|                                                                         |
|   ORDER SERVICE:                                                        |
|                                                                         |
|   * orchestrates the order lifecycle                                    |
|   * calls inventory service to reserve stock at order creation          |
|   * calls inventory service to confirm at shipment                      |
|   * calls inventory service to release on cancellation                  |
|   * implements saga pattern for distributed transactions                |
|                                                                         |
|   SYNC SERVICE:                                                         |
|                                                                         |
|   * synchronizes stock levels across channels                           |
|   * pushes updates to marketplace APIs (Amazon, eBay sellers)           |
|   * receives POS transaction events from retail stores                  |
|   * implements CQRS read models for channel-specific views              |
|                                                                         |
|   ANALYTICS SERVICE:                                                    |
|                                                                         |
|   * consumes Kafka events for real-time dashboards                      |
|   * computes inventory turnover, days-on-hand, fill rates               |
|   * feeds demand forecasting models                                     |
|   * generates shrinkage and loss reports                                |
|                                                                         |
|   ALERT SERVICE:                                                        |
|                                                                         |
|   * monitors stock levels against configured thresholds                 |
|   * triggers low-stock, out-of-stock, and overstock alerts              |
|   * sends notifications via email, Slack, PagerDuty                     |
|   * can trigger automatic reorder workflows                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5: DATA MODEL

### CORE TABLES

```
+-------------------------------------------------------------------------+
|                                                                         |
|   TABLE: skus                                                           |
|                                                                         |
|   * id              BIGINT PRIMARY KEY                                  |
|   * sku_code        VARCHAR(50) UNIQUE NOT NULL                         |
|   * name            VARCHAR(255) NOT NULL                               |
|   * category_id     BIGINT REFERENCES categories(id)                    |
|   * unit_cost       DECIMAL(12,2)                                       |
|   * weight_grams    INTEGER                                             |
|   * dimensions_json JSONB                                               |
|   * is_active       BOOLEAN DEFAULT true                                |
|   * created_at      TIMESTAMP DEFAULT now()                             |
|                                                                         |
|   TABLE: locations                                                      |
|                                                                         |
|   * id              BIGINT PRIMARY KEY                                  |
|   * code            VARCHAR(50) UNIQUE NOT NULL                         |
|   * name            VARCHAR(255)                                        |
|   * type            ENUM('warehouse','store','fulfillment','virtual')   |
|   * address_json    JSONB                                               |
|   * region          VARCHAR(50)                                         |
|   * is_active       BOOLEAN DEFAULT true                                |
|                                                                         |
|   TABLE: inventory_records                                              |
|                                                                         |
|   * id              BIGINT PRIMARY KEY                                  |
|   * sku_id          BIGINT REFERENCES skus(id)                          |
|   * location_id     BIGINT REFERENCES locations(id)                     |
|   * available       INTEGER NOT NULL DEFAULT 0                          |
|   * reserved        INTEGER NOT NULL DEFAULT 0                          |
|   * damaged         INTEGER NOT NULL DEFAULT 0                          |
|   * in_transit      INTEGER NOT NULL DEFAULT 0                          |
|   * safety_stock    INTEGER NOT NULL DEFAULT 0                          |
|   * version         INTEGER NOT NULL DEFAULT 0                          |
|   * updated_at      TIMESTAMP DEFAULT now()                             |
|   * UNIQUE(sku_id, location_id)                                         |
|   * CHECK(available >= 0)                                               |
|   * CHECK(reserved >= 0)                                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### INVENTORY LEDGER

```
+--------------------------------------------------------------------------+
|                                                                          |
|   the ledger is an append-only audit trail of every stock change.        |
|   it enables full reconstruction of inventory state at any point         |
|   in time and serves as the source of truth for reconciliation.          |
|                                                                          |
|   TABLE: inventory_ledger                                                |
|                                                                          |
|   * id              BIGINT PRIMARY KEY (auto-increment)                  |
|   * sku_id          BIGINT NOT NULL                                      |
|   * location_id     BIGINT NOT NULL                                      |
|   * operation       ENUM('reserve','confirm','release','receive',        |
|                          'transfer_out','transfer_in','damage',          |
|                          'adjust','return')                              |
|   * quantity         INTEGER NOT NULL                                    |
|   * reference_type   VARCHAR(50)   -- 'order', 'transfer', 'po'          |
|   * reference_id     VARCHAR(100)  -- the order_id, transfer_id, etc     |
|   * before_available INTEGER                                             |
|   * after_available  INTEGER                                             |
|   * before_reserved  INTEGER                                             |
|   * after_reserved   INTEGER                                             |
|   * actor_id         BIGINT        -- user or system that made change    |
|   * reason           TEXT                                                |
|   * created_at       TIMESTAMP DEFAULT now()                             |
|                                                                          |
|   * partitioned by created_at (monthly partitions)                       |
|   * indexes on (sku_id, location_id, created_at) for lookups             |
|   * archived to cold storage (S3 + Athena) after 2 years                 |
|                                                                          |
|   LEDGER GUARANTEES:                                                     |
|                                                                          |
|   * every write to inventory_records has a corresponding ledger entry    |
|   * both writes happen in the same database transaction                  |
|   * sum of ledger entries must equal current inventory state             |
|   * reconciliation job runs nightly to detect drift                      |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 6: STOCK OPERATIONS

### RESERVE OPERATION

```
+--------------------------------------------------------------------------+
|                                                                          |
|   triggered when a customer places an order. must atomically             |
|   decrement available and increment reserved.                            |
|                                                                          |
|   PSEUDO-CODE:                                                           |
|                                                                          |
|   BEGIN TRANSACTION                                                      |
|     SELECT available, reserved, version                                  |
|       FROM inventory_records                                             |
|       WHERE sku_id = :sku AND location_id = :loc                         |
|       FOR UPDATE                                                         |
|                                                                          |
|     IF available < :quantity THEN                                        |
|       ROLLBACK                                                           |
|       RETURN insufficient_stock                                          |
|     END IF                                                               |
|                                                                          |
|     UPDATE inventory_records                                             |
|       SET available = available - :quantity,                             |
|           reserved = reserved + :quantity,                               |
|           version = version + 1,                                         |
|           updated_at = now()                                             |
|       WHERE sku_id = :sku AND location_id = :loc                         |
|                                                                          |
|     INSERT INTO inventory_ledger                                         |
|       (sku_id, location_id, operation, quantity,                         |
|        reference_type, reference_id, ...)                                |
|       VALUES (:sku, :loc, 'reserve', :quantity,                          |
|        'order', :order_id, ...)                                          |
|   COMMIT                                                                 |
|                                                                          |
|   * the FOR UPDATE clause acquires a row-level lock                      |
|   * prevents concurrent reserves from overselling                        |
|   * CHECK constraint on available >= 0 is a safety net                   |
|                                                                          |
+--------------------------------------------------------------------------+
```

### CONFIRM, RELEASE, AND RECEIVE

```
+--------------------------------------------------------------------------+
|                                                                          |
|   CONFIRM (order shipped):                                               |
|                                                                          |
|   * decrement reserved by quantity                                       |
|   * the stock has left the building, no longer in our inventory          |
|   * reserved -= quantity (no change to available)                        |
|   * ledger entry: operation = 'confirm'                                  |
|                                                                          |
|   RELEASE (order cancelled):                                             |
|                                                                          |
|   * move stock from reserved back to available                           |
|   * available += quantity, reserved -= quantity                          |
|   * ledger entry: operation = 'release'                                  |
|   * must handle partial cancellations (release only some items)          |
|                                                                          |
|   RECEIVE (supplier delivery):                                           |
|                                                                          |
|   * increment available by received quantity                             |
|   * triggered by warehouse scanning incoming shipment                    |
|   * available += quantity                                                |
|   * ledger entry: operation = 'receive', reference = purchase_order      |
|   * may trigger low-stock alert clearance                                |
|                                                                          |
|   TRANSFER (between locations):                                          |
|                                                                          |
|   * two-phase operation across source and destination                    |
|   * source: available -= quantity, in_transit += quantity                |
|   * destination (on arrival): in_transit -= quantity (at source),        |
|     available += quantity (at destination)                               |
|   * ledger entries at both locations                                     |
|   * transfer has its own lifecycle: requested, in_transit, received      |
|                                                                          |
|   DAMAGE (defective stock):                                              |
|                                                                          |
|   * remove from available, add to damaged                                |
|   * available -= quantity, damaged += quantity                           |
|   * ledger entry: operation = 'damage', reason = description             |
|   * triggers shrinkage reporting                                         |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 7: OVERSELLING PREVENTION

### DATABASE-LEVEL STRATEGIES

```
+-------------------------------------------------------------------------+
|                                                                         |
|   APPROACH 1: PESSIMISTIC LOCKING (SELECT FOR UPDATE)                   |
|                                                                         |
|   * lock the inventory row before reading                               |
|   * other transactions block until the lock is released                 |
|   * guarantees no race condition                                        |
|   * pros: simplest to implement, strongest guarantee                    |
|   * cons: high contention on popular SKUs, deadlock risk                |
|   * best for: low-to-medium concurrency scenarios                       |
|                                                                         |
|   APPROACH 2: OPTIMISTIC LOCKING (version column)                       |
|                                                                         |
|   * read the row with current version                                   |
|   * perform business logic validation                                   |
|   * UPDATE ... WHERE version = :expected_version                        |
|   * if rows_affected = 0, someone else changed it; retry                |
|   * pros: no blocking, better throughput under moderate contention      |
|   * cons: retries waste work under high contention                      |
|   * best for: medium concurrency, when most operations succeed          |
|                                                                         |
|   APPROACH 3: CHECK CONSTRAINT AS SAFETY NET                            |
|                                                                         |
|   * always have CHECK(available >= 0) on the table                      |
|   * even if application logic has a bug, DB prevents negative stock     |
|   * the constraint violation throws an error the app can catch          |
|   * this is a backstop, not a primary strategy                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### REDIS-BASED STRATEGIES

```
+-------------------------------------------------------------------------+
|                                                                         |
|   APPROACH 4: REDIS ATOMIC DECREMENT                                    |
|                                                                         |
|   * store available stock in Redis: key = "stock:{sku}:{loc}"           |
|   * use DECRBY to atomically decrement                                  |
|   * check result: if < 0, the stock was insufficient                    |
|     * immediately INCRBY to restore, return error                       |
|                                                                         |
|   Lua script for atomic reserve:                                        |
|                                                                         |
|     local current = tonumber(redis.call('GET', key))                    |
|     if current >= quantity then                                         |
|       redis.call('DECRBY', key, quantity)                               |
|       return current - quantity  -- new available                       |
|     end                                                                 |
|     return -1  -- insufficient stock                                    |
|                                                                         |
|   * pros: sub-millisecond latency, handles extreme concurrency          |
|   * cons: must sync with DB (dual-write problem), Redis crash risk      |
|   * mitigate: write-ahead to DB, confirm in Redis, reconcile            |
|                                                                         |
|   APPROACH 5: QUEUE SERIALIZATION                                       |
|                                                                         |
|   * all reserve requests for a SKU go to a single Kafka partition       |
|   * a dedicated consumer processes them sequentially                    |
|   * eliminates concurrency entirely for a given SKU                     |
|   * pros: zero race conditions, simple logic                            |
|   * cons: higher latency (queue delay), consumer bottleneck             |
|   * best for: very high-value items where correctness > speed           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### FLASH SALE PATTERN

```
+--------------------------------------------------------------------------+
|                                                                          |
|   PROBLEM: 100K users try to buy 1000 units in the first second          |
|                                                                          |
|   FLASH SALE ARCHITECTURE:                                               |
|                                                                          |
|   1. PRE-LOAD: before sale starts, load stock into Redis                 |
|      SET stock:flash:{sku} 1000                                          |
|                                                                          |
|   2. GATE: use a token bucket or counter to limit concurrent             |
|      requests to the reserve endpoint (e.g. max 5000 in-flight)          |
|                                                                          |
|   3. RESERVE: use Redis Lua script for atomic decrement                  |
|      * if stock > 0: decrement and return success token                  |
|      * if stock = 0: return "sold out" immediately                       |
|                                                                          |
|   4. QUEUE: successful reserves placed in order queue                    |
|      * order service processes queue at sustainable rate                 |
|      * DB writes happen asynchronously behind the queue                  |
|                                                                          |
|   5. TIMEOUT: if order not confirmed within 10 minutes,                  |
|      release the reserved stock back to Redis                            |
|                                                                          |
|   FLOW DIAGRAM:                                                          |
|                                                                          |
|   user -> rate limiter -> Redis DECR -> order queue -> DB persist        |
|                              |                                           |
|                         sold out? --> reject immediately                 |
|                                                                          |
|   * 99% of requests answered in < 10ms (Redis)                           |
|   * only successful reserves hit the database                            |
|   * reduces DB load from 100K/sec to 1K/sec                              |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 8: MULTI-CHANNEL SYNC

```
+-------------------------------------------------------------------------+
|                                                                         |
|   CHALLENGE: stock sold in-store must immediately reflect online,       |
|   and vice versa. marketplace listings must stay accurate.              |
|                                                                         |
|   CHANNELS:                                                             |
|                                                                         |
|   * direct website (walmart.com, amazon.com)                            |
|   * mobile app                                                          |
|   * physical retail stores (POS terminals)                              |
|   * third-party marketplaces (seller accounts on other platforms)       |
|   * B2B / wholesale portal                                              |
|                                                                         |
|   SYNC STRATEGY: EVENT-DRIVEN VIA KAFKA                                 |
|                                                                         |
|   * every stock change publishes an event to Kafka                      |
|   * channel-specific consumers update their respective systems          |
|   * decouples channels: adding a new channel = new consumer             |
|                                                                         |
|   event schema:                                                         |
|   {                                                                     |
|     "event_type": "stock_changed",                                      |
|     "sku_id": 12345,                                                    |
|     "location_id": 67,                                                  |
|     "available": 142,                                                   |
|     "reserved": 28,                                                     |
|     "timestamp": "2026-03-14T10:30:00Z",                                |
|     "source": "order_service",                                          |
|     "reference_id": "ORD-789456"                                        |
|   }                                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CQRS PATTERN FOR CHANNEL VIEWS

```
+-------------------------------------------------------------------------+
|                                                                         |
|   each channel maintains its own read-optimized view of inventory.      |
|                                                                         |
|   WRITE SIDE (command):                                                 |
|                                                                         |
|   * single source of truth in PostgreSQL                                |
|   * all writes go through inventory service                             |
|   * strict consistency for all mutations                                |
|                                                                         |
|   READ SIDE (query):                                                    |
|                                                                         |
|   * website: Redis cache with sub-second updates                        |
|   * mobile app: Redis cache + push notifications                        |
|   * marketplace: dedicated sync service with rate-limited API calls     |
|   * analytics: ClickHouse for aggregated time-series queries            |
|   * POS: local cache at store with periodic sync                        |
|                                                                         |
|   CHANNEL-SPECIFIC INVENTORY POOLS:                                     |
|                                                                         |
|   * some businesses reserve stock per channel:                          |
|     * 500 units for website                                             |
|     * 200 units for marketplace                                         |
|     * 300 units for stores                                              |
|   * overflow pool: shared stock available to any channel when           |
|     their dedicated pool runs out                                       |
|   * pool sizes adjusted dynamically based on demand patterns            |
|                                                                         |
|   POS SYNC CHALLENGES:                                                  |
|                                                                         |
|   * store POS may operate offline (internet outage)                     |
|   * use local-first architecture: POS writes locally, syncs later       |
|   * on reconnect, replay events and reconcile conflicts                 |
|   * conflict resolution: POS "wins" for in-store sales (physical)       |
|   * overselling risk during offline: accept and reconcile manually      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 9: EVENT-DRIVEN ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|   every inventory change produces a Kafka event. downstream             |
|   services consume these events for their specific needs.               |
|                                                                         |
|   KAFKA TOPICS:                                                         |
|                                                                         |
|   * inventory.stock_changed   -- all stock mutations                    |
|   * inventory.low_stock       -- threshold breach events                |
|   * inventory.out_of_stock    -- zero-available events                  |
|   * inventory.received        -- new stock from suppliers               |
|   * inventory.transferred     -- inter-location movements               |
|   * inventory.damaged         -- defective stock events                 |
|                                                                         |
|   CONSUMER GROUPS:                                                      |
|                                                                         |
|   * analytics-consumer:                                                 |
|     reads stock_changed, builds time-series in ClickHouse               |
|     computes real-time dashboards (current stock, turnover)             |
|                                                                         |
|   * alert-consumer:                                                     |
|     reads low_stock and out_of_stock events                             |
|     sends notifications to operations team                              |
|     triggers automatic reorder if configured                            |
|                                                                         |
|   * search-consumer:                                                    |
|     reads stock_changed, updates product search index                   |
|     marks products as "in stock" or "out of stock" in Elasticsearch     |
|                                                                         |
|   * marketplace-sync-consumer:                                          |
|     reads stock_changed, pushes updates to marketplace APIs             |
|     implements rate limiting per marketplace (e.g. 100 calls/sec)       |
|                                                                         |
|   * reporting-consumer:                                                 |
|     reads all events, aggregates daily/weekly/monthly reports           |
|     feeds into data warehouse for BI tools                              |
|                                                                         |
|   EVENT ORDERING:                                                       |
|                                                                         |
|   * partition key = sku_id ensures all events for a SKU are ordered     |
|   * consumers process events for each SKU in sequence                   |
|   * enables correct reconstruction of inventory state                   |
|                                                                         |
|   EXACTLY-ONCE PROCESSING:                                              |
|                                                                         |
|   * use Kafka consumer group offsets + idempotent consumers             |
|   * each event has a unique event_id                                    |
|   * consumers track last processed event_id to skip duplicates          |
|   * critical for financial reconciliation and reporting                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 10: WAREHOUSE OPERATIONS

### BIN AND SHELF TRACKING

```
+--------------------------------------------------------------------------+
|                                                                          |
|   within a warehouse, stock is organized by physical location:           |
|                                                                          |
|   LOCATION HIERARCHY:                                                    |
|                                                                          |
|   warehouse -> zone -> aisle -> rack -> shelf -> bin                     |
|                                                                          |
|   * each bin has a unique barcode / QR code                              |
|   * a SKU can exist in multiple bins (e.g. overflow areas)               |
|   * bin assignment optimized for pick efficiency                         |
|                                                                          |
|   TABLE: bin_inventory                                                   |
|                                                                          |
|   * bin_id          VARCHAR(50)                                          |
|   * sku_id          BIGINT                                               |
|   * quantity         INTEGER                                             |
|   * zone             VARCHAR(10) -- 'A', 'B', 'COLD', 'HAZMAT'           |
|   * aisle            INTEGER                                             |
|   * rack             INTEGER                                             |
|   * shelf            INTEGER                                             |
|   * last_counted_at  TIMESTAMP                                           |
|                                                                          |
|   * total quantity across all bins for a SKU at a location must          |
|     equal the available + reserved in inventory_records                  |
|                                                                          |
+--------------------------------------------------------------------------+
```

### PICK-PACK-SHIP WORKFLOW

```
+--------------------------------------------------------------------------+
|                                                                          |
|   ORDER FULFILLMENT FLOW:                                                |
|                                                                          |
|   1. ALLOCATION: order service assigns items to specific bins            |
|      * algorithm: nearest bin to packing station, FIFO by receipt        |
|      * creates pick_list with bin locations and quantities               |
|                                                                          |
|   2. PICKING: warehouse worker follows optimized pick route              |
|      * scan bin barcode -> scan item barcode -> confirm quantity         |
|      * system validates: correct SKU, correct bin, correct count         |
|      * partial picks allowed if bin has insufficient quantity            |
|                                                                          |
|   3. PACKING: items consolidated at packing station                      |
|      * verify all items for order are present                            |
|      * select box size based on item dimensions                          |
|      * print shipping label and packing slip                             |
|      * weight check: actual vs expected (catch errors)                   |
|                                                                          |
|   4. SHIPPING: package handed to carrier                                 |
|      * scan package -> carrier pickup scan                               |
|      * inventory status: reserved -> confirmed (shipped)                 |
|      * tracking number associated with order                             |
|                                                                          |
|   PICK ROUTE OPTIMIZATION:                                               |
|                                                                          |
|   * snake pattern: traverse aisles in alternating directions             |
|   * batch picking: pick items for multiple orders in one trip            |
|   * zone picking: workers assigned to zones, items consolidated          |
|   * wave picking: orders grouped by carrier cutoff time                  |
|                                                                          |
+--------------------------------------------------------------------------+
```

### CYCLE COUNTING

```
+--------------------------------------------------------------------------+
|                                                                          |
|   cycle counting is continuous auditing of physical stock against        |
|   system records, replacing full annual physical inventory counts.       |
|                                                                          |
|   APPROACH:                                                              |
|                                                                          |
|   * divide all bins into counting groups                                 |
|   * count a subset of bins each day (rotate through all yearly)          |
|   * prioritize high-value and high-velocity SKUs                         |
|   * ABC analysis: count A items monthly, B quarterly, C annually         |
|                                                                          |
|   COUNTING PROCESS:                                                      |
|                                                                          |
|   1. system generates count task for assigned bins                       |
|   2. worker physically counts items in each bin                          |
|   3. worker enters count into handheld scanner                           |
|   4. system compares physical count to system record                     |
|   5. if discrepancy > threshold: flag for recount                        |
|   6. if confirmed discrepancy: create adjustment ledger entry            |
|                                                                          |
|   INVENTORY ADJUSTMENT:                                                  |
|                                                                          |
|   * system count: 50, physical count: 47                                 |
|   * adjustment: -3 units, operation = 'adjust'                           |
|   * requires supervisor approval for adjustments above threshold         |
|   * all adjustments tracked for shrinkage analysis                       |
|                                                                          |
|   FIFO / LIFO TRACKING:                                                  |
|                                                                          |
|   * FIFO (first in, first out): default for perishables, food            |
|     * track receipt_date per batch in each bin                           |
|     * pick oldest batch first                                            |
|   * LIFO (last in, first out): used for accounting purposes              |
|   * lot tracking: required for pharmaceuticals, recalls                  |
|   * expiry tracking: alert if stock nears expiry date                    |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 11: SCALING STRATEGIES

### DATABASE SCALING

```
+-------------------------------------------------------------------------+
|                                                                         |
|   SHARD BY SKU:                                                         |
|                                                                         |
|   * shard key: hash(sku_id) % num_shards                                |
|   * all inventory records for a SKU on the same shard                   |
|   * enables efficient queries: "stock for SKU X across all locations"   |
|                                                                         |
|   shard 0:  sku_id hash [0 - 999]                                       |
|   shard 1:  sku_id hash [1000 - 1999]                                   |
|   shard 2:  sku_id hash [2000 - 2999]                                   |
|   ...                                                                   |
|   shard 15: sku_id hash [15000 - 15999]                                 |
|                                                                         |
|   * cross-shard queries (e.g. "all stock at location Y") use            |
|     scatter-gather across all shards, or a separate read replica        |
|     that aggregates data for location-centric views                     |
|                                                                         |
|   READ REPLICAS:                                                        |
|                                                                         |
|   * each shard has 2 read replicas                                      |
|   * product pages read from replicas (eventual consistency ok)          |
|   * reserve operations always go to primary (strong consistency)        |
|   * replication lag < 100ms under normal conditions                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### REDIS FOR HOT SKUS

```
+-------------------------------------------------------------------------+
|                                                                         |
|   HOT SKU DETECTION:                                                    |
|                                                                         |
|   * monitor request rate per SKU (sliding window counter)               |
|   * if read QPS > 1000 or write QPS > 100: classify as "hot"            |
|   * hot SKUs get dedicated Redis keys with TTL-based refresh            |
|                                                                         |
|   CACHING STRATEGY:                                                     |
|                                                                         |
|   * normal SKU: cache-aside pattern                                     |
|     * read: check Redis -> if miss, read DB, populate Redis             |
|     * write: update DB, invalidate Redis (or update through)            |
|                                                                         |
|   * hot SKU: write-through pattern                                      |
|     * Redis is primary for reads AND atomic decrements                  |
|     * DB writes happen asynchronously via Kafka                         |
|     * reconciliation job compares Redis and DB every 60 seconds         |
|                                                                         |
|   REDIS DATA STRUCTURES:                                                |
|                                                                         |
|   * stock:{sku}:{loc}         -> STRING (available count)               |
|   * stock:{sku}:total         -> STRING (aggregate across locations)    |
|   * stock:{sku}:reserved      -> STRING (reserved count)                |
|   * hot_skus                  -> SET (currently hot SKU ids)            |
|                                                                         |
|   FAILOVER:                                                             |
|                                                                         |
|   * Redis Sentinel for automatic failover                               |
|   * if Redis is down, fall back to database with pessimistic locking    |
|   * circuit breaker pattern: after 3 Redis failures, switch to DB       |
|   * on Redis recovery, warm cache from DB before resuming               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### TIME-SERIES HISTORY AND MULTI-REGION

```
+-------------------------------------------------------------------------+
|                                                                         |
|   TIME-SERIES STORAGE:                                                  |
|                                                                         |
|   * every stock_changed event stored in ClickHouse (columnar DB)        |
|   * enables queries like: "stock level for SKU X at time T"             |
|   * retention: raw events for 2 years, aggregated for 5 years           |
|   * used for demand forecasting, trend analysis, auditing               |
|                                                                         |
|   PARTITIONING:                                                         |
|                                                                         |
|   * PostgreSQL ledger: partitioned by month on created_at               |
|   * ClickHouse: partitioned by day, sorted by sku_id                    |
|   * old partitions archived to S3, queryable via Athena                 |
|                                                                         |
|   MULTI-REGION DEPLOYMENT:                                              |
|                                                                         |
|   * each region has its own inventory service + database                |
|   * region owns its warehouses and stores                               |
|   * cross-region stock transfers are explicit operations                |
|   * global catalog service for SKU metadata (eventually consistent)     |
|                                                                         |
|   REGION TOPOLOGY:                                                      |
|                                                                         |
|   +-------------+     +-------------+     +-------------+               |
|   |  US-EAST    |     |  US-WEST    |     |  EU-WEST    |               |
|   | 5 warehouses| <-> | 3 warehouses| <-> | 4 warehouses|               |
|   | 2000 stores |     | 1500 stores |     | 1000 stores |               |
|   +-------------+     +-------------+     +-------------+               |
|                                                                         |
|   * each region is self-contained for latency                           |
|   * cross-region reads via global read replica (for reporting)          |
|   * cross-region writes only for transfers (async via Kafka)            |
|   * global aggregation in data warehouse for executive dashboards       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 12: INTERVIEW QUESTIONS AND ANSWERS

### Q1: HOW DO YOU PREVENT OVERSELLING DURING A FLASH SALE?

```
+-------------------------------------------------------------------------+
|                                                                         |
|   * pre-load flash sale stock into Redis before the sale starts         |
|   * use a Lua script for atomic check-and-decrement in Redis            |
|   * if Redis returns < 0, the stock is gone; reject immediately         |
|   * only successful reserves go to the order queue for DB persist       |
|   * this reduces DB load from 100K/sec to just the successful           |
|     reserves (e.g. 1K/sec for 1000 units)                               |
|   * add a rate limiter in front to cap in-flight requests               |
|   * reservation timeout (10 min) releases stock if order abandoned      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q2: HOW DO YOU HANDLE INVENTORY ACROSS MULTIPLE WAREHOUSES?

```
+-------------------------------------------------------------------------+
|                                                                         |
|   * each warehouse is a separate location in the inventory system       |
|   * aggregate "available" across all warehouses for product display     |
|   * when an order comes in, choose the optimal warehouse:               |
|     * closest to the customer (minimize shipping cost/time)             |
|     * has sufficient stock                                              |
|     * has available picking capacity                                    |
|   * the reservation is made against a specific warehouse                |
|   * if the chosen warehouse runs out, order routing can failover        |
|     to the next-closest warehouse with stock                            |
|   * inter-warehouse transfers to rebalance stock proactively            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q3: WHAT IS YOUR DATA CONSISTENCY STRATEGY?

```
+-------------------------------------------------------------------------+
|                                                                         |
|   * writes (reserve, release, confirm) use strong consistency           |
|     via PostgreSQL transactions with row-level locking                  |
|   * reads for product pages use eventual consistency                    |
|     via read replicas or Redis cache (< 100ms lag)                      |
|   * the inventory ledger provides an immutable audit trail              |
|   * nightly reconciliation job compares ledger sum vs current state     |
|   * for Redis-based operations (flash sales), async DB persistence      |
|     with periodic reconciliation ensures durability                     |
|   * two-phase commit is avoided; instead use saga pattern               |
|     with compensating transactions for multi-service operations         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q4: HOW DO YOU HANDLE STOCK SYNC WITH OFFLINE POS?

```
+-------------------------------------------------------------------------+
|                                                                         |
|   * POS systems use local-first architecture with SQLite                |
|   * all sales recorded locally first, queued for sync                   |
|   * when connectivity restores, events replay to central system         |
|   * conflict resolution:                                                |
|     * physical sale always wins (item already left the store)           |
|     * if online order reserved the same stock: cancel online order      |
|       and notify customer                                               |
|   * minimize risk: POS stock buffer (reserve 10% for online)            |
|   * real-time sync when online: POS pushes every transaction            |
|     within 2 seconds via websocket connection                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q5: HOW DO YOU DESIGN THE INVENTORY LEDGER?

```
+-------------------------------------------------------------------------+
|                                                                         |
|   * append-only table recording every stock mutation                    |
|   * columns: sku_id, location_id, operation, quantity, before/after     |
|     values, reference_type, reference_id, actor, timestamp              |
|   * partitioned by month for query performance                          |
|   * the sum of all ledger entries for a SKU/location must equal         |
|     the current inventory_records values                                |
|   * enables point-in-time reconstruction of inventory state             |
|   * supports audit requirements, dispute resolution, and analytics      |
|   * archived to cold storage after 2 years, queryable via Athena        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q6: HOW DO YOU SCALE THE SYSTEM FOR 1M+ SKUS?

```
+--------------------------------------------------------------------------+
|                                                                          |
|   * shard the database by sku_id (hash-based partitioning)               |
|   * 16+ shards, each handling ~60K SKUs worth of inventory records       |
|   * Redis cluster for hot SKUs and aggregate stock counts                |
|   * read replicas for product catalog queries (read-heavy)               |
|   * Elasticsearch for full-text search across SKU attributes             |
|   * Kafka for decoupling write path from downstream consumers            |
|   * auto-scaling inventory service instances based on request rate       |
|   * batch operations for bulk stock updates (supplier deliveries)        |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Q7: HOW DO YOU IMPLEMENT LOW-STOCK ALERTS?

```
+-------------------------------------------------------------------------+
|                                                                         |
|   * each SKU has a configurable safety_stock threshold per location     |
|   * after every stock change, compare available vs safety_stock         |
|   * if available <= safety_stock and was previously above:              |
|     publish "low_stock" event to Kafka                                  |
|   * if available = 0: publish "out_of_stock" event                      |
|   * alert service consumes these events and:                            |
|     * sends notification (email, Slack, SMS)                            |
|     * optionally triggers automatic purchase order to supplier          |
|     * updates product page ("only 3 left!" messaging)                   |
|   * debouncing: suppress repeat alerts within a cooldown period         |
|   * alert escalation: if no restock within 24h, escalate to manager     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q8: HOW DO YOU HANDLE RETURNS?

```
+-------------------------------------------------------------------------+
|                                                                         |
|   * customer initiates return, system creates return authorization      |
|   * item arrives at warehouse, goes through inspection:                 |
|     * if sellable: available += quantity, ledger op = 'return'          |
|     * if damaged: damaged += quantity, ledger op = 'return_damaged'     |
|     * if needs refurbishment: held in separate pool                     |
|   * the return is linked to the original order for traceability         |
|   * return processing is async: stock not available until inspected     |
|   * metrics: return rate by SKU, reason codes, time to restock          |
|   * high-return SKUs flagged for quality review or listing changes      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q9: WHAT HAPPENS IF REDIS AND THE DATABASE DISAGREE?

```
+-------------------------------------------------------------------------+
|                                                                         |
|   * Redis is treated as a fast cache / acceleration layer               |
|   * PostgreSQL is the source of truth for inventory                     |
|   * reconciliation job runs every 60 seconds:                           |
|     * compare Redis stock:{sku}:{loc} with DB available column          |
|     * if mismatch: log the discrepancy, alert ops team                  |
|     * for small drift (< 5%): auto-correct Redis from DB                |
|     * for large drift: flag for manual investigation                    |
|   * during flash sales (Redis is primary): reconcile after sale ends    |
|   * all corrections generate ledger entries with operation = 'adjust'   |
|   * monitoring: track drift rate as a system health metric              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q10: HOW DO YOU SUPPORT MULTI-CHANNEL INVENTORY POOLS?

```
+-------------------------------------------------------------------------+
|                                                                         |
|   * partition available stock into channel-specific pools:              |
|     * web_pool: 50%, marketplace_pool: 20%, store_pool: 30%             |
|   * implement as virtual locations or as separate counters              |
|   * each channel reserves from its own pool first                       |
|   * if a channel's pool is exhausted, draw from shared overflow pool    |
|   * pool sizes recalculated dynamically:                                |
|     * hourly rebalance based on recent demand per channel               |
|     * seasonal adjustments (more store stock during holidays)           |
|   * implementation: Redis hash per SKU                                  |
|     HSET stock:{sku} web 500 marketplace 200 store 300 overflow 100     |
|   * atomic Lua script checks channel pool, falls back to overflow       |
|   * total across all pools must equal physical available stock          |
|   * reconciliation ensures pool sum matches inventory_records           |
|                                                                         |
+-------------------------------------------------------------------------+
```
