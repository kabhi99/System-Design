# NEARBY FRIENDS SYSTEM DESIGN (FACEBOOK / WHATSAPP LIVE LOCATION)
*Complete Design: Requirements, Architecture, and Interview Guide*

Nearby Friends lets users see which of their friends are geographically
close in real-time. Unlike a proximity service that searches static POIs,
this system tracks continuously moving users who explicitly opt in to share
their live location with friends. The core challenge is computing proximity
over millions of simultaneously moving entities with low latency, strong
privacy guarantees, and minimal battery drain.

## SECTION 1: UNDERSTANDING THE PROBLEM

### WHAT IS NEARBY FRIENDS?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Nearby Friends answers the question:                                   |
|  "Which of my friends are near me RIGHT NOW?"                           |
|                                                                         |
|  USER EXPERIENCE:                                                       |
|  1. Open the app (Facebook, WhatsApp, Snapchat)                         |
|  2. Tap "Share Live Location" - choose friends and duration             |
|  3. App begins sending your GPS coordinates periodically                |
|  4. Friends who are also sharing see each other on a map                |
|  5. Friends within a configurable radius get highlighted                |
|  6. When sharing expires or user stops, location is no longer visible   |
|                                                                         |
|  REAL-WORLD EXAMPLES:                                                   |
|  * Facebook Nearby Friends - see which friends are nearby               |
|  * WhatsApp Live Location  - share real-time location in a chat         |
|  * Snapchat Snap Map       - see friends on a map in real-time          |
|  * Apple Find My Friends   - locate friends and family                  |
|  * Google Maps Location Sharing - share live location                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHY IS THIS HARD TO BUILD?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KEY CHALLENGES:                                                        |
|                                                                         |
|  1. CONSTANTLY MOVING ENTITIES                                          |
|  ------------------------------                                         |
|  Unlike Yelp (static businesses), every user is moving.                 |
|  Location data is stale within seconds.                                 |
|  Must process millions of location updates per second.                  |
|                                                                         |
|  2. REAL-TIME PROXIMITY COMPUTATION                                     |
|  -----------------------------------                                    |
|  When user A moves, need to check if A is now near any friend.          |
|  If user A has 500 friends, and each friend is moving too,              |
|  the naive approach explodes combinatorially.                           |
|                                                                         |
|  3. BATTERY DRAIN                                                       |
|  ----------------                                                       |
|  GPS polling every few seconds kills battery in hours.                  |
|  Must be smart about when and how often to poll GPS.                    |
|  Users will uninstall if the app drains their battery.                  |
|                                                                         |
|  4. PRIVACY IS PARAMOUNT                                                |
|  -----------------------                                                |
|  Location is the most sensitive data category.                          |
|  Users must have full control: who sees them, for how long.             |
|  Must comply with GDPR, CCPA, and regional privacy laws.                |
|  A privacy breach here is front-page news.                              |
|                                                                         |
|  5. SCALE - EVERYONE AT ONCE                                            |
|  ----------------------------                                           |
|  100M+ daily active users, many sharing simultaneously.                 |
|  New Year's Eve, concerts, festivals - massive spikes.                  |
|  Must handle bursty traffic gracefully.                                 |
|                                                                         |
|  6. BIDIRECTIONAL SHARING                                               |
|  -------------------------                                              |
|  Both users must consent. If A shares with B, B might not               |
|  share back. Sharing is not symmetric - it's per-pair.                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2: REQUIREMENTS

### FUNCTIONAL REQUIREMENTS

```
+--------------------------------------------------------------------------+
|                                                                          |
|  CORE FEATURES:                                                          |
|                                                                          |
|  1. SHARE LIVE LOCATION                                                  |
|     * Start/stop sharing with selected friends                           |
|     * Set duration: 15 min, 1 hour, 8 hours, indefinite                  |
|     * Auto-expire when duration ends                                     |
|                                                                          |
|  2. SEE NEARBY FRIENDS ON MAP                                            |
|     * Display friends currently sharing within your radius               |
|     * Show friend's name, distance, last updated time                    |
|     * Real-time movement on the map                                      |
|                                                                          |
|  3. CONFIGURABLE RADIUS                                                  |
|     * User sets "nearby" threshold: 1 km, 5 km, 10 km, etc.              |
|     * Default radius based on density (urban vs rural)                   |
|                                                                          |
|  4. PRIVACY CONTROLS                                                     |
|     * Share with ALL friends, SPECIFIC friends, or NOBODY                |
|     * Ghost mode - appear offline even while using the app               |
|     * Approximate location - city-level instead of exact GPS             |
|     * View who can see your location                                     |
|                                                                          |
|  5. NOTIFICATIONS                                                        |
|     * Alert when a friend arrives nearby                                 |
|     * Alert when a friend leaves the area                                |
|     * Configurable notification preferences                              |
|                                                                          |
+--------------------------------------------------------------------------+
```

