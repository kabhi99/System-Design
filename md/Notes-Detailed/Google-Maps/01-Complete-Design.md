# DESIGN GOOGLE MAPS / NAVIGATION SYSTEM

*Complete Design: Requirements, Architecture, and Interview Guide*

## SECTION 1: UNDERSTANDING THE PROBLEM

Google Maps is a global-scale mapping and navigation platform that serves
billions of requests daily. The core challenge is delivering fast, accurate
routing and rich map experiences across web and mobile clients.

```
+-----------------------------------------------------------------------+
|                     GOOGLE MAPS - CORE CAPABILITIES                   |
+-----------------------------------------------------------------------+
|                                                                       |
|  +------------------+  +------------------+  +------------------+     |
|  |  Map Rendering   |  |   Directions     |  | Real-Time Nav    |     |
|  |  (tiles, POI,    |  |   (A > B route   |  | (turn-by-turn,   |     |
|  |   satellite)     |  |    planning)     |  |  rerouting)      |     |
|  +------------------+  +------------------+  +------------------+     |
|                                                                       |
|  +------------------+  +------------------+  +------------------+     |
|  | ETA Prediction   |  | Location Search  |  |  Traffic Layer   |     |
|  | (arrival time,   |  | (geocoding,      |  |  (live speed,    |     |
|  |  confidence)     |  |  autocomplete)   |  |   incidents)     |     |
|  +------------------+  +------------------+  +------------------+     |
|                                                                       |
|  +------------------+  +------------------+                           |
|  | Transport Modes  |  |  Offline Maps    |                           |
|  | (drive, walk,    |  |  (pre-downloaded |                           |
|  |  bike, transit)  |  |   regions)       |                           |
|  +------------------+  +------------------+                           |
+-----------------------------------------------------------------------+
```

Key dimensions of difficulty:
- The road network graph has hundreds of millions of segments worldwide
- Map tiles must render at sub-second latency for smooth pan/zoom
- Traffic conditions change every few seconds on busy corridors
- ETA must be accurate across diverse geographies and times of day
- Navigation must work reliably even with intermittent connectivity

## SECTION 2: REQUIREMENTS

### FUNCTIONAL REQUIREMENTS

```
+-----------------------------------------------------------------------+
|                      FUNCTIONAL REQUIREMENTS                          |
+-----------------------------------------------------------------------+
|                                                                       |
|  FR-1  Location Search / Geocoding                                    |
|        * Forward: "1600 Amphitheatre Pkwy" > (37.42, -122.08)         |
|        * Reverse: (lat, lng) > human-readable address                 |
|        * Autocomplete with fuzzy matching                             |
|                                                                       |
|  FR-2  Directions (A > B)                                             |
|        * Optimal route for driving, walking, biking, transit          |
|        * Alternative routes with comparison                           |
|        * Turn-by-turn instruction generation                          |
|                                                                       |
|  FR-3  Real-Time Navigation                                           |
|        * Continuous position tracking on route                        |
|        * Off-route detection and automatic rerouting                  |
|        * Speed limit and lane guidance                                |
|                                                                       |
|  FR-4  ETA Estimation                                                 |
|        * Predicted arrival time with confidence interval              |
|        * Dynamic update as traffic changes                            |
|                                                                       |
|  FR-5  Map Tile Rendering                                             |
|        * Seamless pan/zoom across 22 zoom levels (0-21)               |
|        * Satellite imagery, terrain, and street view overlays         |
|                                                                       |
|  FR-6  Transport Modes                                                |
|        * Car, walk, bicycle, public transit, ride-share               |
|        * Multi-modal trip planning (walk > bus > walk)                |
|                                                                       |
+-----------------------------------------------------------------------+
```

### NON-FUNCTIONAL REQUIREMENTS

```
+-----------------------------------------------------------------------+
|                    NON-FUNCTIONAL REQUIREMENTS                        |
+-----------------------------------------------------------------------+
|                                                                       |
|  NFR-1  Routing latency       < 500 ms for p95                        |
|  NFR-2  Tile load latency     < 200 ms (CDN edge hit)                 |
|  NFR-3  Availability          99.99% uptime                           |
|  NFR-4  Scale                 ~5 billion map tile requests / day      |
|                               ~1 billion direction requests / day     |
|  NFR-5  Freshness             Traffic data < 30 s stale               |
|  NFR-6  Accuracy              ETA within ~10% for 90% of trips        |
|  NFR-7  Global reach          Multi-region, low latency everywhere    |
|                                                                       |
+-----------------------------------------------------------------------+
```

## SECTION 3: BACK-OF-ENVELOPE ESTIMATION

```
+-----------------------------------------------------------------------+
|                    CAPACITY ESTIMATION                                |
+-----------------------------------------------------------------------+
|                                                                       |
|  Daily active users (DAU)          ~1.5 billion                       |
|  Tile requests / day               ~5 billion                         |
|  Routing requests / day            ~1 billion                         |
|  Navigation sessions / day         ~200 million                       |
|                                                                       |
|  --- Tile Storage ---                                                 |
|  Zoom levels: 0-21                                                    |
|  Total tiles at level 21:  4^21 ~ 4.4 trillion (but only ~30%         |
|                             have meaningful data - land/roads)        |
|  Avg raster tile size:     ~20 KB                                     |
|  Avg vector tile size:     ~5 KB                                      |
|  Estimated tile storage:   ~50 PB (raster), ~12 PB (vector)           |
|                                                                       |
|  --- Road Graph ---                                                   |
|  Road segments worldwide:  ~500 million                               |
|  Avg segment metadata:     ~200 bytes                                 |
|  Raw graph size:           ~100 GB                                    |
|  With contraction data:    ~300 GB (fits in memory cluster)           |
|                                                                       |
|  --- Traffic Pipeline ---                                             |
|  GPS pings from devices:   ~50 billion / day                          |
|  Throughput:               ~580K events / second                      |
|  After map-matching:       speed per segment every ~30 s              |
|                                                                       |
|  --- Bandwidth ---                                                    |
|  Tile serving:  5B x 10 KB avg = 50 PB / day ~ 4.6 Tbps               |
|  (CDN absorbs ~95% > origin sees ~230 Gbps)                           |
|                                                                       |
+-----------------------------------------------------------------------+
```

