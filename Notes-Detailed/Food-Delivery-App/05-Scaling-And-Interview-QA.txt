================================================================================
FOOD DELIVERY PLATFORM SYSTEM DESIGN
================================================================================

PART 5: SCALING, RELIABILITY & INTERVIEW Q&A
================================================================================


================================================================================
SECTION 1: SCALING STRATEGIES
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  DATABASE SHARDING                                                     │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  USERS TABLE: Shard by user_id                                │  │
    │  │  • Hash(user_id) % num_shards                                 │  │
    │  │  • User data rarely joins with other users                    │  │
    │  │                                                                 │  │
    │  │  ORDERS TABLE: Shard by user_id                               │  │
    │  │  • Co-located with user for order history queries             │  │
    │  │  • Challenge: Restaurant needs cross-shard query              │  │
    │  │  • Solution: Maintain denormalized restaurant_orders table   │  │
    │  │                                                                 │  │
    │  │  RESTAURANTS TABLE: Shard by city_id                          │  │
    │  │  • Geographically co-located data                             │  │
    │  │  • City-based queries don't cross shards                     │  │
    │  │                                                                 │  │
    │  │  DELIVERY_PARTNERS TABLE: Shard by city_id                   │  │
    │  │  • Partners operate within a city                             │  │
    │  │  • Assignment queries are city-local                          │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  CACHING STRATEGY                                                      │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Layer 1: CDN                                                  │  │
    │  │  ───────────────                                                │  │
    │  │  • Food images (90% of bandwidth)                             │  │
    │  │  • Restaurant logos                                           │  │
    │  │  • Static assets                                               │  │
    │  │  • TTL: 24 hours                                              │  │
    │  │                                                                 │  │
    │  │  Layer 2: Application Cache (Redis)                           │  │
    │  │  ─────────────────────────────────────                          │  │
    │  │                                                                 │  │
    │  │  What to cache:                                                │  │
    │  │  • Restaurant menus (read heavy, rarely updated)              │  │
    │  │    Key: menu:{restaurant_id}                                  │  │
    │  │    TTL: 1 hour + invalidation on update                       │  │
    │  │                                                                 │  │
    │  │  • Restaurant details                                         │  │
    │  │    Key: restaurant:{id}                                       │  │
    │  │    TTL: 15 minutes                                            │  │
    │  │                                                                 │  │
    │  │  • User sessions                                               │  │
    │  │    Key: session:{token}                                       │  │
    │  │    TTL: 24 hours                                              │  │
    │  │                                                                 │  │
    │  │  • Active coupons                                              │  │
    │  │    Key: coupons:active                                        │  │
    │  │    TTL: 5 minutes                                             │  │
    │  │                                                                 │  │
    │  │  • Partner locations (real-time)                              │  │
    │  │    Key: partner:locations (GEO)                               │  │
    │  │    TTL: None (continuously updated)                           │  │
    │  │                                                                 │  │
    │  │  What NOT to cache:                                            │  │
    │  │  • Order data (strong consistency needed)                     │  │
    │  │  • Payment transactions                                       │  │
    │  │  • Real-time availability (changes too fast)                 │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  MESSAGE QUEUE ARCHITECTURE                                           │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  KAFKA TOPICS:                                                 │  │
    │  │                                                                 │  │
    │  │  order-events                                                  │  │
    │  │  ├── order-placed                                             │  │
    │  │  ├── order-confirmed                                          │  │
    │  │  ├── order-preparing                                          │  │
    │  │  ├── order-ready                                              │  │
    │  │  ├── order-picked-up                                          │  │
    │  │  ├── order-delivered                                          │  │
    │  │  └── order-cancelled                                          │  │
    │  │                                                                 │  │
    │  │  delivery-events                                               │  │
    │  │  ├── partner-assigned                                         │  │
    │  │  ├── partner-reached-restaurant                               │  │
    │  │  └── partner-near-customer                                    │  │
    │  │                                                                 │  │
    │  │  location-updates (High throughput topic)                     │  │
    │  │  • Partitioned by partner_id % 100                            │  │
    │  │  • 100 partitions for parallelism                             │  │
    │  │  • Retention: 4 hours                                         │  │
    │  │                                                                 │  │
    │  │  notification-events                                           │  │
    │  │  ├── push                                                     │  │
    │  │  ├── sms                                                      │  │
    │  │  └── email                                                    │  │
    │  │                                                                 │  │
    │  │  CONSUMER GROUPS:                                              │  │
    │  │  • notification-service (consumes order-events)               │  │
    │  │  • analytics-service (consumes all events)                   │  │
    │  │  • tracking-service (consumes location-updates)              │  │
    │  │  • delivery-service (consumes order-confirmed)               │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 2: RELIABILITY & FAULT TOLERANCE
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  HANDLING FAILURES                                                     │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  1. DATABASE FAILURE                                           │  │
    │  │  ─────────────────────                                          │  │
    │  │                                                                 │  │
    │  │  Primary fails:                                                │  │
    │  │  • Automatic failover to replica (< 30 seconds)               │  │
    │  │  • Application retries with exponential backoff               │  │
    │  │  • New primary promoted                                        │  │
    │  │                                                                 │  │
    │  │  Read replica fails:                                           │  │
    │  │  • Traffic routed to other replicas                           │  │
    │  │  • No impact on writes                                        │  │
    │  │                                                                 │  │
    │  │  ────────────────────────────────────────────────────────────  │  │
    │  │                                                                 │  │
    │  │  2. REDIS FAILURE                                              │  │
    │  │  ──────────────────                                             │  │
    │  │                                                                 │  │
    │  │  Cache miss behavior:                                          │  │
    │  │  • Fall back to database                                      │  │
    │  │  • Serve stale data if DB also slow (circuit breaker)        │  │
    │  │                                                                 │  │
    │  │  Session store fails:                                          │  │
    │  │  • Use Redis Cluster (automatic failover)                    │  │
    │  │  • Or fallback to JWT tokens (stateless)                     │  │
    │  │                                                                 │  │
    │  │  Location cache fails:                                         │  │
    │  │  • Critical! Need Redis Cluster with replicas                │  │
    │  │  • Maintain backup in secondary region                        │  │
    │  │                                                                 │  │
    │  │  ────────────────────────────────────────────────────────────  │  │
    │  │                                                                 │  │
    │  │  3. KAFKA FAILURE                                              │  │
    │  │  ──────────────────                                             │  │
    │  │                                                                 │  │
    │  │  Broker fails:                                                 │  │
    │  │  • Partition leadership moves to replica                      │  │
    │  │  • Producers/consumers auto-reconnect                         │  │
    │  │                                                                 │  │
    │  │  Consumer lag:                                                 │  │
    │  │  • Monitor consumer lag                                       │  │
    │  │  • Auto-scale consumers                                       │  │
    │  │  • Dead letter queue for failed messages                     │  │
    │  │                                                                 │  │
    │  │  ────────────────────────────────────────────────────────────  │  │
    │  │                                                                 │  │
    │  │  4. PAYMENT GATEWAY FAILURE                                    │  │
    │  │  ────────────────────────────                                   │  │
    │  │                                                                 │  │
    │  │  Primary gateway (Razorpay) fails:                            │  │
    │  │  • Switch to backup gateway (Stripe/PayU)                    │  │
    │  │  • Offer COD as fallback                                      │  │
    │  │  • Notify customer of payment options                        │  │
    │  │                                                                 │  │
    │  │  Webhook not received:                                         │  │
    │  │  • Poll gateway for payment status                           │  │
    │  │  • Reconciliation job every 5 minutes                        │  │
    │  │                                                                 │  │
    │  │  ────────────────────────────────────────────────────────────  │  │
    │  │                                                                 │  │
    │  │  5. SERVICE FAILURE                                            │  │
    │  │  ────────────────────                                           │  │
    │  │                                                                 │  │
    │  │  Circuit Breaker Pattern:                                      │  │
    │  │  • If service fails > 50% in 30 seconds → OPEN circuit       │  │
    │  │  • Return cached/default response                             │  │
    │  │  • Try again after 60 seconds → HALF-OPEN                    │  │
    │  │  • If success → CLOSED                                        │  │
    │  │                                                                 │  │
    │  │  Graceful Degradation:                                         │  │
    │  │  • Search fails → Show cached popular restaurants            │  │
    │  │  • ETA fails → Show "30-45 mins" estimate                    │  │
    │  │  • Recommendations fail → Show all restaurants               │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  DATA CONSISTENCY                                                      │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  STRONG CONSISTENCY REQUIRED:                                  │  │
    │  │  • Order creation (no double orders)                          │  │
    │  │  • Payment transactions                                       │  │
    │  │  • Inventory updates                                          │  │
    │  │  • Partner assignment (no double assignment)                  │  │
    │  │                                                                 │  │
    │  │  Implementation:                                               │  │
    │  │  • Database transactions (ACID)                               │  │
    │  │  • Distributed locks (Redis SETNX)                           │  │
    │  │  • Idempotency keys                                           │  │
    │  │                                                                 │  │
    │  │  ────────────────────────────────────────────────────────────  │  │
    │  │                                                                 │  │
    │  │  EVENTUAL CONSISTENCY OK:                                      │  │
    │  │  • Ratings and reviews                                        │  │
    │  │  • Analytics data                                              │  │
    │  │  • Search index updates                                       │  │
    │  │  • Partner location (few seconds delay OK)                   │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  IDEMPOTENCY                                                           │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Problem: Network retries can cause duplicate operations      │  │
    │  │                                                                 │  │
    │  │  Solution: Idempotency Keys                                   │  │
    │  │                                                                 │  │
    │  │  POST /api/orders                                              │  │
    │  │  Headers:                                                       │  │
    │  │    Idempotency-Key: uuid-abc-123-xyz                          │  │
    │  │                                                                 │  │
    │  │  Server:                                                        │  │
    │  │  1. Check Redis: idempotency:{key}                            │  │
    │  │  2. If exists → return cached response                        │  │
    │  │  3. If not → process request                                  │  │
    │  │  4. Store: idempotency:{key} = response (TTL: 24 hours)      │  │
    │  │  5. Return response                                            │  │
    │  │                                                                 │  │
    │  │  Critical for:                                                 │  │
    │  │  • Order placement                                            │  │
    │  │  • Payment processing                                         │  │
    │  │  • Partner assignment                                         │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 3: MONITORING & OBSERVABILITY
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  KEY METRICS TO MONITOR                                                │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  BUSINESS METRICS:                                             │  │
    │  │  • Orders per minute (by city)                                │  │
    │  │  • GMV (Gross Merchandise Value)                              │  │
    │  │  • Average order value                                        │  │
    │  │  • Conversion rate (search → order)                          │  │
    │  │  • Cancellation rate                                          │  │
    │  │                                                                 │  │
    │  │  OPERATIONAL METRICS:                                          │  │
    │  │  • Restaurant acceptance rate                                 │  │
    │  │  • Average delivery time                                      │  │
    │  │  • Partner utilization (orders per partner)                  │  │
    │  │  • Partner online/offline ratio                               │  │
    │  │  • ETA accuracy                                                │  │
    │  │                                                                 │  │
    │  │  TECHNICAL METRICS:                                            │  │
    │  │  • API latency (p50, p95, p99)                               │  │
    │  │  • Error rates by endpoint                                    │  │
    │  │  • Database query times                                       │  │
    │  │  • Redis hit rate                                              │  │
    │  │  • Kafka consumer lag                                         │  │
    │  │  • WebSocket connections                                      │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  ALERTS                                                                │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  CRITICAL (Page on-call immediately):                         │  │
    │  │  • Order creation failure rate > 1%                           │  │
    │  │  • Payment success rate < 95%                                 │  │
    │  │  • Database master down                                       │  │
    │  │  • Partner assignment taking > 5 minutes                     │  │
    │  │                                                                 │  │
    │  │  WARNING (Investigate soon):                                  │  │
    │  │  • API latency p99 > 500ms                                   │  │
    │  │  • Cache hit rate < 80%                                       │  │
    │  │  • Kafka consumer lag > 10,000                                │  │
    │  │  • Restaurant rejection rate > 20%                            │  │
    │  │                                                                 │  │
    │  │  INFO (Monitor trend):                                        │  │
    │  │  • Orders below/above hourly average                         │  │
    │  │  • New restaurant onboarded                                   │  │
    │  │  • Partner going offline                                      │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 4: INTERVIEW QUICK REFERENCE
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  KEY TALKING POINTS                                                    │
    │                                                                         │
    │  1. THREE-SIDED MARKETPLACE                                           │
    │     • Customers, Restaurants, Delivery Partners                       │
    │     • Each has different needs and apps                               │
    │     • Platform balances supply and demand                             │
    │                                                                         │
    │  2. LOCATION SERVICE (Most Unique Part!)                             │
    │     • 75K location updates/second                                    │
    │     • Redis GEO for storage and proximity queries                    │
    │     • Geohash sharding for horizontal scaling                        │
    │     • WebSocket for live tracking to customers                       │
    │                                                                         │
    │  3. PARTNER ASSIGNMENT ALGORITHM                                      │
    │     • Multi-factor scoring: distance, rating, workload, fairness    │
    │     • Sequential requests with timeout                               │
    │     • Retry with expanding radius                                    │
    │                                                                         │
    │  4. ORDER STATE MACHINE                                               │
    │     • Clear states: PLACED → CONFIRMED → PREPARING → READY →        │
    │       PICKED_UP → DELIVERED                                          │
    │     • Event-driven architecture (Kafka)                              │
    │     • Each state change triggers notifications                       │
    │                                                                         │
    │  5. SEARCH                                                             │
    │     • Elasticsearch for full-text + geo search                       │
    │     • Ranking: relevance, distance, rating, personalization         │
    │     • Near real-time sync via CDC/Kafka                             │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  COMMON INTERVIEW QUESTIONS                                           │
    │                                                                         │
    │  Q: How do you find the nearest available delivery partner?          │
    │  A: Redis GEO with GEORADIUS query around restaurant location.       │
    │     Filter by status=ONLINE and current_orders < max. Score by       │
    │     distance, rating, workload. Send sequential requests.            │
    │                                                                         │
    │  Q: How do you handle 75K location updates per second?               │
    │  A: Use Redis (in-memory, O(logN) for geo). Shard by geohash        │
    │     prefix. Location service is stateless, horizontally scaled.      │
    │     Kafka for streaming to tracking service.                         │
    │                                                                         │
    │  Q: How do you show live tracking to customer?                       │
    │  A: WebSocket connection when customer opens tracking. Server        │
    │     consumes location updates from Kafka, pushes to relevant        │
    │     WebSocket connections. Scale with consistent hashing.            │
    │                                                                         │
    │  Q: How do you calculate ETA?                                        │
    │  A: ETA = Prep time + Partner→Restaurant + Pickup buffer +          │
    │     Restaurant→Customer. Prep time from restaurant settings.         │
    │     Travel time from Google Maps API. Dynamic updates every 30s.    │
    │                                                                         │
    │  Q: How do you handle surge pricing?                                 │
    │  A: Calculate demand/supply ratio per zone. If ratio > threshold,   │
    │     apply multiplier to delivery fee. Show surge indicator to user.│
    │                                                                         │
    │  Q: How do you ensure order is not lost?                             │
    │  A: Write to MySQL first (durable). Then publish to Kafka.          │
    │     Idempotency keys prevent duplicates. Reconciliation jobs        │
    │     for any missed events.                                           │
    │                                                                         │
    │  Q: What if payment gateway fails?                                   │
    │  A: Multiple gateway integration. Fallback to backup gateway.       │
    │     COD as last resort. Poll for status if webhook missed.          │
    │     Reconciliation job matches orders with payments.                 │
    │                                                                         │
    │  Q: How do you scale the database?                                   │
    │  A: Shard orders by user_id (for order history). Shard restaurants │
    │     by city_id (for geo queries). Read replicas for heavy reads.   │
    │     Cache menus heavily (Redis).                                     │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  ARCHITECTURE SUMMARY                                                  │
    │                                                                         │
    │  Order Flow:                                                           │
    │  Customer App → API Gateway → Order Service → MySQL → Kafka          │
    │      → Restaurant App (confirm) → Delivery Service (assign)          │
    │      → Partner App (pickup) → Customer App (track)                   │
    │                                                                         │
    │  Location Flow:                                                        │
    │  Partner App → Location Service → Redis GEO + Kafka                  │
    │      → Tracking Service → WebSocket → Customer App                   │
    │                                                                         │
    │  Search Flow:                                                          │
    │  Customer App → Search Service → Elasticsearch → Rankings           │
    │      → Response with personalized results                            │
    │                                                                         │
    │  Key Numbers:                                                          │
    │  • 3M orders/day, 140 orders/second peak                            │
    │  • 75K location updates/second                                       │
    │  • 500K active delivery partners                                     │
    │  • 500K restaurant partners                                          │
    │  • 5000 searches/second peak                                         │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 4: ADVANCED TOPICS & REAL-WORLD PROBLEMS
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  FRAUD DETECTION & PREVENTION                                          │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  CUSTOMER FRAUD PATTERNS:                                      │  │
    │  │                                                                 │  │
    │  │  1. PROMO ABUSE                                                │  │
    │  │     • Same person creates multiple accounts for new user      │  │
    │  │       discounts                                                 │  │
    │  │     • Detection: Device fingerprint, phone number patterns,   │  │
    │  │       delivery address clustering, payment method linking     │  │
    │  │                                                                 │  │
    │  │  2. REFUND FRAUD                                               │  │
    │  │     • Claim "food never arrived" for free food                │  │
    │  │     • Detection: Refund rate per customer, GPS proof of       │  │
    │  │       delivery, photo verification at delivery               │  │
    │  │                                                                 │  │
    │  │  3. PAYMENT FRAUD                                              │  │
    │  │     • Stolen credit cards                                     │  │
    │  │     • Detection: Address verification, velocity checks,       │  │
    │  │       ML model for suspicious patterns                        │  │
    │  │                                                                 │  │
    │  │  RESTAURANT FRAUD:                                             │  │
    │  │  • Accept order → never prepare → keep platform's attention  │  │
    │  │  • Inflate prices vs in-store prices                          │  │
    │  │  • Detection: Completion rate, customer complaints, price     │  │
    │  │    comparison crawlers                                        │  │
    │  │                                                                 │  │
    │  │  DELIVERY PARTNER FRAUD:                                       │  │
    │  │  • GPS spoofing to fake deliveries                            │  │
    │  │  • Mark delivered without delivering                          │  │
    │  │  • Detection: GPS trajectory analysis, customer confirmation, │  │
    │  │    photo proof, ML anomaly detection                         │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  ML/AI FOR ETA PREDICTION                                             │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  FEATURES FOR ETA MODEL:                                       │  │
    │  │                                                                 │  │
    │  │  Restaurant features:                                          │  │
    │  │  • Historical prep time (per item, per day, per hour)        │  │
    │  │  • Current queue depth (pending orders)                       │  │
    │  │  • Staff availability                                         │  │
    │  │  • Item complexity                                            │  │
    │  │                                                                 │  │
    │  │  Delivery features:                                            │  │
    │  │  • Real-time traffic from Google Maps / HERE                 │  │
    │  │  • Weather conditions (rain = slower)                        │  │
    │  │  • Partner's current location & heading                      │  │
    │  │  • Historical delivery times for this route                  │  │
    │  │                                                                 │  │
    │  │  Contextual features:                                          │  │
    │  │  • Day of week, time of day                                   │  │
    │  │  • Special events (cricket match, festival)                  │  │
    │  │  • Building type (apartment vs house)                        │  │
    │  │                                                                 │  │
    │  │  Model: Gradient Boosting / Neural Network                    │  │
    │  │  Output: Predicted ETA with confidence interval               │  │
    │  │  Retraining: Daily with last 30 days of data                 │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  BATCHING ORDERS (Multi-Drop Delivery)                                │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Problem: Single delivery per trip is inefficient             │  │
    │  │                                                                 │  │
    │  │  Solution: Batch multiple orders to same delivery partner    │  │
    │  │                                                                 │  │
    │  │  ┌───────────────────────────────────────────────────────────┐│  │
    │  │  │                                                           ││  │
    │  │  │  Partner picks up from Restaurant A                      ││  │
    │  │  │       │                                                   ││  │
    │  │  │       ├──► Deliver to Customer 1 (on the way)           ││  │
    │  │  │       │                                                   ││  │
    │  │  │       └──► Deliver to Customer 2 (final)                ││  │
    │  │  │                                                           ││  │
    │  │  └───────────────────────────────────────────────────────────┘│  │
    │  │                                                                 │  │
    │  │  BATCHING ALGORITHM:                                           │  │
    │  │  • Wait 2-3 minutes after first order for potential batches   │  │
    │  │  • Match orders going in same direction                       │  │
    │  │  • Constraint: Second delivery ETA increase < 5 minutes      │  │
    │  │  • Incentivize partner with extra pay for batched deliveries │  │
    │  │                                                                 │  │
    │  │  STACKING FROM MULTIPLE RESTAURANTS:                           │  │
    │  │  • Pick up from Restaurant A, then Restaurant B               │  │
    │  │  • Constraint: Restaurants must be close (<1 km)             │  │
    │  │  • Food quality concern: Hot food cools if waiting           │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  DARK KITCHENS / CLOUD KITCHENS                                       │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  What: Kitchen-only restaurants (no dine-in)                  │  │
    │  │                                                                 │  │
    │  │  System Changes:                                               │  │
    │  │  • One physical kitchen → Multiple virtual brands             │  │
    │  │  • "Pizza Palace" and "Burger Barn" same kitchen            │  │
    │  │  • Inventory shared across brands                             │  │
    │  │  • Single partner pickup for multi-brand orders              │  │
    │  │                                                                 │  │
    │  │  Data Model:                                                   │  │
    │  │  kitchen_id → [brand_1, brand_2, brand_3]                    │  │
    │  │  brand shows as separate restaurant to customer              │  │
    │  │                                                                 │  │
    │  │  Benefits for Platform:                                        │  │
    │  │  • Better kitchen utilization                                 │  │
    │  │  • Lower food cost                                            │  │
    │  │  • Strategic placement in underserved areas                  │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  PEAK HOUR HANDLING (Surge Management)                                │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  PROBLEM: Dinner time (7-9 PM) = 5x normal traffic           │  │
    │  │                                                                 │  │
    │  │  SUPPLY-SIDE SOLUTIONS:                                        │  │
    │  │  • Partner incentives: "₹20 extra per order 7-9 PM"          │  │
    │  │  • Predict demand → pre-position partners in hot zones       │  │
    │  │  • Part-time partners for peak hours only                    │  │
    │  │                                                                 │  │
    │  │  DEMAND-SIDE SOLUTIONS:                                        │  │
    │  │  • Surge pricing on delivery fee                              │  │
    │  │  • "Order for later" with discount                           │  │
    │  │  • Hide restaurants with long wait times                     │  │
    │  │  • Show "Busy" badge, suggest alternatives                   │  │
    │  │                                                                 │  │
    │  │  TECHNICAL SOLUTIONS:                                          │  │
    │  │  • Auto-scale backend services (Kubernetes HPA)              │  │
    │  │  • Pre-warm caches before peak                               │  │
    │  │  • Degrade non-critical features (recommendations)           │  │
    │  │  • Read from replicas more aggressively                      │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  COLD START PROBLEM (New Restaurants)                                 │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Problem: New restaurant has no ratings, no order history     │  │
    │  │           → Ranking algorithm pushes them down → No orders    │  │
    │  │           → They leave platform                                │  │
    │  │                                                                 │  │
    │  │  Solutions:                                                    │  │
    │  │                                                                 │  │
    │  │  1. NEW RESTAURANT BOOST                                      │  │
    │  │     • First 2 weeks: Artificially boost ranking              │  │
    │  │     • Show "New" badge to attract curious users              │  │
    │  │                                                                 │  │
    │  │  2. SPECIAL PROMOTIONS                                        │  │
    │  │     • Platform-funded discounts for new restaurants          │  │
    │  │     • "Try something new" section                            │  │
    │  │                                                                 │  │
    │  │  3. QUALITY SIGNALS                                           │  │
    │  │     • Use aggregated ratings from Google/Yelp initially      │  │
    │  │     • Restaurant's social media presence                     │  │
    │  │     • Brand chain rating as default                          │  │
    │  │                                                                 │  │
    │  │  4. EXPLORATION VS EXPLOITATION                               │  │
    │  │     • Multi-armed bandit for ranking                         │  │
    │  │     • Occasionally show new restaurants to learn their      │  │
    │  │       true quality                                            │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  WEATHER IMPACT                                                        │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Rain creates perfect storm:                                   │  │
    │  │  • Demand ↑↑↑ (people don't want to go out)                  │  │
    │  │  • Supply ↓↓↓ (partners don't want to ride in rain)         │  │
    │  │                                                                 │  │
    │  │  System Response:                                              │  │
    │  │  1. Weather API integration (forecast + real-time)           │  │
    │  │  2. Proactive surge pricing                                   │  │
    │  │  3. Rain bonus for partners (₹15-30 extra per delivery)     │  │
    │  │  4. Increased ETA estimates                                   │  │
    │  │  5. Push notifications to partners: "High demand due to rain"│  │
    │  │  6. Pre-fetch menu caches (traffic spike coming)            │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  REAL-TIME INVENTORY SYNC                                             │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Problem: Customer orders item → Restaurant says "out of stock"│  │
    │  │           → Bad experience, cancellation                       │  │
    │  │                                                                 │  │
    │  │  Solutions:                                                    │  │
    │  │                                                                 │  │
    │  │  1. REAL-TIME POS INTEGRATION                                 │  │
    │  │     • Connect to restaurant's Point of Sale system            │  │
    │  │     • Sync inventory in real-time                            │  │
    │  │     • Works for chains with modern POS                       │  │
    │  │                                                                 │  │
    │  │  2. MANUAL TOGGLE (Small restaurants)                        │  │
    │  │     • Restaurant marks items unavailable in app              │  │
    │  │     • Often forgotten → stale data                           │  │
    │  │                                                                 │  │
    │  │  3. PREDICTIVE STOCK-OUT                                      │  │
    │  │     • ML model predicts when items run out                   │  │
    │  │     • Based on time of day, order volume, historical data   │  │
    │  │     • Auto-hide items likely to be unavailable              │  │
    │  │                                                                 │  │
    │  │  4. ORDER CONFIRMATION REQUIRED                               │  │
    │  │     • Restaurant must confirm each order                     │  │
    │  │     • Can modify/reject items                                 │  │
    │  │     • Customer notified before preparation starts            │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  DRIVER FATIGUE & SAFETY                                              │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Problem: Partners work 12+ hours for income                  │  │
    │  │           Fatigue → accidents → liability + bad PR            │  │
    │  │                                                                 │  │
    │  │  Solutions:                                                    │  │
    │  │                                                                 │  │
    │  │  1. MANDATORY BREAKS                                          │  │
    │  │     • Force offline after 10 hours continuous                │  │
    │  │     • 30-min break required every 4 hours                    │  │
    │  │     • Track via app (can't accept orders during break)       │  │
    │  │                                                                 │  │
    │  │  2. EARNINGS CAP ALERTS                                       │  │
    │  │     • "You've earned ₹X today. Consider taking a break"     │  │
    │  │                                                                 │  │
    │  │  3. SPEED ALERTS                                              │  │
    │  │     • GPS tracks speed                                        │  │
    │  │     • Warning if consistently speeding                       │  │
    │  │     • Penalty for repeated violations                        │  │
    │  │                                                                 │  │
    │  │  4. INSURANCE & SUPPORT                                       │  │
    │  │     • Accident insurance provided                            │  │
    │  │     • Emergency button in app                                │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  DISPUTE RESOLUTION                                                    │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Common Disputes:                                              │  │
    │  │  • "Food never arrived" (customer claims)                    │  │
    │  │  • "Food was cold/wrong/damaged"                             │  │
    │  │  • "Partial order missing"                                    │  │
    │  │  • "Charged but order cancelled"                             │  │
    │  │                                                                 │  │
    │  │  Evidence Collection:                                          │  │
    │  │  • GPS trail of partner (proof of delivery location)        │  │
    │  │  • Photo at delivery (timestamp + geotag)                    │  │
    │  │  • OTP verification (customer provides PIN)                  │  │
    │  │  • Chat logs between customer/partner                        │  │
    │  │                                                                 │  │
    │  │  Resolution Flow:                                              │  │
    │  │  1. Auto-resolve: Low-value disputes (<₹100) auto-refund    │  │
    │  │  2. ML triage: Score dispute legitimacy                      │  │
    │  │  3. Human review: High-value or repeat complainers          │  │
    │  │  4. Decision: Full refund / partial refund / reject         │  │
    │  │                                                                 │  │
    │  │  Blacklist: Flag users with high dispute rate                │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
ARCHITECTURE DIAGRAM
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  ┌─────────┐    ┌─────────┐    ┌─────────────┐                         │
    │  │Customer │    │Restaur. │    │  Delivery   │                         │
    │  │  App    │    │  App    │    │ Partner App │                         │
    │  └────┬────┘    └────┬────┘    └──────┬──────┘                         │
    │       │              │                │                                │
    │       └──────────────┼────────────────┘                                │
    │                      │                                                  │
    │                      ▼                                                  │
    │               ┌──────────────┐                                         │
    │               │     CDN      │                                         │
    │               └──────┬───────┘                                         │
    │                      │                                                  │
    │                      ▼                                                  │
    │               ┌──────────────┐                                         │
    │               │ API Gateway  │                                         │
    │               │ • Auth       │                                         │
    │               │ • Rate Limit │                                         │
    │               └──────┬───────┘                                         │
    │                      │                                                  │
    │     ┌────────────────┼────────────────┬──────────────┐                │
    │     │                │                │              │                │
    │     ▼                ▼                ▼              ▼                │
    │  ┌───────┐     ┌──────────┐    ┌──────────┐   ┌──────────┐          │
    │  │ User  │     │  Order   │    │ Location │   │  Search  │          │
    │  │Service│     │ Service  │    │ Service  │   │ Service  │          │
    │  └───┬───┘     └────┬─────┘    └────┬─────┘   └────┬─────┘          │
    │      │              │               │              │                  │
    │      ▼              ▼               ▼              ▼                  │
    │  ┌───────┐     ┌──────────┐    ┌──────────┐   ┌──────────┐          │
    │  │ MySQL │     │  MySQL   │    │  Redis   │   │Elasticsea│          │
    │  │(users)│     │ (orders) │    │   GEO    │   │   rch    │          │
    │  └───────┘     └────┬─────┘    └──────────┘   └──────────┘          │
    │                     │                                                  │
    │                     ▼                                                  │
    │              ┌──────────────┐                                         │
    │              │    KAFKA     │                                         │
    │              │              │                                         │
    │              │ • orders     │                                         │
    │              │ • location   │                                         │
    │              │ • notify     │                                         │
    │              └──────┬───────┘                                         │
    │                     │                                                  │
    │    ┌────────────────┼────────────────┐                                │
    │    │                │                │                                │
    │    ▼                ▼                ▼                                │
    │  ┌───────┐    ┌──────────┐    ┌──────────┐                           │
    │  │Notif. │    │ Delivery │    │ Tracking │                           │
    │  │Service│    │ Service  │    │ Service  │                           │
    │  └───────┘    └──────────┘    └────┬─────┘                           │
    │                                    │                                  │
    │                                    ▼                                  │
    │                              ┌──────────┐                             │
    │                              │ WebSocket│                             │
    │                              │ (live    │                             │
    │                              │ tracking)│                             │
    │                              └──────────┘                             │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
END OF FOOD DELIVERY PLATFORM SYSTEM DESIGN
================================================================================