### NON-FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PERFORMANCE:                                                           |
|  * Location update propagation: < 10 seconds end-to-end                 |
|  * Nearby friend list refresh: < 5 seconds                              |
|  * Map rendering with friend locations: < 2 seconds                     |
|                                                                         |
|  SCALE:                                                                 |
|  * 100 million daily active users (DAU)                                 |
|  * 10 million concurrent location sharers at peak                       |
|  * Average 400 friends per user                                         |
|                                                                         |
|  RELIABILITY:                                                           |
|  * Location updates should not be lost                                  |
|  * Graceful degradation under extreme load                              |
|  * Eventually consistent is acceptable (not banking)                    |
|                                                                         |
|  BATTERY:                                                               |
|  * < 5% additional battery drain per hour of active sharing             |
|  * Adaptive GPS polling to minimize drain                               |
|  * Must not keep device awake unnecessarily                             |
|                                                                         |
|  PRIVACY:                                                               |
|  * No location stored longer than necessary                             |
|  * GDPR / CCPA compliant - right to deletion                            |
|  * End-to-end encryption for location data in transit                   |
|  * Location history auto-purged after sharing ends                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3: BACK-OF-ENVELOPE ESTIMATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  USERS AND UPDATES:                                                     |
|  * 100M DAU, 10% sharing at any time = 10M concurrent sharers           |
|  * Each sharer sends update every ~30 seconds on average                |
|  * Location updates/sec = 10M / 30 = ~333,000 updates/sec               |
|  * Peak (2x average) = ~666,000 updates/sec                             |
|                                                                         |
|  STORAGE PER UPDATE:                                                    |
|  * user_id (8B) + lat (8B) + lng (8B) + timestamp (8B)                  |
|    + geohash (8B) + accuracy (4B) + metadata (20B) ~ 64 bytes           |
|                                                                         |
|  LOCATION CACHE SIZE:                                                   |
|  * Only store LATEST location per active sharer                         |
|  * 10M sharers x 64 bytes = 640 MB (fits in Redis easily)               |
|                                                                         |
|  BANDWIDTH:                                                             |
|  * Ingestion: 333K updates/sec x 64 bytes = ~21 MB/sec inbound          |
|  * Fan-out: each update may notify ~20 nearby friends                   |
|  * Fan-out bandwidth: 333K x 20 x 64 bytes = ~426 MB/sec outbound       |
|  * This is the expensive part - fan-out dominates                       |
|                                                                         |
|  PUB/SUB CHANNELS:                                                      |
|  * 10M active sharers = 10M channels                                    |
|  * Average subscribers per channel: ~20 (mutual sharing friends)        |
|  * Total subscriptions: 10M x 20 = 200M active subscriptions            |
|                                                                         |
|  FRIEND LIST LOOKUPS:                                                   |
|  * 333K location updates/sec > 333K friend list lookups/sec             |
|  * Friend list: 400 friends avg x 8 bytes = 3.2 KB per user             |
|  * Cache all active users' friend lists: 10M x 3.2 KB = 32 GB           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4: HIGH-LEVEL ARCHITECTURE

```
+--------------------------------------------------------------------------+
|                          HIGH-LEVEL ARCHITECTURE                         |
+--------------------------------------------------------------------------+
|                                                                          |
|  +------------+         +-------------------+                            |
|  |   Mobile   | ------> | Load Balancer /   |                            |
|  |   Client   | <------ | API Gateway       |                            |
|  +------------+         +-------------------+                            |
|        |                    |           |                                |
|        |                    v           v                                |
|        |          +-----------+   +------------+                         |
|        |          | Location  |   | Friend     |                         |
|        |          | Ingestion |   | Service    |                         |
|        |          | Service   |   | (social    |                         |
|        |          |           |   |  graph)    |                         |
|        |          +-----------+   +------------+                         |
|        |               |               |                                 |
|        |               v               v                                 |
|        |        +-------------+  +------------+                          |
|        |        | Location    |  | Friend     |                          |
|        |        | Cache       |  | Cache      |                          |
|        |        | (Redis)     |  | (Redis)    |                          |
|        |        +-------------+  +------------+                          |
|        |               |                                                 |
|        |               v                                                 |
|        |        +------------------+                                     |
|        |        | Proximity        |                                     |
|        |        | Calculation      |                                     |
|        |        | Service          |                                     |
|        |        +------------------+                                     |
|        |               |                                                 |
|        |               v                                                 |
|        |        +------------------+                                     |
|        |        | Pub/Sub Layer    |                                     |
|   WebSocket     | (Redis Pub/Sub   |                                     |
|   Connection    |  or Kafka)       |                                     |
|        |        +------------------+                                     |
|        |               |                                                 |
|        |               v                                                 |
|        |        +------------------+                                     |
|        +------> | WebSocket        |                                     |
|                 | Gateway          |                                     |
|                 | (push to clients)|                                     |
|                 +------------------+                                     |
|                                                                          |
+--------------------------------------------------------------------------+
```

### DATA FLOW OVERVIEW

```
+--------------------------------------------------------------------------+
|                                                                          |
|  1. LOCATION UPDATE FLOW:                                                |
|                                                                          |
|  Mobile GPS --> Location Ingestion --> Location Cache (Redis)            |
|                        |                                                 |
|                        v                                                 |
|                  Pub/Sub Channel --> Subscribed Friends --> WebSocket    |
|                                                                          |
|  2. NEARBY FRIENDS QUERY FLOW:                                           |
|                                                                          |
|  Client Request --> API Gateway --> Friend Service (get friend list)     |
|                                         |                                |
|                                         v                                |
|                               Location Cache (get each friend's loc)     |
|                                         |                                |
|                                         v                                |
|                               Proximity Calc (filter by radius)          |
|                                         |                                |
|                                         v                                |
|                               Return nearby friends list to client       |
|                                                                          |
|  3. SUBSCRIPTION MANAGEMENT:                                             |
|                                                                          |
|  User starts sharing --> Subscribe friends to user's channel             |
|  User stops sharing  --> Unsubscribe all from user's channel             |
|  User moves geohash  --> Update channel, resubscribe                     |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 5: DEEP DIVE - LOCATION INGESTION

### HOW MOBILE SENDS LOCATION UPDATES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LOCATION UPDATE PAYLOAD:                                               |
|                                                                         |
|  {                                                                      |
|    "user_id":    "u_abc123",                                            |
|    "latitude":   37.7749,                                               |
|    "longitude": -122.4194,                                              |
|    "accuracy":   15,            // meters                               |
|    "speed":      2.5,           // m/s                                  |
|    "bearing":    180,           // degrees                              |
|    "timestamp":  1709312400,    // epoch seconds                        |
|    "battery":    72,            // percent - server uses for adaptive   |
|    "source":     "gps"          // gps | wifi | cell                    |
|  }                                                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### TRANSPORT PROTOCOL: HTTP VS WEBSOCKET

```
+-------------------------------------------------------------------------+
|                                                                         |
|  OPTION A: HTTP (REST)                                                  |
|  ----------------------                                                 |
|  POST /v1/location                                                      |
|                                                                         |
|  Pros:                                                                  |
|  + Simple, stateless, works through all proxies                         |
|  + Easy to batch multiple updates in one request                        |
|  + Standard retry and error handling                                    |
|                                                                         |
|  Cons:                                                                  |
|  * TCP + TLS handshake overhead per request                             |
|  * HTTP headers add ~200-500 bytes per request                          |
|  * Higher latency for real-time push back to client                     |
|                                                                         |
|  OPTION B: WEBSOCKET (BIDIRECTIONAL)                                    |
|  ------------------------------------                                   |
|  Persistent connection for both send and receive                        |
|                                                                         |
|  Pros:                                                                  |
|  + Single connection for upload AND download                            |
|  + Low overhead per message (~6 bytes framing)                          |
|  + Server can push friend location updates instantly                    |
|                                                                         |
|  Cons:                                                                  |
|  * Stateful - harder to load balance                                    |
|  * Connection drops on network switch (WiFi - cellular)                 |
|  * More complex infrastructure                                          |
|                                                                         |
|  RECOMMENDED: WEBSOCKET                                                 |
|  Since we need real-time push for friend updates anyway,                |
|  use WebSocket for both upload and download.                            |
|  Fall back to HTTP polling if WebSocket unavailable.                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### ADAPTIVE UPDATE FREQUENCY

