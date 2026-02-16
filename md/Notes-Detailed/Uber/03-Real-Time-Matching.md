# UBER SYSTEM DESIGN
*Chapter 3: Real-Time Matching and Dispatch*

The matching system is the brain of Uber—deciding which driver gets
which ride request. This chapter covers matching algorithms, dispatch
optimization, and the real-time infrastructure that makes it work.

## SECTION 3.1: THE MATCHING PROBLEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS MATCHING?                                                     |
|                                                                         |
|  Given:                                                                |
|  * A rider requesting a ride at location P                            |
|  * N available drivers near P                                         |
|                                                                         |
|  Find:                                                                 |
|  * The "best" driver to assign to this ride                          |
|                                                                         |
|  But what does "best" mean?                                           |
|  * Shortest pickup time? (rider happiness)                           |
|  * Shortest driver travel? (driver happiness)                        |
|  * Best rating match?                                                 |
|  * Vehicle type match?                                                |
|  * Overall system efficiency?                                        |
|                                                                         |
|  CONSTRAINTS:                                                          |
|  * Must be fast (<100ms decision)                                    |
|  * Must be fair to drivers                                           |
|  * Must minimize rider wait time                                     |
|  * Must handle 1,000+ matches per second                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.2: MATCHING STRATEGIES

### STRATEGY 1: NEAREST DRIVER (Simple)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NEAREST DRIVER ALGORITHM                                             |
|                                                                         |
|  def find_best_driver(rider_location):                                |
|      # 1. Find nearby drivers                                        |
|      nearby = find_drivers_within(rider_location, radius=5km)        |
|                                                                         |
|      # 2. Calculate ETA for each                                     |
|      for driver in nearby:                                            |
|          driver.eta = calculate_eta(driver.location, rider_location) |
|                                                                         |
|      # 3. Return nearest                                             |
|      return min(nearby, key=lambda d: d.eta)                         |
|                                                                         |
|  PROS:                                                                 |
|  Y Simple to implement                                               |
|  Y Fast                                                              |
|  Y Minimizes rider wait time                                        |
|                                                                         |
|  CONS:                                                                 |
|  X Not globally optimal                                              |
|  X Can be unfair to drivers (same drivers always get rides)        |
|  X Doesn't consider future demand                                   |
|                                                                         |
|  EXAMPLE OF WHY IT FAILS:                                             |
|  --------------------------                                             |
|                                                                         |
|       D1 ------- R1 ------- R2 ------- D2                            |
|       |<-- 2min--|<-- 5min --|<-- 2min -|                            |
|                                                                         |
|  Nearest matching:                                                     |
|  * R1 gets D1 (2 min)                                                |
|  * R2 gets D2 (2 min)                                                |
|  * Total: 4 minutes                                                  |
|                                                                         |
|  If we assigned:                                                       |
|  * R1 gets D2 (7 min) — worse for R1                                |
|  * R2 gets D1 (7 min) — worse for R2                                |
|  * Total: 14 minutes — much worse!                                  |
|                                                                         |
|  In this case, nearest is optimal. But not always...                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### STRATEGY 2: BATCHED MATCHING (Uber's Approach)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BATCHED MATCHING                                                      |
|                                                                         |
|  Instead of matching each request immediately, collect requests       |
|  over a short window (2-5 seconds) and optimize globally.            |
|                                                                         |
|  Time: 0s           2s           4s                                   |
|        |            |            |                                    |
|        |  R1, R2,   |  Compute   |  R4, R5,                          |
|        |  R3 arrive |  optimal   |  R6 arrive                        |
|        |            |  matching  |                                    |
|        |            |            |                                    |
|                                                                         |
|  BIPARTITE MATCHING PROBLEM                                           |
|  ===========================                                           |
|                                                                         |
|  Riders (left)        Drivers (right)                                 |
|                                                                         |
|       R1 -------------- D1                                            |
|          \            /                                                |
|           \----------/                                                 |
|       R2 ------\------ D2                                             |
|                 \                                                       |
|       R3 -------------- D3                                            |
|                                                                         |
|  Each edge has a cost (ETA).                                         |
|  Find assignment that minimizes total cost.                          |
|                                                                         |
|  HUNGARIAN ALGORITHM                                                   |
|  --------------------                                                   |
|  * Solves bipartite matching in O(n³)                               |
|  * For N riders, N drivers                                           |
|  * Guarantees globally optimal solution                              |
|                                                                         |
|  SIMPLIFIED EXAMPLE:                                                   |
|  --------------------                                                   |
|                                                                         |
|  Cost matrix (ETA in minutes):                                       |
|  +-------------------------+                                          |
|  |         |  D1  |  D2  |  D3  |                                    |
|  |-------------------------|                                          |
|  |   R1    |  2   |  5   |  8   |                                    |
|  |   R2    |  4   |  3   |  6   |                                    |
|  |   R3    |  7   |  6   |  2   |                                    |
|  +-------------------------+                                          |
|                                                                         |
|  Nearest matching:                                                     |
|  R1>D1(2), R2>D2(3), R3>D3(2) = Total 7 min Y (optimal here)       |
|                                                                         |
|  But with more complex scenarios, batching helps!                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### STRATEGY 3: SCORING-BASED MATCHING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCORING FUNCTION                                                      |
|                                                                         |
|  Instead of just ETA, use a weighted score:                          |
|                                                                         |
|  score = w1 * eta_score                                              |
|        + w2 * driver_rating_match                                    |
|        + w3 * vehicle_type_score                                     |
|        + w4 * driver_wait_time_fairness                              |
|        + w5 * surge_price_willingness                                |
|        + w6 * historical_acceptance_rate                             |
|                                                                         |
|  FACTORS:                                                              |
|  ---------                                                              |
|                                                                         |
|  1. ETA Score (most important):                                      |
|     eta_score = 1.0 - (eta_minutes / max_eta)                       |
|                                                                         |
|  2. Driver Rating Match:                                             |
|     * Premium riders prefer high-rated drivers                       |
|     * New drivers need rides to build rating                        |
|                                                                         |
|  3. Vehicle Type:                                                     |
|     * Requested UberX? Don't show UberBlack driver                  |
|     * Unless rider is willing to upgrade                            |
|                                                                         |
|  4. Fairness:                                                         |
|     * Driver waiting 30 minutes gets priority                       |
|     * Prevents some drivers from getting all rides                  |
|                                                                         |
|  5. Acceptance Rate:                                                  |
|     * Driver who accepts 95% rides > 50% accepts                   |
|     * Reduces wasted offers                                          |
|                                                                         |
|  def calculate_match_score(rider, driver):                           |
|      eta = calculate_eta(driver.location, rider.pickup)              |
|      eta_score = max(0, 1.0 - eta / 15.0)  # 15 min max             |
|                                                                         |
|      fairness = min(1.0, driver.wait_minutes / 20.0)                 |
|                                                                         |
|      acceptance = driver.acceptance_rate                              |
|                                                                         |
|      score = (                                                         |
|          0.5 * eta_score +                                            |
|          0.2 * fairness +                                             |
|          0.2 * acceptance +                                           |
|          0.1 * rating_score(rider, driver)                           |
|      )                                                                 |
|      return score                                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.3: DISPATCH ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DISPATCH SERVICE ARCHITECTURE                                        |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |   Rider App                                                     |  |
|  |       |                                                         |  |
|  |       | Request Ride                                           |  |
|  |       v                                                         |  |
|  |  +----------------------------------------------------------+  |  |
|  |  |                   API Gateway                            |  |  |
|  |  +----------------------------------------------------------+  |  |
|  |       |                                                         |  |
|  |       v                                                         |  |
|  |  +----------------------------------------------------------+  |  |
|  |  |                 Ride Request Service                     |  |  |
|  |  |  - Validate request                                      |  |  |
|  |  |  - Check surge pricing                                   |  |  |
|  |  |  - Calculate fare estimate                              |  |  |
|  |  |  - Create ride request record                            |  |  |
|  |  +----------------------------------------------------------+  |  |
|  |       |                                                         |  |
|  |       v                                                         |  |
|  |  +----------------------------------------------------------+  |  |
|  |  |                  Dispatch Service                        |  |  |
|  |  |  (Core matching logic)                                   |  |  |
|  |  +----------------------------------------------------------+  |  |
|  |       |                    |                                    |  |
|  |       v                    v                                    |  |
|  |  +--------------+    +--------------+                          |  |
|  |  |   Location   |    |    Supply    |                          |  |
|  |  |   Service    |    |   Service    |                          |  |
|  |  |              |    |  (Driver     |                          |  |
|  |  |  "Nearby     |    |  availability|                          |  |
|  |  |   drivers"   |    |   status)    |                          |  |
|  |  +--------------+    +--------------+                          |  |
|  |       |                                                         |  |
|  |       v                                                         |  |
|  |  +----------------------------------------------------------+  |  |
|  |  |              Driver Communication Service                |  |  |
|  |  |  - Send ride offer via push/socket                      |  |  |
|  |  |  - Wait for response                                    |  |  |
|  |  |  - Handle timeout/rejection                             |  |  |
|  |  +----------------------------------------------------------+  |  |
|  |       |                                                         |  |
|  |       v                                                         |  |
|  |   Driver App                                                    |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.4: DISPATCH FLOW (SEQUENCE DIAGRAM)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RIDE REQUEST > DRIVER ASSIGNMENT FLOW                                |
|                                                                         |
|  Rider     RideSvc    Dispatch    Location    Driver     DriverApp   |
|    |          |          |           |          |            |        |
|    | Request  |          |           |          |            |        |
|    |--------->|          |           |          |            |        |
|    |          |          |           |          |            |        |
|    |          | Find     |           |          |            |        |
|    |          | Match    |           |          |            |        |
|    |          |--------->|           |          |            |        |
|    |          |          |           |          |            |        |
|    |          |          | Get nearby|          |            |        |
|    |          |          |----------->|          |            |        |
|    |          |          |           |          |            |        |
|    |          |          |<----------|          |            |        |
|    |          |          | [D1,D2,D3]|          |            |        |
|    |          |          |           |          |            |        |
|    |          |          | Calculate scores     |            |        |
|    |          |          | Select D1            |            |        |
|    |          |          |           |          |            |        |
|    |          |          | Reserve driver       |            |        |
|    |          |          |---------------------->|            |        |
|    |          |          |           |          |            |        |
|    |          |          | Send offer|          |            |        |
|    |          |          |---------------------------------->|        |
|    |          |          |           |          |            |        |
|    |          |          |           |          |            | ACCEPT |
|    |          |          |<----------------------------------|        |
|    |          |          |           |          |            |        |
|    |          |          | Update    |          |            |        |
|    |          |          | status    |          |            |        |
|    |          |          |---------------------->|            |        |
|    |          |          |           |          |            |        |
|    |          |<---------|           |          |            |        |
|    |          | Match    |           |          |            |        |
|    |          | confirmed|           |          |            |        |
|    |<---------|          |           |          |            |        |
|    | Driver   |          |           |          |            |        |
|    | assigned |          |           |          |            |        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### HANDLING DRIVER REJECTION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IF DRIVER REJECTS OR TIMES OUT?                                 |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Dispatch sends offer to D1                                    |  |
|  |       |                                                         |  |
|  |       v                                                         |  |
|  |  +---------+                                                    |  |
|  |  | Wait    |<---- 15 second timeout                           |  |
|  |  | for     |                                                    |  |
|  |  | response|                                                    |  |
|  |  +----+----+                                                    |  |
|  |       |                                                         |  |
|  |       v                                                         |  |
|  |  +---------------------------------------------------------+   |  |
|  |  |                    RESPONSE?                            |   |  |
|  |  +---------------------------------------------------------+   |  |
|  |       |                 |                    |                  |  |
|  |       v                 v                    v                  |  |
|  |   ACCEPTED          REJECTED            TIMEOUT               |  |
|  |       |                 |                    |                  |  |
|  |       |                 |                    |                  |  |
|  |       v                 +--------+-----------+                  |  |
|  |   Confirm                        |                              |  |
|  |   ride                           v                              |  |
|  |                          Try next driver (D2)                  |  |
|  |                                  |                              |  |
|  |                                  v                              |  |
|  |                          +---------+                            |  |
|  |                          | Max     |                            |  |
|  |                          | retries?|                            |  |
|  |                          +----+----+                            |  |
|  |                               |                                 |  |
|  |                   +-----------+-----------+                     |  |
|  |                   v                       v                     |  |
|  |                  NO                      YES                    |  |
|  |              Try D3                  Notify rider              |  |
|  |                                     "No drivers                |  |
|  |                                      available"                |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  RETRY STRATEGY:                                                       |
|  ----------------                                                       |
|  * Try 3 drivers before giving up                                    |
|  * Exclude previously tried drivers                                  |
|  * May increase search radius on retry                               |
|  * Track rejection for driver scoring                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.5: REAL-TIME COMMUNICATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PUSH NOTIFICATIONS vs WEBSOCKETS                                     |
|                                                                         |
|  WEBSOCKETS (Preferred for active users)                              |
|  ========================================                               |
|                                                                         |
|  * Persistent TCP connection                                          |
|  * Bi-directional communication                                       |
|  * Sub-second latency                                                 |
|  * Battery intensive (keep connection alive)                         |
|                                                                         |
|  Used for:                                                             |
|  * Ride offers to drivers                                            |
|  * Location updates during ride                                      |
|  * Real-time ETA updates                                             |
|                                                                         |
|  PUSH NOTIFICATIONS (Fallback)                                        |
|  ==============================                                        |
|                                                                         |
|  * APNs (iOS) / FCM (Android)                                        |
|  * No persistent connection                                          |
|  * Higher latency (1-5 seconds)                                      |
|  * Works when app is backgrounded                                    |
|                                                                         |
|  Used for:                                                             |
|  * Driver is offline, rider requests                                 |
|  * Trip reminders                                                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WEBSOCKET ARCHITECTURE                                               |
|                                                                         |
|  +----------------------------------------------------------------+   |
|  |                                                                |   |
|  |   Driver Apps (1M connections)                                |   |
|  |        |                                                       |   |
|  |        | WebSocket                                            |   |
|  |        v                                                       |   |
|  |   +------------------------------------------------------+    |   |
|  |   |            Load Balancer (Sticky)                   |    |   |
|  |   +------------------------------------------------------+    |   |
|  |        |                                                       |   |
|  |        v                                                       |   |
|  |   +----------+  +----------+  +----------+                    |   |
|  |   | Gateway  |  | Gateway  |  | Gateway  |  (100 servers)    |   |
|  |   | Server 1 |  | Server 2 |  | Server N |                    |   |
|  |   |          |  |          |  |          |                    |   |
|  |   | 10K conn |  | 10K conn |  | 10K conn |                    |   |
|  |   +----+-----+  +----+-----+  +----+-----+                    |   |
|  |        |             |             |                           |   |
|  |        +-------------+-------------+                           |   |
|  |                      |                                         |   |
|  |                      v                                         |   |
|  |   +------------------------------------------------------+    |   |
|  |   |               Redis Pub/Sub                          |    |   |
|  |   |  (Message routing between gateways)                  |    |   |
|  |   +------------------------------------------------------+    |   |
|  |                      |                                         |   |
|  |                      v                                         |   |
|  |               Dispatch Service                                |   |
|  |                                                                |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
|  MESSAGE ROUTING:                                                      |
|  -----------------                                                      |
|                                                                         |
|  Problem: Driver D1 is connected to Gateway 3.                       |
|           Dispatch runs on separate servers.                         |
|           How does Dispatch send message to D1?                      |
|                                                                         |
|  Solution: Redis Pub/Sub                                              |
|                                                                         |
|  1. Each Gateway subscribes to channel for its connections:          |
|     SUBSCRIBE gateway:3                                               |
|                                                                         |
|  2. Maintain mapping: driver_id > gateway_id (in Redis)              |
|     SET connection:D1 "gateway:3"                                    |
|                                                                         |
|  3. Dispatch publishes to correct channel:                           |
|     gateway_id = GET connection:D1                                   |
|     PUBLISH gateway:3 "{ride_offer...}"                              |
|                                                                         |
|  4. Gateway 3 receives message, sends to D1's socket                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.6: CONCURRENCY AND STATE MANAGEMENT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RACE CONDITIONS IN MATCHING                                          |
|                                                                         |
|  Problem: Multiple ride requests might try to match same driver      |
|                                                                         |
|  Time     Rider 1                    Rider 2                          |
|   |                                                                    |
|   |   Find nearby drivers           Find nearby drivers              |
|   |   > D1, D2, D3                  > D1, D2, D4                     |
|   |                                                                    |
|   |   Select best: D1               Select best: D1                  |
|   |                                                                    |
|   |   Send offer to D1              Send offer to D1                 |
|   |         |                              |                          |
|   |         +----------> D1 gets 2 offers!                           |
|   |                      Chaos! 🔥                                   |
|   v                                                                    |
|                                                                         |
|  SOLUTION: DRIVER RESERVATION                                         |
|  ===============================                                        |
|                                                                         |
|  // Before sending offer, atomically reserve driver                  |
|                                                                         |
|  SETNX driver:D1:reserved ride_request_123 EX 30                     |
|                                                                         |
|  // Only proceeds if we got the lock                                 |
|  if (reserved successfully) {                                         |
|      send_offer_to_driver(D1);                                        |
|  } else {                                                              |
|      // D1 already reserved, try D2                                  |
|      select_next_best_driver();                                       |
|  }                                                                     |
|                                                                         |
|  // After offer accepted/rejected, release                           |
|  DEL driver:D1:reserved                                               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  DRIVER STATE MACHINE                                                 |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |                      +----------+                               |  |
|  |                      | OFFLINE  |                               |  |
|  |                      +----+-----+                               |  |
|  |                           | Goes online                        |  |
|  |                           v                                     |  |
|  |                      +----------+                               |  |
|  |        +-------------|AVAILABLE |<------------+                |  |
|  |        |             +----+-----+             |                |  |
|  |        |                  | Ride offer        | Ride complete  |  |
|  |        |                  v                   |                |  |
|  |        |             +----------+             |                |  |
|  |        |             | RESERVED |             |                |  |
|  |        |             +----+-----+             |                |  |
|  |        |                  |                   |                |  |
|  |        |    +-------------+-------------+     |                |  |
|  |        |    |             |             |     |                |  |
|  |        |    v             v             v     |                |  |
|  |        | TIMEOUT      ACCEPTED      REJECTED  |                |  |
|  |        |    |             |             |     |                |  |
|  |        |    |             v             |     |                |  |
|  |        |    |        +----------+       |     |                |  |
|  |        |    |        |EN_ROUTE  |       |     |                |  |
|  |        |    |        +----+-----+       |     |                |  |
|  |        |    |             | Arrived     |     |                |  |
|  |        |    |             v             |     |                |  |
|  |        |    |        +----------+       |     |                |  |
|  |        |    |        | WAITING  |       |     |                |  |
|  |        |    |        +----+-----+       |     |                |  |
|  |        |    |             | Pickup      |     |                |  |
|  |        |    |             v             |     |                |  |
|  |        |    |        +----------+       |     |                |  |
|  |        |    |        |ON_TRIP   |       |     |                |  |
|  |        |    |        +----+-----+       |     |                |  |
|  |        |    |             |             |     |                |  |
|  |        +----+-------------+-------------+-----+                |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REAL-TIME MATCHING - KEY TAKEAWAYS                                   |
|                                                                         |
|  MATCHING STRATEGIES                                                   |
|  --------------------                                                   |
|  * Nearest driver: Simple, fast, not globally optimal                |
|  * Batched matching: Collect requests, optimize globally            |
|  * Scoring-based: Multi-factor (ETA, fairness, rating)              |
|                                                                         |
|  DISPATCH ARCHITECTURE                                                 |
|  ---------------------                                                  |
|  * Stateless dispatch service for horizontal scaling                 |
|  * Location service for nearby queries                               |
|  * WebSocket gateways for real-time communication                    |
|  * Redis Pub/Sub for message routing                                 |
|                                                                         |
|  CONCURRENCY                                                           |
|  -----------                                                           |
|  * Reserve driver before sending offer                               |
|  * Use Redis SETNX for atomic reservation                           |
|  * State machine for driver status                                   |
|                                                                         |
|  INTERVIEW TIP                                                         |
|  -------------                                                         |
|  Draw the dispatch flow sequence.                                    |
|  Explain race condition and solution.                                |
|  Discuss WebSocket vs Push trade-offs.                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 3