## SECTION 4: HIGH-LEVEL ARCHITECTURE

```
+-----------------------------------------------------------------------+
|                       HIGH-LEVEL ARCHITECTURE                         |
+-----------------------------------------------------------------------+
|                                                                       |
|    +------------+          +------------+                             |
|    |   Mobile   |          |    Web     |                             |
|    |   Client   |          |   Client   |                             |
|    +-----+------+          +-----+------+                             |
|          |                       |                                    |
|          +----------++-----------+                                    |
|                     ||                                                |
|                     vv                                                |
|           +---------+----------+                                      |
|           |    CDN / Edge      |  (tile cache, static assets)         |
|           +---------+----------+                                      |
|                     |                                                 |
|                     v                                                 |
|           +---------+----------+                                      |
|           |   API Gateway /    |                                      |
|           |   Load Balancer    |                                      |
|           +---------+----------+                                      |
|                     |                                                 |
|       +-------------+-------------+-------------+                     |
|       |             |             |             |                     |
|       v             v             v             v                     |
|  +----+-----+ +----+-----+ +----+-----+ +-----+----+                  |
|  |  Map Tile | | Routing  | | Geocoding| | Traffic  |                 |
|  |  Service  | | Service  | | Service  | | Service  |                 |
|  +----+------+ +----+-----+ +----+-----+ +----+-----+                 |
|       |             |             |             |                     |
|       |             v             |             v                     |
|       |       +-----+------+     |       +-----+------+               |
|       |       | Navigation |     |       |    ETA     |               |
|       |       |  Service   |     |       |  Service   |               |
|       |       +-----+------+     |       +-----+------+               |
|       |             |             |             |                     |
|       v             v             v             v                     |
|  +----+-------------+-------------+-------------+----+                |
|  |              Data & Storage Layer                  |               |
|  |  +----------+ +----------+ +----------+ +------+  |                |
|  |  |Tile Store| |Road Graph| | Geo Index| |Traffic|  |               |
|  |  | (S3/GCS) | |(in-mem)  | |(Elastic/ | | DB   |  |                |
|  |  |          | |          | | Trie)    | |(TSDB) |  |               |
|  |  +----------+ +----------+ +----------+ +------+  |                |
|  +----------------------------------------------------+               |
+-----------------------------------------------------------------------+
```

### SERVICE RESPONSIBILITIES

```
+-------------------+----------------------------------------------------+
|     Service       |              Responsibility                        |
+-------------------+----------------------------------------------------+
| Map Tile Service  | Serve pre-rendered / on-demand tiles at each       |
|                   | zoom level. Vector tile encoding. CDN origin.      |
+-------------------+----------------------------------------------------+
| Routing Service   | Compute shortest / fastest path on road graph.     |
|                   | Supports multiple transport modes.                 |
+-------------------+----------------------------------------------------+
| Geocoding Service | Forward / reverse geocoding. Autocomplete.         |
|                   | Address parsing and fuzzy matching.                |
+-------------------+----------------------------------------------------+
| Traffic Service   | Ingest GPS traces, map-match, aggregate speeds,    |
|                   | detect incidents, publish live traffic layer.      |
+-------------------+----------------------------------------------------+
| Navigation Service| Real-time turn-by-turn, off-route detection,       |
|                   | rerouting, offline map support.                    |
+-------------------+----------------------------------------------------+
| ETA Service       | ML-based arrival prediction. Confidence bands.     |
|                   | Historical + live traffic blending.                |
+-------------------+----------------------------------------------------+
```

## SECTION 5: MAP TILE RENDERING

### TILE PYRAMID

The world is projected (Web Mercator) and recursively subdivided into
square tiles. At zoom level z, there are 4^z tiles.

```
+-----------------------------------------------------------------------+
|                         TILE PYRAMID                                  |
+-----------------------------------------------------------------------+
|                                                                       |
|  Zoom 0:   1 tile  (entire world)                                     |
|            +--------+                                                 |
|            |        |                                                 |
|            | world  |                                                 |
|            |        |                                                 |
|            +--------+                                                 |
|                                                                       |
|  Zoom 1:   4 tiles                                                    |
|            +----+----+                                                |
|            | 0,0| 1,0|                                                |
|            +----+----+                                                |
|            | 0,1| 1,1|                                                |
|            +----+----+                                                |
|                                                                       |
|  Zoom 2:   16 tiles                                                   |
|            +--+--+--+--+                                              |
|            |  |  |  |  |                                              |
|            +--+--+--+--+                                              |
|            |  |  |  |  |                                              |
|            +--+--+--+--+                                              |
|            |  |  |  |  |                                              |
|            +--+--+--+--+                                              |
|            |  |  |  |  |                                              |
|            +--+--+--+--+                                              |
|                                                                       |
|  ...                                                                  |
|  Zoom 21:  ~4.4 trillion tiles (256x256 px each)                      |
|                                                                       |
|  Tile address: /{z}/{x}/{y}.png  or  .pbf (vector)                    |
+-----------------------------------------------------------------------+
```

