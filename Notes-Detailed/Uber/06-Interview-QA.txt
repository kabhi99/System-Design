================================================================================
         UBER SYSTEM DESIGN
         Chapter 6: Interview Questions and Answers
================================================================================

This chapter provides detailed answers to common interview questions
about Uber's system design, helping you prepare for senior engineer
and architect-level interviews.


================================================================================
SECTION 6.1: CORE ARCHITECTURE QUESTIONS
================================================================================

Q1: HOW WOULD YOU DESIGN THE HIGH-LEVEL ARCHITECTURE FOR UBER?
──────────────────────────────────────────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  ANSWER STRUCTURE                                                      │
    │                                                                         │
    │  1. CLARIFY REQUIREMENTS (2 min)                                       │
    │     • Users: Riders and Drivers                                       │
    │     • Core flow: Request ride → match → pickup → dropoff             │
    │     • Scale: 100M+ users, 1M+ concurrent drivers                     │
    │     • Real-time: Location updates every 4 seconds                    │
    │                                                                         │
    │  2. HIGH-LEVEL COMPONENTS (5 min)                                      │
    │                                                                         │
    │     ┌────────────────────────────────────────────────────────────┐    │
    │     │                                                            │    │
    │     │   [Rider App]     [Driver App]                            │    │
    │     │        │               │                                   │    │
    │     │        └───────┬───────┘                                   │    │
    │     │                ▼                                           │    │
    │     │        [API Gateway]                                       │    │
    │     │                │                                           │    │
    │     │    ┌───────────┼───────────┬──────────────┐               │    │
    │     │    ▼           ▼           ▼              ▼               │    │
    │     │  [User]    [Location]   [Matching]    [Pricing]           │    │
    │     │ Service    Service      Service       Service             │    │
    │     │                                                            │    │
    │     │    │           │           │              │               │    │
    │     │    ▼           ▼           ▼              ▼               │    │
    │     │ [Postgres]  [Redis]    [Redis]        [Redis]            │    │
    │     │                                                            │    │
    │     │            [Kafka for async events]                       │    │
    │     │                                                            │    │
    │     └────────────────────────────────────────────────────────────┘    │
    │                                                                         │
    │  3. KEY SERVICES                                                       │
    │     • Location Service: Store/query driver locations                 │
    │     • Matching Service: Match riders with drivers                    │
    │     • Pricing Service: Calculate fares and surge                     │
    │     • Trip Service: Manage trip lifecycle                           │
    │     • Payment Service: Handle payments                               │
    │     • Notification Service: Push/SMS/Email                          │
    │                                                                         │
    │  4. DATA FLOW                                                          │
    │     Rider requests → Matching finds nearby → Driver accepts         │
    │     → Trip created → Navigation provided → Payment processed        │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


Q2: HOW DO YOU HANDLE 250,000+ LOCATION UPDATES PER SECOND?
───────────────────────────────────────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  ANSWER                                                                │
    │                                                                         │
    │  1. INGESTION TIER                                                     │
    │     • Stateless location ingestion service                           │
    │     • Horizontally scaled (100+ instances)                           │
    │     • Each handles ~2,500 updates/sec                                │
    │     • Load balanced across instances                                 │
    │                                                                         │
    │  2. STORAGE TIER                                                       │
    │     • Current location: Redis (in-memory for speed)                  │
    │     • History: Kafka → Time-series DB (for analytics)               │
    │     • Shard by driver_id or geographic region                       │
    │                                                                         │
    │  3. OPTIMIZATIONS                                                      │
    │     • Batch writes (accumulate 100ms, write batch)                  │
    │     • Skip insignificant updates (<10m movement)                    │
    │     • Use UDP for lower latency (trade reliability)                 │
    │     • Connection pooling to Redis                                    │
    │     • Compress location data                                         │
    │                                                                         │
    │  4. DATA MODEL IN REDIS                                                │
    │     • driver:{id}:location → {lat, lng, heading, ts}               │
    │     • cell:{s2_cell} → Set<driver_ids>  (for spatial query)        │
    │     • Update both atomically when location changes                  │
    │                                                                         │
    │  5. GEOGRAPHIC SHARDING                                                │
    │     • Shard Redis by city/region                                     │
    │     • NYC drivers on one cluster, LA on another                     │
    │     • Reduces cross-region latency                                   │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


