# HOTEL / AIRLINE RESERVATION SYSTEM (BOOKING.COM STYLE)
*Complete Design: Requirements, Architecture, and Interview Guide*

A hotel reservation system allows users to search for hotels by location and dates,
view room availability, and book rooms with payment - all while preventing double-booking.
At scale, it must handle millions of concurrent searchers, thousands of simultaneous
bookings, and flash-sale traffic spikes with strong consistency for the booking path.

## SECTION 1: UNDERSTANDING THE PROBLEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS A HOTEL RESERVATION SYSTEM?                                    |
|                                                                         |
|  User Journey:                                                          |
|  1. Search: "Hotels in Paris, Dec 20-25, 2 guests"                      |
|  2. Browse results: filter by price, rating, amenities                  |
|  3. Select hotel, view room types and availability                      |
|  4. Choose room > system places temporary hold                          |
|  5. Enter payment details > system charges card                         |
|  6. Confirm booking > receive confirmation email/SMS                    |
|  7. (Optional) Cancel booking within cancellation window                |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  WHY IS THIS HARD?                                                      |
|                                                                         |
|  1. DOUBLE-BOOKING PREVENTION (THE core challenge)                      |
|     Two users try to book the last room simultaneously.                 |
|     Only one must succeed. Zero tolerance for overbooking hotels.       |
|     (Airlines intentionally overbook ~15%; hotels generally don't.)     |
|                                                                         |
|  2. SEARCH vs BOOKING MISMATCH                                          |
|     Search is read-heavy: 100:1 search-to-book ratio.                   |
|     Booking is write-heavy with strong consistency needs.               |
|     Different patterns need different optimization strategies.          |
|                                                                         |
|  3. FLASH SALE / SURGE TRAFFIC                                          |
|     A luxury hotel posts a 90% discount > 100K users try to book.       |
|     System must handle spike without downtime or data corruption.       |
|                                                                         |
|  4. DISTRIBUTED TRANSACTIONS                                            |
|     A booking spans: inventory check, payment, confirmation, email.     |
|     If payment fails after inventory reserved, must roll back.          |
|     Saga pattern needed for distributed coordination.                   |
|                                                                         |
|  5. INVENTORY IS DATE-BASED                                             |
|     Room availability changes per date. Booking Dec 20-25 must          |
|     check and reserve inventory for EACH of the 5 nights.               |
|     Partial availability (3 of 5 nights) = no booking.                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2: REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FUNCTIONAL REQUIREMENTS:                                               |
|                                                                         |
|  1. HOTEL SEARCH                                                        |
|     * Search by location, check-in/check-out dates, number of guests    |
|     * Filter by price range, star rating, amenities, review score       |
|     * Sort by price, rating, distance, relevance                        |
|     * View hotel details: photos, descriptions, policies                |
|                                                                         |
|  2. ROOM AVAILABILITY                                                   |
|     * Check real-time room availability for a date range                |
|     * Show room types: single, double, suite, etc.                      |
|     * Display pricing per night (dynamic pricing)                       |
|     * Show cancellation policy per room type                            |
|                                                                         |
|  3. BOOKING                                                             |
|     * Reserve a room with guest details                                 |
|     * Process payment (credit card, etc.)                               |
|     * Generate booking confirmation with unique ID                      |
|     * Send confirmation via email and SMS                               |
|                                                                         |
|  4. CANCELLATION                                                        |
|     * Cancel booking within policy window                               |
|     * Full/partial refund based on cancellation policy                  |
|     * Release inventory back to available pool                          |
|     * Notify hotel of cancellation                                      |
|                                                                         |
|  5. HOTEL MANAGEMENT (Admin)                                            |
|     * Hotels manage room inventory and pricing                          |
|     * Set availability, blackout dates                                  |
|     * View bookings and revenue reports                                 |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  NON-FUNCTIONAL REQUIREMENTS:                                           |
|                                                                         |
|  * Strong consistency for bookings (no double-booking)                  |
|  * High availability for search (eventual consistency OK)               |
|  * Search latency: < 500ms p99                                          |
|  * Booking latency: < 2 seconds end-to-end                              |
|  * Handle 10K+ concurrent bookings/sec during flash sales               |
|  * 99.99% availability for search, 99.9% for booking                    |
|  * Support 500K+ hotels, 10M+ rooms globally                            |
|  * Idempotent booking API (retry-safe)                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3: BACK-OF-ENVELOPE ESTIMATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCALE ESTIMATES:                                                       |
|                                                                         |
|  Hotels: 500,000 hotels on the platform                                 |
|  Rooms per hotel: ~20 avg > 10,000,000 rooms total                      |
|  Room types per hotel: ~5 avg                                           |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  SEARCH TRAFFIC:                                                        |
|                                                                         |
|  DAU: 5M users searching                                                |
|  Searches per user per session: ~10                                     |
|  Total searches/day: 50M                                                |
|  Search QPS: 50M / 86,400 ~ ~580 QPS average                            |
|  Peak QPS (3x): ~1,800 QPS                                              |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  BOOKING TRAFFIC:                                                       |
|                                                                         |
|  Conversion rate: ~2% of searchers book                                 |
|  Bookings/day: 5M * 0.02 = 100,000 bookings/day                         |
|  Booking QPS: 100K / 86,400 ~ ~1.2 QPS average                          |
|  Peak (flash sale): 100x > ~120 QPS                                     |
|  100:1 read-to-write ratio for search vs booking                        |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  STORAGE:                                                               |
|                                                                         |
|  Hotel data: 500K * 10KB = ~5 GB (easily fits in memory/cache)          |
|  Room inventory: 10M rooms * 365 days * 50B = ~180 GB/year              |
|  Bookings: 100K/day * 1KB * 365 = ~36 GB/year                           |
|  Total active data: ~250 GB (manageable on single DB + replicas)        |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  KEY INSIGHT:                                                           |
|  The data volume is not extreme. The challenge is CONCURRENCY           |
|  and CONSISTENCY, not raw storage or throughput. A well-sharded         |
|  PostgreSQL cluster can handle the booking write volume.                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4: HIGH-LEVEL ARCHITECTURE

```
+--------------------------------------------------------------------------+
|                                                                          |
|  HOTEL RESERVATION ARCHITECTURE                                          |
|                                                                          |
|  +--------+    +-----------+                                             |
|  | Mobile  | -> | API       |                                            |
|  | Web App |    | Gateway   |                                            |
|  +--------+    | (Auth,    |                                             |
|                | Rate Limit|                                             |
|                +-----+-----+                                             |
|                      |                                                   |
|        +-------------+------------------+------------------+             |
|        |             |                  |                  |             |
|        v             v                  v                  v             |
|  +-----------+ +-----------+   +-------------+   +-----------+           |
|  | Search    | | Hotel     |   | Availability|   | Booking   |           |
|  | Service   | | Service   |   | Service     |   | Service   |           |
|  | (ES +     | | (details, |   | (inventory, |   | (reserve, |           |
|  |  geo)     | |  photos,  |   |  check,     |   |  confirm, |           |
|  |           | |  reviews) |   |  hold)      |   |  cancel)  |           |
|  +-----+-----+ +-----+-----+   +------+------+   +-----+-----+           |
|        |             |                |                  |               |
|        v             v                v                  v               |
|  +-----------+ +-----------+   +-------------+   +-----------+           |
|  | Elastic-  | | Hotel DB  |   | Inventory   |   | Booking   |           |
|  | search    | | (Postgres)|   | DB          |   | DB        |           |
|  | Cluster   | +-----------+   | (Postgres)  |   | (Postgres)|           |
|  +-----------+                 +-------------+   +-----------+           |
|                                                        |                 |
|                                        +---------------+-------+         |
|                                        |               |       |         |
|                                        v               v       v         |
|                                  +-----------+  +--------+ +---------+   |
|                                  | Payment   |  | Notif. | | Hotel   |   |
|                                  | Service   |  | Service| | Mgmt    |   |
|                                  | (Stripe)  |  | (email,| | Service |   |
|                                  +-----------+  |  SMS)  | +---------+   |
|                                                 +--------+               |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 5: HOTEL SEARCH - GEO + FULL-TEXT + RANKING

```
+--------------------------------------------------------------------------+
|                                                                          |
|  GEO-BASED SEARCH:                                                       |
|                                                                          |
|  User searches: "Hotels near Times Square, NYC"                          |
|  We need: all hotels within N km of a point / within a bounding box      |
|                                                                          |
|  OPTION 1: GEOHASH                                                       |
|  * Encode (lat, lng) into a string: "dr5ru7" (precision level)           |
|  * Nearby locations share a common geohash prefix                        |
|  * Query: WHERE geohash LIKE 'dr5ru%'                                    |
|  * Fast prefix-based index lookup                                        |
|  * Edge case: neighbors at geohash boundary may not share prefix         |
|    > query current cell + 8 neighboring cells                            |
|                                                                          |
|  +------+------+------+                                                  |
|  | dr5rt| dr5ru| dr5rv|                                                  |
|  +------+------+------+                                                  |
|  | dr5rq| dr5rr| dr5rs|  < user is in dr5rr                              |
|  +------+------+------+    query dr5rr + all 8 neighbors                 |
|  | dr5rm| dr5rn| dr5rp|                                                  |
|  +------+------+------+                                                  |
|                                                                          |
|  OPTION 2: QUADTREE                                                      |
|  * Recursively divide map into 4 quadrants                               |
|  * Split until each cell has < N hotels                                  |
|  * Dense areas (NYC) have deeper tree, sparse areas are coarse           |
|  * Good for in-memory spatial index                                      |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  ELASTICSEARCH FOR FULL-TEXT + FILTERS:                                  |
|                                                                          |
|  Hotel document indexed in Elasticsearch:                                |
|  {                                                                       |
|    "hotel_id": "h_12345",                                                |
|    "name": "Grand Hyatt NYC",                                            |
|    "location": { "lat": 40.7549, "lon": -73.9764 },                      |
|    "city": "New York",                                                   |
|    "star_rating": 4,                                                     |
|    "amenities": ["pool", "wifi", "gym", "spa"],                          |
|    "avg_review_score": 8.7,                                              |
|    "price_range": { "min": 250, "max": 800 },                            |
|    "room_types": ["single", "double", "suite"]                           |
|  }                                                                       |
|                                                                          |
|  ES query combines:                                                      |
|  * geo_distance filter (within 5km of point)                             |
|  * range filter (price, star rating)                                     |
|  * term filter (amenities, room type)                                    |
|  * full-text match (hotel name, description)                             |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  SEARCH RANKING:                                                         |
|                                                                          |
|  +-------------------+------+-----------------------------------------+  |
|  | Factor            |Weight| Notes                                   |  |
|  +-------------------+------+-----------------------------------------+  |
|  | Price match       | 25%  | Closer to user's budget = higher        |  |
|  | Review score      | 20%  | Average guest rating                    |  |
|  | Distance          | 15%  | Proximity to searched location          |  |
|  | Relevance         | 15%  | Text match on name/description          |  |
|  | Promoted/Ads      | 10%  | Hotels paying for placement             |  |
|  | Conversion rate   | 10%  | Historical booking rate for listing     |  |
|  | Recency           | 5%   | Recently updated listings               |  |
|  +-------------------+------+-----------------------------------------+  |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  CACHING SEARCH RESULTS:                                                 |
|                                                                          |
|  +----------+    +-----------+    +---------------+                      |
|  | Search   | -> | Redis     | -> | Elasticsearch |                      |
|  | Request  |    | Cache     |    | (cache miss)  |                      |
|  +----------+    | TTL: 60s  |    +---------------+                      |
|                  +-----------+                                           |
|                                                                          |
|  WHY REDIS CACHE: Same search (city + dates) repeated by thousands       |
|  of users. 60s TTL avoids hitting ES for every request. Sub-ms reads.    |
|  WHY ELASTICSEARCH: Full-text (hotel names) + geo (location radius)      |
|  + facets (price range, amenities, rating) in one query. Combined        |
|  text+geo+filter queries impossible at scale with SQL alone.             |
|                                                                          |
|  Cache key: hash(location, dates, filters, sort, page)                   |
|  TTL: 60 seconds (availability can change, but search results are        |
|        approximate - real availability checked at booking time)          |
|                                                                          |
|  Pagination: use search_after (cursor-based) instead of offset           |
|  for consistent deep pagination results.                                 |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 6: AVAILABILITY SYSTEM - THE HARD PART

```
+--------------------------------------------------------------------------+
|                                                                          |
|  THIS IS THE CORE INTERVIEW DISCUSSION TOPIC.                            |
|                                                                          |
|  ROOM INVENTORY MODEL:                                                   |
|                                                                          |
|  Table: room_inventory                                                   |
|  +----------+-----------+--------+--------+---------+                    |
|  | hotel_id | room_type | date   | total  | booked  |                    |
|  +----------+-----------+--------+--------+---------+                    |
|  | h_123    | double    | Dec 20 | 50     | 48      |                    |
|  | h_123    | double    | Dec 21 | 50     | 49      |                    |
|  | h_123    | double    | Dec 22 | 50     | 50      |  < SOLD OUT        |
|  | h_123    | double    | Dec 23 | 50     | 47      |                    |
|  | h_123    | double    | Dec 24 | 50     | 45      |                    |
|  | h_123    | suite     | Dec 20 | 10     | 10      |  < SOLD OUT        |
|  +----------+-----------+--------+--------+---------+                    |
|                                                                          |
|  Available rooms = total - booked                                        |
|  Check availability for Dec 20-24:                                       |
|    MIN(total - booked) for all dates in range                            |
|    If MIN = 0 > at least one night sold out > not bookable               |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  APPROACH 1: PESSIMISTIC LOCKING (SELECT ... FOR UPDATE)                 |
|                                                                          |
|  BEGIN TRANSACTION;                                                      |
|    SELECT booked, total FROM room_inventory                              |
|    WHERE hotel_id = 'h_123'                                              |
|      AND room_type = 'double'                                            |
|      AND date BETWEEN '2024-12-20' AND '2024-12-24'                      |
|    FOR UPDATE;  -- LOCKS these rows                                      |
|                                                                          |
|    -- Check: all dates have (total - booked) >= 1                        |
|    -- If yes:                                                            |
|    UPDATE room_inventory SET booked = booked + 1                         |
|    WHERE hotel_id = 'h_123'                                              |
|      AND room_type = 'double'                                            |
|      AND date BETWEEN '2024-12-20' AND '2024-12-24';                     |
|  COMMIT;                                                                 |
|                                                                          |
|  Pros: simple, guaranteed correctness                                    |
|  Cons: locks held for entire transaction duration                        |
|        high contention on popular hotels > slow                          |
|        deadlock risk if lock ordering is inconsistent                    |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  APPROACH 2: OPTIMISTIC LOCKING (version column)                         |
|                                                                          |
|  Table adds: version INT                                                 |
|                                                                          |
|  Step 1: Read (no lock)                                                  |
|    SELECT booked, total, version FROM room_inventory                     |
|    WHERE hotel_id = 'h_123'                                              |
|      AND room_type = 'double'                                            |
|      AND date = '2024-12-20';                                            |
|    -- booked=48, total=50, version=5                                     |
|                                                                          |
|  Step 2: Update with version check                                       |
|    UPDATE room_inventory                                                 |
|    SET booked = 49, version = 6                                          |
|    WHERE hotel_id = 'h_123'                                              |
|      AND room_type = 'double'                                            |
|      AND date = '2024-12-20'                                             |
|      AND version = 5;                                                    |
|    -- Rows affected = 1? Success!                                        |
|    -- Rows affected = 0? Someone else updated > RETRY                    |
|                                                                          |
|  Pros: no locks held, higher throughput under moderate contention        |
|  Cons: retry storms under high contention (flash sale)                   |
|        must retry ALL dates if ANY date conflicts                        |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  APPROACH 3: ATOMIC CONDITIONAL UPDATE (best for this use case)          |
|                                                                          |
|  UPDATE room_inventory                                                   |
|  SET booked = booked + 1                                                 |
|  WHERE hotel_id = 'h_123'                                                |
|    AND room_type = 'double'                                              |
|    AND date BETWEEN '2024-12-20' AND '2024-12-24'                        |
|    AND booked < total;                                                   |
|                                                                          |
|  -- If rows_updated = 5 (all 5 nights) > success!                        |
|  -- If rows_updated < 5 > at least one night full > ROLLBACK             |
|                                                                          |
|  Pros: single atomic SQL, no application-level retry logic               |
|  Cons: need to rollback partial updates if not all dates succeed         |
|        wrap in transaction to make it all-or-nothing                     |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  APPROACH 4: REDIS ATOMIC DECREMENT                                      |
|                                                                          |
|  Key: availability:{hotel_id}:{room_type}:{date}                         |
|  Value: remaining room count                                             |
|                                                                          |
|  MULTI                                                                   |
|    DECR availability:h_123:double:2024-12-20                             |
|    DECR availability:h_123:double:2024-12-21                             |
|    DECR availability:h_123:double:2024-12-22                             |
|    DECR availability:h_123:double:2024-12-23                             |
|    DECR availability:h_123:double:2024-12-24                             |
|  EXEC                                                                    |
|                                                                          |
|  Check results: if any value < 0, INCR them all back (rollback)          |
|                                                                          |
|  Pros: extremely fast (in-memory), high throughput                       |
|  Cons: Redis is not durable by default - must sync to DB                 |
|        two-source-of-truth risk (Redis vs DB)                            |
|        best used as a fast-path with DB as source of truth               |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  OVERBOOKING STRATEGY (airlines vs hotels):                              |
|                                                                          |
|  Airlines: intentionally overbook by ~15%                                |
|    * Historical no-show rate: 10-15%                                     |
|    * total = 200 seats, sell 230 tickets                                 |
|    * If everyone shows up > offer compensation + rebooking               |
|    * Revenue optimization: empty seats = lost revenue                    |
|                                                                          |
|  Hotels: generally do NOT overbook                                       |
|    * Guest expectation is guaranteed room                                |
|    * "Walking" a guest (sending to another hotel) is expensive           |
|    * Some hotels overbook by 5% for no-shows + cancellations             |
|    * Overbooking threshold = historical (no_show + late_cancel) rate     |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 7: BOOKING FLOW - HOLD > PAY > CONFIRM

```
+--------------------------------------------------------------------------+
|                                                                          |
|  BOOKING STATE MACHINE:                                                  |
|                                                                          |
|  +----------+    +---------+    +-----------+    +-----------+           |
|  | AVAILABLE| -> | HELD    | -> | PAYMENT   | -> | CONFIRMED |           |
|  |          |    | (temp,  |    | PROCESSING|    |           |           |
|  +----------+    | 10 min  |    +-----------+    +-----------+           |
|       ^          | TTL)    |         |                 |                 |
|       |          +----+----+         |                 v                 |
|       |               |              |           +-----------+           |
|       |               v              v           | CANCELLED |           |
|       |          +---------+    +---------+      +-----------+           |
|       +--------- | EXPIRED |    | PAYMENT |                              |
|       (release)  | (TTL    |    | FAILED  |                              |
|                  |  hit)   |    +---------+                              |
|                  +---------+         |                                   |
|                                      v                                   |
|                                 (release inventory)                      |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  DETAILED FLOW:                                                          |
|                                                                          |
|  Step 1: User selects room                                               |
|  +--------+                    +------------------+                      |
|  | User   | -- POST /hold --> | Availability     |                       |
|  | clicks |    {hotel, room,  | Service          |                       |
|  | "Book" |     dates,        | - Check avail    |                       |
|  +--------+     idempotency_  | - Decrement      |                       |
|                 key}          |   inventory       |                      |
|                               | - Create hold     |                      |
|                               |   with TTL=10min  |                      |
|                               +------------------+                       |
|                                                                          |
|  Step 2: User enters payment details (within 10 min hold)                |
|  +--------+                    +------------------+                      |
|  | User   | -- POST /book --> | Booking Service  |                       |
|  | submits|    {hold_id,      | - Verify hold    |                       |
|  | payment|     payment_info, |   still active   |                       |
|  +--------+     idempotency_  | - Call Payment   |                       |
|                 key}          |   Service         |                      |
|                               +--------+---------+                       |
|                                        |                                 |
|  Step 3: Payment processing             |                                |
|                                        v                                 |
|                               +------------------+                       |
|                               | Payment Service  |                       |
|                               | - Charge card    |                       |
|                               | - Return success |                       |
|                               |   or failure     |                       |
|                               +--------+---------+                       |
|                                        |                                 |
|  Step 4: Confirm or rollback           |                                 |
|                                        v                                 |
|                               +------------------+                       |
|                               | If payment OK:   |                       |
|                               | - Mark CONFIRMED |                       |
|                               | - Persist booking|                       |
|                               | - Send confirm   |                       |
|                               |   notification   |                       |
|                               |                  |                       |
|                               | If payment FAIL: |                       |
|                               | - Release hold   |                       |
|                               | - Restore avail  |                       |
|                               | - Notify user    |                       |
|                               +------------------+                       |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  IDEMPOTENCY KEY:                                                        |
|                                                                          |
|  Every booking request carries a client-generated idempotency_key.       |
|                                                                          |
|  +----------+    +------------------+    +-----------+                   |
|  | Request  | -> | Check:           | -> | Key exists|                   |
|  | with key |    | idempotency_keys |    | in DB?    |                   |
|  | "abc-123"|    | table            |    +-----+-----+                   |
|  +----------+    +------------------+          |                         |
|                                          +-----+-----+                   |
|                                          |           |                   |
|                                         YES          NO                  |
|                                          |           |                   |
|                                          v           v                   |
|                                   +-----------+ +-----------+            |
|                                   | Return    | | Process   |            |
|                                   | previous  | | booking,  |            |
|                                   | result    | | store key |            |
|                                   +-----------+ | + result  |            |
|                                                 +-----------+            |
|                                                                          |
|  Prevents double-booking on network retries or user double-click.        |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  SAGA PATTERN FOR DISTRIBUTED TRANSACTION:                               |
|                                                                          |
|  A booking is NOT a single DB transaction. It spans services:            |
|                                                                          |
|  FORWARD FLOW (happy path):                                              |
|  +------------------+    +------------------+    +-------------------+   |
|  | 1. Reserve       | -> | 2. Charge        | -> | 3. Confirm         |  |
|  |    Inventory     |    |    Payment       |    |    Booking         |  |
|  | (availability    |    | (payment service)|    | (booking service)  |  |
|  |  service)        |    |                  |    | + notification     |  |
|  +------------------+    +------------------+    +-------------------+   |
|                                                                          |
|  COMPENSATION (on failure at any step):                                  |
|  +------------------+    +------------------+    +-------------------+   |
|  | 3. FAIL?         | -> | Refund Payment   | -> | Release            |  |
|  | Booking can't    |    | (reverse charge) |    | Inventory          |  |
|  | be created       |    |                  |    | (increment back)   |  |
|  +------------------+    +------------------+    +-------------------+   |
|                                                                          |
|  Orchestrator-based saga: a central BookingSaga service                  |
|  coordinates the steps and triggers compensations on failure.            |
|                                                                          |
|  Each step is idempotent (can be retried safely).                        |
|  Each step has a corresponding compensation action.                      |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 8: CONCURRENCY & DOUBLE-BOOKING PREVENTION

```
+--------------------------------------------------------------------------+
|                                                                          |
|  THE RACE CONDITION:                                                     |
|                                                                          |
|  Last room available for Dec 20. Two users book simultaneously:          |
|                                                                          |
|  Time    User A                    User B                                |
|  ----    ------                    ------                                |
|  T1      Read: booked=49, total=50                                       |
|  T2                                Read: booked=49, total=50             |
|  T3      49 < 50? Yes > book!                                            |
|  T4                                49 < 50? Yes > book!                  |
|  T5      UPDATE SET booked=50      UPDATE SET booked=50                  |
|  T6      Y Confirmed              Y Confirmed  < DOUBLE BOOKED!          |
|                                                                          |
|  Both users see availability, both succeed > OVERBOOKING.                |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  SOLUTION 1: PESSIMISTIC LOCKING (SELECT FOR UPDATE)                     |
|                                                                          |
|  Time    User A                    User B                                |
|  ----    ------                    ------                                |
|  T1      SELECT ... FOR UPDATE                                           |
|          (acquires row lock)                                             |
|  T2                                SELECT ... FOR UPDATE                 |
|                                    (BLOCKED - waiting for lock)          |
|  T3      booked=49 < 50 > UPDATE                                         |
|  T4      COMMIT (releases lock)                                          |
|  T5                                (lock acquired)                       |
|  T6                                booked=50, total=50                   |
|  T7                                50 < 50? NO > REJECT                  |
|                                                                          |
|  Y Correct. Only User A books.                                           |
|  X Low throughput: requests serialize on the lock.                       |
|  X Lock held during entire transaction (including payment?).             |
|                                                                          |
|  BEST FOR: low-to-moderate concurrency, simple implementation.           |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  SOLUTION 2: OPTIMISTIC CONCURRENCY CONTROL                              |
|                                                                          |
|  Time    User A                    User B                                |
|  ----    ------                    ------                                |
|  T1      Read: booked=49, ver=5                                          |
|  T2                                Read: booked=49, ver=5                |
|  T3      UPDATE ... WHERE ver=5                                          |
|          (1 row affected > success)                                      |
|  T4                                UPDATE ... WHERE ver=5                |
|                                    (0 rows > CONFLICT > retry)           |
|  T5                                Re-read: booked=50, ver=6             |
|  T6                                50 < 50? NO > REJECT                  |
|                                                                          |
|  Y No locks held during read/compute phase.                              |
|  Y Higher throughput under low-to-moderate contention.                   |
|  X Retry storms under HIGH contention (flash sale: 1000 users,           |
|    1 room > 999 retries > all fail again > cascading retries).           |
|                                                                          |
|  BEST FOR: moderate concurrency, most hotel booking scenarios.           |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  SOLUTION 3: DISTRIBUTED LOCK (Redis SETNX)                              |
|                                                                          |
|  +----------+    +-------------------+    +------------------+           |
|  | User A   | -> | SETNX lock:       | -> | Lock acquired?   |           |
|  | requests |    | h_123:double:     |    | YES > proceed    |           |
|  | booking  |    | 2024-12-20        |    | NO > wait/reject |           |
|  +----------+    | EX 30             |    +------------------+           |
|                  +-------------------+                                   |
|                                                                          |
|  Only one request at a time can hold the lock for a given                |
|  (hotel, room_type, date) combination.                                   |
|                                                                          |
|  Y Fast (Redis in-memory).                                               |
|  Y Works across multiple application servers.                            |
|  X Need to handle lock expiry carefully (what if holder crashes?).       |
|  X Fencing tokens needed to prevent stale lock holders from writing.     |
|                                                                          |
|  BEST FOR: distributed systems where DB-level locking is insufficient.   |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  SOLUTION 4: QUEUE SERIALIZATION                                         |
|                                                                          |
|  +----------+    +----------+    +----------+    +----------+            |
|  | Booking  | -> | Kafka /  | -> | Single   | -> | DB       |            |
|  | Requests |    | SQS      |    | Consumer |    | Write    |            |
|  | (all)    |    | Queue    |    | per hotel|    |          |            |
|  +----------+    | partition|    +----------+    +----------+            |
|                  | by hotel |                                            |
|                  +----------+                                            |
|                                                                          |
|  All booking requests for a hotel go to the same partition.              |
|  Single consumer processes them sequentially - no race condition.        |
|                                                                          |
|  Y Zero race conditions by design.                                       |
|  Y Natural backpressure handling.                                        |
|  X Higher latency (queued, not immediate).                               |
|  X Single consumer per hotel = throughput bottleneck.                    |
|                                                                          |
|  BEST FOR: extreme contention scenarios (flash sales).                   |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  COMPARISON SUMMARY:                                                     |
|                                                                          |
|  +------------------+-------------+-----------+----------+------------+  |
|  | Approach         | Correctness | Throughput| Latency  | Complexity |  |
|  +------------------+-------------+-----------+----------+------------+  |
|  | Pessimistic Lock | Y Strong   | Low       | Medium   | Low         |  |
|  | Optimistic Lock  | Y Strong   | Medium    | Low*     | Medium      |  |
|  | Redis Dist Lock  | Y Strong   | High      | Low      | High        |  |
|  | Queue Serial     | Y Strong   | Medium    | High     | Medium      |  |
|  +------------------+-------------+-----------+----------+------------+  |
|  * Low latency when no contention; degrades under retries                |
|                                                                          |
|  RECOMMENDED: Optimistic locking for normal flow +                       |
|  queue serialization as fallback for flash-sale scenarios.               |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 9: CANCELLATION FLOW

```
+--------------------------------------------------------------------------+
|                                                                          |
|  CANCELLATION STATE MACHINE:                                             |
|                                                                          |
|  +-----------+    +-------------------+    +-----------+                 |
|  | CONFIRMED | -> | CANCELLATION      | -> | CANCELLED |                 |
|  |           |    | PROCESSING        |    |           |                 |
|  +-----------+    | - check policy    |    +-----------+                 |
|                   | - calculate refund|                                  |
|                   | - release rooms   |                                  |
|                   +-------------------+                                  |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  CANCELLATION POLICIES:                                                  |
|                                                                          |
|  +----------------------------+-------------------------------------+    |
|  | Policy                     | Refund                              |    |
|  +----------------------------+-------------------------------------+    |
|  | Free cancellation          | Full refund if cancelled > 24h      |    |
|  | (most common)              | before check-in                     |    |
|  +----------------------------+-------------------------------------+    |
|  | Moderate                   | Full refund > 5 days before         |    |
|  |                            | 50% refund 1-5 days before          |    |
|  |                            | No refund < 24 hours                |    |
|  +----------------------------+-------------------------------------+    |
|  | Non-refundable             | No refund at any time               |    |
|  | (discounted rate)          | (cheaper price as trade-off)        |    |
|  +----------------------------+-------------------------------------+    |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  REFUND + INVENTORY RELEASE FLOW:                                        |
|                                                                          |
|  +------------------+                                                    |
|  | User requests    |                                                    |
|  | cancellation     |                                                    |
|  +--------+---------+                                                    |
|           |                                                              |
|           v                                                              |
|  +------------------+                                                    |
|  | Booking Service  |                                                    |
|  | 1. Validate      |                                                    |
|  |    booking exists|                                                    |
|  | 2. Check cancel  |                                                    |
|  |    policy + time |                                                    |
|  | 3. Calculate     |                                                    |
|  |    refund amount |                                                    |
|  +--------+---------+                                                    |
|           |                                                              |
|     +-----+-----+                                                        |
|     |           |                                                        |
|     v           v                                                        |
|  +----------+  +------------------+                                      |
|  | Payment  |  | Availability     |                                      |
|  | Service  |  | Service          |                                      |
|  | - refund |  | - increment      |                                      |
|  |   card   |  |   booked count   |                                      |
|  +----------+  |   (release rooms)|                                      |
|                +------------------+                                      |
|     |           |                                                        |
|     v           v                                                        |
|  +------------------+                                                    |
|  | Notification     |                                                    |
|  | - Confirm cancel |                                                    |
|  |   to user        |                                                    |
|  | - Notify hotel   |                                                    |
|  +------------------+                                                    |
|                                                                          |
|  COMPENSATION SAGA FOR CANCELLATION:                                     |
|                                                                          |
|  Step 1: Mark booking as CANCELLING (prevent double-cancel)              |
|  Step 2: Process refund via Payment Service                              |
|  Step 3: Release inventory via Availability Service                      |
|  Step 4: Mark booking as CANCELLED                                       |
|  Step 5: Send notifications                                              |
|                                                                          |
|  If refund fails > retry with exponential backoff.                       |
|  If inventory release fails > retry (idempotent: decrementing            |
|  booked count for an already-released booking is a no-op).               |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 10: SCALING

```
+--------------------------------------------------------------------------+
|                                                                          |
|  SCALING BY ACCESS PATTERN:                                              |
|                                                                          |
|  SEARCH (read-heavy, 100x more than booking):                            |
|  -------------------------------------------------------------------     |
|                                                                          |
|  +------------------+    +-------------------+                           |
|  | Elasticsearch    |    | Redis Cache       |                           |
|  | Cluster          |    | - search results  |                           |
|  | - 3+ data nodes  |    | - hotel details   |                           |
|  | - read replicas  |    | - TTL: 60s        |                           |
|  | - shard per      |    +-------------------+                           |
|  |   region/city    |                                                    |
|  +------------------+                                                    |
|                                                                          |
|  Strategy:                                                               |
|  * Elasticsearch sharded by geography (city/region)                      |
|  * Read replicas: scale reads independently                              |
|  * Redis caches hot search queries + hotel detail pages                  |
|  * CDN for hotel images/static content                                   |
|  * Eventual consistency OK: availability shown in search is              |
|    approximate - real check happens at booking time                      |
|                                                                          |
|  BOOKING (write-heavy, strong consistency required):                     |
|  -------------------------------------------------------------------     |
|                                                                          |
|  +------------------+    +-------------------+                           |
|  | Booking DB       |    | Inventory DB      |                           |
|  | (PostgreSQL)     |    | (PostgreSQL)      |                           |
|  | - shard by       |    | - shard by        |                           |
|  |   hotel_id       |    |   hotel_id        |                           |
|  | - 2 replicas     |    | - same shard key  |                           |
|  |   per shard      |    |   as booking DB   |                           |
|  +------------------+    +-------------------+                           |
|                                                                          |
|  Strategy:                                                               |
|  * Shard by hotel_id: all data for one hotel on one shard                |
|  * Booking + inventory for same hotel on same shard                      |
|    > enables single-shard transactions (no distributed txn)              |
|  * Replicas for read queries (booking history, reports)                  |
|  * Connection pooling (PgBouncer) to handle connection spikes            |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  EVENT-DRIVEN ARCHITECTURE:                                              |
|                                                                          |
|  +------------------+                                                    |
|  | Booking Service  |                                                    |
|  | emits events:    |                                                    |
|  | - BookingCreated |                                                    |
|  | - BookingCancel  |                                                    |
|  +--------+---------+                                                    |
|           |                                                              |
|           v                                                              |
|  +------------------+                                                    |
|  | Event Bus        |                                                    |
|  | (Kafka)          |                                                    |
|  +--+------+------+-+                                                    |
|     |      |      |                                                      |
|     v      v      v                                                      |
|  +------+ +------+ +------+                                              |
|  |Notif | |Search| |Analyt|                                              |
|  |Svc   | |Index | |ics   |                                              |
|  |(email| |Update| |(rev  |                                              |
|  | SMS) | |(ES)  | |report|                                              |
|  +------+ +------+ |s)   |                                               |
|                     +------+                                             |
|                                                                          |
|  Benefits:                                                               |
|  * Services are decoupled: booking doesn't wait for email                |
|  * ES index updated asynchronously (eventual consistency OK)             |
|  * Analytics and reporting consume same event stream                     |
|  * Easy to add new consumers without changing booking service            |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  MULTI-REGION DEPLOYMENT:                                                |
|                                                                          |
|  +------------------+           +------------------+                     |
|  | US Region        |           | EU Region        |                     |
|  | - Search (local  |           | - Search (local  |                     |
|  |   ES + cache)    |           |   ES + cache)    |                     |
|  | - Read replicas  |           | - Read replicas  |                     |
|  +--------+---------+           +--------+---------+                     |
|           |                              |                               |
|           +----------+  +----------------+                               |
|                      |  |                                                |
|                      v  v                                                |
|               +------------------+                                       |
|               | Central Region   |                                       |
|               | - Booking writes |                                       |
|               | - Inventory DB   |                                       |
|               |   (source of     |                                       |
|               |    truth)        |                                       |
|               +------------------+                                       |
|                                                                          |
|  Search: fully regional for low latency (replicated ES + cache).         |
|  Booking: centralized for strong consistency.                            |
|  Trade-off: booking latency is higher for non-central regions            |
|  (~100-200ms cross-region), but correctness is guaranteed.               |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 11: INTERVIEW Q&A

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q1: How do you prevent double-booking the last room?                   |
|  -------------------------------------------------------------------    |
|  A: Use optimistic concurrency control with a version column.           |
|  Both users read booked=49, version=5. User A's UPDATE succeeds         |
|  (version matches), incrementing to version=6. User B's UPDATE          |
|  finds version=6 (not 5), gets 0 rows affected, and retries.            |
|  On retry, User B sees booked=50=total and is rejected gracefully.      |
|  For flash sales, fall back to queue serialization to avoid retry       |
|  storms.                                                                |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q2: Why not use a distributed lock for every booking?                  |
|  -------------------------------------------------------------------    |
|  A: Distributed locks (Redis SETNX) add complexity: lock expiry,        |
|  fencing tokens, clock skew, and an external dependency. For most       |
|  hotel bookings, contention is low (many room types, many dates),       |
|  so optimistic locking with DB-level version checks is simpler and      |
|  sufficient. Reserve distributed locks for extreme contention           |
|  scenarios where DB-level retries become expensive.                     |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q3: What if payment succeeds but the confirmation write fails?         |
|  -------------------------------------------------------------------    |
|  A: The saga pattern handles this. The BookingSaga orchestrator         |
|  detects the confirmation failure and triggers compensation:            |
|  1. Refund the payment (payment service idempotent refund API)          |
|  2. Release the inventory hold                                          |
|  3. Notify the user of the failure                                      |
|  Each compensation step is idempotent and retried until success.        |
|  The saga's state is persisted, so even if the orchestrator crashes,    |
|  it resumes compensation on restart.                                    |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q4: How does the temporary hold work? What if the user abandons?       |
|  -------------------------------------------------------------------    |
|  A: When a user selects a room, we decrement available inventory        |
|  and create a hold record with a 10-15 minute TTL. A background         |
|  job (or Redis key expiry callback) checks for expired holds and        |
|  releases them back to inventory. The hold prevents others from         |
|  booking while the user enters payment details, but auto-expires        |
|  to prevent permanent inventory lockup from abandoned sessions.         |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q5: How would you handle a flash sale (e.g., 50% off a luxury hotel)?  |
|  -------------------------------------------------------------------    |
|  A: Multi-layer defense:                                                |
|  1. Rate limiting at API gateway (per-user, per-IP)                     |
|  2. Queue serialization: route all booking requests for that hotel      |
|     through a Kafka partition > single consumer processes in order      |
|  3. Waiting room / virtual queue: frontend shows "You are #347 in       |
|     line" to manage user expectations and reduce server load            |
|  4. Pre-validate availability before entering the queue to reject       |
|     obviously impossible requests early                                 |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q6: Why shard by hotel_id and not by user_id?                          |
|  -------------------------------------------------------------------    |
|  A: The critical transaction is: "check availability + decrement        |
|  inventory + create booking" - all for the SAME hotel. Sharding         |
|  by hotel_id keeps all these operations on a single shard, avoiding     |
|  distributed transactions. User-level queries (my bookings) are         |
|  less frequent and can use a secondary index or a separate read         |
|  model (event-sourced from booking events).                             |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q7: How do you keep Elasticsearch in sync with the booking DB?         |
|  -------------------------------------------------------------------    |
|  A: Event-driven sync via Kafka. When a booking is created or           |
|  cancelled, a BookingEvent is published to Kafka. An ES updater         |
|  consumer reads the event and updates the hotel's availability in       |
|  the ES index. This is eventually consistent (seconds delay), which     |
|  is acceptable for search results. The real availability check          |
|  happens at booking time against the source-of-truth Postgres DB.       |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q8: How do you handle the case where search shows "available" but      |
|      booking fails because it was just booked?                          |
|  -------------------------------------------------------------------    |
|  A: This is expected and by design. Search uses cached/eventually       |
|  consistent data for performance. When the user clicks "Book", the      |
|  availability service does a real-time check against the DB. If         |
|  the room was just booked, we return a clear error: "This room is       |
|  no longer available" and suggest alternative rooms or dates. The       |
|  UX should gracefully handle this common scenario.                      |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q9: How would you add dynamic pricing?                                 |
|  -------------------------------------------------------------------    |
|  A: A pricing service that adjusts rates based on:                      |
|  * Demand (occupancy rate approaching capacity > price up)              |
|  * Seasonality (holidays, events in the city)                           |
|  * Competitor pricing (scrape or API)                                   |
|  * Lead time (last-minute deals vs far-out bookings)                    |
|  Prices computed periodically (every 15 min) and cached. The search     |
|  index stores current prices. At booking time, the confirmed price      |
|  is locked in (the price shown at selection time, not a stale cache).   |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q10: How is this different from designing an airline reservation?      |
|  -------------------------------------------------------------------    |
|  A: Key differences:                                                    |
|  1. Overbooking: airlines overbook (~15%), hotels generally don't       |
|  2. Seat selection: airlines have specific seats (assigned graph),      |
|     hotels have room TYPES (fungible inventory count)                   |
|  3. Pricing: airline pricing is far more dynamic (yield management),    |
|     hotel pricing changes less frequently                               |
|  4. Multi-leg: flights have connections (A>B>C), hotels are single      |
|     location but multi-night (each night is like a "leg")               |
|  5. Check-in: airlines have online check-in + boarding pass,            |
|     hotels have front-desk check-in                                     |
|  The core booking/concurrency patterns are very similar.                |
|                                                                         |
+-------------------------------------------------------------------------+
```