### RASTER VS VECTOR TILES

```
+----------------------------------+------------------------------------+
|          RASTER TILES            |           VECTOR TILES             |
+----------------------------------+------------------------------------+
| Pre-rendered PNG/JPEG images     | Protobuf-encoded geometry + attrs  |
| ~15-25 KB per tile               | ~3-8 KB per tile                   |
| Served as-is from CDN            | Rendered on client (GPU)           |
| Fixed style at render time       | Dynamic styling (dark mode, etc.)  |
| Higher storage cost              | Lower storage, higher client CPU   |
| Simpler client                   | Smooth rotation and 3D tilt        |
| Static label placement           | Dynamic label placement            |
+----------------------------------+------------------------------------+
```

### TILE SERVING FLOW

```
+-----------------------------------------------------------------------+
|                       TILE SERVING FLOW                               |
+-----------------------------------------------------------------------+
|                                                                       |
|  Client requests /tiles/14/8192/5461.pbf                              |
|         |                                                             |
|         v                                                             |
|  +------+-------+    cache     +------------------+                   |
|  |   CDN Edge   +------------>|  Return cached    |                   |
|  |   (PoP)      |    HIT      |  tile instantly   |                   |
|  +------+-------+             +------------------+                    |
|         | MISS                                                        |
|         v                                                             |
|  +------+-------+    cache     +------------------+                   |
|  | Regional     +------------>|  Return + backfill|                   |
|  | Tile Cache   |    HIT      |  CDN edge         |                   |
|  +------+-------+             +------------------+                    |
|         | MISS                                                        |
|         v                                                             |
|  +------+-------+                                                     |
|  |  Tile Origin  |  Read from blob store (S3/GCS)                     |
|  |  Server       |  or render on-the-fly for rare tiles               |
|  +------+-------+                                                     |
|         |                                                             |
|         v                                                             |
|  +------+-------+                                                     |
|  | Blob Store   |  Pre-rendered tile archive                          |
|  | (S3 / GCS)   |  Petabytes of tile data                             |
|  +--------------+                                                     |
+-----------------------------------------------------------------------+
```

## SECTION 6: GEOCODING

### FORWARD GEOCODING PIPELINE

```
+-----------------------------------------------------------------------+
|                   FORWARD GEOCODING PIPELINE                          |
+-----------------------------------------------------------------------+
|                                                                       |
|  Input: "1600 Amphitheatre Parkway, Mountain View, CA"                |
|         |                                                             |
|         v                                                             |
|  +------+-----------+                                                 |
|  | Address Parser    |  Tokenize into components:                     |
|  |                   |  house_number=1600, street=Amphitheatre Pkwy,  |
|  |                   |  city=Mountain View, state=CA                  |
|  +------+-----------+                                                 |
|         |                                                             |
|         v                                                             |
|  +------+-----------+                                                 |
|  | Normalization     |  Expand abbreviations: Pkwy>Parkway, CA>Calif  |
|  |                   |  Lowercase, remove punctuation                 |
|  +------+-----------+                                                 |
|         |                                                             |
|         v                                                             |
|  +------+-----------+                                                 |
|  | Candidate Lookup  |  Trie / inverted index lookup                  |
|  |                   |  Produce candidate (lat,lng) matches           |
|  +------+-----------+                                                 |
|         |                                                             |
|         v                                                             |
|  +------+-----------+                                                 |
|  | Ranking / Scoring |  Score by edit distance, popularity,           |
|  |                   |  user location proximity, recency              |
|  +------+-----------+                                                 |
|         |                                                             |
|         v                                                             |
|  Output: { lat: 37.4220, lng: -122.0841, confidence: 0.98 }           |
+-----------------------------------------------------------------------+
```

### REVERSE GEOCODING

```
+-----------------------------------------------------------------------+
|                    REVERSE GEOCODING                                  |
+-----------------------------------------------------------------------+
|                                                                       |
|  Input: (37.4220, -122.0841)                                          |
|         |                                                             |
|         v                                                             |
|  +------+-----------+                                                 |
|  | Spatial Index     |  R-tree or geohash grid lookup                 |
|  | (R-tree/S2)      |  Find nearest address points / polygons         |
|  +------+-----------+                                                 |
|         |                                                             |
|         v                                                             |
|  +------+-----------+                                                 |
|  | Interpolation     |  If exact address not indexed, interpolate     |
|  |                   |  along the street segment (house number range) |
|  +------+-----------+                                                 |
|         |                                                             |
|         v                                                             |
|  Output: "1600 Amphitheatre Parkway, Mountain View, CA 94043"         |
+-----------------------------------------------------------------------+
```

### AUTOCOMPLETE & FUZZY MATCHING

```
+-----------------------------------------------------------------------+
|                    AUTOCOMPLETE ARCHITECTURE                          |
+-----------------------------------------------------------------------+
|                                                                       |
|  User types: "starbuc"                                                |
|         |                                                             |
|         v                                                             |
|  +------+-----------+                                                 |
|  | Prefix Trie      |  Trie over place names / addresses              |
|  |                   |  Returns candidates starting with "starbuc"    |
|  +------+-----------+                                                 |
|         |                                                             |
|         v                                                             |
|  +------+-----------+                                                 |
|  | Fuzzy Layer       |  Levenshtein distance < 2                      |
|  | (BK-tree /        |  Handles typos: "starbukc" > "starbucks"       |
|  |  Symspell)        |                                                |
|  +------+-----------+                                                 |
|         |                                                             |
|         v                                                             |
|  +------+-----------+                                                 |
|  | Personalized      |  Boost by: user history, proximity,            |
|  | Ranking           |  popularity, freshness                         |
|  +------+-----------+                                                 |
|         |                                                             |
|         v                                                             |
|  Output: ["Starbucks Reserve", "Starbucks - Main St", ...]            |
+-----------------------------------------------------------------------+
```

