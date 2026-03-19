# AUCTION SYSTEM DESIGN (EBAY)

*Complete Design: Requirements, Architecture, and Interview Guide*

## SECTION 1: UNDERSTANDING THE PROBLEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|   an online auction system enables users to list items for sale,        |
|   place competitive bids, and the highest bidder wins when the          |
|   auction timer expires. the system must handle real-time price         |
|   updates, enforce bidding rules, and ensure fair outcomes.             |
|                                                                         |
|   KEY CONCEPTS:                                                         |
|                                                                         |
|   * sellers create listings with a starting price and duration          |
|   * buyers place bids that must exceed the current highest bid          |
|   * the highest bidder when the timer expires wins the item             |
|   * real-time updates keep all participants informed of changes         |
|   * optional reserve price sets a minimum acceptable sale price         |
|   * "buy it now" allows instant purchase at a fixed price               |
|                                                                         |
|   AUCTION TYPES:                                                        |
|                                                                         |
|   * english auction (ascending): bids increase, highest wins            |
|     most common type, used by ebay for standard auctions                |
|   * dutch auction (descending): price drops until someone accepts       |
|     used for perishable goods, flowers, some wholesale markets          |
|   * sealed-bid: single hidden bid, highest wins                         |
|     used for government contracts, real estate                          |
|   * vickrey: sealed-bid but winner pays second-highest price            |
|     encourages truthful bidding, used in ad auctions                    |
|                                                                         |
|   CORE ENTITIES:                                                        |
|                                                                         |
|   * item: the product or service being auctioned                        |
|   * auction: the time-bound event with rules for selling an item        |
|   * bid: a monetary offer placed by a buyer on an auction               |
|   * user: a participant who can act as seller, buyer, or both           |
|   * watchlist: items a user is monitoring without actively bidding      |
|   * feedback: ratings and reviews exchanged after transactions          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2: REQUIREMENTS

### FUNCTIONAL REQUIREMENTS

```
+--------------------------------------------------------------------------+
|                                                                          |
|   SELLER CAPABILITIES:                                                   |
|                                                                          |
|   * create an auction with title, description, images, category          |
|   * set starting price, reserve price, and buy-it-now price              |
|   * define auction start time and end time (scheduled auctions)          |
|   * edit auction details before the first bid is placed                  |
|   * cancel an auction if no bids have been received yet                  |
|   * view real-time bid activity and current highest bid                  |
|                                                                          |
|   BUYER CAPABILITIES:                                                    |
|                                                                          |
|   * browse and search auctions by category, keyword, price range         |
|   * place a bid that exceeds the current highest bid by min increment    |
|   * set a maximum bid for automatic proxy bidding                        |
|   * use "buy it now" to purchase immediately at fixed price              |
|   * add auctions to a personal watchlist for tracking                    |
|   * receive notifications on outbid, auction ending, win                 |
|                                                                          |
|   SYSTEM CAPABILITIES:                                                   |
|                                                                          |
|   * auto-extend auction by 2-5 minutes if bid placed near end            |
|   * enforce minimum bid increments based on current price                |
|   * determine winner automatically when auction timer expires            |
|   * handle reserve price logic (no winner if reserve not met)            |
|   * process payment and coordinate shipping after auction ends           |
|   * maintain bid history with timestamps for audit trail                 |
|                                                                          |
+--------------------------------------------------------------------------+
```

### NON-FUNCTIONAL REQUIREMENTS

