================================================================================
         UBER SYSTEM DESIGN
         Chapter 4: ETA Calculation and Routing
================================================================================

Accurate ETA (Estimated Time of Arrival) is crucial for user experience
and business operations. This chapter covers how Uber calculates ETAs,
routing algorithms, and traffic prediction.


================================================================================
SECTION 4.1: WHY ETA MATTERS
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  ETA IS USED EVERYWHERE                                               │
    │                                                                         │
    │  1. RIDER EXPERIENCE                                                   │
    │     "Your driver arrives in 3 minutes"                               │
    │     "Trip will take 25 minutes"                                      │
    │     "Arriving at 5:45 PM"                                            │
    │                                                                         │
    │  2. DRIVER MATCHING                                                    │
    │     Score drivers by pickup ETA                                      │
    │     Better ETA → higher matching priority                           │
    │                                                                         │
    │  3. PRICING                                                            │
    │     Fare = Base + (Rate × Time) + (Rate × Distance)                 │
    │     ETA directly affects pricing display                             │
    │                                                                         │
    │  4. SURGE CALCULATION                                                  │
    │     Areas with high demand + long ETAs → surge pricing             │
    │                                                                         │
    │  5. DRIVER INCENTIVES                                                  │
    │     "Complete 10 trips, earn bonus"                                  │
    │     Need ETA to plan driver shifts                                   │
    │                                                                         │
    │  ACCURACY REQUIREMENTS                                                 │
    │  ─────────────────────                                                  │
    │  • Within 2 minutes for short trips                                  │
    │  • Within 5 minutes for medium trips                                 │
    │  • User satisfaction drops sharply if ETA is wrong                  │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 4.2: ETA CALCULATION APPROACHES
================================================================================