## SECTION 7: ROAD NETWORK & GRAPH MODEL

```
+-----------------------------------------------------------------------+
|                    ROAD NETWORK AS A GRAPH                            |
+-----------------------------------------------------------------------+
|                                                                       |
|  Representation:                                                      |
|    * Nodes  = intersections / endpoints                               |
|    * Edges  = road segments (directed, weighted)                      |
|    * Weight = time (preferred) or distance                            |
|                                                                       |
|  Example subgraph:                                                    |
|                                                                       |
|         (A)----5 min--->(B)----3 min--->(C)                           |
|          |               ^               |                            |
|          |               |               |                            |
|         2 min          4 min           6 min                          |
|          |               |               |                            |
|          v               |               v                            |
|         (D)----3 min--->(E)----2 min--->(F)                           |
|                                                                       |
|  Edge metadata per segment:                                           |
|  +--------------------+------------------------------------------+    |
|  | Field              | Example                                  |    |
|  +--------------------+------------------------------------------+    |
|  | segment_id         | seg_8823901                              |    |
|  | from_node          | node_42                                  |    |
|  | to_node            | node_43                                  |    |
|  | length_meters      | 320                                      |    |
|  | speed_limit_kmh    | 50                                       |    |
|  | road_class         | secondary                                |    |
|  | one_way            | true                                     |    |
|  | toll               | false                                    |    |
|  | turn_restrictions   | no_left_from_seg_8823900                |    |
|  | live_speed_kmh     | 38  (from traffic service)               |    |
|  +--------------------+------------------------------------------+    |
|                                                                       |
+-----------------------------------------------------------------------+
```

### HANDLING TURN RESTRICTIONS & ONE-WAY STREETS

```
+------------------------------------------------------------------------+
|                    TURN RESTRICTIONS                                   |
+------------------------------------------------------------------------+
|                                                                        |
|  Problem: Simple node-to-node graphs cannot model "no U-turn" or       |
|           "no left turn" because those depend on the incoming edge.    |
|                                                                        |
|  Solution: Edge-based graph (or "dual graph")                          |
|                                                                        |
|    Node-based:   A ----> B ----> C                                     |
|                          ^                                             |
|                          | (left turn banned from D>B>A)               |
|                          D                                             |
|                                                                        |
|    Edge-based:   (A>B) ----> (B>C)    allowed                          |
|                  (D>B) --X-> (B>A)    blocked (turn restriction)       |
|                  (D>B) ----> (B>C)    allowed                          |
|                                                                        |
|  Each edge in the dual graph represents a traversal:                   |
|    "arriving on segment X and departing on segment Y"                  |
|                                                                        |
|  One-way streets: simply omit the reverse edge from the graph.         |
+------------------------------------------------------------------------+
```

## SECTION 8: ROUTING ALGORITHMS

### DIJKSTRA'S ALGORITHM

```
+------------------------------------------------------------------------+
|                      DIJKSTRA'S ALGORITHM                              |
+------------------------------------------------------------------------+
|                                                                        |
|  * Classic shortest-path on weighted graph                             |
|  * Explores nodes in order of increasing distance from source          |
|  * Time complexity: O((V + E) log V) with binary heap                  |
|                                                                        |
|  Pros: Guaranteed optimal, simple implementation                       |
|  Cons: Explores in all directions - too slow for continent-scale       |
|        graphs (500M+ edges)                                            |
|                                                                        |
|  Exploration pattern (bidirectional search):                           |
|                                                                        |
|       Source o))))))))))                (((((((((((o Target            |
|              expanding outward    expanding outward                    |
|                        meet in the middle                              |
|                                                                        |
|  Bidirectional Dijkstra: run from both ends, meet in middle.           |
|  Roughly halves exploration but still O(V) worst case.                 |
+------------------------------------------------------------------------+
```

### A* ALGORITHM

```
+------------------------------------------------------------------------+
|                        A* ALGORITHM                                    |
+------------------------------------------------------------------------+
|                                                                        |
|  Improvement over Dijkstra: uses a heuristic h(n) to guide search      |
|  toward the target.                                                    |
|                                                                        |
|  f(n) = g(n) + h(n)                                                    |
|    g(n) = actual cost from source to n                                 |
|    h(n) = estimated cost from n to target (e.g., haversine distance)   |
|                                                                        |
|  Exploration pattern:                                                  |
|                                                                        |
|       Source o)))))))-->-->-->-->-->--->o Target                       |
|              directed exploration toward goal                          |
|                                                                        |
|  Pros: Explores far fewer nodes than Dijkstra                          |
|  Cons: Still touches too many nodes at continental scale               |
|        Heuristic must be admissible (never overestimate)               |
+------------------------------------------------------------------------+
```

### CONTRACTION HIERARCHIES (CH)