```
+--------------------------------------------------------------------------+
|                                                                          |
|   CONSISTENCY:                                                           |
|                                                                          |
|   * strong consistency for bid placement and acceptance                  |
|   * no two bids should be accepted for the same amount                   |
|   * bid ordering must be deterministic (first valid bid wins ties)       |
|   * auction end state must be consistent across all nodes                |
|                                                                          |
|   LATENCY:                                                               |
|                                                                          |
|   * bid placement response within 200ms                                  |
|   * real-time price updates delivered within 1 second                    |
|   * search results returned within 500ms                                 |
|   * notification delivery within 2 seconds of triggering event           |
|                                                                          |
|   SCALE:                                                                 |
|                                                                          |
|   * 100K+ concurrent users during peak hours                             |
|   * 10M+ active auctions at any given time                               |
|   * 1000+ bids per second on popular auctions                            |
|   * 50M+ registered users total                                          |
|                                                                          |
|   AVAILABILITY:                                                          |
|                                                                          |
|   * 99.99% uptime for bid placement service                              |
|   * graceful degradation: search can be eventually consistent            |
|   * auction timer must be reliable (cannot miss auction end)             |
|   * payment processing must be exactly-once                              |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 3: BACK-OF-ENVELOPE ESTIMATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|   TRAFFIC ESTIMATES:                                                    |
|                                                                         |
|   * 50M registered users, 5M daily active users (DAU)                   |
|   * 10M active auctions at any time                                     |
|   * average auction receives 20 bids over its lifetime                  |
|   * 500K new auctions created per day                                   |
|   * 10M bids placed per day                                             |
|   * peak bid rate: 10M / 86400 * 10x peak factor = ~1150 bids/sec       |
|   * hot auctions: single auction can see 100+ bids/sec at end           |
|                                                                         |
|   STORAGE ESTIMATES:                                                    |
|                                                                         |
|   * auction record: ~2 KB (metadata, description, settings)             |
|   * bid record: ~200 bytes (auction_id, user_id, amount, timestamp)     |
|   * images: ~5 images per auction * 500 KB = 2.5 MB per auction         |
|   * daily new auctions: 500K * 2 KB = 1 GB metadata                     |
|   * daily new bids: 10M * 200 bytes = 2 GB                              |
|   * daily images: 500K * 2.5 MB = 1.25 TB                               |
|   * yearly storage: ~500 TB (mostly images, stored in object store)     |
|                                                                         |
|   BANDWIDTH ESTIMATES:                                                  |
|                                                                         |
|   * bid placement: 1150 bids/sec * 1 KB = 1.15 MB/sec inbound           |
|   * real-time updates: each bid fans out to ~100 watchers               |
|   * update fanout: 1150 * 100 * 500 bytes = 57.5 MB/sec outbound        |
|   * search queries: 10K QPS * 10 KB response = 100 MB/sec               |
|   * image serving: 50K req/sec * 500 KB = 25 GB/sec (use CDN)           |
|                                                                         |
|   INFRASTRUCTURE SUMMARY:                                               |
|                                                                         |
|   * bid service: 20+ servers (high CPU for validation + locking)        |
|   * websocket servers: 50+ servers (100K connections each)              |
|   * database: sharded PostgreSQL cluster (10+ shards)                   |
|     WHY PG: Bids are financial - ACID prevents double-bids. Sharded     |
|     by auction_id for write scalability. Strong consistency for         |
|     "highest bid" queries (no stale reads).                             |
|   * cache: Redis cluster with 500 GB+ memory                            |
|     WHY REDIS: Current highest bid checked on every new bid. Sub-ms     |
|     reads. Sorted sets for leaderboards. Pub/Sub for real-time          |
|     bid notifications to watchers.                                      |
|   * message broker: Kafka cluster (bid events, notifications)           |
|     WHY KAFKA: Bid events fan out to notification, analytics, fraud     |
|     detection. Durable log for audit. Ordered per partition             |
|     (auction_id key) ensures bid sequence preserved.                    |
|   * CDN: for all static assets (images, thumbnails)                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4: HIGH-LEVEL ARCHITECTURE

```
+--------------------------------------------------------------------------+
|                                                                          |
|   SYSTEM COMPONENTS OVERVIEW:                                            |
|                                                                          |
|                        +------------------+                              |
|                        |  load balancer   |                              |
|                        |  (nginx / ALB)   |                              |
|                        +--------+---------+                              |
|                                 |                                        |
|              +------------------+------------------+                     |
|              |                  |                  |                     |
|     +--------+-------+ +-------+--------+ +-------+--------+             |
|     |    API         | |   WebSocket    | |    CDN         |             |
|     |    gateway     | |   gateway      | |    (images)    |             |
|     +--------+-------+ +-------+--------+ +----------------+             |
|              |                  |                                        |
|    +---------+---------+--------+---------+                              |
|    |         |         |        |         |                              |
|  +-+--+  +--+-+  +----++  +---+--+  +---+---+                            |
|  |auc | |bid | |timer | |notif | |search |                               |
|  |svc | |svc | | svc  | | svc  | | svc   |                               |
|  +-+--+  +--+-+  +----++  +---+--+  +---+---+                            |
|    |         |      |        |          |                                |
|  +-+--+  +--+-+  +-+---+  +-+---+  +---+----+                            |
|  | PG |  |redis|  |redis|  |kafka|  |elastic |                           |
|  |    |  |     |  |timer|  |     |  |search  |                           |
|  +----+  +-----+  +-----+  +-----+  +--------+                           |
|                                                                          |
+--------------------------------------------------------------------------+
```

### SERVICE RESPONSIBILITIES

```
+-------------------------------------------------------------------------+
|                                                                         |
|   AUCTION SERVICE:                                                      |
|                                                                         |
|   * manages auction CRUD operations (create, read, update, delete)      |
|   * enforces auction rules (cannot edit after first bid, etc.)          |
|   * stores auction metadata in PostgreSQL                               |
|   * publishes auction lifecycle events to Kafka                         |
|   * handles category management and auction templates                   |
|                                                                         |
|   BID SERVICE:                                                          |
|                                                                         |
|   * accepts and validates incoming bids                                 |
|   * manages bid concurrency with Redis-backed locking                   |
|   * implements proxy bidding (auto-bid) logic                           |
|   * publishes bid events to Kafka for real-time fanout                  |
|   * maintains bid history for audit and dispute resolution              |
|                                                                         |
|   TIMER SERVICE:                                                        |
|                                                                         |
|   * tracks auction start and end times                                  |
|   * triggers auction state transitions at scheduled times               |
|   * handles auto-extension logic when late bids arrive                  |
|   * uses Redis sorted sets for efficient timer management               |
|   * must be highly reliable (missing an end time is critical)           |
|                                                                         |
|   NOTIFICATION SERVICE:                                                 |
|                                                                         |
|   * sends real-time updates via WebSocket connections                   |
|   * delivers email/push notifications for key events                    |
|   * handles outbid alerts, auction ending soon, winner notices          |
|   * consumes events from Kafka and fans out to subscribers              |
|                                                                         |
|   PAYMENT SERVICE:                                                      |
|                                                                         |
|   * processes winner payment after auction ends                         |
|   * manages escrow (hold funds until item delivered)                    |
|   * handles refunds and dispute resolution                              |
|   * integrates with external payment gateways (Stripe, PayPal)          |
|                                                                         |
|   SEARCH SERVICE:                                                       |
|                                                                         |
|   * indexes auction data in Elasticsearch                               |
|   * supports full-text search, filters, faceted navigation              |
|   * handles category browsing and recommendation queries                |
|   * eventually consistent (slight delay after auction updates)          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5: AUCTION LIFECYCLE

