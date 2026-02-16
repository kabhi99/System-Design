# UBER SYSTEM DESIGN: A DEEP DIVE
*From Zero to Millions of Rides Per Day*

### TABLE OF CONTENTS

· A Real-World Problem
· Part 1: Requirements & Core Challenges
∘ 1.1 Functional Requirements
∘ 1.2 Non-Functional Requirements
∘ 1.3 Scale Estimation
∘ 1.4 Main Challenges
· Part 2: Core Architecture — Real-Time Location Tracking
∘ 2.1 The Location Update Problem
∘ 2.2 WebSocket vs HTTP Polling: A Critical Decision
∘ 2.3 Location Gateway Architecture
∘ 2.4 Connection Registry Pattern
∘ 2.5 Location Update Flow (Complete Sequence)
· Part 3: Geospatial Indexing — Finding Nearby Drivers
∘ 3.1 The Proximity Search Problem
∘ 3.2 Geohash: Encoding Location as Strings
∘ 3.3 Quadtree: Adaptive Spatial Partitioning
∘ 3.4 S2 Geometry: Google's Approach
∘ 3.5 H3: Uber's Hexagonal Grid (Deep Dive)
∘ 3.6 Redis Geospatial Implementation
· Part 4: Driver-Rider Matching — The Heart of Uber
∘ 4.1 The Matching Problem
∘ 4.2 Greedy vs Optimal Matching
∘ 4.3 Batched Matching Algorithm
∘ 4.4 Handling Race Conditions (Multiple Drivers)
∘ 4.5 Distributed Locking Deep Dive
∘ 4.6 Complete Matching Sequence
· Part 5: ETA Prediction — Accuracy Matters
∘ 5.1 Why ETA is Hard
∘ 5.2 Road Network Graph
∘ 5.3 Routing Algorithms (Dijkstra, A*, Contraction Hierarchies)
∘ 5.4 Machine Learning for ETA
∘ 5.5 Real-Time Traffic Integration
· Part 6: Surge Pricing — Balancing Supply and Demand
∘ 6.1 The Economics of Surge
∘ 6.2 Demand-Supply Calculation
∘ 6.3 Zone-Based Pricing with H3
∘ 6.4 Surge Smoothing and Caps
· Part 7: Ride State Machine — Managing Ride Lifecycle
∘ 7.1 State Transitions
∘ 7.2 Concurrent State Modifications
∘ 7.3 Saga Pattern for Distributed Transactions
· Part 8: Payment Processing — Reliability at Scale
∘ 8.1 Two-Phase Payment (Authorize + Capture)
∘ 8.2 Idempotency Implementation
∘ 8.3 Handling Payment Failures
· Part 9: Ride Sharing (UberPool) — Optimization at Scale
∘ 9.1 The Pooling Problem (TSP Variant)
∘ 9.2 Matching Multiple Riders
∘ 9.3 Dynamic Re-Routing
∘ 9.4 Fair Pricing
· Part 10: Database Architecture — Choosing the Right Storage
∘ 10.1 PostgreSQL for Transactional Data
∘ 10.2 Redis for Real-Time Data
∘ 10.3 Cassandra for Time-Series Data
∘ 10.4 Kafka for Event Streaming
· Part 11: Failure Handling — When Things Go Wrong
∘ 11.1 Driver Goes Offline Mid-Ride
∘ 11.2 Payment Gateway Timeout
∘ 11.3 GPS Accuracy Issues
∘ 11.4 Data Center Failure
· Part 12: Complete System Architecture
∘ 12.1 High-Level Architecture
∘ 12.2 End-to-End Ride Flow
∘ 12.3 Service Responsibilities
· Part 13: Scaling to Millions
∘ 13.1 Horizontal Scaling Strategy
∘ 13.2 Geographic Sharding
∘ 13.3 Handling Traffic Spikes
· Part 14: Trade-offs and Design Decisions
∘ 14.1 Critical Trade-offs
∘ 14.2 What We Learned
· Final Architecture Summary
· Part 15: Theoretical Foundations
∘ 15.1 CAP Theorem
∘ 15.2 ACID vs BASE
∘ 15.3 Consistency Models
∘ 15.4 Database Scaling Concepts
∘ 15.5 Caching Patterns
∘ 15.6 Load Balancing
∘ 15.7 Rate Limiting
∘ 15.8 Message Queue Semantics
∘ 15.9 Microservices Patterns
∘ 15.10 API Design

## A REAL-WORLD PROBLEM

Imagine you're standing on a busy street corner in San Francisco. It's raining,
you're late for a meeting, and you need a ride. You open the Uber app, tap a
button, and within seconds, you see a car icon moving toward you on the map.
Three minutes later, you're in the car heading to your destination.

This seemingly simple experience hides one of the most complex distributed
systems ever built. Behind that single button tap:

- Your phone's GPS coordinates are sent to Uber's servers
- The system searches through thousands of nearby drivers in milliseconds
- It calculates the optimal match considering ETA, driver rating, and vehicle type
- It handles the race condition of multiple riders requesting nearby drivers
- It tracks the driver's location in real-time, updating your screen every second
- It calculates a fare estimate using ML models trained on millions of trips
- It processes your payment securely and reliably

All of this happens in under 5 seconds, and the system handles 20 million
rides per day globally.

In this deep dive, we'll build Uber from scratch. Not a toy version, but the
real system with all its complexity — the distributed locking, the geospatial
indexing, the failure handling, and the trade-offs that make it work at scale.

## PART 1: REQUIREMENTS & CORE CHALLENGES

Before writing a single line of code, we need to understand what we're building.

### 1.1 FUNCTIONAL REQUIREMENTS

For Riders:
- Request a ride from current location to a destination
- See nearby available drivers on a map
- Get an ETA and fare estimate before confirming
- Track the driver's location in real-time after matching
- Pay through the app (card, wallet, cash in some regions)
- Rate the driver after the ride

For Drivers:
- Go online/offline to accept rides
- Send location updates continuously while online
- Receive ride requests with pickup/dropoff details
- Accept or reject ride requests within a time window
- Navigate to pickup and dropoff locations
- Mark ride as started and completed
- See earnings and ride history

For the System:
- Match riders with the nearest available drivers
- Calculate accurate ETAs based on traffic and road conditions
- Implement surge pricing during high-demand periods
- Handle multiple ride types (UberX, UberXL, UberBlack, Pool)
- Support ride scheduling for future trips
- Handle ride cancellations with appropriate penalties

### 1.2 NON-FUNCTIONAL REQUIREMENTS

Availability: 99.99% uptime
The system cannot go down. Users depend on Uber for transportation, sometimes
in emergencies. 99.99% means less than 53 minutes of downtime per year.

Latency: Sub-second matching
When a rider requests a ride, they expect to see a driver match within
seconds. Anything longer feels broken. Our target:
- Nearby driver search: < 100ms
- Driver matching: < 1 second
- Location updates: < 50ms write latency

Scalability: Handle traffic spikes gracefully
New Year's Eve can have 10x normal traffic. A concert letting out can create
50,000 requests from one location. The system must handle these spikes without
degradation.