```
+------------------------------------------------------------------------+
|                   CONTRACTION HIERARCHIES                              |
+------------------------------------------------------------------------+
|                                                                        |
|  Key insight: pre-process the graph once, answer queries in            |
|  milliseconds by exploiting "shortcut" edges.                          |
|                                                                        |
|  PREPROCESSING (offline, hours):                                       |
|  1. Order nodes by "importance" (low-degree rural nodes first)         |
|  2. Contract each node: for neighbors u, v of contracted node w,       |
|     if shortest u>v path goes through w, add shortcut edge u>v         |
|  3. Result: augmented graph with shortcut edges                        |
|                                                                        |
|  Before contraction:                                                   |
|    A --2--> B --3--> C --1--> D                                        |
|                                                                        |
|  Contract B (low importance):                                          |
|    A --5--> C --1--> D    (shortcut A>C, weight=2+3)                   |
|    (B still exists but at lower level in hierarchy)                    |
|                                                                        |
|  QUERY (online, < 1 ms):                                               |
|  1. Bidirectional Dijkstra on the augmented graph                      |
|  2. Forward search: only relax edges to HIGHER importance nodes        |
|  3. Backward search: only relax edges to HIGHER importance nodes       |
|  4. Meet at highest-importance node on shortest path                   |
|                                                                        |
|        Source o ------> o  o <------ o Target                          |
|               \        /|  |\        /                                 |
|            up  \      / |  | \      /  up                              |
|                 \    /  |  |  \    /                                   |
|                  \  /   |  |   \  /                                    |
|                   o highway node o                                     |
|                   (highest importance)                                 |
|                                                                        |
|  Performance:                                                          |
|    * Preprocessing: ~2 hours for all of Europe                         |
|    * Query: < 1 ms (explores ~500-1000 nodes)                          |
|    * Space: ~2x original graph (shortcut edges)                        |
+------------------------------------------------------------------------+
```

### HIERARCHICAL ROUTING

```
+-------------------------------------------------------------------------+
|                   HIERARCHICAL ROUTING                                  |
+-------------------------------------------------------------------------+
|                                                                         |
|  Concept: partition road network into hierarchy of levels               |
|                                                                         |
|  Level 0 (local):       residential streets, alleys                     |
|  Level 1 (collector):   secondary roads                                 |
|  Level 2 (arterial):    major roads, state highways                     |
|  Level 3 (highway):     interstates, motorways                          |
|                                                                         |
|  +-------------------------------------------------------+              |
|  |  Level 3 (highways)                                    |             |
|  |   o========o==========o==========o========o           |              |
|  +---+--------+---------+-----------+--------+---+       |              |
|      |        |         |           |        |           |              |
|  +---+--------+---------+-----------+--------+---+       |              |
|  |  Level 2 (arterials)                           |       |             |
|  |   o---o---o---o---o---o---o---o---o---o       |       |              |
|  +---+---+---+---+---+---+---+---+---+---+---+   |       |              |
|      |   |   |   |   |   |   |   |   |   |       |       |              |
|  +---+---+---+---+---+---+---+---+---+---+---+   |       |              |
|  |  Level 0-1 (local streets)                 |   |       |             |
|  |   o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o     |   |       |                |
|  +--------------------------------------------+   |       |             |
|                                                    |       |            |
|  Routing: local > climb to highway > highway >     |       |            |
|           descend to local near destination         |       |           |
+-------------------------------------------------------+   |             |
+-------------------------------------------------------------------------+
```

## SECTION 9: REAL-TIME TRAFFIC

### GPS TRACE INGESTION PIPELINE

```
+-----------------------------------------------------------------------+
|                  TRAFFIC DATA PIPELINE                                |
+-----------------------------------------------------------------------+
|                                                                       |
|  +----------+   +----------+   +-----------+   +----------+           |
|  | Millions |   |  Kafka   |   |  Flink    |   | Traffic  |           |
|  | of GPS   +-->| Ingestion+-->| Stream    +-->| Speed    |           |
|  | Devices  |   |  Topic   |   | Processor |   |   DB     |           |
|  +----------+   +----------+   +-----------+   +-----+----+           |
|                                      |               |                |
|                                      v               v                |
|                                +-----------+   +-----+----+           |
|                                | Map       |   | Incident |           |
|                                | Matching  |   | Detector |           |
|                                | (HMM)     |   |          |           |
|                                +-----------+   +----------+           |
|                                                                       |
+-----------------------------------------------------------------------+
```

### MAP MATCHING

```
+-----------------------------------------------------------------------+
|                       MAP MATCHING                                    |
+-----------------------------------------------------------------------+
|                                                                       |
|  Problem: GPS points are noisy (5-15m error). Which road segment      |
|  is the device actually on?                                           |
|                                                                       |
|  Raw GPS trace:                                                       |
|      . . . .  . .  . . .    (noisy dots)                              |
|                                                                       |
|  Road segments:                                                       |
|      ===================     (segment A - highway)                    |
|           ----------         (segment B - side road)                  |
|                                                                       |
|  Hidden Markov Model (HMM):                                           |
|    * States: candidate road segments for each GPS point               |
|    * Emission probability: distance from GPS point to segment         |
|    * Transition probability: route plausibility between segments      |
|    * Viterbi algorithm finds most likely sequence of segments         |
|                                                                       |
|  Result: snapped trace on actual road segments with timestamps        |
|    o---o---o---o---o---o    (matched to segment A)                    |
+-----------------------------------------------------------------------+
```

### SPEED AGGREGATION & INCIDENT DETECTION