```
+-------------------------------------------------------------------------+
|                                                                         |
|   STATE MACHINE:                                                        |
|                                                                         |
|   +-------+     +-----------+     +--------+     +-------------+        |
|   | DRAFT | --> | SCHEDULED | --> | ACTIVE | --> | ENDING SOON |        |
|   +-------+     +-----------+     +--------+     +------+------+        |
|       |                               |                  |              |
|       v                               v                  v              |
|   +-----------+                 +-----------+      +----------+         |
|   | CANCELLED |                 | CANCELLED |      |  ENDED   |         |
|   +-----------+                 +-----------+      +-----+----+         |
|                                  (no bids only)          |              |
|                                                    +-----+-----+        |
|                                                    |  reserve   |       |
|                                                    |  met?      |       |
|                                                    +--+------+--+       |
|                                                   yes |      | no       |
|                                                       v      v          |
|                                                 +-------+ +---------+   |
|                                                 |PAYMENT| |NO SALE  |   |
|                                                 +---+---+ +---------+   |
|                                                     |                   |
|                                                     v                   |
|                                                 +-----------+           |
|                                                 | COMPLETED |           |
|                                                 +-----------+           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### STATE TRANSITION DETAILS

```
+--------------------------------------------------------------------------+
|                                                                          |
|   DRAFT --> SCHEDULED:                                                   |
|                                                                          |
|   * seller fills in all required fields and submits                      |
|   * system validates item details, images, pricing                       |
|   * auction is queued for activation at the start time                   |
|   * timer service registers the start time trigger                       |
|                                                                          |
|   SCHEDULED --> ACTIVE:                                                  |
|                                                                          |
|   * timer service fires at the scheduled start time                      |
|   * auction becomes visible in search results                            |
|   * bid service begins accepting bids for this auction                   |
|   * websocket channels are opened for real-time updates                  |
|                                                                          |
|   ACTIVE --> ENDING SOON:                                                |
|                                                                          |
|   * triggered when remaining time falls below threshold (e.g. 5 min)     |
|   * notification service alerts all watchers and bidders                 |
|   * UI displays urgent visual indicators (countdown, color change)       |
|   * auto-extend logic becomes active during this phase                   |
|                                                                          |
|   ENDING SOON --> ENDED:                                                 |
|                                                                          |
|   * timer expires and no more bids are within the extension window       |
|   * bid service stops accepting new bids atomically                      |
|   * final highest bid is locked as the winning bid                       |
|   * system checks if reserve price was met                               |
|                                                                          |
|   AUTO-EXTENSION LOGIC:                                                  |
|                                                                          |
|   * if a bid arrives in the last N minutes (typically 2-5 min)           |
|   * the auction end time extends by N minutes from the bid time          |
|   * prevents "auction sniping" (last-second bids)                        |
|   * extension can repeat multiple times but has a maximum cap            |
|   * timer service must update the end time atomically                    |
|                                                                          |
|   ENDED --> PAYMENT --> COMPLETED:                                       |
|                                                                          |
|   * winner is notified and given a payment deadline (e.g. 48 hours)      |
|   * payment is collected and held in escrow                              |
|   * seller ships the item and provides tracking info                     |
|   * buyer confirms receipt or auto-confirm after timeout                 |
|   * funds are released to seller, feedback is exchanged                  |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 6: BID PROCESSING

### BID VALIDATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|   VALIDATION PIPELINE (executed in order):                              |
|                                                                         |
|   1. authentication: verify user is logged in and not banned            |
|   2. auction status: confirm auction is in ACTIVE state                 |
|   3. seller check: ensure bidder is not the auction seller              |
|   4. amount check: bid >= current_highest + minimum_increment           |
|   5. balance check: verify bidder has sufficient funds or credit        |
|   6. rate limit: prevent bid flooding (max N bids per minute)           |
|   7. fraud check: run real-time fraud scoring on the bid                |
|                                                                         |
|   MINIMUM BID INCREMENT TABLE:                                          |
|                                                                         |
|   current price         |  minimum increment                            |
|   ----------------------|------------------                             |
|   $0.01   - $0.99       |  $0.05                                        |
|   $1.00   - $4.99       |  $0.25                                        |
|   $5.00   - $24.99      |  $0.50                                        |
|   $25.00  - $99.99      |  $1.00                                        |
|   $100.00 - $249.99     |  $2.50                                        |
|   $250.00 - $499.99     |  $5.00                                        |
|   $500.00 - $999.99     |  $10.00                                       |
|   $1000+                |  $25.00                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CONCURRENCY CONTROL

