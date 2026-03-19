# PROXIMITY SERVICE SYSTEM DESIGN (YELP / NEARBY PLACES)
*Complete Design: Requirements, Architecture, and Interview Guide*

A proximity service finds nearby businesses or points of interest given a user's
location (latitude/longitude) and a search radius. At scale, it must index hundreds
of millions of businesses, serve geo-queries with sub-200ms latency, and handle
a massively read-heavy workload across the globe.

## SECTION 1: UNDERSTANDING THE PROBLEM

### WHAT IS A PROXIMITY SERVICE?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  A proximity service answers the question:                              |
|  "What businesses/places are near me?"                                  |
|                                                                         |
|  USER EXPERIENCE:                                                       |
|  1. Open the app (Yelp, Google Maps, Uber Eats)                         |
|  2. App detects your location (lat: 37.7749, lng: -122.4194)            |
|  3. App shows nearby restaurants, shops, etc. on a map and list         |
|  4. User can filter by category (restaurants, gas stations, etc.)       |
|  5. User can filter by rating, price, open now                          |
|  6. Results are sorted by distance, relevance, or rating                |
|  7. User taps a business to see details, reviews, photos                |
|                                                                         |
|  EXAMPLES:                                                              |
|  * Yelp           — find restaurants, services near you                 |
|  * Google Maps     — "restaurants near me"                              |
|  * Uber Eats       — find nearby restaurants for delivery               |
|  * Airbnb          — find nearby listings                               |
|  * Tinder          — find nearby people                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHY IS THIS HARD TO BUILD?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KEY CHALLENGES:                                                        |
|                                                                         |
|  1. EFFICIENT SPATIAL SEARCH                                            |
|  ----------------------------                                           |
|  200 million businesses worldwide. You can't scan all of them           |
|  and compute distance for each one. Need spatial indexing.              |
|                                                                         |
|  2. TWO-DIMENSIONAL DATA                                                |
|  -------------------------                                              |
|  Latitude and longitude are two separate dimensions.                    |
|  Traditional B-tree indexes work on one dimension.                      |
|  Need special data structures for 2D range queries.                     |
|                                                                         |
|  3. EARTH IS A SPHERE                                                   |
|  ----------------------                                                 |
|  Euclidean distance doesn't work on a sphere.                           |
|  Need Haversine formula or great-circle distance.                       |
|  Edge cases: international date line, poles, equator.                   |
|                                                                         |
|  4. MASSIVELY READ-HEAVY                                                |
|  -----------------------                                                |
|  Millions of search queries per second.                                 |
|  Business data changes rarely (new restaurants, closures).              |
|  Read:write ratio is 95:5 or higher.                                    |
|                                                                         |
|  5. DYNAMIC RADIUS                                                      |
|  -----------------                                                      |
|  In Manhattan, 500m radius returns 200 restaurants.                     |
|  In rural Montana, 50km radius returns 3 restaurants.                   |
|  Need adaptive density handling.                                        |
|                                                                         |
|  6. REAL-TIME FILTERS                                                   |
|  --------------------                                                   |
|  Users filter by "open now", "4+ stars", "$$ price range".              |
|  These filters must be applied on top of the spatial query.             |
|  Combining spatial + attribute filtering efficiently is hard.           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2: REQUIREMENTS

### FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FUNCTIONAL REQUIREMENTS:                                               |
|                                                                         |
|  1. SEARCH NEARBY BUSINESSES                                            |
|     * Given lat/lng and radius, return nearby businesses                |
|     * Support multiple radius options (1km, 5km, 10km, 25km)            |
|     * Return results sorted by distance by default                      |
|     * Show distance from user to each result                            |
|     * Paginate results (20 per page)                                    |
|                                                                         |
|  2. FILTER & SORT                                                       |
|     * Filter by category (restaurant, gas station, hotel, etc.)         |
|     * Filter by rating (4+ stars)                                       |
|     * Filter by price range ($, $$, $$$, $$$$)                          |
|     * Filter by "open now"                                              |
|     * Sort by: distance, rating, number of reviews, relevance           |
|                                                                         |
|  3. BUSINESS CRUD                                                       |
|     * Business owners can add/update/delete their business              |
|     * Update address, hours, phone, photos, description                 |
|     * Changes don't need to be real-time (eventual consistency OK)      |
|                                                                         |
|  4. BUSINESS DETAILS                                                    |
|     * View detailed business page (photos, hours, menu, etc.)           |
|     * View and submit reviews/ratings                                   |
|     * View on map                                                       |
|                                                                         |
|  5. REVIEWS & RATINGS                                                   |
|     * Users can write reviews with star ratings                         |
|     * View reviews sorted by date or helpfulness                        |
|     * Report inappropriate reviews                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### NON-FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NON-FUNCTIONAL REQUIREMENTS:                                           |
|                                                                         |
|  1. LOW LATENCY                                                         |
|     * Search results returned in <200ms (P99)                           |
|     * Users expect instant results when they open the app               |
|     * Geo-queries must be fast even with millions of records            |
|                                                                         |
|  2. HIGH AVAILABILITY                                                   |
|     * 99.99% uptime                                                     |
|     * Degraded results (stale cache) better than no results             |
|     * Geo-redundant deployment                                          |
|                                                                         |
|  3. SCALABILITY                                                         |
|     * 200 million businesses worldwide                                  |
|     * 500 million daily active users                                    |
|     * Handle traffic spikes (lunch time, events, holidays)              |
|                                                                         |
|  4. READ-HEAVY                                                          |
|     * Read:write ratio = 95:5                                           |
|     * Optimize aggressively for read performance                        |
|     * Business data changes are infrequent                              |
|                                                                         |
|  5. ACCURACY                                                            |
|     * Distance calculations must be correct (Haversine)                 |
|     * No missing results within the search radius                       |
|     * Stale data (closed business still showing) is acceptable          |
|       for short periods                                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3: BACK-OF-ENVELOPE ESTIMATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCALE ASSUMPTIONS                                                      |
|                                                                         |
|  Total businesses:           200 million                                |
|  Daily active users (DAU):   500 million                                |
|  Average searches per user:  5 per day                                  |
|  Total searches per day:     2.5 billion                                |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  QUERIES PER SECOND (QPS)                                               |
|                                                                         |
|  Daily QPS:  2.5B / 86400 = ~29,000 QPS                                 |
|  Peak QPS:   2x average = ~58,000 QPS                                   |
|  Lunch rush: 5x average = ~145,000 QPS                                  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  STORAGE ESTIMATES                                                      |
|                                                                         |
|  Per business record:                                                   |
|    * ID, name, address:         ~500 bytes                              |
|    * Lat/lng:                   16 bytes                                |
|    * Category, price, rating:   ~100 bytes                              |
|    * Hours, phone, URL:         ~300 bytes                              |
|    * Photos (metadata/URLs):    ~1 KB                                   |
|    * Total per business:        ~2 KB                                   |
|                                                                         |
|  Total business data:  200M * 2KB = 400 GB                              |
|  (Fits in memory of a few servers!)                                     |
|                                                                         |
|  Geospatial index size:                                                 |
|    200M * (ID + lat/lng + geohash) = 200M * 40B = 8 GB                  |
|    (Easily fits in memory)                                              |
|                                                                         |
|  Reviews data:                                                          |
|    Average 10 reviews per business = 2 billion reviews                  |
|    ~500 bytes per review = 1 TB                                         |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  BANDWIDTH                                                              |
|                                                                         |
|  Average response size:  20 businesses * 2KB = 40 KB                    |
|  Peak bandwidth:         145K QPS * 40KB = 5.8 GB/s outbound            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4: HIGH-LEVEL ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  OVERALL SYSTEM ARCHITECTURE                                            |
|                                                                         |
|  +---------+     +---------------+     +--------------------+           |
|  | Mobile  |---->| API Gateway / |---->| Location Service   |           |
|  | Client  |     | Load Balancer |     | (Geo Search)       |           |
|  +---------+     +---------------+     +--------------------+           |
|                        |                        |                       |
|                        |                        v                       |
|                        |               +--------------------+           |
|                        |               | Geospatial Index   |           |
|                        |               | (Geohash/Quadtree) |           |
|                        |               +--------------------+           |
|                        |                                                |
|                        v                                                |
|                 +---------------+      +--------------------+           |
|                 | Business      |----->| Business DB        |           |
|                 | Service       |      | (PostgreSQL)       |           |
|                 | (CRUD/Details)|      +--------------------+           |
|                 +---------------+                                       |
|                        |                                                |
|                        v                                                |
|                 +---------------+      +--------------------+           |
|                 | Review        |----->| Review DB          |           |
|                 | Service       |      | (NoSQL/PostgreSQL) |           |
|                 +---------------+      +--------------------+           |
|                                                                         |
|                 +---------------+                                       |
|                 | Cache Layer   |  (Redis — hot geohash prefixes)       |
|                 | (Redis)       |                                       |
|                 +---------------+                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMPONENT RESPONSIBILITIES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. API GATEWAY / LOAD BALANCER                                         |
|  ---------------------------------                                      |
|  * Rate limiting, authentication, request routing                       |
|  * Routes search requests to Location Service                           |
|  * Routes business CRUD to Business Service                             |
|  * Routes review requests to Review Service                             |
|                                                                         |
|  2. LOCATION SERVICE (Read-heavy, latency-critical)                     |
|  ---------------------------------------------------                    |
|  * Receives: lat, lng, radius, filters                                  |
|  * Queries geospatial index for candidate businesses                    |
|  * Applies filters (category, rating, price, open now)                  |
|  * Computes exact distances (Haversine) for candidates                  |
|  * Ranks and returns results                                            |
|  * Stateless: horizontally scalable                                     |
|                                                                         |
|  3. GEOSPATIAL INDEX                                                    |
|  ----------------------                                                 |
|  * In-memory data structure for fast geo-queries                        |
|  * Options: Geohash, Quadtree, S2 Geometry, R-tree                      |
|  * Periodically rebuilt from business DB (batch update)                 |
|  * Read-optimized; writes go through Business Service                   |
|                                                                         |
|  4. BUSINESS SERVICE (Write path)                                       |
|  ----------------------------------                                     |
|  * CRUD operations for businesses                                       |
|  * Validates and persists business data                                 |
|  * Triggers async geospatial index update on changes                    |
|  * Serves business detail pages                                         |
|                                                                         |
|  5. BUSINESS DATABASE                                                   |
|  ----------------------                                                 |
|  * Source of truth for all business data                                |
|  * PostgreSQL with PostGIS extension (or similar)                       |
|  * Read replicas for scaling reads                                      |
|                                                                         |
|  6. CACHE LAYER (Redis)                                                 |
|  ------------------------                                               |
|  * Cache search results by geohash prefix + filters                     |
|  * Cache popular business details                                       |
|  * Cache hot areas (downtown Manhattan at lunch time)                   |
|                                                                         |
|  7. REVIEW SERVICE                                                      |
|  ------------------                                                     |
|  * Submit, view, flag reviews                                           |
|  * Compute and update aggregate ratings                                 |
|  * Separate from business service for independent scaling               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### API DESIGN

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KEY API ENDPOINTS:                                                     |
|                                                                         |
|  1. SEARCH NEARBY                                                       |
|  ------------------                                                     |
|  GET /v1/search/nearby                                                  |
|    ?lat=37.7749                                                         |
|    &lng=-122.4194                                                       |
|    &radius=5000          (meters)                                       |
|    &category=restaurant                                                 |
|    &min_rating=4.0                                                      |
|    &price=$$                                                            |
|    &open_now=true                                                       |
|    &sort_by=distance                                                    |
|    &page=1                                                              |
|    &page_size=20                                                        |
|                                                                         |
|  Response:                                                              |
|  +-----------------------------------+                                  |
|  | total: 142                        |                                  |
|  | businesses: [                     |                                  |
|  |   { id, name, lat, lng,           |                                  |
|  |     distance_m: 320,              |                                  |
|  |     category, rating,             |                                  |
|  |     price_range, is_open,         |                                  |
|  |     thumbnail_url }               |                                  |
|  | ]                                 |                                  |
|  | next_page_token: "..."            |                                  |
|  +-----------------------------------+                                  |
|                                                                         |
|  2. GET BUSINESS DETAILS                                                |
|  -------------------------                                              |
|  GET /v1/businesses/{businessId}                                        |
|                                                                         |
|  3. CREATE/UPDATE BUSINESS                                              |
|  --------------------------                                             |
|  POST /v1/businesses                                                    |
|  PUT  /v1/businesses/{businessId}                                       |
|                                                                         |
|  4. REVIEWS                                                             |
|  -----------                                                            |
|  GET  /v1/businesses/{businessId}/reviews                               |
|  POST /v1/businesses/{businessId}/reviews                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5: DEEP DIVE — GEOSPATIAL INDEXING

### APPROACH 1: NAIVE BRUTE FORCE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NAIVE APPROACH: SCAN ALL BUSINESSES                                    |
|                                                                         |
|  For each search query:                                                 |
|  1. Load ALL 200 million businesses                                     |
|  2. For each business, compute distance to the user's location          |
|  3. Filter those within the radius                                      |
|  4. Sort by distance                                                    |
|  5. Return top N                                                        |
|                                                                         |
|  COMPLEXITY: O(n) per query where n = 200 million                       |
|                                                                         |
|  TIME: ~200M distance calculations * ~100ns each = ~20 seconds          |
|                                                                         |
|  VERDICT: Completely unusable at scale.                                 |
|  Even with a SQL query like:                                            |
|    SELECT * FROM businesses                                             |
|    WHERE haversine(lat, lng, user_lat, user_lng) < radius               |
|  This is a full table scan — O(n) every time.                           |
|                                                                         |
|  We need a SPATIAL INDEX to prune the search space.                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### APPROACH 2: GEOHASH