Q3: WHY USE S2/H3 INSTEAD OF SIMPLE LAT/LNG?
────────────────────────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  ANSWER                                                                │
    │                                                                         │
    │  PROBLEM WITH LAT/LNG                                                  │
    │  • "Find drivers within 3km" requires checking every driver         │
    │  • Can't index efficiently (need function on column)                │
    │  • Distance calculation is expensive (trigonometry)                 │
    │                                                                         │
    │  S2/H3 BENEFITS                                                        │
    │                                                                         │
    │  1. INDEXABILITY                                                       │
    │     • Convert 2D coordinates to 1D cell ID                          │
    │     • Cell ID is an integer → standard B-tree index works          │
    │     • Nearby points have similar cell IDs                           │
    │                                                                         │
    │  2. EFFICIENT RANGE QUERIES                                            │
    │     • "Find all in 3km" = "Find all in cells [A, B, C, ...]"       │
    │     • O(N) where N = results, not total drivers                     │
    │                                                                         │
    │  3. HIERARCHICAL                                                       │
    │     • Zoom in/out by changing cell level                            │
    │     • Good for different precision needs                             │
    │                                                                         │
    │  4. SHARDING                                                           │
    │     • Shard data by cell ID                                          │
    │     • Locality preserved (nearby data on same shard)                │
    │                                                                         │
    │  WHY H3 (HEXAGONS) FOR SURGE                                          │
    │  • All neighbors equidistant                                         │
    │  • Smoother surge transitions                                        │
    │  • No corner artifacts                                               │
    │                                                                         │
    │  WHY S2 FOR LOCATION                                                   │
    │  • Better for arbitrary shapes (covering)                            │
    │  • More mature library                                               │
    │  • Used by Google internally                                         │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 6.2: MATCHING AND DISPATCH QUESTIONS
================================================================================

Q4: HOW DO YOU PREVENT TWO RIDE REQUESTS FROM MATCHING THE SAME DRIVER?
───────────────────────────────────────────────────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  ANSWER                                                                │
    │                                                                         │
    │  RACE CONDITION SCENARIO                                               │
    │                                                                         │
    │  Request A                       Request B                            │
    │      │                               │                                │
    │      │ Find nearby: [D1,D2,D3]      │ Find nearby: [D1,D4,D5]        │
    │      │ Best: D1                     │ Best: D1                        │
    │      │                               │                                │
    │      │ Send offer to D1 ─────────────│ Send offer to D1              │
    │      ▼                               ▼                                │
    │           D1 receives TWO offers! 💥                                  │
    │                                                                         │
    │  SOLUTION: ATOMIC RESERVATION                                         │
    │  ═══════════════════════════════                                        │
    │                                                                         │
    │  Before sending offer, atomically reserve driver:                    │
    │                                                                         │
    │  // Redis command                                                      │
    │  SET driver:{D1}:reserved {request_A} NX EX 30                       │
    │                                                                         │
    │  NX = only set if not exists                                          │
    │  EX 30 = expires in 30 seconds                                       │
    │                                                                         │
    │  FLOW:                                                                 │
    │  1. Request A: SET ... NX → Success (got lock)                       │
    │  2. Request B: SET ... NX → Fails (already reserved)                │
    │  3. Request A sends offer to D1                                      │
    │  4. Request B tries next best driver (D4)                           │
    │                                                                         │
    │  AFTER RESPONSE:                                                       │
    │  • If accepted: Confirm, delete reservation                          │
    │  • If rejected: Delete reservation, try next                        │
    │  • If timeout: TTL expires, driver available again                  │
    │                                                                         │
    │  KEY INSIGHT                                                           │
    │  ───────────                                                           │
    │  This is optimistic locking. We assume we'll get the driver,        │
    │  but verify atomically before committing. Much faster than          │
    │  pessimistic locking (SELECT FOR UPDATE).                            │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


Q5: HOW WOULD YOU DESIGN THE MATCHING ALGORITHM?
────────────────────────────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  ANSWER                                                                │
    │                                                                         │
    │  SIMPLE APPROACH: NEAREST DRIVER                                      │
    │  ───────────────────────────────                                        │
    │  • Find drivers within radius                                        │
    │  • Calculate ETA for each                                            │
    │  • Pick lowest ETA                                                   │
    │  • Pros: Fast, simple                                                │
    │  • Cons: Not globally optimal, unfair to drivers                    │
    │                                                                         │
    │  PRODUCTION APPROACH: SCORING + BATCHING                              │
    │  ────────────────────────────────────────                               │
    │                                                                         │
    │  1. SCORING FUNCTION                                                   │
    │     score = w1 × eta_score                                           │
    │           + w2 × driver_rating                                       │
    │           + w3 × acceptance_rate                                     │
    │           + w4 × wait_time_fairness                                  │
    │           + w5 × vehicle_match                                       │
    │                                                                         │
    │     eta_score: Lower ETA = higher score                              │
    │     fairness: Driver waiting long = higher score                     │
    │     acceptance: Reliable driver = higher score                       │
    │                                                                         │
    │  2. BATCHING (Optional)                                                │
    │     • Collect requests over 2-5 second window                       │
    │     • Solve bipartite matching (Hungarian algorithm)                │
    │     • Globally optimal assignment                                    │
    │     • Trade-off: Slight delay for better matches                    │
    │                                                                         │
    │  3. IMPLEMENTATION                                                     │
    │     def find_best_driver(request):                                   │
    │         nearby = location_svc.find_nearby(request.pickup, 5km)      │
    │         candidates = filter(available, nearby)                       │
    │                                                                         │
    │         scored = []                                                    │
    │         for driver in candidates:                                     │
    │             eta = eta_svc.get_eta(driver.loc, request.pickup)       │
    │             score = calculate_score(driver, eta, request)           │
    │             scored.append((driver, score))                           │
    │                                                                         │
    │         return max(scored, key=lambda x: x[1])[0]                    │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


