# BOOKMYSHOW SYSTEM DESIGN
*Chapter 2: High-Level Architecture*

This chapter presents the complete architecture of a ticket booking system,
explaining each component, its responsibilities, and how they interact.

## SECTION 2.1: ARCHITECTURE OVERVIEW

```
+-------------------------------------------------------------------------+
|                                                                         |
|                    BOOKMYSHOW ARCHITECTURE                              |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                         CLIENTS                                   |  |
|  |    [Mobile App]    [Web Browser]    [Partner APIs]                |  |
|  +-------------------------------------------------------------------+  |
|                              |                                          |
|                              v                                          |
|  +-------------------------------------------------------------------+  |
|  |                           CDN                                     |  |
|  |               (Static assets, images, JS/CSS)                     |  |
|  +-------------------------------------------------------------------+  |
|                              |                                          |
|                              v                                          |
|  +-------------------------------------------------------------------+  |
|  |                      LOAD BALANCER                                |  |
|  |                   (L7 - Application Layer)                        |  |
|  +-------------------------------------------------------------------+  |
|                              |                                          |
|                              v                                          |
|  +-------------------------------------------------------------------+  |
|  |                      API GATEWAY                                  |  |
|  |    [Rate Limiting] [Auth] [Routing] [SSL Termination]             |  |
|  +-------------------------------------------------------------------+  |
|                              |                                          |
|           +------------------+------------------+                       |
|           v                  v                  v                       |
|  +-------------+    +-------------+    +-------------+                  |
|  |   User      |    |   Catalog   |    |   Booking   |                  |
|  |  Service    |    |   Service   |    |   Service   |                  |
|  +-------------+    +-------------+    +-------------+                  |
|           |                  |                  |                       |
|           |                  |                  |                       |
|  +-------------+    +-------------+    +-------------+                  |
|  |   Search    |    |   Payment   |    | Notification|                  |
|  |   Service   |    |   Service   |    |   Service   |                  |
|  +-------------+    +-------------+    +-------------+                  |
|           |                  |                  |                       |
|           v                  v                  v                       |
|  +-------------------------------------------------------------------+  |
|  |                      DATA LAYER                                   |  |
|  |                                                                   |  |
|  |  +-------------+  +-------------+  +-------------+                |  |
|  |  | PostgreSQL  |  |    Redis    |  |Elasticsearch|                |  |
|  |  |  (Primary)  |  |   (Cache)   |  |  (Search)   |                |  |
|  |  +-------------+  +-------------+  +-------------+                |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                              |                                          |
|                              v                                          |
|  +-------------------------------------------------------------------+  |
|  |                    MESSAGE QUEUE (Kafka)                          |  |
|  |            [Events] [Notifications] [Analytics]                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.2: COMPONENT DEEP DIVE

### CLIENT LAYER

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CLIENTS                                                                |
|                                                                         |
|  MOBILE APPS (iOS, Android)                                             |
|  ------------------------------                                         |
|  * Native apps for best UX                                              |
|  * Offline caching for movie info                                       |
|  * Push notifications for reminders                                     |
|  * QR code scanner for ticket entry                                     |
|                                                                         |
|  WEB APPLICATION                                                        |
|  ----------------                                                       |
|  * Responsive SPA (React/Vue)                                           |
|  * SEO for movie pages                                                  |
|  * PWA for mobile web experience                                        |
|                                                                         |
|  PARTNER APIs                                                           |
|  -------------                                                          |
|  * B2B integrations (Paytm, Google Pay)                                 |
|  * Affiliate partners                                                   |
|  * Corporate booking portals                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### EDGE LAYER

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CDN (Content Delivery Network)                                         |
|  ===============================                                        |
|                                                                         |
|  PURPOSE:                                                               |
|  Serve static content from edge locations close to users.               |
|                                                                         |
|  WHAT IT SERVES:                                                        |
|  * Movie posters and banners                                            |
|  * Venue photos                                                         |
|  * JavaScript, CSS bundles                                              |
|  * Static HTML pages                                                    |
|                                                                         |
|  BENEFITS:                                                              |
|  * Reduces latency (served from nearby edge)                            |
|  * Reduces load on origin servers                                       |
|  * Handles traffic spikes                                               |
|                                                                         |
|  PROVIDERS: CloudFront, Cloudflare, Akamai                              |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  LOAD BALANCER                                                          |
|  =============                                                          |
|                                                                         |
|  TYPE: Layer 7 (Application Layer)                                      |
|                                                                         |
|  RESPONSIBILITIES:                                                      |
|  * Distribute traffic across API Gateway instances                      |
|  * SSL termination                                                      |
|  * Health checks                                                        |
|  * Geographic routing (route to nearest datacenter)                     |
|                                                                         |
|  ALGORITHM: Least connections (for even distribution)                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### API GATEWAY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  API GATEWAY                                                            |
|  ===========                                                            |
|                                                                         |
|  The API Gateway is the single entry point for all API requests.        |
|  It handles cross-cutting concerns.                                     |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Request --> [Rate Limit] --> [Auth] --> [Route] --> Service      |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  RESPONSIBILITIES:                                                      |
|                                                                         |
|  1. AUTHENTICATION                                                      |
|     Validate JWT tokens                                                 |
|     Extract user context from token                                     |
|     Pass user info to downstream services                               |
|                                                                         |
|  2. RATE LIMITING                                                       |
|     +--------------------------------------------------------------+    |
|     | Endpoint              | Rate Limit                           |    |
|     +--------------------------------------------------------------+    |
|     | /api/search           | 100 req/min per IP                   |    |
|     | /api/shows/{id}/seats | 30 req/min per user                  |    |
|     | /api/bookings         | 10 req/min per user                  |    |
|     | /api/payments         | 5 req/min per user                   |    |
|     +--------------------------------------------------------------+    |
|                                                                         |
|  3. REQUEST ROUTING                                                     |
|     Route to appropriate microservice based on path                     |
|     /api/users/*     > User Service                                     |
|     /api/movies/*    > Catalog Service                                  |
|     /api/bookings/*  > Booking Service                                  |
|                                                                         |
|  4. REQUEST/RESPONSE TRANSFORMATION                                     |
|     Add request IDs for tracing                                         |
|     Compress responses                                                  |
|     Format errors consistently                                          |
|                                                                         |
|  5. VIRTUAL WAITING ROOM (for flash sales)                              |
|     Queue excess traffic during high-demand events                      |
|     Fair queuing based on arrival time                                  |
|                                                                         |
|  IMPLEMENTATIONS: Kong, AWS API Gateway, NGINX                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### MICROSERVICES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MICROSERVICES                                                          |
|                                                                         |
|  1. USER SERVICE                                                        |
|  ===============                                                        |
|  Manages user accounts and authentication.                              |
|                                                                         |
|  Endpoints:                                                             |
|  * POST /users/register                                                 |
|  * POST /users/login                                                    |
|  * GET /users/profile                                                   |
|  * PUT /users/preferences                                               |
|                                                                         |
|  Data:                                                                  |
|  * User profiles                                                        |
|  * Authentication tokens                                                |
|  * Preferences (location, language)                                     |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  2. CATALOG SERVICE                                                     |
|  ==================                                                     |
|  Manages movies, events, venues, and shows.                             |
|                                                                         |
|  Endpoints:                                                             |
|  * GET /movies (list with filters)                                      |
|  * GET /movies/{id}                                                     |
|  * GET /movies/{id}/shows                                               |
|  * GET /venues                                                          |
|  * GET /shows/{id}                                                      |
|                                                                         |
|  Data:                                                                  |
|  * Movie metadata (title, cast, ratings)                                |
|  * Venue information (name, location, seat layout)                      |
|  * Show schedules                                                       |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  3. BOOKING SERVICE  (Most Critical)                                    |
|  =======================================                                |
|  Handles seat selection and booking flow.                               |
|                                                                         |
|  Endpoints:                                                             |
|  * GET /shows/{id}/seats (get seat availability)                        |
|  * POST /reservations (lock seats temporarily)                          |
|  * POST /bookings (confirm booking after payment)                       |
|  * DELETE /reservations/{id} (release seats)                            |
|  * GET /bookings (user's bookings)                                      |
|                                                                         |
|  Data:                                                                  |
|  * Seat availability (real-time)                                        |
|  * Reservations (temporary locks)                                       |
|  * Bookings (confirmed purchases)                                       |
|                                                                         |
|  CRITICAL REQUIREMENTS:                                                 |
|  * No double-booking                                                    |
|  * Fast seat locking                                                    |
|  * Automatic lock expiry                                                |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  4. PAYMENT SERVICE                                                     |
|  ==================                                                     |
|  Integrates with payment gateways.                                      |
|                                                                         |
|  Endpoints:                                                             |
|  * POST /payments/initiate                                              |
|  * POST /payments/callback (webhook from gateway)                       |
|  * GET /payments/{id}/status                                            |
|  * POST /payments/{id}/refund                                           |
|                                                                         |
|  Integrations:                                                          |
|  * Razorpay, PayU, Paytm                                                |
|  * Credit/Debit cards                                                   |
|  * UPI (India)                                                          |
|  * Wallets                                                              |
|                                                                         |
|  REQUIREMENTS:                                                          |
|  * Idempotent operations (handle duplicate callbacks)                   |
|  * PCI-DSS compliance                                                   |
|  * Retry failed payments                                                |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  5. SEARCH SERVICE                                                      |
|  =================                                                      |
|  Provides fast search capabilities.                                     |
|                                                                         |
|  Endpoints:                                                             |
|  * GET /search?q=avengers&city=mumbai                                   |
|  * GET /search/suggest (autocomplete)                                   |
|                                                                         |
|  Features:                                                              |
|  * Full-text search                                                     |
|  * Faceted search (filters)                                             |
|  * Autocomplete                                                         |
|  * Spell correction                                                     |
|  * Relevance ranking                                                    |
|                                                                         |
|  Backend: Elasticsearch                                                 |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  6. NOTIFICATION SERVICE                                                |
|  =========================                                              |
|  Sends notifications to users.                                          |
|                                                                         |
|  Channels:                                                              |
|  * Email (booking confirmation, e-ticket)                               |
|  * SMS (OTP, booking confirmation)                                      |
|  * Push notifications (reminders)                                       |
|                                                                         |
|  Pattern: Async via message queue                                       |
|  Booking Service > Kafka > Notification Service > Send                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DATA LAYER

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DATA STORES                                                            |
|                                                                         |
|  1. POSTGRESQL (Primary Database)                                       |
|  ================================                                       |
|                                                                         |
|  WHY POSTGRESQL?                                                        |
|  * ACID compliance (critical for booking)                               |
|  * Row-level locking (SELECT FOR UPDATE)                                |
|  * Mature, reliable, well-understood                                    |
|  * Good performance with proper indexing                                |
|                                                                         |
|  TABLES:                                                                |
|  * users, user_preferences                                              |
|  * movies, events, genres                                               |
|  * venues, screens, seat_templates                                      |
|  * shows, show_seats                                                    |
|  * reservations, bookings, booking_items                                |
|  * payments, refunds                                                    |
|                                                                         |
|  SCALING:                                                               |
|  * Read replicas for read-heavy queries                                 |
|  * Sharding by city/region for large scale                              |
|  * Partitioning for historical data (old shows)                         |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  2. REDIS (Cache + Distributed Lock)                                    |
|  ===================================                                    |
|                                                                         |
|  USE CASES:                                                             |
|                                                                         |
|  a) CACHING                                                             |
|     * Movie details (rarely changes)                                    |
|     * Venue information                                                 |
|     * Show listings                                                     |
|     * User sessions                                                     |
|                                                                         |
|  b) SEAT AVAILABILITY (Real-time)                                       |
|     * Bitmap for each show's seat availability                          |
|     * Fast reads: Is seat A5 available?                                 |
|     * Fast updates: Mark A5 as locked                                   |
|                                                                         |
|  c) DISTRIBUTED LOCKING                                                 |
|     * Lock seats during reservation                                     |
|     * Prevent race conditions                                           |
|     * Auto-expiry for abandoned locks                                   |
|                                                                         |
|  d) RATE LIMITING                                                       |
|     * Token bucket counters                                             |
|     * Track requests per user/IP                                        |
|                                                                         |
|  CONFIGURATION:                                                         |
|  * Redis Cluster (for high availability)                                |
|  * Persistence: RDB snapshots (for recovery)                            |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  3. ELASTICSEARCH (Search)                                              |
|  =========================                                              |
|                                                                         |
|  INDEXES:                                                               |
|  * movies (title, cast, genres, language, ratings)                      |
|  * events (name, category, artists, venue)                              |
|  * venues (name, city, area)                                            |
|                                                                         |
|  FEATURES USED:                                                         |
|  * Full-text search with analyzers                                      |
|  * Fuzzy matching for typos                                             |
|  * Aggregations for filters                                             |
|  * Geo queries for nearby venues                                        |
|                                                                         |
|  DATA SYNC:                                                             |
|  PostgreSQL > Debezium (CDC) > Kafka > Elasticsearch                    |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  4. KAFKA (Message Queue)                                               |
|  =========================                                              |
|                                                                         |
|  TOPICS:                                                                |
|  * booking.created     > Trigger notification                           |
|  * booking.confirmed   > Analytics, loyalty points                      |
|  * payment.completed   > Finalize booking                               |
|  * seat.availability   > Real-time updates to clients                   |
|                                                                         |
|  WHY KAFKA?                                                             |
|  * High throughput                                                      |
|  * Message replay (debug issues)                                        |
|  * Multiple consumers per topic                                         |
|  * Ordering within partitions                                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.3: DATA FLOW DIAGRAMS

### SEARCH FLOW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  USER SEARCHES FOR "AVENGERS IN MUMBAI"                                 |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |  User                                                            |   |
|  |   |                                                              |   |
|  |   |  GET /search?q=avengers&city=mumbai                          |   |
|  |   v                                                              |   |
|  |  API Gateway                                                     |   |
|  |   |                                                              |   |
|  |   |  1. Validate token                                           |   |
|  |   |  2. Rate limit check                                         |   |
|  |   v                                                              |   |
|  |  Search Service                                                  |   |
|  |   |                                                              |   |
|  |   |  3. Query Elasticsearch                                      |   |
|  |   |     - Match "avengers" in title                              |   |
|  |   |     - Filter by city "mumbai"                                |   |
|  |   |     - Sort by relevance                                      |   |
|  |   v                                                              |   |
|  |  Elasticsearch                                                   |   |
|  |   |                                                              |   |
|  |   |  Returns: [Avengers Endgame, Avengers Infinity War, ...]     |   |
|  |   v                                                              |   |
|  |  Search Service                                                  |   |
|  |   |                                                              |   |
|  |   |  4. Enrich with cache data (ratings, images)                 |   |
|  |   v                                                              |   |
|  |  Redis Cache                                                     |   |
|  |   |                                                              |   |
|  |   v                                                              |   |
|  |  Response: { movies: [...], venues: [...] }                      |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  LATENCY TARGET: < 200ms                                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SEAT SELECTION FLOW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  USER VIEWS SEAT MAP FOR A SHOW                                         |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |  User                                                            |   |
|  |   |                                                              |   |
|  |   |  GET /shows/123/seats                                        |   |
|  |   v                                                              |   |
|  |  Booking Service                                                 |   |
|  |   |                                                              |   |
|  |   |  1. Get seat layout (venue template)                         |   |
|  |   v                                                              |   |
|  |  Redis: venue:456:layout > seat positions, categories            |   |
|  |   |                                                              |   |
|  |   |  2. Get real-time availability                               |   |
|  |   v                                                              |   |
|  |  Redis: show:123:seats > bitmap of availability                  |   |
|  |   |                                                              |   |
|  |   |     Bit 0 = A1, Bit 1 = A2, ...                              |   |
|  |   |     0 = available, 1 = taken/locked                          |   |
|  |   |                                                              |   |
|  |   |  3. Merge layout + availability                              |   |
|  |   v                                                              |   |
|  |  Response:                                                       |   |
|  |  {                                                               |   |
|  |    seats: [                                                      |   |
|  |      { id: "A1", row: "A", number: 1, status: "available",       |   |
|  |        category: "GOLD", price: 300 },                           |   |
|  |      { id: "A2", row: "A", number: 2, status: "booked", ... },   |   |
|  |      { id: "A3", row: "A", number: 3, status: "locked", ... }    |   |
|  |    ]                                                             |   |
|  |  }                                                               |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  LATENCY TARGET: < 500ms                                                |
|                                                                         |
|  REAL-TIME UPDATES:                                                     |
|  WebSocket connection pushes availability changes                       |
|  When another user books > push update to all viewing users             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### REAL-TIME SEAT AVAILABILITY (WEBSOCKET + REDIS PUB/SUB)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PROBLEM                                                                |
|                                                                         |
|  200 users are viewing the same show's seat map simultaneously.         |
|  User A locks seat A5. The other 199 users still see A5 as              |
|  "available" until they refresh. They click A5, get an error.           |
|  Terrible UX. We need all viewers to see changes in real time.          |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  SOLUTION: WEBSOCKET + REDIS PUB/SUB                                    |
|                                                                         |
|  1. Client opens the seat map page                                      |
|  2. Client establishes a WebSocket connection to the server             |
|  3. Server subscribes the connection to a Redis Pub/Sub channel:        |
|     channel = "show:{showId}:seat_updates"                              |
|  4. When any seat status changes, server publishes to that channel      |
|  5. All connected clients receive the update and re-render the seat     |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  DATA FLOW WHEN USER A LOCKS SEAT A5                                    |
|                                                                         |
|  User A      Booking     Redis         Redis      WS Servers  User B    |
|  (Client)    Service     (Lock+Bitmap) (Pub/Sub)  (per show)  (Client)  |
|    |            |            |            |            |          |     |
|    | POST /reservations      |            |            |          |     |
|    | {seats:[A5,A6]}         |            |            |          |     |
|    |----------->|            |            |            |          |     |
|    |            |            |            |            |          |     |
|    |            | Lua script:|            |            |          |     |
|    |            | SET NX + SETBIT         |            |          |     |
|    |            |----------->|            |            |          |     |
|    |            |   OK (locked)           |            |          |     |
|    |            |<-----------|            |            |          |     |
|    |            |            |            |            |          |     |
|    |            | PUBLISH show:123:seat_updates        |          |     |
|    |            |------------------------>|            |          |     |
|    |            |            |            |            |          |     |
|    |            |            |  Message delivered      |          |     |
|    |            |            |            |----------->|          |     |
|    |            |            |            |            |          |     |
|    |            |            |            | Broadcast  |          |     |
|    |            |            |            | to all     |          |     |
|    |            |            |            | clients    |          |     |
|    |            |            |            |            |--------->|     |
|    |            |            |            |            | WS msg:  |     |
|    |            |            |            |            | A5,A6    |     |
|    |            |            |            |            | locked   |     |
|    |            |            |            |            |          |     |
|    |            | INSERT reservation      |            |  Client  |     |
|    |            |---> PostgreSQL          |            |  updates |     |
|    |            |<--- OK     |            |            |  seat    |     |
|    |            |            |            |            |  map UI  |     |
|    |  200 OK    |            |            |            |          |     |
|    |  {reservationId,        |            |            |          |     |
|    |   expiresAt}            |            |            |          |     |
|    |<-----------|            |            |            |          |     |
|    |            |            |            |            |          |     |
|                                                                         |
|  TIMING:                                                                |
|  Steps 1-2 (Redis lock + publish):  ~1-2ms                              |
|  Step 3-4  (Pub/Sub + WS broadcast): ~5-10ms                            |
|  Step 5    (DB insert, parallel):    ~5-10ms                            |
|  Step 6    (UI update at User B):    ~50ms (includes network)           |
|                                                                         |
|  User B sees A5 turn grey within ~50-100ms of User A clicking.          |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  WHY REDIS PUB/SUB (NOT KAFKA)?                                         |
|                                                                         |
|  * Seat updates are ephemeral: no need to persist or replay them.       |
|    If a client misses one, the next update or a full refresh fixes it.  |
|  * Ultra-low latency: Redis Pub/Sub delivers in <1ms.                   |
|    Kafka adds 5-50ms and is designed for durable event streaming.       |
|  * Fan-out to many subscribers per show is Pub/Sub's sweet spot.        |
|  * Fire-and-forget: if no one is listening, the message is dropped.     |
|    This is fine -- no viewers means no one to update.                   |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  SCALING WEBSOCKET CONNECTIONS                                          |
|                                                                         |
|  Problem: A popular show has 50K concurrent viewers. One WebSocket      |
|  server can handle ~10K-50K connections. How to scale?                  |
|                                                                         |
|  +----------------------------------------------------------------+     |
|  |                                                                |     |
|  |  Users viewing show 123                                        |     |
|  |    |          |          |                                     |     |
|  |    v          v          v                                     |     |
|  |  WS Server  WS Server  WS Server                               |     |
|  |  (10K conn) (10K conn) (10K conn)                               |    |
|  |    |          |          |                                     |     |
|  |    +--------- +----------+                                     |     |
|  |               |                                                |     |
|  |     All subscribe to Redis channel:                            |     |
|  |     show:123:seat_updates                                      |     |
|  |               |                                                |     |
|  |               v                                                |     |
|  |         Redis Pub/Sub                                          |     |
|  |                                                                |     |
|  +----------------------------------------------------------------+     |
|                                                                         |
|  Each WS server subscribes to the same Redis channel. When a seat       |
|  update is published, ALL WS servers receive it and broadcast to        |
|  their local connections. Redis handles the fan-out across servers.     |
|                                                                         |
|  STICKY SESSIONS:                                                       |
|  Load balancer uses sticky sessions (cookie or IP hash) so a            |
|  client's HTTP requests and WebSocket go to the same server.            |
|  Not strictly required (any server can serve any client), but           |
|  reduces reconnection overhead.                                         |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  MESSAGE FORMAT (WebSocket payload)                                     |
|                                                                         |
|  {                                                                      |
|    "type": "SEAT_UPDATE",                                               |
|    "showId": 123,                                                       |
|    "changes": [                                                         |
|      { "seatId": "A5", "status": "locked" },                            |
|      { "seatId": "A6", "status": "locked" }                             |
|    ],                                                                   |
|    "timestamp": 1705312500000                                           |
|  }                                                                      |
|                                                                         |
|  Client uses the timestamp to ignore stale messages                     |
|  (e.g., if messages arrive out of order).                               |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  FALLBACK: POLLING FOR NON-WEBSOCKET CLIENTS                            |
|                                                                         |
|  Some environments block WebSocket (corporate proxies, old browsers).   |
|                                                                         |
|  Fallback: client polls GET /shows/123/seats every 5 seconds.           |
|  Server returns only changed seats since last poll (delta):             |
|  GET /shows/123/seats?since=1705312500000                               |
|                                                                         |
|  Trade-off:                                                             |
|  * 5s polling = up to 5 seconds stale (acceptable for most users)       |
|  * Much higher server load than WebSocket (request per client per 5s)   |
|  * Use WebSocket where possible, polling as last resort                 |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  CONNECTION LIFECYCLE                                                   |
|                                                                         |
|  1. User opens seat map -> client opens WebSocket                       |
|  2. Server registers connection under show:123 channel                  |
|  3. User receives real-time updates while viewing                       |
|  4. User navigates away -> client closes WebSocket                      |
|  5. Server unsubscribes connection from the channel                     |
|  6. If last connection for that show -> server unsubscribes             |
|     from Redis channel (no unnecessary traffic)                         |
|                                                                         |
|  HEARTBEAT:                                                             |
|  * Server pings every 30 seconds                                        |
|  * If client doesn't respond (pong) within 10 seconds -> close          |
|  * Prevents zombie connections from accumulating                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DATA PERSISTENCE STRATEGY

```
+------------------------------------------------------------------------+
|                                                                        |
|  DUAL-WRITE PATTERN: REDIS FIRST, THEN POSTGRESQL                      |
|                                                                        |
|  The system uses Redis as the fast real-time layer and PostgreSQL      |
|  as the durable source of truth. Writes happen in a specific order     |
|  depending on the operation type.                                      |
|                                                                        |
|  ====================================================================  |
|                                                                        |
|  SEAT STATUS STATE MACHINE                                             |
|                                                                        |
|  A seat goes through exactly these states:                             |
|                                                                        |
|  AVAILABLE --[reserve]--> LOCKED --[pay+confirm]--> BOOKED             |
|       ^                     |                                          |
|       |                     | (TTL expires or                          |
|       +-----[expire]--------+  payment fails)                          |
|                                                                        |
|  WHERE EACH STATE LIVES:                                               |
|  +--------------------------------------------------------------+      |
|  | State     | Redis                    | PostgreSQL             |     |
|  +--------------------------------------------------------------+      |
|  | AVAILABLE | bitmap bit = 0           | show_seats.status =    |     |
|  |           | no lock key exists       | 'AVAILABLE'            |     |
|  +--------------------------------------------------------------+      |
|  | LOCKED    | bitmap bit = 1           | show_seats.status =    |     |
|  |           | lock key exists with TTL | 'LOCKED'               |     |
|  |           |                          | reservations.status =  |     |
|  |           |                          | 'PENDING'              |     |
|  +--------------------------------------------------------------+      |
|  | BOOKED    | bitmap bit = 1           | show_seats.status =    |     |
|  |           | lock key deleted (or TTL)| 'BOOKED'               |     |
|  |           |                          | reservations.status =  |     |
|  |           |                          | 'CONFIRMED'            |     |
|  |           |                          | bookings row exists    |     |
|  +--------------------------------------------------------------+      |
|                                                                        |
|  ====================================================================  |
|                                                                        |
|  OPERATION 1: SEAT RESERVATION (WRITE PATH)                            |
|                                                                        |
|  This is NOT one transaction. It is two independent steps.             |
|  Redis and PostgreSQL cannot share a transaction (different systems).  |
|                                                                        |
|  STEP 1 -> Redis (fast gate, sub-millisecond)                          |
|  -------                                                               |
|  Lua script runs atomically inside Redis:                              |
|    a) SET seat:123:A5 res_abc NX EX 600 (lock key, 10min TTL)          |
|    b) SET seat:123:A6 res_abc NX EX 600                                |
|    c) SETBIT show:123:seats 4 1         (flip bitmap: A5 taken)        |
|    d) SETBIT show:123:seats 5 1         (flip bitmap: A6 taken)        |
|    e) PUBLISH show:123:seat_updates     (notify WS clients)            |
|                                                                        |
|  If NX fails (key already exists) -> return error immediately.         |
|  No DB call happens. User sees "seat already taken".                   |
|                                                                        |
|  STEP 2 -> PostgreSQL (durable record, ~5-10ms)                        |
|  -------                                                               |
|  Only runs if Step 1 succeeded:                                        |
|                                                                        |
|  BEGIN;                                                                |
|    INSERT INTO reservations                                            |
|      (id, show_id, user_id, status, expires_at, created_at)            |
|    VALUES                                                              |
|      ('res_abc', 123, 'user_A', 'PENDING',                             |
|       NOW() + INTERVAL '10 min', NOW());                               |
|                                                                        |
|    INSERT INTO reservation_seats (reservation_id, seat_id)             |
|    VALUES ('res_abc', 'A5'), ('res_abc', 'A6');                        |
|                                                                        |
|    UPDATE show_seats                                                   |
|    SET status = 'LOCKED', locked_by = 'res_abc',                       |
|        locked_at = NOW()                                               |
|    WHERE show_id = 123 AND seat_id IN ('A5', 'A6')                     |
|      AND status = 'AVAILABLE';                                         |
|  COMMIT;                                                               |
|                                                                        |
|  IF DB FAILS AFTER REDIS SUCCEEDED:                                    |
|  * Redis lock keys expire in 10 min automatically (TTL)                |
|  * Bitmap bits get reset by reconciliation job                         |
|  * No manual intervention needed -- system self-heals                  |
|  * User sees an error and can retry                                    |
|                                                                        |
|  ====================================================================  |
|                                                                        |
|  OPERATION 2: BOOKING CONFIRMATION (WRITE PATH)                        |
|                                                                        |
|  Triggered when payment gateway sends success webhook.                 |
|  This IS a single PostgreSQL transaction -- all 5 writes               |
|  succeed together or all 5 roll back. Nothing half-committed.          |
|                                                                        |
|  BEGIN;                                                                |
|                                                                        |
|    -- 1. VERIFY: Is the reservation still valid?                       |
|    SELECT * FROM reservations                                          |
|    WHERE id = 'res_abc'                                                |
|      AND status = 'PENDING'                                            |
|      AND expires_at > NOW()                                            |
|    FOR UPDATE;            -- locks row to prevent races                |
|                                                                        |
|    -- If no row: expired or already confirmed.                         |
|    -- ROLLBACK, initiate refund, return error.                         |
|                                                                        |
|    -- 2. FLIP reservation: PENDING -> CONFIRMED                        |
|    UPDATE reservations                                                 |
|    SET status = 'CONFIRMED', confirmed_at = NOW()                      |
|    WHERE id = 'res_abc';                                               |
|                                                                        |
|    -- 3. CREATE the booking (the permanent record)                     |
|    INSERT INTO bookings                                                |
|      (id, reservation_id, user_id, show_id,                            |
|       total_amount, status, created_at)                                |
|    VALUES                                                              |
|      ('book_xyz', 'res_abc', 'user_A', 123,                            |
|       600, 'CONFIRMED', NOW());                                        |
|                                                                        |
|    INSERT INTO booking_seats (booking_id, seat_id, price)              |
|    VALUES ('book_xyz', 'A5', 300), ('book_xyz', 'A6', 300);            |
|                                                                        |
|    -- 4. FLIP seat status: LOCKED -> BOOKED (permanent)                |
|    UPDATE show_seats                                                   |
|    SET status = 'BOOKED', booking_id = 'book_xyz'                      |
|    WHERE show_id = 123 AND seat_id IN ('A5', 'A6');                    |
|                                                                        |
|    -- 5. RECORD the payment                                            |
|    INSERT INTO payments                                                |
|      (id, booking_id, amount, method, gateway_ref, status)             |
|    VALUES                                                              |
|      ('pay_001', 'book_xyz', 600, 'UPI', 'gw_ref_123',                 |
|       'SUCCESS');                                                      |
|                                                                        |
|  COMMIT;   -- ALL 5 writes commit atomically, or none do               |
|                                                                        |
|  AFTER COMMIT (async, outside the transaction):                        |
|                                                                        |
|  a) Redis cleanup:                                                     |
|     DEL seat:123:A5 seat:123:A6   (remove lock keys)                   |
|     PUBLISH show:123:seat_updates  (notify: now "booked")              |
|     * If Redis is down: TTL expires the keys anyway.                   |
|     * Bitmap bit stays 1 (correct -- seat IS taken).                   |
|                                                                        |
|  b) Kafka event:                                                       |
|     PRODUCE booking.confirmed {bookingId, showId, seats}               |
|     * Notification Service -> sends email/SMS/e-ticket                 |
|     * Analytics Service -> updates dashboards                          |
|                                                                        |
|  ====================================================================  |
|                                                                        |
|  OPERATION 3: EXPIRY (AUTOMATIC CLEANUP)                               |
|                                                                        |
|  When user abandons payment and the 10-minute timer expires:           |
|                                                                        |
|  REDIS (automatic):                                                    |
|  * Lock keys expire via TTL -> deleted by Redis                        |
|  * Bitmap bits need explicit reset (see reconciliation)                |
|                                                                        |
|  POSTGRESQL (scheduled job, runs every 60 seconds):                    |
|                                                                        |
|  UPDATE reservations                                                   |
|  SET status = 'EXPIRED'                                                |
|  WHERE status = 'PENDING' AND expires_at < NOW();                      |
|                                                                        |
|  UPDATE show_seats                                                     |
|  SET status = 'AVAILABLE', locked_by = NULL                            |
|  WHERE status = 'LOCKED'                                               |
|    AND locked_by IN (                                                  |
|      SELECT id FROM reservations WHERE status = 'EXPIRED'              |
|    );                                                                  |
|                                                                        |
|  REDIS BITMAP RECONCILIATION (every 5 minutes):                        |
|  * Read show_seats from DB for active shows                            |
|  * Rebuild bitmap: AVAILABLE = 0, LOCKED/BOOKED = 1                    |
|  * Overwrite Redis bitmap -> corrects any drift                        |
|                                                                        |
|  ====================================================================  |
|                                                                        |
|  OPERATION 4: SEAT AVAILABILITY (READ PATH)                            |
|                                                                        |
|  READ from Redis (bitmap) -> cache hit = return instantly              |
|  On cache miss -> READ from PostgreSQL (show_seats table)              |
|               -> Populate Redis bitmap                                 |
|               -> Return to client                                      |
|                                                                        |
|  CACHE INVALIDATION:                                                   |
|  * On reservation: flip bitmap bit in Redis (real-time)                |
|  * On booking: bitmap already reflects locked state                    |
|  * On expiry: bitmap bit resets via reconciliation job                 |
|  * Fallback: recon job rebuilds bitmap from DB every 5 min             |
|                                                                        |
|                                                                        |
|  FAILURE SCENARIOS AND RECOVERY                                        |
|                                                                        |
|  +----------------------------------------------------------------+    |
|  | Failure                      | Impact & Recovery               |    |
|  +----------------------------------------------------------------+    |
|  | Redis lock succeeds,         | Redis TTL auto-expires the      |    |
|  | DB insert fails              | lock. No manual cleanup needed. |    |
|  +----------------------------------------------------------------+    |
|  | DB confirms booking,         | No impact. TTL will expire.     |    |
|  | Redis DEL fails              | Seat shows "locked" briefly     |    |
|  |                              | instead of "booked" in UI.      |    |
|  +----------------------------------------------------------------+    |
|  | Redis goes down entirely     | Fall back to pessimistic DB     |    |
|  |                              | locking (SELECT FOR UPDATE).    |    |
|  |                              | Slower but still correct.       |    |
|  +----------------------------------------------------------------+    |
|  | DB goes down                 | System cannot accept bookings.  |    |
|  |                              | Return 503. Redis locks expire  |    |
|  |                              | naturally. No inconsistency.    |    |
|  +----------------------------------------------------------------+    |
|                                                                        |
|  KEY PRINCIPLE:                                                        |
|  Redis is the PERFORMANCE layer (fast locks, real-time reads).         |
|  PostgreSQL is the TRUTH layer (durable bookings, ACID).               |
|  If they ever disagree, PostgreSQL wins. Redis self-heals via TTL.     |
|                                                                        |
+------------------------------------------------------------------------+
```

## SECTION 2.4: TECHNOLOGY CHOICES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TECHNOLOGY STACK                                                       |
|                                                                         |
|  COMPONENT              | TECHNOLOGY        | REASONING                 |
|  ===================================================================    |
|  API Gateway            | Kong / NGINX      | Mature, extensible        |
|  Services               | Java/Spring Boot  | Strong typing, tooling    |
|  Primary Database       | PostgreSQL        | ACID, reliability         |
|  Cache                  | Redis Cluster     | Speed, atomic ops         |
|  Search                 | Elasticsearch     | Full-text, scalable       |
|  Message Queue          | Kafka             | Throughput, replay        |
|  CDN                    | CloudFront        | Global edge network       |
|  Container Orchestration| Kubernetes        | Scaling, self-healing     |
|  Monitoring             | Prometheus+Grafana| Metrics, alerting         |
|  Logging                | ELK Stack         | Centralized logs          |
|  Tracing                | Jaeger            | Distributed tracing       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ARCHITECTURE - KEY TAKEAWAYS                                           |
|                                                                         |
|  LAYERS                                                                 |
|  ------                                                                 |
|  * CDN: Static content                                                  |
|  * API Gateway: Auth, rate limiting, routing                            |
|  * Microservices: Domain-specific logic                                 |
|  * Data Layer: PostgreSQL, Redis, Elasticsearch                         |
|  * Messaging: Kafka for async communication                             |
|                                                                         |
|  CRITICAL SERVICES                                                      |
|  -----------------                                                      |
|  * Booking Service: The heart of the system                             |
|  * Payment Service: PCI-compliant, idempotent                           |
|                                                                         |
|  DATA STORES                                                            |
|  -----------                                                            |
|  * PostgreSQL: Source of truth (bookings, payments)                     |
|  * Redis: Real-time data (availability, locks)                          |
|  * Elasticsearch: Search (movies, events)                               |
|                                                                         |
|  INTERVIEW TIP                                                          |
|  -------------                                                          |
|  Draw the architecture diagram first.                                   |
|  Explain each component's role clearly.                                 |
|  Highlight the Booking Service as most critical.                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 2