```
+--------------------------------------------------------------------------+
|                                                                          |
|  PROBLEM: Fixed-interval GPS polling wastes battery.                     |
|                                                                          |
|  SOLUTION: Adapt frequency based on movement and context.                |
|                                                                          |
|  +-------------------+----------------+-------------------+              |
|  | USER STATE        | GPS INTERVAL   | RATIONALE         |              |
|  +-------------------+----------------+-------------------+              |
|  | Walking (>1 m/s)  | Every 10 sec   | Position changes  |              |
|  |                   |                | meaningfully       |             |
|  +-------------------+----------------+-------------------+              |
|  | Driving (>10 m/s) | Every 5 sec    | Fast movement,    |              |
|  |                   |                | need frequent      |             |
|  +-------------------+----------------+-------------------+              |
|  | Stationary        | Every 60 sec   | Minimal change,   |              |
|  |                   |                | save battery       |             |
|  +-------------------+----------------+-------------------+              |
|  | Low battery (<20%)| Every 120 sec  | Preserve battery  |              |
|  +-------------------+----------------+-------------------+              |
|  | Background app    | Significant    | OS-level events   |              |
|  |                   | change only    | only               |             |
|  +-------------------+----------------+-------------------+              |
|                                                                          |
|  HOW TO DETECT MOVEMENT:                                                 |
|  * Compare consecutive GPS readings                                      |
|  * Use accelerometer (no GPS needed) to detect motion                    |
|  * iOS: CMMotionActivityManager                                          |
|  * Android: ActivityRecognitionClient                                    |
|                                                                          |
+--------------------------------------------------------------------------+
```

### BATCH UPLOADS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Instead of sending each GPS reading individually, batch them:          |
|                                                                         |
|  CLIENT BUFFER:                                                         |
|  +------+------+------+------+                                          |
|  | loc1 | loc2 | loc3 | loc4 |  ---- flush every 30 sec -->  Server     |
|  +------+------+------+------+                                          |
|                                                                         |
|  FLUSH TRIGGERS:                                                        |
|  1. Timer expires (every 30 seconds)                                    |
|  2. Buffer full (e.g., 10 locations)                                    |
|  3. Significant movement detected (>100m from last sent)                |
|  4. User opens the app (need fresh data)                                |
|                                                                         |
|  BENEFITS:                                                              |
|  * Fewer network requests > less battery drain                          |
|  * Fewer TCP/TLS handshakes                                             |
|  * Server can process in bulk                                           |
|  * Network-efficient: one 640-byte batch vs ten 64-byte singles         |
|                                                                         |
|  SERVER PROCESSING:                                                     |
|  * Extract latest location from batch                                   |
|  * Update cache with latest only (older readings discarded)             |
|  * Log all readings to cold storage for analytics (optional)            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6: DEEP DIVE - PROXIMITY CALCULATION

