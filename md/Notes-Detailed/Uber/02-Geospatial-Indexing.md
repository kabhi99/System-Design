# UBER SYSTEM DESIGN
*Chapter 2: Geospatial Indexing and Location Services*

The ability to efficiently query "find all drivers within X km" is the
core challenge in ride-hailing systems. This chapter covers geospatial
indexing techniques and location service design.

## SECTION 2.1: THE GEOSPATIAL PROBLEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CORE QUERIES WE NEED TO ANSWER                                         |
|                                                                         |
|  1. "Find all drivers within 3km of this point"                         |
|  2. "Find the 10 nearest drivers to this location"                      |
|  3. "Update driver location" (250,000 times/second!)                    |
|  4. "Calculate distance between two points"                             |
|  5. "Estimate travel time between two points"                           |
|                                                                         |
|  THE NAIVE APPROACH (And why it fails)                                  |
|  -------------------------------------                                  |
|                                                                         |
|  SELECT * FROM drivers                                                  |
|  WHERE status = 'available'                                             |
|    AND SQRT(POW(lat - :rider_lat, 2) + POW(lng - :rider_lng, 2))        |
|        < :radius;                                                       |
|                                                                         |
|  PROBLEMS:                                                              |
|  * Full table scan (1 million rows!)                                    |
|  * Can't use indexes (function on column)                               |
|  * Too slow for real-time (seconds, not milliseconds)                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.2: GEOSPATIAL INDEXING TECHNIQUES

### TECHNIQUE 1: GEOHASH