Consistency: Strong where it matters
- Location data: Eventual consistency is fine (few seconds stale is acceptable)
- Ride state: Strong consistency required (can't double-book a driver)
- Payments: Exactly-once semantics (no duplicate charges)

### 1.3 SCALE ESTIMATION

Let's work through the numbers to understand what we're dealing with:

**USERS AND DRIVERS:**
- Daily Active Riders: 100 million
- Active Drivers: 5 million
- Rides per day: 20 million

**LOCATION UPDATES:**
Each driver sends a location update every 4 seconds while online.
- 5 million drivers × 1 update/4 seconds = 1.25 million updates/second
- Each update: ~200 bytes (driver_id, lat, lng, timestamp, heading, speed)
- Write throughput: 1.25M × 200 bytes = 250 MB/second

This is our first major challenge. Traditional databases cannot handle 1.25
million writes per second with low latency.

**RIDE REQUESTS:**
- 20 million rides per day = ~230 rides/second average
- Peak (rush hour): 5x average = 1,150 rides/second
- Event spike: 50,000 simultaneous requests from one location

**READ QUERIES:**
For each ride request, we need to:
- Find nearby drivers (geospatial query)
- Fetch driver details (ratings, vehicle info)
- Calculate ETA for each candidate driver
- Check driver availability

This multiplies our read load by 10-20x per ride request.

**STORAGE:**
- Trip data: 20M trips/day × 5 KB = 100 GB/day = 36 TB/year
- Location history: 1.25M updates/sec × 200 bytes × 86400 sec = 21 TB/day
- Total: ~50+ TB/year (with compression and TTL)

### 1.4 MAIN CHALLENGES

Based on our requirements and scale, we can identify the core technical
challenges we need to solve:

CHALLENGE 1: Real-Time Location Tracking
How do we handle 1.25 million location updates per second? Traditional
REST APIs won't work — the overhead of establishing HTTP connections and
sending headers would consume more bandwidth than the data itself.

CHALLENGE 2: Geospatial Queries at Scale
When a rider requests a ride, we need to find drivers within a certain
radius — fast. Scanning 5 million driver locations for each request is not
feasible. We need specialized geospatial indexing.

CHALLENGE 3: Race Conditions in Matching
When a rider requests a ride, we send the request to the best driver. But
what if two riders request simultaneously and both get matched to the same
driver? We need distributed locking without sacrificing performance.

CHALLENGE 4: Accurate ETA Prediction
Users expect accurate ETAs. But predicting travel time is hard — it depends
on traffic, road conditions, time of day, weather, and countless other
factors. We need ML-based predictions updated in real-time.

CHALLENGE 5: Consistency vs. Availability
Location data can be eventually consistent, but ride assignments cannot.
A driver cannot accept two rides simultaneously. We need to carefully
design for the right consistency level for each component.

CHALLENGE 6: Failure Handling
What happens when a driver's phone loses connectivity mid-ride? When a
payment fails? When an entire data center goes down? The system must
gracefully handle failures without losing data or leaving users stranded.

Let's tackle each of these challenges systematically.

## PART 1B: DATA MODEL & API CONTRACTS

Before diving into architecture, let's define our data model and APIs.
This establishes the contract between components.

### 1.5 DATABASE SCHEMA

**CORE ENTITIES:**

```
+-------------------------------------------------------------------------+
|                           USERS TABLE                                   |
|                     (PostgreSQL - ACID required)                        |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |  Column           |  Type           |  Notes                    |   |
|  +-------------------+-----------------+---------------------------+   |
|  |  id               |  UUID (PK)      |  Unique user identifier   |   |
|  |  email            |  VARCHAR(255)   |  Unique, indexed          |   |
|  |  phone            |  VARCHAR(20)    |  Unique, indexed          |   |
|  |  name             |  VARCHAR(100)   |                           |   |
|  |  password_hash    |  VARCHAR(255)   |  bcrypt hashed            |   |
|  |  user_type        |  ENUM           |  'RIDER', 'DRIVER'        |   |
|  |  status           |  ENUM           |  'ACTIVE','SUSPENDED'     |   |
|  |  rating           |  DECIMAL(3,2)   |  4.85 (average rating)    |   |
|  |  created_at       |  TIMESTAMP      |                           |   |
|  |  updated_at       |  TIMESTAMP      |                           |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  Indexes:                                                              |
|  * PRIMARY KEY (id)                                                    |
|  * UNIQUE INDEX (email)                                                |
|  * UNIQUE INDEX (phone)                                                |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                         DRIVERS TABLE                                   |
|                    (PostgreSQL - extends Users)                         |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |  Column              |  Type           |  Notes                 |   |
|  +----------------------+-----------------+------------------------+   |
|  |  id                  |  UUID (PK, FK)  |  References users.id   |   |
|  |  license_number      |  VARCHAR(50)    |  Driving license       |   |
|  |  license_expiry      |  DATE           |                        |   |
|  |  vehicle_id          |  UUID (FK)      |  Current vehicle       |   |
|  |  is_online           |  BOOLEAN        |  Currently accepting   |   |
|  |  current_location    |  POINT          |  Last known (lat,lng)  |   |
|  |  location_updated_at |  TIMESTAMP      |  When last updated     |   |
|  |  acceptance_rate     |  DECIMAL(5,2)   |  % of accepted rides   |   |
|  |  total_trips         |  INTEGER        |  Lifetime trips        |   |
|  |  earnings_balance    |  DECIMAL(10,2)  |  Pending payout        |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  Indexes:                                                              |
|  * PRIMARY KEY (id)                                                    |
|  * INDEX (is_online) — for finding available drivers                  |
|  * SPATIAL INDEX (current_location) — for proximity queries           |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                         VEHICLES TABLE                                  |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |  Column           |  Type           |  Notes                    |   |
|  +-------------------+-----------------+---------------------------+   |
|  |  id               |  UUID (PK)      |                           |   |
|  |  driver_id        |  UUID (FK)      |  Owner                    |   |
|  |  make             |  VARCHAR(50)    |  Toyota, Honda            |   |
|  |  model            |  VARCHAR(50)    |  Camry, Civic             |   |
|  |  year             |  INTEGER        |  2022                     |   |
|  |  color            |  VARCHAR(30)    |  Black, White             |   |
|  |  license_plate    |  VARCHAR(20)    |  Unique                   |   |
|  |  vehicle_type     |  ENUM           |  'UBERX','XL','BLACK'     |   |
|  |  capacity         |  INTEGER        |  Number of seats          |   |
|  |  is_active        |  BOOLEAN        |  Approved for trips       |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                          RIDES TABLE                                    |
|            (PostgreSQL - ACID critical for ride state)                  |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |  Column              |  Type           |  Notes                 |   |
|  +----------------------+-----------------+------------------------+   |
|  |  id                  |  UUID (PK)      |  Ride identifier       |   |
|  |  rider_id            |  UUID (FK)      |  Who requested         |   |
|  |  driver_id           |  UUID (FK)      |  Assigned driver       |   |
|  |  vehicle_type        |  ENUM           |  Requested type        |   |
|  |  status              |  ENUM           |  See state machine     |   |
|  |                      |                 |                        |   |
|  |  pickup_location     |  POINT          |  (lat, lng)            |   |
|  |  pickup_address      |  VARCHAR(255)   |  Human readable        |   |
|  |  dropoff_location    |  POINT          |  (lat, lng)            |   |
|  |  dropoff_address     |  VARCHAR(255)   |  Human readable        |   |
|  |                      |                 |                        |   |
|  |  estimated_fare      |  DECIMAL(10,2)  |  Upfront estimate      |   |
|  |  actual_fare         |  DECIMAL(10,2)  |  Final charge          |   |
|  |  surge_multiplier    |  DECIMAL(3,2)   |  1.0, 1.5, 2.0         |   |
|  |                      |                 |                        |   |
|  |  estimated_eta       |  INTEGER        |  Minutes to pickup     |   |
|  |  estimated_duration  |  INTEGER        |  Minutes for trip      |   |
|  |  actual_duration     |  INTEGER        |  Actual minutes        |   |
|  |  distance_km         |  DECIMAL(8,2)   |  Trip distance         |   |
|  |                      |                 |                        |   |
|  |  requested_at        |  TIMESTAMP      |  When ride requested   |   |
|  |  accepted_at         |  TIMESTAMP      |  Driver accepted       |   |
|  |  arrived_at          |  TIMESTAMP      |  Driver at pickup      |   |
|  |  started_at          |  TIMESTAMP      |  Trip started          |   |
|  |  completed_at        |  TIMESTAMP      |  Trip ended            |   |
|  |  cancelled_at        |  TIMESTAMP      |  If cancelled          |   |
|  |  cancelled_by        |  ENUM           |  'RIDER','DRIVER'      |   |
|  |                      |                 |                        |   |
|  |  fence_token         |  BIGINT         |  For distributed lock  |   |
|  |  version             |  INTEGER        |  Optimistic locking    |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  Status ENUM values:                                                   |
|  'REQUESTED', 'MATCHING', 'ACCEPTED', 'EN_ROUTE', 'ARRIVED',          |
|  'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'NO_DRIVER'                 |
|                                                                         |
|  Indexes:                                                              |
|  * PRIMARY KEY (id)                                                    |
|  * INDEX (rider_id, status) — rider's active/past rides               |
|  * INDEX (driver_id, status) — driver's active/past rides             |
|  * INDEX (status, requested_at) — for matching queue                  |
|  * SPATIAL INDEX (pickup_location) — for surge calculation            |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                        PAYMENTS TABLE                                   |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |  Column              |  Type           |  Notes                 |   |
|  +----------------------+-----------------+------------------------+   |
|  |  id                  |  UUID (PK)      |                        |   |
|  |  ride_id             |  UUID (FK)      |  Which ride            |   |
|  |  rider_id            |  UUID (FK)      |  Who paid              |   |
|  |  amount              |  DECIMAL(10,2)  |  Charge amount         |   |
|  |  currency            |  CHAR(3)        |  'USD', 'EUR'          |   |
|  |  payment_method_id   |  UUID (FK)      |  Card/wallet used      |   |
|  |  status              |  ENUM           |  'AUTHORIZED',         |   |
|  |                      |                 |  'CAPTURED','FAILED'   |   |
|  |  gateway_txn_id      |  VARCHAR(100)   |  Stripe/Braintree ID   |   |
|  |  idempotency_key     |  VARCHAR(255)   |  UNIQUE - prevents dup |   |
|  |  authorized_at       |  TIMESTAMP      |                        |   |
|  |  captured_at         |  TIMESTAMP      |                        |   |
|  |  failure_reason      |  VARCHAR(255)   |  If failed             |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  Indexes:                                                              |
|  * PRIMARY KEY (id)                                                    |
|  * UNIQUE INDEX (idempotency_key) — prevents double charge            |
|  * INDEX (ride_id)                                                     |
|  * INDEX (rider_id, status)                                           |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    DRIVER_LOCATIONS TABLE                               |
|              (Cassandra - High write throughput, TTL)                   |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |  Column           |  Type           |  Notes                    |   |
|  +-------------------+-----------------+---------------------------+   |
|  |  driver_id        |  UUID           |  Partition key            |   |
|  |  timestamp        |  TIMESTAMP      |  Clustering key (DESC)    |   |
|  |  lat              |  DOUBLE         |  Latitude                 |   |
|  |  lng              |  DOUBLE         |  Longitude                |   |
|  |  heading          |  DOUBLE         |  Direction (0-360)        |   |
|  |  speed            |  DOUBLE         |  km/h                     |   |
|  |  accuracy         |  DOUBLE         |  GPS accuracy meters      |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  PRIMARY KEY: (driver_id, timestamp)                                   |
|  * Partition by driver_id — all history for one driver together       |
|  * Cluster by timestamp DESC — recent locations first                 |
|  * TTL: 30 days — auto-delete old location data                       |
|                                                                         |
|  Query pattern:                                                        |
|  SELECT * FROM driver_locations                                        |
|  WHERE driver_id = ? AND timestamp > ?                                 |
|  ORDER BY timestamp DESC LIMIT 100;                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

**REDIS DATA STRUCTURES:**

```
+-------------------------------------------------------------------------+
|                    REDIS REAL-TIME DATA                                 |
|                                                                         |
|  1. DRIVER LOCATIONS (Geospatial)                                      |
|  -----------------------------------                                   |
|  Key: drivers:{city}                                                   |
|  Type: Sorted Set with Geospatial indexing                            |
|  Example: drivers:sf, drivers:nyc                                      |
|                                                                         |
|  GEOADD drivers:sf -122.4194 37.7749 "driver_abc"                     |
|  GEORADIUS drivers:sf -122.4 37.78 5 km WITHDIST COUNT 20             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  2. DRIVER STATUS                                                      |
|  -------------------                                                   |
|  Key: driver:status:{driver_id}                                        |
|  Type: Hash                                                            |
|  Fields: is_online, current_ride_id, last_seen                        |
|                                                                         |
|  HSET driver:status:abc is_online true current_ride_id null           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  3. CONNECTION REGISTRY                                                |
|  -------------------------                                             |
|  Key: connections:drivers                                              |
|  Type: Hash                                                            |
|  Field: driver_id > gateway_hostname                                  |
|                                                                         |
|  HSET connections:drivers driver_abc gateway-1.uber.internal          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  4. ACTIVE RIDES                                                       |
|  ------------------                                                    |
|  Key: rider_active_ride:{rider_id} > ride_id                          |
|  Key: driver_active_ride:{driver_id} > ride_id                        |
|  Type: String with TTL                                                 |
|                                                                         |
|  SET rider_active_ride:rider123 ride456 EX 7200  (2 hour TTL)         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  5. SURGE CACHE                                                        |
|  -----------------                                                     |
|  Key: surge:{h3_zone_id}                                              |
|  Type: String (float)                                                  |
|  TTL: 2 minutes                                                        |
|                                                                         |
|  SET surge:89283082837ffff "1.5" EX 120                               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  6. DISTRIBUTED LOCKS                                                  |
|  -----------------------                                               |
|  Key: lock:ride:{ride_id}                                             |
|  Key: lock:driver:{driver_id}                                         |
|  Type: String (lock token)                                            |
|  TTL: 30 seconds                                                       |
|                                                                         |
|  SET lock:ride:123 "token_abc" NX EX 30                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 1.6 API CONTRACTS

RIDER APP APIs (REST over HTTPS):

```
+-------------------------------------------------------------------------+
|                      RIDER API ENDPOINTS                                |
|                                                                         |
|  ===================================================================   |
|  REQUEST A RIDE                                                        |
|  ===================================================================   |
|                                                                         |
|  POST /api/v1/rides                                                    |
|                                                                         |
|  Request:                                                              |
|  {                                                                     |
|    "pickup": {                                                         |
|      "lat": 37.7749,                                                   |
|      "lng": -122.4194,                                                 |
|      "address": "123 Market St, San Francisco"                        |
|    },                                                                  |
|    "dropoff": {                                                        |
|      "lat": 37.7849,                                                   |
|      "lng": -122.4094,                                                 |
|      "address": "456 Mission St, San Francisco"                       |
|    },                                                                  |
|    "vehicle_type": "UBERX",                                           |
|    "payment_method_id": "pm_abc123"                                   |
|  }                                                                     |
|                                                                         |
|  Response (201 Created):                                               |
|  {                                                                     |
|    "ride_id": "ride_xyz789",                                          |
|    "status": "MATCHING",                                              |
|    "estimated_fare": {                                                |
|      "min": 12.50,                                                    |
|      "max": 15.00,                                                    |
|      "currency": "USD"                                                |
|    },                                                                  |
|    "surge_multiplier": 1.0,                                           |
|    "estimated_pickup_time": 4                                         |
|  }                                                                     |
|                                                                         |
|  ===================================================================   |
|  GET RIDE STATUS                                                       |
|  ===================================================================   |
|                                                                         |
|  GET /api/v1/rides/{ride_id}                                          |
|                                                                         |
|  Response:                                                             |
|  {                                                                     |
|    "ride_id": "ride_xyz789",                                          |
|    "status": "EN_ROUTE",                                              |
|    "driver": {                                                        |
|      "id": "driver_abc",                                              |
|      "name": "John",                                                  |
|      "rating": 4.92,                                                  |
|      "photo_url": "https://...",                                      |
|      "phone": "+1234567890",                                          |
|      "vehicle": {                                                     |
|        "make": "Toyota",                                              |
|        "model": "Camry",                                              |
|        "color": "Black",                                              |
|        "license_plate": "ABC123"                                      |
|      },                                                               |
|      "current_location": {                                            |
|        "lat": 37.7760,                                                |
|        "lng": -122.4180                                               |
|      }                                                                |
|    },                                                                  |
|    "eta_minutes": 3,                                                  |
|    "pickup": { ... },                                                 |
|    "dropoff": { ... }                                                 |
|  }                                                                     |
|                                                                         |
|  ===================================================================   |
|  CANCEL RIDE                                                           |
|  ===================================================================   |
|                                                                         |
|  POST /api/v1/rides/{ride_id}/cancel                                  |
|                                                                         |
|  Request:                                                              |
|  {                                                                     |
|    "reason": "CHANGED_PLANS"                                          |
|  }                                                                     |
|                                                                         |
|  Response:                                                             |
|  {                                                                     |
|    "status": "CANCELLED",                                             |
|    "cancellation_fee": 5.00    // If applicable                       |
|  }                                                                     |
|                                                                         |
|  ===================================================================   |
|  GET FARE ESTIMATE                                                     |
|  ===================================================================   |
|                                                                         |
|  GET /api/v1/fare-estimate?                                           |
|      pickup_lat=37.7749&pickup_lng=-122.4194&                         |
|      dropoff_lat=37.7849&dropoff_lng=-122.4094&                       |
|      vehicle_type=UBERX                                               |
|                                                                         |
|  Response:                                                             |
|  {                                                                     |
|    "estimates": [                                                     |
|      {                                                                |
|        "vehicle_type": "UBERX",                                       |
|        "fare_min": 12.50,                                             |
|        "fare_max": 15.00,                                             |
|        "surge_multiplier": 1.0,                                       |
|        "eta_minutes": 4,                                              |
|        "duration_minutes": 12                                         |
|      },                                                               |
|      {                                                                |
|        "vehicle_type": "UBERXL",                                      |
|        "fare_min": 18.00,                                             |
|        "fare_max": 22.00,                                             |
|        ...                                                            |
|      }                                                                |
|    ],                                                                  |
|    "surge_zones": [...]                                               |
|  }                                                                     |
|                                                                         |
|  ===================================================================   |
|  RATE DRIVER                                                           |
|  ===================================================================   |
|                                                                         |
|  POST /api/v1/rides/{ride_id}/rating                                  |
|                                                                         |
|  Request:                                                              |
|  {                                                                     |
|    "rating": 5,                                                       |
|    "tip_amount": 3.00,                                                |
|    "feedback": "Great driver!"                                        |
|  }                                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

DRIVER APP APIs:

```
+-------------------------------------------------------------------------+
|                      DRIVER API ENDPOINTS                               |
|                                                                         |
|  ===================================================================   |
|  GO ONLINE / OFFLINE                                                   |
|  ===================================================================   |
|                                                                         |
|  PUT /api/v1/driver/status                                            |
|                                                                         |
|  Request:                                                              |
|  {                                                                     |
|    "is_online": true,                                                 |
|    "vehicle_id": "vehicle_123",                                       |
|    "location": {                                                      |
|      "lat": 37.7749,                                                  |
|      "lng": -122.4194                                                 |
|    }                                                                   |
|  }                                                                     |
|                                                                         |
|  Response:                                                             |
|  {                                                                     |
|    "status": "ONLINE",                                                |
|    "websocket_url": "wss://location.uber.com/driver",                 |
|    "token": "ws_token_xyz"                                            |
|  }                                                                     |
|                                                                         |
|  ===================================================================   |
|  ACCEPT / REJECT RIDE                                                  |
|  ===================================================================   |
|                                                                         |
|  POST /api/v1/driver/rides/{ride_id}/accept                           |
|                                                                         |
|  Response:                                                             |
|  {                                                                     |
|    "ride_id": "ride_xyz",                                             |
|    "status": "ACCEPTED",                                              |
|    "pickup": {                                                        |
|      "lat": 37.7749,                                                  |
|      "lng": -122.4194,                                                |
|      "address": "123 Market St"                                       |
|    },                                                                  |
|    "rider": {                                                         |
|      "name": "Alice",                                                 |
|      "rating": 4.85                                                   |
|    },                                                                  |
|    "navigation_url": "uber://navigate?..."                            |
|  }                                                                     |
|                                                                         |
|  POST /api/v1/driver/rides/{ride_id}/reject                           |
|  (No response body needed, 204 No Content)                            |
|                                                                         |
|  ===================================================================   |
|  UPDATE RIDE STATUS                                                    |
|  ===================================================================   |
|                                                                         |
|  POST /api/v1/driver/rides/{ride_id}/arrived                          |
|  POST /api/v1/driver/rides/{ride_id}/start                            |
|  POST /api/v1/driver/rides/{ride_id}/complete                         |
|                                                                         |
|  Response for /complete:                                               |
|  {                                                                     |
|    "ride_id": "ride_xyz",                                             |
|    "status": "COMPLETED",                                             |
|    "fare": 15.50,                                                     |
|    "distance_km": 5.2,                                                |
|    "duration_minutes": 18,                                            |
|    "driver_earnings": 12.40                                           |
|  }                                                                     |
|                                                                         |
|  ===================================================================   |
|  GET EARNINGS                                                          |
|  ===================================================================   |
|                                                                         |
|  GET /api/v1/driver/earnings?period=weekly                            |
|                                                                         |
|  Response:                                                             |
|  {                                                                     |
|    "period": "2024-01-08 to 2024-01-14",                              |
|    "total_earnings": 850.00,                                          |
|    "total_trips": 45,                                                 |
|    "total_hours_online": 32.5,                                        |
|    "tips": 65.00,                                                     |
|    "daily_breakdown": [...]                                           |
|  }                                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 1.7 WEBSOCKET MESSAGE FORMATS

DRIVER > SERVER (Location Updates):

```
+-------------------------------------------------------------------------+
|                    DRIVER LOCATION MESSAGE                              |
|                                                                         |
|  Sent every 4 seconds while driver is online                           |
|                                                                         |
|  {                                                                     |
|    "type": "LOCATION_UPDATE",                                         |
|    "payload": {                                                       |
|      "lat": 37.7749,                                                  |
|      "lng": -122.4194,                                                |
|      "heading": 45.0,         // Degrees from north                   |
|      "speed": 35.5,           // km/h                                 |
|      "accuracy": 5.0,         // GPS accuracy in meters               |
|      "timestamp": 1699500000  // Unix timestamp                       |
|    }                                                                   |
|  }                                                                     |
|                                                                         |
|  Binary-optimized format (production):                                 |
|  [type:1byte][lat:8bytes][lng:8bytes][heading:4bytes]                 |
|  [speed:4bytes][accuracy:4bytes][timestamp:8bytes]                    |
|  Total: 37 bytes vs ~200 bytes JSON                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

SERVER > DRIVER (Ride Request):

```
+-------------------------------------------------------------------------+
|                    RIDE REQUEST MESSAGE                                 |
|                                                                         |
|  Sent when driver is matched to a ride                                 |
|                                                                         |
|  {                                                                     |
|    "type": "RIDE_REQUEST",                                            |
|    "payload": {                                                       |
|      "ride_id": "ride_xyz789",                                        |
|      "pickup": {                                                      |
|        "lat": 37.7749,                                                |
|        "lng": -122.4194,                                              |
|        "address": "123 Market St"                                     |
|      },                                                               |
|      "dropoff": {                                                     |
|        "lat": 37.7849,                                                |
|        "lng": -122.4094,                                              |
|        "address": "456 Mission St"                                    |
|      },                                                               |
|      "rider": {                                                       |
|        "name": "Alice",                                               |
|        "rating": 4.85                                                 |
|      },                                                               |
|      "vehicle_type": "UBERX",                                         |
|      "estimated_fare": 15.00,                                         |
|      "surge_multiplier": 1.5,                                         |
|      "accept_timeout_seconds": 15                                     |
|    }                                                                   |
|  }                                                                     |
|                                                                         |
|  Driver must respond within accept_timeout_seconds or                  |
|  request is sent to next driver.                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

SERVER > RIDER (Driver Location Updates):

```
+-------------------------------------------------------------------------+
|                    DRIVER LOCATION TO RIDER                             |
|                                                                         |
|  Pushed via WebSocket or Pub/Sub when rider is tracking driver         |
|                                                                         |
|  {                                                                     |
|    "type": "DRIVER_LOCATION",                                         |
|    "payload": {                                                       |
|      "ride_id": "ride_xyz789",                                        |
|      "driver_location": {                                             |
|        "lat": 37.7760,                                                |
|        "lng": -122.4180,                                              |
|        "heading": 90.0                                                |
|      },                                                               |
|      "eta_minutes": 3,                                                |
|      "timestamp": 1699500000                                          |
|    }                                                                   |
|  }                                                                     |
|                                                                         |
|  Sent every 4 seconds while driver is en route to pickup              |
|  or during the ride.                                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

**RIDE STATUS UPDATES:**

```
+-------------------------------------------------------------------------+
|                    RIDE STATUS MESSAGE                                  |
|                                                                         |
|  Sent to both rider and driver when ride status changes                |
|                                                                         |
|  {                                                                     |
|    "type": "RIDE_STATUS_UPDATE",                                      |
|    "payload": {                                                       |
|      "ride_id": "ride_xyz789",                                        |
|      "status": "ARRIVED",                                             |
|      "previous_status": "EN_ROUTE",                                   |
|      "timestamp": 1699500000,                                         |
|      "metadata": {                                                    |
|        "wait_timer_started": true,                                    |
|        "wait_timer_minutes": 5                                        |
|      }                                                                |
|    }                                                                   |
|  }                                                                     |
|                                                                         |
|  Status values:                                                        |
|  MATCHING > ACCEPTED > EN_ROUTE > ARRIVED > IN_PROGRESS > COMPLETED   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 1.8 ERROR RESPONSE FORMAT

```
+-------------------------------------------------------------------------+
|                    STANDARD ERROR RESPONSE                              |
|                                                                         |
|  All APIs return errors in consistent format:                          |
|                                                                         |
|  {                                                                     |
|    "error": {                                                         |
|      "code": "DRIVER_NOT_AVAILABLE",                                  |
|      "message": "No drivers available in your area",                  |
|      "details": {                                                     |
|        "retry_after_seconds": 30,                                     |
|        "surge_multiplier": 2.5                                        |
|      }                                                                |
|    }                                                                   |
|  }                                                                     |
|                                                                         |
|  Common error codes:                                                   |
|  * INVALID_REQUEST       - Missing or invalid parameters              |
|  * UNAUTHORIZED          - Invalid or expired token                   |
|  * PAYMENT_FAILED        - Card declined                              |
|  * DRIVER_NOT_AVAILABLE  - No drivers in area                        |
|  * RIDE_ALREADY_ACCEPTED - Race condition, driver took another ride  |
|  * RIDE_CANCELLED        - Ride was cancelled                        |
|  * RATE_LIMITED          - Too many requests                         |
|                                                                         |
|  HTTP Status Codes:                                                    |
|  * 400 - Bad Request (invalid input)                                  |
|  * 401 - Unauthorized                                                 |
|  * 403 - Forbidden (not allowed)                                      |
|  * 404 - Not Found                                                    |
|  * 409 - Conflict (race condition)                                    |
|  * 429 - Too Many Requests                                            |
|  * 500 - Internal Server Error                                        |
|  * 503 - Service Unavailable                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 2: CORE ARCHITECTURE — REAL-TIME LOCATION TRACKING

The foundation of Uber is knowing where drivers are in real-time. Without
accurate, up-to-date location data, nothing else works — we can't find nearby
drivers, can't show accurate ETAs, can't track rides on a map.

### 2.1 THE LOCATION UPDATE PROBLEM

A driver's phone has GPS that provides location coordinates. We need to:

1. Send these coordinates to our servers every few seconds
2. Store them for real-time queries (find nearby drivers)
3. Store them for historical analysis (route reconstruction, fraud detection)
4. Update the rider's map in real-time during a ride

The naive approach would be HTTP POST requests:

```
POST /api/v1/driver/location
{
    "driver_id": "abc123",
    "lat": 37.7749,
    "lng": -122.4194,
    "timestamp": 1699500000,
    "heading": 45,
    "speed": 35
}
```

Let's calculate the cost of this approach:

- HTTP headers: ~500 bytes per request (cookies, auth tokens, content-type)
- Payload: ~200 bytes
- Total: ~700 bytes per update
- 5 million drivers × 1 update/4 sec = 1.25M requests/second
- Bandwidth: 1.25M × 700 bytes = 875 MB/second just for overhead

This is wasteful. The actual data is 200 bytes, but we're sending 700 bytes
due to HTTP overhead. Worse, each request requires a new TCP connection
(or connection from a pool), adding latency.

### 2.2 WEBSOCKET VS HTTP POLLING: A CRITICAL DECISION

We have three options for real-time communication:

OPTION 1: HTTP POLLING
The client sends a request every N seconds. Simple, but:
- High overhead (headers, connection establishment)
- Delayed updates (if polling every 5 seconds, data is up to 5 seconds stale)
- Wasteful (most polls return "no new data")

OPTION 2: HTTP LONG POLLING
The server holds the connection open until there's new data. Better, but:
- Complex to implement at scale
- Connection timeouts cause reconnection overhead
- Server resources tied up for waiting connections

OPTION 3: WEBSOCKET
A persistent, bidirectional connection. The client and server can send
messages at any time without the overhead of HTTP headers.

For Uber, WebSocket is the clear winner:

```
+-------------------------------------------------------------------------+
|                          HTTP POLLING                                   |
|                                                                         |
|  Driver Phone                                    Server                 |
|      |                                             |                    |
|      |---- POST /location (700 bytes) ------------>|                    |
|      |<--- 200 OK ---------------------------------|                    |
|      |                    (4 seconds pass)         |                    |
|      |---- POST /location (700 bytes) ------------>|                    |
|      |<--- 200 OK ---------------------------------|                    |
|      |                    (repeat forever)         |                    |
|                                                                         |
|  Problem: 700 bytes × 1.25M/sec = 875 MB/sec bandwidth waste            |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                          WEBSOCKET                                      |
|                                                                         |
|  Driver Phone                                    Server                 |
|      |                                             |                    |
|      |---- WebSocket Handshake (once) ------------>|                    |
|      |<--- 101 Switching Protocols ----------------|                    |
|      |                                             |                    |
|      |<========== Persistent Connection ==========>|                    |
|      |                                             |                    |
|      |---- Location frame (206 bytes) ------------>|                    |
|      |                    (4 seconds pass)         |                    |
|      |---- Location frame (206 bytes) ------------>|                    |
|      |                                             |                    |
|      |<--- Ride request push (instant) ------------|                    |
|      |                                             |                    |
|  Benefit: 206 bytes × 1.25M/sec = 257 MB/sec (70% reduction)            |
|  Bonus: Server can push ride requests instantly                         |
+-------------------------------------------------------------------------+
```

WebSocket gives us:
- 70% bandwidth reduction (no HTTP headers per message)
- Bidirectional communication (server can push ride requests)
- Lower latency (no connection establishment per message)
- Better battery life on mobile devices

### 2.3 LOCATION GATEWAY ARCHITECTURE

With 5 million drivers online, we can't have all connections on one server.
A typical server can handle 50,000-100,000 concurrent WebSocket connections
with careful tuning. We need a fleet of "Location Gateway" servers.

```
+-------------------------------------------------------------------------+
|                    LOCATION GATEWAY ARCHITECTURE                        |
|                                                                         |
|                         +------------------+                            |
|                         |   L4 Load        |                            |
|       Driver Apps ----->|   Balancer       |                            |
|       (5M connections)  |   (NGINX/NLB)    |                            |
|                         +--------+---------+                            | 
|                                  |                                      |
|                    +-------------+-------------+                        |
|                    v             v             v                        |
|              +----------+  +----------+  +----------+                   |
|              | Gateway  |  | Gateway  |  | Gateway  |  ... (100+)       |
|              | Server 1 |  | Server 2 |  | Server 3 |                   |
|              | 50K conn |  | 50K conn |  | 50K conn |                   |
|              +----+-----+  +----+-----+  +----+-----+                   |
|                   |             |             |                         |
|                   +-------------+-------------+                         |
|                                 v                                       |
|                         +--------------+                                |
|                         |    Kafka     |                                |
|                         |  (location   |                                |
|                         |   events)    |                                |
|                         +------+-------+                                |
|                                |                                        |
|                    +-----------+-----------+                            |
|                    v           v           v                            |
|              +----------+ +---------+ +-----------+                     |
|              |  Redis   | |Location | | Cassandra |                     |
|              |(realtime)| | Service | | (history) |                     |
|              +----------+ +---------+ +-----------+                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

Key design decisions:

1. L4 LOAD BALANCER (not L7)

### CONCEPT: OSI MODEL LAYERS

The OSI model has 7 layers. Load balancers operate at different layers:

Layer 4 (Transport): Sees only TCP/UDP packets - IP addresses and ports.
Makes routing decisions based on IP hash. Doesn't understand HTTP.

Layer 7 (Application): Parses HTTP headers, cookies, URLs. Can route
based on /api/v1 vs /api/v2. More features but more overhead.

For WebSocket:
- Initial handshake is HTTP (needs L7 briefly)
- After upgrade, it's just TCP frames (L4 is sufficient)
- L7 parsing every frame wastes CPU cycles

We use L4 (AWS NLB / HAProxy TCP mode) for WebSocket traffic.

2. STICKY SESSIONS (Session Affinity)

### CONCEPT: CONSISTENT HASHING

When a driver connects, we need them to always reach the same gateway.

Why? The gateway maintains the WebSocket connection in memory. If the
next request goes to a different gateway, that connection doesn't exist.

How: Hash the client IP to determine which server handles them.

hash(client_ip) % num_servers = server_index

Problem: When servers are added/removed, all hashes change!

Solution: CONSISTENT HASHING
- Arrange servers on a virtual ring (0 to 2^32)
- Hash each server to a position on the ring
- Hash client IP, walk clockwise to find nearest server
- When server is added/removed, only nearby clients move

```
+---------------------------------------------------------------------+
|                    CONSISTENT HASHING RING                          |
|                                                                     |
|                         Gateway-1                                   |
|                            ●                                        |
|                      /           \                                  |
|                    /               \                                |
|        Gateway-4 ●                   ● Gateway-2                    |
|                    \               /                                |
|                      \           /                                  |
|                            ●                                        |
|                         Gateway-3                                   |
|                                                                     |
|   Client IP hashes to a point, walks clockwise to find server      |
+---------------------------------------------------------------------+
```

3. KAFKA FOR DECOUPLING

### CONCEPT: PUBLISH-SUBSCRIBE & BACKPRESSURE

Without Kafka, if Cassandra is slow:
- Gateway blocks waiting for DB write
- WebSocket connection stalls
- Driver's app shows lag
- Bad user experience

With Kafka (async pub-sub):
- Gateway publishes to Kafka topic (fast, ~1ms)
- Returns ACK to driver immediately
- Separate consumer writes to Cassandra at its own pace

**BACKPRESSURE PRINCIPLE:**
When downstream is slow, the queue grows. We monitor queue depth:
- Normal: < 1000 messages
- Warning: 1000-10000 messages (scale consumers)
- Critical: > 10000 messages (drop low-priority data)

This prevents cascading failures where slow DB brings down the whole system.

### 2.4 CONNECTION REGISTRY PATTERN

Here's a critical problem: A rider is matched with a driver. We need to send
a ride request to that driver. But which Gateway server holds the driver's
WebSocket connection?

We solve this with a Connection Registry — a distributed map of
driver_id > gateway_server_id stored in Redis:

```
+-------------------------------------------------------------------------+
|                       CONNECTION REGISTRY                               |
|                                                                         |
|  Redis Hash: driver_connections                                         |
|  +-----------------------------------------------------------------+    |
|  |  driver_abc  >  gateway-1.uber.internal                         |    |
|  |  driver_def  >  gateway-3.uber.internal                         |    |
|  |  driver_ghi  >  gateway-1.uber.internal                         |    |
|  |  driver_jkl  >  gateway-2.uber.internal                         |    |
|  |  ...                                                            |    |
|  +-----------------------------------------------------------------+    |
|                                                                         |
|  When driver connects:                                                  |
|  HSET driver_connections driver_abc gateway-1.uber.internal             |
|                                                                         |
|  When driver disconnects:                                               |
|  HDEL driver_connections driver_abc                                     |
|                                                                         |
|  To find where driver is connected:                                     |
|  HGET driver_connections driver_abc                                     |
|  > "gateway-1.uber.internal"                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 2.5 LOCATION UPDATE FLOW (COMPLETE SEQUENCE)

Let's trace a complete location update from the driver's phone to storage:

```
+-------------------------------------------------------------------------+
|                  LOCATION UPDATE SEQUENCE                               |
|                                                                         |
|  Driver       Gateway      Redis         Kafka        Cassandra         |
|  Phone        Server       (realtime)    (stream)     (history)         |
|    |            |            |             |             |              |
|    |            |            |             |             |              |
|    |- Location ->|           |             |             |              |
|    |  frame      |           |             |             |              |
|    |  (206 B)    |           |             |             |              |
|    |            |            |             |             |              |
|    |            |-- GEOADD -->|            |             |              |
|    |            |  drivers:sf|             |             |              |
|    |            |  lng lat   |             |             |              |
|    |            |  driver_id |             |             |              |
|    |            |<-- OK -----|             |             |              |
|    |            |  (0.5ms)   |             |             |              |
|    |            |            |             |             |              |
|    |            |-- Produce -------------->|             |              |
|    |            |  location-events         |             |              |
|    |            |  (async, no wait)        |             |              |
|    |            |            |             |             |              |
|    |<-- ACK ----|            |             |             |              |
|    |  (15ms     |            |             |             |              |
|    |   total)   |            |             |             |              |
|    |            |            |             |             |              |
|    |            |            |             |-- Consume -->|             |
|    |            |            |             |  (batch)     |             |
|    |            |            |             |             |-- INSERT     |
|    |            |            |             |             |   (async)    |
|    |            |            |             |             |              |
|                                                                         |
|  Total latency for driver: ~15ms                                        |
|  Redis updated: ~0.5ms (sub-second freshness)                           |
|  Cassandra updated: ~100ms-1s (async, eventual)                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

Why this design?

1. REDIS FIRST (Synchronous)
We update Redis immediately because that's what real-time queries use.
The driver's location is queryable within 0.5ms of being received.

2. KAFKA FOR DURABILITY (Asynchronous)
We don't wait for Kafka acknowledgment before sending ACK to the driver.
If Kafka is slow, we don't want to delay the driver's app. The location
data is already in Redis for immediate use.

3. CASSANDRA VIA CONSUMER (Background)
A separate consumer process reads from Kafka and writes to Cassandra.
This decouples the hot path from historical storage. If Cassandra is
slow, it doesn't affect real-time performance.

### 2.6 CROSS-SERVER LOCATION STREAMING: HOW RIDER SEES DRIVER'S LOCATION

### THE PROBLEM

Once a ride is matched, the rider needs to see the driver's real-time location
on their map. But here's the challenge:

- Driver "John" is connected via WebSocket to Gateway Server A (NYC region)
- Rider "Alice" is connected via WebSocket to Gateway Server B (NYC region)
- How does Alice's phone get John's location updates in real-time?

The driver and rider are on DIFFERENT servers. The servers don't share memory.
We need a mechanism to route driver location updates to the correct rider.

```
+-------------------------------------------------------------------------+
|                      THE CROSS-SERVER PROBLEM                           |
|                                                                         |
|   Gateway Server A                        Gateway Server B              |
|   +---------------+                      +---------------+              |
|   |               |                      |               |              |
|   |  Driver John  |                      |  Rider Alice  |              |
|   |  WebSocket <--+---- Location ----?---+-- WebSocket   |              |
|   |  Connection   |    How does this     |  Connection   |              |
|   |               |    data flow?        |               |              |
|   +---------------+                      +---------------+              |
|                                                                         |
|   Server A has the driver's location.                                   |
|   Server B has the rider's connection.                                  |
|   How do we bridge them?                                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SOLUTION: PUBLISH-SUBSCRIBE WITH RIDE-BASED CHANNELS

The key insight: Once a ride is matched, we know which driver and rider are
paired. We can create a "channel" for each active ride and use Redis Pub/Sub
to broadcast location updates.

### PRINCIPLE: PUBLISH-SUBSCRIBE PATTERN

Pub/Sub decouples message producers from consumers:

- Publisher: Doesn't know/care who is listening
- Subscriber: Doesn't know/care who is publishing
- Broker (Redis): Routes messages from publishers to subscribers

This is perfect for our use case because:
1. Driver publishes location > doesn't care which server rider is on
2. Rider's server subscribes > automatically receives updates
3. Redis handles all the routing

**ARCHITECTURE:**

```
+-------------------------------------------------------------------------+
|                   REDIS PUB/SUB FOR RIDE TRACKING                       |
|                                                                         |
|                           Redis Cluster                                 |
|                      +-------------------+                              |
|                      |   Channel:        |                              |
|                      |   ride:r_12345    |                              |
|                      |                   |                              |
|          +--PUBLISH-->  {lat, lng, ts}  +--SUBSCRIBE-----+              |
|          |           |                   |               |              |
|          |           +-------------------+               |              |
|          |                                               v              |
|   +------+------+                               +-----------------+     |
|   | Gateway A   |                               |   Gateway B     |     |
|   |             |                               |                 |     |
|   | Driver John |                               |  Rider Alice    |     |
|   | WebSocket   |                               |  WebSocket      |     |
|   |             |                               |  <-- push loc   |     |
|   +-------------+                               +-----------------+     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMPLETE FLOW: DRIVER LOCATION > RIDER'S PHONE

Step-by-step sequence when driver moves:

```
+-------------------------------------------------------------------------+
|            LOCATION STREAMING TO RIDER (FULL SEQUENCE)                  |
|                                                                         |
|  Driver       Gateway A     Redis         Gateway B      Rider          |
|  Phone                      Cluster                      Phone          |
|    |              |           |              |             |            |
|    |              |           |              |             |            |
|    | -- GPS ------>           |              |             |            |
|    |  Location    |           |              |             |            |
|    |  Update      |           |              |             |            |
|    |              |           |              |             |            |
|    |              |-- GEOADD -->             |             |            |
|    |              |  (update hot location)   |             |            |
|    |              |<-- OK ----|              |             |            |
|    |              |           |              |             |            |
|    |              |-- PUBLISH -->            |             |            |
|    |              |  ride:r_12345            |             |            |
|    |              |  {lat, lng, heading,     |             |            |
|    |              |   speed, timestamp}      |             |            |
|    |              |           |              |             |            |
|    |              |           |-- Message -->|             |            |
|    |              |           |  (subscriber |             |            |
|    |              |           |   receives)  |             |            |
|    |              |           |              |             |            |
|    |              |           |              |-- WebSocket ->           |
|    |              |           |              |  Push location           |
|    |              |           |              |  to rider app            |
|    |              |           |              |             |            |
|    |              |           |              |             |-- Update   |
|    |              |           |              |             |   Map UI   |
|    |              |           |              |             |            |
|                                                                         |
|  Total latency: ~30-50ms from driver GPS to rider's map                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 2.7 THE FUNDAMENTAL PROBLEM: CROSS-SERVER WEBSOCKET COMMUNICATION

Before diving into solutions, let's understand the core problem deeply.

### THE CORE CHALLENGE

WebSocket is a STATEFUL protocol. Unlike HTTP where each request is independent,
a WebSocket connection maintains persistent state:

- The connection lives on ONE specific server
- Server memory holds the socket object, buffers, session data
- You cannot "move" a connection to another server
- If Server A has the connection, Server B cannot send data through it

This creates a fundamental routing problem:

```
+-------------------------------------------------------------------------+
|                    WHY THIS IS HARD                                     |
|                                                                         |
|   User A <--WebSocket--> Server 1     Server 2 <--WebSocket--> User B   |
|                                                                         |
|   User A wants to send message to User B.                               |
|                                                                         |
|   Problem:                                                              |
|   * Server 1 receives the message                                       |
|   * Server 1 has NO connection to User B                                |
|   * Server 2 has the connection, but doesn't know about the message     |
|                                                                         |
|   The servers don't share memory. They're isolated processes.           |
|   How do we bridge them?                                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

This is a DISTRIBUTED SYSTEMS problem, not a WebSocket problem.

### 2.8 ALL APPROACHES TO CROSS-SERVER COMMUNICATION

There are fundamentally 5 approaches to solve this. Each has different
trade-offs for latency, complexity, scalability, and reliability.

### APPROACH 1: STICKY SESSIONS (AVOID THE PROBLEM)

**CONCEPT:**
Force both driver and rider to connect to the SAME server, so no cross-server
communication is needed.

**HOW IT WORKS:**
```
1. When ride is matched, determine which server the driver is on
2. When rider needs to track, route them to that same server
3. Server has BOTH connections locally > simple in-memory message passing

+-------------------------------------------------------------------------+
|                      STICKY SESSIONS                                    |
|                                                                         |
|   Load Balancer (route by ride_id hash)                                 |
|            |                                                            |
|            v                                                            |
|   +-----------------+                                                   |
|   |    Server 1     |  < Both driver AND rider for ride_123             |
|   |                 |                                                   |
|   |  Driver --------|-> Local memory ----> Rider                        |
|   |  WebSocket      |     (no network)     WebSocket                    |
|   |                 |                                                   |
|   +-----------------+                                                   |
|                                                                         |
|   No cross-server communication needed!                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

**IMPLEMENTATION:**
- Load balancer uses "consistent hashing" on ride_id
- All requests for ride_123 go to same server
- Rider connects with ride_id > routed to driver's server

**PROS:**
+ Simplest architecture
+ Lowest latency (no network hop between servers)
+ No message broker needed
+ Easy to debug (everything on one machine)

**CONS:**
- SINGLE POINT OF FAILURE: If that server dies, both lose connection
- UNEVEN LOAD: Popular areas might overload one server
- SCALING LIMITS: Can't spread one ride across servers
- RECONNECTION PROBLEM: If rider reconnects, might go to different server

VERDICT: Good for small scale, problematic at Uber's scale.

### APPROACH 2: DIRECT SERVER-TO-SERVER COMMUNICATION

**CONCEPT:**
Server A directly calls Server B to deliver the message. Requires knowing
which server has the target connection.

**HOW IT WORKS:**
```
1. Maintain a "Connection Registry" — a distributed map of 
   {user_id > server_hostname}
2. When Server A needs to send to User B:
   a. Lookup: "Which server has User B?" > Server B
   b. Make RPC/HTTP call: Server A > Server B with message
   c. Server B finds local WebSocket > delivers message

+-------------------------------------------------------------------------+
|                 DIRECT SERVER-TO-SERVER                                 |
|                                                                         |
|              Connection Registry (Redis Hash)                           |
|              +------------------------------+                           |
|              |  rider_abc > gateway-2       |                           |
|              |  rider_def > gateway-1       |                           |
|              |  driver_xyz > gateway-1      |                           |
|              +------------------------------+                           |
|                          |                                              |
|                     +----+----+                                         |
|                     | Lookup  |                                         |
|                     +----+----+                                         |
|                          |                                              |
|   +-----------+    +-----v-----+    +-----------+                       |
|   | Gateway 1 |--->|   gRPC    |--->| Gateway 2 |                       |
|   |           |    |   Call    |    |           |                       |
|   | Driver    |    |           |    | Rider     |                       |
|   | sends loc |    |"send to   |    | receives  |                       |
|   |           |    | rider_abc"|    | location  |                       |
|   +-----------+    +-----------+    +-----------+                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

**CONNECTION REGISTRY PRINCIPLE:**
- Every gateway updates registry when user connects/disconnects
- CONNECT:  HSET connections rider_abc gateway-2.internal
- DISCONNECT: HDEL connections rider_abc
- TTL/Heartbeat prevents stale entries if server crashes

**PROS:**
+ Lower latency than message broker (direct call)
+ Simple mental model (point-to-point)
+ No additional infrastructure (if you have service discovery)

**CONS:**
- TIGHT COUPLING: Gateways must know about each other
- CONNECTION MANAGEMENT: Must maintain connection pools between servers
- FAILURE HANDLING: What if Server B is temporarily unreachable?
- SCALABILITY: N servers = N×N potential connections (mesh topology)
- REGISTRY STALENESS: User might have moved to different server

VERDICT: Works for moderate scale, gets complex with many servers.

### APPROACH 3: MESSAGE BROKER / PUB-SUB (RECOMMENDED FOR REAL-TIME)

**CONCEPT:**
Introduce a central message broker. Servers publish messages to the broker,
and subscribers receive them. Complete decoupling.

PRINCIPLE: PUBLISH-SUBSCRIBE PATTERN
```
- PUBLISHER: Sends message to a "channel" or "topic" — doesn't know/care 
  who receives it
- SUBSCRIBER: Listens to channels — doesn't know/care who publishes
- BROKER: Routes messages from publishers to all subscribers

+-------------------------------------------------------------------------+
|                    PUB/SUB ARCHITECTURE                                 |
|                                                                         |
|                    +-----------------+                                  |
|                    |  Message Broker |                                  |
|                    |  (Redis/Kafka)  |                                  |
|                    |                 |                                  |
|                    | Channel:        |                                  |
|                    | "ride:r_12345"  |                                  |
|                    |                 |                                  |
|        +-PUBLISH--->  [location]    -+--SUBSCRIBE--+                    |
|        |           |                 |             |                    |
|        |           +-----------------+             |                    |
|        |                                           v                    |
|   +----+------+                           +------------+                |
|   | Gateway A |                           | Gateway B  |                |
|   |           |  (No direct connection    |            |                |
|   | Driver    |   between gateways!)      | Rider      |                |
|   +-----------+                           +------------+                |
|                                                                         |
|   KEY INSIGHT: Gateway A doesn't know Gateway B exists.                 |
|                It just publishes. Broker handles routing.               |
|                                                                         |
+-------------------------------------------------------------------------+
```

**WHY PUB/SUB IS POWERFUL:**

1. DECOUPLING
Publishers and subscribers evolve independently. Add new gateways
without changing existing ones. Add new subscribers (e.g., analytics)
without touching publisher code.

2. FANOUT
One message can go to multiple subscribers. If rider is connected to
multiple devices, or if we add a monitoring system, all receive updates.

3. LOCATION TRANSPARENCY
Publisher doesn't need to know WHERE subscriber is. Broker handles it.
User can reconnect to different server — new server just subscribes.

4. FAILURE ISOLATION
If Gateway B is slow, Gateway A doesn't block. It publishes and moves on.

**CHANNEL DESIGN OPTIONS:**

```
+-------------------------------------------------------------------------+
|                    CHANNEL NAMING STRATEGIES                            |
|                                                                         |
|  Option A: Per-Ride Channel                                             |
|  -------------------------                                              |
|  Channel name: "ride:{ride_id}"                                         |
|  Example: "ride:r_12345"                                                |
|                                                                         |
|  * Driver's gateway PUBLISHES to "ride:r_12345"                         |
|  * Rider's gateway SUBSCRIBES to "ride:r_12345"                         |
|  * When ride ends, unsubscribe                                          |
|                                                                         |
|  Pros: Clean isolation, easy to reason about                            |
|  Cons: Many channels (one per active ride)                              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Option B: Per-User Channel                                             |
|  -------------------------                                              |
|  Channel name: "user:{user_id}"                                         |
|  Example: "user:rider_abc"                                              |
|                                                                         |
|  * Driver's gateway PUBLISHES to "user:rider_abc"                       |
|  * Rider's gateway SUBSCRIBES to "user:rider_abc" on connect            |
|  * Subscription persists across rides                                   |
|                                                                         |
|  Pros: Simpler subscription management                                  |
|  Cons: Must include ride_id in message for filtering                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Option C: Geographic Channel (for broadcast)                           |
|  -------------------------                                              |
|  Channel name: "zone:{geohash}"                                         |
|  Example: "zone:9q8yy"                                                  |
|                                                                         |
|  * Good for broadcasting surge pricing to all drivers in area           |
|  * Not ideal for 1:1 rider-driver communication                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

BROKER CHOICE: REDIS PUB/SUB vs KAFKA

```
+-------------------------------------------------------------------------+
|                                                                         |
|                  REDIS PUB/SUB              KAFKA                       |
|                  --------------             -----                       |
|                                                                         |
|  Delivery       At-most-once               At-least-once                |
|  Guarantee      (fire-and-forget)          (with offsets)               |
|                                                                         |
|  Persistence    None (in-memory)           Yes (disk-based)             |
|                                                                         |
|  Latency        ~1-2ms                     ~10-50ms                     |
|                                                                         |
|  Throughput     Very high                  Extremely high               |
|                 (100K+ msg/sec)            (millions msg/sec)           |
|                                                                         |
|  Replay         Not possible               Yes (offset seek)            |
|                                                                         |
|  Ordering       Not guaranteed             Per-partition                |
|                                                                         |
|  Use When:      * Speed > reliability      * Must not lose messages     |
|                 * Data is ephemeral        * Need audit trail           |
|                 * Missing msg is OK        * Need replay capability     |
|                 * Real-time streaming      * Event sourcing             |
|                                                                         |
|  FOR LOCATION STREAMING: Redis Pub/Sub wins.                            |
|  Location is ephemeral — old location is worthless.                     |
|  New update comes in 4 seconds anyway.                                  |
|  Speed (1-2ms) matters more than reliability.                           |
|                                                                         |
|  FOR RIDE STATE CHANGES: Kafka wins.                                    |
|  "Ride completed" must not be lost.                                     |
|  Payment depends on it.                                                 |
|  Need audit trail.                                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

**PROS:**
+ Clean decoupling (gateways don't know about each other)
+ Easy to add new consumers (monitoring, analytics)
+ Handles server failures gracefully
+ Scales horizontally with broker cluster
+ Battle-tested at massive scale (Redis/Kafka)

**CONS:**
- Additional infrastructure (broker cluster)
- Single point of failure (must cluster the broker)
- Slight latency overhead vs direct call
- Must manage subscriptions/unsubscriptions

VERDICT: Best approach for Uber's scale. Used in production.

### APPROACH 4: SHARED DATABASE POLLING (ANTI-PATTERN FOR REAL-TIME)

**CONCEPT:**
Driver writes location to database. Rider's server polls database for updates.

**HOW IT WORKS:**
```
1. Driver's gateway writes location to DB (every 4 seconds)
2. Rider's gateway polls DB (every 1 second): "Any new location?"
3. If new location found, push to rider's WebSocket

+-------------------------------------------------------------------------+
|                    DATABASE POLLING                                     |
|                                                                         |
|   Gateway A                  Database             Gateway B             |
|      |                          |                     |                 |
|      |-- INSERT location ------>|                     |                 |
|      |                          |<-- SELECT (poll) ---|                 |
|      |                          |                     | (every 1 sec)   |
|      |-- INSERT location ------>|                     |                 |
|      |                          |<-- SELECT (poll) ---|                 |
|      |                          |-- return location -->|                |
|      |                          |                     |--> push to      |
|      |                          |                     |    rider WS     |
|                                                                         |
+-------------------------------------------------------------------------+
```

**WHY THIS IS AN ANTI-PATTERN:**

1. LATENCY
Polling interval of 1 second = up to 1 second delay.
Pub/Sub delivers in 1-2 milliseconds.

2. DATABASE LOAD
1 million active rides × 1 poll/second = 1 million queries/second
This will crush any database.

3. INEFFICIENCY
Most polls return "no new data" — wasted work.
Pub/Sub only delivers when there's actual data.

4. SCALING
Database becomes bottleneck. Can't horizontally scale reads
without complex replication.

**PROS:**
+ Simple to implement
+ Uses existing infrastructure
+ Reliable (database is durable)

**CONS:**
- Terrible latency
- Massive database load
- Doesn't scale
- Wasteful (polling when no data)

VERDICT: Never use for real-time. OK for batch/async operations.

### APPROACH 5: WEBSOCKET CLUSTER WITH SHARED STATE (SOCKET.IO ADAPTER)

**CONCEPT:**
Use a WebSocket framework that handles cross-server communication internally.
The framework provides an "adapter" that syncs state across servers.

**HOW IT WORKS:**
- All servers connect to a shared adapter (Redis, Kafka, etc.)
- When you broadcast, the framework handles routing
- You write code as if all connections are local

EXAMPLE: Socket.IO with Redis Adapter
```
- Server A emits to "room:ride_123"
- Socket.IO adapter publishes to Redis
- Server B receives via Redis subscription
- Server B delivers to local sockets in that room

+-------------------------------------------------------------------------+
|                  SOCKET.IO REDIS ADAPTER                                |
|                                                                         |
|  +---------------+    +---------------+    +---------------+            |
|  |   Server 1    |    |   Server 2    |    |   Server 3    |            |
|  |               |    |               |    |               |            |
|  |  Socket.IO    |    |  Socket.IO    |    |  Socket.IO    |            |
|  |      |        |    |      |        |    |      |        |            |
|  |      v        |    |      v        |    |      v        |            |
|  | Redis Adapter |    | Redis Adapter |    | Redis Adapter |            |
|  |      |        |    |      |        |    |      |        |            |
|  +------+--------+    +------+--------+    +------+--------+            |
|         |                    |                    |                     |
|         +--------------------+--------------------+                     |
|                              |                                          |
|                       +------v------+                                   |
|                       |    Redis    |                                   |
|                       |   Cluster   |                                   |
|                       +-------------+                                   |
|                                                                         |
|  FROM YOUR CODE'S PERSPECTIVE:                                          |
|  io.to("ride_123").emit("location", data);                              |
|  // Just works! Framework handles cross-server routing.                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

**PROS:**
+ Simple API (framework handles complexity)
+ Built-in room/namespace management
+ Presence detection, heartbeats included
+ Well-tested, widely used

**CONS:**
- Framework lock-in
- Less control over optimization
- Under the hood, still uses Approach 3 (Pub/Sub)
- May not scale to Uber's level (millions of rooms)

VERDICT: Good for medium scale. Uber likely uses custom implementation.

### 2.9 COMPARISON: WHICH APPROACH IS BEST?

```
+-------------------------------------------------------------------------+
|                    APPROACH COMPARISON MATRIX                           |
|                                                                         |
|  Approach          Latency   Scalability  Complexity  Best For          |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  1. Sticky         ~1ms      Poor         Low         Small apps,       |
|     Sessions                 (hotspots)               prototypes        |
|                                                                         |
|  2. Direct         ~2-5ms    Medium       Medium      Moderate scale,   |
|     Server-to-                (N×N mesh)              low infra budget  |
|     Server                                                              |
|                                                                         |
|  3. Pub/Sub        ~2-5ms    Excellent    Medium      Large scale,      |
|     (Redis)                                           real-time         |
|                                                       streaming Y       |
|                                                                         |
|  4. DB Polling     ~1000ms   Poor         Low         Never for         |
|                              (DB crush)               real-time!        |
|                                                                         |
|  5. WS Cluster     ~2-5ms    Good         Low         Medium scale,     |
|     Framework                                         rapid dev         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  FOR UBER'S LOCATION STREAMING:                                         |
|                                                                         |
|  > Approach 3 (Redis Pub/Sub) is the winner.                            |
|                                                                         |
|  Reasons:                                                               |
|  * Millions of concurrent rides = need horizontal scaling               |
|  * Real-time requirement (30-50ms end-to-end)                           |
|  * Fire-and-forget is acceptable (location is ephemeral)                |
|  * Already using Redis for geospatial queries                           |
|  * Decoupling allows independent gateway scaling                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 2.10 HANDLING RECONNECTION: THE CONCEPTUAL CHALLENGE

**THE PROBLEM:**

Mobile networks are unreliable. Users disconnect and reconnect constantly:
- Entering elevator/tunnel (no signal)
- Switching from WiFi to cellular
- App backgrounded then foregrounded
- Network congestion

When rider reconnects, they might land on a DIFFERENT gateway server.

```
+-------------------------------------------------------------------------+
|                    RECONNECTION SCENARIO                                |
|                                                                         |
|   TIME T1: Rider connected to Gateway B                                 |
|   -------------------------------------                                 |
|   Gateway B subscribed to "ride:r_123"                                  |
|   Rider receiving location updates Y                                    |
|                                                                         |
|   TIME T2: Connection drops (tunnel)                                    |
|   ------------------------------------                                  |
|   Gateway B detects disconnect                                          |
|   Rider's app shows "Reconnecting..."                                   |
|                                                                         |
|   TIME T3: Rider reconnects                                             |
|   ------------------------------                                        |
|   Load balancer routes to Gateway C (different server!)                 |
|   Gateway C has NO subscription to "ride:r_123"                         |
|   Rider would NOT receive location updates!                             |
|                                                                         |
|   QUESTION: How does Gateway C know to subscribe?                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### THE SOLUTION: STATELESS RECOVERY

The key insight: Don't rely on server memory. Store ride state externally.

PRINCIPLE: EXTERNALIZE SESSION STATE
```
- Server memory is volatile (process can die, connection can move)
- Store "what should this user see?" in Redis
- On reconnection, server READS state and RECONSTRUCTS subscriptions

+-------------------------------------------------------------------------+
|                    STATE EXTERNALIZATION                                |
|                                                                         |
|   Redis Keys (always up-to-date):                                       |
|   +---------------------------------------------------------------+     |
|   |                                                               |     |
|   |   rider_active_ride:rider_abc  >  "ride_12345"                |     |
|   |   ride_driver:ride_12345       >  "driver_xyz"                |     |
|   |   driver_location:driver_xyz   >  {lat, lng, timestamp}       |     |
|   |                                                               |     |
|   +---------------------------------------------------------------+     |
|                                                                         |
|   RECONNECTION FLOW:                                                    |
|                                                                         |
|   1. Rider connects to Gateway C (any gateway)                          |
|                                                                         |
|   2. Gateway C receives connection with rider_id in auth token          |
|                                                                         |
|   3. Gateway C queries: "Does this rider have an active ride?"          |
|      > GET rider_active_ride:rider_abc > "ride_12345"                   |
|                                                                         |
|   4. If active ride exists:                                             |
|      a. Subscribe to "ride:ride_12345" channel                          |
|      b. Fetch current driver location from Redis                        |
|      c. Push current location to rider immediately (catch-up)           |
|                                                                         |
|   5. Rider sees driver on map without missing a beat                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

**WHY THIS WORKS:**
- ANY gateway can handle ANY rider
- No sticky sessions required
- No cross-server coordination needed
- State is externalized > servers are stateless
- If Gateway C dies, Gateway D can take over seamlessly

### HANDLING OLD SUBSCRIPTIONS (CLEANUP)

When rider moves from Gateway B to Gateway C, Gateway B still has a
subscription. This wastes resources (messages delivered to no one).

**THREE CLEANUP STRATEGIES:**

```
+-------------------------------------------------------------------------+
|                                                                         |
|   STRATEGY 1: EXPLICIT CLEANUP ON DISCONNECT                            |
|   ---------------------------------------------                         |
|                                                                         |
|   When Gateway B detects disconnect:                                    |
|   * Unsubscribe from "ride:r_123"                                       |
|   * Remove from connection registry                                     |
|                                                                         |
|   Pros: Immediate cleanup, no wasted resources                          |
|   Cons: Disconnect detection isn't always reliable (network partition)  |
|                                                                         |
|   ---------------------------------------------------------------------  |
|                                                                         |
|   STRATEGY 2: TTL-BASED EXPIRATION                                      |
|   ---------------------------------                                     |
|                                                                         |
|   * Subscription has TTL (e.g., 60 seconds)                             |
|   * Client sends periodic heartbeat to refresh TTL                      |
|   * If no heartbeat > subscription auto-expires                         |
|                                                                         |
|   Pros: Handles undetected disconnects, no false negatives              |
|   Cons: Wasted resources until TTL expires                              |
|                                                                         |
|   ---------------------------------------------------------------------  |
|                                                                         |
|   STRATEGY 3: HYBRID (RECOMMENDED)                                      |
|   -------------------------------                                       |
|                                                                         |
|   * Explicit cleanup when disconnect detected                           |
|   * TTL as safety net for undetected disconnects                        |
|   * Best of both worlds                                                 |
|                                                                         |
|   Implementation:                                                       |
|   * On connect: Subscribe + set TTL key "sub:ride_123:gateway_b" = 60s  |
|   * On heartbeat: Refresh TTL                                           |
|   * On disconnect: Immediately unsubscribe + delete key                 |
|   * If key expires: Background job unsubscribes                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMPLETE DATA FLOW SUMMARY

```
+-------------------------------------------------------------------------+
|           DRIVER LOCATION > RIDER'S MAP (COMPLETE PICTURE)              |
|                                                                         |
|  +----------+    +----------+    +----------+    +----------+          |
|  |  Driver  |    | Gateway  |    |  Redis   |    | Gateway  |          |
|  |  Phone   |    |    A     |    | Cluster  |    |    B     |          |
|  |          |    |          |    |          |    |          |          |
|  | GPS chip |    | WebSocket|    | * GEO    |    | Subscr.  |          |
|  | > 4s     |--->| Handler  |--->| * Pub/Sub|--->| Listener |          |
|  | updates  |    |          |    |          |    |          |          |
|  +----------+    +----------+    +----------+    +----+-----+          |
|                                                       |                 |
|                                                       v                 |
|                                               +--------------+          |
|                                               |    Rider     |          |
|                                               |    Phone     |          |
|                                               |              |          |
|                                               |  +--------+  |          |
|                                               |  | Map UI |  |          |
|                                               |  |  📍🚗  |  |          |
|                                               |  +--------+  |          |
|                                               +--------------+          |
|                                                                         |
|  LATENCY BREAKDOWN:                                                     |
|  +-- GPS to Driver WebSocket:     ~10ms                                 |
|  +-- Gateway A > Redis GEOADD:    ~0.5ms                                |
|  +-- Redis PUBLISH > Gateway B:   ~1-2ms                                |
|  +-- Gateway B > Rider WebSocket: ~5ms                                  |
|  +-- Render on Rider's map:       ~10ms                                 |
|  +-- TOTAL:                       ~30-50ms                              |
|                                                                         |
|  This means the rider sees the driver's position with sub-second        |
|  latency, even when connected to completely different servers.          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 3: GEOSPATIAL INDEXING — FINDING NEARBY DRIVERS

Now that we're receiving location updates, we need to answer the most
fundamental question in ride-hailing: "Which drivers are near this rider?"

### 3.1 THE PROXIMITY SEARCH PROBLEM

A rider at coordinates (37.7749, -122.4194) requests a ride. We need to find
all available drivers within 5 km. The naive approach:

for driver in all_drivers:  # 5 million drivers
distance = haversine(rider.location, driver.location)
if distance < 5:
candidates.append(driver)

This is O(N) where N = 5 million. Even at 1 microsecond per distance
calculation, that's 5 seconds per query. Unacceptable.

We need a data structure that allows spatial queries in O(log N) or better.

### 3.2 GEOHASH: ENCODING LOCATION AS STRINGS

### CONCEPT: SPACE-FILLING CURVES & LOCALITY PRESERVATION

The fundamental problem: How do we convert 2D coordinates (lat, lng) into a
1D value that preserves locality? Points that are close in 2D should have
similar 1D values.

PRINCIPLE: Z-ORDER CURVE (MORTON CODE)
Geohash uses a Z-order curve to interleave latitude and longitude bits:

Latitude bits:   1 0 1 1 0
Longitude bits:  0 1 1 0 1
Interleaved:    01 10 11 01 01  = "9q8yy" (base-32 encoded)

This creates a recursive spatial partitioning where nearby points often
(but not always) share prefixes.

```
+-------------------------------------------------------------------------+
|                    GEOHASH ENCODING ALGORITHM                           |
|                                                                         |
|  public class GeohashEncoder {                                         |
|      private static final String BASE32 = "0123456789bcdefghjkmnpqrs"+ |
|                                           "tuvwxyz";                   |
|                                                                         |
|      /**                                                               |
|       * Encode lat/lng to geohash string.                              |
|       *                                                                |
|       * ALGORITHM:                                                     |
|       * 1. Start with world bounds: lat [-90,90], lng [-180,180]       |
|       * 2. Binary search: Is point in left or right half?              |
|       * 3. Record bit: 0=left/lower, 1=right/upper                     |
|       * 4. Narrow bounds to the half containing the point              |
|       * 5. Alternate between longitude and latitude                    |
|       * 6. Every 5 bits, encode as base-32 character                   |
|       */                                                               |
|      public String encode(double lat, double lng, int precision) {     |
|          double[] latRange = {-90.0, 90.0};                            |
|          double[] lngRange = {-180.0, 180.0};                          |
|                                                                         |
|          StringBuilder geohash = new StringBuilder();                  |
|          int bits = 0;                                                 |
|          int bitCount = 0;                                             |
|          boolean isLng = true;  // Start with longitude                |
|                                                                         |
|          while (geohash.length() < precision) {                        |
|              double[] range = isLng ? lngRange : latRange;             |
|              double value = isLng ? lng : lat;                         |
|              double mid = (range[0] + range[1]) / 2;                   |
|                                                                         |
|              if (value >= mid) {                                       |
|                  bits = (bits << 1) | 1;  // Bit = 1 (upper half)     |
|                  range[0] = mid;                                       |
|              } else {                                                  |
|                  bits = bits << 1;         // Bit = 0 (lower half)    |
|                  range[1] = mid;                                       |
|              }                                                         |
|                                                                         |
|              bitCount++;                                               |
|              isLng = !isLng;  // Alternate lat/lng                    |
|                                                                         |
|              // Every 5 bits = 1 base-32 character                     |
|              if (bitCount == 5) {                                      |
|                  geohash.append(BASE32.charAt(bits));                  |
|                  bits = 0;                                             |
|                  bitCount = 0;                                         |
|              }                                                         |
|          }                                                             |
|          return geohash.toString();                                    |
|      }                                                                 |
|  }                                                                     |
|                                                                         |
|  // Example:                                                           |
|  // encode(37.7749, -122.4194, 5) > "9q8yy"                           |
|  // encode(37.7750, -122.4190, 5) > "9q8yy"  (nearby = same prefix)   |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    PRECISION LEVELS                                     |
|                                                                         |
|  +----------+------------------+-------------------------------------+ |
|  |  Length  |  Cell Size       |  Use Case                           | |
|  +----------+------------------+-------------------------------------+ |
|  |  1       |  5,000 km        |  Continent                          | |
|  |  2       |  1,250 km        |  Large country                      | |
|  |  3       |  156 km          |  State/Province                     | |
|  |  4       |  39 km           |  City                               | |
|  |  5       |  4.9 km          |  Neighborhood (Uber uses this)     | |
|  |  6       |  1.2 km          |  Street                             | |
|  |  7       |  152 m           |  Block                              | |
|  |  8       |  38 m            |  Building                           | |
|  +----------+------------------+-------------------------------------+ |
|                                                                         |
+-------------------------------------------------------------------------+
```

**EDGE EFFECT PROBLEM & SOLUTION:**

```
+---------+---------+
|  9q8yx  |  9q8yy  |  
|    *    |   ★     |  * and ★ are 100m apart but in DIFFERENT cells!
+---------+---------+
```

Because the Z-curve has "jumps" at cell boundaries, nearby points can have
completely different prefixes. Solution: Query the 8 neighboring cells too.

```
+-------------------------------------------------------------------------+
|  public List<String> getNeighbors(String geohash) {                    |
|      // Returns 8 adjacent cells plus the center                       |
|      // Algorithm: Decode to lat/lng, offset, re-encode                |
|      List<String> neighbors = new ArrayList<>();                       |
|      for (int dx = -1; dx <= 1; dx++) {                                |
|          for (int dy = -1; dy <= 1; dy++) {                            |
|              neighbors.add(getNeighbor(geohash, dx, dy));              |
|          }                                                             |
|      }                                                                 |
|      return neighbors;                                                 |
|  }                                                                     |
|                                                                         |
|  // Query all 9 cells                                                  |
|  List<String> cells = getNeighbors(riderGeohash);                     |
|  List<Driver> nearby = driverRepository.findByGeohashIn(cells);       |
+-------------------------------------------------------------------------+
```

**TRADE-OFFS:**

Advantages:
- Simple to implement and understand
- Works with standard database string indexes
- Hierarchical (longer prefix = smaller area)

Disadvantages:
- Edge effects (need to query 9 cells instead of 1)
- Cells are not uniform (vary by latitude due to Earth's curvature)
- Square cells don't align with movement (diagonals are √2 times farther)

### 3.3 H3: UBER'S HEXAGONAL GRID (DEEP DIVE)

Uber developed H3, a hexagonal hierarchical grid, to address geohash's
limitations. Why hexagons?

```
+-------------------------------------------------------------------------+
|              SQUARES VS HEXAGONS                                        |
|                                                                         |
|  SQUARES (Geohash):                 HEXAGONS (H3):                     |
|  +---+---+---+                         /\ /\ /\                        |
|  |   |   |   |                        /  \/  \/  \                      |
|  +---+-★-+---+                        \  /\★ /\  /                      |
|  |   |   |   |                         \/  \/  \/                       |
|  +---+---+---+                         /\ /\ /\                        |
|                                                                         |
|  8 neighbors                       6 neighbors                         |
|  4 at distance d                   ALL at distance d                   |
|  4 at distance √2×d                                                    |
|                                                                         |
|  For a car, moving to diagonal     All neighbors are equidistant      |
|  neighbor takes 41% longer         Better for travel time estimates   |
|                                                                         |
+-------------------------------------------------------------------------+
```

H3 key properties:

1. UNIFORM NEIGHBOR DISTANCE
All 6 neighbors are equidistant. This matters for ride-hailing because
we're estimating travel time, not just straight-line distance.

2. HIERARCHICAL RESOLUTIONS
H3 has 16 resolution levels (0-15):
- Resolution 0: ~4.3 million km² (continental)
- Resolution 7: ~5.2 km² (city analysis)
- Resolution 9: ~0.1 km² (driver matching)
- Resolution 12: ~300 m² (pickup precision)

3. CONSISTENT CELL IDS
Each cell has a 64-bit ID that encodes its position and resolution.
This makes storage and indexing efficient.

```
+-------------------------------------------------------------------------+
|                    H3 IN PRACTICE                                       |
|                                                                         |
|  # Convert location to H3 cell (resolution 9, ~100m cells)             |
|  cell_id = h3.latlng_to_cell(37.7749, -122.4194, resolution=9)         |
|  # > '89283082837ffff'                                                 |
|                                                                         |
|  # Get all drivers in this cell and neighbors                          |
|  cells = h3.grid_disk(cell_id, k=2)  # Cell + 2 rings of neighbors    |
|  # > ['89283082837ffff', '89283082833ffff', ...]  (19 cells total)    |
|                                                                         |
|  # Query Redis for drivers in these cells                              |
|  for cell in cells:                                                    |
|      drivers = redis.smembers(f"drivers:{cell}")                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 3.4 REDIS GEOSPATIAL IMPLEMENTATION

Redis has built-in geospatial support using sorted sets. Under the hood,
it uses geohash encoding, but the API abstracts this away.

```
+-------------------------------------------------------------------------+
|                    REDIS GEOSPATIAL COMMANDS                            |
|                                                                         |
|  # Add driver location                                                 |
|  GEOADD drivers:sf -122.4194 37.7749 "driver_abc"                     |
|                                                                         |
|  # Find drivers within 5 km of rider                                  |
|  GEORADIUS drivers:sf -122.4000 37.7800 5 km                          |
|      WITHDIST        # Include distance                                |
|      WITHCOORD       # Include coordinates                             |
|      COUNT 20        # Limit results                                   |
|      ASC             # Sort by distance                                |
|                                                                         |
|  # Result:                                                             |
|  # 1) "driver_abc"                                                     |
|  #    distance: 1.2345                                                 |
|  #    coordinates: [-122.4194, 37.7749]                                |
|  # 2) "driver_def"                                                     |
|  #    distance: 2.3456                                                 |
|  #    ...                                                              |
|                                                                         |
|  Time complexity: O(N+log(M)) where N = results, M = total points     |
|  For 50,000 drivers in a city, finding 20 nearby: ~1-2ms              |
|                                                                         |
+-------------------------------------------------------------------------+
```

We partition by city to keep each geospatial index manageable:

drivers:sf     > San Francisco drivers (50K)
drivers:nyc    > New York drivers (80K)
drivers:london > London drivers (40K)

This partitioning serves two purposes:
1. PERFORMANCE: Smaller indexes mean faster queries
2. SCALING: We can put different cities on different Redis clusters

## PART 4: DRIVER-RIDER MATCHING — THE HEART OF UBER

We can track drivers and find nearby ones. Now comes the core algorithm:
matching a rider with the best available driver.

### 4.1 THE MATCHING PROBLEM

When a rider requests a ride, we need to:
1. Find nearby available drivers
2. Calculate ETA for each driver
3. Consider driver ratings and acceptance rates
4. Select the best match
5. Send the request to the driver
6. Handle acceptance/rejection/timeout
7. Prevent race conditions if multiple riders want the same driver

This isn't just a proximity problem — it's an optimization problem with
multiple constraints and objectives.

### 4.2 GREEDY VS OPTIMAL MATCHING

GREEDY APPROACH (Simple):
For each ride request, immediately match with the closest available driver.

Rider R1 requests at T=0, Driver D1 is 1 min away > Match R1-D1
Rider R2 requests at T=0.5, D2 is 3 min away > Match R2-D2

Problem: What if R2's pickup is on D1's route, and R1's pickup is on D2's
route? Greedy matching might result in suboptimal total wait time.

OPTIMAL APPROACH (Batch Matching):
Collect requests over a small time window (e.g., 2 seconds), then solve
the assignment problem globally.

```
+-------------------------------------------------------------------------+
|                    BATCHED MATCHING                                     |
|                                                                         |
|  Time Window: 2 seconds                                                 |
|                                                                         |
|  Requests collected: R1, R2, R3                                         |
|  Available drivers: D1, D2, D3, D4                                      |
|                                                                         |
|  Cost Matrix (ETA in minutes):                                         |
|  +-----+-----+-----+-----+-----+                                       |
|  |     | D1  | D2  | D3  | D4  |                                       |
|  +-----+-----+-----+-----+-----+                                       |
|  | R1  |  2  |  5  |  3  |  7  |                                       |
|  | R2  |  4  |  3  |  6  |  2  |                                       |
|  | R3  |  8  |  4  |  2  |  5  |                                       |
|  +-----+-----+-----+-----+-----+                                       |
|                                                                         |
|  Greedy assignment:                                                    |
|  R1 > D1 (closest), R2 > D2 (closest remaining), R3 > D3              |
|  Total: 2 + 3 + 2 = 7 minutes                                         |
|                                                                         |
|  Optimal assignment (Hungarian algorithm):                             |
|  R1 > D1 (2), R2 > D4 (2), R3 > D3 (2)                                |
|  Total: 2 + 2 + 2 = 6 minutes                                         |
|                                                                         |
|  Improvement: 14% reduction in total wait time                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

Uber uses batched matching. The 2-second delay is imperceptible to users,
but the optimization reduces average wait times by 10-20%.

### 4.3 HANDLING RACE CONDITIONS (MULTIPLE DRIVERS)

Here's a scenario that will break a naive implementation:

T=0.000s: Rider R1 requests ride
T=0.001s: Rider R2 requests ride

Both requests are processed in parallel on different servers.

T=0.010s: Server A finds Driver D1 is closest to R1
T=0.011s: Server B finds Driver D1 is closest to R2

T=0.020s: Server A sends ride request to D1 for R1
T=0.021s: Server B sends ride request to D1 for R2

D1 receives two ride requests!

Without proper locking, we could:
- Double-book a driver
- Leave one rider without a match
- Create inconsistent state in our database

We need distributed locking.

### 4.4 DISTRIBUTED LOCKING DEEP DIVE

### THE FUNDAMENTAL PROBLEM

In a single-server world, locking is easy. Java's synchronized keyword or
ReentrantLock works because all threads share the same memory space. The lock
is just a memory location that threads can read and write atomically.

In a distributed system, this breaks completely:

```
+-------------------------------------------------------------------------+
|                    WHY LOCAL LOCKS DON'T WORK                          |
|                                                                         |
|   Server A (NYC)                    Server B (NYC)                      |
|   +-----------------+              +-----------------+                 |
|   |  Memory         |              |  Memory         |                 |
|   |  +-----------+  |              |  +-----------+  |                 |
|   |  | lock = 0  |  |              |  | lock = 0  |  |                 |
|   |  +-----------+  |              |  +-----------+  |                 |
|   +-----------------+              +-----------------+                 |
|                                                                         |
|   Both servers have their OWN memory.                                  |
|   Both can set their local lock = 1.                                   |
|   Both think they have the lock!                                       |
|                                                                         |
|   There's no shared memory in a distributed system.                    |
|   We need an EXTERNAL coordination point.                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### THREE REQUIREMENTS FOR A CORRECT DISTRIBUTED LOCK

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. MUTUAL EXCLUSION (Safety)                                          |
|     -------------------------                                          |
|     At any given moment, AT MOST one client holds the lock.            |
|     If two clients think they have the lock simultaneously,            |
|     the lock is useless.                                               |
|                                                                         |
|  2. DEADLOCK FREEDOM (Liveness)                                        |
|     ---------------------------                                        |
|     If a client acquires the lock and then crashes (or gets            |
|     partitioned), the lock must EVENTUALLY be released.                |
|     Otherwise, the resource is locked forever.                         |
|                                                                         |
|  3. FAULT TOLERANCE (Availability)                                     |
|     ------------------------------                                     |
|     As long as the majority of lock servers are running,               |
|     clients should be able to acquire and release locks.               |
|     The lock system itself can't be a single point of failure.         |
|                                                                         |
+-------------------------------------------------------------------------+
```

These requirements are in TENSION. Strong mutual exclusion often conflicts
with high availability (see: CAP theorem). Each locking approach makes
different trade-offs.

### APPROACH 1: DATABASE-BASED LOCKING

CONCEPT: Use the database's ACID properties to create a lock table.

**HOW IT WORKS:**

```
+-------------------------------------------------------------------------+
|                    DATABASE LOCK MECHANISM                              |
|                                                                         |
|  Lock Table:                                                           |
|  +----------------------------------------------------------+          |
|  |  resource_id (PK)  |  owner_id   |  acquired_at          |          |
|  +--------------------+-------------+-----------------------+          |
|  |  ride_12345        |  server_A   |  2024-01-15 10:30:00  |          |
|  +----------------------------------------------------------+          |
|                                                                         |
|  ACQUIRE LOCK:                                                         |
|  INSERT INTO locks (resource_id, owner_id, acquired_at)                |
|  VALUES ('ride_12345', 'server_A', NOW());                             |
|                                                                         |
|  * If INSERT succeeds > Lock acquired                                  |
|  * If INSERT fails (duplicate key) > Lock held by someone else        |
|                                                                         |
|  RELEASE LOCK:                                                         |
|  DELETE FROM locks WHERE resource_id = 'ride_12345'                    |
|                       AND owner_id = 'server_A';                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

**WHY IT WORKS:**
- Database guarantees unique constraint on resource_id
- INSERT is atomic — only one will succeed
- ACID properties ensure consistency

**PROBLEMS:**
- SLOW: Database round-trip is 1-10ms, compared to <1ms for Redis
- SINGLE POINT OF FAILURE: DB down = no locks
- NO AUTO-EXPIRY: If lock holder crashes, lock is stuck forever
(Need a separate cleanup job to delete old locks)
- CONNECTION LIMITS: Each lock attempt uses a DB connection
- BLOCKING: High lock contention crushes the database

VERDICT: Works for low-throughput systems. Not suitable for Uber's
1000+ ride matches per second.

### APPROACH 2: ZOOKEEPER-BASED LOCKING

CONCEPT: Use Zookeeper's consensus protocol and ephemeral nodes for
coordination.

WHAT IS ZOOKEEPER?
Zookeeper is a distributed coordination service that provides:
- Strongly consistent key-value storage
- Ephemeral nodes (automatically deleted when client disconnects)
- Sequential nodes (for ordering)
- Watch notifications (get notified when data changes)

**HOW EPHEMERAL ZNODES WORK:**

```
+-------------------------------------------------------------------------+
|                    ZOOKEEPER EPHEMERAL NODES                            |
|                                                                         |
|  PRINCIPLE: Session-Based Automatic Cleanup                            |
|                                                                         |
|  When a client connects to Zookeeper, it establishes a SESSION.        |
|  Ephemeral nodes are tied to this session:                             |
|                                                                         |
|  * Client connects > Session created                                   |
|  * Client creates ephemeral node > Node tied to session                |
|  * Client disconnects (crash, network failure) > Session expires       |
|  * Session expires > ALL ephemeral nodes auto-deleted                  |
|                                                                         |
|  This solves the "crash while holding lock" problem automatically!     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  LOCK ACQUISITION:                                                     |
|  1. Try to create ephemeral node: /locks/ride_12345                    |
|  2. If created > You have the lock                                     |
|  3. If exists > Set a WATCH and wait                                   |
|  4. When node deleted > Watch fires, retry from step 1                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SEQUENTIAL NODES FOR FAIRNESS:                                        |
|  Instead of all clients fighting for one node, each creates a          |
|  sequential ephemeral node:                                            |
|                                                                         |
|  /locks/ride_12345/lock-0000000001  < Created by Server A              |
|  /locks/ride_12345/lock-0000000002  < Created by Server B              |
|  /locks/ride_12345/lock-0000000003  < Created by Server C              |
|                                                                         |
|  RULE: The client with the LOWEST sequence number has the lock.        |
|  Each client watches only the node BEFORE it (prevents herd effect).   |
|                                                                         |
+-------------------------------------------------------------------------+
```

**WHY IT WORKS:**
- CONSENSUS PROTOCOL (ZAB): All Zookeeper nodes agree on state
- EPHEMERAL NODES: Automatic lock release on client failure
- SEQUENTIAL NODES: Fair ordering (FIFO)
- WATCHES: Efficient notification, no polling

**PROBLEMS:**
- COMPLEXITY: Requires running a Zookeeper cluster (3-5 nodes minimum)
- LATENCY: Consensus overhead adds 5-20ms per operation
- SESSION TIMEOUT TUNING: Too short = false lock releases, too long =
delayed cleanup
- OPERATIONAL OVERHEAD: Another system to monitor and maintain

VERDICT: Best for strong consistency requirements. Used by Kafka, HBase.
Overkill for Uber's ride matching where we verify in the database anyway.

### APPROACH 3: REDIS-BASED LOCKING (SETNX)

CONCEPT: Use Redis's atomic operations with TTL for simple, fast locking.

**THE SETNX PRINCIPLE:**

```
+-------------------------------------------------------------------------+
|                    COMPARE-AND-SWAP (CAS) PATTERN                       |
|                                                                         |
|  SETNX = "SET if Not eXists"                                           |
|                                                                         |
|  The command does THREE things ATOMICALLY (all-or-nothing):            |
|  1. Check if key exists                                                |
|  2. If not, set the key to a value                                     |
|  3. Return whether we succeeded                                        |
|                                                                         |
|  This atomicity is CRITICAL. If check and set were separate:           |
|                                                                         |
|  Server A: EXISTS lock?     > No                                       |
|  Server B: EXISTS lock?     > No                                       |
|  Server A: SET lock = "A"   > OK                                       |
|  Server B: SET lock = "B"   > OK (overwrites A!)                       |
|                                                                         |
|  Both think they have the lock. Disaster!                              |
|                                                                         |
|  With SETNX:                                                           |
|  Server A: SETNX lock "A"   > 1 (success, lock acquired)               |
|  Server B: SETNX lock "B"   > 0 (failed, lock held by A)               |
|                                                                         |
|  Only one succeeds. Mutual exclusion guaranteed.                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

**TTL FOR DEADLOCK PREVENTION:**

```
+-------------------------------------------------------------------------+
|                    TIME-TO-LIVE (TTL) MECHANISM                         |
|                                                                         |
|  PROBLEM: If lock holder crashes, the lock stays forever.              |
|                                                                         |
|  SOLUTION: Set expiration time when acquiring lock.                    |
|                                                                         |
|  Command: SET lock "owner_A" NX EX 30                                  |
|                               |  |                                      |
|                               |  +-- Expire after 30 seconds           |
|                               +----- Only if Not eXists                |
|                                                                         |
|  TIMELINE:                                                             |
|  T=0s:   Server A acquires lock (TTL = 30s)                           |
|  T=5s:   Server A crashes                                             |
|  T=30s:  Lock auto-expires                                            |
|  T=31s:  Server B can acquire the lock                                |
|                                                                         |
|  No manual cleanup needed! Redis handles it automatically.             |
|                                                                         |
+-------------------------------------------------------------------------+
```

**THE LOCK TOKEN (WHY IT MATTERS):**

```
+-------------------------------------------------------------------------+
|                    SAFE LOCK RELEASE                                    |
|                                                                         |
|  WRONG WAY TO RELEASE:                                                 |
|  DELETE lock                                                           |
|                                                                         |
|  Why is this wrong? Race condition:                                    |
|                                                                         |
|  T=0s:   Server A acquires lock                                        |
|  T=25s:  Server A finishes work, about to release                     |
|  T=30s:  Lock expires (A took too long!)                              |
|  T=31s:  Server B acquires the lock                                   |
|  T=32s:  Server A executes DELETE lock                                |
|          > Deletes B's lock! B doesn't know it lost the lock.         |
|                                                                         |
|  --------------------------------------------------------------------- |
|                                                                         |
|  RIGHT WAY: Use a unique token                                         |
|                                                                         |
|  ACQUIRE: SET lock "unique_token_abc" NX EX 30                         |
|  RELEASE: Only delete IF the value is still "unique_token_abc"         |
|                                                                         |
|  This must be ATOMIC (check value + delete in one operation).          |
|  Redis doesn't have a native command for this, so we use Lua script.  |
|                                                                         |
|  PRINCIPLE: "Delete only if it's still mine"                           |
|                                                                         |
|  Algorithm:                                                            |
|  1. Read the lock value                                                |
|  2. Compare with my token                                              |
|  3. If match, delete the lock                                          |
|  4. All three steps execute atomically                                 |
|                                                                         |
|  This prevents accidentally deleting someone else's lock.              |
|                                                                         |
+-------------------------------------------------------------------------+
```

**WHY UBER CHOOSES REDIS:**
- SPEED: Sub-millisecond latency (critical for 1000+ matches/second)
- ALREADY IN STACK: We use Redis for location data anyway
- SIMPLE: No consensus protocol to understand or operate
- TTL: Automatic deadlock prevention
- GOOD ENOUGH: We verify in the database before committing

**PROBLEMS WITH REDIS LOCKING:**
- NOT PERFECTLY SAFE: Redis replication is async. If master fails
right after granting lock, the new master might not have it.
- CLOCK SKEW: TTL depends on time. Clock drift can cause issues.
- SINGLE POINT OF FAILURE: Single Redis = no lock if Redis is down.

### APPROACH 4: ETCD-BASED LOCKING

CONCEPT: Like Redis but with strong consistency via Raft consensus.

```
+-------------------------------------------------------------------------+
|                    ETCD LEASE-BASED LOCKING                             |
|                                                                         |
|  LEASE CONCEPT:                                                        |
|  A lease is a time-bound grant. The client must keep renewing it       |
|  (sending heartbeats). If heartbeats stop, lease expires.              |
|                                                                         |
|  ACQUIRE:                                                              |
|  1. Create a lease with TTL (e.g., 30 seconds)                        |
|  2. Put key with this lease attached                                   |
|  3. Start lease keepalive (background heartbeat)                       |
|                                                                         |
|  RELEASE:                                                              |
|  1. Revoke the lease                                                   |
|  2. All keys attached to lease are deleted automatically               |
|                                                                         |
|  AUTO-RELEASE:                                                         |
|  If client crashes, heartbeats stop, lease expires, lock released.    |
|                                                                         |
|  WHY STRONGER THAN REDIS:                                              |
|  etcd uses Raft consensus. A write is only acknowledged after         |
|  majority of nodes have it. No data loss on failover.                 |
|                                                                         |
|  TRADE-OFF:                                                            |
|  Stronger guarantees but ~5-10ms latency (vs <1ms for Redis).         |
|                                                                         |
+-------------------------------------------------------------------------+
```

VERDICT: Use when you need strong consistency AND can tolerate
slightly higher latency. Kubernetes uses etcd for its coordination.

### THE REDLOCK CONTROVERSY

Redis's creator (antirez) proposed Redlock: use 5 Redis nodes, acquire
lock on majority (3+). This provides better fault tolerance.

```
+-------------------------------------------------------------------------+
|                    REDLOCK ALGORITHM                                    |
|                                                                         |
|  1. Get current time in milliseconds                                    |
|  2. Try to acquire lock on all 5 Redis nodes sequentially               |
|     (with short timeout, e.g., 5-50ms per node)                         |
|  3. Calculate elapsed time                                              |
|  4. Lock is acquired if:                                                |
|     * Acquired on majority (3+ nodes)                                   |
|     * Elapsed time < lock TTL                                           |
|  5. If lock acquired, validity time = TTL - elapsed time                |
|  6. If lock failed, unlock all nodes                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

**THE DEBATE:**
Martin Kleppmann (author of "Designing Data-Intensive Applications")
criticized Redlock as unsafe:

```
+-------------------------------------------------------------------------+
|                    KLEPPMANN'S CRITICISM                                |
|                                                                         |
|  TIMING ASSUMPTION PROBLEM:                                            |
|  Redlock assumes bounded network delays and process pauses.            |
|  In reality:                                                           |
|  * GC pauses can be 10+ seconds                                       |
|  * Network can be arbitrarily slow                                    |
|  * Clocks can drift                                                   |
|                                                                         |
|  SCENARIO:                                                             |
|  T=0:  Client A acquires lock (TTL = 30s)                             |
|  T=1:  Client A starts long GC pause                                  |
|  T=31: Lock expires on Redis (while A is frozen)                      |
|  T=32: Client B acquires lock                                         |
|  T=33: Client B writes to database                                    |
|  T=40: Client A's GC ends, it THINKS it has the lock                  |
|  T=41: Client A writes to database (CORRUPTS DATA!)                   |
|                                                                         |
|  The lock expiration happened while A was paused.                     |
|  A has no way to know the lock was lost.                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

UBER'S PRAGMATIC APPROACH:
We don't rely solely on the distributed lock. We use it as an
optimization, but the DATABASE is the source of truth. We verify
before committing (more on fencing tokens below).

### LOCK GRANULARITY: WHAT EXACTLY ARE WE LOCKING?

When we say "lock," we need to be precise about WHAT we're locking.
The granularity affects concurrency, performance, and correctness.

```
+-------------------------------------------------------------------------+
|                    LOCK GRANULARITY LEVELS                              |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |  LEVEL        |  LOCKS           |  CONCURRENCY  |  OVERHEAD    |   |
|  +---------------+------------------+---------------+--------------+   |
|  |  Database     |  Entire DB       |  Very Low     |  Very Low    |   |
|  |  Table        |  Whole table     |  Low          |  Low         |   |
|  |  Row          |  Single row      |  High         |  Medium      |   |
|  |  Field/Column |  Single field    |  Very High    |  High        |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  TRADE-OFF: Finer granularity = more concurrency but more overhead    |
|                                                                         |
+-------------------------------------------------------------------------+
```

FOR UBER'S RIDE MATCHING, WE LOCK AT THE ROW LEVEL:

```
+-------------------------------------------------------------------------+
|                    ROW-LEVEL LOCKING IN RIDE MATCHING                   |
|                                                                         |
|  WHAT WE LOCK: One specific ride row                                    |
|  LOCK KEY:     "lock:ride:{ride_id}"                                    |
|                                                                         |
|  Example:                                                               |
|  * lock:ride:12345 > Locks only ride 12345                              |
|  * lock:ride:67890 > Locks only ride 67890                              |
|                                                                         |
|  These are INDEPENDENT. Two servers can simultaneously:                 |
|  * Server A works on ride 12345 (holds lock:ride:12345)                 |
|  * Server B works on ride 67890 (holds lock:ride:67890)                 |
|                                                                         |
|  No conflict! Maximum concurrency.                                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WHY NOT TABLE-LEVEL?                                                   |
|                                                                         |
|  If we locked the entire "rides" table:                                |
|  * Only ONE ride could be matched at a time                           |
|  * 1000 rides/second would queue behind each other                    |
|  * System would be unusably slow                                      |
|                                                                         |
|  WHY NOT FIELD-LEVEL?                                                  |
|                                                                         |
|  Ride matching modifies multiple fields together:                      |
|  * driver_id, status, matched_at, eta                                 |
|  * These MUST change atomically (all or nothing)                      |
|  * Locking individual fields would allow partial updates              |
|  * Row-level ensures atomic update of all fields                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

DRIVER LOCKING — ALSO ROW LEVEL:

```
+-------------------------------------------------------------------------+
|                    DRIVER AVAILABILITY LOCK                             |
|                                                                         |
|  Sometimes we need to lock the DRIVER, not the ride.                   |
|                                                                         |
|  SCENARIO:                                                             |
|  Two riders (R1 and R2) both want Driver D1.                          |
|  We need to ensure only ONE gets D1.                                  |
|                                                                         |
|  APPROACH 1: Lock the Ride                                             |
|  -----------------------------                                         |
|  Lock ride:R1, check if D1 available, assign D1                       |
|  Lock ride:R2, check if D1 available, assign D1                       |
|                                                                         |
|  PROBLEM: Both checks happen before either assignment!                 |
|  Both see D1 as available. Race condition.                            |
|                                                                         |
|  APPROACH 2: Lock the Driver (Correct)                                 |
|  ------------------------------------                                  |
|  Lock driver:D1                                                       |
|    > Check D1's current assignment                                    |
|    > If available, assign to R1                                       |
|    > Update D1's status                                               |
|  Unlock driver:D1                                                     |
|                                                                         |
|  Now when R2 tries to lock driver:D1:                                 |
|    > Lock already held by R1's operation                              |
|    > R2 waits or tries different driver                               |
|                                                                         |
|  LOCK KEY: "lock:driver:{driver_id}"                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### HOW TO DECIDE: DRIVER LOCK VS RIDE LOCK?

This is one of the most important design decisions. The answer depends on
understanding the RACE CONDITION you're trying to prevent.

**THE DECISION FRAMEWORK:**

```
+-------------------------------------------------------------------------+
|                    ASK: WHAT IS THE SHARED RESOURCE?                    |
|                                                                         |
|  The lock protects access to a SHARED RESOURCE.                        |
|  Identify what's being competed for:                                   |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  | Scenario                     | Shared Resource | Lock Needed    |   |
|  +------------------------------+-----------------+----------------+   |
|  | 2 riders want same driver    | The DRIVER      | Driver Lock    |   |
|  | 2 servers update same ride   | The RIDE        | Ride Lock      |   |
|  | 2 threads charge same ride   | The PAYMENT     | Payment Lock   |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  PRINCIPLE: Lock the resource that's being COMPETED FOR.               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SCENARIO ANALYSIS: WHEN TO USE EACH LOCK

```
+-------------------------------------------------------------------------+
|                    SCENARIO 1: RIDER REQUESTS A RIDE                    |
|                                                                         |
|  What happens:                                                         |
|  1. Rider requests ride > system creates ride record                   |
|  2. Matching service finds nearby drivers                              |
|  3. System needs to assign best driver to this ride                   |
|                                                                         |
|  What could go wrong?                                                  |
|                                                                         |
|  RACE CONDITION A: Same ride matched twice                            |
|  ----------------------------------------                              |
|  Two matching servers both pick up ride_123.                          |
|  Both find drivers, both try to assign.                               |
|  > Ride ends up with conflicting driver assignments!                  |
|                                                                         |
|  SOLUTION: Lock the RIDE                                               |
|  Lock key: "lock:ride:123"                                            |
|  First server to lock processes the ride.                             |
|  Second server sees lock, skips (ride already being handled).         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  RACE CONDITION B: Same driver assigned to multiple rides             |
|  ----------------------------------------------------                  |
|  Ride_123 and Ride_456 are both looking for drivers.                  |
|  Both identify Driver_D1 as closest.                                  |
|  Both check: "Is D1 available?" > Yes (at that moment)               |
|  Both assign D1 > D1 has two rides!                                   |
|                                                                         |
|  SOLUTION: Lock the DRIVER                                             |
|  Before assigning D1 to a ride:                                       |
|  1. Lock "lock:driver:D1"                                             |
|  2. Check D1's status WHILE HOLDING LOCK                              |
|  3. If available, assign and update status                            |
|  4. Release lock                                                       |
|                                                                         |
|  Second ride sees lock, waits or tries different driver.              |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    SCENARIO 2: DRIVER ACCEPTS RIDE                      |
|                                                                         |
|  What happens:                                                         |
|  1. Driver receives ride request on phone                              |
|  2. Driver taps "Accept"                                               |
|  3. System updates ride status to ACCEPTED                            |
|                                                                         |
|  What could go wrong?                                                  |
|                                                                         |
|  RACE CONDITION: Driver accepts, but ride already cancelled           |
|  -----------------------------------------------------------           |
|  T=0: Rider cancels ride (status > CANCELLED)                         |
|  T=1: Driver taps Accept (tries to set status > ACCEPTED)             |
|  Without lock: Accept might overwrite CANCELLED!                      |
|                                                                         |
|  SOLUTION: Lock the RIDE                                               |
|  Before accepting:                                                     |
|  1. Lock "lock:ride:123"                                              |
|  2. Check current status                                              |
|  3. If status is MATCHING, update to ACCEPTED                         |
|  4. If status is CANCELLED, reject acceptance                         |
|  5. Release lock                                                       |
|                                                                         |
|  WHY NOT DRIVER LOCK?                                                  |
|  The conflict is about the RIDE's state, not the driver.              |
|  Two operations (cancel and accept) are competing to modify           |
|  the same ride record.                                                |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    SCENARIO 3: BATCHED MATCHING                         |
|                                                                         |
|  What happens:                                                         |
|  1. System collects 50 ride requests in 2-second window               |
|  2. System has 100 available drivers                                  |
|  3. Hungarian algorithm finds optimal assignment                       |
|  4. System assigns all 50 rides to 50 drivers                         |
|                                                                         |
|  What could go wrong?                                                  |
|                                                                         |
|  RACE CONDITION: Another server runs matching simultaneously          |
|  ---------------------------------------------------------             |
|  Server A: Runs matching, assigns D1 to R1                            |
|  Server B: Runs matching, assigns D1 to R2 (same driver!)             |
|                                                                         |
|  SOLUTION: Multiple locks needed                                       |
|                                                                         |
|  Option A: Lock each driver individually                              |
|  -----------------------------------------                             |
|  For each assignment (ride, driver):                                  |
|    1. Lock "lock:driver:{driver_id}"                                  |
|    2. Verify driver still available                                   |
|    3. Assign                                                          |
|    4. Release lock                                                     |
|                                                                         |
|  PROS: Fine-grained, high concurrency                                 |
|  CONS: Many lock operations, potential for partial failures           |
|                                                                         |
|  Option B: Lock the entire matching zone                              |
|  -----------------------------------------                             |
|  Lock "lock:matching:zone:sf_downtown"                                |
|  Only one server runs matching for this zone at a time                |
|                                                                         |
|  PROS: Simpler, atomic batch                                          |
|  CONS: Less concurrency                                               |
|                                                                         |
|  UBER'S APPROACH: Option A with verification                          |
|  Lock each driver, but verify each assignment.                        |
|  If one fails, continue with others (don't rollback all).            |
|                                                                         |
+-------------------------------------------------------------------------+
```

**THE COMPLETE DECISION TREE:**

```
+-------------------------------------------------------------------------+
|                                                                         |
|  When you need a lock, ask:                                            |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |  Q1: What RESOURCE is being modified?                          |   |
|  |      v                                                          |   |
|  |  +-----------------------------------------------------------+ |   |
|  |  | Ride record (status, driver_id)    > Lock: RIDE           | |   |
|  |  | Driver availability                > Lock: DRIVER         | |   |
|  |  | Payment record                     > Lock: PAYMENT        | |   |
|  |  | Both ride AND driver               > Lock: BOTH           | |   |
|  |  +-----------------------------------------------------------+ |   |
|  |                                                                 |   |
|  |  Q2: What is being COMPETED FOR?                               |   |
|  |      v                                                          |   |
|  |  +-----------------------------------------------------------+ |   |
|  |  | Two riders want same driver         > Lock: DRIVER        | |   |
|  |  | Two servers process same ride       > Lock: RIDE          | |   |
|  |  | Two requests charge same payment    > Lock: PAYMENT       | |   |
|  |  +-----------------------------------------------------------+ |   |
|  |                                                                 |   |
|  |  Q3: What's the SMALLEST scope that ensures correctness?       |   |
|  |      v                                                          |   |
|  |  +-----------------------------------------------------------+ |   |
|  |  | Lock the specific ride, not all rides                     | |   |
|  |  | Lock the specific driver, not all drivers                 | |   |
|  |  | Finer granularity = more concurrency                      | |   |
|  |  +-----------------------------------------------------------+ |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### UBER'S MATCHING FLOW: BOTH LOCKS NEEDED

```
+-------------------------------------------------------------------------+
|                    COMPLETE MATCHING SEQUENCE                           |
|                                                                         |
|  When a ride request comes in, both locks are used at different        |
|  stages to prevent different race conditions:                          |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |  STEP 1: Prevent duplicate processing of same ride             |   |
|  |  -------------------------------------------------              |   |
|  |  Lock: "lock:ride:123"                                         |   |
|  |  Why: If two servers both pick up this ride request,           |   |
|  |       only one should process it.                              |   |
|  |                                                                 |   |
|  |  STEP 2: Find nearby available drivers                         |   |
|  |  -------------------------------------                         |   |
|  |  No lock needed (read operation)                               |   |
|  |  Query Redis: GEORADIUS drivers:sf 5km                        |   |
|  |  Get list: [D1, D2, D3, D4, D5]                                |   |
|  |                                                                 |   |
|  |  STEP 3: Select best driver (D1)                               |   |
|  |  -------------------------------                               |   |
|  |  No lock needed (calculation)                                  |   |
|  |  Consider: ETA, rating, acceptance rate                       |   |
|  |                                                                 |   |
|  |  STEP 4: Reserve the driver                                    |   |
|  |  -----------------------------                                 |   |
|  |  Lock: "lock:driver:D1"                                       |   |
|  |  Why: Another ride might be trying to assign D1 too.          |   |
|  |                                                                 |   |
|  |  While holding driver lock:                                    |   |
|  |  - Check D1 is still available (not assigned elsewhere)       |   |
|  |  - If yes: Mark D1 as "reserved for ride 123"                 |   |
|  |  - If no: Release lock, try D2                                |   |
|  |                                                                 |   |
|  |  STEP 5: Update ride with assigned driver                      |   |
|  |  -------------------------------------                         |   |
|  |  Already holding ride lock from Step 1                        |   |
|  |  UPDATE rides SET driver_id = D1, status = ACCEPTED           |   |
|  |                                                                 |   |
|  |  STEP 6: Release both locks                                    |   |
|  |  ------------------------                                      |   |
|  |  Release "lock:driver:D1"                                     |   |
|  |  Release "lock:ride:123"                                      |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  LOCK TIMELINE:                                                        |
|                                                                         |
|  Time ---------------------------------------------------------->      |
|                                                                         |
|  ride:123    ████████████████████████████████████████████             |
|              ^                                          ^              |
|              acquire                                    release        |
|                                                                         |
|  driver:D1               ███████████████████                           |
|                          ^                 ^                            |
|                          acquire           release                      |
|                                                                         |
|  The ride lock is held longer (covers the whole operation).            |
|  The driver lock is held briefly (just for reservation).              |
|                                                                         |
+-------------------------------------------------------------------------+
```

**COMMON MISTAKES AND HOW TO AVOID THEM:**

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MISTAKE 1: Locking too broadly                                        |
|  ---------------------------------                                     |
|  Lock "lock:all_drivers" when assigning one driver.                   |
|  > Only one ride can be matched at a time globally!                   |
|  > System throughput: 1 ride per lock duration                        |
|                                                                         |
|  FIX: Lock only "lock:driver:D1" (the specific driver)               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  MISTAKE 2: Locking the wrong resource                                 |
|  ------------------------------------                                  |
|  Two riders want D1. You lock each rider's ride.                      |
|  > Both locks acquired, both check D1, both assign D1!               |
|  > Race condition not prevented                                       |
|                                                                         |
|  FIX: Lock the DRIVER (the shared resource), not the rides           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  MISTAKE 3: Not holding lock during check-and-update                  |
|  -----------------------------------------------------                 |
|  1. Lock driver:D1                                                    |
|  2. Check if D1 available > Yes                                       |
|  3. Release lock                                                      |
|  4. Update D1 to assigned                                             |
|                                                                         |
|  Between steps 3 and 4, someone else could assign D1!                 |
|                                                                         |
|  FIX: Hold lock until AFTER the update is committed                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  MISTAKE 4: Inconsistent lock ordering (deadlock)                     |
|  ------------------------------------------------                     |
|  Thread A: Lock ride:123, then driver:D1                              |
|  Thread B: Lock driver:D1, then ride:123                              |
|  > Deadlock!                                                          |
|                                                                         |
|  FIX: Always lock in same order (e.g., driver before ride)           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### OPTIMISTIC VS PESSIMISTIC LOCKING: WHICH IS OUR REDIS LOCK?

The Redis SETNX distributed lock is PESSIMISTIC locking. Let's understand
the difference and when to use each.

```
+-------------------------------------------------------------------------+
|                    TWO LOCKING PHILOSOPHIES                             |
|                                                                         |
|  PESSIMISTIC LOCKING: "Assume conflict. Lock first, then work."        |
|  ------------------------------------------------------------          |
|  Philosophy: "Someone will definitely try to touch my data while       |
|              I'm working. I'll block them upfront."                    |
|                                                                         |
|  Flow:                                                                 |
|  1. ACQUIRE LOCK first                                                 |
|  2. Read data                                                          |
|  3. Do work                                                            |
|  4. Write data                                                         |
|  5. RELEASE LOCK                                                       |
|                                                                         |
|  Others who try to access: BLOCKED until lock released                |
|                                                                         |
|  ===================================================================   |
|                                                                         |
|  OPTIMISTIC LOCKING: "Assume no conflict. Check at commit time."       |
|  ------------------------------------------------------------          |
|  Philosophy: "Conflicts are rare. I'll work freely and check if        |
|              anyone changed my data only when I'm ready to save."      |
|                                                                         |
|  Flow:                                                                 |
|  1. Read data (including a VERSION number)                             |
|  2. Do work (NO LOCK held)                                             |
|  3. When ready to write: "Update WHERE version = my_version"           |
|  4. If 0 rows affected: Someone else modified! Retry.                  |
|                                                                         |
|  Others who try to access: NOT blocked, can work in parallel          |
|                                                                         |
+-------------------------------------------------------------------------+
```

**THE REDIS SETNX LOCK IS PESSIMISTIC:**

```
+-------------------------------------------------------------------------+
|                    REDIS SETNX = PESSIMISTIC LOCK                       |
|                                                                         |
|  Our distributed lock using Redis SET NX (Set if Not eXists):          |
|                                                                         |
|  1. SET lock:driver:D1 "token" NX EX 30   < ACQUIRE LOCK FIRST         |
|  2. If acquired:                                                       |
|     - Read driver status                                               |
|     - Check availability                                               |
|     - Assign to ride                                                   |
|     - Update status                                                    |
|  3. DEL lock:driver:D1                    < RELEASE LOCK               |
|                                                                         |
|  This is PESSIMISTIC because:                                          |
|  * We lock BEFORE doing any work                                      |
|  * Other servers are BLOCKED from acquiring the same lock             |
|  * We assume conflicts WILL happen (high-contention resource)          |
|                                                                         |
|  WHY PESSIMISTIC FOR DRIVER ASSIGNMENT?                                |
|  * Drivers are HIGH-CONTENTION resources                              |
|  * Many rides might want the same driver simultaneously               |
|  * Retry cost is high (wasted matching computation)                   |
|  * We EXPECT conflicts, so block them upfront                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMPARISON: WHEN TO USE EACH

```
+-------------------------------------------------------------------------+
|                                                                         |
|  +----------------+----------------------+------------------------+    |
|  | Aspect         | Pessimistic          | Optimistic             |    |
|  +----------------+----------------------+------------------------+    |
|  | Philosophy     | Assume conflict      | Assume no conflict     |    |
|  +----------------+----------------------+------------------------+    |
|  | When to lock   | BEFORE reading       | Don't lock at all      |    |
|  +----------------+----------------------+------------------------+    |
|  | Conflict check | Upfront (blocked)    | At commit time         |    |
|  +----------------+----------------------+------------------------+    |
|  | On conflict    | Others wait          | Retry your work        |    |
|  +----------------+----------------------+------------------------+    |
|  | Concurrency    | Lower                | Higher                 |    |
|  +----------------+----------------------+------------------------+    |
|  | Latency        | Blocked waiting      | Retry if conflict      |    |
|  +----------------+----------------------+------------------------+    |
|  | Best for       | High contention      | Low contention         |    |
|  |                | Expensive retries    | Cheap retries          |    |
|  |                | Short operations     | Read-heavy workloads   |    |
|  +----------------+----------------------+------------------------+    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### UBER'S APPROACH: HYBRID (BOTH STRATEGIES)

```
+-------------------------------------------------------------------------+
|                    UBER USES BOTH STRATEGIES                            |
|                                                                         |
|  PESSIMISTIC LOCK (Redis SETNX):                                       |
|  ---------------------------------                                     |
|  Used for: Driver assignment, ride matching                            |
|                                                                         |
|  Why: High contention. Many requests might want the same driver.       |
|       Blocking is better than wasted matching work.                    |
|                                                                         |
|  Flow:                                                                 |
|  1. SET lock:driver:D1 NX EX 30  < Block other servers                |
|  2. Check driver available                                             |
|  3. Assign driver                                                      |
|  4. Release lock                                                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  OPTIMISTIC LOCK (Version Column in Database):                         |
|  -----------------------------------------------                       |
|  Used for: Ride status updates, user profile updates                  |
|                                                                         |
|  Why: Lower contention. Most updates don't conflict.                  |
|       Higher concurrency, no blocking.                                |
|                                                                         |
|  Flow:                                                                 |
|  1. SELECT * FROM rides WHERE id = 123  > version = 5                 |
|  2. Do some work (calculate fare, etc.)                               |
|  3. UPDATE rides SET fare = 20, version = 6                           |
|     WHERE id = 123 AND version = 5                                    |
|  4. If 0 rows affected > Someone else updated! Retry.                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  COMBINING BOTH (Defense in Depth):                                    |
|  -----------------------------------                                   |
|  For critical operations like driver assignment:                       |
|                                                                         |
|  Layer 1: Pessimistic (Redis lock on driver)                          |
|           > Blocks most concurrent attempts                           |
|                                                                         |
|  Layer 2: Optimistic (Database WHERE clause)                          |
|           > Catches anything that slipped through                     |
|           UPDATE drivers SET current_ride = 123                       |
|           WHERE id = D1 AND current_ride IS NULL                      |
|           > If another assignment happened, 0 rows affected           |
|                                                                         |
|  WHY BOTH?                                                             |
|  * Redis lock might fail (network partition, Redis down)              |
|  * Database is the ULTIMATE source of truth                           |
|  * Belt and suspenders approach                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### OPTIMISTIC LOCKING IN DETAIL (HOW VERSION COLUMN WORKS)

```
+-------------------------------------------------------------------------+
|                    VERSION-BASED OPTIMISTIC LOCKING                     |
|                                                                         |
|  SCHEMA:                                                               |
|  +------------------------------------------------------------------+  |
|  |  id    |  status     |  driver_id  |  fare    |  version        |  |
|  +--------+-------------+-------------+----------+-----------------+  |
|  |  123   |  ACCEPTED   |  D1         |  NULL    |  5              |  |
|  +------------------------------------------------------------------+  |
|                                                                         |
|  SCENARIO: Two servers try to update ride 123's fare                   |
|                                                                         |
|  SERVER A                          SERVER B                            |
|  ---------                         ---------                           |
|  T1: SELECT ... > version = 5      T2: SELECT ... > version = 5       |
|  T3: Calculate fare = $18          T4: Calculate fare = $20           |
|  T5: UPDATE ... SET fare=18,       T6: UPDATE ... SET fare=20,        |
|      version=6 WHERE version=5         version=6 WHERE version=5      |
|      > 1 row affected Y                > 0 rows affected X            |
|                                        (version already changed!)     |
|                                                                         |
|  RESULT:                                                               |
|  * Server A's update committed (fare = $18, version = 6)              |
|  * Server B detected conflict, must retry with fresh data             |
|  * No data corruption!                                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WHY "OPTIMISTIC"?                                                     |
|  * We didn't block Server B from reading                              |
|  * We HOPED there wouldn't be a conflict                              |
|  * We only checked at commit time                                     |
|  * If conflict happens, we deal with it then (retry)                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  ALTERNATIVE: Use timestamp instead of version                         |
|                                                                         |
|  UPDATE rides SET fare = 18, updated_at = NOW()                       |
|  WHERE id = 123 AND updated_at = '2024-01-15 10:30:00'               |
|                                                                         |
|  Works the same way, but version numbers are cleaner.                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CHOOSING BETWEEN THEM: DECISION GUIDE

```
+-------------------------------------------------------------------------+
|                    WHEN TO USE WHICH?                                   |
|                                                                         |
|  USE PESSIMISTIC (Redis SETNX) WHEN:                                   |
|  ------------------------------------                                  |
|  Y High contention (many requests for same resource)                  |
|  Y Retry is expensive (e.g., re-running matching algorithm)           |
|  Y Critical section is short (don't hold lock long)                   |
|  Y You need to guarantee only one proceeds                            |
|                                                                         |
|  Examples in Uber:                                                     |
|  * Driver assignment (many rides want popular drivers)                |
|  * Payment processing (can't have parallel charges)                   |
|  * Ride matching (expensive computation, don't waste it)              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  USE OPTIMISTIC (Version Column) WHEN:                                 |
|  ------------------------------------                                  |
|  Y Low contention (conflicts are rare)                                |
|  Y Retry is cheap (just read and try again)                          |
|  Y Read-heavy workload (many reads, few writes)                       |
|  Y Long-running operations (don't want to block others)               |
|                                                                         |
|  Examples in Uber:                                                     |
|  * User profile updates (user updates their own profile)              |
|  * Rating submission (one rider rates one ride)                       |
|  * Ride status updates (most updates are sequential)                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  USE BOTH (Defense in Depth) WHEN:                                     |
|  --------------------------------                                      |
|  Y Data integrity is CRITICAL (payments, driver assignment)           |
|  Y Distributed lock might fail (network issues)                       |
|  Y You need guarantees at multiple levels                             |
|                                                                         |
|  Pattern:                                                              |
|  1. Pessimistic lock (Redis) - first line of defense                  |
|  2. Optimistic lock (DB WHERE) - backup verification                  |
|  3. Unique constraint (DB) - last resort protection                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

COMPOSITE LOCKS — WHEN YOU NEED MULTIPLE RESOURCES:

```
+-------------------------------------------------------------------------+
|                    LOCKING MULTIPLE RESOURCES                           |
|                                                                         |
|  Sometimes an operation needs BOTH ride AND driver locked.             |
|                                                                         |
|  DANGER: DEADLOCK                                                      |
|                                                                         |
|  Server A: Lock ride:123, then lock driver:D1                         |
|  Server B: Lock driver:D1, then lock ride:123                         |
|                                                                         |
|  Server A holds ride:123, waiting for driver:D1                       |
|  Server B holds driver:D1, waiting for ride:123                       |
|  > DEADLOCK! Neither can proceed.                                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTION: CONSISTENT LOCK ORDERING                                    |
|                                                                         |
|  RULE: Always acquire locks in the SAME order.                        |
|                                                                         |
|  Convention: Alphabetical by lock key                                  |
|  * "driver:D1" comes before "ride:123"                                |
|  * ALWAYS lock driver first, then ride                                |
|                                                                         |
|  Server A: Lock driver:D1, then lock ride:123                         |
|  Server B: Lock driver:D1, then lock ride:123                         |
|                                                                         |
|  Now only one can get driver:D1 first. No deadlock possible.          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  ALTERNATIVE: SINGLE COMPOSITE LOCK                                    |
|                                                                         |
|  Instead of two locks, use one that covers both:                       |
|  Lock key: "lock:match:{ride_id}:{driver_id}"                         |
|                                                                         |
|  Example: "lock:match:123:D1"                                         |
|                                                                         |
|  This works when the ride-driver pair is known upfront.               |
|                                                                         |
+-------------------------------------------------------------------------+
```

UBER'S ACTUAL LOCKING STRATEGY:

```
+-------------------------------------------------------------------------+
|                    WHAT UBER LOCKS                                      |
|                                                                         |
|  PHASE 1: MATCHING (Finding a driver)                                  |
|  -------------------------------------                                 |
|  Lock: "lock:ride:{ride_id}"                                          |
|  Why: Prevent duplicate matching for the same ride                    |
|  Granularity: ROW (one ride)                                          |
|                                                                         |
|  PHASE 2: DRIVER ASSIGNMENT (Reserving the driver)                     |
|  --------------------------------------------------                    |
|  Lock: "lock:driver:{driver_id}"                                      |
|  Why: Prevent same driver assigned to multiple rides                  |
|  Granularity: ROW (one driver)                                        |
|                                                                         |
|  PHASE 3: PAYMENT (Charging the rider)                                 |
|  --------------------------------------                                |
|  Lock: "lock:payment:{idempotency_key}"                               |
|  Why: Prevent duplicate charges                                       |
|  Granularity: One specific payment attempt                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PRINCIPLE: Lock the SMALLEST unit that ensures correctness.           |
|                                                                         |
|  * Don't lock "all rides" when you only need "ride 12345"             |
|  * Don't lock "all drivers" when you only need "driver D1"            |
|  * Finer granularity = more parallel operations = higher throughput   |
|                                                                         |
+-------------------------------------------------------------------------+
```

**DATABASE ROW-LEVEL LOCKS (PESSIMISTIC LOCKING):**

```
+-------------------------------------------------------------------------+
|                    SELECT FOR UPDATE                                    |
|                                                                         |
|  Besides distributed locks (Redis), databases have built-in row locks. |
|                                                                         |
|  PESSIMISTIC LOCKING:                                                  |
|  SELECT * FROM rides WHERE ride_id = 12345 FOR UPDATE;                 |
|                                                                         |
|  This:                                                                 |
|  1. Reads the row                                                      |
|  2. Acquires an EXCLUSIVE lock on that row                            |
|  3. Other transactions trying to lock this row will WAIT              |
|  4. Lock released when transaction commits/rollbacks                   |
|                                                                         |
|  WHEN TO USE:                                                          |
|  * When you're DEFINITELY going to update the row                     |
|  * When conflicts are COMMON (high contention)                        |
|  * When you need the lock to span multiple queries                    |
|                                                                         |
|  DOWNSIDE:                                                             |
|  * Holds database connection while locked                              |
|  * Can cause connection pool exhaustion under high load               |
|  * Doesn't work across multiple databases                              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  OPTIMISTIC LOCKING (Alternative):                                     |
|                                                                         |
|  Don't lock upfront. Instead, check at write time:                    |
|                                                                         |
|  UPDATE rides                                                          |
|  SET driver_id = 'D1', version = version + 1                          |
|  WHERE ride_id = 12345 AND version = 5;                               |
|                                                                         |
|  If version changed (someone else updated), 0 rows affected.           |
|  Application retries with fresh data.                                  |
|                                                                         |
|  WHEN TO USE:                                                          |
|  * Conflicts are RARE (low contention)                                |
|  * Don't want to hold locks                                           |
|  * Read-heavy workloads                                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### FENCING TOKENS: THE ULTIMATE SAFETY NET

**THE PROBLEM RESTATED:**
No matter which distributed lock we use, there's a fundamental problem:
A client can BELIEVE it holds the lock when it actually doesn't.

```
+-------------------------------------------------------------------------+
|                    THE STALE LOCK HOLDER PROBLEM                        |
|                                                                         |
|  Server A               Lock Service              Database             |
|     |                       |                        |                  |
|     |-- Acquire lock ------>|                        |                  |
|     |<-- Lock granted ------|                        |                  |
|     |   (token = 42)        |                        |                  |
|     |                       |                        |                  |
|     |   [A pauses: GC]      |                        |                  |
|     |   .....               |                        |                  |
|     |   .....               |-- Lock expires ------->|                  |
|     |   .....               |                        |                  |
|     |   .....               |                        |                  |
|     |                       |                        |                  |
|  Server B -- Acquire lock -->|                       |                  |
|     |<-- Lock granted ------|  (token = 43)         |                  |
|     |                       |                        |                  |
|     |                       |                        |                  |
|     |-- Write (token 43) ---------------------------->| Y Accepted     |
|     |                       |                        |                  |
|     |   [A resumes]         |                        |                  |
|     |                       |                        |                  |
|     |-- Write (token 42) ---------------------------->| Y Accepted!    |
|     |                       |                        |  CORRUPTION!    |
|                                                                         |
|  Both writes succeeded. A's stale write corrupted B's data.            |
|                                                                         |
+-------------------------------------------------------------------------+
```

SOLUTION: FENCING TOKEN

```
+-------------------------------------------------------------------------+
|                    FENCING TOKEN PRINCIPLE                              |
|                                                                         |
|  CONCEPT:                                                              |
|  Every lock acquisition gets a MONOTONICALLY INCREASING number.        |
|  The database REJECTS writes with old tokens.                          |
|                                                                         |
|  Token 42 > Token 43 > Token 44 > ...                                  |
|                                                                         |
|  Each new lock holder gets a HIGHER token than all previous holders.   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  HOW THE DATABASE USES IT:                                             |
|                                                                         |
|  Every write includes the fencing token.                               |
|  The database tracks the highest token it has seen.                    |
|  It REJECTS any write with a token ≤ the highest seen.                |
|                                                                         |
|  Server B writes: token = 43 > DB accepts, records max_token = 43     |
|  Server A writes: token = 42 > DB rejects (42 < 43)                   |
|                                                                         |
|  A's stale write is BLOCKED, even though A doesn't know the lock      |
|  expired.                                                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

**HOW FENCING TOKENS ARE GENERATED:**

```
+-------------------------------------------------------------------------+
|                    TOKEN GENERATION APPROACHES                          |
|                                                                         |
|  APPROACH 1: Atomic Counter in Lock Service                            |
|  -----------------------------------------                              |
|  Lock service maintains a counter per resource.                        |
|  Each lock acquisition increments and returns the counter.             |
|                                                                         |
|  APPROACH 2: Zookeeper Sequential Nodes                                |
|  --------------------------------------                                |
|  Zookeeper's sequential znodes are already monotonically numbered.     |
|  /locks/ride_12345/lock-0000000042 > Token is 42                       |
|                                                                         |
|  APPROACH 3: etcd Revision Numbers                                     |
|  ---------------------------------                                     |
|  Every etcd write returns a revision number that only increases.       |
|  Use this as the fencing token.                                        |
|                                                                         |
|  APPROACH 4: Redis INCR                                                |
|  ----------------------                                                |
|  Before acquiring lock, atomically increment a counter:                |
|  INCR fencing:ride_12345 > Returns next token                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

**IMPLEMENTING IN THE DATABASE:**

```
+-------------------------------------------------------------------------+
|                    DATABASE-SIDE FENCING                                |
|                                                                         |
|  Table schema includes a token column:                                 |
|                                                                         |
|  rides                                                                 |
|  +----------------------------------------------------------+          |
|  |  ride_id    |  driver_id  |  status   |  fence_token     |          |
|  +-------------+-------------+-----------+------------------+          |
|  |  12345      |  NULL       |  PENDING  |  41              |          |
|  +----------------------------------------------------------+          |
|                                                                         |
|  UPDATE rides                                                          |
|  SET driver_id = 'D1', fence_token = 43                               |
|  WHERE ride_id = '12345' AND fence_token < 43;                        |
|                                                                         |
|  * If current token is 41, update succeeds (41 < 43)                  |
|  * If current token is 43+, update fails (no rows affected)           |
|                                                                         |
|  The WHERE clause ensures only FRESHER tokens can write.               |
|                                                                         |
+-------------------------------------------------------------------------+
```

**WHY THIS SOLVES THE PROBLEM:**

```
+-------------------------------------------------------------------------+
|                    FENCING IN ACTION                                    |
|                                                                         |
|  Same scenario, but with fencing:                                      |
|                                                                         |
|  T=0:   A acquires lock with token = 42                               |
|  T=1:   A pauses (GC)                                                 |
|  T=31:  Lock expires                                                  |
|  T=32:  B acquires lock with token = 43                               |
|  T=33:  B writes with token 43 > DB accepts, sets fence_token = 43   |
|  T=40:  A resumes, tries to write with token 42                       |
|  T=41:  DB rejects (42 < 43) > 0 rows affected                        |
|         A's code sees 0 rows, knows something went wrong              |
|                                                                         |
|  DATA INTEGRITY PRESERVED!                                             |
|                                                                         |
|  Even though A didn't know the lock expired, the database             |
|  protected the data.                                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

UBER'S DEFENSE-IN-DEPTH STRATEGY:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LAYER 1: Distributed Lock (Redis)                                     |
|  ----------------------------------                                    |
|  Fast, prevents MOST concurrent modifications.                         |
|  99.9% of race conditions stopped here.                                |
|                                                                         |
|  LAYER 2: Verify Before Write                                          |
|  ----------------------------                                          |
|  After acquiring lock, check the current state in DB.                  |
|  "Is this driver still available?" "Is this ride still pending?"      |
|                                                                         |
|  LAYER 3: Optimistic Locking (WHERE clause)                            |
|  ----------------------------------------                              |
|  UPDATE rides SET driver = ? WHERE ride_id = ? AND status = 'PENDING' |
|  If status changed, 0 rows affected > operation fails safely.          |
|                                                                         |
|  LAYER 4: Fencing Token                                                |
|  ----------------------                                                |
|  Last line of defense against stale lock holders.                      |
|  Database rejects writes with old tokens.                              |
|                                                                         |
|  PRINCIPLE: Don't trust any single layer. Defense in depth.            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SUMMARY: WHICH LOCK TO USE WHEN?

```
+-------------------------------------------------------------------------+
|                    DISTRIBUTED LOCK SELECTION                           |
|                                                                         |
|  +-----------+----------+----------+-----------+-------------------+   |
|  | Approach  | Latency  | Guaranty | Complexity| Best For          |   |
|  +-----------+----------+----------+-----------+-------------------+   |
|  | Database  | 5-50ms   | Strong   | Low       | Low throughput,   |   |
|  |           |          |          |           | already have DB   |   |
|  +-----------+----------+----------+-----------+-------------------+   |
|  | Zookeeper | 5-20ms   | Strong   | High      | Need strong       |   |
|  |           |          | (CP)     |           | ordering, Kafka   |   |
|  +-----------+----------+----------+-----------+-------------------+   |
|  | Redis     | <1ms     | Weak     | Low       | High throughput,  |   |
|  |           |          | (AP)     |           | verify in DB  Y   |   |
|  +-----------+----------+----------+-----------+-------------------+   |
|  | etcd      | 5-10ms   | Strong   | Medium    | Kubernetes-style  |   |
|  |           |          | (CP)     |           | coordination      |   |
|  +-----------+----------+----------+-----------+-------------------+   |
|                                                                         |
|  FOR UBER:                                                             |
|  > Redis lock for speed                                                |
|  > Verify in database before write                                     |
|  > Fencing tokens for safety net                                       |
|  > Database optimistic locking as final check                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 4.5 COMPLETE MATCHING SEQUENCE

Let's trace a complete ride request with locking:

```
+-------------------------------------------------------------------------+
|                    COMPLETE MATCHING SEQUENCE                           |
|                                                                         |
|  Rider         Matching        Redis         Postgres       Driver      |
|  App           Service         (lock/geo)    (rides DB)     App         |
|   |               |               |              |            |         |
|   |- Request ---->|               |              |            |         |
|   |  ride         |               |              |            |         |
|   |               |               |              |            |         |
|   |               |-- GEORADIUS ->|              |            |         |
|   |               |   (find nearby drivers)      |             |         |
|   |               |<-- [D1,D2,D3] -|             |            |         |
|   |               |               |              |            |         |
|   |               |-- GET driver details -------------------->|         |
|   |               |   (parallel ETA calls)       |             |         |
|   |               |<-- D1: 3min, D2: 5min ------------------  |         |
|   |               |               |              |            |         |
|   |               |   Select D1 (closest)        |             |         |
|   |               |               |              |            |         |
|   |               |-- SETNX ----->|              |            |         |
|   |               |   lock:ride:123              |             |         |
|   |               |<-- OK --------|              |            |         |
|   |               |   (lock acquired)            |             |         |
|   |               |               |              |            |         |
|   |               |-- Verify D1 still available ------------->|         |
|   |               |<-- Available -----------------------------|         |
|   |               |               |              |            |         |
|   |               |-- UPDATE rides SET driver_id = D1 ------->|         |
|   |               |   WHERE ride_id = 123 AND status = PENDING|         |
|   |               |<-- 1 row affected -----------|            |         |
|   |               |               |              |            |         |
|   |               |-- Release lock >|            |            |         |
|   |               |               |              |            |         |
|   |               |-- Push ride request via WebSocket ------->|         |
|   |               |               |              |            |         |
|   |               |               |              |<-- Accept -|         |
|   |               |               |              |            |         |
|   |<-- Match! ----|               |              |            |         |
|   |   D1, ETA 3m  |               |              |            |         |
|   |               |               |              |            |         |
+-------------------------------------------------------------------------+
```

Key points in this flow:

1. LOCK BEFORE WRITE
We acquire the lock before modifying the database. This prevents
race conditions.

2. VERIFY AFTER LOCK
Even after acquiring the lock, we verify the driver is still available.
They might have gone offline or accepted another ride.

3. DATABASE AS SOURCE OF TRUTH
The Redis lock is for coordination. The database is the source of truth.
The UPDATE uses a WHERE clause to ensure atomicity.

4. LOCK TIMEOUT
The lock has a 30-second TTL. If our server crashes while holding the
lock, it will auto-release, preventing deadlocks.

## PART 5: ETA PREDICTION — ACCURACY MATTERS

"Your driver will arrive in 3 minutes." This simple message drives countless
user decisions. If we say 3 minutes and it takes 10, users lose trust. If
we say 10 and it takes 3, they might have chosen a different option. ETA
accuracy is critical to user experience.

### 5.1 WHY ETA IS HARD

Calculating travel time seems simple: distance ÷ speed. But real-world
travel is far more complex:

- ROAD NETWORK: You can't travel in straight lines. Roads have turns,
one-ways, and varying speed limits.

- TRAFFIC: A 2-mile drive can take 5 minutes or 30 minutes depending on
traffic conditions.

- TIME PATTERNS: Rush hour traffic is predictable. But unexpected events
(accidents, construction) are not.

- LOCAL KNOWLEDGE: Experienced drivers know shortcuts that GPS doesn't.

- PICKUP COMPLEXITY: Finding the rider at an airport or stadium takes
longer than a residential street.

### 5.2 ROAD NETWORK GRAPH

We model the road network as a weighted directed graph:

```
+-------------------------------------------------------------------------+
|                       ROAD NETWORK GRAPH                                |
|                                                                         |
|  Nodes: Intersections                                                  |
|  Edges: Road segments                                                  |
|  Edge Weight: Travel time (not distance!)                              |
|                                                                         |
|                    2 min                                               |
|            A ---------------> B                                        |
|            |                  |                                        |
|      3 min |                  | 1 min                                  |
|            |                  |                                        |
|            v        4 min     v                                        |
|            C ---------------> D                                        |
|                                                                         |
|  Path A > D options:                                                   |
|  * A > B > D: 2 + 1 = 3 min                                           |
|  * A > C > D: 3 + 4 = 7 min                                           |
|                                                                         |
|  Edge weight varies by:                                                |
|  * Base travel time (distance ÷ speed limit)                          |
|  * Current traffic (from live driver data)                            |
|  * Historical patterns (weekday 8am = rush hour)                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

We use OpenStreetMap (OSM) data for the base road network, enriched with
Uber's own data from millions of trips.

### 5.3 ROUTING ALGORITHMS

DIJKSTRA'S ALGORITHM:
The classic shortest-path algorithm. From a source node, it explores
outward, always visiting the closest unvisited node.

Time Complexity: O((V + E) log V) where V = vertices, E = edges
For a city with 1 million intersections, this takes ~100ms per query.
That's too slow for real-time matching where we need ETAs for 20 drivers.

A* ALGORITHM:
An improvement over Dijkstra that uses a heuristic (straight-line distance
to destination) to guide the search. It expands fewer nodes by prioritizing
paths that "look promising."

Time Complexity: O(E) in best case, but typically 2-10x faster than Dijkstra
For our city, ~20-50ms per query. Better, but still not fast enough.

**CONTRACTION HIERARCHIES (CH):**
The key insight: most long-distance routes use highways. We can precompute
shortcuts for these common paths.

```
+-------------------------------------------------------------------------+
|                    CONTRACTION HIERARCHIES                              |
|                                                                         |
|  Original graph:                                                       |
|  A --- B --- C --- D --- E                                            |
|        |           |                                                   |
|        +--- F -----+                                                   |
|                                                                         |
|  After contraction (shortcuts added):                                  |
|  A --------------------------- E  (shortcut: A>E in 1 hop)            |
|  A --- B --- C --- D --- E                                            |
|        |           |                                                   |
|        +--- F -----+                                                   |
|                                                                         |
|  Preprocessing: O(V × E × log V) - done once, takes hours             |
|  Query time: O(log V) - sub-millisecond!                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

Uber uses Contraction Hierarchies with dynamic edge weights. The structure
is precomputed, but edge weights are updated in real-time based on traffic.

### 5.4 MACHINE LEARNING FOR ETA

Graph algorithms give us route-based estimates. ML gives us trip-based
predictions that account for factors the graph doesn't capture.

```
+-------------------------------------------------------------------------+
|                    ML ETA PREDICTION                                    |
|                                                                         |
|  Features (inputs to the model):                                       |
|                                                                         |
|  ROUTE FEATURES:                                                       |
|  * Distance (from routing algorithm)                                   |
|  * Number of turns                                                     |
|  * Road types (highway %, local road %)                               |
|  * Number of traffic signals                                          |
|                                                                         |
|  TEMPORAL FEATURES:                                                    |
|  * Hour of day (one-hot encoded)                                      |
|  * Day of week                                                        |
|  * Is holiday?                                                        |
|  * Minutes until rush hour                                            |
|                                                                         |
|  REAL-TIME FEATURES:                                                   |
|  * Current speed on route segments (from driver GPS)                  |
|  * Recent trip durations on similar routes                            |
|  * Weather (rain increases travel time 10-30%)                        |
|                                                                         |
|  LOCATION FEATURES:                                                    |
|  * Pickup type (street, airport, stadium)                             |
|  * Historical pickup time at this location                            |
|  * H3 cell embeddings (learned representations of areas)              |
|                                                                         |
|  Model: Gradient Boosted Trees (XGBoost)                              |
|  Training data: Billions of historical trips                          |
|  Output: Predicted trip duration in seconds                           |
|                                                                         |
|  Accuracy: 90% of predictions within 2 minutes of actual             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 6: SURGE PRICING — BALANCING SUPPLY AND DEMAND

At 2 AM on New Year's Eve, everyone wants a ride home. There aren't enough
drivers. What do you do?

Surge pricing is Uber's market-based solution: raise prices to reduce demand
and incentivize more drivers to get on the road.

### 6.1 THE ECONOMICS OF SURGE

```
+-------------------------------------------------------------------------+
|                    SUPPLY-DEMAND DYNAMICS                               |
|                                                                         |
|  Normal conditions:                                                    |
|  * Demand: 1000 rides/hour                                            |
|  * Supply: 1200 available drivers                                     |
|  * Wait time: 3 minutes average                                       |
|  * Price multiplier: 1.0x (no surge)                                  |
|                                                                         |
|  Concert lets out:                                                     |
|  * Demand: 5000 rides/hour (5x normal)                                |
|  * Supply: 1200 available drivers (unchanged)                         |
|  * Wait time: 15+ minutes (if no intervention)                        |
|                                                                         |
|  With surge pricing (2.5x):                                           |
|  * Demand drops to: 2000 rides/hour (price-sensitive users wait)      |
|  * Supply increases to: 1800 drivers (attracted by higher fares)      |
|  * Wait time: 5 minutes                                               |
|                                                                         |
|  Surge achieves two goals:                                             |
|  1. DEMAND REDUCTION: Higher prices discourage marginal trips         |
|  2. SUPPLY INCREASE: Higher earnings attract more drivers             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 6.2 ZONE-BASED PRICING WITH H3

We don't calculate surge for every coordinate. We divide the city into
hexagonal zones using H3 and calculate surge per zone.

### CONCEPT: DYNAMIC PRICING ECONOMICS

PRINCIPLE: Price Elasticity of Demand
When price increases, demand decreases. The relationship:
- Some trips are INELASTIC (business travel, emergencies) - will pay surge
- Some trips are ELASTIC (casual outings) - will wait or take transit

PRINCIPLE: Market Clearing Price
Find the price where supply meets demand. If 1000 people want rides but
only 500 drivers available, price increases until only 500 people are
willing to pay, matching supply.

### 6.3 SURGE CALCULATION: HOW IT WORKS

### THE CORE FORMULA

```
+-------------------------------------------------------------------------+
|                    SURGE CALCULATION PRINCIPLE                          |
|                                                                         |
|  STEP 1: MEASURE DEMAND AND SUPPLY                                     |
|                                                                         |
|  For each H3 zone (hexagonal cell ~100m):                              |
|                                                                         |
|  DEMAND = Number of ride requests in last 5 minutes                    |
|  SUPPLY = Number of available drivers currently in zone               |
|                                                                         |
|  Example: Downtown SF, Friday 6 PM                                     |
|  * Demand: 150 ride requests in last 5 min                             |
|  * Supply: 50 available drivers                                        |
|  * Ratio = 150 / 50 = 3.0                                              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  STEP 2: CONVERT RATIO TO MULTIPLIER                                   |
|                                                                         |
|  The surge function is PIECEWISE LINEAR (not exponential):             |
|                                                                         |
|  +----------------------------------------------------------------+    |
|  | Demand/Supply Ratio | Surge Multiplier | What It Means         |    |
|  +---------------------+------------------+-----------------------+    |
|  | < 1.0               | 1.0x             | Supply exceeds demand |    |
|  | 1.0 - 2.0           | 1.0x - 1.5x      | Light imbalance       |    |
|  | 2.0 - 4.0           | 1.5x - 2.5x      | Moderate shortage     |    |
|  | > 4.0               | 2.5x - 4.0x      | Severe shortage       |    |
|  | (capped at 4.0x)    |                  |                       |    |
|  +----------------------------------------------------------------+    |
|                                                                         |
|  VISUAL: SURGE CURVE                                                   |
|                                                                         |
|  Surge                                                                 |
|  4.0x - - - - - - - - - - - - - - - - - - - - - - - - - - - (cap)   |
|       |                                            ///                 |
|  2.5x -                                        ///                     |
|       |                              /////////                         |
|  1.5x -                    /////////                                   |
|       |          /////////                                             |
|  1.0x - - - - - -                                                      |
|       +-----+-----+-----+-----+-----+-----------------> Ratio          |
|             1     2     3     4     5                                  |
|                                                                         |
|  WHY PIECEWISE LINEAR?                                                 |
|  * Gradual increase (not jarring jumps)                               |
|  * Capped at 4x (to prevent extreme pricing)                          |
|  * Easy to explain to users ("demand is 2x supply")                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHY ZONES? (NOT PER-COORDINATE)

```
+-------------------------------------------------------------------------+
|                    ZONE-BASED PRICING RATIONALE                         |
|                                                                         |
|  OPTION A: Calculate surge for each rider's exact location            |
|  ---------------------------------------------------------              |
|  * 1000 ride requests/second × surge calculation = massive load       |
|  * Two riders 10 meters apart might see different prices              |
|  * Confusing UX ("I moved one block and price changed!")              |
|                                                                         |
|  OPTION B: Divide city into zones, calculate once per zone (Used)     |
|  ---------------------------------------------------------              |
|  * ~500 zones per city × 1 calc/zone/2min = 250 calculations/min     |
|  * All riders in same zone see same price (fair and predictable)        |
|  * Can cache aggressively (same zone = same surge)                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WHY H3 HEXAGONS (not squares)?                                         |
|                                                                         |
|  /\/\ /\ /\             +--+--+--+                                      |
| /  \/  \/  \            |  |  |  |                                      |
| \  /\  /\  /            +--+--+--+                                      |
|  \/  \/  \/             |  |  |  |                                      |
|  Hexagons               +--+--+--+                                      |
|                         Squares                                         |
|                                                                         |
|  * Hexagons have UNIFORM neighbor distance (6 equidistant neighbors)    |
|  * Squares have diagonal neighbors 41% farther than edge neighbors      |
|  * Better for "spread" calculations (surge bleeding between zones)      |
|                                                                         |
|  Zone resolution: ~100m × 100m (H3 resolution 9)                        |
|  * Small enough for local price differentiation                         |
|  * Large enough to have meaningful supply/demand counts                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CACHING STRATEGY

```
+-------------------------------------------------------------------------+
|                    SURGE CACHING ARCHITECTURE                           |
|                                                                         |
|  PROBLEM:                                                              |
|  * Calculating surge requires counting recent rides + drivers          |
|  * These are expensive queries (aggregations)                          |
|  * Can't do this for every fare estimate request                      |
|                                                                         |
|  SOLUTION: Two-Level Cache                                             |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |  Level 1: REDIS CACHE                                          |   |
|  |  Key: surge:{h3_zone_id}                                       |   |
|  |  Value: multiplier (e.g., 1.5)                                 |   |
|  |  TTL: 2 minutes                                                |   |
|  |                                                                 |   |
|  |  When rider requests fare estimate:                            |   |
|  |  1. Convert location to H3 zone                                |   |
|  |  2. Check Redis: GET surge:89283082837ffff                    |   |
|  |  3. If exists, return cached value (sub-millisecond)          |   |
|  |  4. If miss, calculate and cache                              |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |  Level 2: BACKGROUND CALCULATION                               |   |
|  |                                                                 |   |
|  |  A background job recalculates surge for ALL zones every       |   |
|  |  1-2 minutes. This ensures:                                    |   |
|  |  * Cache is always warm                                        |   |
|  |  * No rider ever triggers expensive calculation                |   |
|  |  * Surge is consistent across zone (no stale data)            |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

**SURGE SMOOTHING:**

To prevent jarring price jumps, we smooth surge transitions:
- Don't increase more than 0.5x per update
- Don't decrease more than 0.25x per update
- Average with neighboring zones to reduce edge effects

## PART 7: RIDE STATE MACHINE — MANAGING RIDE LIFECYCLE

A ride goes through multiple states from request to completion. Managing
these transitions correctly is critical — we can't have a ride stuck in
an invalid state or allow illegal transitions.

### 7.1 STATE TRANSITIONS

```
+-------------------------------------------------------------------------+
|                       RIDE STATE MACHINE                                |
|                                                                         |
|                          +-----------+                                 |
|                          | REQUESTED |                                 |
|                          +-----+-----+                                 |
|                                |                                        |
|              +-----------------+-----------------+                     |
|              v                 v                 v                     |
|       +-----------+     +-----------+     +-----------+               |
|       |  MATCHING |     | NO_DRIVER |     | CANCELLED |               |
|       +-----+-----+     +-----------+     +-----------+               |
|             |            (terminal)        (terminal)                  |
|             v                                                          |
|       +-----------+                                                    |
|       | ACCEPTED  |<---------------+                                  |
|       +-----+-----+                |                                  |
|             |                      | (driver cancels)                 |
|             v                      |                                  |
|       +-----------+         +------+----+                             |
|       | EN_ROUTE  |-------->|REASSIGNING|                             |
|       +-----+-----+         +-----------+                             |
|             |                                                          |
|             v                                                          |
|       +-----------+         +-----------+                             |
|       |  ARRIVED  |-------->|  NO_SHOW  |                             |
|       +-----+-----+         +-----------+                             |
|             |                (terminal)                                |
|             v                                                          |
|       +------------+                                                   |
|       |IN_PROGRESS |                                                   |
|       +-----+------+                                                   |
|             |                                                          |
|             v                                                          |
|       +-----------+        +-----------+                              |
|       | COMPLETED |------->|   PAID    |                              |
|       +-----------+        +-----------+                              |
|        (terminal)           (terminal)                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 7.2 SAGA PATTERN FOR DISTRIBUTED TRANSACTIONS

### THE PROBLEM: MULTI-SERVICE TRANSACTIONS

When a ride completes, multiple services must act together:

```
+-------------------------------------------------------------------------+
|                    RIDE COMPLETION REQUIRES                             |
|                                                                         |
|  Step 1: Ride Service      > Mark ride as COMPLETED                    |
|  Step 2: Pricing Service   > Calculate final fare                      |
|  Step 3: Payment Service   > Charge rider's card                       |
|  Step 4: Earnings Service  > Credit driver's balance                   |
|  Step 5: Notification Svc  > Send receipt email                        |
|  Step 6: Rating Service    > Request rating from rider                 |
|                                                                         |
|  Each step is a DIFFERENT microservice with its OWN database.          |
|                                                                         |
+-------------------------------------------------------------------------+
```

What if Step 3 fails (card declined)? We can't leave the system in an
inconsistent state where ride is marked COMPLETED but rider wasn't charged.

### WHY TRADITIONAL TRANSACTIONS DON'T WORK

```
+-------------------------------------------------------------------------+
|                    TWO-PHASE COMMIT (2PC) PROBLEMS                      |
|                                                                         |
|  In a monolith, we use database transactions:                          |
|                                                                         |
|  BEGIN TRANSACTION                                                     |
|    UPDATE rides SET status = 'COMPLETED' ...                           |
|    INSERT INTO payments ...                                            |
|    UPDATE driver_earnings ...                                          |
|  COMMIT                                                                |
|                                                                         |
|  Either ALL succeed or ALL rollback. ACID guarantees.                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  BUT in microservices, each service has its OWN database:              |
|                                                                         |
|  Ride Service      > PostgreSQL (rides DB)                             |
|  Payment Service   > PostgreSQL (payments DB)                          |
|  Earnings Service  > PostgreSQL (earnings DB)                          |
|                                                                         |
|  There's NO single transaction that spans all three!                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Two-Phase Commit (2PC) tries to solve this:                           |
|                                                                         |
|  PHASE 1 (Prepare): Coordinator asks all participants "Can you commit?"|
|  PHASE 2 (Commit):  If all say yes, coordinator says "Commit!"        |
|                                                                         |
|  PROBLEMS WITH 2PC:                                                    |
|                                                                         |
|  1. BLOCKING: All participants lock resources while waiting for        |
|     coordinator. If coordinator dies, everyone is stuck.               |
|                                                                         |
|  2. LATENCY: Round trips between coordinator and all participants.     |
|     At Uber's scale (1000+ txn/sec), this kills performance.          |
|                                                                         |
|  3. AVAILABILITY: Requires ALL participants to be available.           |
|     If Payment Service is down, entire transaction fails.              |
|                                                                         |
|  4. COUPLING: All services must speak the same 2PC protocol.          |
|     Tight coupling defeats the purpose of microservices.               |
|                                                                         |
|  VERDICT: 2PC doesn't scale. We need a different approach.            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### THE SAGA PATTERN: A DIFFERENT PHILOSOPHY

```
+-------------------------------------------------------------------------+
|                    SAGA CORE CONCEPT                                    |
|                                                                         |
|  PHILOSOPHY SHIFT:                                                     |
|                                                                         |
|  2PC says:  "All or nothing. If anything fails, rollback everything."  |
|  Saga says: "Do what you can. If something fails, UNDO what you did."  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  DEFINITION:                                                           |
|  A Saga is a sequence of LOCAL transactions where:                     |
|  * Each step commits to its OWN database (no locking across services)  |
|  * Each step has a COMPENSATION action (how to undo it)                |
|  * If a step fails, compensations run in REVERSE order                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  KEY PRINCIPLE: COMPENSATING TRANSACTIONS                              |
|                                                                         |
|  A compensation is NOT a database rollback.                            |
|  It's a NEW transaction that semantically reverses the effect.         |
|                                                                         |
|  Original Action           >  Compensation Action                      |
|  ---------------------------------------------------------------------  |
|  Charge $20 to card        >  Refund $20 to card                       |
|  Mark ride as COMPLETED    >  Mark ride as PAYMENT_PENDING             |
|  Credit driver $16         >  Debit driver $16                         |
|  Reserve inventory item    >  Release inventory item                   |
|  Send confirmation email   >  Send cancellation email                  |
|                                                                         |
|  Compensation must be:                                                 |
|  * IDEMPOTENT: Safe to run multiple times (in case of retries)        |
|  * EVENTUALLY SUCCESSFUL: May retry until it succeeds                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SAGA EXECUTION: SUCCESS VS FAILURE

```
+-------------------------------------------------------------------------+
|                    SAGA SUCCESS SCENARIO                                |
|                                                                         |
|  T1: Mark ride COMPLETED    Y Commit to Ride DB                        |
|  T2: Calculate fare         Y Read-only, no commit needed              |
|  T3: Charge rider $20       Y Commit to Payment DB                     |
|  T4: Credit driver $16      Y Commit to Earnings DB                    |
|  T5: Send receipt           Y Email sent                               |
|                                                                         |
|  All steps succeeded. Saga completes. No compensation needed.          |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    SAGA FAILURE SCENARIO                                |
|                                                                         |
|  T1: Mark ride COMPLETED    Y Committed                                |
|  T2: Calculate fare         Y Done                                     |
|  T3: Charge rider $20       X FAILED (card declined)                   |
|                                                                         |
|  Step 3 failed. Now we run compensations in REVERSE order:             |
|                                                                         |
|  C2: (Calculate fare has no compensation - read only)                  |
|  C1: Revert ride to PAYMENT_FAILED                                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  TIMELINE:                                                             |
|                                                                         |
|  Time ---------------------------------------------------------->      |
|                                                                         |
|  T1 ----> T2 ----> T3 ----X (failure)                                  |
|                           |                                             |
|                           +--> C2 ----> C1                             |
|                                        |                                |
|                                        v                                |
|                               System consistent                         |
|                               (ride is PAYMENT_FAILED)                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### PARTIAL FAILURE: THE TRICKY CASE

```
+-------------------------------------------------------------------------+
|                    WHAT IF COMPENSATION FAILS?                          |
|                                                                         |
|  T1: Mark ride COMPLETED    Y Committed                                |
|  T2: Charge rider $20       Y Committed                                |
|  T3: Credit driver $16      X FAILED (earnings service down)           |
|                                                                         |
|  Now we compensate:                                                    |
|  C2: Refund rider $20       X FAILED (payment service timeout)         |
|                                                                         |
|  What now?! Rider was charged but compensation failed!                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTIONS:                                                            |
|                                                                         |
|  1. RETRY WITH BACKOFF                                                 |
|     Keep retrying the compensation until it succeeds.                  |
|     Compensations MUST be idempotent for this to work.                 |
|                                                                         |
|  2. DEAD LETTER QUEUE                                                  |
|     After N retries, put failed compensation in a special queue.       |
|     Operations team manually resolves.                                 |
|                                                                         |
|  3. HUMAN INTERVENTION                                                 |
|     Alert on-call engineer. They manually refund the rider.            |
|     Not ideal, but sometimes necessary.                                |
|                                                                         |
|  KEY INSIGHT: Sagas provide EVENTUAL consistency, not ACID.            |
|  There may be a window where the system is inconsistent.               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 7.3 CHOREOGRAPHY VS ORCHESTRATION: TWO WAYS TO COORDINATE

There are two fundamentally different ways to coordinate a saga.

### APPROACH 1: CHOREOGRAPHY (Event-Driven)

```
+-------------------------------------------------------------------------+
|                    CHOREOGRAPHY CONCEPT                                 |
|                                                                         |
|  PRINCIPLE: No central coordinator. Each service:                      |
|  * Does its work                                                       |
|  * Publishes an event saying "I'm done"                                |
|  * Next service listens for that event and continues                   |
|                                                                         |
|  Like a dance where each dancer knows their part and reacts to         |
|  what others do. No choreographer telling them what to do.             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  UBER RIDE COMPLETION WITH CHOREOGRAPHY:                               |
|                                                                         |
|  +-------------+                                                       |
|  | Driver taps |                                                       |
|  | "End Ride"  |                                                       |
|  +------+------+                                                       |
|         |                                                               |
|         v                                                               |
|  +-------------+     publishes      +-------------------------+        |
|  | Ride Service| -----------------> | Event: RIDE_COMPLETED   |        |
|  | marks ride  |                    | {ride_id, fare, ...}    |        |
|  | completed   |                    +-----------+-------------+        |
|  +-------------+                                |                      |
|                                     +-----------+-------------+        |
|                                     |      Event Bus (Kafka)   |        |
|                                     +-----------+-------------+        |
|                      +--------------------------+--------------+       |
|                      |                          |              |       |
|                      v                          v              v       |
|              +-------------+           +-------------+  +-----------+  |
|              | Payment Svc |           | Earnings Svc|  | Notif Svc |  |
|              | (subscribes)|           | (subscribes)|  |(subscribes|  |
|              +------+------+           +------+------+  +-----+-----+  |
|                     |                         |               |        |
|                     v                         v               v        |
|              Charges rider             Credits driver    Sends email   |
|                     |                         |                        |
|                     v                         |                        |
|              +-------------------------+      |                        |
|              | Event: PAYMENT_COMPLETED|      |                        |
|              +-------------------------+      |                        |
|                                               |                        |
|                                               v                        |
|                                        +-------------------------+     |
|                                        | Event: EARNINGS_CREDITED|     |
|                                        +-------------------------+     |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    CHOREOGRAPHY: HANDLING FAILURE                       |
|                                                                         |
|  What if Payment Service fails after Ride Service committed?           |
|                                                                         |
|  Payment Service publishes: Event: PAYMENT_FAILED                      |
|                                                                         |
|  Ride Service listens for PAYMENT_FAILED:                              |
|  > Reverts ride status to PAYMENT_PENDING                              |
|  > Publishes: Event: RIDE_REVERTED                                     |
|                                                                         |
|  Each service knows what events trigger its compensation.              |
|                                                                         |
+-------------------------------------------------------------------------+
```

**CHOREOGRAPHY TRADE-OFFS:**

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ADVANTAGES:                                                           |
|  -----------                                                           |
|  * LOOSE COUPLING: Services don't know about each other, only events  |
|  * NO SINGLE POINT OF FAILURE: No coordinator to crash                |
|  * SCALABILITY: Each service scales independently                      |
|  * AUTONOMY: Teams can deploy services independently                   |
|                                                                         |
|  DISADVANTAGES:                                                        |
|  --------------                                                        |
|  * HARD TO UNDERSTAND: No single place shows the whole flow           |
|  * DEBUGGING NIGHTMARE: Tracing a saga across 10 services is hard     |
|  * CYCLIC DEPENDENCIES: Event chains can become circular              |
|  * IMPLICIT FLOW: Logic is scattered across services                  |
|  * TESTING: How do you test the entire saga?                          |
|                                                                         |
|  WHEN TO USE:                                                          |
|  * Simple flows (2-4 steps)                                           |
|  * When services are truly independent                                 |
|  * When you want maximum decoupling                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### APPROACH 2: ORCHESTRATION (Central Coordinator)

```
+-------------------------------------------------------------------------+
|                    ORCHESTRATION CONCEPT                                |
|                                                                         |
|  PRINCIPLE: A central ORCHESTRATOR (coordinator) tells each service   |
|  what to do and when. Services don't talk to each other.               |
|                                                                         |
|  Like a conductor leading an orchestra. Musicians don't decide         |
|  when to play — they follow the conductor's instructions.              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  UBER RIDE COMPLETION WITH ORCHESTRATION:                              |
|                                                                         |
|                    +---------------------------+                       |
|                    |   SAGA ORCHESTRATOR       |                       |
|                    |   (Ride Completion Saga)  |                       |
|                    |                           |                       |
|                    |   Knows the entire flow:  |                       |
|                    |   1. Mark completed       |                       |
|                    |   2. Calculate fare       |                       |
|                    |   3. Charge payment       |                       |
|                    |   4. Credit earnings      |                       |
|                    |   5. Send notifications   |                       |
|                    |                           |                       |
|                    |   Also knows compensations|                       |
|                    +-------------+-------------+                       |
|                                  |                                      |
|         +------------------------+------------------------+            |
|         |                        |                        |            |
|         v                        v                        v            |
|  +-------------+          +-------------+          +-------------+    |
|  | Ride Service|          |Payment Svc  |          |Earnings Svc |    |
|  |             |          |             |          |             |    |
|  | "Mark ride  |          | "Charge     |          | "Credit     |    |
|  |  completed" |          |  $20"       |          |  driver $16"|    |
|  +-------------+          +-------------+          +-------------+    |
|         |                        |                        |            |
|         | done                   | done                   | done       |
|         +------------------------+------------------------+            |
|                                  |                                      |
|                                  v                                      |
|                    +---------------------------+                       |
|                    |   ORCHESTRATOR            |                       |
|                    |   "All done! Saga complete|                       |
|                    +---------------------------+                       |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    ORCHESTRATION: HANDLING FAILURE                      |
|                                                                         |
|  What if Payment Service fails?                                        |
|                                                                         |
|  ORCHESTRATOR:                                                         |
|  1. Calls Ride Service: "Mark completed"          Y                    |
|  2. Calls Payment Service: "Charge $20"           X FAILED             |
|                                                                         |
|  ORCHESTRATOR detects failure and runs compensations:                  |
|  1. Calls Ride Service: "Revert to PAYMENT_FAILED"                    |
|                                                                         |
|  The orchestrator has FULL VISIBILITY and CONTROL.                    |
|  It knows exactly what succeeded and what to compensate.              |
|                                                                         |
+-------------------------------------------------------------------------+
```

**ORCHESTRATION TRADE-OFFS:**

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ADVANTAGES:                                                           |
|  -----------                                                           |
|  * EASY TO UNDERSTAND: Entire flow in one place                       |
|  * EASY TO DEBUG: Orchestrator has full state of saga                 |
|  * EXPLICIT FLOW: Clear sequence, easy to modify                      |
|  * CENTRALIZED ERROR HANDLING: One place to handle all failures       |
|  * TESTABLE: Can unit test the orchestrator                           |
|                                                                         |
|  DISADVANTAGES:                                                        |
|  --------------                                                        |
|  * SINGLE POINT OF FAILURE: Orchestrator goes down = no sagas run    |
|    (Mitigated by making orchestrator stateless + durable)             |
|  * COUPLING: Orchestrator knows about all services                    |
|  * BOTTLENECK: All saga traffic goes through orchestrator             |
|                                                                         |
|  WHEN TO USE:                                                          |
|  * Complex flows (5+ steps)                                           |
|  * When you need visibility and control                               |
|  * When debugging is important (payments, critical flows)             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 7.4 UBER'S IMPLEMENTATION: CADENCE WORKFLOW ENGINE

Uber built and open-sourced CADENCE — a workflow engine for orchestration.

```
+-------------------------------------------------------------------------+
|                    WHAT IS CADENCE?                                     |
|                                                                         |
|  Cadence is a STATEFUL workflow orchestrator that:                     |
|                                                                         |
|  1. PERSISTS WORKFLOW STATE                                            |
|     Every step of the saga is saved to a database.                     |
|     If orchestrator crashes, it resumes from where it left off.        |
|                                                                         |
|  2. HANDLES RETRIES AUTOMATICALLY                                      |
|     Failed steps are retried with exponential backoff.                 |
|     You define retry policies per activity.                            |
|                                                                         |
|  3. SUPPORTS LONG-RUNNING WORKFLOWS                                    |
|     A saga can wait for hours/days (e.g., waiting for user action).    |
|     State is persisted, not held in memory.                            |
|                                                                         |
|  4. PROVIDES VISIBILITY                                                |
|     UI shows all running workflows, their state, history.              |
|     Easy debugging: "What step is this ride on?"                       |
|                                                                         |
|  5. GUARANTEES EXACTLY-ONCE EXECUTION                                  |
|     Even if worker crashes mid-step, step runs exactly once.           |
|                                                                         |
+-------------------------------------------------------------------------+
```

**HOW UBER USES CADENCE FOR RIDE COMPLETION:**

```
+-------------------------------------------------------------------------+
|                    RIDE COMPLETION WORKFLOW                             |
|                                                                         |
|  WORKFLOW DEFINITION (conceptual):                                     |
|                                                                         |
|  RideCompletionWorkflow:                                               |
|                                                                         |
|    Step 1: MARK_COMPLETED                                              |
|    +-- Action: Call RideService.markCompleted(rideId)                  |
|    +-- Compensation: Call RideService.revertStatus(rideId)             |
|    +-- Retry: 3 times, exponential backoff                             |
|                                                                         |
|    Step 2: CALCULATE_FARE                                              |
|    +-- Action: Call PricingService.calculate(rideId)                   |
|    +-- Compensation: None (read-only)                                  |
|    +-- Retry: 3 times                                                  |
|                                                                         |
|    Step 3: CHARGE_PAYMENT                                              |
|    +-- Action: Call PaymentService.charge(rideId, fare)                |
|    +-- Compensation: Call PaymentService.refund(transactionId)         |
|    +-- Retry: 5 times (payment is critical)                            |
|                                                                         |
|    Step 4: CREDIT_EARNINGS                                             |
|    +-- Action: Call EarningsService.credit(driverId, amount)           |
|    +-- Compensation: Call EarningsService.debit(driverId, amount)      |
|    +-- Retry: 5 times                                                  |
|                                                                         |
|    Step 5: SEND_NOTIFICATIONS (async, non-blocking)                    |
|    +-- Action: Call NotificationService.sendReceipt(rideId)            |
|    +-- Compensation: None (best effort)                                |
|    +-- On failure: Log and continue (non-critical)                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  EXECUTION FLOW:                                                       |
|                                                                         |
|  1. Driver taps "End Ride"                                             |
|  2. API creates new RideCompletionWorkflow(rideId)                     |
|  3. Cadence persists workflow state                                    |
|  4. Cadence worker picks up workflow, executes Step 1                  |
|  5. Step 1 completes, state persisted, worker executes Step 2          |
|  6. ... continues until all steps complete                             |
|                                                                         |
|  If worker crashes at Step 3:                                          |
|  * Cadence detects timeout                                             |
|  * Another worker picks up workflow                                    |
|  * Workflow resumes from Step 3 (not Step 1!)                         |
|  * Idempotent step design ensures no duplicate charges                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

**WHY UBER CHOSE ORCHESTRATION OVER CHOREOGRAPHY:**

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. PAYMENT IS CRITICAL                                                |
|     Can't afford to lose track of whether rider was charged.           |
|     Orchestrator has complete audit trail.                             |
|                                                                         |
|  2. COMPLEX FLOWS                                                      |
|     Ride completion has 6+ steps with dependencies.                    |
|     Choreography would be a nightmare to debug.                        |
|                                                                         |
|  3. VISIBILITY REQUIREMENTS                                            |
|     Support team needs to see "Where is this ride stuck?"             |
|     Cadence UI shows exactly which step and why.                       |
|                                                                         |
|  4. REGULATORY COMPLIANCE                                              |
|     Need full audit trail for financial transactions.                  |
|     Cadence persists entire workflow history.                          |
|                                                                         |
|  5. FAILURE RECOVERY                                                   |
|     If data center fails, workflows resume automatically.              |
|     Choreography would need complex recovery logic in each service.    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SUMMARY: CHOREOGRAPHY VS ORCHESTRATION

```
+-------------------------------------------------------------------------+
|                    COMPARISON MATRIX                                    |
|                                                                         |
|  Aspect             | Choreography          | Orchestration            |
|  -------------------+-----------------------+------------------------  |
|  Coordination       | Events between svcs   | Central coordinator      |
|  Coupling           | Loose                 | Tighter                  |
|  Flow visibility    | Scattered             | Centralized              |
|  Debugging          | Hard                  | Easy                     |
|  Single point fail  | No                    | Yes (mitigated)          |
|  Complexity grows   | Exponentially         | Linearly                 |
|  Best for           | Simple flows          | Complex flows            |
|                                                                         |
|  UBER'S CHOICE: Orchestration via Cadence                              |
|  * Ride completion, payment, driver payouts = orchestrated            |
|  * Simple notifications = choreographed (fire-and-forget events)      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 8: PAYMENT PROCESSING — RELIABILITY AT SCALE

Processing payments at Uber's scale (20 million rides/day) requires
bulletproof reliability. We cannot double-charge customers or miss payments.

### 8.1 TWO-PHASE PAYMENT (AUTHORIZE + CAPTURE)

```
+-------------------------------------------------------------------------+
|                    TWO-PHASE PAYMENT FLOW                               |
|                                                                         |
|  PHASE 1: AUTHORIZATION (Before ride)                                  |
|  ------------------------------------                                  |
|  1. Rider requests ride, estimated fare = $20                         |
|  2. We authorize $25 on their card (fare + 25% buffer)                |
|  3. Bank confirms funds are available and holds them                  |
|  4. Ride can proceed                                                  |
|                                                                         |
|  If authorization fails:                                               |
|  > Prompt rider to use different payment method                       |
|  > Cannot request ride without valid payment                          |
|                                                                         |
|  PHASE 2: CAPTURE (After ride)                                         |
|  -----------------------------                                         |
|  1. Ride completes, actual fare = $18                                 |
|  2. We capture $18 (actual amount)                                    |
|  3. Remaining $7 hold is released                                     |
|  4. Transaction complete                                              |
|                                                                         |
|  If capture fails:                                                     |
|  > Retry with exponential backoff                                     |
|  > Try backup payment method                                          |
|  > Block rider from new rides until resolved                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 8.2 IDEMPOTENCY IMPLEMENTATION

### CONCEPT: IDEMPOTENCY

DEFINITION: An operation is idempotent if executing it multiple times has
the same effect as executing it once.

PRINCIPLE: "Exactly Once" Semantics
In distributed systems, network failures are common. A request might be:
- Sent but not received
- Received but response lost
- Processed but confirmation lost

The client will RETRY. Without idempotency, a payment could be charged twice!

```
+-------------------------------------------------------------------------+
|                    THE RETRY PROBLEM                                    |
|                                                                         |
|  Client           Network           Payment Service                    |
|    |                 |                    |                            |
|    |-- Charge $20 -->|------------------>|                            |
|    |                 |                   |-- Charges card              |
|    |                 |<-- Response ------|                            |
|    |                 X (network fails)   |                            |
|    |                 |                   |                            |
|    | (timeout, retry)|                   |                            |
|    |-- Charge $20 -->|------------------>|                            |
|    |                 |                   |-- Charges card AGAIN! ❌   |
|    |                 |                   |                            |
|                                                                         |
|  WITHOUT IDEMPOTENCY: Customer charged $40 instead of $20!            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 8.3 IDEMPOTENCY: HOW TO IMPLEMENT "EXACTLY ONCE"

### THE CORE PRINCIPLE: IDEMPOTENCY KEYS

```
+-------------------------------------------------------------------------+
|                    WHAT IS AN IDEMPOTENCY KEY?                          |
|                                                                         |
|  DEFINITION:                                                           |
|  A unique identifier attached to a request that represents the         |
|  INTENT of the operation, not the request itself.                      |
|                                                                         |
|  KEY INSIGHT:                                                          |
|  The key should be the SAME when a client retries                      |
|  but DIFFERENT for genuinely new operations.                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  HOW IT WORKS:                                                         |
|                                                                         |
|  Request 1: "Charge ride_123" with key = "payment:ride_123:attempt_1" |
|             > System processes, charges $20, stores result with key   |
|                                                                         |
|  Request 2: Same key (retry)                                          |
|             > System sees key exists                                   |
|             > Returns stored result WITHOUT processing again          |
|             > Customer charged exactly once!                          |
|                                                                         |
|  Request 3: "Charge ride_456" with key = "payment:ride_456:attempt_1" |
|             > Different key, genuinely new operation                    |
|             > System processes normally                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### THE CHECK-BEFORE-PROCESS PATTERN

```
+-------------------------------------------------------------------------+
|                    IDEMPOTENCY PROCESSING FLOW                          |
|                                                                         |
|  Every idempotent operation follows this pattern:                      |
|                                                                         |
|  +------------------------------------------------------------------+  |
|  |                                                                  |  |
|  |  STEP 1: CHECK CACHE (Fast Path)                                |  |
|  |  -----------------------------                                  |  |
|  |  Look up idempotency key in Redis cache.                        |  |
|  |  If found > Return cached result immediately (sub-millisecond)  |  |
|  |  If not found > Continue to step 2                              |  |
|  |                                                                  |  |
|  |  Why cache? Most retries happen within seconds.                 |  |
|  |  Redis lookup: < 1ms. Database lookup: 5-20ms.                  |  |
|  |                                                                  |  |
|  +------------------------------------------------------------------+  |
|                         |                                              |
|                         v                                              |
|  +------------------------------------------------------------------+  |
|  |                                                                  |  |
|  |  STEP 2: CHECK DATABASE (Cache Miss)                            |  |
|  |  -----------------------------------                            |  |
|  |  Cache might have expired but operation was done.               |  |
|  |  Query database: "Any payment with this idempotency key?"      |  |
|  |  If found > Return result, warm the cache                      |  |
|  |  If not found > Continue to step 3                              |  |
|  |                                                                  |  |
|  +------------------------------------------------------------------+  |
|                         |                                              |
|                         v                                              |
|  +------------------------------------------------------------------+  |
|  |                                                                  |  |
|  |  STEP 3: ACQUIRE LOCK (Prevent Race Condition)                  |  |
|  |  ---------------------------------------------                  |  |
|  |  What if two retries arrive simultaneously?                     |  |
|  |  Both pass steps 1 & 2 (nothing found yet).                    |  |
|  |  Without locking, both would process > double charge!          |  |
|  |                                                                  |  |
|  |  Solution: Acquire distributed lock on idempotency key.         |  |
|  |  * First request gets lock > proceeds to step 4                |  |
|  |  * Second request waits or fails with "in progress"            |  |
|  |                                                                  |  |
|  +------------------------------------------------------------------+  |
|                         |                                              |
|                         v                                              |
|  +------------------------------------------------------------------+  |
|  |                                                                  |  |
|  |  STEP 4: PROCESS THE OPERATION                                  |  |
|  |  -----------------------------                                  |  |
|  |  Now we know: not in cache, not in DB, we have the lock.        |  |
|  |  Safe to process. Call payment gateway, charge the card.        |  |
|  |                                                                  |  |
|  +------------------------------------------------------------------+  |
|                         |                                              |
|                         v                                              |
|  +------------------------------------------------------------------+  |
|  |                                                                  |  |
|  |  STEP 5: STORE RESULT                                           |  |
|  |  ------------------                                             |  |
|  |  Store result with idempotency key in BOTH:                     |  |
|  |  * Database (permanent, survives cache eviction)               |  |
|  |  * Redis cache (fast lookup for retries)                       |  |
|  |                                                                  |  |
|  |  CRITICAL: Store BEFORE releasing lock!                        |  |
|  |                                                                  |  |
|  +------------------------------------------------------------------+  |
|                         |                                              |
|                         v                                              |
|  +------------------------------------------------------------------+  |
|  |                                                                  |  |
|  |  STEP 6: RELEASE LOCK & RETURN                                  |  |
|  |  -----------------------------                                  |  |
|  |  Release the distributed lock.                                  |  |
|  |  Return result to caller.                                       |  |
|  |                                                                  |  |
|  |  Any future requests with same key will hit cache/DB.          |  |
|  |                                                                  |  |
|  +------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### IDEMPOTENCY KEY DESIGN

```
+-------------------------------------------------------------------------+
|                    HOW TO DESIGN IDEMPOTENCY KEYS                       |
|                                                                         |
|  PRINCIPLE: The key must identify the INTENT, not the request.         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  GOOD KEY DESIGNS:                                                     |
|                                                                         |
|  For payments:                                                         |
|  payment:{ride_id}:{attempt_number}                                    |
|  Example: "payment:ride_12345:1"                                       |
|                                                                         |
|  WHY IT WORKS:                                                         |
|  * Same ride_id + attempt = same key on retry Y                       |
|  * If payment failed and rider retries with new card,                 |
|    increment attempt_number > different key > new charge              |
|                                                                         |
|  For ride requests:                                                    |
|  ride:{rider_id}:{pickup_geohash}:{minute_bucket}                      |
|  Example: "ride:user_abc:9q8yy:202401151430"                          |
|                                                                         |
|  WHY IT WORKS:                                                         |
|  * Same user, same location, same minute = duplicate request          |
|  * If they really want two rides, they'll request a minute later      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  BAD KEY DESIGNS:                                                      |
|                                                                         |
|  payment:{random_uuid}                                                 |
|  PROBLEM: Client generates new UUID on retry > double charge!         |
|                                                                         |
|  payment:{timestamp}                                                   |
|  PROBLEM: Timestamp changes on retry > double charge!                 |
|                                                                         |
|  payment:{request_id}                                                  |
|  PROBLEM: What if client retries with same request_id but             |
|           different amount? We'd return wrong cached result!          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WHO GENERATES THE KEY?                                                |
|                                                                         |
|  OPTION A: Client generates                                            |
|  * Client creates key based on their intent                           |
|  * Sends key with every request                                       |
|  * PROS: Client controls retry semantics                              |
|  * CONS: Client might generate bad keys                               |
|                                                                         |
|  OPTION B: Server generates from request content                       |
|  * Server hashes: f(ride_id, amount, timestamp_minute)                |
|  * PROS: Consistent key generation                                    |
|  * CONS: Less flexibility for client                                  |
|                                                                         |
|  UBER'S APPROACH: Hybrid                                               |
|  * Client sends idempotency key header                                |
|  * If missing, server generates from request content                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### STORING RESULTS: WHAT TO CACHE?

```
+-------------------------------------------------------------------------+
|                    WHAT TO STORE WITH IDEMPOTENCY KEY                   |
|                                                                         |
|  Store the COMPLETE response, not just "done":                         |
|                                                                         |
|  +----------------------------------------------------------------+    |
|  |  Idempotency Key        |  Stored Value                       |    |
|  +-------------------------+-------------------------------------+    |
|  |  payment:ride_123:1     |  {                                  |    |
|  |                         |    "status": "SUCCESS",             |    |
|  |                         |    "transaction_id": "txn_xyz",     |    |
|  |                         |    "amount": 20.00,                 |    |
|  |                         |    "charged_at": "2024-01-15..."    |    |
|  |                         |  }                                  |    |
|  +----------------------------------------------------------------+    |
|                                                                         |
|  WHY STORE COMPLETE RESPONSE?                                          |
|  * Retry should return EXACTLY what original request returned         |
|  * Client expects same response shape                                 |
|  * Includes transaction_id for reconciliation                         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WHAT IF ORIGINAL REQUEST FAILED?                                      |
|                                                                         |
|  Store failures too!                                                   |
|                                                                         |
|  +----------------------------------------------------------------+    |
|  |  payment:ride_123:1     |  {                                  |    |
|  |                         |    "status": "FAILED",              |    |
|  |                         |    "error": "CARD_DECLINED",        |    |
|  |                         |    "message": "Insufficient funds"  |    |
|  |                         |  }                                  |    |
|  +----------------------------------------------------------------+    |
|                                                                         |
|  On retry, client gets same failure > knows to try different card.    |
|  Don't retry the charge (card is still declined!).                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CACHE TTL:                                                            |
|                                                                         |
|  Redis cache: 24 hours (most retries happen within minutes)           |
|  Database: Forever (permanent record of all payments)                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DEFENSE IN DEPTH: DATABASE CONSTRAINT

```
+-------------------------------------------------------------------------+
|                    LAST LINE OF DEFENSE                                 |
|                                                                         |
|  Application-level checks can have bugs. Always add a database         |
|  constraint as the ultimate safety net.                                |
|                                                                         |
|  PAYMENTS TABLE:                                                       |
|  +------------------------------------------------------------------+  |
|  |  id                 |  UUID PRIMARY KEY                         |  |
|  |  ride_id            |  UUID NOT NULL                            |  |
|  |  amount             |  DECIMAL(10,2)                            |  |
|  |  status             |  VARCHAR(20)                              |  |
|  |  idempotency_key    |  VARCHAR(255) UNIQUE  < DATABASE ENFORCED |  |
|  |  created_at         |  TIMESTAMP                                |  |
|  +------------------------------------------------------------------+  |
|                                                                         |
|  WHY THIS MATTERS:                                                     |
|                                                                         |
|  If two requests somehow bypass application checks and try to          |
|  insert payments with the same idempotency_key:                        |
|                                                                         |
|  * First INSERT succeeds                                              |
|  * Second INSERT fails with UNIQUE CONSTRAINT VIOLATION               |
|  * Application catches this exception                                 |
|  * Returns existing payment instead of creating duplicate             |
|                                                                         |
|  Even with bugs in cache/lock logic, database prevents double charge!  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### EDGE CASES AND CONSIDERATIONS

```
+-------------------------------------------------------------------------+
|                    TRICKY SCENARIOS                                     |
|                                                                         |
|  SCENARIO 1: Processing crashed after charging, before storing         |
|  ---------------------------------------------------------------------  |
|  1. Request received, passed all checks                               |
|  2. Called payment gateway, card charged Y                            |
|  3. Server crashed before saving to database X                        |
|  4. Client retries...                                                 |
|                                                                         |
|  PROBLEM: No record in our DB, but card was charged!                  |
|                                                                         |
|  SOLUTION: Forward idempotency key to payment gateway                 |
|  * Stripe/Braintree support idempotency keys                         |
|  * If we retry, gateway says "already charged, here's result"         |
|  * We save that result and return                                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SCENARIO 2: Same key, different parameters                           |
|  ---------------------------------------------------------------------  |
|  Request 1: Charge $20 with key "payment:123:1"                       |
|  Request 2: Charge $25 with key "payment:123:1" (same key!)           |
|                                                                         |
|  QUESTION: Return cached $20 result? Or reject?                       |
|                                                                         |
|  SOLUTION: Validate parameters match                                   |
|  * Store request parameters with idempotency key                      |
|  * On cache hit, compare stored params with new request               |
|  * If mismatch > reject with "conflicting request"                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SCENARIO 3: Idempotency key reuse after long time                    |
|  ---------------------------------------------------------------------  |
|  Request 1: Jan 1, charge for ride_123 with key "payment:123:1"       |
|  Request 2: Mar 1, charge for ride_456 with key "payment:123:1"       |
|             (client reused key by mistake)                            |
|                                                                         |
|  PROBLEM: Returns old cached result for wrong ride!                   |
|                                                                         |
|  SOLUTION: Include relevant context in key                            |
|  * Key should be: "payment:{ride_id}:{attempt}"                       |
|  * Different ride = different key (even with same attempt #)          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SUMMARY: IDEMPOTENCY LAYERS

```
+-------------------------------------------------------------------------+
|                    DEFENSE IN DEPTH                                     |
|                                                                         |
|  LAYER 1: Redis Cache                                                  |
|  ---------------------                                                 |
|  * Fast lookup for immediate retries                                  |
|  * TTL: 24 hours                                                      |
|  * Catches 99% of retries                                             |
|                                                                         |
|  LAYER 2: Database Lookup                                              |
|  -------------------------                                             |
|  * Catches retries after cache expiry                                 |
|  * Permanent record                                                   |
|  * Query by idempotency_key index                                     |
|                                                                         |
|  LAYER 3: Distributed Lock                                             |
|  -------------------------                                             |
|  * Prevents race condition on concurrent retries                      |
|  * Short-lived (30 seconds)                                           |
|  * Only one request processes at a time                               |
|                                                                         |
|  LAYER 4: Database Unique Constraint                                   |
|  -----------------------------------                                   |
|  * Ultimate safety net                                                |
|  * If all else fails, DB rejects duplicate                           |
|  * Application catches and returns existing                           |
|                                                                         |
|  LAYER 5: Payment Gateway Idempotency                                  |
|  ------------------------------------                                  |
|  * Forward key to Stripe/Braintree                                    |
|  * Even if our system fails, gateway prevents double charge          |
|                                                                         |
|  RESULT: Customer charged EXACTLY ONCE, guaranteed.                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 9: RIDE SHARING (UBERPOOL) — OPTIMIZATION AT SCALE

UberPool matches multiple riders going in the same direction, sharing a
single vehicle. This is a significantly more complex problem than 1:1 matching.

### 9.1 THE POOLING PROBLEM (TSP VARIANT)

Given N riders, each with a pickup and dropoff location, we need to:
1. Find which riders can share a vehicle (compatible directions)
2. Determine the optimal order to visit all 2N waypoints
3. Ensure no rider's trip is extended more than a threshold
4. Calculate fair pricing for each rider

This is a variant of the Traveling Salesman Problem (TSP), which is NP-hard.
But with constraints (max 3 riders, max 10-minute detour), we can solve it
for each request in real-time.

### CONCEPT: CONSTRAINED OPTIMIZATION

PRINCIPLE: NP-Hard Problem Made Tractable
TSP is NP-hard: O(n!) time complexity. For 10 stops, that's 3.6 million
permutations! But our constraints reduce the search space dramatically:

1. MAX 3 RIDERS: At most 6 waypoints (3 pickups + 3 dropoffs)
2. ORDER CONSTRAINT: Pickup must precede dropoff for each rider
3. DETOUR LIMIT: Prune routes that exceed 10-minute detour

With these constraints, we can enumerate valid orderings efficiently.

```
+-------------------------------------------------------------------------+
|                    POOL MATCHING ALGORITHM (CONCEPT)                    |
|                                                                         |
|  GOAL: Given a new ride request, either:                               |
|        (A) Add rider to an existing pool with minimal detour, OR       |
|        (B) Create a new pool if no compatible pool exists              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### STEP 1: SPATIAL FILTERING — FIND NEARBY POOLS

```
+-------------------------------------------------------------------------+
|  PRINCIPLE: Pools far from the new rider's pickup are irrelevant.      |
|                                                                         |
|  APPROACH:                                                             |
|  * Use geospatial index (Redis GEO, H3, or PostGIS) to find pools     |
|    within a search radius (e.g., 3 km from new rider's pickup)        |
|                                                                         |
|  * Only consider pools that:                                           |
|    - Have not reached max capacity (typically 2-3 riders)             |
|    - Haven't passed too many waypoints (still can add detour)         |
|    - Are actively looking for matches                                 |
|                                                                         |
|  WHY: Reduces O(n) scan of all pools to O(k) where k << n             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Example:                                                              |
|  * 10,000 active pools in city                                        |
|  * Geospatial filter returns 50 pools within 3 km                     |
|  * Reduced search space by 99.5%                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### STEP 2: DIRECTION FILTERING — SAME GENERAL HEADING

```
+-------------------------------------------------------------------------+
|  PRINCIPLE: Pooling works only if riders are going the same way.      |
|                                                                         |
|  APPROACH:                                                             |
|  * Calculate heading/bearing for pool (current location > destination)|
|  * Calculate heading for new rider (pickup > dropoff)                 |
|  * If angle difference > threshold (e.g., 45°), skip this pool        |
|                                                                         |
|                        N (0°)                                          |
|                          ^                                             |
|                          |                                             |
|              Pool -------+--------> E (90°)                           |
|              heading     |                                             |
|                   \      |                                             |
|                    \45°  |                                             |
|                     \    |                                             |
|                      ↘   |                                             |
|                   New rider heading                                    |
|                                                                         |
|  If both headings within ~45°, riders are going "same direction"      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WHY 45°?                                                              |
|  * Too strict (10°): Miss valid pools, fewer matches                  |
|  * Too loose (90°): Excessive detours, unhappy riders                 |
|  * 45° is a practical balance                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### STEP 3: DETOUR CALCULATION — CAN WE ADD RIDER WITHOUT TOO MUCH DETOUR?

```
+-------------------------------------------------------------------------+
|  PRINCIPLE: Each existing rider must not be delayed beyond threshold.  |
|                                                                         |
|  KEY CONCEPT: DETOUR                                                   |
|  ------------------------                                              |
|  Detour = (New ETA with pool) - (Original ETA without pool)           |
|                                                                         |
|  Example:                                                              |
|  * Rider A's original ETA: 15 minutes                                 |
|  * After adding Rider B: Rider A's new ETA: 22 minutes                |
|  * Rider A's detour: 7 minutes                                        |
|                                                                         |
|  CONSTRAINT: No rider's detour can exceed MAX_DETOUR (e.g., 10 min)   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WHAT WE CALCULATE:                                                    |
|  * Add new rider's pickup + dropoff to current waypoint list          |
|  * Find the OPTIMAL ordering of all waypoints                         |
|  * For each ordering, calculate each rider's detour                   |
|  * Keep ordering only if ALL detours < MAX_DETOUR                     |
|  * Among valid orderings, pick the one with MINIMUM total detour      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### STEP 4: OPTIMAL WAYPOINT ORDERING — THE HARD PART

```
+-------------------------------------------------------------------------+
|  PROBLEM: Given N riders, we have 2N waypoints (N pickups + N drops). |
|           In what order should the driver visit them?                  |
|                                                                         |
|  CONSTRAINT: For each rider, pickup MUST come before dropoff.         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  EXAMPLE: 2 Riders (4 Waypoints)                                       |
|  * P1 = Rider 1 Pickup,  D1 = Rider 1 Dropoff                         |
|  * P2 = Rider 2 Pickup,  D2 = Rider 2 Dropoff                         |
|                                                                         |
|  VALID orderings (P before D for each rider):                         |
|                                                                         |
|  +------------------------------------------------------------------+  |
|  |  P1 > P2 > D1 > D2    Pick both, drop 1, drop 2                 |  |
|  |  P1 > P2 > D2 > D1    Pick both, drop 2, drop 1                 |  |
|  |  P1 > D1 > P2 > D2    Pick 1, drop 1, then pick & drop 2        |  |
|  |  P2 > P1 > D1 > D2    Pick 2, pick 1, drop 1, drop 2            |  |
|  |  P2 > P1 > D2 > D1    Pick 2, pick 1, drop 2, drop 1            |  |
|  |  P2 > D2 > P1 > D1    Pick 2, drop 2, then pick & drop 1        |  |
|  +------------------------------------------------------------------+  |
|                                                                         |
|  INVALID orderings (D before P):                                       |
|  X D1 > P1 > ...  (Can't drop before pickup!)                         |
|  X P1 > D2 > P2 > D1  (D2 before P2!)                                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SCALING:                                                              |
|  * 2 riders: 6 valid orderings                                        |
|  * 3 riders: 90 valid orderings                                       |
|  * 4 riders: 2520 valid orderings                                     |
|                                                                         |
|  With max 3 riders per pool, enumeration is tractable.               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### STEP 5: SCORING AND SELECTION

```
+-------------------------------------------------------------------------+
|  For each candidate pool, we now have:                                 |
|  * The best valid ordering (minimum detour)                           |
|  * The maximum detour any rider would experience                      |
|                                                                         |
|  SELECTION CRITERIA:                                                   |
|  --------------------                                                  |
|  1. Filter: Discard pools where max detour > threshold                |
|  2. Rank: Among remaining, pick pool with MINIMUM detour              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  ALTERNATIVE SCORING FUNCTIONS:                                        |
|                                                                         |
|  * Minimize MAX detour (fairness — no one suffers too much)           |
|  * Minimize TOTAL detour (efficiency — optimize overall time)         |
|  * Minimize DRIVER empty miles (cost optimization)                    |
|  * Weighted combination of above                                      |
|                                                                         |
|  Uber likely uses weighted multi-objective optimization.              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### STEP 6: NO MATCH FOUND — CREATE NEW POOL

```
+-------------------------------------------------------------------------+
|  If no existing pool satisfies constraints:                            |
|                                                                         |
|  * Create a NEW pool with just this rider                             |
|  * Assign a driver (using regular driver matching algorithm)          |
|  * New pool is now available for future riders to join                |
|                                                                         |
|  The new pool will be indexed geospatially so future requests         |
|  can find it in Step 1.                                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

**COMPLETE ALGORITHM FLOW:**

```
+-------------------------------------------------------------------------+
|                                                                         |
|   New Ride Request                                                     |
|         |                                                              |
|         v                                                              |
|  +---------------------+                                              |
|  |  SPATIAL FILTER     |  "Find pools within 3 km"                    |
|  |  (Geospatial Query) |                                              |
|  +----------+----------+                                              |
|             | Nearby pools                                            |
|             v                                                          |
|  +---------------------+                                              |
|  |  DIRECTION FILTER   |  "Keep only same-direction pools"           |
|  |  (Heading < 45°)    |                                              |
|  +----------+----------+                                              |
|             | Compatible pools                                        |
|             v                                                          |
|  +---------------------+                                              |
|  |  FOR EACH POOL:     |                                              |
|  |  - Find optimal     |                                              |
|  |    waypoint order   |  "Enumerate valid orderings"                 |
|  |  - Calculate detour |                                              |
|  |    for all riders   |                                              |
|  +----------+----------+                                              |
|             | (Pool, BestOrdering, MaxDetour)                         |
|             v                                                          |
|  +---------------------+                                              |
|  |  FILTER:            |                                              |
|  |  MaxDetour < 10min? |                                              |
|  +----------+----------+                                              |
|             |                                                          |
|     +-------+-------+                                                 |
|     v               v                                                 |
|  +------+       +--------------+                                      |
|  | YES  |       | NO valid     |                                      |
|  |      |       | pools        |                                      |
|  +--+---+       +------+-------+                                      |
|     |                  |                                               |
|     v                  v                                               |
|  +--------------+  +--------------+                                   |
|  | SELECT pool  |  | CREATE new   |                                   |
|  | with MINIMUM |  | pool with    |                                   |
|  | detour       |  | just this    |                                   |
|  |              |  | rider        |                                   |
|  +--------------+  +--------------+                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

**TIME COMPLEXITY ANALYSIS:**

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Let:                                                                  |
|  * P = number of nearby pools (after spatial filter)                  |
|  * N = max riders per pool (typically 2-3)                            |
|  * V = valid orderings for N riders = (2N)! / 2^N                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Step 1 (Spatial): O(log M) where M = total pools (index lookup)      |
|  Step 2 (Direction): O(P) — check each nearby pool                    |
|  Step 3-4 (Ordering): O(P × V × N) — for each pool, enumerate orders  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  With N = 3: V = 90 orderings                                         |
|  With P = 50 nearby pools: 50 × 90 × 3 = 13,500 operations            |
|                                                                         |
|  This is very tractable — completes in milliseconds.                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  KEY INSIGHT: The constraint (max 3 riders) makes enumeration         |
|  feasible. Without it, we'd need heuristics (TSP approximations).    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### VALID ORDERING GENERATION (Backtracking Algorithm):

For 2 riders (4 waypoints), valid orderings where Pickup < Dropoff for each:
- P1 > P2 > D1 > D2
- P1 > P2 > D2 > D1
- P1 > D1 > P2 > D2
- P2 > P1 > D1 > D2
- P2 > P1 > D2 > D1
- P2 > D2 > P1 > D1

Only 6 valid orderings out of 24 total permutations (4!).

```
+-------------------------------------------------------------------------+
|  /**                                                                   |
|   * Generate valid orderings using backtracking.                       |
|   * Constraint: Pickup must come before dropoff for each rider.       |
|   */                                                                   |
|  private void backtrack(List<Waypoint> remaining,                      |
|                         List<Waypoint> current,                        |
|                         Set<String> pickedUp,                          |
|                         List<List<Waypoint>> result) {                 |
|                                                                         |
|      if (remaining.isEmpty()) {                                        |
|          result.add(new ArrayList<>(current));                         |
|          return;                                                       |
|      }                                                                 |
|                                                                         |
|      for (int i = 0; i < remaining.size(); i++) {                      |
|          Waypoint wp = remaining.get(i);                               |
|                                                                         |
|          // CONSTRAINT: Can only dropoff if already picked up          |
|          if (wp.isDropoff() && !pickedUp.contains(wp.getRiderId())) { |
|              continue;  // Skip: invalid ordering                     |
|          }                                                             |
|                                                                         |
|          current.add(wp);                                              |
|          if (wp.isPickup()) pickedUp.add(wp.getRiderId());            |
|                                                                         |
|          backtrack(remaining.without(i), current, pickedUp, result);   |
|                                                                         |
|          current.removeLast();                                         |
|          if (wp.isPickup()) pickedUp.remove(wp.getRiderId());         |
|      }                                                                 |
|  }                                                                     |
+-------------------------------------------------------------------------+
```

## PART 10: DATABASE ARCHITECTURE — CHOOSING THE RIGHT STORAGE

Different data has different access patterns. Using one database for
everything would be a mistake. We use specialized storage for each use case.

### 10.1 STORAGE SELECTION MATRIX

```
+-------------------------------------------------------------------------+
|                    DATABASE SELECTION                                   |
|                                                                         |
|  +----------------+---------------+-------------------------------+    |
|  | Data Type      | Storage       | Why This Choice               |    |
|  +----------------+---------------+-------------------------------+    |
|  | User profiles  | PostgreSQL    | ACID, complex queries,        |    |
|  | Rides          |               | relationships                 |    |
|  | Payments       |               |                               |    |
|  +----------------+---------------+-------------------------------+    |
|  | Driver         | Redis         | Sub-ms reads, geospatial      |    |
|  | locations      | (GEOADD)      | queries, 1M+ writes/sec       |    |
|  | (real-time)    |               |                               |    |
|  +----------------+---------------+-------------------------------+    |
|  | Location       | Cassandra     | High write throughput,        |    |
|  | history        |               | time-series optimized,        |    |
|  |                |               | auto-TTL                      |    |
|  +----------------+---------------+-------------------------------+    |
|  | Events/        | Kafka         | Durable queue, replay,        |    |
|  | messages       |               | decoupling                    |    |
|  +----------------+---------------+-------------------------------+    |
|  | Session data   | Redis         | Fast access, TTL support      |    |
|  | Surge cache    |               |                               |    |
|  +----------------+---------------+-------------------------------+    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 11: FAILURE HANDLING — WHEN THINGS GO WRONG

In a distributed system, failures are not exceptions — they're the norm.
Networks partition, servers crash, disks fail. Our system must handle these
gracefully.

### 11.1 DRIVER GOES OFFLINE MID-RIDE

```
+-------------------------------------------------------------------------+
|                    DRIVER OFFLINE HANDLING                              |
|                                                                         |
|  Detection:                                                            |
|  * No location update for 60 seconds                                  |
|  * WebSocket heartbeat fails                                          |
|                                                                         |
|  Timeline:                                                             |
|  +-----------------------------------------------------------------+   |
|  | T+0s:    Last location received                                |   |
|  | T+30s:   Warning: Check connection                             |   |
|  | T+60s:   Mark as "potentially offline"                         |   |
|  | T+60s:   Push notification to driver                           |   |
|  | T+120s:  Mark ride as "DRIVER_UNREACHABLE"                     |   |
|  |          Notify rider with options:                            |   |
|  |          1. Wait longer                                        |   |
|  |          2. Cancel (no charge)                                 |   |
|  |          3. Find new driver                                    |   |
|  | T+180s:  Auto-reassign if still offline                        |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  If ride was IN_PROGRESS:                                              |
|  * Estimate position based on last known location + route            |
|  * Calculate partial fare for distance traveled                      |
|  * Log incident for driver review                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 11.2 GPS ACCURACY ISSUES

```
+-------------------------------------------------------------------------+
|                    GPS CORRECTION TECHNIQUES                            |
|                                                                         |
|  Problem: GPS shows driver in a river                                  |
|                                                                         |
|  Solution 1: KALMAN FILTER                                             |
|  -----------------------------                                         |
|  Combine GPS with accelerometer and gyroscope data to smooth          |
|  erratic readings and predict position when GPS is unreliable.        |
|                                                                         |
|  predicted_position = last_position + velocity × time                  |
|  smoothed_position = predicted × (1-K) + GPS × K                      |
|  where K = confidence in GPS reading                                  |
|                                                                         |
|  Solution 2: MAP MATCHING                                              |
|  -----------------------                                               |
|  Snap GPS points to the road network using a Hidden Markov Model.     |
|  The model considers:                                                 |
|  * Distance from GPS point to nearby roads                            |
|  * Probability of transitioning from previous road                    |
|  * Speed limits and travel patterns                                   |
|                                                                         |
|  Solution 3: DEAD RECKONING                                            |
|  -------------------------                                             |
|  When GPS is completely lost (tunnel), estimate position using:       |
|  position = last_known + speed × time × heading                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 12: COMPLETE SYSTEM ARCHITECTURE

Let's bring everything together into a complete picture.

### 12.1 HIGH-LEVEL ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|              Rider App                         Driver App               |
|                  |                                  |                   |
|                  | (HTTPS/REST)                     | (WebSocket)       |
|                  v                                  v                   |
|    +---------------------------------------------------------------+   |
|    |                     CDN (CloudFront)                          |   |
|    |                  Map tiles, static assets                     |   |
|    +---------------------------+-----------------------------------+   |
|                                |                                        |
|    +---------------------------v-----------------------------------+   |
|    |                    DNS (Route53)                              |   |
|    |               Geolocation-based routing                       |   |
|    +---------------------------+-----------------------------------+   |
|                                |                                        |
|    +---------------------------v-----------------------------------+   |
|    |              API Gateway / Load Balancer                      |   |
|    |         Auth, Rate Limiting, SSL Termination                  |   |
|    +---------------------------+-----------------------------------+   |
|                                |                                        |
|         +--------------+-------+-------+--------------+                |
|         v              v               v              v                |
|    +---------+   +----------+   +----------+   +----------+           |
|    |  Ride   |   | Location |   | Matching |   | Payment  |           |
|    | Service |   | Service  |   | Service  |   | Service  |           |
|    +----+----+   +----+-----+   +----+-----+   +----+-----+           |
|         |             |              |              |                  |
|         +-------------+------+-------+--------------+                  |
|                              |                                          |
|              +---------------+---------------+                         |
|              v               v               v                         |
|         +---------+    +---------+    +-----------+                   |
|         |  Redis  |    |  Kafka  |    | PostgreSQL|                   |
|         |(realtime|    |(events) |    |  (ACID)   |                   |
|         | + geo)  |    |         |    |           |                   |
|         +---------+    +----+----+    +-----------+                   |
|                             |                                          |
|                             v                                          |
|                       +-----------+                                    |
|                       | Cassandra |                                    |
|                       | (history) |                                    |
|                       +-----------+                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 12.2 END-TO-END RIDE FLOW

```
+-------------------------------------------------------------------------+
|                    COMPLETE RIDE JOURNEY                                |
|                                                                         |
|  1. RIDER OPENS APP                                                    |
|     App gets GPS location, sends to server                            |
|     Server shows nearby drivers on map (from Redis GEORADIUS)         |
|                                                                         |
|  2. RIDER ENTERS DESTINATION                                           |
|     ETA Service calculates route and estimate                         |
|     Pricing Service calculates fare (including surge if any)          |
|     Payment Service pre-authorizes payment method                     |
|                                                                         |
|  3. RIDER CONFIRMS RIDE                                                |
|     Ride Service creates ride record (status: REQUESTED)              |
|     Matching Service queries Redis for nearby available drivers       |
|     ETA calculated for top candidates                                 |
|     Best driver selected, distributed lock acquired                   |
|     Ride assigned to driver (status: ACCEPTED)                        |
|                                                                         |
|  4. DRIVER RECEIVES REQUEST                                            |
|     Push via WebSocket to driver's gateway server                     |
|     Driver taps Accept                                                |
|     Ride status: EN_ROUTE                                             |
|                                                                         |
|  5. DRIVER EN ROUTE                                                    |
|     Location updates stream to Kafka > Redis                          |
|     Rider app polls/subscribes for driver location                    |
|     Live map shows driver approaching                                 |
|                                                                         |
|  6. DRIVER ARRIVES                                                     |
|     Status: ARRIVED, 5-minute timer starts                            |
|     Rider notified: "Your driver is here"                             |
|                                                                         |
|  7. RIDE STARTS                                                        |
|     Driver swipes "Start Ride"                                        |
|     Status: IN_PROGRESS                                               |
|     GPS trace recorded for fare calculation                           |
|                                                                         |
|  8. RIDE ENDS                                                          |
|     Driver swipes "End Ride"                                          |
|     Fare calculated from GPS trace                                    |
|     Payment captured                                                  |
|     Status: COMPLETED > PAID                                          |
|     Receipt sent, rating requested                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 13: SCALING TO MILLIONS

Our architecture needs to handle 100M daily active users, 5M drivers,
and 20M rides per day. Here's how we scale each component.

### 13.1 HORIZONTAL SCALING STRATEGY

```
+-------------------------------------------------------------------------+
|                    SCALING EACH LAYER                                   |
|                                                                         |
|  STATELESS SERVICES (Ride, Matching, ETA):                            |
|  * Run in Kubernetes with Horizontal Pod Autoscaler                   |
|  * Scale based on CPU utilization or request queue depth             |
|  * No sticky sessions needed — any pod can handle any request        |
|                                                                         |
|  WEBSOCKET GATEWAYS:                                                   |
|  * Each server handles 50K connections                                |
|  * Scale by adding more gateway servers                               |
|  * Use Connection Registry (Redis) for routing                        |
|                                                                         |
|  REDIS:                                                                |
|  * Cluster mode with 6+ nodes                                         |
|  * Partition by city for geospatial data                             |
|  * Each city can scale independently                                  |
|                                                                         |
|  POSTGRESQL:                                                           |
|  * Primary-replica setup for read scaling                            |
|  * Shard by city_id for write scaling                                |
|  * PgBouncer for connection pooling                                  |
|                                                                         |
|  KAFKA:                                                                |
|  * Partition by city for location events                             |
|  * Multiple consumer groups for different consumers                   |
|  * Retain 7 days for replay capability                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 13.2 GEOGRAPHIC SHARDING

Most ride-hailing activity is local. A driver in NYC never needs to see
riders in London. We use this property for geographic sharding:

```
+-------------------------------------------------------------------------+
|                    GEOGRAPHIC SHARDING                                  |
|                                                                         |
|  +---------------+    +---------------+    +---------------+           |
|  |   US-EAST     |    |   US-WEST     |    |   EU-WEST     |           |
|  |   Region      |    |   Region      |    |   Region      |           |
|  +---------------+    +---------------+    +---------------+           |
|  | NYC Shard     |    | SF Shard      |    | London Shard  |           |
|  | Boston Shard  |    | LA Shard      |    | Paris Shard   |           |
|  | Miami Shard   |    | Seattle Shard |    | Berlin Shard  |           |
|  +---------------+    +---------------+    +---------------+           |
|                                                                         |
|  Benefits:                                                             |
|  * Data locality — queries only touch local data                      |
|  * Independent scaling — busy cities get more resources               |
|  * Failure isolation — NYC outage doesn't affect London              |
|  * Regulatory compliance — EU data stays in EU                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 14: TRADE-OFFS AND DESIGN DECISIONS

Every architectural decision involves trade-offs. Here are the key ones
we made and why.

### 14.1 CRITICAL TRADE-OFFS

```
+-------------------------------------------------------------------------+
|  TRADE-OFF 1: Eventual vs Strong Consistency                           |
|  ------------------------------------------                            |
|  Location data: Eventual consistency (OK if few seconds stale)        |
|  Ride assignments: Strong consistency (can't double-book)             |
|  Payments: Strong consistency + idempotency                           |
|                                                                         |
|  Why: Forcing strong consistency everywhere would kill performance.   |
|  Location updates at 1M+/sec would be impossible with synchronous    |
|  writes. But for ride assignments, we accept the latency cost.       |
+-------------------------------------------------------------------------+
|  TRADE-OFF 2: Batched vs Immediate Matching                           |
|  -------------------------------------------                          |
|  We batch ride requests for 2 seconds before matching.               |
|                                                                         |
|  Cost: 2-second delay for every rider                                 |
|  Benefit: 15-20% reduction in average wait times (better global match)|
|                                                                         |
|  Why: The 2-second delay is imperceptible, but the wait time         |
|  improvement is noticeable. Users care about total wait, not request |
|  processing time.                                                     |
+-------------------------------------------------------------------------+
|  TRADE-OFF 3: Redis Lock vs Database Lock                             |
|  ----------------------------------------                              |
|  We use Redis for distributed locks instead of database locks.         |
|                                                                        |
|  Redis advantages: Sub-millisecond latency, no DB connection needed    |
|  Redis risks: If Redis is partitioned, lock might be inconsistent      |
|                                                                         |
|  Mitigation: Database is always the source of truth. Redis lock is   |
|  an optimization — we verify in DB before committing.                |
+-------------------------------------------------------------------------+
|  TRADE-OFF 4: Kafka vs Direct Database Writes                         |
|  ---------------------------------------------                        |
|  Location updates go through Kafka before database.                  |
|                                                                         |
|  Cost: Additional latency for historical storage                      |
|  Benefit: Decoupling, replay capability, handles bursts               |
|                                                                         |
|  Why: Real-time data goes to Redis first (synchronous). Kafka adds   |
|  durability and allows multiple consumers without affecting the      |
|  hot path.                                                            |
+-------------------------------------------------------------------------+
```

### 14.2 WHAT WE LEARNED

Building Uber teaches us several key distributed systems principles:

1. USE THE RIGHT TOOL FOR EACH JOB
Don't use one database for everything. PostgreSQL for transactions,
Redis for real-time, Cassandra for time-series. Each is optimized
for its use case.

2. DESIGN FOR FAILURE
Assume every component will fail. Use timeouts, retries, circuit
breakers, and graceful degradation. The system should never
completely stop working.

3. CONSISTENCY IS A SPECTRUM
Not everything needs strong consistency. Identify where eventual
consistency is acceptable and use it to improve performance.

4. OPTIMIZE THE COMMON PATH
Location updates (hot path) must be fast. Historical storage can
be async. Design differently for different access patterns.

5. GEOGRAPHIC LOCALITY IS POWERFUL
Riders and drivers in NYC don't interact with those in London.
Exploit this for sharding, caching, and latency optimization.

## FINAL ARCHITECTURE SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  UBER SYSTEM DESIGN - KEY COMPONENTS                                   |
|  ====================================                                  |
|                                                                         |
|  COMMUNICATION:                                                        |
|  * WebSocket for driver location streaming (1M+ connections)          |
|  * REST for rider app API                                             |
|  * gRPC for inter-service communication                               |
|                                                                         |
|  STORAGE:                                                              |
|  * PostgreSQL: Users, rides, payments (ACID)                          |
|  * Redis: Real-time locations, sessions, locks (sub-ms)               |
|  * Cassandra: Location history (high-write, time-series)              |
|  * Kafka: Event streaming (durable, replayable)                       |
|                                                                         |
|  ALGORITHMS:                                                           |
|  * H3: Hexagonal geospatial indexing                                  |
|  * Contraction Hierarchies: Fast routing                              |
|  * Hungarian: Optimal ride matching                                   |
|  * Kalman Filter: GPS smoothing                                       |
|                                                                         |
|  PATTERNS:                                                             |
|  * Distributed locking (Redis SETNX with TTL)                         |
|  * Idempotency keys (exactly-once payments)                           |
|  * Saga pattern (distributed transactions)                            |
|  * State machine (ride lifecycle)                                     |
|  * Connection registry (WebSocket routing)                            |
|                                                                         |
|  SCALING:                                                              |
|  * Geographic sharding (city-level partitioning)                      |
|  * Horizontal scaling (stateless services)                            |
|  * Read replicas (PostgreSQL)                                         |
|  * Multi-region deployment (low latency, high availability)           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 15: THEORETICAL FOUNDATIONS

### 15.1 CAP THEOREM

```
+-------------------------------------------------------------------------+
|                    CAP THEOREM FOR RIDE-HAILING                         |
|                                                                         |
|  CONSISTENCY (C):  All nodes see same data                             |
|  AVAILABILITY (A): System always responds                              |
|  PARTITION (P):    System works despite network failures               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  UBER SYSTEM CHOICES:                                                   |
|                                                                         |
|  DRIVER LOCATIONS (AP):                                                 |
|  ---------------------                                                  |
|  * Availability over consistency                                       |
|  * Stale location (5 sec old) is acceptable                           |
|  * System must always show available drivers                          |
|  * Redis with eventual consistency                                    |
|                                                                         |
|  RIDE STATE (CP):                                                       |
|  -----------------                                                      |
|  * Consistency over availability for ride assignment                  |
|  * Can't have two riders assigned same driver                         |
|  * Brief unavailability acceptable                                    |
|  * PostgreSQL with strong consistency                                 |
|                                                                         |
|  PAYMENT PROCESSING (CP):                                               |
|  ------------------------                                               |
|  * Strong consistency required                                         |
|  * Exactly-once semantics                                             |
|  * ACID transactions                                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 15.2 ACID vs BASE

```
+-------------------------------------------------------------------------+
|                    UBER DATA CLASSIFICATION                             |
|                                                                         |
|  ACID (PostgreSQL):                                                     |
|  -------------------                                                    |
|  * Ride creation and assignment                                        |
|  * Payment processing                                                  |
|  * User account operations                                             |
|  * Driver-rider matching confirmation                                  |
|                                                                         |
|  Transaction Example:                                                   |
|  BEGIN;                                                                 |
|    UPDATE rides SET driver_id = 123, status = 'ASSIGNED'              |
|    WHERE ride_id = 456 AND status = 'PENDING';                        |
|    UPDATE drivers SET status = 'ON_RIDE'                              |
|    WHERE driver_id = 123 AND status = 'AVAILABLE';                    |
|  COMMIT;                                                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  BASE (Redis, Cassandra):                                               |
|  -------------------------                                              |
|  * Real-time driver locations                                         |
|  * Location history                                                    |
|  * ETA calculations                                                    |
|  * Surge pricing data                                                 |
|                                                                         |
|  Eventually consistent, but always available                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 15.3 CONSISTENCY MODELS

```
+-------------------------------------------------------------------------+
|                    CONSISTENCY IN UBER                                  |
|                                                                         |
|  LINEARIZABLE (Strongest):                                              |
|  --------------------------                                             |
|  * Ride assignment: Only one driver gets the ride                      |
|  * Payment deduction: Exactly once                                     |
|  * Implementation: PostgreSQL with SELECT FOR UPDATE                   |
|                                                                         |
|  EVENTUAL CONSISTENCY:                                                  |
|  ---------------------                                                  |
|  * Driver location updates                                             |
|  * Location history in Cassandra                                       |
|  * Driver may appear in slightly wrong position briefly               |
|  * Convergence within seconds                                         |
|                                                                         |
|  READ-YOUR-WRITES:                                                      |
|  -------------------                                                    |
|  * Driver updates location > immediately sees own position            |
|  * Rider requests ride > immediately sees pending status              |
|  * Implementation: Read from leader after write                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 15.4 DATABASE SCALING CONCEPTS

```
+-------------------------------------------------------------------------+
|                    UBER SCALING STRATEGIES                              |
|                                                                         |
|  GEOGRAPHIC SHARDING (Primary Strategy):                                |
|  ----------------------------------------                               |
|                                                                         |
|  NYC users > NYC shard                                                 |
|  LA users > LA shard                                                   |
|  London users > London shard                                           |
|                                                                         |
|  WHY IT WORKS:                                                          |
|  * NYC rider never matches with LA driver                             |
|  * Natural data isolation                                             |
|  * Lower latency (data near users)                                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  REPLICATION:                                                           |
|                                                                         |
|  PostgreSQL (Single-Leader):                                           |
|  * Writes > Leader                                                    |
|  * Reads > Followers (read replicas)                                  |
|  * Ride assignments: Read from leader (consistency)                   |
|  * Historical data: Read from followers (performance)                 |
|                                                                         |
|  Cassandra (Leaderless):                                               |
|  * Multi-master writes                                                |
|  * Location history at massive scale                                  |
|  * Tunable consistency (quorum reads/writes)                         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  H3 GEOSPATIAL INDEXING:                                               |
|  -------------------------                                              |
|  * World divided into hexagonal cells                                 |
|  * Each cell has unique ID                                            |
|  * "Find drivers near me" = Find drivers in nearby cells             |
|  * O(1) lookup instead of distance calculation                       |
|                                                                         |
|     ⬡ ⬡ ⬡                                                             |
|    ⬡ ● ⬡ ⬡    ● = rider, search adjacent hexagons                    |
|     ⬡ ⬡ ⬡                                                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 15.5 CACHING PATTERNS

```
+-------------------------------------------------------------------------+
|                    UBER CACHING STRATEGY                                |
|                                                                         |
|  DRIVER LOCATIONS (Write-Through to Redis):                             |
|  --------------------------------------------                           |
|  * Driver app sends location                                           |
|  * Write directly to Redis (GEOADD)                                   |
|  * TTL: 60 seconds (driver timeout)                                   |
|  * Async: Kafka > Cassandra (history)                                 |
|                                                                         |
|  RIDE STATE (Cache-Aside):                                              |
|  ---------------------------                                            |
|  * Read: Check Redis cache first                                       |
|  * Miss: Query PostgreSQL, cache result                               |
|  * Write: Update DB, invalidate cache                                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CACHE LAYERS:                                                          |
|  +------------------+------------+------------------------------------+|
|  | Data             | Store      | TTL                                ||
|  +------------------+------------+------------------------------------+|
|  | Driver locations | Redis GEO  | 60 sec (auto-expire if no update) ||
|  | Surge pricing    | Redis      | 5 min                              ||
|  | User sessions    | Redis      | 24 hours                           ||
|  | Ride state       | Redis      | Until ride completes               ||
|  | Map tiles        | CDN        | 1 week                             ||
|  | Route cache      | Redis      | 15 min (traffic changes)           ||
|  +------------------+------------+------------------------------------+|
|                                                                         |
+-------------------------------------------------------------------------+
```

### 15.6 LOAD BALANCING

```
+-------------------------------------------------------------------------+
|                    UBER LOAD BALANCING                                  |
|                                                                         |
|  LAYER 4 (TCP/NLB):                                                     |
|  -------------------                                                    |
|  * WebSocket connections (driver location streaming)                  |
|  * High throughput, low latency                                       |
|  * No SSL termination overhead                                        |
|                                                                         |
|  LAYER 7 (HTTP/ALB):                                                    |
|  -------------------                                                    |
|  * Rider REST API                                                      |
|  * Path-based routing (/api/rides, /api/drivers)                      |
|  * SSL termination                                                    |
|  * Request inspection                                                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WEBSOCKET ROUTING:                                                     |
|  -------------------                                                    |
|  * Connection registry tracks which server has each driver            |
|  * "Send message to driver 123" > Lookup server > Route              |
|  * Sticky sessions (IP hash) for connection stability                 |
|                                                                         |
|  GEOGRAPHIC ROUTING (DNS-based):                                        |
|  ---------------------------------                                      |
|  * NYC users > NYC data center                                        |
|  * EU users > EU data center                                          |
|  * Route53 latency-based routing                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 15.7 RATE LIMITING

```
+-------------------------------------------------------------------------+
|                    UBER RATE LIMITING                                   |
|                                                                         |
|  TOKEN BUCKET FOR API:                                                  |
|  ---------------------                                                  |
|  * Allows bursts (user scrolling map)                                 |
|  * Smooth rate limiting over time                                     |
|                                                                         |
|  +-------------------------+----------------------------------------+  |
|  | Endpoint                | Limit                                  |  |
|  +-------------------------+----------------------------------------+  |
|  | Location updates        | 1/second per driver                    |  |
|  | Ride requests           | 5/minute per user                      |  |
|  | Driver search           | 10/minute per user                     |  |
|  | Price quotes            | 20/minute per user                     |  |
|  | OTP requests            | 3/minute per phone                     |  |
|  +-------------------------+----------------------------------------+  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SURGE PROTECTION:                                                      |
|  ------------------                                                     |
|  When system overloaded (concert ending, NYE):                         |
|  * Adaptive rate limiting (lower limits)                              |
|  * Priority queue (existing rides > new requests)                     |
|  * Circuit breaker on non-critical services                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 15.8 MESSAGE QUEUE SEMANTICS

```
+-------------------------------------------------------------------------+
|                    KAFKA IN UBER                                        |
|                                                                         |
|  DELIVERY GUARANTEES:                                                   |
|  ---------------------                                                  |
|                                                                         |
|  Location Updates: AT-LEAST-ONCE                                       |
|  * Lost location is OK (next one coming in 4 sec)                     |
|  * Duplicate is OK (just overwrite)                                   |
|                                                                         |
|  Ride Events: AT-LEAST-ONCE + IDEMPOTENT CONSUMER                     |
|  * Consumer checks if event already processed                         |
|  * Idempotency key = ride_id + event_type + timestamp                |
|                                                                         |
|  Payment Events: EXACTLY-ONCE (Kafka Transactions)                    |
|  * Transactional producer                                             |
|  * Read committed isolation                                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  ORDERING:                                                              |
|  ----------                                                             |
|  * Partition key = ride_id                                            |
|  * All events for same ride > same partition > ordered               |
|                                                                         |
|  Ride lifecycle (ordered within partition):                            |
|  REQUESTED > MATCHED > DRIVER_ARRIVED > IN_PROGRESS > COMPLETED       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 15.9 MICROSERVICES PATTERNS

```
+-------------------------------------------------------------------------+
|                    UBER PATTERNS                                        |
|                                                                         |
|  CIRCUIT BREAKER:                                                       |
|  -----------------                                                      |
|  Payment gateway down? Don't keep calling, fail fast.                  |
|                                                                         |
|  CLOSED > (failures exceed threshold) > OPEN                           |
|  OPEN > (timeout) > HALF-OPEN > (test success) > CLOSED               |
|                                                                         |
|  Used for:                                                              |
|  * Payment service                                                     |
|  * Maps/routing service                                               |
|  * Notification service                                               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SAGA PATTERN:                                                          |
|  --------------                                                         |
|  Ride completion involves multiple services:                           |
|                                                                         |
|  1. Update ride status > SUCCESS                                      |
|  2. Calculate fare > SUCCESS                                          |
|  3. Charge payment > FAILED                                           |
|  4. COMPENSATE: Revert fare, update status to PAYMENT_FAILED         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  STATE MACHINE:                                                         |
|  ---------------                                                        |
|  Ride states with valid transitions:                                   |
|                                                                         |
|  REQUESTED > MATCHING > MATCHED > DRIVER_ARRIVED                      |
|           ↘  CANCELLED   v            v                               |
|                    IN_PROGRESS > COMPLETED                            |
|                         v                                             |
|                    CANCELLED                                          |
|                                                                         |
|  Each state transition has:                                            |
|  * Allowed next states                                                |
|  * Actions to perform                                                 |
|  * Validation rules                                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 15.10 API DESIGN

```
+-------------------------------------------------------------------------+
|                    UBER API DESIGN                                      |
|                                                                         |
|  REST (Rider App):                                                      |
|  ------------------                                                     |
|  POST   /rides                Create ride request                      |
|  GET    /rides/{id}           Get ride details                         |
|  DELETE /rides/{id}           Cancel ride                              |
|  GET    /rides/{id}/driver    Get assigned driver                      |
|                                                                         |
|  gRPC (Service-to-Service):                                             |
|  ---------------------------                                            |
|  * Lower latency than REST                                            |
|  * Strongly typed (protobuf)                                          |
|  * Bi-directional streaming                                           |
|                                                                         |
|  WebSocket (Driver Location):                                          |
|  -----------------------------                                          |
|  * Persistent connection                                               |
|  * Driver sends location every 4 seconds                              |
|  * Server pushes ride requests                                        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  IDEMPOTENCY:                                                           |
|  -------------                                                          |
|  POST /rides                                                           |
|  Idempotency-Key: user123-1703123456                                  |
|                                                                         |
|  * User clicks "Request Ride" twice (network retry)                   |
|  * Same idempotency key = same ride returned                          |
|  * No duplicate ride created                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF DOCUMENT

