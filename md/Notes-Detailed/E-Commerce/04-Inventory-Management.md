# E-COMMERCE SYSTEM DESIGN
*Chapter 4: Inventory Management*

Inventory management is one of the most challenging aspects of e-commerce.
This chapter covers inventory strategies, reservation patterns, and
handling race conditions during flash sales.

## SECTION 4.1: THE INVENTORY CHALLENGE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY IS INVENTORY HARD?                                               |
|                                                                         |
|  1. RACE CONDITIONS                                                    |
|  --------------------                                                   |
|  100 users try to buy the last item simultaneously.                   |
|  Who gets it?                                                         |
|                                                                         |
|  2. DISTRIBUTED INVENTORY                                              |
|  --------------------------                                             |
|  Stock is spread across multiple warehouses.                          |
|  Need to aggregate but also route to nearest.                        |
|                                                                         |
|  3. RESERVATION vs IMMEDIATE DEDUCT                                   |
|  -------------------------------------                                  |
|  When to deduct stock? On add to cart? Checkout? Shipping?           |
|                                                                         |
|  4. FLASH SALES                                                        |
|  -------------                                                          |
|  10,000 users want 100 items at exact same second.                   |
|  Database can't handle that many writes.                             |
|                                                                         |
|  5. OVERSELLING vs UNDERSELLING                                       |
|  ---------------------------------                                      |
|  Overselling: Sell more than in stock (angry customers)              |
|  Underselling: Show "out of stock" when items exist (lost sales)    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.2: INVENTORY DATA MODEL

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DATABASE SCHEMA                                                       |
|                                                                         |
|  CREATE TABLE products (                                               |
|      id              BIGSERIAL PRIMARY KEY,                           |
|      sku             VARCHAR(50) UNIQUE NOT NULL,                     |
|      name            VARCHAR(255) NOT NULL,                           |
|      -- Global inventory view (denormalized)                          |
|      total_stock     INTEGER DEFAULT 0,                               |
|      reserved_stock  INTEGER DEFAULT 0,                               |
|      available_stock INTEGER GENERATED ALWAYS AS                      |
|                      (total_stock - reserved_stock) STORED            |
|  );                                                                    |
|                                                                         |
|  CREATE TABLE warehouses (                                             |
|      id              BIGSERIAL PRIMARY KEY,                           |
|      code            VARCHAR(20) UNIQUE NOT NULL,                     |
|      name            VARCHAR(255) NOT NULL,                           |
|      city            VARCHAR(100),                                     |
|      latitude        DECIMAL(10, 8),                                  |
|      longitude       DECIMAL(11, 8)                                   |
|  );                                                                    |
|                                                                         |
|  CREATE TABLE inventory (                                              |
|      id              BIGSERIAL PRIMARY KEY,                           |
|      product_id      BIGINT REFERENCES products(id),                  |
|      warehouse_id    BIGINT REFERENCES warehouses(id),                |
|      quantity        INTEGER NOT NULL DEFAULT 0,                      |
|      reserved        INTEGER NOT NULL DEFAULT 0,                      |
|      version         INTEGER NOT NULL DEFAULT 1,                      |
|      updated_at      TIMESTAMP DEFAULT NOW(),                         |
|                                                                         |
|      UNIQUE(product_id, warehouse_id),                                |
|      CHECK(quantity >= reserved),                                     |
|      CHECK(reserved >= 0)                                             |
|  );                                                                    |
|                                                                         |
|  CREATE TABLE inventory_reservations (                                |
|      id              BIGSERIAL PRIMARY KEY,                           |
|      reservation_id  UUID NOT NULL,  -- Saga/order reference         |
|      product_id      BIGINT REFERENCES products(id),                  |
|      warehouse_id    BIGINT REFERENCES warehouses(id),                |
|      quantity        INTEGER NOT NULL,                                |
|      status          VARCHAR(20) DEFAULT 'ACTIVE',                    |
|                      -- ACTIVE, CONFIRMED, RELEASED, EXPIRED         |
|      created_at      TIMESTAMP DEFAULT NOW(),                         |
|      expires_at      TIMESTAMP NOT NULL,                              |
|      confirmed_at    TIMESTAMP,                                        |
|      released_at     TIMESTAMP                                        |
|  );                                                                    |
|                                                                         |
|  CREATE INDEX idx_inv_product_warehouse                               |
|      ON inventory(product_id, warehouse_id);                         |
|  CREATE INDEX idx_reservations_expiry                                 |
|      ON inventory_reservations(expires_at)                           |
|      WHERE status = 'ACTIVE';                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.3: INVENTORY OPERATIONS