### APPROACH 1: BRUTE FORCE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ALGORITHM:                                                             |
|  For each user requesting nearby friends:                               |
|    1. Get user's friend list (e.g., 400 friends)                        |
|    2. For each friend, get their latest location from cache             |
|    3. Compute Haversine distance between user and friend                |
|    4. Filter friends within radius (e.g., 5 km)                         |
|    5. Return matching friends sorted by distance                        |
|                                                                         |
|  COMPLEXITY: O(F) per query where F = number of friends                 |
|                                                                         |
|  +--------+      get friends      +---------+                           |
|  | User A | ------------------->  | Friend  |                           |
|  | (query)|      [B, C, D, ...]   | Service |                           |
|  +--------+                       +---------+                           |
|      |                                                                  |
|      | for each friend, get location                                    |
|      v                                                                  |
|  +------------------+                                                   |
|  | Location Cache   |   B: (37.77, -122.41)                             |
|  | (Redis)          |   C: (37.78, -122.42)                             |
|  |                  |   D: (offline / no data)                          |
|  +------------------+                                                   |
|      |                                                                  |
|      | compute distance for each                                        |
|      v                                                                  |
|  dist(A,B) = 1.2 km  Y within 5 km                                      |
|  dist(A,C) = 2.4 km  Y within 5 km                                      |
|  dist(A,D) = N/A      (offline)                                         |
|                                                                         |
|  PROS:                                                                  |
|  + Simple to implement and reason about                                 |
|  + Works perfectly for moderate friend counts (<1000)                   |
|  + No complex spatial indexing needed                                   |
|  + Each query is independent - easy to parallelize                      |
|                                                                         |
|  CONS:                                                                  |
|  * Doesn't scale if friend lists grow very large                        |
|  * Still requires O(F) cache lookups per query                          |
|  * No spatial locality - cache misses spread across shards              |
|                                                                         |
|  VERDICT: Good enough for most cases. With 400 friends avg and          |
|  Redis sub-ms lookups, this takes <10ms per query. Start here.          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### APPROACH 2: GEOHASH-BASED PROXIMITY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  GEOHASH CONCEPT:                                                       |
|  Encode (lat, lng) into a string where shared prefix = nearby.          |
|                                                                         |
|  Precision table:                                                       |
|  +----------+-------------------+                                       |
|  | Length   | Cell Size (approx)|                                       |
|  +----------+-------------------+                                       |
|  | 4 chars  | 39 km x 19 km    |                                        |
|  | 5 chars  | 4.9 km x 4.9 km  |                                        |
|  | 6 chars  | 1.2 km x 0.6 km  |                                        |
|  | 7 chars  | 153 m x 153 m    |                                        |
|  +----------+-------------------+                                       |
|                                                                         |
|  ALGORITHM:                                                             |
|  1. Compute user's geohash at desired precision (e.g., 6 chars)         |
|  2. Get user's geohash + 8 neighboring geohashes (3x3 grid)             |
|  3. Look up all friends located in those 9 geohash cells                |
|  4. Compute exact distance only for friends in those cells              |
|                                                                         |
|  GEOHASH GRID (3x3 neighbors):                                          |
|  +--------+--------+--------+                                           |
|  | 9q8yy1 | 9q8yy2 | 9q8yy3 |                                           |
|  +--------+--------+--------+                                           |
|  | 9q8yy4 | 9q8yy5 | 9q8yy6 |   < User is in center cell                |
|  +--------+--------+--------+                                           |
|  | 9q8yy7 | 9q8yy8 | 9q8yy9 |                                           |
|  +--------+--------+--------+                                           |
|                                                                         |
|  DATA STRUCTURE IN REDIS:                                               |
|  Key: geohash:9q8yy5 > Set { user_B, user_C, user_F }                   |
|  Key: geohash:9q8yy4 > Set { user_D }                                   |
|                                                                         |
|  PROS:                                                                  |
|  + Filters candidates spatially before expensive distance calc          |
|  + Reduces computation when density is low                              |
|  + Well-understood algorithm                                            |
|                                                                         |
|  CONS:                                                                  |
|  * Must update geohash sets on every location change                    |
|  * Edge cases at geohash boundaries (neighbors fix this mostly)         |
|  * Still need friend-list intersection (spatial set ∩ friend set)       |
|  * Overhead of maintaining geohash-to-user mappings at scale            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### APPROACH 3: PUB/SUB CHANNELS PER GEOHASH

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CORE IDEA:                                                             |
|  Each geohash cell has a pub/sub channel. Users subscribe to the        |
|  geohash channels where their friends might be. When a friend           |
|  publishes their location, the subscriber receives it in real-time.     |
|                                                                         |
|  HOW IT WORKS:                                                          |
|                                                                         |
|  1. User A is in geohash "9q8yy5"                                       |
|  2. User A's friend B is in geohash "9q8yy4"                            |
|  3. User A subscribes to channels for B's current geohash               |
|     + neighboring geohashes                                             |
|  4. When B moves and publishes to "9q8yy4", A receives it               |
|  5. If B moves to a new geohash "9q8yz1", B publishes there             |
|     > A must update subscriptions accordingly                           |
|                                                                         |
|  +----------+                +------------------+                       |
|  | User A   | -- subscribes --> | Channel:        |                     |
|  | (in      |    to friend B's  | geohash:9q8yy4 |                      |
|  |  9q8yy5) |    geohash area   +------------------+                    |
|  +----------+                         ^                                 |
|                                       |                                 |
|  +----------+                         |                                 |
|  | User B   | -- publishes location --+                                 |
|  | (in      |    to own geohash                                         |
|  |  9q8yy4) |    channel                                                |
|  +----------+                                                           |
|                                                                         |
|  PROS:                                                                  |
|  + True real-time - push, not poll                                      |
|  + No periodic "check all friends" queries                              |
|  + Scales naturally with pub/sub infrastructure                         |
|                                                                         |
|  CONS:                                                                  |
|  * Complex subscription management when users move between cells        |
|  * Each geohash change = unsubscribe old channels + subscribe new       |
|  * Thundering herd if many users in one geohash (concert, stadium)      |
|  * Memory for millions of channels and subscriptions                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMPARISON OF APPROACHES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  +----------------+-------------+-------------+---------------+         |
|  | Criteria       | Brute Force | Geohash     | Pub/Sub +     |         |
|  |                |             | Lookup      | Geohash       |         |
|  +----------------+-------------+-------------+---------------+         |
|  | Latency        | Low (O(F))  | Low         | Lowest (push) |         |
|  | Complexity     | Simple      | Medium      | High          |         |
|  | Real-time      | Poll-based  | Poll-based  | Push-based    |         |
|  | Battery impact | Higher      | Medium      | Lowest        |         |
|  |                | (polling)   | (polling)   | (event-driven)|         |
|  | Scaling        | Good        | Good        | Best          |         |
|  | Fan-out cost   | Per-query   | Per-query   | Per-update    |         |
|  +----------------+-------------+-------------+---------------+         |
|                                                                         |
|  RECOMMENDED: HYBRID                                                    |
|  * Use Pub/Sub per user (not per geohash) for real-time updates         |
|  * Each user has a channel; friends subscribe to it                     |
|  * On location update, publish to user's channel                        |
|  * Subscribers receive it, compute distance client-side                 |
|  * Server-side geohash filtering to avoid sending irrelevant updates    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7: DEEP DIVE - PUB/SUB ARCHITECTURE

### PER-USER CHANNEL MODEL

```
+--------------------------------------------------------------------------+
|                                                                          |
|  DESIGN: Each sharing user gets a pub/sub channel.                       |
|  Friends who want updates subscribe to that channel.                     |
|                                                                          |
|  EXAMPLE:                                                                |
|  User A starts sharing with friends B, C, D:                             |
|                                                                          |
|  Channel: location:user_A                                                |
|  Subscribers: [user_B, user_C, user_D]                                   |
|                                                                          |
|  When A moves:                                                           |
|  A publishes > {lat, lng, timestamp} > Channel: location:user_A          |
|  > B, C, D all receive the update                                        |
|                                                                          |
|  LIFECYCLE:                                                              |
|                                                                          |
|  +----------+  start sharing   +-------------------+                     |
|  | User A   | --------------> | Create channel     |                     |
|  | taps     |                 | location:user_A    |                     |
|  | "Share"  |                 | Subscribe B, C, D  |                     |
|  +----------+                 +-------------------+                      |
|       |                                                                  |
|       | every N seconds                                                  |
|       v                                                                  |
|  +-----------+  publish   +-------------------+  deliver                 |
|  | GPS fix   | ---------> | Channel           | --------> B, C, D        |
|  | obtained  |            | location:user_A   |           (via WS)       |
|  +-----------+            +-------------------+                          |
|       |                                                                  |
|       | sharing expires                                                  |
|       v                                                                  |
|  +-----------+            +-------------------+                          |
|  | Timer     | ---------> | Delete channel    |                          |
|  | expires   |            | Unsubscribe all   |                          |
|  +-----------+            +-------------------+                          |
|                                                                          |
+--------------------------------------------------------------------------+
```

### SUBSCRIPTION MANAGEMENT