```
+-------------------------------------------------------------------------+
|                                                                         |
|   CHALLENGE: thousands of users may bid on the same auction             |
|   simultaneously. we must ensure exactly one bid wins at each           |
|   price level and maintain a consistent bid ordering.                   |
|                                                                         |
|   APPROACH 1: OPTIMISTIC LOCKING (PostgreSQL)                           |
|                                                                         |
|   * each auction row has a version column                               |
|   * read current price and version                                      |
|   * validate bid amount > current price + increment                     |
|   * UPDATE auctions SET current_price = :bid, version = version + 1     |
|     WHERE id = :auction_id AND version = :expected_version              |
|   * if rows_affected = 0, another bid won the race; retry or reject     |
|   * pros: simple, uses existing DB infrastructure                       |
|   * cons: high contention on hot auctions causes many retries           |
|                                                                         |
|   APPROACH 2: REDIS SORTED SET (recommended for hot auctions)           |
|                                                                         |
|   * use Redis sorted set with score = bid amount, member = bid_id       |
|   * ZADD with NX flag ensures only one bid per exact amount             |
|   * Lua script for atomic check-and-set:                                |
|                                                                         |
|     local current = redis.call('ZREVRANGE', key, 0, 0, 'WITHSCORES')    |
|     if bid_amount > current_score then                                  |
|       redis.call('ZADD', key, bid_amount, bid_id)                       |
|       return 1  -- bid accepted                                         |
|     end                                                                 |
|     return 0  -- bid rejected (stale)                                   |
|                                                                         |
|   * pros: extremely fast, handles high contention well                  |
|   * cons: need to persist to DB asynchronously, Redis failure risk      |
|                                                                         |
|   APPROACH 3: QUEUE SERIALIZATION                                       |
|                                                                         |
|   * all bids for an auction go to a single partition in Kafka           |
|   * a dedicated consumer processes bids sequentially per auction        |
|   * eliminates concurrency entirely for a given auction                 |
|   * pros: simple logic, no race conditions                              |
|   * cons: higher latency, single consumer bottleneck                    |
|                                                                         |
|   RECOMMENDATION: use Redis sorted set for hot auctions (100+ bids/     |
|   sec) and optimistic locking for normal auctions. detect hotness       |
|   dynamically and route accordingly.                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### PROXY BIDDING (AUTO-BID)

```
+-------------------------------------------------------------------------+
|                                                                         |
|   proxy bidding lets a user set a maximum bid, and the system           |
|   automatically bids on their behalf up to that maximum.                |
|                                                                         |
|   HOW IT WORKS:                                                         |
|                                                                         |
|   * user sets max_bid = $100 when current price is $50                  |
|   * system places bid at $50 + min_increment = $51                      |
|   * when another user bids $55, system auto-bids $56 for proxy user     |
|   * this continues until max_bid is reached or auction ends             |
|   * if two proxy bidders compete, the one with higher max wins          |
|     at the loser's max + min_increment                                  |
|                                                                         |
|   IMPLEMENTATION:                                                       |
|                                                                         |
|   * store proxy bids in a separate table:                               |
|     proxy_bids(id, auction_id, user_id, max_amount, active)             |
|   * on each new bid, check if any active proxy bids can respond         |
|   * process proxy bids synchronously within the bid pipeline            |
|   * a single incoming bid may trigger a chain of proxy responses        |
|   * limit chain depth to prevent infinite loops (max 50 iterations)     |
|                                                                         |
|   EDGE CASES:                                                           |
|                                                                         |
|   * two proxy bidders with same max: first one to set it wins           |
|   * proxy bid equal to current price: rejected (must exceed)            |
|   * proxy bid set after auction enters ENDING SOON: still valid         |
|   * user manually bids while proxy is active: proxy is cancelled        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7: REAL-TIME UPDATES