Q6: HOW DO YOU HANDLE DRIVER REJECTION OR TIMEOUT?
──────────────────────────────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  ANSWER                                                                │
    │                                                                         │
    │  TIMEOUT HANDLING                                                      │
    │  ─────────────────                                                      │
    │  • Driver has 15 seconds to respond                                  │
    │  • After timeout, try next best driver                              │
    │  • Maximum 3 retries before failing request                         │
    │                                                                         │
    │  STATE MACHINE                                                         │
    │  ─────────────                                                         │
    │                                                                         │
    │  [Pending] ──offer sent──► [Waiting] ──accepted──► [Matched]        │
    │                               │                                       │
    │                               │ rejected/timeout                     │
    │                               ▼                                       │
    │                          [Retry Queue]                               │
    │                               │                                       │
    │                               │ retries < 3                          │
    │                               ▼                                       │
    │                          [Find Next] ──► [Waiting]                   │
    │                               │                                       │
    │                               │ retries >= 3                         │
    │                               ▼                                       │
    │                          [Failed] ──► Notify rider                   │
    │                                                                         │
    │  IMPLEMENTATION                                                        │
    │  ───────────────                                                        │
    │                                                                         │
    │  def handle_driver_response(ride_id, response):                      │
    │      ride = get_ride(ride_id)                                         │
    │                                                                         │
    │      if response == ACCEPTED:                                         │
    │          ride.status = MATCHED                                        │
    │          release_reservation(ride.driver_id)                         │
    │          notify_rider(ride.rider_id, "Driver on the way!")          │
    │                                                                         │
    │      elif response in [REJECTED, TIMEOUT]:                           │
    │          release_reservation(ride.driver_id)                         │
    │          ride.excluded_drivers.add(ride.driver_id)                   │
    │          ride.retry_count += 1                                        │
    │                                                                         │
    │          if ride.retry_count < MAX_RETRIES:                          │
    │              next_driver = find_best_driver(                          │
    │                  ride.request,                                         │
    │                  exclude=ride.excluded_drivers                        │
    │              )                                                         │
    │              send_offer(next_driver, ride)                            │
    │          else:                                                         │
    │              ride.status = FAILED                                     │
    │              notify_rider(ride.rider_id, "No drivers available")    │
    │                                                                         │
    │  TRACKING                                                              │
    │  ────────                                                              │
    │  • Log rejections for driver scoring                                 │
    │  • High rejection rate → lower matching priority                    │
    │  • Timeouts might indicate driver's app crashed                     │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 6.3: ETA AND ROUTING QUESTIONS
================================================================================