```
+--------------------------------------------------------------------------+
|                                                                          |
|  WHEN USER OPENS NEARBY FRIENDS:                                         |
|  1. Fetch friend list from Friend Service                                |
|  2. Filter to friends currently sharing (check sharing status cache)     |
|  3. Subscribe to each sharing friend's channel                           |
|  4. Fetch latest location for each from Location Cache (initial load)    |
|  5. Subsequent updates arrive via pub/sub in real-time                   |
|                                                                          |
|  SUBSCRIPTION BOOKKEEPING:                                               |
|                                                                          |
|  +-----------------------------------------------+                       |
|  | user_A subscribes to:                          |                      |
|  |   - location:user_B (friend, currently sharing)|                      |
|  |   - location:user_C (friend, currently sharing)|                      |
|  |                                                |                      |
|  | user_A does NOT subscribe to:                  |                      |
|  |   - location:user_D (friend, NOT sharing)      |                      |
|  |   - location:user_E (not a friend)             |                      |
|  +-----------------------------------------------+                       |
|                                                                          |
|  HANDLING CHANGES:                                                       |
|                                                                          |
|  Friend B stops sharing:                                                 |
|    > Server deletes channel location:user_B                              |
|    > All subscribers auto-disconnected                                   |
|    > A's client removes B from the map                                   |
|                                                                          |
|  Friend D starts sharing:                                                |
|    > Server notifies A: "D started sharing"                              |
|    > A subscribes to location:user_D                                     |
|    > D appears on A's map                                                |
|                                                                          |
+--------------------------------------------------------------------------+
```

### PUB/SUB INFRASTRUCTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  OPTION 1: REDIS PUB/SUB                                                |
|  -------------------------                                              |
|  + Ultra-low latency (<1ms publish-to-deliver)                          |
|  + Simple API: PUBLISH, SUBSCRIBE                                       |
|  + Battle-tested at scale                                               |
|  * Messages not persisted (if subscriber offline, message lost)         |
|  * Single-threaded per node - fan-out limited                           |
|  * No message ordering guarantees across nodes                          |
|                                                                         |
|  OPTION 2: DEDICATED PUB/SUB (e.g., custom built on Erlang/Elixir)      |
|  ------------------------------------------------------------------     |
|  + Purpose-built for millions of channels                               |
|  + Can handle connection management, presence, etc.                     |
|  + Facebook's real-time infra is custom-built                           |
|  * Complex to build and maintain                                        |
|                                                                         |
|  OPTION 3: KAFKA (message queue style)                                  |
|  --------------------------------------                                 |
|  + Persistent, replayable                                               |
|  + Strong ordering guarantees                                           |
|  * Higher latency (10-100ms)                                            |
|  * Not designed for millions of topics (one per user)                   |
|  * Overkill for ephemeral location data                                 |
|                                                                         |
|  RECOMMENDED: Redis Pub/Sub for location fan-out                        |
|  (ephemeral data, low-latency requirement, no replay needed).           |
|  Use Kafka for the ingestion pipeline if durability matters.            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CHANNEL MANAGEMENT ON GEOHASH CHANGE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  When a user moves to a new geohash cell, we can optionally             |
|  use geohash info to filter irrelevant updates server-side:             |
|                                                                         |
|  BEFORE MOVE:                                                           |
|  User B is in geohash 9q8yy5                                            |
|  User A (subscriber) is in geohash 9q8yy4 (neighbor - relevant)         |
|                                                                         |
|  AFTER MOVE:                                                            |
|  User B moves to geohash 9q8zz1 (far away)                              |
|                                                                         |
|  SERVER-SIDE OPTIMIZATION:                                              |
|  The pub/sub layer checks: is subscriber A's geohash a neighbor         |
|  of publisher B's new geohash?                                          |
|    * If YES: deliver the update                                         |
|    * If NO:  suppress the update (save bandwidth)                       |
|                                                                         |
|  This is OPTIONAL - the simple model delivers ALL friend updates        |
|  and lets the client filter. The optimization reduces fan-out           |
|  bandwidth at the cost of server-side geohash computation.              |
|                                                                         |
|  +----------+   update    +----------+   check geohash   +----------+   |
|  | User B   | ----------> | Pub/Sub  | ----------------> | Filter   |   |
|  | moved to |             | Channel  |   neighbor?        | Layer   |   |
|  | 9q8zz1   |             +----------+                   +----------+   |
|  +----------+                                             |    |        |
|                                                     YES   |    | NO     |
|                                                     v          v        |
|                                              +----------+ +---------+   |
|                                              | Deliver  | | Suppress|   |
|                                              | to sub A | | (save   |   |
|                                              +----------+ | BW)     |   |
|                                                           +---------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8: DEEP DIVE - LOCATION CACHE

### REDIS CACHE DESIGN

```
+--------------------------------------------------------------------------+
|                                                                          |
|  PRIMARY CACHE: Latest location per user (Redis)                         |
|  WHY REDIS? Location data is ephemeral (only current position            |
|  matters). 10M users sharing = 640 MB - fits in memory easily.           |
|  Sub-ms reads for "where is user X now?" lookups. TTL auto-cleans        |
|  stale locations when users stop sharing. Hash structure maps            |
|  naturally to lat/lng/timestamp per user.                                |
|                                                                          |
|  Key Pattern: loc:{user_id}                                              |
|  Value: Hash                                                             |
|    * lat: 37.7749                                                        |
|    * lng: -122.4194                                                      |
|    * geohash: 9q8yy5                                                     |
|    * timestamp: 1709312400                                               |
|    * accuracy: 15                                                        |
|    * speed: 2.5                                                          |
|  TTL: 600 seconds (10 minutes)                                           |
|                                                                          |
|  WHY TTL?                                                                |
|  * If no update in 10 min, consider user offline                         |
|  * Auto-cleanup - no stale data lingering                                |
|  * Each new update resets the TTL                                        |
|                                                                          |
|  SECONDARY INDEX: Geohash > users (optional, for geohash approach)       |
|                                                                          |
|  Key Pattern: geo:{geohash_prefix}                                       |
|  Value: Set of user_ids in that geohash cell                             |
|  TTL: 300 seconds (refreshed on each user update)                        |
|                                                                          |
|  FRIEND LIST CACHE:                                                      |
|                                                                          |
|  Key Pattern: friends:{user_id}                                          |
|  Value: Set of friend user_ids                                           |
|  TTL: 3600 seconds (1 hour, refreshed on access)                         |
|  Invalidated on friend add/remove events                                 |
|                                                                          |
|  SHARING STATUS CACHE:                                                   |
|                                                                          |
|  Key Pattern: sharing:{user_id}                                          |
|  Value: Hash                                                             |
|    * active: true                                                        |
|    * expires_at: 1709316000                                              |
|    * shared_with: [user_B, user_C]                                       |
|  TTL: matches sharing duration                                           |
|                                                                          |
+--------------------------------------------------------------------------+
```