```
+-----------------------------------------------------------------------+
|                 SPEED AGGREGATION                                     |
+-----------------------------------------------------------------------+
|                                                                       |
|  For each road segment, every 30-second window:                       |
|                                                                       |
|  1. Collect all matched GPS traversals                                |
|  2. Compute median speed (robust to outliers)                         |
|  3. Compare to:                                                       |
|     * Speed limit > congestion ratio                                  |
|     * Historical speed for this time/day > anomaly score              |
|                                                                       |
|  +--segment_id--+--window--+--median_speed--+--free_flow--+--ratio--+ |
|  | seg_882      | 10:30:00 |   22 km/h      |  60 km/h   |  0.37    | |
|  | seg_882      | 10:30:30 |   18 km/h      |  60 km/h   |  0.30    | |
|  | seg_883      | 10:30:00 |   55 km/h      |  60 km/h   |  0.92    | |
|  +--segment_id--+--window--+--median_speed--+--free_flow--+--ratio--+ |
|                                                                       |
|  Incident Detection:                                                  |
|  * Sudden speed drop on multiple adjacent segments > likely accident  |
|  * Corroborate with user reports and camera feeds                     |
|  * Publish incident event to downstream consumers                     |
|                                                                       |
|  Historical + Live Blending:                                          |
|  * If few live data points (rural, night): weight historical higher   |
|  * If dense live data: weight real-time measurements higher           |
|  * Blended speed = α x live_speed + (1-α) x historical_speed          |
|    where α depends on sample count confidence                         |
+-----------------------------------------------------------------------+
```

## SECTION 10: ETA PREDICTION

```
+-----------------------------------------------------------------------+
|                      ETA PREDICTION                                   |
+-----------------------------------------------------------------------+
|                                                                       |
|  Simple approach: sum(segment_length / segment_speed) along route     |
|  Problem: doesn't account for signals, stops, acceleration patterns   |
|                                                                       |
|  ML-based ETA:                                                        |
|                                                                       |
|  +------------------+                                                 |
|  |   FEATURES       |                                                 |
|  +------------------+                                                 |
|  | Route segments   |                                                 |
|  | Live speeds      +------+                                          |
|  | Historical speeds|      |      +------------------+                |
|  | Time of day      |      +----->|  Gradient Boosted|                |
|  | Day of week      |      |      |  Trees / Deep    +---> ETA (min)  |
|  | Weather          +------+      |  Neural Network  |     ~ CI       |
|  | Special events   |             +------------------+                |
|  | Road class mix   |                                                 |
|  | Num. of turns    |                                                 |
|  | Traffic trend    |                                                 |
|  +------------------+                                                 |
|                                                                       |
|  Confidence Interval:                                                 |
|    "ETA: 23 min (likely 20-28 min)"                                   |
|    Wider interval during unusual conditions (weather, events)         |
|                                                                       |
|  Continuous Re-estimation:                                            |
|    During navigation, ETA is recalculated every 30s using:            |
|    * Remaining route segments                                         |
|    * Updated live traffic                                             |
|    * Actual progress vs predicted progress                            |
|                                                                       |
|  Rerouting Trigger:                                                   |
|    If new_route_ETA < current_route_ETA - threshold (e.g., 5 min),    |
|    suggest or automatically reroute                                   |
+-----------------------------------------------------------------------+
```

## SECTION 11: NAVIGATION

### TURN-BY-TURN NAVIGATION FLOW

```
+-----------------------------------------------------------------------+
|                 TURN-BY-TURN NAVIGATION                               |
+-----------------------------------------------------------------------+
|                                                                       |
|  +----------+    +------------+    +------------+    +-----------+    |
|  | GPS Fix  +--->| Snap to    +--->| Instruction+--->| Render    |    |
|  | (device) |    | Route      |    | Generator  |    | on Map    |    |
|  +----------+    +------+-----+    +------+-----+    +-----------+    |
|                         |                 |                           |
|                         v                 v                           |
|                  +------+-----+    +------+-----+                     |
|                  | Off-Route  |    | Voice       |                    |
|                  | Detector   |    | Synthesis   |                    |
|                  +------+-----+    +-------------+                    |
|                         |                                             |
|                         v                                             |
|                  +------+------+                                      |
|                  | Reroute     |                                      |
|                  | Engine      |                                      |
|                  +-------------+                                      |
|                                                                       |
|  Off-Route Detection:                                                 |
|    * Continuously compare device position to planned route            |
|    * If distance > 50m for > 5 seconds > off-route                    |
|    * Trigger reroute from current position to destination             |
|                                                                       |
|  Instruction Generation:                                              |
|    * "In 300 meters, turn right onto Oak Street"                      |
|    * Derived from road geometry angles, street names, landmarks       |
|    * Lane guidance: "Use the two right lanes"                         |
+-----------------------------------------------------------------------+
```

### OFFLINE MAPS

```
+-----------------------------------------------------------------------+
|                       OFFLINE MAPS                                    |
+-----------------------------------------------------------------------+
|                                                                       |
|  Download Package per Region:                                         |
|  +----------------------------+                                       |
|  |  Region: "San Francisco"   |                                       |
|  +----------------------------+                                       |
|  |  Vector tiles (zoom 0-16)  |  ~150 MB                              |
|  |  Road graph (local)        |  ~30 MB                               |
|  |  POI / address index       |  ~20 MB                               |
|  |  Precomputed CH shortcuts  |  ~40 MB                               |
|  +----------------------------+                                       |
|  |  Total: ~240 MB            |                                       |
|  +----------------------------+                                       |
|                                                                       |
|  Offline capabilities:                                                |
|  * Map viewing and panning (vector tiles)                             |
|  * Route computation (local graph + CH)                               |
|  * Address search (local index)                                       |
|  * Turn-by-turn navigation (no live traffic)                          |
|                                                                       |
|  Limitations:                                                         |
|  * No live traffic or rerouting based on conditions                   |
|  * Data may be stale (prompt user to update monthly)                  |
|  * Satellite imagery not included (too large)                         |
+-----------------------------------------------------------------------+
```

## SECTION 12: SCALING

### TILE CDN STRATEGY

