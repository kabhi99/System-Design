# E-COMMERCE SYSTEM DESIGN
*Chapter 2: High-Level Architecture*

This chapter presents the complete architecture of an e-commerce platform,
explaining microservices, data flow, and technology choices.

## SECTION 2.1: ARCHITECTURE OVERVIEW

```
+-------------------------------------------------------------------------+
|                                                                         |
|                    E-COMMERCE ARCHITECTURE                              |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                         CLIENTS                                   |  |
|  |    [Web App]    [Mobile Apps]    [Partner APIs]                   |  |
|  +-------------------------------------------------------------------+  |
|                              |                                          |
|                              v                                          |
|  +-------------------------------------------------------------------+  |
|  |              CDN (Static assets, images, product pages)           |  |
|  +-------------------------------------------------------------------+  |
|                              |                                          |
|                              v                                          |
|  +-------------------------------------------------------------------+  |
|  |                      API GATEWAY                                  |  |
|  |    [Auth] [Rate Limit] [Routing] [Load Balance]                   |  |
|  +-------------------------------------------------------------------+  |
|                              |                                          |
|  +---------------------------+---------------------------+              |
|  |                           |                           |              |
|  v                           v                           v              |
|  +------------+      +------------+      +------------+                 |
|  |   User     |      |  Product   |      |   Search   |                 |
|  |  Service   |      |  Catalog   |      |  Service   |                 |
|  +------------+      +------------+      +------------+                 |
|                                                                         |
|  +------------+      +------------+      +------------+                 |
|  |   Cart     |      |  Inventory |      |   Order    |                 |
|  |  Service   |      |  Service   |      |  Service   |                 |
|  +------------+      +------------+      +------------+                 |
|                                                                         |
|  +------------+      +------------+      +------------+                 |
|  |  Payment   |      |  Shipping  |      | Notification|                |
|  |  Service   |      |  Service   |      |  Service   |                 |
|  +------------+      +------------+      +------------+                 |
|                              |                                          |
|  +---------------------------+---------------------------+              |
|  |                      DATA LAYER                       |              |
|  |  +---------+  +---------+  +---------+  +---------+ |                |
|  |  |PostgreSQL|  | MongoDB |  |  Redis  |  |  Elastic| |               |
|  |  | (Orders) |  |(Catalog)|  | (Cache) |  | (Search)| |               |
|  |  +---------+  +---------+  +---------+  +---------+ |                |
|  +-------------------------------------------------------+              |
|                              |                                          |
|  +---------------------------+---------------------------+              |
|  |                    KAFKA (Event Bus)                  |              |
|  |  [Order Events] [Inventory] [Payments] [Analytics]   |               |
|  +-------------------------------------------------------+              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.2: MICROSERVICES DEEP DIVE

### USER SERVICE

```
+--------------------------------------------------------------------------+
|                                                                          |
|  USER SERVICE                                                            |
|                                                                          |
|  RESPONSIBILITIES:                                                       |
|  * User registration and authentication                                  |
|  * Profile management                                                    |
|  * Address book management                                               |
|  * Wishlist                                                              |
|                                                                          |
|  ENDPOINTS:                                                              |
|  POST /users/register                                                    |
|  POST /users/login                                                       |
|  GET  /users/profile                                                     |
|  POST /users/addresses                                                   |
|  GET  /users/wishlist                                                    |
|                                                                          |
|  DATABASE: PostgreSQL (users, addresses)                                 |
|  * WHY POSTGRESQL? User data is relational (user->addresses,             |
|    user->wishlist). Needs ACID for signup/login (no duplicate emails).   |
|    Mature auth ecosystem (pgcrypto, row-level security).                 |
|                                                                          |
|  CACHE: Redis (sessions, profile cache)                                  |
|  * WHY REDIS? Sessions need sub-ms reads on every authenticated          |
|    request. Redis TTL auto-expires sessions. In-memory speed avoids      |
|    hitting DB on every API call. Profile cache reduces read load         |
|    (profiles are read 100x more than updated).                           |
|                                                                          |
+--------------------------------------------------------------------------+
```

### PRODUCT CATALOG SERVICE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PRODUCT CATALOG SERVICE                                                |
|                                                                         |
|  RESPONSIBILITIES:                                                      |
|  * Product listing and details                                          |
|  * Categories and attributes                                            |
|  * Pricing (can be separate service at scale)                           |
|  * Reviews and ratings                                                  |
|                                                                         |
|  ENDPOINTS:                                                             |
|  GET  /products                                                         |
|  GET  /products/{id}                                                    |
|  GET  /products/{id}/reviews                                            |
|  GET  /categories                                                       |
|  POST /products (seller)                                                |
|                                                                         |
|  WHY MONGODB?                                                           |
|  Products have varying attributes:                                      |
|  * Laptop: RAM, processor, screen size                                  |
|  * Shirt: size, color, material                                         |
|  * Book: author, pages, ISBN                                            |
|                                                                         |
|  Document model handles this flexibility well.                          |
|                                                                         |
|  DATABASE: MongoDB                                                      |
|  * Products collection (flexible schema)                                |
|  * Categories collection                                                |
|  * Reviews collection                                                   |
|                                                                         |
|  CACHE: Redis                                                           |
|  * Popular products (top 10K products = 90% of traffic)                 |
|  * Category listings                                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SEARCH SERVICE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SEARCH SERVICE                                                         |
|                                                                         |
|  RESPONSIBILITIES:                                                      |
|  * Full-text product search with relevance ranking                      |
|  * Faceted search (brand, price range, rating, category filters)        |
|  * Autocomplete / typeahead suggestions                                 |
|  * Spell correction and synonym handling                                |
|  * Search analytics (what users search, click-through rates)            |
|                                                                         |
|  ENDPOINTS:                                                             |
|  GET /search?q=laptop&brand=dell&price=50000-100000&sort=relevance      |
|  GET /search/suggest?q=lapt          (autocomplete)                     |
|  GET /search/trending                (popular searches)                 |
|                                                                         |
|  -----------------------------------------------------------------      |
|  BACKEND: Elasticsearch cluster                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  WHY ELASTICSEARCH?                                                     |
|  * Inverted index enables full-text search in ~50ms vs seconds          |
|    with SQL LIKE. At 50M products, SQL LIKE '%laptop%' does a           |
|    full table scan — Elasticsearch looks up "laptop" in the             |
|    inverted index in O(1) and returns matching doc IDs.                 |
|  * Built-in fuzzy matching (typo tolerance): "laptp" still finds        |
|    "laptop" via Levenshtein distance (edit distance <= 2).              |
|  * Faceted aggregations: returns filter counts (e.g., "Dell: 342,       |
|    HP: 218") in the SAME query — no separate COUNT(*) queries.          |
|  * Synonym expansion: "laptop" also matches "notebook", "MacBook".      |
|    Configured per-index without code changes.                           |
|  * BM25 relevance scoring: ranks results by term frequency,             |
|    inverse document frequency, and field length. Title matches          |
|    score higher than description matches via field boosting.            |
|  * WHY NOT MongoDB text index? MongoDB text search lacks faceted        |
|    aggregations, fuzzy matching, and custom scoring. At e-commerce      |
|    scale (50M+ docs, 10K+ QPS), ES is 10-50x faster for complex         |
|    search queries.                                                      |
|                                                                         |
|  -----------------------------------------------------------------      |
|  ELASTICSEARCH INDEX DESIGN                                             |
|  -----------------------------------------------------------------      |
|                                                                         |
|  Index: products                                                        |
|  +---------------------------------------------------------------+      |
|  | Field             | Type      | Purpose                       |      |
|  +-------------------+-----------+-------------------------------+      |
|  | title             | text      | Full-text search (boosted 3x) |      |
|  | title.keyword     | keyword   | Exact match, sorting          |      |
|  | description       | text      | Full-text search (boosted 1x) |      |
|  | brand             | keyword   | Filter + facet aggregation    |      |
|  | category_path     | keyword   | Hierarchical filter           |      |
|  | price             | float     | Range filter + sorting        |      |
|  | rating_avg        | float     | Filter + sorting              |      |
|  | rating_count      | integer   | Popularity signal for ranking |      |
|  | in_stock          | boolean   | Filter (hide out-of-stock)    |      |
|  | tags              | keyword[] | Multi-value filter            |      |
|  | suggest           | completion| Autocomplete (FST-based)      |      |
|  | created_at        | date      | "New arrivals" sorting        |      |
|  +-------------------+-----------+-------------------------------+      |
|                                                                         |
|  WHY THIS MAPPING?                                                      |
|  * "text" fields are analyzed (tokenized, lowercased, stemmed)          |
|    for full-text search. "keyword" fields are stored as-is for          |
|    exact match filters and aggregations.                                |
|  * title has BOTH text + keyword (multi-field) so the same field        |
|    supports full-text search AND exact sorting.                         |
|  * "completion" type for suggest uses an FST (finite state              |
|    transducer) — an in-memory data structure that returns               |
|    prefix matches in O(prefix_length), not O(n_documents).              |
|                                                                         |
|  -----------------------------------------------------------------      |
|  SEARCH QUERY FLOW                                                      |
|  -----------------------------------------------------------------      |
|                                                                         |
|  User types "dell laptop 16gb" and selects price: 50K-100K              |
|                                                                         |
|  Step 1: QUERY PARSING                                                  |
|    Raw query: "dell laptop 16gb"                                        |
|    -> Tokenize: ["dell", "laptop", "16gb"]                              |
|    -> Spell check: no corrections needed                                |
|    -> Synonym expand: "laptop" -> ["laptop", "notebook"]                |
|                                                                         |
|  Step 2: ELASTICSEARCH QUERY (simplified)                               |
|  {                                                                      |
|    "query": {                                                           |
|      "bool": {                                                          |
|        "must": [                                                        |
|          { "multi_match": {                                             |
|              "query": "dell laptop notebook 16gb",                      |
|              "fields": ["title^3", "description", "brand^2"],           |
|              "type": "best_fields",                                     |
|              "fuzziness": "AUTO"                                        |
|          }}                                                             |
|        ],                                                               |
|        "filter": [                                                      |
|          { "range": { "price": { "gte": 50000, "lte": 100000 }}},       |
|          { "term": { "in_stock": true }}                                |
|        ]                                                                |
|      }                                                                  |
|    },                                                                   |
|    "aggs": {                                                            |
|      "brands":    { "terms": { "field": "brand", "size": 20 }},         |
|      "price_ranges": { "range": { "field": "price",                     |
|        "ranges": [{"to":25000},{"from":25000,"to":50000},               |
|                   {"from":50000,"to":100000},{"from":100000}]           |
|      }},                                                                |
|      "avg_rating": { "avg": { "field": "rating_avg" }}                  |
|    }                                                                    |
|  }                                                                      |
|                                                                         |
|  WHY THIS QUERY STRUCTURE?                                              |
|  * "must" affects scoring (relevant results first).                     |
|    "filter" does NOT affect scoring (just yes/no) and is CACHED         |
|    by ES — repeated price range filters are instant.                    |
|  * multi_match searches title, description, brand in one query.         |
|    "^3" boosts title matches 3x (title match > description match).      |
|  * "fuzziness: AUTO" = edit distance 1 for 3-5 char terms, 2 for        |
|    6+ char terms. Handles typos without manual configuration.           |
|  * Aggregations ("aggs") compute filter sidebar counts in the           |
|    SAME request — no additional round-trips.                            |
|                                                                         |
|  Step 3: RESULT RANKING                                                 |
|    Base score: BM25 (term frequency * inverse doc frequency)            |
|    + Field boost: title match (3x) > brand (2x) > description (1x)      |
|    + Business boost: promoted/sponsored products get score bump         |
|    + Popularity signal: higher rating_count = slight score boost        |
|    Final: sorted by _score descending                                   |
|                                                                         |
|  Step 4: RESPONSE (20-50ms typical)                                     |
|    { hits: [...top 20 products...],                                     |
|      facets: { brands: {Dell:342, HP:218}, price_ranges: {...} },       |
|      total: 1560,                                                       |
|      suggestions: ["dell laptop 16gb ram", "dell laptop i7"] }          |
|                                                                         |
|  -----------------------------------------------------------------      |
|  AUTOCOMPLETE / TYPEAHEAD                                               |
|  -----------------------------------------------------------------      |
|                                                                         |
|  User types: "lap" -> suggestions appear in <100ms                      |
|                                                                         |
|  IMPLEMENTATION:                                                        |
|  * ES "completion" suggester uses FST (finite state transducer),        |
|    an in-memory data structure built at index time.                     |
|  * FST maps prefixes to completions in O(prefix_length) time.           |
|    Unlike a LIKE 'lap%' query that scans all 50M products.              |
|  * Weighted by popularity: "laptop" (weight: 50000) ranks above         |
|    "lamp" (weight: 800) for prefix "la".                                |
|  * Context-aware: can filter suggestions by category so "lap" in        |
|    Electronics shows "laptop" but in Home shows "lap desk".             |
|                                                                         |
|  ADDITIONAL LAYER: Popular/trending queries stored in Redis             |
|  sorted set. Top queries updated hourly from search analytics.          |
|  Served directly from Redis if prefix matches — avoids hitting          |
|  ES for the most common searches.                                       |
|                                                                         |
|  -----------------------------------------------------------------      |
|  CACHING STRATEGY                                                       |
|  -----------------------------------------------------------------      |
|                                                                         |
|  * L1 CACHE (Redis, TTL: 60s):                                          |
|    Key: search:{hash(query + filters + sort + page)}                    |
|    Identical searches by different users hit cache.                     |
|    WHY 60s TTL? Balances freshness (new products, price changes)        |
|    vs load reduction. 60s means max 1 ES query/min per unique           |
|    search — at 10K QPS that's 10K cache hits per ES query.              |
|                                                                         |
|  * L2 CACHE (ES internal query cache):                                  |
|    ES auto-caches filter clauses. Repeated "in_stock: true" or          |
|    "price: 50K-100K" filters are served from bitset cache.              |
|                                                                         |
|  * AUTOCOMPLETE CACHE (Redis, TTL: 5min):                               |
|    Top 1000 prefixes (2-3 chars) pre-cached. Covers ~80% of             |
|    autocomplete requests without hitting ES.                            |
|                                                                         |
|  -----------------------------------------------------------------      |
|  DATA SYNC: HOW PRODUCTS REACH ELASTICSEARCH                            |
|  -----------------------------------------------------------------      |
|                                                                         |
|  MongoDB (source of truth) --> CDC --> Kafka --> ES Consumer            |
|                                                                         |
|  * WHY CDC + KAFKA (not direct writes)?                                 |
|    Product catalog is updated by sellers (price changes, new            |
|    listings, stock updates). Writing to both MongoDB AND ES             |
|    in the same request is fragile (what if ES write fails?).            |
|    CDC captures every MongoDB change as an event in Kafka.              |
|    ES consumer reads events and updates the index.                      |
|    If ES consumer falls behind, Kafka retains events (7 days)           |
|    — consumer catches up without data loss.                             |
|                                                                         |
|  * LATENCY: Product change visible in search within 1-5 seconds         |
|    (near real-time). Acceptable for e-commerce — users don't            |
|    expect a new listing to appear in search within milliseconds.        |
|                                                                         |
|  * FULL REINDEX: Periodically (weekly) rebuild the entire ES            |
|    index from MongoDB to fix any drift. Zero-downtime via               |
|    index aliasing: build new index, swap alias, delete old.             |
|                                                                         |
|  -----------------------------------------------------------------      |
|  PERSONALIZATION                                                        |
|  -----------------------------------------------------------------      |
|                                                                         |
|  Search results personalized based on:                                  |
|  * Purchase history: user bought Dell laptops -> boost Dell             |
|  * Browsing history: recently viewed Gaming category -> boost           |
|  * Location: show products available in user's delivery zone            |
|  * Implemented via function_score query in ES — applies user            |
|    preference weights on top of BM25 base score.                        |
|                                                                         |
|  -----------------------------------------------------------------      |
|  SCALE CONSIDERATIONS                                                   |
|  -----------------------------------------------------------------      |
|                                                                         |
|  * 50M products, ~2KB per doc = ~100GB index                            |
|  * 3 primary shards + 2 replicas = 5 copies (read throughput)           |
|  * 10K search QPS: replicas handle parallel reads                       |
|  * Autocomplete: 100K QPS (prefix queries are cheap — FST is            |
|    in-memory, no disk I/O)                                              |
|  * Cluster: 6-9 nodes (3 master-eligible, 3-6 data nodes)               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CART SERVICE

```
+--------------------------------------------------------------------------+
|                                                                          |
|  CART SERVICE                                                            |
|                                                                          |
|  RESPONSIBILITIES:                                                       |
|  * Manage shopping cart                                                  |
|  * Persist cart across sessions                                          |
|  * Handle cart merging (guest > logged in)                               |
|  * Price updates                                                         |
|                                                                          |
|  ENDPOINTS:                                                              |
|  GET    /cart                                                            |
|  POST   /cart/items                                                      |
|  PUT    /cart/items/{id}                                                 |
|  DELETE /cart/items/{id}                                                 |
|  POST   /cart/apply-coupon                                               |
|                                                                          |
|  STORAGE: Redis (primary) + PostgreSQL (backup)                          |
|  * WHY REDIS PRIMARY? Cart is accessed on every page view and            |
|    updated frequently (add/remove/quantity change). Redis gives          |
|    sub-ms reads/writes vs ~5-10ms for PostgreSQL. Hash structure         |
|    maps naturally to cart:{user_id}. TTL auto-cleans abandoned           |
|    carts (30-day expiry) without running cleanup jobs.                   |
|  * WHY POSTGRESQL BACKUP? Redis is volatile - if Redis restarts,         |
|    cart data is lost. Async write-behind to PostgreSQL ensures           |
|    cart survives Redis failures. Also needed for analytics               |
|    (abandoned cart reports, conversion tracking).                        |
|                                                                          |
|  CART STRUCTURE IN REDIS:                                                |
|  +-------------------------------------------------------------------+   |
|  | Key: cart:{user_id}                                               |   |
|  | Value: {                                                          |   |
|  |   "items": [                                                      |   |
|  |     {                                                             |   |
|  |       "product_id": "prod_123",                                   |   |
|  |       "quantity": 2,                                              |   |
|  |       "price": 999.00,                                            |   |
|  |       "added_at": "2024-01-15T10:00:00Z"                          |   |
|  |     }                                                             |   |
|  |   ],                                                              |   |
|  |   "coupon": "SAVE10",                                             |   |
|  |   "updated_at": "2024-01-15T10:30:00Z"                            |   |
|  | }                                                                 |   |
|  | TTL: 30 days                                                      |   |
|  +-------------------------------------------------------------------+   |
|                                                                          |
|  CART CHALLENGES:                                                        |
|  * Price changes: Recalculate on checkout                                |
|  * Out of stock: Notify user on checkout                                 |
|  * Guest carts: Merge when user logs in                                  |
|                                                                          |
+--------------------------------------------------------------------------+
```

### INVENTORY SERVICE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  INVENTORY SERVICE (Critical!)                                          |
|                                                                         |
|  RESPONSIBILITIES:                                                      |
|  * Track stock levels per product per warehouse                         |
|  * Reserve inventory during checkout                                    |
|  * Release inventory if order cancelled                                 |
|  * Prevent overselling                                                  |
|                                                                         |
|  ENDPOINTS:                                                             |
|  GET  /inventory/{product_id}                                           |
|  POST /inventory/reserve                                                |
|  POST /inventory/release                                                |
|  POST /inventory/deduct (on shipment)                                   |
|                                                                         |
|  DATABASE: PostgreSQL (ACID for inventory transactions)                 |
|                                                                         |
|  INVENTORY STATES:                                                      |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |  +--------------+     +--------------+     +------------------+  |   |
|  |  |  AVAILABLE   |---->|   RESERVED   |---->|   SOLD           |  |   |
|  |  |   (100)      |     |    (10)      |     |    (5)           |  |   |
|  |  +--------------+     +--------------+     +------------------+  |   |
|  |         ^                    |                                   |   |
|  |         |                    | Order cancelled                   |   |
|  |         +--------------------+ (Release)                         |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  Total Stock = Available + Reserved + Sold                              |
|                                                                         |
|  MULTI-WAREHOUSE:                                                       |
|  +------------------------------------------------------------------+   |
|  | product_id | warehouse_id | available | reserved | sold          |   |
|  |----------------------------------------------------------------  |   |
|  | PROD_123   | WH_MUMBAI    |    50     |    5     |  100          |   |
|  | PROD_123   | WH_DELHI     |    30     |    2     |   75          |   |
|  | PROD_123   | WH_BANGALORE |    20     |    0     |   50          |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### ORDER SERVICE

```
+--------------------------------------------------------------------------+
|                                                                          |
|  ORDER SERVICE (Critical!)                                               |
|                                                                          |
|  RESPONSIBILITIES:                                                       |
|  * Create orders from cart                                               |
|  * Order lifecycle management                                            |
|  * Order history                                                         |
|  * Cancellation and returns                                              |
|                                                                          |
|  ENDPOINTS:                                                              |
|  POST /orders (create order)                                             |
|  GET  /orders/{id}                                                       |
|  GET  /orders (user's orders)                                            |
|  POST /orders/{id}/cancel                                                |
|  POST /orders/{id}/return                                                |
|                                                                          |
|  ORDER STATES:                                                           |
|  +-------------------------------------------------------------------+   |
|  |                                                                   |   |
|  |  CREATED > PAYMENT_PENDING > CONFIRMED > PROCESSING               |   |
|  |                                              v                    |   |
|  |                                          SHIPPED                  |   |
|  |                                              v                    |   |
|  |                                          DELIVERED                |   |
|  |                                              v                    |   |
|  |                                          COMPLETED                |   |
|  |                                                                   |   |
|  |  At any point: > CANCELLED or RETURNED                            |   |
|  |                                                                   |   |
|  +-------------------------------------------------------------------+   |
|                                                                          |
|  DATABASE: PostgreSQL                                                    |
|  * WHY POSTGRESQL? Orders involve money - needs strict ACID              |
|    guarantees (no partial orders, no lost payments). Relational          |
|    model fits naturally: order->order_items->status_history.             |
|    Supports complex queries (order reports, seller payouts,              |
|    refund joins). JSONB column for flexible metadata without             |
|    sacrificing transactions.                                             |
|                                                                          |
|  * orders (main order info)                                              |
|  * order_items (line items)                                              |
|  * order_status_history (audit trail)                                    |
|                                                                          |
+--------------------------------------------------------------------------+
```

### PAYMENT SERVICE

```
+--------------------------------------------------------------------------+
|                                                                          |
|  PAYMENT SERVICE                                                         |
|                                                                          |
|  RESPONSIBILITIES:                                                       |
|  * Payment processing                                                    |
|  * Multiple payment methods                                              |
|  * Refunds                                                               |
|  * Payment reconciliation                                                |
|                                                                          |
|  INTEGRATIONS:                                                           |
|  * Stripe, Razorpay, PayU (payment gateways)                             |
|  * UPI (India)                                                           |
|  * Wallets (PayPal, Paytm)                                               |
|                                                                          |
|  CRITICAL FEATURES:                                                      |
|  * Idempotency keys for retries                                          |
|  * PCI-DSS compliance                                                    |
|  * Fraud detection integration                                           |
|                                                                          |
|  DATABASE: PostgreSQL                                                    |
|  * WHY POSTGRESQL? Payments are financial records - ACID is              |
|    non-negotiable (double-charge prevention via unique                   |
|    idempotency_key constraint). Need strong consistency for              |
|    refund reconciliation. Audit compliance requires durable,             |
|    tamper-evident storage. Foreign keys enforce referential              |
|    integrity (payment->order linkage).                                   |
|                                                                          |
|  * payments (with idempotency_key)                                       |
|  * refunds                                                               |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 2.3: CHECKOUT FLOW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CHECKOUT SEQUENCE DIAGRAM                                              |
|                                                                         |
|  User        API GW      Cart     Inventory    Payment     Order        |
|   |            |          |          |           |          |           |
|   | Checkout   |          |          |           |          |           |
|   |----------->|          |          |           |          |           |
|   |            | Get Cart |          |           |          |           |
|   |            |--------->|          |           |          |           |
|   |            |<---------|          |           |          |           |
|   |            |          |          |           |          |           |
|   |            | Reserve Inventory   |           |          |           |
|   |            |--------------------->           |          |           |
|   |            |<---------------------           |          |           |
|   |            |     (success/fail)  |           |          |           |
|   |            |          |          |           |          |           |
|   |            | Create Order (PENDING)          |          |           |
|   |            |--------------------------------------------->          |
|   |            |<----------------------------------------------         |
|   |            |          |          |           |          |           |
|   |            | Process Payment     |           |          |           |
|   |            |--------------------------------->          |           |
|   | Payment UI |          |          |           |          |           |
|   |<-----------|          |          |           |          |           |
|   | Complete   |          |          |           |          |           |
|   |----------->|          |          |           |          |           |
|   |            |          |          | Callback  |          |           |
|   |            |<---------------------------------          |           |
|   |            |          |          |           |          |           |
|   |            | Update Order (CONFIRMED)        |          |           |
|   |            |--------------------------------------------->          |
|   |            |          |          |           |          |           |
|   | Confirmation|         |          |           |          |           |
|   |<-----------|          |          |           |          |           |
|   |            |          |          |           |          |           |
|                                                                         |
|  IF PAYMENT FAILS:                                                      |
|  * Order marked as PAYMENT_FAILED                                       |
|  * Inventory released                                                   |
|  * User notified                                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.4: TECHNOLOGY CHOICES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TECHNOLOGY STACK                                                       |
|                                                                         |
|  COMPONENT              | TECHNOLOGY        | REASONING                 |
|  ===================================================================    |
|  API Gateway            | Kong / Envoy      | Rate limiting, routing    |
|  Backend Services       | Java/Go           | Performance, ecosystem    |
|  Product Catalog        | MongoDB           | Flexible schema           |
|  Orders/Payments        | PostgreSQL        | ACID transactions         |
|  Cart/Sessions          | Redis             | Speed, TTL                |
|  Search                 | Elasticsearch     | Full-text, facets         |
|  Message Queue          | Kafka             | Event-driven, replay      |
|  CDN                    | CloudFront        | Global edge               |
|  Object Storage         | S3                | Product images            |
|  Container              | Kubernetes        | Scaling, orchestration    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1: CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ARCHITECTURE - KEY TAKEAWAYS                                           |
|                                                                         |
|  CORE SERVICES                                                          |
|  -------------                                                          |
|  * Catalog: MongoDB for flexible product schema                         |
|  * Inventory: PostgreSQL for ACID guarantees                            |
|  * Orders: PostgreSQL with event sourcing                               |
|  * Cart: Redis for speed                                                |
|  * Search: Elasticsearch for performance                                |
|                                                                         |
|  DATA FLOW                                                              |
|  ---------                                                              |
|  * Checkout: Cart > Inventory > Order > Payment                         |
|  * Search: MongoDB > CDC > Kafka > Elasticsearch                        |
|  * Events: All services > Kafka > Consumers                             |
|                                                                         |
|  CRITICAL POINTS                                                        |
|  ---------------                                                        |
|  * Inventory reservation prevents overselling                           |
|  * Event-driven for loose coupling                                      |
|  * Multiple payment gateway fallback                                    |
|                                                                         |
|  INTERVIEW TIP                                                          |
|  -------------                                                          |
|  Draw the checkout flow sequence diagram.                               |
|  Explain what happens if payment fails.                                 |
|  Discuss inventory reservation vs deduction.                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 2