APPROACH 1: HAVERSINE DISTANCE (Too Simple)
───────────────────────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  STRAIGHT-LINE DISTANCE                                               │
    │                                                                         │
    │  def haversine_distance(lat1, lng1, lat2, lng2):                     │
    │      """Calculate straight-line distance between two points."""      │
    │      R = 6371  # Earth's radius in km                                │
    │      dlat = radians(lat2 - lat1)                                     │
    │      dlng = radians(lng2 - lng1)                                     │
    │                                                                         │
    │      a = sin(dlat/2)**2 + cos(radians(lat1)) *                       │
    │          cos(radians(lat2)) * sin(dlng/2)**2                         │
    │      c = 2 * asin(sqrt(a))                                           │
    │                                                                         │
    │      return R * c                                                      │
    │                                                                         │
    │  eta_minutes = distance_km / average_speed_kmh * 60                  │
    │                                                                         │
    │  PROBLEMS:                                                             │
    │  ─────────                                                              │
    │  • Ignores roads (can't fly!)                                        │
    │  • Ignores traffic                                                   │
    │  • Ignores one-way streets                                           │
    │  • Ignores speed limits                                              │
    │                                                                         │
    │        A ═══════════════════════ B   ← Straight line: 2km           │
    │        │                         │                                    │
    │        │    ┌─────────────────┐  │                                    │
    │        │    │     RIVER       │  │                                    │
    │        │    └─────────────────┘  │                                    │
    │        │                         │                                    │
    │        └─────────────────────────┘   ← Actual route: 5km!           │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


APPROACH 2: ROAD NETWORK GRAPH + DIJKSTRA
─────────────────────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  ROAD NETWORK AS GRAPH                                                │
    │                                                                         │
    │  Model the road network as a weighted graph:                         │
    │  • Nodes = Intersections                                             │
    │  • Edges = Road segments                                             │
    │  • Weights = Travel time (or distance)                               │
    │                                                                         │
    │        [A]───5min───[B]───3min───[C]                                  │
    │         │            │            │                                    │
    │        2min         4min         6min                                  │
    │         │            │            │                                    │
    │        [D]───7min───[E]───2min───[F]                                  │
    │                                                                         │
    │  DIJKSTRA'S ALGORITHM                                                 │
    │  ══════════════════════                                                │
    │                                                                         │
    │  Finds shortest path from source to all other nodes.                 │
    │                                                                         │
    │  def dijkstra(graph, start, end):                                    │
    │      distances = {node: infinity for node in graph}                  │
    │      distances[start] = 0                                             │
    │      pq = [(0, start)]  # priority queue                             │
    │                                                                         │
    │      while pq:                                                         │
    │          current_dist, current = heappop(pq)                         │
    │                                                                         │
    │          if current == end:                                           │
    │              return current_dist                                      │
    │                                                                         │
    │          for neighbor, weight in graph[current]:                     │
    │              distance = current_dist + weight                        │
    │                                                                         │
    │              if distance < distances[neighbor]:                      │
    │                  distances[neighbor] = distance                      │
    │                  heappush(pq, (distance, neighbor))                  │
    │                                                                         │
    │      return distances[end]                                            │
    │                                                                         │
    │  COMPLEXITY: O((V + E) log V)                                        │
    │  • V = vertices (intersections)                                      │
    │  • E = edges (road segments)                                         │
    │                                                                         │
    │  PROBLEM: Too slow for real-time!                                    │
    │  NYC has ~1M intersections. Each query takes 100ms+                  │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


APPROACH 3: A* ALGORITHM (Better)
─────────────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  A* = DIJKSTRA + HEURISTIC                                            │
    │                                                                         │
    │  Uses a heuristic (estimated remaining distance) to guide search.    │
    │  Explores fewer nodes than Dijkstra.                                 │
    │                                                                         │
    │  f(n) = g(n) + h(n)                                                   │
    │                                                                         │
    │  Where:                                                                │
    │  • g(n) = actual cost from start to n                                │
    │  • h(n) = estimated cost from n to goal (heuristic)                 │
    │  • f(n) = total estimated cost                                       │
    │                                                                         │
    │  def a_star(graph, start, end):                                      │
    │      open_set = [(0, start)]                                          │
    │      g_score = {start: 0}                                             │
    │                                                                         │
    │      while open_set:                                                   │
    │          _, current = heappop(open_set)                               │
    │                                                                         │
    │          if current == end:                                           │
    │              return g_score[end]                                      │
    │                                                                         │
    │          for neighbor, weight in graph[current]:                     │
    │              tentative_g = g_score[current] + weight                 │
    │                                                                         │
    │              if tentative_g < g_score.get(neighbor, infinity):       │
    │                  g_score[neighbor] = tentative_g                     │
    │                  f = tentative_g + heuristic(neighbor, end)          │
    │                  heappush(open_set, (f, neighbor))                   │
    │                                                                         │
    │      return infinity                                                   │
    │                                                                         │
    │  def heuristic(a, b):                                                  │
    │      """Straight-line distance as optimistic estimate."""            │
    │      return haversine_distance(a.lat, a.lng, b.lat, b.lng)          │
    │                                                                         │
    │  WHY IT'S FASTER:                                                     │
    │  ─────────────────                                                      │
    │  Dijkstra explores in all directions (like ripples in water).        │
    │  A* explores toward the goal (like a focused beam).                  │
    │                                                                         │
    │  Dijkstra:                    A*:                                      │
    │      ○ ○ ○ ○ ○                    ○                                   │
    │    ○ ○ ○ ○ ○ ○ ○              ○ ○ ○ ○                                 │
    │  ○ ○ ○ S ○ ○ ○ ○ ○        ○ ○ S ○ ○ ○ ○                               │
    │    ○ ○ ○ ○ ○ ○ ○ G            ○ ○ ○ ○ G                               │
    │      ○ ○ ○ ○ ○                    ○                                   │
    │                                                                         │
    │  Still not fast enough for production at scale!                      │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


APPROACH 4: CONTRACTION HIERARCHIES (Production)
────────────────────────────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  CONTRACTION HIERARCHIES                                              │
    │                                                                         │
    │  Key insight: Most routes use highways/main roads.                   │
    │  Pre-process to create "shortcuts" for common paths.                │
    │                                                                         │
    │  PREPROCESSING (Offline, once):                                       │
    │  ═══════════════════════════════                                        │
    │                                                                         │
    │  1. Rank nodes by importance                                         │
    │     Highway intersections = high importance                          │
    │     Residential streets = low importance                             │
    │                                                                         │
    │  2. "Contract" low-importance nodes                                  │
    │     Remove node, add shortcut edge                                   │
    │                                                                         │
    │     Before:    A ──3──> B ──5──> C                                   │
    │     After:     A ════════8═══════> C  (shortcut)                     │
    │                                                                         │
    │  3. Build hierarchical graph                                         │
    │                                                                         │
    │  QUERY (Online, real-time):                                           │
    │  ════════════════════════════                                          │
    │                                                                         │
    │  Bidirectional search:                                               │
    │  • Forward from start (going up hierarchy)                          │
    │  • Backward from end (going up hierarchy)                           │
    │  • Meet in the middle (at high-importance node)                     │
    │                                                                         │
    │        Start ──────────────────────────────── End                    │
    │          │                                      │                     │
    │          ▼ (up hierarchy)      (up hierarchy) ▼                     │
    │         [Local]              [Local]                                 │
    │          │                      │                                     │
    │          ▼                      ▼                                     │
    │        [Highway] ════════════ [Highway]                              │
    │               (shortcut edges)                                        │
    │                                                                         │
    │  PERFORMANCE:                                                          │
    │  ─────────────                                                          │
    │  • Preprocessing: Hours (do once)                                    │
    │  • Query: <1 millisecond for any route!                             │
    │  • Used by OSRM (Open Source Routing Machine)                       │
    │                                                                         │
    │  TRADE-OFFS:                                                           │
    │  ────────────                                                          │
    │  • Requires hours of preprocessing                                   │
    │  • Graph updates (road closures) are expensive                      │
    │  • Not ideal for dynamic traffic                                     │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 4.3: INCORPORATING REAL-TIME TRAFFIC
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  TRAFFIC DATA SOURCES                                                 │
    │                                                                         │
    │  1. HISTORICAL PATTERNS                                               │
    │     • "This road is slow at 8 AM on Mondays"                        │
    │     • Aggregated from millions of past trips                        │
    │     • Stored by: road_segment × day_of_week × time_of_day          │
    │                                                                         │
    │  2. REAL-TIME GPS PROBES                                              │
    │     • Current driver locations and speeds                            │
    │     • Millions of updates per minute                                 │
    │     • Most accurate, most fresh                                      │
    │                                                                         │
    │  3. TRAFFIC INCIDENTS                                                  │
    │     • Accidents, construction, events                                │
    │     • From traffic APIs (Waze, TomTom)                              │
    │     • Manual reports                                                 │
    │                                                                         │
    │  ─────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  TRAFFIC-AWARE ETA CALCULATION                                        │
    │                                                                         │
    │  def calculate_traffic_eta(route_segments):                          │
    │      total_time = 0                                                    │
    │                                                                         │
    │      for segment in route_segments:                                   │
    │          # Base travel time (speed limit)                            │
    │          base_time = segment.length / segment.speed_limit            │
    │                                                                         │
    │          # Get traffic factor                                        │
    │          traffic_factor = get_traffic_factor(                        │
    │              segment.id,                                               │
    │              current_time()                                            │
    │          )                                                             │
    │                                                                         │
    │          # Adjust time                                                │
    │          adjusted_time = base_time * traffic_factor                  │
    │          total_time += adjusted_time                                  │
    │                                                                         │
    │      return total_time                                                 │
    │                                                                         │
    │  Traffic factor examples:                                             │
    │  • 1.0 = Free-flowing traffic                                        │
    │  • 1.5 = Moderate congestion                                         │
    │  • 3.0 = Heavy traffic                                               │
    │  • 5.0 = Standstill                                                  │
    │                                                                         │
    │  ─────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  TRAFFIC TILES (Uber's Approach)                                      │
    │                                                                         │
    │  Problem: Can't update edge weights in real-time                     │
    │          (would invalidate precomputed shortcuts)                    │
    │                                                                         │
    │  Solution: Separate static routing from dynamic traffic              │
    │                                                                         │
    │  1. Get route from static graph (fast)                               │
    │  2. For each segment, lookup current traffic                        │
    │  3. Adjust ETA based on traffic                                      │
    │                                                                         │
    │  TRAFFIC TILE STRUCTURE:                                              │
    │                                                                         │
    │  World divided into tiles (S2 cells)                                 │
    │  Each tile contains:                                                  │
    │  {                                                                     │
    │    "tile_id": "89c25a",                                               │
    │    "timestamp": "2024-01-15T08:30:00Z",                              │
    │    "segments": [                                                       │
    │      {                                                                  │
    │        "segment_id": "seg_123",                                       │
    │        "current_speed": 25,  // km/h                                 │
    │        "free_flow_speed": 50,                                        │
    │        "congestion_level": "moderate"                                │
    │      },                                                                │
    │      ...                                                               │
    │    ]                                                                    │
    │  }                                                                     │
    │                                                                         │
    │  Tiles updated every 30-60 seconds                                   │
    │  Cached in Redis/Memcached for fast access                           │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 4.4: ETA SERVICE ARCHITECTURE
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  ETA SERVICE COMPONENTS                                               │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │   Request: Get ETA from A to B                                 │  │
    │  │       │                                                         │  │
    │  │       ▼                                                         │  │
    │  │  ┌──────────────────────────────────────────────────────────┐  │  │
    │  │  │                    ETA Service                           │  │  │
    │  │  └──────────────────────────────────────────────────────────┘  │  │
    │  │       │                                                         │  │
    │  │       ├─────────────┬─────────────┬─────────────┐              │  │
    │  │       ▼             ▼             ▼             ▼              │  │
    │  │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐        │  │
    │  │  │ Map     │   │ Routing │   │ Traffic │   │ ML      │        │  │
    │  │  │ Matcher │   │ Engine  │   │ Service │   │ Model   │        │  │
    │  │  │         │   │         │   │         │   │         │        │  │
    │  │  │ Snap to │   │ Find    │   │ Current │   │ Adjust  │        │  │
    │  │  │ road    │   │ route   │   │ speed   │   │ for     │        │  │
    │  │  │ network │   │ segments│   │ factors │   │ patterns│        │  │
    │  │  └─────────┘   └─────────┘   └─────────┘   └─────────┘        │  │
    │  │       │             │             │             │              │  │
    │  │       └─────────────┴─────────────┴─────────────┘              │  │
    │  │                           │                                     │  │
    │  │                           ▼                                     │  │
    │  │                    ┌──────────────┐                             │  │
    │  │                    │ Combine &    │                             │  │
    │  │                    │ Return ETA   │                             │  │
    │  │                    └──────────────┘                             │  │
    │  │                           │                                     │  │
    │  │                           ▼                                     │  │
    │  │                    Response: 12 minutes                        │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  SERVICES EXPLAINED:                                                   │
    │  ─────────────────────                                                  │
    │                                                                         │
    │  1. MAP MATCHER                                                        │
    │     • GPS coordinates might not be exactly on road                   │
    │     • "Snap" to nearest road segment                                 │
    │     • Handle GPS errors/drift                                        │
    │                                                                         │
    │  2. ROUTING ENGINE                                                     │
    │     • Contraction Hierarchies for fast routing                       │
    │     • Returns sequence of road segments                              │
    │     • OSRM or Valhalla for open-source                              │
    │                                                                         │
    │  3. TRAFFIC SERVICE                                                    │
    │     • Real-time traffic data by segment                              │
    │     • Updates every 30-60 seconds                                    │
    │     • Stored in Redis/Memcached                                      │
    │                                                                         │
    │  4. ML MODEL                                                           │
    │     • Historical patterns for time-of-day adjustments               │
    │     • Learns from actual trip durations                              │
    │     • Improves over time                                             │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 4.5: ETA BATCHING AND CACHING
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  WHY BATCHING AND CACHING?                                            │
    │                                                                         │
    │  Problem: For driver matching, need ETA to 20+ nearby drivers.       │
    │           20 sequential routing calls = 200ms+ latency.               │
    │                                                                         │
    │  ─────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  BATCHED ETA API                                                       │
    │                                                                         │
    │  POST /eta/batch                                                       │
    │  {                                                                     │
    │    "destinations": [                                                   │
    │      {"lat": 37.7749, "lng": -122.4194},  // rider                  │
    │    ],                                                                   │
    │    "sources": [                                                        │
    │      {"lat": 37.7849, "lng": -122.4094},  // driver 1               │
    │      {"lat": 37.7649, "lng": -122.4294},  // driver 2               │
    │      {"lat": 37.7549, "lng": -122.4394},  // driver 3               │
    │      ...                                                               │
    │    ]                                                                    │
    │  }                                                                     │
    │                                                                         │
    │  Response:                                                             │
    │  {                                                                     │
    │    "etas": [                                                           │
    │      {"source_idx": 0, "dest_idx": 0, "eta_seconds": 180},          │
    │      {"source_idx": 1, "dest_idx": 0, "eta_seconds": 240},          │
    │      {"source_idx": 2, "dest_idx": 0, "eta_seconds": 360},          │
    │    ]                                                                    │
    │  }                                                                     │
    │                                                                         │
    │  ─────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  ETA CACHING                                                           │
    │                                                                         │
    │  Many queries for similar routes.                                    │
    │  Cache recently computed ETAs.                                        │
    │                                                                         │
    │  CACHE KEY DESIGN:                                                     │
    │  ───────────────────                                                    │
    │                                                                         │
    │  // Round coordinates to reduce key space                            │
    │  def make_cache_key(src_lat, src_lng, dst_lat, dst_lng):            │
    │      // Round to ~100m precision                                     │
    │      src_cell = s2_cell_id(src_lat, src_lng, level=16)              │
    │      dst_cell = s2_cell_id(dst_lat, dst_lng, level=16)              │
    │                                                                         │
    │      // Include time bucket (5-minute windows)                       │
    │      time_bucket = current_time() // 300                             │
    │                                                                         │
    │      return f"eta:{src_cell}:{dst_cell}:{time_bucket}"              │
    │                                                                         │
    │  CACHE TTL: 60-120 seconds                                           │
    │  (Traffic changes, so don't cache too long)                          │
    │                                                                         │
    │  HIT RATE: ~70-80% for popular areas                                 │
    │                                                                         │
    │  ─────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  IMPLEMENTATION:                                                       │
    │                                                                         │
    │  def get_eta(src, dst):                                               │
    │      cache_key = make_cache_key(src, dst)                            │
    │                                                                         │
    │      # Check cache                                                    │
    │      cached = redis.get(cache_key)                                   │
    │      if cached:                                                        │
    │          return cached                                                 │
    │                                                                         │
    │      # Calculate                                                       │
    │      eta = calculate_eta(src, dst)                                   │
    │                                                                         │
    │      # Store in cache                                                 │
    │      redis.setex(cache_key, 90, eta)  # 90 second TTL               │
    │                                                                         │
    │      return eta                                                        │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 4.6: ROUTE GUIDANCE
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  TURN-BY-TURN NAVIGATION                                              │
    │                                                                         │
    │  Once driver accepts ride, provide navigation:                       │
    │                                                                         │
    │  1. "Head north on Market Street"                                    │
    │  2. "In 200m, turn left onto 5th Avenue"                            │
    │  3. "Continue for 1.2 km"                                            │
    │  4. "Your destination is on the right"                              │
    │                                                                         │
    │  NAVIGATION DATA STRUCTURE:                                           │
    │  ───────────────────────────                                            │
    │                                                                         │
    │  {                                                                     │
    │    "route": {                                                          │
    │      "geometry": "encoded_polyline",                                 │
    │      "distance_meters": 2400,                                        │
    │      "duration_seconds": 480,                                        │
    │      "legs": [                                                         │
    │        {                                                               │
    │          "steps": [                                                    │
    │            {                                                           │
    │              "maneuver": "turn",                                      │
    │              "modifier": "left",                                      │
    │              "instruction": "Turn left onto 5th Avenue",            │
    │              "distance": 200,                                        │
    │              "duration": 30,                                         │
    │              "geometry": "segment_polyline"                          │
    │            },                                                          │
    │            ...                                                         │
    │          ]                                                             │
    │        }                                                               │
    │      ]                                                                  │
    │    }                                                                    │
    │  }                                                                     │
    │                                                                         │
    │  ROUTE UPDATES:                                                        │
    │  ───────────────                                                        │
    │                                                                         │
    │  • Driver deviates from route → recalculate                         │
    │  • Traffic changes → suggest alternative                            │
    │  • Update every 30 seconds during trip                               │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
CHAPTER SUMMARY
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  ETA AND ROUTING - KEY TAKEAWAYS                                      │
    │                                                                         │
    │  ROUTING ALGORITHMS                                                    │
    │  ──────────────────                                                     │
    │  • Haversine: Too simple, ignores roads                              │
    │  • Dijkstra: Correct but slow O((V+E)logV)                          │
    │  • A*: Better, uses heuristic                                        │
    │  • Contraction Hierarchies: Production choice (<1ms)                │
    │                                                                         │
    │  TRAFFIC                                                               │
    │  ───────                                                               │
    │  • Historical patterns (day/time)                                    │
    │  • Real-time GPS probes from drivers                                 │
    │  • Traffic tiles updated every 30-60s                                │
    │                                                                         │
    │  OPTIMIZATION                                                          │
    │  ────────────                                                          │
    │  • Batch ETA requests (20+ drivers)                                  │
    │  • Cache with S2 cell + time bucket keys                            │
    │  • 70-80% cache hit rate                                             │
    │                                                                         │
    │  INTERVIEW TIP                                                         │
    │  ─────────────                                                         │
    │  Explain why Dijkstra is too slow.                                   │
    │  Describe Contraction Hierarchies concept.                           │
    │  Discuss traffic data integration.                                   │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
                              END OF CHAPTER 4
================================================================================