```
+-----------------------------------------------------------------------+
|                      TILE CDN SCALING                                 |
+-----------------------------------------------------------------------+
|                                                                       |
|  +--------+    +--------+    +--------+    +--------+                 |
|  |  PoP   |    |  PoP   |    |  PoP   |    |  PoP   |                 |
|  | Tokyo  |    | London |    |  NYC   |    | Sydney |                 |
|  +---+----+    +---+----+    +---+----+    +---+----+                 |
|      |             |             |             |                      |
|      +------+------+------+------+             |                      |
|             |             |                    |                      |
|        +----+----+   +----+----+          +----+----+                 |
|        | Regional|   | Regional|          | Regional|                 |
|        | Cache   |   | Cache   |          | Cache   |                 |
|        | (US-W)  |   | (EU)    |          | (APAC)  |                 |
|        +----+----+   +----+----+          +----+----+                 |
|             |             |                    |                      |
|             +-------------+--------------------+                      |
|                           |                                           |
|                    +------+------+                                    |
|                    | Tile Origin |                                    |
|                    | (multi-reg) |                                    |
|                    +-------------+                                    |
|                                                                       |
|  Cache hit rate: ~95%+ for popular zoom levels (0-14)                 |
|  Long-tail tiles (zoom 18-21): lower hit rate, render on demand       |
|  TTL: 24h for base tiles, 5 min for traffic overlay tiles             |
+-----------------------------------------------------------------------+
```

### ROUTING GRAPH SHARDING

```
+------------------------------------------------------------------------+
|                  ROUTING GRAPH SHARDING                                |
+------------------------------------------------------------------------+
|                                                                        |
|  The global road graph is too large for a single machine.              |
|  Partition geographically with overlap at boundaries.                  |
|                                                                        |
|  +----------+----------+----------+                                    |
|  | Shard:   | Shard:   | Shard:   |                                    |
|  | Americas | Europe + | Asia +   |                                    |
|  |          | Africa   | Oceania  |                                    |
|  +----------+----------+----------+                                    |
|                                                                        |
|  Each shard:                                                           |
|  * Full CH-augmented graph for its region                              |
|  * Loaded entirely in RAM (~50-100 GB per region)                      |
|  * Multiple replicas for availability and load balancing               |
|                                                                        |
|  Cross-region routing:                                                 |
|  * Rare (e.g., driving from Europe to Asia)                            |
|  * Handled by stitching routes at border nodes                         |
|  * Border nodes shared between adjacent shards                         |
|                                                                        |
|  Live traffic integration:                                             |
|  * Edge weights updated in-place every 30 seconds                      |
|  * CH shortcuts recomputed periodically (customizable CH or            |
|    use time-dependent routing as fallback)                             |
+------------------------------------------------------------------------+
```

### TRAFFIC PIPELINE SCALING

```
+-----------------------------------------------------------------------+
|                TRAFFIC PIPELINE (KAFKA > FLINK)                       |
+-----------------------------------------------------------------------+
|                                                                       |
|  +-------+    +-----------+    +-----------+    +--------+            |
|  | GPS   |    |  Kafka    |    |   Flink   |    | Speed  |            |
|  | Pings +--->| (100+     +--->| (map-match+--->|  DB    |            |
|  | 580K/s|    |  parts)   |    |  + agg)   |    |(TSDB)  |            |
|  +-------+    +-----------+    +-----+-----+    +--------+            |
|                                      |                                |
|                                      v                                |
|                                +-----+-----+                          |
|                                | Incident   |                         |
|                                | Alerts     |                         |
|                                | (pub/sub)  |                         |
|                                +-----------+                          |
|                                                                       |
|  Kafka: partitioned by geohash prefix (co-locate nearby segments)     |
|  Flink: stateful map-matching per device, windowed aggregation        |
|  TSDB: time-series DB (e.g., InfluxDB, TimescaleDB) for speed data    |
|                                                                       |
|  Scaling levers:                                                      |
|  * Kafka partitions: scale ingestion horizontally                     |
|  * Flink parallelism: scale processing per geohash region             |
|  * TSDB sharding: shard by segment_id range                           |
+-----------------------------------------------------------------------+
```

### MULTI-REGION DEPLOYMENT

```
+------------------------------------------------------------------------+
|                  MULTI-REGION DEPLOYMENT                               |
+------------------------------------------------------------------------+
|                                                                        |
|        +-------------------+                                           |
|        |  Global DNS /     |                                           |
|        |  Anycast routing  |                                           |
|        +--------+----------+                                           |
|                 |                                                      |
|     +-----------+-----------+                                          |
|     |           |           |                                          |
|  +--+---+   +--+---+   +--+---+                                        |
|  | US   |   |  EU  |   | APAC |                                        |
|  +------+   +------+   +------+                                        |
|  | API GW|   | API GW|   | API GW|                                     |
|  | Route |   | Route |   | Route |                                     |
|  | Geo   |   | Geo   |   | Geo   |                                     |
|  | Traffic|   | Traffic|   | Traffic|                                  |
|  | Tiles |   | Tiles |   | Tiles |                                     |
|  +------+   +------+   +------+                                        |
|                                                                        |
|  Each region: independent stack for low-latency                        |
|  Cross-region: shared tile origin, async graph sync                    |
|  Failover: DNS health checks, automatic traffic shift                  |
+------------------------------------------------------------------------+
```

## SECTION 13: INTERVIEW Q&A