### CACHE ACCESS PATTERNS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ON LOCATION UPDATE (write path):                                       |
|  1. SET loc:{user_id} with new coordinates + TTL reset                  |
|  2. If geohash changed:                                                 |
|     a. SREM geo:{old_geohash} user_id                                   |
|     b. SADD geo:{new_geohash} user_id                                   |
|  3. PUBLISH to location:{user_id} channel                               |
|                                                                         |
|  ON NEARBY FRIENDS QUERY (read path):                                   |
|  1. SMEMBERS friends:{user_id} > get friend list                        |
|  2. For each friend:                                                    |
|     a. EXISTS sharing:{friend_id} > is friend sharing?                  |
|     b. HGETALL loc:{friend_id} > get location                           |
|  3. Compute distance, filter by radius                                  |
|  4. Return sorted results                                               |
|                                                                         |
|  OPTIMIZATION - PIPELINE:                                               |
|  Instead of N individual Redis calls, use PIPELINE:                     |
|  Send all HGETALL commands in one batch > single round-trip             |
|                                                                         |
|  +--------+  1 pipeline request  +-------+  1 response                  |
|  | Server | ------------------> | Redis | ------------------->          |
|  |        |  (400 HGETALL cmds) |       |  (400 results)                |
|  +--------+                     +-------+                               |
|                                                                         |
|  Latency: ~2ms for 400 lookups (pipelined) vs ~400ms (sequential)       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 9: DEEP DIVE - PRIVACY

### PRIVACY CONTROLS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SHARING GRANULARITY:                                                   |
|                                                                         |
|  +---------------------+-------------------------------------------+    |
|  | Mode                | Description                               |    |
|  +---------------------+-------------------------------------------+    |
|  | Share with ALL      | All friends can see your location         |    |
|  | Share with LIST     | Only selected friends can see             |    |
|  | Ghost mode          | No one sees you, you can still see others |    |
|  | Approximate         | Shows city/neighborhood, not exact GPS    |    |
|  | Off                 | No sharing, no visibility                 |    |
|  +---------------------+-------------------------------------------+    |
|                                                                         |
|  TIME-LIMITED SHARING:                                                  |
|                                                                         |
|  User taps "Share" > selects duration:                                  |
|  +----------+----------+----------+----------+                          |
|  | 15 min   | 1 hour   | 8 hours  | Until I  |                          |
|  |          |          |          | turn off |                          |
|  +----------+----------+----------+----------+                          |
|                                                                         |
|  Server sets TTL on sharing status.                                     |
|  When TTL expires:                                                      |
|    > Channel torn down                                                  |
|    > Subscribers notified: "User A stopped sharing"                     |
|    > Location cache entry expires naturally                             |
|    > No manual cleanup needed                                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### APPROXIMATE LOCATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Some users want to share generally but not exactly.                    |
|                                                                         |
|  IMPLEMENTATION:                                                        |
|  * Instead of sharing (37.7749, -122.4194)                              |
|  * Share truncated geohash: "9q8y" > resolves to ~39 km2 area           |
|  * Client displays "In San Francisco" instead of a precise dot          |
|                                                                         |
|  PRECISION LEVELS:                                                      |
|  +-------------------+-------------------+------------------+           |
|  | Level             | Geohash Precision | Shows As         |           |
|  +-------------------+-------------------+------------------+           |
|  | Exact             | 7+ chars          | Pin on map       |           |
|  | Neighborhood      | 5 chars           | "In Mission Dist"|           |
|  | City              | 4 chars           | "In San Francisco|           |
|  | Region            | 3 chars           | "In Bay Area"    |           |
|  +-------------------+-------------------+------------------+           |
|                                                                         |
|  RANDOM OFFSET (alternative):                                           |
|  Add random ~500m to actual coordinates.                                |
|  Re-randomize every 30 min so it's not trackable.                       |
|  Simpler than geohash truncation but less predictable UX.               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### GDPR AND DATA COMPLIANCE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DATA LIFECYCLE:                                                        |
|                                                                         |
|  +----------+    +----------+    +----------+    +----------+           |
|  | Collect  | -> | Process  | -> | Store    | -> | Delete   |           |
|  | (GPS     |    | (compute |    | (Redis   |    | (TTL     |           |
|  |  from    |    |  prox-   |    |  cache,  |    |  expires,|           |
|  |  device) |    |  imity)  |    |  10 min  |    |  auto-   |           |
|  |          |    |          |    |  TTL)    |    |  purge)  |           |
|  +----------+    +----------+    +----------+    +----------+           |
|                                                                         |
|  GDPR REQUIREMENTS:                                                     |
|  * Explicit consent before any location collection                      |
|  * Right to be forgotten: delete all location data on request           |
|  * Data minimization: only collect what's needed                        |
|  * Purpose limitation: only use for nearby friends feature              |
|  * Data portability: export user's location history on request          |
|                                                                         |
|  IMPLEMENTATION:                                                        |
|  * No permanent location storage (cache with TTL only)                  |
|  * Consent stored in user profile: "location_sharing_consent": true     |
|  * Audit log: who accessed whose location, when                         |
|  * Anonymize/aggregate for analytics (no individual tracking)           |
|  * Regular privacy impact assessments                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 10: DEEP DIVE - BATTERY OPTIMIZATION

