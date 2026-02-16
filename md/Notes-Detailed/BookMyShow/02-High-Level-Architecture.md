# BOOKMYSHOW SYSTEM DESIGN
*Chapter 2: High-Level Architecture*

This chapter presents the complete architecture of a ticket booking system,
explaining each component, its responsibilities, and how they interact.

## SECTION 2.1: ARCHITECTURE OVERVIEW

```
+-------------------------------------------------------------------------+
|                                                                         |
|                    BOOKMYSHOW ARCHITECTURE                             |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                         CLIENTS                                 |  |
|  |    [Mobile App]    [Web Browser]    [Partner APIs]             |  |
|  +-----------------------------------------------------------------+  |
|                              |                                         |
|                              v                                         |
|  +-----------------------------------------------------------------+  |
|  |                           CDN                                   |  |
|  |               (Static assets, images, JS/CSS)                  |  |
|  +-----------------------------------------------------------------+  |
|                              |                                         |
|                              v                                         |
|  +-----------------------------------------------------------------+  |
|  |                      LOAD BALANCER                              |  |
|  |                   (L7 - Application Layer)                     |  |
|  +-----------------------------------------------------------------+  |
|                              |                                         |
|                              v                                         |
|  +-----------------------------------------------------------------+  |
|  |                      API GATEWAY                                |  |
|  |    [Rate Limiting] [Auth] [Routing] [SSL Termination]          |  |
|  +-----------------------------------------------------------------+  |
|                              |                                         |
|           +------------------+------------------+                     |
|           v                  v                  v                     |
|  +-------------+    +-------------+    +-------------+              |
|  |   User      |    |   Catalog   |    |   Booking   |              |
|  |  Service    |    |   Service   |    |   Service   |              |
|  +-------------+    +-------------+    +-------------+              |
|           |                  |                  |                     |
|           |                  |                  |                     |
|  +-------------+    +-------------+    +-------------+              |
|  |   Search    |    |   Payment   |    | Notification|              |
|  |   Service   |    |   Service   |    |   Service   |              |
|  +-------------+    +-------------+    +-------------+              |
|           |                  |                  |                     |
|           v                  v                  v                     |
|  +-----------------------------------------------------------------+  |
|  |                      DATA LAYER                                 |  |
|  |                                                                 |  |
|  |  +-------------+  +-------------+  +-------------+            |  |
|  |  | PostgreSQL  |  |    Redis    |  |Elasticsearch|            |  |
|  |  |  (Primary)  |  |   (Cache)   |  |  (Search)   |            |  |
|  |  +-------------+  +-------------+  +-------------+            |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                              |                                         |
|                              v                                         |
|  +-----------------------------------------------------------------+  |
|  |                    MESSAGE QUEUE (Kafka)                        |  |
|  |            [Events] [Notifications] [Analytics]                |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.2: COMPONENT DEEP DIVE

### CLIENT LAYER

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CLIENTS                                                               |
|                                                                         |
|  MOBILE APPS (iOS, Android)                                           |
|  ------------------------------                                         |
|  * Native apps for best UX                                            |
|  * Offline caching for movie info                                     |
|  * Push notifications for reminders                                   |
|  * QR code scanner for ticket entry                                   |
|                                                                         |
|  WEB APPLICATION                                                       |
|  ----------------                                                       |
|  * Responsive SPA (React/Vue)                                         |
|  * SEO for movie pages                                                |
|  * PWA for mobile web experience                                      |
|                                                                         |
|  PARTNER APIs                                                          |
|  -------------                                                          |
|  * B2B integrations (Paytm, Google Pay)                              |
|  * Affiliate partners                                                 |
|  * Corporate booking portals                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### EDGE LAYER

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CDN (Content Delivery Network)                                       |
|  ===============================                                        |
|                                                                         |
|  PURPOSE:                                                              |
|  Serve static content from edge locations close to users.            |
|                                                                         |
|  WHAT IT SERVES:                                                       |
|  * Movie posters and banners                                          |
|  * Venue photos                                                       |
|  * JavaScript, CSS bundles                                            |
|  * Static HTML pages                                                  |
|                                                                         |
|  BENEFITS:                                                             |
|  * Reduces latency (served from nearby edge)                         |
|  * Reduces load on origin servers                                     |
|  * Handles traffic spikes                                             |
|                                                                         |
|  PROVIDERS: CloudFront, Cloudflare, Akamai                            |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  LOAD BALANCER                                                         |
|  =============                                                          |
|                                                                         |
|  TYPE: Layer 7 (Application Layer)                                    |
|                                                                         |
|  RESPONSIBILITIES:                                                     |
|  * Distribute traffic across API Gateway instances                   |
|  * SSL termination                                                    |
|  * Health checks                                                      |
|  * Geographic routing (route to nearest datacenter)                  |
|                                                                         |
|  ALGORITHM: Least connections (for even distribution)                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### API GATEWAY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  API GATEWAY                                                           |
|  ===========                                                            |
|                                                                         |
|  The API Gateway is the single entry point for all API requests.      |
|  It handles cross-cutting concerns.                                   |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Request --> [Rate Limit] --> [Auth] --> [Route] --> Service  |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  RESPONSIBILITIES:                                                     |
|                                                                         |
|  1. AUTHENTICATION                                                     |
|     Validate JWT tokens                                               |
|     Extract user context from token                                   |
|     Pass user info to downstream services                            |
|                                                                         |
|  2. RATE LIMITING                                                      |
|     +------------------------------------------------------------+    |
|     | Endpoint              | Rate Limit                        |    |
|     +------------------------------------------------------------+    |
|     | /api/search           | 100 req/min per IP                |    |
|     | /api/shows/{id}/seats | 30 req/min per user               |    |
|     | /api/bookings         | 10 req/min per user               |    |
|     | /api/payments         | 5 req/min per user                |    |
|     +------------------------------------------------------------+    |
|                                                                         |
|  3. REQUEST ROUTING                                                    |
|     Route to appropriate microservice based on path                  |
|     /api/users/*     > User Service                                  |
|     /api/movies/*    > Catalog Service                               |
|     /api/bookings/*  > Booking Service                               |
|                                                                         |
|  4. REQUEST/RESPONSE TRANSFORMATION                                   |
|     Add request IDs for tracing                                       |
|     Compress responses                                                |
|     Format errors consistently                                        |
|                                                                         |
|  5. VIRTUAL WAITING ROOM (for flash sales)                           |
|     Queue excess traffic during high-demand events                   |
|     Fair queuing based on arrival time                               |
|                                                                         |
|  IMPLEMENTATIONS: Kong, AWS API Gateway, NGINX                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### MICROSERVICES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MICROSERVICES                                                         |
|                                                                         |
|  1. USER SERVICE                                                       |
|  ===============                                                        |
|  Manages user accounts and authentication.                            |
|                                                                         |
|  Endpoints:                                                            |
|  * POST /users/register                                               |
|  * POST /users/login                                                  |
|  * GET /users/profile                                                 |
|  * PUT /users/preferences                                             |
|                                                                         |
|  Data:                                                                 |
|  * User profiles                                                      |
|  * Authentication tokens                                              |
|  * Preferences (location, language)                                  |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. CATALOG SERVICE                                                    |
|  ==================                                                     |
|  Manages movies, events, venues, and shows.                           |
|                                                                         |
|  Endpoints:                                                            |
|  * GET /movies (list with filters)                                   |
|  * GET /movies/{id}                                                   |
|  * GET /movies/{id}/shows                                            |
|  * GET /venues                                                        |
|  * GET /shows/{id}                                                    |
|                                                                         |
|  Data:                                                                 |
|  * Movie metadata (title, cast, ratings)                             |
|  * Venue information (name, location, seat layout)                   |
|  * Show schedules                                                     |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. BOOKING SERVICE  (Most Critical)                                |
|  =======================================                                |
|  Handles seat selection and booking flow.                             |
|                                                                         |
|  Endpoints:                                                            |
|  * GET /shows/{id}/seats (get seat availability)                     |
|  * POST /reservations (lock seats temporarily)                       |
|  * POST /bookings (confirm booking after payment)                    |
|  * DELETE /reservations/{id} (release seats)                         |
|  * GET /bookings (user's bookings)                                   |
|                                                                         |
|  Data:                                                                 |
|  * Seat availability (real-time)                                      |
|  * Reservations (temporary locks)                                     |
|  * Bookings (confirmed purchases)                                    |
|                                                                         |
|  CRITICAL REQUIREMENTS:                                               |
|  * No double-booking                                                  |
|  * Fast seat locking                                                  |
|  * Automatic lock expiry                                              |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  4. PAYMENT SERVICE                                                    |
|  ==================                                                     |
|  Integrates with payment gateways.                                    |
|                                                                         |
|  Endpoints:                                                            |
|  * POST /payments/initiate                                            |
|  * POST /payments/callback (webhook from gateway)                    |
|  * GET /payments/{id}/status                                          |
|  * POST /payments/{id}/refund                                        |
|                                                                         |
|  Integrations:                                                         |
|  * Razorpay, PayU, Paytm                                             |
|  * Credit/Debit cards                                                 |
|  * UPI (India)                                                        |
|  * Wallets                                                            |
|                                                                         |
|  REQUIREMENTS:                                                         |
|  * Idempotent operations (handle duplicate callbacks)                |
|  * PCI-DSS compliance                                                 |
|  * Retry failed payments                                              |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  5. SEARCH SERVICE                                                     |
|  =================                                                      |
|  Provides fast search capabilities.                                   |
|                                                                         |
|  Endpoints:                                                            |
|  * GET /search?q=avengers&city=mumbai                                |
|  * GET /search/suggest (autocomplete)                                |
|                                                                         |
|  Features:                                                             |
|  * Full-text search                                                   |
|  * Faceted search (filters)                                          |
|  * Autocomplete                                                       |
|  * Spell correction                                                   |
|  * Relevance ranking                                                  |
|                                                                         |
|  Backend: Elasticsearch                                               |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  6. NOTIFICATION SERVICE                                              |
|  =========================                                              |
|  Sends notifications to users.                                        |
|                                                                         |
|  Channels:                                                             |
|  * Email (booking confirmation, e-ticket)                            |
|  * SMS (OTP, booking confirmation)                                   |
|  * Push notifications (reminders)                                    |
|                                                                         |
|  Pattern: Async via message queue                                     |
|  Booking Service > Kafka > Notification Service > Send              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DATA LAYER

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DATA STORES                                                           |
|                                                                         |
|  1. POSTGRESQL (Primary Database)                                     |
|  ================================                                       |
|                                                                         |
|  WHY POSTGRESQL?                                                       |
|  * ACID compliance (critical for booking)                             |
|  * Row-level locking (SELECT FOR UPDATE)                             |
|  * Mature, reliable, well-understood                                 |
|  * Good performance with proper indexing                             |
|                                                                         |
|  TABLES:                                                               |
|  * users, user_preferences                                            |
|  * movies, events, genres                                             |
|  * venues, screens, seat_templates                                    |
|  * shows, show_seats                                                  |
|  * reservations, bookings, booking_items                             |
|  * payments, refunds                                                  |
|                                                                         |
|  SCALING:                                                              |
|  * Read replicas for read-heavy queries                              |
|  * Sharding by city/region for large scale                          |
|  * Partitioning for historical data (old shows)                      |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. REDIS (Cache + Distributed Lock)                                  |
|  ===================================                                    |
|                                                                         |
|  USE CASES:                                                            |
|                                                                         |
|  a) CACHING                                                            |
|     * Movie details (rarely changes)                                  |
|     * Venue information                                               |
|     * Show listings                                                   |
|     * User sessions                                                   |
|                                                                         |
|  b) SEAT AVAILABILITY (Real-time)                                     |
|     * Bitmap for each show's seat availability                       |
|     * Fast reads: Is seat A5 available?                              |
|     * Fast updates: Mark A5 as locked                                |
|                                                                         |
|  c) DISTRIBUTED LOCKING                                               |
|     * Lock seats during reservation                                   |
|     * Prevent race conditions                                         |
|     * Auto-expiry for abandoned locks                                |
|                                                                         |
|  d) RATE LIMITING                                                      |
|     * Token bucket counters                                           |
|     * Track requests per user/IP                                     |
|                                                                         |
|  CONFIGURATION:                                                        |
|  * Redis Cluster (for high availability)                             |
|  * Persistence: RDB snapshots (for recovery)                         |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. ELASTICSEARCH (Search)                                            |
|  =========================                                              |
|                                                                         |
|  INDEXES:                                                              |
|  * movies (title, cast, genres, language, ratings)                   |
|  * events (name, category, artists, venue)                           |
|  * venues (name, city, area)                                         |
|                                                                         |
|  FEATURES USED:                                                        |
|  * Full-text search with analyzers                                   |
|  * Fuzzy matching for typos                                          |
|  * Aggregations for filters                                          |
|  * Geo queries for nearby venues                                     |
|                                                                         |
|  DATA SYNC:                                                            |
|  PostgreSQL > Debezium (CDC) > Kafka > Elasticsearch                 |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  4. KAFKA (Message Queue)                                             |
|  =========================                                              |
|                                                                         |
|  TOPICS:                                                               |
|  * booking.created     > Trigger notification                        |
|  * booking.confirmed   > Analytics, loyalty points                   |
|  * payment.completed   > Finalize booking                            |
|  * seat.availability   > Real-time updates to clients               |
|                                                                         |
|  WHY KAFKA?                                                            |
|  * High throughput                                                    |
|  * Message replay (debug issues)                                     |
|  * Multiple consumers per topic                                      |
|  * Ordering within partitions                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.3: DATA FLOW DIAGRAMS

### SEARCH FLOW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  USER SEARCHES FOR "AVENGERS IN MUMBAI"                               |
|                                                                         |
|  +----------------------------------------------------------------+   |
|  |                                                                |   |
|  |  User                                                          |   |
|  |   |                                                            |   |
|  |   |  GET /search?q=avengers&city=mumbai                       |   |
|  |   v                                                            |   |
|  |  API Gateway                                                   |   |
|  |   |                                                            |   |
|  |   |  1. Validate token                                        |   |
|  |   |  2. Rate limit check                                      |   |
|  |   v                                                            |   |
|  |  Search Service                                                |   |
|  |   |                                                            |   |
|  |   |  3. Query Elasticsearch                                   |   |
|  |   |     - Match "avengers" in title                           |   |
|  |   |     - Filter by city "mumbai"                             |   |
|  |   |     - Sort by relevance                                   |   |
|  |   v                                                            |   |
|  |  Elasticsearch                                                 |   |
|  |   |                                                            |   |
|  |   |  Returns: [Avengers Endgame, Avengers Infinity War, ...]  |   |
|  |   v                                                            |   |
|  |  Search Service                                                |   |
|  |   |                                                            |   |
|  |   |  4. Enrich with cache data (ratings, images)              |   |
|  |   v                                                            |   |
|  |  Redis Cache                                                   |   |
|  |   |                                                            |   |
|  |   v                                                            |   |
|  |  Response: { movies: [...], venues: [...] }                   |   |
|  |                                                                |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
|  LATENCY TARGET: < 200ms                                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SEAT SELECTION FLOW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  USER VIEWS SEAT MAP FOR A SHOW                                       |
|                                                                         |
|  +----------------------------------------------------------------+   |
|  |                                                                |   |
|  |  User                                                          |   |
|  |   |                                                            |   |
|  |   |  GET /shows/123/seats                                     |   |
|  |   v                                                            |   |
|  |  Booking Service                                               |   |
|  |   |                                                            |   |
|  |   |  1. Get seat layout (venue template)                      |   |
|  |   v                                                            |   |
|  |  Redis: venue:456:layout > seat positions, categories        |   |
|  |   |                                                            |   |
|  |   |  2. Get real-time availability                            |   |
|  |   v                                                            |   |
|  |  Redis: show:123:seats > bitmap of availability               |   |
|  |   |                                                            |   |
|  |   |     Bit 0 = A1, Bit 1 = A2, ...                           |   |
|  |   |     0 = available, 1 = taken/locked                       |   |
|  |   |                                                            |   |
|  |   |  3. Merge layout + availability                           |   |
|  |   v                                                            |   |
|  |  Response:                                                     |   |
|  |  {                                                             |   |
|  |    seats: [                                                    |   |
|  |      { id: "A1", row: "A", number: 1, status: "available",   |   |
|  |        category: "GOLD", price: 300 },                        |   |
|  |      { id: "A2", row: "A", number: 2, status: "booked", ... },|   |
|  |      { id: "A3", row: "A", number: 3, status: "locked", ... } |   |
|  |    ]                                                           |   |
|  |  }                                                             |   |
|  |                                                                |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
|  LATENCY TARGET: < 500ms                                              |
|                                                                         |
|  REAL-TIME UPDATES:                                                    |
|  WebSocket connection pushes availability changes                     |
|  When another user books > push update to all viewing users          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.4: TECHNOLOGY CHOICES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TECHNOLOGY STACK                                                      |
|                                                                         |
|  COMPONENT              | TECHNOLOGY        | REASONING                |
|  ===================================================================   |
|  API Gateway            | Kong / NGINX      | Mature, extensible       |
|  Services               | Java/Spring Boot  | Strong typing, tooling   |
|  Primary Database       | PostgreSQL        | ACID, reliability        |
|  Cache                  | Redis Cluster     | Speed, atomic ops        |
|  Search                 | Elasticsearch     | Full-text, scalable      |
|  Message Queue          | Kafka             | Throughput, replay       |
|  CDN                    | CloudFront        | Global edge network      |
|  Container Orchestration| Kubernetes        | Scaling, self-healing    |
|  Monitoring             | Prometheus+Grafana| Metrics, alerting        |
|  Logging                | ELK Stack         | Centralized logs         |
|  Tracing                | Jaeger            | Distributed tracing      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ARCHITECTURE - KEY TAKEAWAYS                                         |
|                                                                         |
|  LAYERS                                                                |
|  ------                                                                |
|  * CDN: Static content                                                |
|  * API Gateway: Auth, rate limiting, routing                         |
|  * Microservices: Domain-specific logic                              |
|  * Data Layer: PostgreSQL, Redis, Elasticsearch                      |
|  * Messaging: Kafka for async communication                          |
|                                                                         |
|  CRITICAL SERVICES                                                     |
|  -----------------                                                     |
|  * Booking Service: The heart of the system                          |
|  * Payment Service: PCI-compliant, idempotent                        |
|                                                                         |
|  DATA STORES                                                           |
|  -----------                                                           |
|  * PostgreSQL: Source of truth (bookings, payments)                  |
|  * Redis: Real-time data (availability, locks)                       |
|  * Elasticsearch: Search (movies, events)                            |
|                                                                         |
|  INTERVIEW TIP                                                         |
|  -------------                                                         |
|  Draw the architecture diagram first.                                |
|  Explain each component's role clearly.                              |
|  Highlight the Booking Service as most critical.                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 2