```
+--------------------------------------------------------------------------+
|                                                                          |
|   real-time updates are critical for auction systems. bidders must       |
|   see price changes, time extensions, and auction events within          |
|   1 second to make informed decisions.                                   |
|                                                                          |
|   ARCHITECTURE:                                                          |
|                                                                          |
|   +--------+     +-------+     +---------+     +----------+              |
|   |  bid   | --> | Kafka | --> |  fanout  | --> | WebSocket|             |
|   |service |     | topic |     | service  |     | servers  |             |
|   +--------+     +-------+     +---------+     +-----+----+              |
|                                                       |                  |
|                                                       v                  |
|                                                 +-----------+            |
|                                                 |  browser  |            |
|                                                 |  clients  |            |
|                                                 +-----------+            |
|                                                                          |
|   EVENT FLOW:                                                            |
|                                                                          |
|   1. bid service validates and accepts a new bid                         |
|   2. bid event published to Kafka topic "auction.bids"                   |
|   3. fanout service consumes event, looks up auction subscribers         |
|   4. message pushed to all WebSocket servers hosting subscribers         |
|   5. WebSocket servers deliver update to connected clients               |
|                                                                          |
|   WEBSOCKET MESSAGE PAYLOAD:                                             |
|                                                                          |
|   {                                                                      |
|     "type": "bid_update",                                                |
|     "auction_id": "abc123",                                              |
|     "current_price": 150.00,                                             |
|     "bid_count": 47,                                                     |
|     "time_remaining_sec": 342,                                           |
|     "highest_bidder": "user_masked_id",                                  |
|     "your_status": "outbid"                                              |
|   }                                                                      |
|                                                                          |
+--------------------------------------------------------------------------+
```

### WEBSOCKET CONNECTION MANAGEMENT

```
+--------------------------------------------------------------------------+
|                                                                          |
|   SUBSCRIPTION MODEL:                                                    |
|                                                                          |
|   * client connects and subscribes to specific auction channels          |
|   * server maintains a mapping: auction_id -> set of connections         |
|   * when client navigates away, they unsubscribe from the channel        |
|   * heartbeat every 30 seconds to detect stale connections               |
|                                                                          |
|   SCALING WEBSOCKET SERVERS:                                             |
|                                                                          |
|   * each WebSocket server handles ~100K concurrent connections           |
|   * use consistent hashing to route clients to specific servers          |
|   * sticky sessions via load balancer for connection persistence         |
|   * inter-server communication via Redis pub/sub:                        |
|     when a bid event arrives, publish to Redis channel                   |
|     all WebSocket servers subscribed to that channel broadcast           |
|                                                                          |
|   FALLBACK FOR DISCONNECTED CLIENTS:                                     |
|                                                                          |
|   * if WebSocket connection drops, client polls REST API                 |
|   * long-polling as secondary transport (Server-Sent Events)             |
|   * on reconnect, client sends last_event_id to receive missed           |
|     updates from an event replay buffer (last 5 minutes)                 |
|                                                                          |
|   BANDWIDTH OPTIMIZATION:                                                |
|                                                                          |
|   * only send delta updates (changed fields, not full auction)           |
|   * batch multiple rapid bids into single update (100ms window)          |
|   * compress WebSocket frames with permessage-deflate                    |
|   * rate-limit outbound updates per client (max 5/sec per auction)       |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 8: AUCTION END AND SETTLEMENT

```
+-------------------------------------------------------------------------+
|                                                                         |
|   TIMER SERVICE FOR AUCTION END:                                        |
|                                                                         |
|   * uses Redis sorted set: score = end_timestamp, member = auction_id   |
|   * background worker polls ZRANGEBYSCORE for expired auctions          |
|   * polling interval: every 500ms for high precision                    |
|   * on expiry, publishes "auction.ended" event to Kafka                 |
|   * distributed locking ensures only one worker processes each end      |
|                                                                         |
|   WINNER DETERMINATION:                                                 |
|                                                                         |
|   1. lock the auction to reject any new bids atomically                 |
|   2. query the highest bid from the bid table or Redis sorted set       |
|   3. check if the winning bid meets the reserve price                   |
|   4. if reserve met: mark winner, notify buyer and seller               |
|   5. if reserve not met: mark as NO SALE, notify all parties            |
|   6. if no bids at all: mark as EXPIRED, return to seller               |
|                                                                         |
|   RACE CONDITION AT AUCTION END:                                        |
|                                                                         |
|   * a bid may arrive at the exact moment the timer fires                |
|   * solution: use a distributed lock on the auction                     |
|     * timer acquires lock, sets status = ENDED                          |
|     * bid service checks status before accepting                        |
|     * if ENDED, bid is rejected regardless of timing                    |
|   * the lock ensures the transition is atomic                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### PAYMENT AND ESCROW