```
+------------------------------------------------------------------------+
|  Q1: Why use Contraction Hierarchies instead of plain Dijkstra?        |
+------------------------------------------------------------------------+
|                                                                        |
|  Plain Dijkstra explores millions of nodes on a continental graph,     |
|  taking seconds. CH pre-computes shortcut edges so that queries        |
|  only explore ~500-1000 nodes, answering in < 1 ms. The trade-off      |
|  is hours of preprocessing and ~2x storage for shortcuts. Since the    |
|  road graph changes slowly, this is an excellent trade-off for a       |
|  read-heavy system like Google Maps.                                   |
+------------------------------------------------------------------------+

+------------------------------------------------------------------------+
|  Q2: How do you handle live traffic with pre-computed shortcuts?       |
+------------------------------------------------------------------------+
|                                                                        |
|  Option A - Customizable CH: store a function (not fixed weight)       |
|  on each shortcut edge that computes weight from live child-edge       |
|  weights at query time. Slightly slower but always correct.            |
|                                                                        |
|  Option B - Periodic rebuild: re-contract the graph every N minutes    |
|  with updated weights. During rebuild, serve from the previous CH.     |
|                                                                        |
|  Option C - Hybrid: use CH for the highway-level core and A* with      |
|  live weights for the local-road "first/last mile."                    |
+------------------------------------------------------------------------+

+------------------------------------------------------------------------+
|  Q3: Vector tiles vs raster tiles - when would you choose each?        |
+------------------------------------------------------------------------+
|                                                                        |
|  Vector: preferred for modern clients - smaller transfer, dynamic      |
|  styling, smooth zoom/rotation. Requires GPU rendering on client.      |
|                                                                        |
|  Raster: used for satellite imagery (inherently raster), legacy        |
|  clients, or when server-side rendering control is needed (e.g.,       |
|  exact visual consistency for print/export).                           |
+------------------------------------------------------------------------+

+------------------------------------------------------------------------+
|  Q4: How does map matching work with noisy GPS data?                   |
+------------------------------------------------------------------------+
|                                                                        |
|  Use a Hidden Markov Model. Each GPS observation has candidate road    |
|  segments (states). Emission probabilities are based on GPS-to-road    |
|  distance. Transition probabilities favor connected, plausible road    |
|  sequences. The Viterbi algorithm finds the most likely path through   |
|  the HMM, giving an accurate matched trajectory even with 10-15m       |
|  GPS noise.                                                            |
+------------------------------------------------------------------------+

+------------------------------------------------------------------------+
|  Q5: How would you design the system for offline navigation?           |
+------------------------------------------------------------------------+
|                                                                        |
|  Pre-download a regional package containing vector tiles, local road   |
|  graph with CH shortcuts, and a POI/address index. On the device,      |
|  run the same CH query algorithm locally. Without live traffic, use    |
|  historical speed profiles stored in the package. Prompt users to      |
|  update packages periodically for road changes.                        |
+------------------------------------------------------------------------+

+------------------------------------------------------------------------+
|  Q6: How do you estimate ETA more accurately than summing segment      |
|       travel times?                                                    |
+------------------------------------------------------------------------+
|                                                                        |
|  Segment-sum misses intersection delays, traffic signals, and          |
|  acceleration patterns. A trained ML model (gradient-boosted trees     |
|  or neural network) takes features like route segments, live and       |
|  historical speeds, time of day, weather, and number of turns to       |
|  predict total trip time. It learns systematic biases the naive        |
|  approach misses. The model also outputs a confidence interval.        |
+------------------------------------------------------------------------+

+------------------------------------------------------------------------+
|  Q7: How do you scale the traffic pipeline to handle 580K GPS          |
|       events per second?                                               |
+------------------------------------------------------------------------+
|                                                                        |
|  Ingest into Kafka partitioned by geohash (nearby events land on       |
|  the same partition). Process with Flink: stateful map-matching per    |
|  device, then windowed speed aggregation per segment. Flink scales     |
|  horizontally by adding parallel instances per partition. Output to    |
|  a time-series DB sharded by segment ID. The entire pipeline is        |
|  designed for exactly-once semantics via Kafka transactions +          |
|  Flink checkpointing.                                                  |
+------------------------------------------------------------------------+

+------------------------------------------------------------------------+
|  Q8: What if a user requests a route that spans two graph shards?      |
+------------------------------------------------------------------------+
|                                                                        |
|  Shards overlap at border regions. The routing service identifies      |
|  which shards a route touches, queries each shard independently        |
|  (source>border, border>border, border>dest), and stitches the         |
|  partial paths at shared border nodes. For most queries (same-region   |
|  trips), only one shard is needed.                                     |
+------------------------------------------------------------------------+

+------------------------------------------------------------------------+
|  Q9: How do you handle a major road closure or natural disaster?       |
+------------------------------------------------------------------------+
|                                                                        |
|  1. Incident detection flags abnormal speed drops across many          |
|     adjacent segments.                                                 |
|  2. Operators can manually mark road closures via an admin tool.       |
|  3. The routing graph marks affected edges with infinite weight        |
|     (or removes them).                                                 |
|  4. Active navigation sessions on affected routes trigger immediate    |
|     rerouting.                                                         |
|  5. CH shortcuts involving closed edges are invalidated; fallback      |
|     to A* for affected routes until CH is rebuilt.                     |
+------------------------------------------------------------------------+

+------------------------------------------------------------------------+
|  Q10: How do you ensure the map tile pipeline stays fresh?             |
+------------------------------------------------------------------------+
|                                                                        |
|  Base map tiles (roads, buildings) are re-rendered from source data    |
|  on a weekly or daily cadence. Traffic overlay tiles refresh every     |
|  30-60 seconds. CDN TTLs are set accordingly: long for base tiles,     |
|  short for overlays. When source data changes (new road), an           |
|  invalidation signal purges affected tiles from CDN. Vector tiles      |
|  make partial updates easier since they contain structured data        |
|  rather than pre-baked pixels.                                         |
+------------------------------------------------------------------------+
```

*End of Google Maps / Navigation System Design Notes*