### RESERVATION FLOW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RESERVE INVENTORY (During Checkout)                                  |
|                                                                         |
|  public ReservationResult reserve(                                    |
|      String reservationId,                                            |
|      List<OrderItem> items,                                           |
|      Duration ttl                                                      |
|  ) {                                                                   |
|      Instant expiresAt = Instant.now().plus(ttl);                    |
|                                                                         |
|      // Use database transaction                                      |
|      return transactionTemplate.execute(status -> {                  |
|                                                                         |
|          for (OrderItem item : items) {                              |
|              // Lock the inventory row                                |
|              Inventory inv = inventoryRepo.lockForUpdate(            |
|                  item.getProductId(),                                 |
|                  item.getWarehouseId()                                |
|              );                                                        |
|                                                                         |
|              // Check availability                                    |
|              int available = inv.getQuantity() - inv.getReserved();  |
|              if (available < item.getQuantity()) {                   |
|                  throw new InsufficientStockException(               |
|                      item.getProductId(), available);                |
|              }                                                         |
|                                                                         |
|              // Increment reserved count                              |
|              inv.setReserved(inv.getReserved() + item.getQuantity());|
|              inv.setVersion(inv.getVersion() + 1);                   |
|              inventoryRepo.save(inv);                                 |
|                                                                         |
|              // Create reservation record                            |
|              InventoryReservation reservation = new InventoryReservation(|
|                  reservationId,                                       |
|                  item.getProductId(),                                 |
|                  item.getWarehouseId(),                               |
|                  item.getQuantity(),                                  |
|                  expiresAt                                            |
|              );                                                        |
|              reservationRepo.save(reservation);                      |
|          }                                                             |
|                                                                         |
|          return ReservationResult.success(reservationId, expiresAt); |
|      });                                                               |
|  }                                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CONFIRM RESERVATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CONFIRM RESERVATION (After Payment Success)                          |
|                                                                         |
|  public void confirm(String reservationId) {                          |
|      transactionTemplate.execute(status -> {                         |
|          List<InventoryReservation> reservations =                   |
|              reservationRepo.findByReservationIdAndStatus(           |
|                  reservationId, "ACTIVE"                             |
|              );                                                        |
|                                                                         |
|          for (InventoryReservation res : reservations) {             |
|              // Lock inventory row                                    |
|              Inventory inv = inventoryRepo.lockForUpdate(            |
|                  res.getProductId(),                                  |
|                  res.getWarehouseId()                                 |
|              );                                                        |
|                                                                         |
|              // Move from reserved to sold                            |
|              inv.setQuantity(inv.getQuantity() - res.getQuantity()); |
|              inv.setReserved(inv.getReserved() - res.getQuantity()); |
|              inventoryRepo.save(inv);                                 |
|                                                                         |
|              // Update reservation status                            |
|              res.setStatus("CONFIRMED");                             |
|              res.setConfirmedAt(Instant.now());                      |
|              reservationRepo.save(res);                              |
|          }                                                             |
|          return null;                                                  |
|      });                                                               |
|  }                                                                     |
|                                                                         |
|  INVENTORY STATE TRANSITIONS:                                         |
|  --------------------------------                                       |
|                                                                         |
|  Initial:    quantity=100, reserved=0, available=100                 |
|  After reserve(10): quantity=100, reserved=10, available=90         |
|  After confirm(10): quantity=90, reserved=0, available=90           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### RELEASE RESERVATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RELEASE RESERVATION (On Cancel or Expiry)                            |
|                                                                         |
|  public void release(String reservationId) {                          |
|      transactionTemplate.execute(status -> {                         |
|          List<InventoryReservation> reservations =                   |
|              reservationRepo.findByReservationIdAndStatus(           |
|                  reservationId, "ACTIVE"                             |
|              );                                                        |
|                                                                         |
|          for (InventoryReservation res : reservations) {             |
|              Inventory inv = inventoryRepo.lockForUpdate(            |
|                  res.getProductId(),                                  |
|                  res.getWarehouseId()                                 |
|              );                                                        |
|                                                                         |
|              // Return reserved quantity to available                |
|              inv.setReserved(inv.getReserved() - res.getQuantity()); |
|              inventoryRepo.save(inv);                                 |
|                                                                         |
|              res.setStatus("RELEASED");                              |
|              res.setReleasedAt(Instant.now());                       |
|              reservationRepo.save(res);                              |
|          }                                                             |
|          return null;                                                  |
|      });                                                               |
|  }                                                                     |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  CLEANUP EXPIRED RESERVATIONS (Background Job)                        |
|                                                                         |
|  @Scheduled(fixedRate = 60000)  // Every minute                      |
|  public void cleanupExpired() {                                       |
|      List<InventoryReservation> expired =                            |
|          reservationRepo.findExpired(Instant.now());                 |
|                                                                         |
|      for (InventoryReservation res : expired) {                      |
|          try {                                                         |
|              release(res.getReservationId());                        |
|          } catch (Exception e) {                                      |
|              log.error("Failed to release {}", res.getId(), e);     |
|          }                                                             |
|      }                                                                 |
|  }                                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.4: FLASH SALE STRATEGIES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE FLASH SALE PROBLEM                                               |
|                                                                         |
|  Scenario: 100 iPhones on sale at 12:00 PM                           |
|  10,000 users waiting to buy at exactly 12:00 PM                     |
|                                                                         |
|  Problem:                                                              |
|  * 10,000 concurrent requests hit inventory service                  |
|  * All try to SELECT FOR UPDATE on same row                         |
|  * Database lock contention -> Timeouts -> Failed orders              |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  SOLUTION 1: REDIS ATOMIC COUNTERS                                    |
|  ===================================                                    |
|                                                                         |
|  Use Redis to handle the high-concurrency reservation.               |
|  Database is updated async/batch.                                    |
|                                                                         |
|  public boolean tryReserve(String productId, int quantity) {         |
|      String key = "inventory:" + productId;                          |
|                                                                         |
|      // Atomic decrement in Redis                                    |
|      Long remaining = redisTemplate.execute(                         |
|          DECR_IF_ENOUGH_SCRIPT,                                       |
|          List.of(key),                                                |
|          quantity                                                      |
|      );                                                                |
|                                                                         |
|      return remaining != null && remaining >= 0;                     |
|  }                                                                     |
|                                                                         |
|  Lua Script (DECR_IF_ENOUGH):                                        |
|  +----------------------------------------------------------------+   |
|  |  local current = tonumber(redis.call('GET', KEYS[1]) or 0)    |   |
|  |  local requested = tonumber(ARGV[1])                          |   |
|  |                                                                |   |
|  |  if current >= requested then                                 |   |
|  |      redis.call('DECRBY', KEYS[1], requested)                |   |
|  |      return current - requested                               |   |
|  |  else                                                          |   |
|  |      return -1  -- Not enough stock                          |   |
|  |  end                                                           |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
|  SYNC WITH DATABASE:                                                   |
|  * After Redis success, create reservation in DB (can be async)     |
|  * Background job syncs Redis ↔ DB                                  |
|  * On any discrepancy, DB is source of truth                        |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  SOLUTION 2: TOKEN BUCKET                                             |
|  =========================                                              |
|                                                                         |
|  Pre-create "purchase tokens" equal to inventory.                    |
|  Users acquire token before checkout.                                |
|                                                                         |
|  Setup:                                                                |
|  LPUSH flash:iphone14 token1 token2 ... token100  (100 tokens)      |
|                                                                         |
|  Acquire token:                                                        |
|  String token = redis.LPOP("flash:iphone14");                        |
|  if (token == null) {                                                 |
|      return "SOLD_OUT";                                               |
|  }                                                                     |
|  // User has 10 minutes to complete checkout with this token        |
|                                                                         |
|  Return token (on cancel/expiry):                                    |
|  redis.RPUSH("flash:iphone14", token);                               |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  SOLUTION 3: VIRTUAL QUEUE + BATCH PROCESSING                        |
|  =============================================                          |
|                                                                         |
|  Don't let everyone hit inventory at once.                           |
|                                                                         |
|  1. Users join queue (Redis sorted set with timestamp)               |
|  2. Batch processor picks 100 users at a time                        |
|  3. Process their orders sequentially                                |
|  4. Others wait in queue with position updates                       |
|                                                                         |
|  User experience:                                                      |
|  "You are #4,532 in queue. Estimated wait: 3 minutes"               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.5: MULTI-WAREHOUSE INVENTORY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WAREHOUSE SELECTION STRATEGY                                         |
|                                                                         |
|  When user orders an item available in multiple warehouses,          |
|  which warehouse should fulfill it?                                   |
|                                                                         |
|  STRATEGY 1: NEAREST WAREHOUSE                                        |
|  -------------------------------                                        |
|  Calculate distance from user's shipping address to each warehouse.  |
|  Pick the closest one with available stock.                          |
|                                                                         |
|  SELECT w.id, w.name, i.quantity - i.reserved as available,         |
|         ST_Distance(                                                   |
|           ST_Point(w.longitude, w.latitude),                         |
|           ST_Point(:user_lon, :user_lat)                             |
|         ) as distance                                                  |
|  FROM warehouses w                                                     |
|  JOIN inventory i ON w.id = i.warehouse_id                           |
|  WHERE i.product_id = :product_id                                    |
|    AND (i.quantity - i.reserved) >= :requested_qty                   |
|  ORDER BY distance ASC                                                |
|  LIMIT 1;                                                              |
|                                                                         |
|  STRATEGY 2: COST OPTIMIZATION                                        |
|  -------------------------------                                        |
|  Consider shipping cost, not just distance.                          |
|  Some routes may be cheaper despite longer distance.                 |
|                                                                         |
|  STRATEGY 3: INVENTORY BALANCING                                      |
|  ---------------------------------                                      |
|  Prefer warehouse with highest stock to balance inventory levels.   |
|                                                                         |
|  STRATEGY 4: SPLIT FULFILLMENT                                        |
|  --------------------------------                                       |
|  If no single warehouse has all items, split across warehouses.     |
|  Trade-off: Multiple shipments vs single shipment.                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.6: INVENTORY CONSISTENCY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KEEPING INVENTORY IN SYNC                                            |
|                                                                         |
|  SOURCES OF INVENTORY CHANGE:                                         |
|  * Orders (decrease)                                                  |
|  * Returns (increase)                                                 |
|  * Seller restocking (increase)                                       |
|  * Damaged goods (decrease)                                           |
|  * Warehouse transfers (move between locations)                      |
|                                                                         |
|  INVENTORY AUDIT TRAIL:                                               |
|  ------------------------                                               |
|                                                                         |
|  CREATE TABLE inventory_movements (                                   |
|      id              BIGSERIAL PRIMARY KEY,                           |
|      product_id      BIGINT NOT NULL,                                 |
|      warehouse_id    BIGINT NOT NULL,                                 |
|      movement_type   VARCHAR(20) NOT NULL,                            |
|                      -- ORDER, RETURN, RESTOCK, DAMAGE, TRANSFER     |
|      quantity        INTEGER NOT NULL,  -- positive or negative      |
|      reference_id    VARCHAR(100),      -- order_id, etc.            |
|      balance_before  INTEGER NOT NULL,                                |
|      balance_after   INTEGER NOT NULL,                                |
|      created_at      TIMESTAMP DEFAULT NOW(),                         |
|      created_by      VARCHAR(100)                                     |
|  );                                                                    |
|                                                                         |
|  RECONCILIATION:                                                       |
|  -----------------                                                      |
|  Daily job compares:                                                  |
|  * Sum of movements should equal current inventory                   |
|  * Redis cache should match database                                 |
|  * Alert on any discrepancy                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  INVENTORY MANAGEMENT - KEY TAKEAWAYS                                 |
|                                                                         |
|  DATA MODEL                                                            |
|  ----------                                                            |
|  * Separate quantity and reserved columns                            |
|  * available = quantity - reserved (computed)                        |
|  * Track inventory per product per warehouse                         |
|                                                                         |
|  RESERVATION PATTERN                                                   |
|  -------------------                                                   |
|  * Reserve on checkout initiation                                    |
|  * Confirm on payment success                                        |
|  * Release on cancel/timeout                                         |
|  * Background job cleans expired reservations                        |
|                                                                         |
|  FLASH SALES                                                           |
|  -----------                                                           |
|  * Redis atomic counters for high concurrency                        |
|  * Token bucket for fair allocation                                  |
|  * Virtual queue to control flow                                     |
|                                                                         |
|  MULTI-WAREHOUSE                                                       |
|  ---------------                                                       |
|  * Nearest warehouse selection                                       |
|  * Consider cost optimization                                        |
|  * Split fulfillment when needed                                     |
|                                                                         |
|  INTERVIEW TIP                                                         |
|  -------------                                                         |
|  Explain reservation flow clearly.                                   |
|  Discuss how to prevent overselling during flash sales.             |
|  Mention Redis for high-concurrency scenarios.                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 4