```
+--------------------------------------------------------------------------+
|                                                                          |
|   PAYMENT FLOW:                                                          |
|                                                                          |
|   1. winner receives payment notification with 48-hour deadline          |
|   2. winner submits payment via saved payment method                     |
|   3. payment service authorizes the charge (hold, not capture)           |
|   4. funds are held in escrow (platform-managed account)                 |
|   5. seller is notified to ship the item                                 |
|   6. seller provides shipping tracking number                            |
|   7. buyer confirms receipt (or auto-confirm after 14 days)              |
|   8. escrow releases funds to seller minus platform commission           |
|                                                                          |
|   DISPUTE RESOLUTION:                                                    |
|                                                                          |
|   * buyer can open dispute within 30 days of delivery                    |
|   * common disputes: item not as described, damaged, not received        |
|   * platform mediates between buyer and seller                           |
|   * escalation to manual review if not resolved within 7 days            |
|   * refund can be full or partial depending on case                      |
|   * repeat offenders face account suspension                             |
|                                                                          |
|   EDGE CASES:                                                            |
|                                                                          |
|   * winner does not pay within deadline:                                 |
|     * offer to second-highest bidder                                     |
|     * seller can relist the item                                         |
|     * non-paying bidder receives a strike (3 strikes = ban)              |
|   * seller does not ship within deadline:                                |
|     * automatic refund to buyer from escrow                              |
|     * seller receives a strike and potential suspension                  |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 9: ANTI-FRAUD MEASURES

```
+-------------------------------------------------------------------------+
|                                                                         |
|   SHILL BIDDING DETECTION:                                              |
|                                                                         |
|   * shill bidding: seller (or accomplice) bids on own auction to        |
|     artificially inflate the price                                      |
|                                                                         |
|   detection signals:                                                    |
|   * same IP address as seller places bids on their auctions             |
|   * new accounts that only bid on one seller's items                    |
|   * bidder and seller share payment methods or shipping addresses       |
|   * bidder always loses by small margin (never wins)                    |
|   * bidding pattern analysis: bids only when no competition             |
|                                                                         |
|   BID SHIELDING DETECTION:                                              |
|                                                                         |
|   * bid shielding: two accomplices bid high to scare off real           |
|     bidders, then retract the high bid before auction ends              |
|                                                                         |
|   detection signals:                                                    |
|   * pattern of placing extremely high bids then retracting              |
|   * same pair of users repeatedly bid and retract on same seller        |
|   * bid retraction rate significantly above average                     |
|                                                                         |
|   VELOCITY CHECKS:                                                      |
|                                                                         |
|   * max bids per minute per user (e.g. 10 bids/min)                     |
|   * max bids per minute per auction (e.g. 100 bids/min)                 |
|   * max new accounts per IP per day (e.g. 3 accounts/day)               |
|   * sudden spike in bidding activity on obscure items                   |
|                                                                         |
|   ML-BASED ANOMALY DETECTION:                                           |
|                                                                         |
|   * train models on historical bid patterns (legitimate vs fraud)       |
|   * features: bid timing, amount patterns, user graph, device info      |
|   * real-time scoring: each bid gets a fraud risk score (0-100)         |
|   * high-risk bids are held for manual review                           |
|   * model retrained weekly with newly labeled fraud cases               |
|   * graph analysis: detect rings of colluding accounts                  |
|                                                                         |
|   ENFORCEMENT ACTIONS:                                                  |
|                                                                         |
|   * warning for first-time low-severity violations                      |
|   * temporary suspension (7-30 days) for confirmed fraud                |
|   * permanent ban for repeat offenders                                  |
|   * voiding of fraudulent auction results                               |
|   * reporting to law enforcement for large-scale fraud rings            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 10: SCALING STRATEGIES

### AUCTION DATA SHARDING

```
+-------------------------------------------------------------------------+
|                                                                         |
|   DATABASE SHARDING STRATEGY:                                           |
|                                                                         |
|   * shard key: auction_id (hash-based sharding)                         |
|   * ensures all bids for an auction land on the same shard              |
|   * 16-64 shards initially, split further as needed                     |
|   * lookup table maps auction_id hash range to shard                    |
|                                                                         |
|   shard 0:  auction_id hash [0x0000 - 0x0FFF]                           |
|   shard 1:  auction_id hash [0x1000 - 0x1FFF]                           |
|   shard 2:  auction_id hash [0x2000 - 0x2FFF]                           |
|   ...                                                                   |
|   shard 15: auction_id hash [0xF000 - 0xFFFF]                           |
|                                                                         |
|   * cross-shard queries (e.g. "all auctions by user X") use             |
|     scatter-gather or a secondary index in Elasticsearch                |
|   * each shard has a primary + 2 replicas for fault tolerance           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### HOT AUCTION HANDLING

```
+-------------------------------------------------------------------------+
|                                                                         |
|   PROBLEM: celebrity or viral auctions get 100x normal traffic          |
|   (thousands of bids per second, millions of watchers)                  |
|                                                                         |
|   STRATEGIES:                                                           |
|                                                                         |
|   * detect hot auctions: bid rate > 50/sec triggers "hot" flag          |
|   * promote hot auction to dedicated Redis instance                     |
|   * all bid processing moves to in-memory (Redis Lua scripts)           |
|   * dedicated WebSocket server pool for hot auction subscribers         |
|   * batch bid validation: group bids in 50ms windows, process best      |
|   * rate-limit low bids: reject bids < current + 2x increment           |
|                                                                         |
|   HOT AUCTION ARCHITECTURE:                                             |
|                                                                         |
|     +--------+    +------------+    +----------+                        |
|     | bids   | -> | dedicated  | -> | dedicated|                        |
|     | (queue)| -> | Redis      | -> | WebSocket|                        |
|     +--------+    +------------+    +----------+                        |
|                         |                                               |
|                    +----+-----+                                         |
|                    | async DB |                                         |
|                    | persist  |                                         |
|                    +----------+                                         |
|                                                                         |
|   * bids are accepted in Redis first (sub-millisecond latency)          |
|   * asynchronously persisted to PostgreSQL for durability               |
|   * if Redis fails, fall back to DB-based locking                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WEBSOCKET SCALING