```
+-------------------------------------------------------------------------+
|                                                                         |
|  GEOHASH: CONVERT 2D COORDINATES TO A 1D STRING                         |
|                                                                         |
|  CORE IDEA:                                                             |
|  Divide the Earth into a grid of cells. Each cell gets a unique         |
|  string ID. Nearby locations share a common prefix.                     |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  HOW ENCODING WORKS:                                                    |
|                                                                         |
|  1. Start with the entire world:                                        |
|     Latitude:  [-90, +90]                                               |
|     Longitude: [-180, +180]                                             |
|                                                                         |
|  2. Alternately bisect longitude and latitude:                          |
|                                                                         |
|     Bit 1 (longitude): Is lng > 0?                                      |
|       YES -> right half [0, +180]   bit = 1                             |
|       NO  -> left half  [-180, 0]   bit = 0                             |
|                                                                         |
|     Bit 2 (latitude): Is lat > 0?                                       |
|       YES -> top half [0, +90]      bit = 1                             |
|       NO  -> bottom half [-90, 0]   bit = 0                             |
|                                                                         |
|     Bit 3 (longitude): Bisect the longitude range again...              |
|     ...continue alternating until desired precision                     |
|                                                                         |
|  3. Encode the binary string as base-32 characters                      |
|                                                                         |
|  EXAMPLE:                                                               |
|  San Francisco (37.7749, -122.4194) -> "9q8yyk..."                      |
|  Oakland       (37.8044, -122.2712) -> "9q9p0..."                       |
|  Both start with "9q" — they're in the same coarse region.              |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  PRECISION LEVELS:                                                      |
|                                                                         |
|  +--------+-------------------+----------------------------+            |
|  | Length  | Cell Size         | Use Case                   |           |
|  +--------+-------------------+----------------------------+            |
|  | 1      | ~5,000 km         | Continent                  |            |
|  | 2      | ~1,250 km         | Large country region       |            |
|  | 3      | ~156 km           | State/province             |            |
|  | 4      | ~39 km            | City                       |            |
|  | 5      | ~4.9 km           | Neighborhood               |            |
|  | 6      | ~1.2 km           | Street level               |            |
|  | 7      | ~153 m            | Block level                |            |
|  | 8      | ~38 m             | Building level             |            |
|  +--------+-------------------+----------------------------+            |
|                                                                         |
|  For "restaurants within 5km": use geohash length 5 (~4.9km cell)       |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  PROXIMITY SEARCH WITH GEOHASH:                                         |
|                                                                         |
|  1. Compute user's geohash at the desired precision                     |
|  2. Find all businesses with the same geohash prefix                    |
|  3. Also check the 8 NEIGHBORING cells (edge case!)                     |
|  4. Filter by exact distance (Haversine)                                |
|  5. Return results                                                      |
|                                                                         |
|  WHY CHECK NEIGHBORS?                                                   |
|  A user near a cell boundary might be 100m from a business              |
|  in the adjacent cell. Without checking neighbors, we'd miss it.        |
|                                                                         |
|  +-------+-------+-------+                                              |
|  |       |       |       |                                              |
|  | 9q8yy | 9q8yz | 9q8z0 |                                              |
|  |       |       |       |                                              |
|  +-------+-------+-------+                                              |
|  |       | USER  |       |                                              |
|  | 9q8yw | 9q8yx | 9q8z1 |   <- user is near the right edge             |
|  |       | HERE  |       |      of cell 9q8yx; a business               |
|  +-------+-------+-------+      just across in 9q8z1 would              |
|  |       |       |       |      be missed without neighbor              |
|  | 9q8yv | 9q8yw | 9q8yz |      checking                                |
|  |       |       |       |                                              |
|  +-------+-------+-------+                                              |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  GEOHASH EDGE CASES:                                                    |
|                                                                         |
|  1. BOUNDARY DISCONTINUITY:                                             |
|     Geohash "9q" and "9r" might be adjacent on the map but              |
|     share no common prefix. Neighbor calculation handles this.          |
|                                                                         |
|  2. DIFFERENT CELL SIZES AT DIFFERENT LATITUDES:                        |
|     Cells near the equator are wider than cells near the poles          |
|     (longitude lines converge at poles).                                |
|                                                                         |
|  3. ANTIMERIDIAN (180°/-180° boundary):                                 |
|     Locations near the international date line are geographically       |
|     close but have very different geohashes. Special handling needed.   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### APPROACH 3: QUADTREE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  QUADTREE: RECURSIVE SPATIAL SUBDIVISION                                |
|                                                                         |
|  CORE IDEA:                                                             |
|  Divide the world into 4 quadrants. If a quadrant has too many          |
|  businesses (> threshold), subdivide it into 4 more quadrants.          |
|  Repeat recursively. Dense areas get more subdivisions.                 |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  HOW IT WORKS:                                                          |
|                                                                         |
|  Start: entire world is one node                                        |
|                                                                         |
|  +-----------------------------------+                                  |
|  |                                   |                                  |
|  |  200 million businesses           |                                  |
|  |  (too many! split)                |                                  |
|  |                                   |                                  |
|  +-----------------------------------+                                  |
|                                                                         |
|  After first split:                                                     |
|  +-----------------+-----------------+                                  |
|  |                 |                 |                                  |
|  |  NW: 80M        |  NE: 50M        |                                  |
|  |  (split again)  |  (split again)  |                                  |
|  +-----------------+-----------------+                                  |
|  |                 |                 |                                  |
|  |  SW: 40M        |  SE: 30M        |                                  |
|  |  (split again)  |  (split again)  |                                  |
|  +-----------------+-----------------+                                  |
|                                                                         |
|  Continue splitting until each leaf node has <= threshold               |
|  (e.g., threshold = 100 businesses per leaf).                           |
|                                                                         |
|  Manhattan (dense): tree goes 15-20 levels deep                         |
|  Sahara Desert:     tree stops at level 3-4                             |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  SEARCH ALGORITHM:                                                      |
|                                                                         |
|  Given user at (lat, lng) with radius R:                                |
|                                                                         |
|  1. Traverse tree from root to find the leaf containing (lat, lng)      |
|  2. Check all businesses in that leaf                                   |
|  3. Check if the search circle overlaps neighboring leaves              |
|  4. If yes, check businesses in those leaves too                        |
|  5. Filter by exact distance                                            |
|                                                                         |
|  COMPLEXITY: O(log n) to find the leaf, then O(k) for k candidates      |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  QUADTREE PROPERTIES:                                                   |
|                                                                         |
|  +-------------------------------+----------------------------------+   |
|  | Property                      | Value                            |   |
|  +-------------------------------+----------------------------------+   |
|  | Split threshold               | 100-500 businesses per leaf      |   |
|  | Max depth                     | ~20 levels                       |   |
|  | Total leaf nodes (200M biz)   | ~200M/100 = 2M leaf nodes        |   |
|  | Memory for tree structure     | ~2M * 200B = 400 MB              |   |
|  | Build time                    | O(n log n), ~minutes             |   |
|  | Search time                   | O(log n + k), ~microseconds      |   |
|  +-------------------------------+----------------------------------+   |
|                                                                         |
|  PROS:                                                                  |
|  * Adapts to density (more splits in dense areas)                       |
|  * Fast search: logarithmic tree traversal                              |
|  * Good for in-memory use                                               |
|                                                                         |
|  CONS:                                                                  |
|  * Hard to persist efficiently (tree structure in DB)                   |
|  * Must rebuild when businesses are added/removed                       |
|  * Not trivially distributable (unlike geohash)                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### APPROACH 4: S2 GEOMETRY (GOOGLE'S APPROACH)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  S2 GEOMETRY LIBRARY                                                    |
|                                                                         |
|  CORE IDEA:                                                             |
|  Project the Earth's sphere onto a cube (6 faces).                      |
|  Use a Hilbert curve to map 2D cells to 1D cell IDs.                    |
|  This gives excellent spatial locality (nearby cells have nearby IDs).  |
|                                                                         |
|  Developed by Google, used in Google Maps and Google S2.                |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  HOW IT WORKS:                                                          |
|                                                                         |
|  1. PROJECTION: Sphere -> Cube (6 faces)                                |
|     Each face is a square subdivided into cells.                        |
|                                                                         |
|  2. HILBERT CURVE: Maps 2D space to 1D                                  |
|     Unlike geohash (which uses Z-order/Morton curve),                   |
|     Hilbert curve has better spatial locality:                          |
|     adjacent cells in 2D are (mostly) adjacent in 1D.                   |
|                                                                         |
|  3. CELL LEVELS: 0 (entire face) to 30 (cm-level)                       |
|                                                                         |
|  +--------+-------------------+----------------------------+            |
|  | Level  | Cell Size         | Use Case                   |            |
|  +--------+-------------------+----------------------------+            |
|  | 0      | ~7,800 km         | Cube face                  |            |
|  | 5      | ~250 km           | Large region               |            |
|  | 10     | ~8 km             | City                       |            |
|  | 12     | ~2 km             | Neighborhood               |            |
|  | 14     | ~500 m            | Block                      |            |
|  | 16     | ~120 m            | Building cluster           |            |
|  | 20     | ~8 m              | Building                   |            |
|  | 30     | ~1 cm             | Max precision              |            |
|  +--------+-------------------+----------------------------+            |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  REGION COVERING:                                                       |
|                                                                         |
|  To search "all businesses within 5km of user":                         |
|                                                                         |
|  1. Define a circle (center = user, radius = 5km)                       |
|  2. S2 computes a "covering": a set of S2 cells that cover              |
|     the circle as tightly as possible                                   |
|  3. Query the index for businesses in any of those cell IDs             |
|  4. Filter by exact distance                                            |
|                                                                         |
|  The covering uses a mix of cell levels:                                |
|  * Large cells for the interior of the circle                           |
|  * Smaller cells near the boundary (for precision)                      |
|  * Typically 10-20 cells to cover a circle                              |
|                                                                         |
|  ADVANTAGE: No "neighbor" problem like geohash.                         |
|  The covering precisely captures the search area.                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### APPROACH 5: R-TREE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  R-TREE (USED IN POSTGIS)                                               |
|                                                                         |
|  CORE IDEA:                                                             |
|  A balanced tree where each node represents a bounding rectangle        |
|  (MBR — Minimum Bounding Rectangle) that contains all children.         |
|  Similar concept to B-tree but for spatial data.                        |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  STRUCTURE:                                                             |
|                                                                         |
|  Root: MBR covering the entire dataset                                  |
|  +---------------------------------------------------+                  |
|  |                                                   |                  |
|  |  Child 1: MBR [NW region]                         |                  |
|  |  +---------------------------+                     |                 |
|  |  | Grandchild: MBR [city A] |                     |                  |
|  |  | Grandchild: MBR [city B] |                     |                  |
|  |  +---------------------------+                     |                 |
|  |                                                   |                  |
|  |  Child 2: MBR [SE region]                         |                  |
|  |  +---------------------------+                     |                 |
|  |  | Grandchild: MBR [city C] |                     |                  |
|  |  | Grandchild: MBR [city D] |                     |                  |
|  |  +---------------------------+                     |                 |
|  +---------------------------------------------------+                  |
|                                                                         |
|  SEARCH: "Find all businesses within rectangle R"                       |
|  1. At root, check which children's MBRs overlap R                      |
|  2. Recurse into overlapping children                                   |
|  3. At leaf level, check actual business locations                      |
|  4. Return matches                                                      |
|                                                                         |
|  COMPLEXITY: O(log n) average, O(n) worst case (overlapping MBRs)       |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  PROS:                                                                  |
|  * Excellent for range queries (rectangles, circles)                    |
|  * Built into PostGIS, widely supported                                 |
|  * Handles dynamic inserts/deletes well (self-balancing)                |
|  * Good for both point and polygon data                                 |
|                                                                         |
|  CONS:                                                                  |
|  * Harder to distribute across machines (tree structure)                |
|  * Overlapping MBRs degrade search performance                          |
|  * More complex than geohash for simple point queries                   |
|  * Not easily cacheable by prefix (unlike geohash)                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMPARISON TABLE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  GEOSPATIAL INDEX COMPARISON                                            |
|                                                                         |
|  +----------+----------+----------+----------+----------+               |
|  | Aspect   | Geohash  | Quadtree | S2       | R-tree   |               |
|  +----------+----------+----------+----------+----------+               |
|  | Type     | Hash     | Tree     | Cell     | Tree     |               |
|  |          | (1D str) | (in-mem) | (Hilbert)| (B-tree  |               |
|  |          |          |          |          | variant) |               |
|  +----------+----------+----------+----------+----------+               |
|  | Storage  | Easy     | Hard     | Easy     | Easy     |               |
|  | in DB    | (string  | (custom  | (int64   | (PostGIS |               |
|  |          | column)  | struct)  | column)  | native)  |               |
|  +----------+----------+----------+----------+----------+               |
|  | Density  | Fixed    | Adaptive | Adaptive | Adaptive |               |
|  | Handling | grid     | (splits  | (multi-  | (MBR     |               |
|  |          |          | on need) | level)   | overlap) |               |
|  +----------+----------+----------+----------+----------+               |
|  | Boundary | Check 8  | Check    | Covering | MBR      |               |
|  | Handling | neighbors| adjacent | solves   | overlap  |               |
|  |          |          | leaves   | this     | check    |               |
|  +----------+----------+----------+----------+----------+               |
|  | Cache-   | Excellent| Poor     | Good     | Poor     |               |
|  | ability  | (prefix  | (tree    | (cell ID | (tree    |               |
|  |          | based)   | struct)  | ranges)  | struct)  |               |
|  +----------+----------+----------+----------+----------+               |
|  | Distrib- | Easy     | Hard     | Easy     | Hard     |               |
|  | ution    | (shard   | (tree    | (shard   | (tree    |               |
|  |          | by pfx)  | splits)  | by cell) | splits)  |               |
|  +----------+----------+----------+----------+----------+               |
|  | Dynamic  | Easy     | Rebuild  | Easy     | Easy     |               |
|  | Updates  | (re-hash)| needed   | (re-cell)| (rebal.) |               |
|  +----------+----------+----------+----------+----------+               |
|  | Sphere   | Poor     | Poor     | Excellent| OK with  |               |
|  | Handling | (flat    | (flat    | (native  | geodetic |               |
|  |          | approx)  | approx)  | sphere)  | coords)  |               |
|  +----------+----------+----------+----------+----------+               |
|  | Used By  | Redis    | Custom   | Google   | PostGIS  |               |
|  |          | Elastic  | in-mem   | Maps     | MongoDB  |               |
|  |          | DynamoDB | services | S2 lib   | Oracle   |               |
|  +----------+----------+----------+----------+----------+               |
|                                                                         |
|  RECOMMENDATION:                                                        |
|  * Simple + cacheable: GEOHASH (great for Redis, most common choice)    |
|  * Best precision on sphere: S2 (Google's choice)                       |
|  * Already using PostGIS: R-TREE                                        |
|  * In-memory, density-adaptive: QUADTREE                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6: DEEP DIVE — SEARCH FLOW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SEARCH FLOW: STEP BY STEP                                              |
|                                                                         |
|  User sends: lat=37.7749, lng=-122.4194, radius=5000m,                  |
|              category=restaurant, min_rating=4.0                        |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  STEP 1: COMPUTE GEOHASH PREFIX                                         |
|  ---------------------------------                                      |
|  Convert (37.7749, -122.4194) to geohash: "9q8yyk"                      |
|  For 5km radius, use precision 5: "9q8yy"                               |
|                                                                         |
|  STEP 2: FIND CANDIDATE CELLS                                           |
|  ------------------------------                                         |
|  Get the 9-cell neighborhood (self + 8 neighbors):                      |
|  ["9q8yy", "9q8yz", "9q8yw", "9q8yx", "9q8yv",                          |
|   "9q8z0", "9q8z1", "9q8wu", "9q8wv"]                                   |
|                                                                         |
|  STEP 3: CHECK CACHE                                                    |
|  ---------------------                                                  |
|  For each geohash prefix, check Redis cache:                            |
|  Key: "geo:9q8yy:restaurant"                                            |
|  If cache HIT: use cached business list                                 |
|  If cache MISS: query database                                          |
|                                                                         |
|  STEP 4: QUERY DATABASE (on cache miss)                                 |
|  ----------------------------------------                               |
|  SELECT id, name, lat, lng, rating, price_range                         |
|  FROM businesses                                                        |
|  WHERE geohash LIKE '9q8yy%'                                            |
|    AND category = 'restaurant'                                          |
|                                                                         |
|  Repeat for all 9 geohash prefixes.                                     |
|  (Can be done in parallel or as one IN query)                           |
|                                                                         |
|  STEP 5: COMPUTE EXACT DISTANCES                                        |
|  ----------------------------------                                     |
|  For each candidate business, compute Haversine distance                |
|  from user to business.                                                 |
|  Filter out businesses where distance > 5000m.                          |
|                                                                         |
|  (Geohash gives approximate candidates; exact distance is the filter)   |
|                                                                         |
|  STEP 6: APPLY ATTRIBUTE FILTERS                                        |
|  ----------------------------------                                     |
|  Filter by: rating >= 4.0                                               |
|  Filter by: open_now = true (check business hours vs current time)      |
|                                                                         |
|  STEP 7: RANK AND SORT                                                  |
|  -----------------------                                                |
|  Sort by distance (default) or rating or relevance score.               |
|  Relevance = weighted combination of distance, rating, review count.    |
|                                                                         |
|  STEP 8: PAGINATE AND RETURN                                            |
|  -----------------------------                                          |
|  Return top 20 results with pagination token.                           |
|  Total latency target: <200ms                                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### ADAPTIVE RADIUS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PROBLEM: EMPTY RESULTS IN SPARSE AREAS                                 |
|                                                                         |
|  User searches for "gas station" in rural Wyoming.                      |
|  5km radius returns 0 results.                                          |
|                                                                         |
|  SOLUTION: ADAPTIVE EXPANSION                                           |
|                                                                         |
|  1. Start with the requested radius (5km, geohash precision 5)          |
|  2. If fewer than N results (e.g., N=5):                                |
|     a. Decrease geohash precision (5 -> 4, cell becomes ~39km)          |
|     b. Search the wider area                                            |
|  3. Repeat until enough results or max radius reached                   |
|                                                                         |
|  ALTERNATIVELY:                                                         |
|  Use quadtree which naturally adapts — sparse areas have larger         |
|  leaf nodes covering more area.                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7: DEEP DIVE — DATABASE DESIGN

### SCHEMA

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BUSINESS TABLE                                                         |
|                                                                         |
|  +-------------------+------------------+---------------------+         |
|  | Column            | Type             | Notes               |         |
|  +-------------------+------------------+---------------------+         |
|  | id                | UUID / BIGINT    | Primary key         |         |
|  | name              | VARCHAR(255)     |                     |         |
|  | description       | TEXT             |                     |         |
|  | lat               | DOUBLE           | Latitude            |         |
|  | lng               | DOUBLE           | Longitude           |         |
|  | geohash           | VARCHAR(12)      | Pre-computed         |        |
|  | category          | VARCHAR(50)      | Indexed              |        |
|  | price_range       | SMALLINT (1-4)   | $ to $$$$            |        |
|  | avg_rating        | DECIMAL(2,1)     | Denormalized         |        |
|  | review_count      | INT              | Denormalized         |        |
|  | address           | TEXT             |                     |         |
|  | city              | VARCHAR(100)     | Indexed              |        |
|  | country           | VARCHAR(2)       | ISO code             |        |
|  | phone             | VARCHAR(20)      |                     |         |
|  | website_url       | VARCHAR(500)     |                     |         |
|  | photo_urls        | JSONB            | Array of URLs        |        |
|  | hours             | JSONB            | Mon-Sun open/close   |        |
|  | owner_id          | UUID             | FK to users          |        |
|  | is_active         | BOOLEAN          | Soft delete          |        |
|  | created_at        | TIMESTAMP        |                     |         |
|  | updated_at        | TIMESTAMP        |                     |         |
|  +-------------------+------------------+---------------------+         |
|                                                                         |
|  INDEXES:                                                               |
|  * PRIMARY: id                                                          |
|  * geohash (B-tree, prefix queries via LIKE 'prefix%')                  |
|  * (geohash, category) composite index                                  |
|  * category                                                             |
|  * city                                                                 |
|  * PostGIS: GIST index on geography(lat, lng) if using PostGIS          |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  REVIEW TABLE                                                           |
|                                                                         |
|  +-------------------+------------------+---------------------+         |
|  | Column            | Type             | Notes               |         |
|  +-------------------+------------------+---------------------+         |
|  | id                | UUID             | Primary key         |         |
|  | business_id       | UUID             | FK, indexed          |        |
|  | user_id           | UUID             | FK, indexed          |        |
|  | rating            | SMALLINT (1-5)   |                     |         |
|  | text              | TEXT             |                     |         |
|  | helpful_count     | INT              | Upvotes              |        |
|  | created_at        | TIMESTAMP        |                     |         |
|  +-------------------+------------------+---------------------+         |
|                                                                         |
|  INDEX: (business_id, created_at DESC) for fetching reviews by date     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DATABASE CHOICE & REPLICATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DATABASE STRATEGY:                                                     |
|                                                                         |
|  PRIMARY DATABASE: PostgreSQL with PostGIS                              |
|  WHY POSTGRESQL + POSTGIS? PostGIS adds native geospatial types         |
|  (GEOMETRY, GEOGRAPHY) and spatial indexes (R-tree via GiST).           |
|  ST_DWithin for radius search, ST_Distance for ranking — all in         |
|  SQL. Mature, battle-tested. Combines relational business data          |
|  (name, rating, hours) with geo queries in one engine.                  |
|                                                                         |
|  Why PostgreSQL?                                                        |
|  * PostGIS extension for native geospatial queries                      |
|  * R-tree (GIST) indexes for spatial data                               |
|  * Mature, reliable, well-understood                                    |
|  * Strong consistency for business data                                 |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  REPLICATION TOPOLOGY:                                                  |
|                                                                         |
|  +----------+                                                           |
|  | Primary  |  (handles writes: business CRUD)                          |
|  | (Leader) |                                                           |
|  +----------+                                                           |
|       |                                                                 |
|       +-- replication --> +----------+                                  |
|       |                   | Replica 1| (serves reads: search queries)   |
|       |                   +----------+                                  |
|       |                                                                 |
|       +-- replication --> +----------+                                  |
|       |                   | Replica 2| (serves reads)                   |
|       |                   +----------+                                  |
|       |                                                                 |
|       +-- replication --> +----------+                                  |
|                           | Replica 3| (serves reads)                   |
|                           +----------+                                  |
|                                                                         |
|  95% of traffic (reads) goes to replicas.                               |
|  5% of traffic (writes) goes to the primary.                            |
|  Replication lag of a few seconds is acceptable.                        |
|  (A new restaurant appearing 5s late is fine.)                          |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ALTERNATIVE: GEOSPATIAL INDEX IN MEMORY                                |
|                                                                         |
|  For maximum read performance, maintain the geospatial index            |
|  entirely in memory on the Location Service nodes:                      |
|                                                                         |
|  * Load all business IDs + locations into an in-memory quadtree         |
|  * Total memory: ~8 GB (fits easily)                                    |
|  * Periodically refresh from DB (every few minutes)                     |
|  * Search queries never touch the database directly                     |
|  * Only business detail lookups go to the database                      |
|                                                                         |
|  This is common at companies like Uber and Yelp.                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8: DEEP DIVE — CACHING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CACHING STRATEGY:                                                      |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  LAYER 1: CACHE BY GEOHASH PREFIX                                       |
|  -----------------------------------                                    |
|                                                                         |
|  Key format: "geo:{geohash_prefix}:{category}"                          |
|  Value: list of business IDs in that cell + category                    |
|                                                                         |
|  Example:                                                               |
|  Key:   "geo:9q8yy:restaurant"                                          |
|  Value: [biz_123, biz_456, biz_789, ...]                                |
|  TTL:   1 hour                                                          |
|                                                                         |
|  This cache is EXTREMELY effective because:                             |
|  * Many users in the same area search for the same thing                |
|  * Business data changes slowly                                         |
|  * Geohash prefix = natural cache key                                   |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  LAYER 2: BUSINESS DETAILS CACHE                                        |
|  ----------------------------------                                     |
|                                                                         |
|  Key: "biz:{business_id}"                                               |
|  Value: full business object (name, address, hours, photos, etc.)       |
|  TTL: 30 minutes                                                        |
|                                                                         |
|  Avoids DB lookup when user taps on a business in search results.       |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  LAYER 3: HOT AREA PRE-WARMING                                          |
|  ---------------------------------                                      |
|                                                                         |
|  Some areas are always hot:                                             |
|  * Downtown Manhattan, San Francisco Financial District                 |
|  * Airport terminals, major tourist areas                               |
|  * Near large event venues on event days                                |
|                                                                         |
|  Pre-warm these caches:                                                 |
|  * Analyze query patterns to identify hot geohash prefixes              |
|  * Proactively cache results before users ask                           |
|  * Refresh more frequently (every 5-10 minutes)                         |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  CACHE INVALIDATION:                                                    |
|                                                                         |
|  When a business is updated (address change, new hours, closure):       |
|                                                                         |
|  Option A: TIME-BASED EXPIRY (simple, preferred)                        |
|  * Cache entries expire after TTL (1 hour)                              |
|  * New data appears within 1 hour maximum                               |
|  * Acceptable for this use case (not safety-critical)                   |
|                                                                         |
|  Option B: EVENT-DRIVEN INVALIDATION (more complex)                     |
|  * Business Service publishes "business_updated" event                  |
|  * Cache subscriber computes affected geohash prefixes                  |
|  * Invalidates those specific cache entries                             |
|  * Faster propagation but more infrastructure                           |
|                                                                         |
|  Option C: HYBRID                                                       |
|  * Short TTL (15 min) + event-driven invalidation for critical updates  |
|  * Best of both worlds                                                  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  CACHE HIT RATE ESTIMATE:                                               |
|                                                                         |
|  * Popular areas: 90%+ cache hit rate                                   |
|  * Less popular areas: 50-70% hit rate                                  |
|  * Overall: ~80% cache hit rate                                         |
|  * At 80% hit rate with 58K QPS, only ~12K QPS hit the database         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 9: SCALING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCALING STRATEGY:                                                      |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  1. READ REPLICAS                                                       |
|  ------------------                                                     |
|                                                                         |
|  The system is 95% reads. Use read replicas aggressively.               |
|                                                                         |
|  +----------+                                                           |
|  | Primary  |----+---> Replica 1 (US-East reads)                        |
|  | (Writes) |    +---> Replica 2 (US-East reads)                        |
|  +----------+    +---> Replica 3 (US-West reads)                        |
|                  +---> Replica 4 (EU reads)                             |
|                  +---> Replica 5 (Asia reads)                           |
|                                                                         |
|  Each replica can handle ~10K QPS.                                      |
|  5 replicas = ~50K QPS read capacity.                                   |
|  For peak (145K QPS after cache): add more replicas or scale cache.     |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  2. SHARDING BY GEOHASH                                                 |
|  -------------------------                                              |
|                                                                         |
|  If a single database can't handle the load, shard by geohash:          |
|                                                                         |
|  +--------------------+                                                 |
|  | Geohash prefix "9" | -> Shard A (Americas)                           |
|  | Geohash prefix "u" | -> Shard B (Europe)                             |
|  | Geohash prefix "w" | -> Shard C (Asia)                               |
|  +--------------------+                                                 |
|                                                                         |
|  Advantages:                                                            |
|  * Queries only hit one shard (proximity queries are local)             |
|  * Natural geographic distribution                                      |
|  * Each shard can have its own replicas                                 |
|                                                                         |
|  Challenges:                                                            |
|  * Uneven distribution (Manhattan shard >> rural Montana shard)         |
|  * Cross-boundary queries may hit multiple shards (rare)                |
|  * Rebalancing when shards get too large                                |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  3. CDN FOR STATIC DATA                                                 |
|  -----------------------                                                |
|                                                                         |
|  Much of the business data is effectively static:                       |
|  * Business photos                                                      |
|  * Map tiles                                                            |
|  * Category icons                                                       |
|  * Static business info (rarely changes)                                |
|                                                                         |
|  Serve from CDN edge servers:                                           |
|  * Reduce latency (served from nearest POP)                             |
|  * Reduce load on origin servers                                        |
|  * Cache business detail pages at the edge                              |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  4. MULTI-REGION DEPLOYMENT                                             |
|  ----------------------------                                           |
|                                                                         |
|  +------------------+     +------------------+     +------------------+ |
|  | US-EAST          |     | EU-WEST          |     | AP-SOUTHEAST     | |
|  |                  |     |                  |     |                  | |
|  | Location Svc     |     | Location Svc     |     | Location Svc     | |
|  | Business Svc     |     | Business Svc     |     | Business Svc     | |
|  | Redis Cache      |     | Redis Cache      |     | Redis Cache      | |
|  | DB Replica       |     | DB Replica       |     | DB Replica       | |
|  +------------------+     +------------------+     +------------------+ |
|           |                       |                        |            |
|           +----------- DB Primary (US-EAST) ---------------+            |
|                                                                         |
|  Each region has:                                                       |
|  * Full set of application services                                     |
|  * Local Redis cache                                                    |
|  * Local DB read replica                                                |
|  * Serves users in that geographic area                                 |
|                                                                         |
|  Writes go to the primary region and replicate out.                     |
|  Replication lag (seconds) is acceptable for business data updates.     |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  5. LOCATION SERVICE SCALING                                            |
|  ------------------------------                                         |
|                                                                         |
|  The Location Service is stateless (or holds an in-memory index).       |
|                                                                         |
|  Stateless approach:                                                    |
|  * Query DB/cache each time                                             |
|  * Easy horizontal scaling (just add pods)                              |
|  * Kubernetes HPA based on CPU/QPS                                      |
|                                                                         |
|  In-memory index approach:                                              |
|  * Each instance loads the full geospatial index (~8 GB)                |
|  * Zero-DB-hit searches (fastest possible)                              |
|  * Index refresh: periodically pull updates from DB                     |
|  * Slightly longer startup time (loading index)                         |
|  * Recommended for ultra-low latency requirements                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 10: INTERVIEW Q&A

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q1: WHY NOT JUST USE A SQL QUERY WITH LAT/LNG RANGE?                   |
|                                                                         |
|  You could write:                                                       |
|  SELECT * FROM businesses                                               |
|  WHERE lat BETWEEN 37.5 AND 38.0                                        |
|    AND lng BETWEEN -122.5 AND -122.0                                    |
|                                                                         |
|  Problems:                                                              |
|  1. This searches a RECTANGLE, not a CIRCLE. Corners include            |
|     points that are farther than the radius.                            |
|  2. With separate indexes on lat and lng, the DB uses one index         |
|     and scans the other — inefficient.                                  |
|  3. A composite index (lat, lng) helps but is still not optimized       |
|     for 2D range queries the way a spatial index is.                    |
|  4. Does not account for Earth's curvature (longitude degrees           |
|     vary in distance based on latitude).                                |
|                                                                         |
|  Spatial indexes (geohash, quadtree, R-tree) are purpose-built to       |
|  handle these 2D proximity queries efficiently.                         |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  Q2: GEOHASH VS QUADTREE — WHEN WOULD YOU PICK EACH?                    |
|                                                                         |
|  GEOHASH:                                                               |
|  * When you need simplicity and cacheability                            |
|  * When using Redis or DynamoDB (store geohash as a string column)      |
|  * When you want easy sharding by geohash prefix                        |
|  * When your data density is roughly uniform                            |
|                                                                         |
|  QUADTREE:                                                              |
|  * When data density varies wildly (Manhattan vs rural)                 |
|  * When you need in-memory performance (no DB round-trip)               |
|  * When you control the search service infrastructure                   |
|  * When you need adaptive precision without manual tuning               |
|                                                                         |
|  In practice, many systems use GEOHASH for persistence/caching          |
|  and QUADTREE for in-memory search on the application layer.            |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  Q3: HOW DOES S2 GEOMETRY IMPROVE OVER GEOHASH?                         |
|                                                                         |
|  1. BETTER SPATIAL LOCALITY: S2 uses the Hilbert curve (not Z-order).   |
|     Adjacent cells in 2D are more likely to have adjacent cell IDs.     |
|     Geohash has "jumps" where adjacent cells have very different IDs.   |
|                                                                         |
|  2. SPHERE-NATIVE: S2 projects onto a sphere, not a flat grid.          |
|     Cell sizes are more uniform across latitudes.                       |
|     Geohash cells near the poles are distorted.                         |
|                                                                         |
|  3. REGION COVERING: S2 can compute a precise covering of any shape     |
|     (circle, polygon) using multiple cell levels. No need for the       |
|     "check 8 neighbors" hack that geohash requires.                     |
|                                                                         |
|  4. MULTI-LEVEL INDEXING: One business can be indexed at multiple       |
|     S2 cell levels for different query granularities.                   |
|                                                                         |
|  Trade-off: S2 is more complex to implement. If you're using Redis      |
|  GEOSEARCH, geohash is built in. S2 requires the S2 library.            |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  Q4: HOW DO YOU HANDLE THE "OPEN NOW" FILTER EFFICIENTLY?               |
|                                                                         |
|  Naive: For each candidate business, check if current time falls        |
|  within its hours of operation. This is O(k) per query.                 |
|                                                                         |
|  Better approaches:                                                     |
|                                                                         |
|  1. PRE-COMPUTE IN CACHE:                                               |
|     Every 15 minutes, compute which businesses are currently open.      |
|     Store as a bitmap or set: "open_businesses:{geohash}"               |
|     Intersect with search results.                                      |
|                                                                         |
|  2. TIME-BUCKETED INDEX:                                                |
|     Index businesses by (geohash, day_of_week, hour).                   |
|     "Businesses open at geohash 9q8yy on Tuesday at 2pm."               |
|                                                                         |
|  3. POST-FILTER (simplest):                                             |
|     Fetch slightly more candidates than needed.                         |
|     Filter by open hours in application code.                           |
|     Works well if most businesses are open during query time.           |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  Q5: HOW DO YOU KEEP THE GEOSPATIAL INDEX UP TO DATE?                   |
|                                                                         |
|  Business data changes infrequently (new restaurant, address change,    |
|  closure). Two strategies:                                              |
|                                                                         |
|  1. PERIODIC BATCH REBUILD:                                             |
|     * Every 15-30 minutes, rebuild the in-memory index from the DB      |
|     * Simple, predictable, works well for slowly-changing data          |
|     * Use blue-green deployment: build new index while old one serves   |
|     * Swap atomically when new index is ready                           |
|                                                                         |
|  2. INCREMENTAL UPDATES:                                                |
|     * Business Service publishes events on create/update/delete         |
|     * Location Service consumes events and updates index in-place       |
|     * Lower latency for changes (seconds vs minutes)                    |
|     * More complex: must handle partial failures, ordering              |
|                                                                         |
|  For the geohash in the database:                                       |
|  * Simply update the geohash column when lat/lng changes                |
|  * B-tree index on geohash auto-updates                                 |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  Q6: HOW DO YOU HANDLE SEARCH IN A DENSE AREA (e.g., MANHATTAN)?        |
|                                                                         |
|  Problem: 5km radius in Manhattan returns 10,000+ restaurants.          |
|  Users only want to see 20 at a time.                                   |
|                                                                         |
|  Solutions:                                                             |
|                                                                         |
|  1. RELEVANCE RANKING:                                                  |
|     Don't just sort by distance. Use a score:                           |
|     score = w1 * (1/distance) + w2 * rating + w3 * review_count         |
|     + w4 * recency_boost + w5 * personalization                         |
|     Return top 20 by score.                                             |
|                                                                         |
|  2. PAGINATION:                                                         |
|     Use cursor-based pagination (not offset).                           |
|     Cursor = last seen score + last seen ID.                            |
|     Efficient for "load more" UX.                                       |
|                                                                         |
|  3. REDUCE RADIUS AUTOMATICALLY:                                        |
|     If result count is too high, shrink the search radius.              |
|     "Showing restaurants within 1km" instead of 5km.                    |
|                                                                         |
|  4. CATEGORY FILTERS:                                                   |
|     Encourage users to filter (Italian, Sushi, etc.) to reduce          |
|     result set naturally.                                               |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  Q7: WHAT IS THE HAVERSINE FORMULA AND WHY DO WE NEED IT?               |
|                                                                         |
|  The Haversine formula computes the great-circle distance between       |
|  two points on a sphere given their latitudes and longitudes.           |
|                                                                         |
|  WHY NOT EUCLIDEAN DISTANCE?                                            |
|  The Earth is a sphere. Using sqrt((lat1-lat2)^2 + (lng1-lng2)^2)       |
|  is wrong because:                                                      |
|  1. Longitude degrees are not equal distances at different latitudes    |
|     (1° lng at equator = 111km, at 60°N = 55km)                         |
|  2. Straight-line distance through the Earth != surface distance        |
|                                                                         |
|  Haversine accounts for the Earth's curvature and gives accurate        |
|  surface distances. It's fast to compute (a few trig operations).       |
|                                                                         |
|  For SHORT distances (<10km): a simplified equirectangular              |
|  approximation (multiply lat difference by cos(lat)) is often           |
|  "good enough" and faster.                                              |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  Q8: HOW WOULD YOU ADD PERSONALIZATION TO SEARCH RESULTS?               |
|                                                                         |
|  Beyond distance and rating, personalize results based on:              |
|                                                                         |
|  1. USER HISTORY:                                                       |
|     * Businesses the user has visited/reviewed before                   |
|     * Preferred categories (user often searches "sushi")                |
|     * Preferred price range based on past visits                        |
|                                                                         |
|  2. COLLABORATIVE FILTERING:                                            |
|     "Users similar to you liked these businesses."                      |
|     Based on review overlap with similar users.                         |
|                                                                         |
|  3. TIME-OF-DAY:                                                        |
|     * Morning: coffee shops ranked higher                               |
|     * Lunch/dinner: restaurants ranked higher                           |
|     * Late night: bars ranked higher                                    |
|                                                                         |
|  4. IMPLEMENTATION:                                                     |
|     * Fetch candidates from geospatial index (same as before)           |
|     * Apply a ML-based re-ranking model on the candidate set            |
|     * Model takes: user features, business features, context            |
|     * Returns a personalized relevance score                            |
|     * This re-ranking step adds ~20-50ms latency                        |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  Q9: HOW WOULD YOU HANDLE SEARCHING ACROSS DIFFERENT ENTITY TYPES?      |
|                                                                         |
|  "Show me nearby restaurants AND gas stations AND ATMs."                |
|                                                                         |
|  Approach:                                                              |
|  1. SINGLE INDEX, MULTIPLE CATEGORIES:                                  |
|     All entity types in the same geospatial index.                      |
|     Filter by category during the search.                               |
|     Simple, but the index is larger.                                    |
|                                                                         |
|  2. SEPARATE INDEXES PER CATEGORY:                                      |
|     One index for restaurants, another for gas stations, etc.           |
|     Query each in parallel, merge results.                              |
|     Better cache behavior (restaurant index cached separately).         |
|                                                                         |
|  3. HYBRID:                                                             |
|     One unified index for geo queries.                                  |
|     Category-specific caches on top.                                    |
|     "geo:9q8yy:restaurant" vs "geo:9q8yy:atm"                           |
|                                                                         |
|  The hybrid approach is most common in practice.                        |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  Q10: HOW DO YOU HANDLE BUSINESS DATA CONSISTENCY ACROSS SERVICES?      |
|                                                                         |
|  When a business is updated (e.g., moved to a new address):             |
|                                                                         |
|  1. Business Service updates the Business DB (source of truth)          |
|  2. Publishes a "business_updated" event to a message queue             |
|  3. Location Service consumes the event:                                |
|     * Updates geohash for the new lat/lng                               |
|     * Updates in-memory index                                           |
|  4. Cache Service consumes the event:                                   |
|     * Invalidates affected cache entries                                |
|  5. Search Service consumes the event:                                  |
|     * Re-indexes the business in Elasticsearch (if used)                |
|                                                                         |
|  CONSISTENCY MODEL: Eventual consistency.                               |
|  For a few seconds/minutes, different services may show different data. |
|  This is acceptable because:                                            |
|  * Business changes are rare (a restaurant doesn't move often)          |
|  * Slightly stale data is not harmful (unlike a banking system)         |
|  * Strong consistency would require distributed transactions,           |
|    which are too slow and complex for this read-heavy system.           |
|                                                                         |
+-------------------------------------------------------------------------+
```