Q7: HOW DO YOU CALCULATE ETA FOR MILLIONS OF ROUTES?
────────────────────────────────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  ANSWER                                                                │
    │                                                                         │
    │  NAIVE APPROACH (Won't work)                                          │
    │  ───────────────────────────                                            │
    │  • Model road network as graph                                       │
    │  • Run Dijkstra for each query                                       │
    │  • Problem: O((V+E)logV) per query, too slow                        │
    │  • NYC: ~1M intersections, 100ms+ per query                         │
    │                                                                         │
    │  PRODUCTION APPROACH: CONTRACTION HIERARCHIES                         │
    │  ─────────────────────────────────────────────                          │
    │                                                                         │
    │  1. PREPROCESSING (Offline, once)                                      │
    │     • Rank nodes by importance                                       │
    │     • "Contract" low-importance nodes                                │
    │     • Add shortcut edges between important nodes                    │
    │     • Takes hours, but done once                                     │
    │                                                                         │
    │  2. QUERY (Online, real-time)                                         │
    │     • Bidirectional search from source and destination              │
    │     • Only traverse "up" the hierarchy                              │
    │     • Meet in middle at important node                              │
    │     • <1ms per query!                                               │
    │                                                                         │
    │  3. TRAFFIC ADJUSTMENT                                                 │
    │     • Get static route from CH                                       │
    │     • For each segment, lookup current traffic factor               │
    │     • Adjust ETA based on live conditions                           │
    │                                                                         │
    │  CACHING                                                               │
    │  ───────                                                               │
    │  • Cache ETAs by S2 cell pairs + time bucket                        │
    │  • Key: eta:{src_cell}:{dst_cell}:{time_bucket}                     │
    │  • TTL: 60-120 seconds                                               │
    │  • 70-80% cache hit rate                                             │
    │                                                                         │
    │  BATCHING                                                              │
    │  ────────                                                              │
    │  • For matching: need ETA to 20 drivers                              │
    │  • Batch API: one call returns all 20 ETAs                          │
    │  • Parallel computation on server                                    │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 6.4: PRICING AND SURGE QUESTIONS
================================================================================

Q8: HOW DOES SURGE PRICING WORK?
────────────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  ANSWER                                                                │
    │                                                                         │
    │  PURPOSE                                                               │
    │  ───────                                                               │
    │  Balance supply and demand in real-time.                             │
    │  • High demand → prices rise → some riders wait                    │
    │  • High prices → more drivers come online                          │
    │  • Equilibrium: reasonable wait times                                │
    │                                                                         │
    │  CALCULATION                                                           │
    │  ───────────                                                           │
    │                                                                         │
    │  1. DIVIDE CITY INTO ZONES                                             │
    │     • Hexagonal grid (H3 library)                                    │
    │     • ~5km² per zone                                                │
    │                                                                         │
    │  2. MEASURE DEMAND/SUPPLY PER ZONE                                     │
    │     • Demand: active ride requests                                   │
    │     • Supply: available drivers                                      │
    │     • Ratio: demand / supply                                         │
    │                                                                         │
    │  3. CALCULATE SURGE MULTIPLIER                                         │
    │     if ratio < 1.0:                                                   │
    │         surge = 1.0  (no surge)                                      │
    │     else:                                                              │
    │         surge = f(ratio, historical, weather, events)               │
    │         surge = min(surge, MAX_SURGE)  # cap at 5-8x                │
    │                                                                         │
    │  4. SMOOTHING                                                          │
    │     • Don't change too quickly (confusing for users)                │
    │     • Step increments: 1.0 → 1.25 → 1.5...                         │
    │     • Hysteresis: goes up fast, down slow                           │
    │                                                                         │
    │  5. APPLY TO FARE                                                      │
    │     fare = (base + distance + time) × surge                         │
    │          + booking_fee  (not surged)                                 │
    │                                                                         │
    │  UPDATE FREQUENCY                                                      │
    │  ────────────────                                                       │
    │  • Calculate every 1-2 minutes                                       │
    │  • Store in Redis with 5-minute TTL                                 │
    │  • Broadcast to driver/rider apps                                    │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 6.5: SCALABILITY QUESTIONS
================================================================================

Q9: HOW DO YOU SCALE THE SYSTEM TO HANDLE 1 MILLION CONCURRENT DRIVERS?
───────────────────────────────────────────────────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  ANSWER                                                                │
    │                                                                         │
    │  STATELESS SERVICES                                                    │
    │  ──────────────────                                                     │
    │  • All business logic services are stateless                         │
    │  • Horizontal scaling: add more instances                            │
    │  • Kubernetes auto-scaling based on CPU/requests                    │
    │                                                                         │
    │  GEOGRAPHIC SHARDING                                                   │
    │  ────────────────────                                                   │
    │  • Shard data by city/region                                         │
    │  • NYC cluster, LA cluster, etc.                                     │
    │  • Independent scaling per region                                    │
    │  • Reduces cross-datacenter traffic                                  │
    │                                                                         │
    │  DATABASE SCALING                                                      │
    │  ────────────────                                                       │
    │  • PostgreSQL: Read replicas for queries                            │
    │  • Redis: Cluster mode, shard by driver_id                          │
    │  • Kafka: Partition by driver_id for ordering                       │
    │                                                                         │
    │  WEBSOCKET SCALING                                                     │
    │  ─────────────────                                                      │
    │  • 1M drivers = 1M WebSocket connections                            │
    │  • 10K connections per gateway server                               │
    │  • 100 gateway servers                                               │
    │  • Redis Pub/Sub for message routing                                │
    │                                                                         │
    │  LOAD BALANCING                                                        │
    │  ──────────────                                                        │
    │  • L4/L7 load balancer at entry                                     │
    │  • Sticky sessions for WebSocket                                    │
    │  • Health checks, auto-failover                                     │
    │                                                                         │
    │  CACHING                                                               │
    │  ───────                                                               │
    │  • Cache ETA, surge, driver info                                     │
    │  • Multi-level: local cache → Redis → database                     │
    │  • 80%+ cache hit rate                                               │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


Q10: HOW DO YOU HANDLE A DATA CENTER FAILURE?
─────────────────────────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  ANSWER                                                                │
    │                                                                         │
    │  MULTI-REGION DEPLOYMENT                                               │
    │  ────────────────────────                                               │
    │  • Primary and secondary regions                                     │
    │  • Active-active or active-passive                                  │
    │  • DNS failover (Route 53, Cloudflare)                              │
    │                                                                         │
    │  DATA REPLICATION                                                      │
    │  ────────────────                                                       │
    │  • PostgreSQL: Streaming replication to standby                     │
    │  • Redis: Redis Cluster with replicas                               │
    │  • Kafka: Multi-region replication                                   │
    │                                                                         │
    │  GRACEFUL DEGRADATION                                                  │
    │  ─────────────────────                                                  │
    │  • If location service down: use cached locations                   │
    │  • If surge service down: use default (1.0x) or cached             │
    │  • If payment fails: complete trip, charge later                    │
    │                                                                         │
    │  RECOVERY                                                              │
    │  ────────                                                              │
    │  • In-progress trips persisted to durable storage                   │
    │  • On recovery, resume trips from last known state                  │
    │  • Reconciliation jobs to fix any inconsistencies                   │
    │                                                                         │
    │  TESTING                                                               │
    │  ───────                                                               │
    │  • Chaos engineering: randomly kill services                        │
    │  • Disaster recovery drills                                         │
    │  • Gamedays to test failover                                        │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 6.6: QUICK-FIRE Q&A
================================================================================

Q: How do you ensure a driver doesn't receive multiple ride offers?
A: Reserve driver atomically with Redis SETNX before sending offer.

Q: How do you handle GPS inaccuracy?
A: Map matching - snap GPS coordinates to nearest road segment.

Q: How do drivers know about surge zones?
A: Push via WebSocket, show heat map in driver app.

Q: What happens if rider loses connectivity during trip?
A: Trip continues, driver marks arrival/completion, rider charged on reconnect.

Q: How do you prevent fare manipulation?
A: Route recorded on server, fare calculated from server-side data.

Q: How do you handle trips across city boundaries?
A: Use pickup location for surge, combine pricing from both cities.

Q: What's the latency target for ride matching?
A: <500ms from request to driver notification.

Q: How do you test surge pricing?
A: A/B testing, shadow mode (calculate but don't apply), simulation.

Q: How do you prevent drivers from gaming surge?
A: Monitor unusual patterns, detect coordinated offline behavior.

Q: What if ETA is way off from actual?
A: Log and analyze, retrain ML models, update traffic data.


================================================================================
SECTION 6.7: SYSTEM DESIGN INTERVIEW TEMPLATE
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  45-MINUTE UBER DESIGN INTERVIEW                                      │
    │                                                                         │
    │  1. REQUIREMENTS (5 min)                                               │
    │     □ Functional: Rider requests ride, driver accepts, trip, payment │
    │     □ Non-functional: Low latency (<500ms matching), high available │
    │     □ Scale: 100M users, 1M drivers, 250K location updates/sec      │
    │                                                                         │
    │  2. HIGH-LEVEL DESIGN (10 min)                                         │
    │     □ Draw major components                                           │
    │     □ Show data flow                                                  │
    │     □ Identify databases                                              │
    │                                                                         │
    │  3. DEEP DIVE (20 min) - Pick 2-3 areas                               │
    │     □ Location indexing (S2/Geohash)                                 │
    │     □ Matching algorithm                                              │
    │     □ ETA calculation                                                 │
    │     □ Surge pricing                                                   │
    │     □ Real-time communication                                         │
    │                                                                         │
    │  4. SCALABILITY (5 min)                                                │
    │     □ How to handle 10x growth?                                      │
    │     □ Database sharding strategy                                     │
    │     □ Caching layers                                                  │
    │                                                                         │
    │  5. WRAP UP (5 min)                                                    │
    │     □ Trade-offs discussed                                            │
    │     □ What would you do differently with more time?                 │
    │     □ Questions for interviewer                                       │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
                              END OF CHAPTER 6
================================================================================