```
+--------------------------------------------------------------------------+
|                                                                          |
|   CHALLENGE: 5M concurrent WebSocket connections at peak                 |
|                                                                          |
|   * each server handles ~100K connections (mostly idle)                  |
|   * 50+ WebSocket servers needed at peak                                 |
|   * sticky sessions ensure client reconnects to same server              |
|                                                                          |
|   INTER-SERVER MESSAGE ROUTING:                                          |
|                                                                          |
|   * when bid accepted, determine which servers host subscribers          |
|   * option A: Redis pub/sub (broadcast to all WS servers)                |
|     * simple but wasteful if subscribers are on few servers              |
|   * option B: subscription registry (track server -> auction mapping)    |
|     * more efficient, only send to relevant servers                      |
|     * higher complexity, registry must be kept in sync                   |
|   * option C: hybrid (Redis pub/sub for hot auctions, registry for       |
|     normal auctions)                                                     |
|                                                                          |
|   CONNECTION LIFECYCLE:                                                  |
|                                                                          |
|   * client connects -> authenticate -> subscribe to auction(s)           |
|   * server registers subscription in local memory + registry             |
|   * on disconnect, cleanup subscription after grace period (30s)         |
|   * on server crash, clients reconnect and resubscribe                   |
|   * health checks every 30s, evict connections with 3 missed pings       |
|                                                                          |
+--------------------------------------------------------------------------+
```

### TIMER SERVICE SCALING

```
+--------------------------------------------------------------------------+
|                                                                          |
|   CHALLENGE: 10M active auctions, each with a precise end time           |
|                                                                          |
|   * cannot use cron jobs (too many, not precise enough)                  |
|   * cannot poll database (too slow at scale)                             |
|                                                                          |
|   APPROACH: SHARDED REDIS TIMER WHEELS                                   |
|                                                                          |
|   * partition auctions across N Redis instances by auction_id hash       |
|   * each Redis holds a sorted set: score = end_timestamp                 |
|   * dedicated worker per shard polls every 500ms                         |
|     ZRANGEBYSCORE timers 0 <now> LIMIT 0 100                             |
|   * worker processes expired timers and removes them atomically          |
|                                                                          |
|   RELIABILITY:                                                           |
|                                                                          |
|   * each timer shard has a primary and standby worker                    |
|   * if primary fails health check, standby takes over within 2s          |
|   * timer events are idempotent (processing same end twice is safe)      |
|   * audit log tracks all timer fires for debugging                       |
|   * maximum allowed drift: 1 second (acceptable for auctions)            |
|                                                                          |
|   AUTO-EXTENSION HANDLING:                                               |
|                                                                          |
|   * when auto-extend triggers, update the score in sorted set            |
|   * ZADD timers XX <new_end_time> <auction_id>                           |
|   * the worker will naturally pick up the new end time                   |
|   * concurrent extension and expiry handled by distributed lock          |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 11: INTERVIEW QUESTIONS AND ANSWERS

### Q1: HOW DO YOU PREVENT AUCTION SNIPING?

```
+-------------------------------------------------------------------------+
|                                                                         |
|   auction sniping is when a bidder places a bid in the final            |
|   seconds, leaving no time for others to respond.                       |
|                                                                         |
|   * implement auto-extension: if a bid is placed in the last N          |
|     minutes (typically 2-5), extend the auction by N minutes            |
|   * this gives other bidders time to respond to the new bid             |
|   * the extension can repeat until no bids arrive in the window         |
|   * cap total extensions (e.g. max 30 minutes of extensions)            |
|   * this is the approach used by ebay and most auction platforms        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q2: HOW DO YOU HANDLE CONCURRENT BIDS ON THE SAME AUCTION?

```
+-------------------------------------------------------------------------+
|                                                                         |
|   * use Redis Lua scripts for atomic read-compare-write operations      |
|   * the script checks current highest bid and accepts only if the       |
|     new bid exceeds it by the minimum increment                         |
|   * for normal auctions, optimistic locking on the database row         |
|     works well (version column, retry on conflict)                      |
|   * for hot auctions (100+ bids/sec), use dedicated Redis instance      |
|     with all bid logic in Lua for sub-millisecond processing            |
|   * bids are ordered by amount first, then by timestamp for ties        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q3: WHAT HAPPENS IF THE TIMER SERVICE FAILS?

```
+-------------------------------------------------------------------------+
|                                                                         |
|   * each timer shard has a standby worker that monitors the primary     |
|   * if the primary misses a health check, standby takes over            |
|   * timer events are idempotent: processing an already-ended            |
|     auction is a no-op                                                  |
|   * as a safety net, a sweep job runs every 5 minutes to find           |
|     auctions past their end time that are still marked ACTIVE           |
|   * worst case: an auction ends 1-5 seconds late, which is              |
|     acceptable if the UI shows "ending..." state                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q4: HOW DOES PROXY BIDDING WORK?