```
+--------------------------------------------------------------------------+
|                                                                          |
|  BATTERY COST OF GPS:                                                    |
|                                                                          |
|  +---------------------+------------------+-----------------+            |
|  | Location Source      | Accuracy         | Battery Cost    |           |
|  +---------------------+------------------+-----------------+            |
|  | GPS (fine)           | 5-10 meters      | HIGH            |           |
|  | WiFi positioning     | 15-40 meters     | MEDIUM          |           |
|  | Cell tower           | 100-300 meters   | LOW             |           |
|  | Passive (piggyback)  | Varies           | NEARLY FREE     |           |
|  +---------------------+------------------+-----------------+            |
|                                                                          |
|  STRATEGY 1: ADAPTIVE GPS FREQUENCY                                      |
|  (Already covered in Section 5)                                          |
|  * High frequency when moving, low when stationary                       |
|  * Use accelerometer to detect motion without GPS                        |
|                                                                          |
|  STRATEGY 2: SIGNIFICANT LOCATION CHANGE API                             |
|  -------------------------------------------                             |
|  iOS: CLLocationManager.startMonitoringSignificantLocationChanges()      |
|  Android: FusedLocationProviderClient with PRIORITY_BALANCED_POWER       |
|                                                                          |
|  * OS wakes the app only when user moves ~500m+                          |
|  * Uses cell tower + WiFi (no GPS)                                       |
|  * Battery cost: nearly zero                                             |
|  * Accuracy: ~100-300 meters (good enough for "nearby" at km scale)      |
|                                                                          |
|  STRATEGY 3: CELL TOWER TRIANGULATION                                    |
|  ------------------------------------                                    |
|  When exact GPS is not needed:                                           |
|  * Use cell tower + WiFi triangulation                                   |
|  * Sufficient for "nearby within 5 km" use case                          |
|  * Reserve GPS for "show me their exact position on map"                 |
|                                                                          |
|  STRATEGY 4: BATCH UPLOADS                                               |
|  (Already covered in Section 5)                                          |
|  * Buffer locations, send in batch                                       |
|  * Reduces radio wake-ups                                                |
|                                                                          |
|  STRATEGY 5: SMART WAKE SCHEDULING                                       |
|  ----------------------------------                                      |
|  * Align GPS polling with other app wake-ups (push notifications)        |
|  * Piggyback on other apps' location requests (passive location)         |
|  * iOS: allowDeferredLocationUpdates - batch GPS readings                |
|                                                                          |
|  BATTERY BUDGET EXAMPLE:                                                 |
|  +-------------------------------+------------------+                    |
|  | Scenario                      | Battery/hour     |                    |
|  +-------------------------------+------------------+                    |
|  | GPS every 5 sec (aggressive)  | ~15%             |                    |
|  | GPS every 30 sec (moderate)   | ~5%              |                    |
|  | Significant change only       | ~1%              |                    |
|  | Cell tower only               | ~0.5%            |                    |
|  +-------------------------------+------------------+                    |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 11: SCALING

### LOCATION INGESTION SCALING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CHALLENGE: 333K+ location updates per second at peak.                  |
|                                                                         |
|  +------------+     +----------------+     +------------------+         |
|  | Mobile     |     | Load Balancer  |     | Ingestion Fleet  |         |
|  | Clients    | --> | (L4, by conn)  | --> | (stateless,      |         |
|  | (millions) |     |                |     |  horizontally    |         |
|  +------------+     +----------------+     |  scalable)       |         |
|                                            +------------------+         |
|                                              |  |  |  |  |              |
|                                              v  v  v  v  v              |
|                                         +---------------------+         |
|                                         | Redis Cluster       |         |
|                                         | (sharded by         |         |
|                                         |  user_id hash)      |         |
|                                         +---------------------+         |
|                                                                         |
|  SHARDING STRATEGY:                                                     |
|  * Shard by user_id hash > consistent distribution                      |
|  * Each shard handles ~50K updates/sec                                  |
|  * 10 shards for 500K peak updates/sec (with headroom)                  |
|  * Stateless ingestion servers - any server handles any user            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### REDIS CLUSTER FOR LOCATION CACHE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REDIS CLUSTER:                                                         |
|  * 10M active keys x 64 bytes ~ 640 MB (data)                           |
|  * With overhead and friend caches: ~50 GB total                        |
|  * 6-node cluster (3 primaries + 3 replicas)                            |
|                                                                         |
|  +----------+     +----------+     +----------+                         |
|  | Primary  |     | Primary  |     | Primary  |                         |
|  | Shard 0  |     | Shard 1  |     | Shard 2  |                         |
|  | (hash    |     | (hash    |     | (hash    |                         |
|  |  0-5460) |     | 5461-    |     | 10923-   |                         |
|  +----------+     | 10922)   |     | 16383)   |                         |
|       |           +----------+     +----------+                         |
|       v                |                |                               |
|  +----------+     +----------+     +----------+                         |
|  | Replica  |     | Replica  |     | Replica  |                         |
|  | Shard 0  |     | Shard 1  |     | Shard 2  |                         |
|  +----------+     +----------+     +----------+                         |
|                                                                         |
|  READ PATH: Read from replicas (read-heavy for friend lookups)          |
|  WRITE PATH: Write to primaries (location updates)                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### PUB/SUB SHARDING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  10M active channels (one per sharing user).                            |
|  200M subscriptions across all channels.                                |
|                                                                         |
|  SHARDING BY USER_ID:                                                   |
|  * Channel location:user_A > shard = hash(user_A) % N                   |
|  * All operations for that channel go to that shard                     |
|  * Subscriber connections may span multiple shards                      |
|                                                                         |
|  SCALING PUB/SUB:                                                       |
|  +----------------------------------------------------+                 |
|  | Pub/Sub Cluster                                     |                |
|  |                                                     |                |
|  | +-------------+  +-------------+  +-------------+   |                |
|  | | Shard 0     |  | Shard 1     |  | Shard 2     |   |                |
|  | | Channels:   |  | Channels:   |  | Channels:   |   |                |
|  | | A, D, G...  |  | B, E, H...  |  | C, F, I...  |   |                |
|  | | 3.3M chans  |  | 3.3M chans  |  | 3.3M chans  |   |                |
|  | +-------------+  +-------------+  +-------------+   |                |
|  +----------------------------------------------------+                 |
|                                                                         |
|  CROSS-SHARD SUBSCRIPTIONS:                                             |
|  User A (shard 0) subscribes to User B (shard 1):                       |
|  > WebSocket gateway maintains connections to all shards                |
|  > Gateway subscribes to shard 1 on behalf of A                         |
|  > When B publishes on shard 1, gateway receives and                    |
|    forwards to A's WebSocket connection                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### MULTI-REGION DEPLOYMENT

```
+--------------------------------------------------------------------------+
|                                                                          |
|                    +-------------------+                                 |
|                    | Global DNS / LB   |                                 |
|                    | (route to nearest  |                                |
|                    |  region)           |                                |
|                    +-------------------+                                 |
|                     /        |        \                                  |
|                    v         v         v                                 |
|  +-------------+  +-------------+  +-------------+                       |
|  | US-EAST     |  | EU-WEST     |  | ASIA-EAST   |                       |
|  |             |  |             |  |             |                       |
|  | Ingestion   |  | Ingestion   |  | Ingestion   |                       |
|  | Redis Cache |  | Redis Cache |  | Redis Cache |                       |
|  | Pub/Sub     |  | Pub/Sub     |  | Pub/Sub     |                       |
|  | WebSocket GW|  | WebSocket GW|  | WebSocket GW|                       |
|  +-------------+  +-------------+  +-------------+                       |
|         \              |              /                                  |
|          \             |             /                                   |
|           +-------+----+----+-------+                                    |
|                   |         |                                            |
|            +-------------+  |                                            |
|            | Cross-region|  |                                            |
|            | sync for    |  |                                            |
|            | friends in  |  |                                            |
|            | diff regions|  |                                            |
|            +-------------+  |                                            |
|                                                                          |
|  LOCALITY: Most friends are in the same region.                          |
|  For cross-region friends, replicate location updates                    |
|  between regions via an async pipeline (adds ~50-100ms latency).         |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 12: INTERVIEW Q&A

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Q1: Why use per-user channels instead of per-geohash channels?          |
|  ---------------------------------------------------------------         |
|  A: Per-geohash channels have thundering herd issues in dense areas      |
|  (stadium with 50K users in one geohash). Per-user channels scope        |
|  the fan-out to only friends, which is bounded (~400 avg). It also       |
|  maps naturally to the privacy model - you only publish to people        |
|  you've explicitly shared with.                                          |
|                                                                          |
|  Q2: How do you handle the "cold start" when a user opens the app?       |
|  ---------------------------------------------------------------         |
|  A: When the user opens Nearby Friends:                                  |
|  1. Fetch friend list + sharing statuses in parallel                     |
|  2. Pipeline-fetch all sharing friends' latest locations from Redis      |
|  3. Subscribe to all sharing friends' channels for live updates          |
|  This gives a complete initial snapshot + real-time going forward.       |
|  Total cold start time: ~50-100ms.                                       |
|                                                                          |
|  Q3: What happens if a location update is lost?                          |
|  -----------------------------------------------                         |
|  A: Since we only care about the LATEST location, a lost update          |
|  is naturally corrected by the next update (10-30 sec later). The        |
|  system is eventually consistent. We don't need exactly-once delivery    |
|  - at-least-once with idempotent overwrites is sufficient. The cache     |
|  always has the latest timestamp; stale updates are discarded.           |
|                                                                          |
|  Q4: How do you prevent a user's location from being leaked?             |
|  -----------------------------------------------------------             |
|  A: Multiple layers of protection:                                       |
|  * Sharing is explicit opt-in with per-friend granularity                |
|  * Server enforces ACL: only friends in share list receive updates       |
|  * TLS encryption in transit, encryption at rest                         |
|  * No permanent storage - cache-only with TTL                            |
|  * Audit logs for all location accesses                                  |
|  * Rate limiting on location queries to prevent scraping                 |
|                                                                          |
|  Q5: How would you handle a celebrity with 10M followers?                |
|  -------------------------------------------------------                 |
|  A: Celebrities don't share with all followers (privacy). If they        |
|  share with close friends (say 100), it's a normal channel. If           |
|  they share with a large group, we can tier the fan-out:                 |
|  * Direct push to first 1000 subscribers                                 |
|  * Batch delivery for remaining (slight delay acceptable)                |
|  * Or use a "pull" model for large groups instead of push                |
|                                                                          |
|  Q6: How do you reduce battery usage on the client?                      |
|  --------------------------------------------------                      |
|  A: Adaptive strategy based on context:                                  |
|  * Stationary: use cell tower only, update every 60s                     |
|  * Walking: WiFi + cell, update every 30s                                |
|  * Driving: GPS every 5-10s                                              |
|  * Background: significant location change API only                      |
|  * Low battery: reduce to cell tower, extend interval to 120s            |
|  * Batch uploads to reduce radio wake-ups                                |
|                                                                          |
|  Q7: Why Redis for the location cache instead of a database?             |
|  -----------------------------------------------------------             |
|  A: Location data is ephemeral - only the latest matters, and it         |
|  expires in minutes. Redis provides:                                     |
|  * Sub-millisecond reads (critical for 333K lookups/sec)                 |
|  * Built-in TTL (auto-expire stale locations)                            |
|  * Built-in pub/sub (collocate cache and messaging)                      |
|  * Hash data type (perfect for location fields)                          |
|  A traditional DB would add unnecessary persistence overhead for         |
|  data that is worthless after 10 minutes.                                |
|                                                                          |
|  Q8: How would you test this system?                                     |
|  ------------------------------------                                    |
|  A: Testing approaches:                                                  |
|  * Simulate 10M users with location replay from recorded GPS traces      |
|  * Chaos engineering: kill Redis nodes, drop WebSocket connections       |
|  * Battery profiling on real devices (iOS + Android test labs)           |
|  * Privacy audit: verify no data leaks across share boundaries           |
|  * Load test pub/sub fan-out with worst-case friend counts               |
|  * Geo edge cases: equator, date line, poles                             |
|                                                                          |
|  Q9: How do you handle network partitions between regions?               |
|  ---------------------------------------------------------               |
|  A: Each region operates independently for local friends. Cross-         |
|  region friends may see stale locations during a partition (eventual     |
|  consistency). When the partition heals, the latest location in          |
|  each region's cache is the source of truth (latest timestamp wins).     |
|  This is acceptable because the feature is best-effort by nature.        |
|                                                                          |
|  Q10: Could you use a quadtree instead of geohash?                       |
|  --------------------------------------------------                      |
|  A: A quadtree dynamically adapts to density (subdivides dense           |
|  areas), while geohash has fixed grid cells. For nearby friends,         |
|  geohash is preferred because:                                           |
|  * It's a simple string prefix operation (easy to index in Redis)        |
|  * No tree rebalancing as users move                                     |
|  * Neighbor computation is O(1) arithmetic                               |
|  * The density variation matters less since we're checking friends,      |
|    not all users in a cell                                               |
|  Quadtrees would be better for "find all users near me" (Uber-style)     |
|  where you need adaptive density handling.                               |
|                                                                          |
+--------------------------------------------------------------------------+
```

*End of Nearby Friends System Design*