```
+-------------------------------------------------------------------------+
|                                                                         |
|  GEOHASH                                                                |
|                                                                         |
|  Geohash encodes a geographic location into a short string.             |
|  Nearby locations share common prefixes.                                |
|                                                                         |
|  EXAMPLE:                                                               |
|  ---------                                                              |
|  San Francisco: 37.7749, -122.4194 > "9q8yyk"                           |
|  Nearby point:  37.7750, -122.4195 > "9q8yym"                           |
|                                       ^^^^^^                            |
|                                       Same prefix!                      |
|                                                                         |
|  PRECISION LEVELS:                                                      |
|  +------------------------------------------------------------------+   |
|  | Length | Cell Width    | Cell Height   | Use Case                |   |
|  |----------------------------------------------------------------  |   |
|  |   1    | ~5,000 km     | ~5,000 km     | Continent               |   |
|  |   2    | ~1,250 km     | ~625 km       | Large country           |   |
|  |   3    | ~156 km       | ~156 km       | State                   |   |
|  |   4    | ~39 km        | ~19.5 km      | City                    |   |
|  |   5    | ~4.9 km       | ~4.9 km       | Neighborhood            |   |
|  |   6    | ~1.2 km       | ~609 m        | Street                  |   |
|  |   7    | ~153 m        | ~153 m        | Building                |   |
|  |   8    | ~38 m         | ~19 m         | House                   |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  HOW TO USE FOR PROXIMITY SEARCH:                                       |
|  ---------------------------------                                      |
|                                                                         |
|  1. Calculate geohash for rider's location (precision 6)                |
|  2. Find all 8 neighboring cells (to handle edge cases)                 |
|  3. Query drivers in all 9 cells                                        |
|  4. Calculate actual distance, filter to radius                         |
|                                                                         |
|  SELECT * FROM drivers                                                  |
|  WHERE geohash LIKE '9q8yy%'  -- Cell and neighbors                     |
|     OR geohash LIKE '9q8yym%'                                           |
|     OR geohash LIKE '9q8yyn%'                                           |
|     ...;                                                                |
|                                                                         |
|  PROS:                                                                  |
|  Y Simple string prefix matching                                        |
|  Y Can use standard B-tree index                                        |
|  Y Easy to understand                                                   |
|                                                                         |
|  CONS:                                                                  |
|  X Edge effects (need to check neighbors)                               |
|  X Uneven cell sizes at different latitudes                             |
|  X Multiple queries for neighbors                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### TECHNIQUE 2: QUADTREE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  QUADTREE                                                               |
|                                                                         |
|  Recursively divide space into 4 quadrants.                             |
|  More points in an area > more subdivisions.                            |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Initial space:           After subdivision:                      |  |
|  |                                                                   |  |
|  |  +-----------------+      +--------+--------+                     |  |
|  |  |                 |      |   NW   |   NE   |                     |  |
|  |  |                 |      | (empty)| (dense)|                     |  |
|  |  |    o o o        |  >   +--------+--------+                     |  |
|  |  |  o o o o        |      |   SW   |   SE   |                     |  |
|  |  |    o o          |      |(sparse)|(sparse)|                     |  |
|  |  +-----------------+      +--------+--------+                     |  |
|  |                                                                   |  |
|  |  NE quadrant is dense > subdivide further:                        |  |
|  |                                                                   |  |
|  |  +--------+--------+                                              |  |
|  |  |        |        |                                              |  |
|  |  |   NW   |o  NE   |  (recursively until threshold)               |  |
|  |  |        |        |                                              |  |
|  |  +--------+--------+                                              |  |
|  |  |        |o o     |                                              |  |
|  |  |   SW   |   SE   |                                              |  |
|  |  |        |o o o   |                                              |  |
|  |  +--------+--------+                                              |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  PROXIMITY SEARCH:                                                      |
|  ------------------                                                     |
|  1. Find the quadrant containing the query point                        |
|  2. Check if quadrant overlaps with search radius                       |
|  3. Recursively check overlapping quadrants                             |
|  4. Return points within radius                                         |
|                                                                         |
|  PROS:                                                                  |
|  Y Adapts to data density (more detail where needed)                    |
|  Y Efficient for non-uniform distributions                              |
|                                                                         |
|  CONS:                                                                  |
|  X More complex implementation                                          |
|  X Rebalancing needed when points move                                  |
|  X Memory overhead for tree structure                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### TECHNIQUE 3: S2 GEOMETRY (Google's Solution)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  S2 GEOMETRY LIBRARY                                                    |
|                                                                         |
|  Projects Earth onto a cube, then subdivides each face.                 |
|  Used by Google Maps, Uber, Foursquare.                                 |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |        Earth                    Cube Projection                   |  |
|  |                       >       +----------+                        |  |
|  |                                |    +---+  |                      |  |
|  |                                |    |   |  |                      |  |
|  |                                |    +---+  |                      |  |
|  |                                +----------+                       |  |
|  |                                                                   |  |
|  |  Each face divided into cells (like quadtree but on sphere)       |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  S2 CELL IDs:                                                           |
|  -------------                                                          |
|  * 64-bit integer uniquely identifies each cell                         |
|  * Hierarchical: parent/child relationship encoded                      |
|  * 30 levels (level 30 = ~1 cm2 cells)                                  |
|                                                                         |
|  Level    | Avg Area     | Use Case                                     |
|  --------------------------------------------------                     |
|  0        | 85M km2      | Face of cube (1/6 of Earth)                  |
|  4        | 300K km2     | Large country                                |
|  12       | 3 km2        | City district                                |
|  16       | 10,000 m2    | City block                                   |
|  23       | 1 m2         | Room                                         |
|  30       | 1 cm2        | Maximum precision                            |
|                                                                         |
|  COVERING:                                                              |
|  -----------                                                            |
|  For any shape (circle, polygon), S2 finds minimum set of cells         |
|  that cover it completely.                                              |
|                                                                         |
|  "3km radius around point" > [cell1, cell2, cell3, ...]                 |
|                                                                         |
|  PROS:                                                                  |
|  Y Uniform cell sizes globally                                          |
|  Y Efficient range queries                                              |
|  Y Works with any shape (not just circles)                              |
|  Y Battle-tested at Google/Uber scale                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.3: UBER'S LOCATION SERVICE ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LOCATION SERVICE ARCHITECTURE                                          |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Driver Apps (millions)                                           |  |
|  |       | Location updates (250K/sec)                               |  |
|  |       v                                                           |  |
|  |  +------------------------------------------------------------+   |  |
|  |  |              Load Balancer                                 |   |  |
|  |  +------------------------------------------------------------+   |  |
|  |       |                                                           |  |
|  |       v                                                           |  |
|  |  +------------------------------------------------------------+   |  |
|  |  |         Location Ingestion Service                         |   |  |
|  |  |  (Stateless, horizontally scaled)                          |   |  |
|  |  |  - Validate location data                                  |   |  |
|  |  |  - Calculate S2 Cell ID                                    |   |  |
|  |  |  - Write to storage                                        |   |  |
|  |  +------------------------------------------------------------+   |  |
|  |       |                    |                                      |  |
|  |       v                    v                                      |  |
|  |  +--------------+    +--------------+                             |  |
|  |  |    Redis     |    |    Kafka     |                             |  |
|  |  | (Current     |    | (Location    |                             |  |
|  |  |  locations)  |    |  history)    |                             |  |
|  |  +--------------+    +--------------+                             |  |
|  |       |                    |                                      |  |
|  |       |                    v                                      |  |
|  |       |           +--------------+                                |  |
|  |       |           |  Time-Series |                                |  |
|  |       |           |  Database    |                                |  |
|  |       |           |(Trip tracking)|                               |  |
|  |       |           +--------------+                                |  |
|  |       |                                                           |  |
|  |       v                                                           |  |
|  |  +------------------------------------------------------------+   |  |
|  |  |              Query Service                                 |   |  |
|  |  |  "Find drivers near this location"                         |   |  |
|  |  +------------------------------------------------------------+   |  |
|  |       |                                                           |  |
|  |       v                                                           |  |
|  |  Rider App / Matching Service                                     |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### REDIS DATA STRUCTURE FOR LOCATIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  OPTION 1: REDIS GEO COMMANDS                                           |
|  ============================                                           |
|                                                                         |
|  Redis has built-in geospatial support!                                 |
|                                                                         |
|  GEOADD drivers -122.4194 37.7749 "driver_123"                          |
|  GEOADD drivers -122.4095 37.7849 "driver_456"                          |
|                                                                         |
|  GEORADIUS drivers -122.4194 37.7749 3 km WITHDIST                      |
|  > Returns drivers within 3km with distances                            |
|                                                                         |
|  PROS:                                                                  |
|  Y Built-in, no custom code                                             |
|  Y Fast (O(N+log(M)) for N results, M total items)                      |
|                                                                         |
|  CONS:                                                                  |
|  X All data in one sorted set (memory bound)                            |
|  X Can't filter by driver status easily                                 |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  OPTION 2: SHARDED BY S2 CELL                                           |
|  ===============================                                        |
|                                                                         |
|  Shard drivers by their S2 cell ID.                                     |
|                                                                         |
|  Key: cell:{s2_cell_id}                                                 |
|  Value: Set of driver IDs in that cell                                  |
|                                                                         |
|  cell:89c25a  > {driver_123, driver_456, driver_789}                    |
|  cell:89c25b  > {driver_111, driver_222}                                |
|                                                                         |
|  Each driver also has:                                                  |
|  driver:{driver_id}:location > { lat, lng, status, timestamp }          |
|                                                                         |
|  QUERY FLOW:                                                            |
|  1. Calculate S2 covering cells for search area                         |
|  2. For each cell, get driver IDs from Redis set                        |
|  3. Lookup each driver's full location                                  |
|  4. Filter by status (available)                                        |
|  5. Calculate exact distance, return nearest                            |
|                                                                         |
|  UPDATE FLOW:                                                           |
|  1. Receive new location for driver                                     |
|  2. Calculate new S2 cell                                               |
|  3. If cell changed:                                                    |
|     - SREM old_cell driver_id                                           |
|     - SADD new_cell driver_id                                           |
|  4. Update driver:{id}:location                                         |
|                                                                         |
|  PROS:                                                                  |
|  Y Can filter by any attribute (status, vehicle type)                   |
|  Y Scales better (smaller sets)                                         |
|  Y Can shard across multiple Redis instances                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.4: LOCATION UPDATE FLOW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DRIVER LOCATION UPDATE SEQUENCE                                        |
|                                                                         |
|  Driver App         Ingestion         Redis            Kafka            |
|      |                |                |                |               |
|      | POST /location |                |                |               |
|      | {lat,lng,ts}   |                |                |               |
|      |--------------->|                |                |               |
|      |                |                |                |               |
|      |                | Validate       |                |               |
|      |                | Calculate S2   |                |               |
|      |                |                |                |               |
|      |                | HSET driver:123|                |               |
|      |                |--------------->|                |               |
|      |                |                |                |               |
|      |                | If cell changed:               |                |
|      |                | SREM old_cell  |                |               |
|      |                | SADD new_cell  |                |               |
|      |                |--------------->|                |               |
|      |                |                |                |               |
|      |                | Publish for history            |                |
|      |                |-------------------------------->|               |
|      |                |                |                |               |
|      |<---------------|                |                |               |
|      |    200 OK      |                |                |               |
|      |                |                |                |               |
|                                                                         |
|  OPTIMIZATIONS:                                                         |
|  ----------------                                                       |
|  * Batch updates (driver sends every 4s, but can batch in server)       |
|  * Skip update if location hasn't changed much (<10m)                   |
|  * Use UDP instead of HTTP for lower latency                            |
|  * Connection pooling to Redis                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.5: NEARBY DRIVERS QUERY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FIND NEARBY DRIVERS ALGORITHM                                          |
|                                                                         |
|  public List<Driver> findNearbyDrivers(                                 |
|      double lat, double lng, double radiusKm, int limit                 |
|  ) {                                                                    |
|      // 1. Calculate S2 cells covering the search area                  |
|      S2Point center = S2LatLng.fromDegrees(lat, lng).toPoint();         |
|      S2Cap searchArea = S2Cap.fromAxisArea(                             |
|          center,                                                        |
|          radiusKm * radiusKm / EARTH_RADIUS_KM_SQ                       |
|      );                                                                 |
|                                                                         |
|      S2RegionCoverer coverer = new S2RegionCoverer();                   |
|      coverer.setMaxLevel(12);  // ~3km cells                            |
|      coverer.setMaxCells(20);                                           |
|      List<S2CellId> coveringCells = coverer.getCovering(searchArea);    |
|                                                                         |
|      // 2. Query drivers in each cell                                   |
|      Set<String> candidateDriverIds = new HashSet<>();                  |
|      for (S2CellId cellId : coveringCells) {                            |
|          Set<String> driversInCell = redis.smembers(                    |
|              "cell:" + cellId.toToken()                                 |
|          );                                                             |
|          candidateDriverIds.addAll(driversInCell);                      |
|      }                                                                  |
|                                                                         |
|      // 3. Get full location data for candidates                        |
|      List<Driver> candidates = new ArrayList<>();                       |
|      for (String driverId : candidateDriverIds) {                       |
|          Map<String, String> data = redis.hgetall(                      |
|              "driver:" + driverId + ":location"                         |
|          );                                                             |
|          if ("available".equals(data.get("status"))) {                  |
|              candidates.add(parseDriver(driverId, data));               |
|          }                                                              |
|      }                                                                  |
|                                                                         |
|      // 4. Calculate actual distance, sort, return top N                |
|      return candidates.stream()                                         |
|          .map(d -> new DriverWithDistance(d, calculateDistance(         |
|              lat, lng, d.getLat(), d.getLng()                           |
|          )))                                                            |
|          .filter(d -> d.distance <= radiusKm)                           |
|          .sorted(Comparator.comparing(d -> d.distance))                 |
|          .limit(limit)                                                  |
|          .map(d -> d.driver)                                            |
|          .collect(Collectors.toList());                                 |
|  }                                                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  GEOSPATIAL INDEXING - KEY TAKEAWAYS                                    |
|                                                                         |
|  INDEXING TECHNIQUES                                                    |
|  -------------------                                                    |
|  * Geohash: Simple string prefix, good for basic use                    |
|  * Quadtree: Adapts to density, tree structure                          |
|  * S2 Geometry: Industry standard, uniform cells                        |
|                                                                         |
|  STORAGE                                                                |
|  -------                                                                |
|  * Redis for current locations (in-memory speed)                        |
|  * Shard by S2 cell for scalability                                     |
|  * Kafka for location history (audit, ML)                               |
|                                                                         |
|  QUERY FLOW                                                             |
|  ----------                                                             |
|  1. Calculate covering cells for search area                            |
|  2. Query drivers in each cell                                          |
|  3. Filter by status                                                    |
|  4. Calculate actual distance                                           |
|  5. Sort and return nearest                                             |
|                                                                         |
|  INTERVIEW TIP                                                          |
|  -------------                                                          |
|  Explain why naive SQL doesn't work.                                    |
|  Draw S2 cell covering for a radius search.                             |
|  Discuss Redis data structure for updates.                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 2