```
+-------------------------------------------------------------------------+
|                                                                         |
|   * user sets a maximum amount they are willing to pay                  |
|   * system places the minimum winning bid on their behalf               |
|   * when outbid, the system automatically raises their bid              |
|   * this continues until their maximum is reached                       |
|   * two proxy bidders: higher max wins at (lower max + increment)       |
|   * proxy bids are stored separately and evaluated on each new bid      |
|   * important: proxy max amounts are never revealed to other users      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q5: HOW DO YOU SCALE WEBSOCKET CONNECTIONS?

```
+-------------------------------------------------------------------------+
|                                                                         |
|   * horizontal scaling: each server handles ~100K connections           |
|   * sticky sessions via load balancer for connection persistence        |
|   * inter-server messaging via Redis pub/sub or dedicated message       |
|     bus for broadcasting bid updates across servers                     |
|   * subscription registry tracks which servers host which auction       |
|     subscribers to avoid unnecessary broadcasts                         |
|   * fallback to long-polling if WebSocket connection fails              |
|   * client reconnection with last_event_id for missed updates           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q6: HOW DO YOU DETECT SHILL BIDDING?

```
+--------------------------------------------------------------------------+
|                                                                          |
|   * analyze bidding patterns: accounts that bid only on one              |
|     seller's auctions and always lose by small margins                   |
|   * check for shared signals: IP addresses, device fingerprints,         |
|     payment methods, shipping addresses between bidder and seller        |
|   * graph analysis: build a user interaction graph and detect            |
|     tightly connected clusters of accounts                               |
|   * ML model trained on labeled shill bidding cases                      |
|   * real-time risk scoring on each bid (flag, hold, or block)            |
|   * manual review queue for flagged suspicious activity                  |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Q7: HOW DO YOU HANDLE THE AUCTION DATABASE SCHEMA?

```
+-------------------------------------------------------------------------+
|                                                                         |
|   key tables:                                                           |
|                                                                         |
|   auctions:                                                             |
|     id, seller_id, title, description, category_id,                     |
|     start_price, reserve_price, buy_now_price,                          |
|     current_price, bid_count, highest_bidder_id,                        |
|     start_time, end_time, original_end_time,                            |
|     status, version, created_at, updated_at                             |
|                                                                         |
|   bids:                                                                 |
|     id, auction_id, user_id, amount, bid_type (manual/proxy),           |
|     status (accepted/rejected/retracted), created_at                    |
|                                                                         |
|   proxy_bids:                                                           |
|     id, auction_id, user_id, max_amount, current_bid,                   |
|     active, created_at, updated_at                                      |
|                                                                         |
|   watchers:                                                             |
|     auction_id, user_id, created_at                                     |
|                                                                         |
|   indexes: (auction_id, status), (seller_id), (end_time, status),       |
|   (category_id, status), (highest_bidder_id)                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q8: WHAT IS YOUR CACHING STRATEGY?

```
+-------------------------------------------------------------------------+
|                                                                         |
|   * hot data in Redis: current price, bid count, time remaining         |
|   * these fields change with every bid, so cache-aside would be         |
|     ineffective. instead, Redis is the source of truth during           |
|     active auctions, with async persistence to DB                       |
|   * auction metadata (title, description, images) cached in Redis       |
|     with 5-minute TTL, invalidated on update                            |
|   * search results cached at the CDN layer (30-second TTL)              |
|   * user profile data cached with 15-minute TTL                         |
|   * category tree cached at app startup, refreshed hourly               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q9: HOW DO YOU HANDLE PAYMENT FAILURES?

```
+-------------------------------------------------------------------------+
|                                                                         |
|   * payment is attempted when winner clicks "pay now"                   |
|   * if payment gateway returns failure:                                 |
|     * retry up to 3 times with exponential backoff                      |
|     * notify user to update payment method                              |
|     * hold auction in PAYMENT_PENDING state                             |
|   * if winner does not pay within 48 hours:                             |
|     * send final reminder (24h and 48h notifications)                   |
|     * after deadline: offer item to second-highest bidder               |
|     * non-paying bidder receives a strike on their account              |
|   * idempotency key on each payment attempt to prevent double-charge    |
|   * all payment events logged for audit trail and reconciliation        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q10: HOW WOULD YOU IMPLEMENT BUY-IT-NOW?

```
+-------------------------------------------------------------------------+
|                                                                         |
|   * seller sets an optional buy_now_price on the auction                |
|   * buy-it-now is available only before the first bid is placed         |
|     (or before bidding reaches a threshold, e.g. reserve price)         |
|   * when a buyer clicks "buy it now":                                   |
|     1. atomically check that buy-it-now is still available              |
|     2. set auction status to ENDED with the buyer as winner             |
|     3. reject any concurrent bids                                       |
|     4. proceed directly to payment flow                                 |
|   * use a distributed lock to prevent race between buy-now and bids     |
|   * some platforms allow buy-it-now alongside bidding (hybrid)          |
|     * buy-it-now disappears once bidding exceeds a percentage           |
|       of the buy-now price (e.g. 50%)                                   |
|   * buy-it-now with "make offer": buyer proposes lower price,           |
|     seller can accept, reject, or counter                               |
|                                                                         |
+-------------------------------------------------------------------------+
```
