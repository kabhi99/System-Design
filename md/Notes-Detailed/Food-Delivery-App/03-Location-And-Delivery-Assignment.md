# FOOD DELIVERY PLATFORM SYSTEM DESIGN

PART 3: LOCATION TRACKING & DELIVERY PARTNER ASSIGNMENT
SECTION 1: LOCATION SERVICE (THE CRITICAL COMPONENT)
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  WHY LOCATION IS THE HARDEST PROBLEM                                   |*
*|                                                                         |*
*|  * 300,000 delivery partners online during peak                       |*
*|  * Location update every 4 seconds                                    |*
*|  * = 75,000 location writes/second                                    |*
*|  * + Thousands of "find nearby partner" queries/second               |*
*|  * + Live tracking for every active order                            |*
*|                                                                         |*
*|  This is HIGHER throughput than the order service!                    |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  LOCATION DATA FLOW                                                    |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |   Delivery Partner App                                         |  |*
*|  |         |                                                       |  |*
*|  |         | Every 4 seconds:                                     |  |*
*|  |         | PUT /api/partner/location                           |  |*
*|  |         | { lat, lng, timestamp, speed, heading }             |  |*
*|  |         |                                                       |  |*
*|  |         v                                                       |  |*
*|  |   +------------------+                                        |  |*
*|  |   |  LOAD BALANCER   |                                        |  |*
*|  |   +--------+---------+                                        |  |*
*|  |            |                                                   |  |*
*|  |            v                                                   |  |*
*|  |   +------------------+                                        |  |*
*|  |   | LOCATION SERVICE |                                        |  |*
*|  |   |   (Stateless)    |                                        |  |*
*|  |   +--------+---------+                                        |  |*
*|  |            |                                                   |  |*
*|  |    +-------+-------+                                          |  |*
*|  |    |               |                                          |  |*
*|  |    v               v                                          |  |*
*|  |  +-------+    +---------+                                     |  |*
*|  |  | Redis |    |  Kafka  |                                     |  |*
*|  |  | (GEO) |    | (stream)|                                     |  |*
*|  |  +-------+    +----+----+                                     |  |*
*|  |                    |                                           |  |*
*|  |            +-------+-------+                                  |  |*
*|  |            |               |                                  |  |*
*|  |            v               v                                  |  |*
*|  |    +-------------+  +-------------+                          |  |*
*|  |    |  Tracking   |  |   Partner   |                          |  |*
*|  |    |  Service    |  |  Analytics  |                          |  |*
*|  |    | (WebSocket) |  |             |                          |  |*
*|  |    +-------------+  +-------------+                          |  |*
*|  |          |                                                    |  |*
*|  |          v                                                    |  |*
*|  |    Customer App                                               |  |*
*|  |    (Live Map Update)                                          |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 2: GEOSPATIAL DATA STORAGE
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  OPTION 1: REDIS GEO (Recommended for Partner Location)               |*
*|  ------------------------------------------------------                 |*
*|                                                                         |*
*|  Redis has built-in geospatial commands using Geohash internally      |*
*|                                                                         |*
*|  Store partner location:                                               |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  GEOADD partner:locations <longitude> <latitude> <partner_id>  |  |*
*|  |                                                                 |  |*
*|  |  Example:                                                       |  |*
*|  |  GEOADD partner:locations 77.5946 12.9716 partner_123         |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  Find nearby partners:                                                 |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  GEORADIUS partner:locations <lng> <lat> <radius> <unit>       |  |*
*|  |                                                                 |  |*
*|  |  Example:                                                       |  |*
*|  |  GEORADIUS partner:locations 77.5946 12.9716 3 km             |  |*
*|  |    WITHDIST WITHCOORD COUNT 10 ASC                             |  |*
*|  |                                                                 |  |*
*|  |  Returns: Partners within 3km, sorted by distance             |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  Advantages:                                                           |*
*|  Y Fast O(log N) operations                                          |*
*|  Y Built-in distance calculation                                     |*
*|  Y No external dependency                                            |*
*|  Y 75K writes/second achievable                                      |*
*|                                                                         |*
*|  Limitations:                                                          |*
*|  X Single key (no sharding out of box)                               |*
*|  X Memory intensive                                                   |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  OPTION 2: GEOHASH SHARDING (For Higher Scale)                        |*
*|  -------------------------------------------------                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  GEOHASH: Encode lat/lng into a string                        |  |*
*|  |                                                                 |  |*
*|  |  Location: (12.9716, 77.5946) Bangalore                       |  |*
*|  |  Geohash: "tdr1xnep0"                                         |  |*
*|  |                                                                 |  |*
*|  |  Prefix sharing = nearby locations                            |  |*
*|  |  "tdr1xnep0" and "tdr1xnep1" are neighbors                   |  |*
*|  |                                                                 |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  Geohash Length  >  Cell Size                          |  |  |*
*|  |  |  -----------------------------                          |  |  |*
*|  |  |  1 character     >  5,000 km x 5,000 km                |  |  |*
*|  |  |  4 characters    >  39 km x 19 km                      |  |  |*
*|  |  |  5 characters    >  5 km x 5 km                        |  |  |*
*|  |  |  6 characters    >  1.2 km x 0.6 km                    |  |  |*
*|  |  |  7 characters    >  150m x 150m                        |  |  |*
*|  |  |  8 characters    >  38m x 19m                          |  |  |*
*|  |  |                                                         |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  SHARDING BY GEOHASH:                                                  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Use 4-char geohash prefix for sharding                       |  |*
*|  |                                                                 |  |*
*|  |  Redis Key: partner:locations:{geohash_prefix}                |  |*
*|  |                                                                 |  |*
*|  |  Example:                                                       |  |*
*|  |  * partner:locations:tdr1 (Bangalore area 1)                  |  |*
*|  |  * partner:locations:tdr2 (Bangalore area 2)                  |  |*
*|  |  * partner:locations:w7p9 (Mumbai area)                       |  |*
*|  |                                                                 |  |*
*|  |  Benefits:                                                     |  |*
*|  |  * Horizontal scaling by region                               |  |*
*|  |  * Query only relevant shards                                 |  |*
*|  |  * Hot city (Mumbai) doesn't affect others                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  OPTION 3: QUADTREE (Alternative)                                     |*
*|  --------------------------------                                      |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Divide map into quadrants recursively                        |  |*
*|  |                                                                 |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |           |           |           |                     |  |  |*
*|  |  |    NW     |    NE     |           |                     |  |  |*
*|  |  |           |           |           |                     |  |  |*
*|  |  +-----------+-----------+   NE-SE   |                     |  |  |*
*|  |  |           |           |           |                     |  |  |*
*|  |  |    SW     |    SE     |           |                     |  |  |*
*|  |  |           |           |           |                     |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |                                                                 |  |*
*|  |  Keep subdividing until < N partners per cell                 |  |*
*|  |  N typically = 100-500                                        |  |*
*|  |                                                                 |  |*
*|  |  Good for:                                                     |  |*
*|  |  * Non-uniform distribution (cities denser than rural)       |  |*
*|  |  * Custom implementations                                     |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 3: DELIVERY PARTNER ASSIGNMENT ALGORITHM
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  THE ASSIGNMENT PROBLEM                                                |*
*|                                                                         |*
*|  When order is placed, find the BEST delivery partner                 |*
*|                                                                         |*
*|  FACTORS TO CONSIDER:                                                  |*
*|  1. Distance from restaurant                                          |*
*|  2. Current workload (orders in hand)                                 |*
*|  3. Partner rating                                                     |*
*|  4. Time since last order (fairness)                                  |*
*|  5. Vehicle type (bike for short, car for large orders)              |*
*|  6. Partner's preferred areas                                        |*
*|  7. Order value (high-value > trusted partners)                      |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  ASSIGNMENT ALGORITHM                                                  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  STEP 1: FIND NEARBY AVAILABLE PARTNERS                        |  |*
*|  |  --------------------------------------                         |  |*
*|  |                                                                 |  |*
*|  |  nearby_partners = redis.georadius(                            |  |*
*|  |      key="partner:locations",                                  |  |*
*|  |      longitude=restaurant.lng,                                 |  |*
*|  |      latitude=restaurant.lat,                                  |  |*
*|  |      radius=5,  # km                                          |  |*
*|  |      unit="km",                                                 |  |*
*|  |      count=50,                                                  |  |*
*|  |      sort="ASC"  # nearest first                              |  |*
*|  |  )                                                              |  |*
*|  |                                                                 |  |*
*|  |  STEP 2: FILTER BY AVAILABILITY                                |  |*
*|  |  -------------------------------                                |  |*
*|  |                                                                 |  |*
*|  |  available = []                                                 |  |*
*|  |  for partner in nearby_partners:                               |  |*
*|  |      status = redis.get(f"partner:{partner.id}:status")       |  |*
*|  |      if status == "ONLINE":                                    |  |*
*|  |          current_orders = get_active_orders(partner.id)       |  |*
*|  |          if current_orders < MAX_CONCURRENT_ORDERS:           |  |*
*|  |              available.append(partner)                        |  |*
*|  |                                                                 |  |*
*|  |  STEP 3: CALCULATE SCORE FOR EACH PARTNER                     |  |*
*|  |  ------------------------------------------                     |  |*
*|  |                                                                 |  |*
*|  |  def calculate_score(partner, restaurant, order):             |  |*
*|  |      score = 0                                                  |  |*
*|  |                                                                 |  |*
*|  |      # Distance (closer = better) - 40% weight                |  |*
*|  |      distance = haversine(partner.loc, restaurant.loc)        |  |*
*|  |      distance_score = max(0, 100 - (distance * 20))          |  |*
*|  |      score += distance_score * 0.4                            |  |*
*|  |                                                                 |  |*
*|  |      # Rating - 20% weight                                    |  |*
*|  |      rating_score = partner.rating * 20  # 5.0 > 100         |  |*
*|  |      score += rating_score * 0.2                              |  |*
*|  |                                                                 |  |*
*|  |      # Workload (fewer orders = better) - 20% weight          |  |*
*|  |      current_orders = get_active_orders(partner.id)           |  |*
*|  |      workload_score = (3 - current_orders) * 33               |  |*
*|  |      score += workload_score * 0.2                            |  |*
*|  |                                                                 |  |*
*|  |      # Fairness (longer idle = better) - 10% weight           |  |*
*|  |      idle_minutes = time_since_last_order(partner.id)         |  |*
*|  |      idle_score = min(100, idle_minutes * 2)                  |  |*
*|  |      score += idle_score * 0.1                                |  |*
*|  |                                                                 |  |*
*|  |      # Acceptance rate - 10% weight                           |  |*
*|  |      acceptance_score = partner.acceptance_rate              |  |*
*|  |      score += acceptance_score * 0.1                          |  |*
*|  |                                                                 |  |*
*|  |      return score                                              |  |*
*|  |                                                                 |  |*
*|  |  STEP 4: SORT AND SELECT TOP PARTNERS                         |  |*
*|  |  -------------------------------------                          |  |*
*|  |                                                                 |  |*
*|  |  scored_partners = [                                           |  |*
*|  |      (partner, calculate_score(partner, restaurant, order))   |  |*
*|  |      for partner in available                                  |  |*
*|  |  ]                                                              |  |*
*|  |  scored_partners.sort(key=lambda x: x[1], reverse=True)       |  |*
*|  |  top_partners = scored_partners[:3]  # Try top 3              |  |*
*|  |                                                                 |  |*
*|  |  STEP 5: SEND DELIVERY REQUEST (Sequential)                   |  |*
*|  |  -----------------------------------------                      |  |*
*|  |                                                                 |  |*
*|  |  for partner, score in top_partners:                          |  |*
*|  |      accepted = send_request_and_wait(                        |  |*
*|  |          partner_id=partner.id,                               |  |*
*|  |          order_id=order.id,                                    |  |*
*|  |          timeout=30  # seconds                                |  |*
*|  |      )                                                          |  |*
*|  |      if accepted:                                              |  |*
*|  |          assign_order(order.id, partner.id)                   |  |*
*|  |          return partner                                        |  |*
*|  |                                                                 |  |*
*|  |  # No one accepted - expand radius and retry                  |  |*
*|  |  return retry_with_larger_radius()                            |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 4: ASSIGNMENT FLOW DIAGRAM
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  DELIVERY PARTNER ASSIGNMENT FLOW                                      |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |   Restaurant Confirms Order                                    |  |*
*|  |            |                                                    |  |*
*|  |            v                                                    |  |*
*|  |   +-----------------+                                          |  |*
*|  |   | Order Service   |                                          |  |*
*|  |   | publishes event |                                          |  |*
*|  |   +--------+--------+                                          |  |*
*|  |            |                                                    |  |*
*|  |            v                                                    |  |*
*|  |   +-----------------+                                          |  |*
*|  |   |     Kafka       |                                          |  |*
*|  |   | order-confirmed |                                          |  |*
*|  |   +--------+--------+                                          |  |*
*|  |            |                                                    |  |*
*|  |            v                                                    |  |*
*|  |   +-------------------------------------+                      |  |*
*|  |   |       DELIVERY ASSIGNMENT SERVICE    |                     |  |*
*|  |   |                                       |                     |  |*
*|  |   |   1. Query Redis GEO for nearby     |                     |  |*
*|  |   |   2. Filter by status=ONLINE        |                     |  |*
*|  |   |   3. Calculate scores               |                     |  |*
*|  |   |   4. Sort by score DESC             |                     |  |*
*|  |   |                                       |                     |  |*
*|  |   +--------------+------------------------+                    |  |*
*|  |                  |                                              |  |*
*|  |                  v                                              |  |*
*|  |   +-------------------------------------+                      |  |*
*|  |   |     Send Push Notification          |                     |  |*
*|  |   |     to Top Partner                  |                     |  |*
*|  |   |                                       |                     |  |*
*|  |   |  "New delivery request!"            |                     |  |*
*|  |   |  Restaurant: Pizza Palace           |                     |  |*
*|  |   |  Distance: 1.2 km                   |                     |  |*
*|  |   |  Earnings: R45                      |                     |  |*
*|  |   |  [ACCEPT]  [REJECT]                 |                     |  |*
*|  |   |                                       |                     |  |*
*|  |   +--------------+------------------------+                    |  |*
*|  |                  |                                              |  |*
*|  |         +--------+--------+                                    |  |*
*|  |         |                 |                                    |  |*
*|  |         v                 v                                    |  |*
*|  |   +----------+     +----------+                               |  |*
*|  |   | ACCEPTED |     | REJECTED |                               |  |*
*|  |   |    or    |     |    or    |                               |  |*
*|  |   | TIMEOUT  |     | TIMEOUT  |                               |  |*
*|  |   +----+-----+     +----+-----+                               |  |*
*|  |        |                |                                      |  |*
*|  |        v                v                                      |  |*
*|  |   Assign to         Try next                                  |  |*
*|  |   this partner      ranked partner                            |  |*
*|  |        |                |                                      |  |*
*|  |        v                |                                      |  |*
*|  |   Update Order      <---+                                     |  |*
*|  |   Status                                                       |  |*
*|  |        |                                                       |  |*
*|  |        v                                                       |  |*
*|  |   Notify Customer                                             |  |*
*|  |   Notify Restaurant                                           |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  HANDLING NO PARTNERS AVAILABLE                                       |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  RETRY STRATEGY:                                               |  |*
*|  |                                                                 |  |*
*|  |  Attempt 1: 3 km radius, top 3 partners, 30s timeout          |  |*
*|  |  Attempt 2: 5 km radius, top 5 partners, 45s timeout          |  |*
*|  |  Attempt 3: 8 km radius, all partners, 60s timeout            |  |*
*|  |                                                                 |  |*
*|  |  If all fail:                                                  |  |*
*|  |  * Notify customer about delay                                |  |*
*|  |  * Add to priority queue                                      |  |*
*|  |  * Retry every 2 minutes                                      |  |*
*|  |  * After 15 mins: offer cancellation with full refund        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 5: LIVE TRACKING
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  REAL-TIME TRACKING ARCHITECTURE                                       |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |   Delivery Partner App                                         |  |*
*|  |         |                                                       |  |*
*|  |         | PUT /api/partner/location                           |  |*
*|  |         | (every 4 seconds)                                   |  |*
*|  |         |                                                       |  |*
*|  |         v                                                       |  |*
*|  |   +------------------+                                        |  |*
*|  |   | LOCATION SERVICE |                                        |  |*
*|  |   +--------+---------+                                        |  |*
*|  |            |                                                   |  |*
*|  |    +-------+-------+                                          |  |*
*|  |    |       |       |                                          |  |*
*|  |    v       v       v                                          |  |*
*|  |  +-----+ +-----+ +---------+                                 |  |*
*|  |  |Redis| |Redis| |  Kafka  |                                 |  |*
*|  |  |GEO  | |Hash | |location |                                 |  |*
*|  |  |     | |     | |-updates |                                 |  |*
*|  |  +-----+ +-----+ +----+----+                                 |  |*
*|  |                       |                                       |  |*
*|  |                       v                                       |  |*
*|  |              +----------------+                               |  |*
*|  |              |   TRACKING     |                               |  |*
*|  |              |   SERVICE      |                               |  |*
*|  |              |                |                               |  |*
*|  |              | * Maintain map |                               |  |*
*|  |              |   of active    |                               |  |*
*|  |              |   order_id >   |                               |  |*
*|  |              |   ws_connection|                               |  |*
*|  |              |                |                               |  |*
*|  |              +-------+--------+                               |  |*
*|  |                      |                                        |  |*
*|  |                      | WebSocket push                         |  |*
*|  |                      |                                        |  |*
*|  |                      v                                        |  |*
*|  |              +----------------+                               |  |*
*|  |              |  Customer App  |                               |  |*
*|  |              |                |                               |  |*
*|  |              |   Live map   |                               |  |*
*|  |              |  ETA: 5 mins   |                               |  |*
*|  |              |                |                               |  |*
*|  |              +----------------+                               |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  WEBSOCKET CONNECTION MANAGEMENT                                       |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Customer opens tracking screen:                               |  |*
*|  |  1. Connect WebSocket: ws://tracking.zomato.com/orders/123    |  |*
*|  |  2. Server maps: order_123 > [ws_connection_abc]              |  |*
*|  |                                                                 |  |*
*|  |  When location update arrives (via Kafka):                     |  |*
*|  |  1. Get order_id for this partner                             |  |*
*|  |  2. Look up WebSocket connections for order_id                |  |*
*|  |  3. Push location to all connected clients                    |  |*
*|  |                                                                 |  |*
*|  |  Message format:                                               |  |*
*|  |  {                                                              |  |*
*|  |    "type": "location_update",                                 |  |*
*|  |    "data": {                                                   |  |*
*|  |      "latitude": 12.9716,                                     |  |*
*|  |      "longitude": 77.5946,                                    |  |*
*|  |      "heading": 45,                                           |  |*
*|  |      "speed": 25,                                              |  |*
*|  |      "eta_seconds": 300,                                      |  |*
*|  |      "timestamp": "2024-01-15T15:30:00Z"                     |  |*
*|  |    }                                                           |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SCALING WEBSOCKET CONNECTIONS                                         |*
*|                                                                         |*
*|  Problem: 500K active orders = 500K WebSocket connections             |*
*|  Single server can handle ~50K connections                            |*
*|  Need: 10+ tracking servers                                           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Solution: Consistent Hashing for Connection Routing           |  |*
*|  |                                                                 |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  order_id > hash > tracking_server_N                   |  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  order_123 > hash > Server 3                          |  |  |*
*|  |  |  order_456 > hash > Server 7                          |  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  Redis pub/sub or Kafka for cross-server messages      |  |  |*
*|  |  |                                                         |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 6: ETA CALCULATION
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  ETA COMPONENTS                                                        |*
*|                                                                         |*
*|  Total ETA = Restaurant Prep Time                                      |*
*|            + Partner Travel to Restaurant                              |*
*|            + Pickup Time (parking, waiting)                           |*
*|            + Travel to Customer                                        |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Order Placed                                                  |  |*
*|  |       |                                                        |  |*
*|  |       | Restaurant Prep Time                                  |  |*
*|  |       | (15-30 mins based on items)                          |  |*
*|  |       |                                                        |  |*
*|  |       v                                                        |  |*
*|  |  Food Ready --------------------------------------------      |  |*
*|  |       |                                                        |  |*
*|  |       | Partner arrives (may be before food ready)           |  |*
*|  |       | (5-10 mins based on distance)                        |  |*
*|  |       |                                                        |  |*
*|  |       v                                                        |  |*
*|  |  Pickup -----------------------------------------------       |  |*
*|  |       |                                                        |  |*
*|  |       | Travel to Customer                                   |  |*
*|  |       | (Google Maps API for route)                          |  |*
*|  |       |                                                        |  |*
*|  |       v                                                        |  |*
*|  |  Delivered --------------------------------------------       |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  ETA CALCULATION ALGORITHM                                            |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  def calculate_eta(order, partner, restaurant, customer):     |  |*
*|  |      # 1. Restaurant prep time (from restaurant settings)     |  |*
*|  |      prep_time = restaurant.avg_prep_time                     |  |*
*|  |                                                                 |  |*
*|  |      # Adjust based on current load                           |  |*
*|  |      active_orders = get_restaurant_active_orders(restaurant) |  |*
*|  |      if active_orders > 10:                                   |  |*
*|  |          prep_time += (active_orders - 10) * 2  # +2 min each|  |*
*|  |                                                                 |  |*
*|  |      # 2. Partner to restaurant                               |  |*
*|  |      partner_to_rest = google_maps.get_duration(             |  |*
*|  |          origin=partner.location,                             |  |*
*|  |          destination=restaurant.location,                     |  |*
*|  |          traffic=True                                         |  |*
*|  |      )                                                          |  |*
*|  |                                                                 |  |*
*|  |      # 3. Pickup buffer                                       |  |*
*|  |      pickup_buffer = 3  # minutes for parking, finding, etc. |  |*
*|  |                                                                 |  |*
*|  |      # 4. Restaurant to customer                              |  |*
*|  |      rest_to_customer = google_maps.get_duration(            |  |*
*|  |          origin=restaurant.location,                          |  |*
*|  |          destination=customer.location,                       |  |*
*|  |          traffic=True                                         |  |*
*|  |      )                                                          |  |*
*|  |                                                                 |  |*
*|  |      # 5. Calculate parallel time                             |  |*
*|  |      # Partner travels WHILE food is being prepared          |  |*
*|  |      wait_time = max(0, prep_time - partner_to_rest)         |  |*
*|  |                                                                 |  |*
*|  |      total_eta = (                                            |  |*
*|  |          partner_to_rest +                                    |  |*
*|  |          wait_time +                                          |  |*
*|  |          pickup_buffer +                                      |  |*
*|  |          rest_to_customer                                     |  |*
*|  |      )                                                          |  |*
*|  |                                                                 |  |*
*|  |      # 6. Add buffer for uncertainty                          |  |*
*|  |      total_eta *= 1.1  # 10% buffer                          |  |*
*|  |                                                                 |  |*
*|  |      return round(total_eta)                                  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  DYNAMIC ETA UPDATES                                                   |*
*|                                                                         |*
*|  ETA is recalculated at each stage:                                   |*
*|  * When partner assigned                                              |*
*|  * When partner reaches restaurant                                    |*
*|  * When food picked up                                                |*
*|  * Every 30 seconds during delivery                                  |*
*|  * When traffic conditions change significantly                      |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

END OF PART 3
