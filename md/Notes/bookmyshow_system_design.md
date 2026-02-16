# BOOKMYSHOW SYSTEM DESIGN — DEEP DIVE
*Movie & Event Ticket Booking Platform*

### Table of Contents

Part 1: Requirements & Core Challenges
Part 1B: Data Model & API Contracts
Part 2: High-Level Architecture
2.1 System Architecture Diagram
2.2 Microservices Breakdown
2.3 Technology Choices & Rationale
2.4 Security Model (Authentication & Authorization)    < NEW
2.5 Public vs Private (Internal) APIs                  < NEW
2.6 Database-to-Service Ownership Mapping              < NEW

Part 3: Theater & Show Management
Part 4: Seat Selection & Booking (The Hard Problem)
Part 5: Distributed Locking for Seats
5.1 Redis SETNX for Atomic Locks
5.2 Atomic Multi-Seat Locking (Lua Scripts)
5.3 Safe Lock Release
5.4 Pessimistic vs Optimistic Locking
5.5 Complete Booking Sequence
5.6 Redlock Algorithm (Advanced Distributed Locking)   < NEW

Part 6: Payment Processing & Idempotency
Part 7: Search & Discovery
Part 8: Caching Strategy
Part 9: Notification System
Part 10: Database Architecture
Part 11: Failure Scenarios & Recovery
Part 12: Scaling & Performance
Part 13: Trade-offs & Decisions
Part 14: Interview Follow-ups
14.1 Common Interview Questions (Q1-Q8)
14.1+ Additional Questions (Q9-Q16)                    < NEW
14.2 Deep Dive Interview Questions (Q17-Q20)           < NEW
14.3 Homework Assignments

Part 15: Theoretical Foundations
15.1 CAP Theorem
15.2 ACID vs BASE
15.3 Consistency Models
15.4 Database Scaling Concepts
15.5 Caching Patterns
15.6 Load Balancing
15.7 Rate Limiting Algorithms
15.8 Message Queue Semantics
15.9 Distributed Locking Theory
15.10 API Design Principles

## A REAL-WORLD PROBLEM

Imagine this scenario:

Friday evening, 7 PM. A blockbuster movie just released.

100,000 users open BookMyShow simultaneously.
They all want the 9 PM show at the same theater.
The theater has only 300 seats.

User A and User B both click on seat F-12 at the exact same moment.

QUESTIONS:
- Who gets the seat?
- How do we prevent double-booking?
- How do we handle 100,000 concurrent users for 300 seats?
- What if User A selects the seat but never pays?
- How do we show real-time seat availability to everyone?

This is the BookMyShow problem — a classic example of:
- High-read, low-write with extreme contention
- Inventory management with finite resources
- Distributed locking in a real-time system
- Handling traffic spikes (10x-100x normal load)

## PART 1: REQUIREMENTS & CORE CHALLENGES

### 1.1 FUNCTIONAL REQUIREMENTS

USERS (Customers):
- Search movies by name, genre, language, city
- View movie details, trailers, reviews, ratings
- Browse theaters near their location
- View show timings for a movie at various theaters
- Select seats from an interactive seat map
- Hold seats temporarily during checkout
- Complete payment and receive tickets
- View booking history
- Cancel bookings (with refund policy)

**THEATER PARTNERS:**
- Onboard theaters with screen configurations
- Define seat layouts (rows, columns, categories)
- Create shows with pricing by seat category
- View booking reports and revenue
- Block seats for maintenance

**ADMIN:**
- Add/edit movies with metadata
- Manage theater partnerships
- Configure pricing rules, offers, discounts
- Monitor system health and fraud

### 1.2 NON-FUNCTIONAL REQUIREMENTS

**SCALE:**
- 50 million monthly active users
- 10,000+ theaters across 500+ cities
- 100,000+ shows daily
- 5 million bookings per day
- Peak: 500,000 concurrent users during blockbuster releases

**PERFORMANCE:**
- Seat map load: < 500ms
- Seat lock acquisition: < 100ms
- Search results: < 200ms
- Booking confirmation: < 3 seconds
- 99.9% availability

**CONSISTENCY:**
- NO double-booking (critical invariant)
- Seat availability must be eventually consistent (< 2 seconds)
- Payment and booking must be atomic

**RELIABILITY:**
- Zero lost bookings
- Graceful degradation under load
- Automatic recovery from failures

### 1.3 CAPACITY ESTIMATION

```
+-------------------------------------------------------------------------+
|                    TRAFFIC ESTIMATION                                   |
|                                                                         |
|  DAILY ACTIVE USERS:                                                   |
|  * 50M MAU > ~5M DAU (10% daily active)                               |
|                                                                         |
|  BOOKINGS:                                                             |
|  * 5M bookings/day                                                     |
|  * Peak hours (6 PM - 10 PM): 60% of bookings = 3M in 4 hours         |
|  * Peak TPS: 3M / (4 × 3600) ≈ 210 bookings/second                    |
|  * Spike during releases: 10x = 2,100 bookings/second                 |
|                                                                         |
|  READS (Seat Map Views):                                               |
|  * Each booking requires ~5 seat map views (browsing)                 |
|  * 5M × 5 = 25M seat map views/day                                    |
|  * Peak: 25M × 0.6 / (4 × 3600) ≈ 1,000 views/second                  |
|  * Spike: 10,000 views/second                                         |
|                                                                         |
|  READ:WRITE RATIO:                                                     |
|  * Seat map views : Bookings = 25M : 5M = 5:1                         |
|  * But seat locks are writes too!                                     |
|  * Effective ratio with locks: ~3:1                                   |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    STORAGE ESTIMATION                                   |
|                                                                         |
|  MOVIES:                                                               |
|  * 50,000 movies (historical + current)                               |
|  * ~10 KB per movie (metadata, images URLs)                           |
|  * Total: 500 MB                                                       |
|                                                                         |
|  THEATERS & SCREENS:                                                   |
|  * 10,000 theaters × 5 screens = 50,000 screens                       |
|  * ~5 KB per screen (layout, seat config)                             |
|  * Total: 250 MB                                                       |
|                                                                         |
|  SHOWS:                                                                |
|  * 100,000 shows/day × 30 days = 3M active shows                      |
|  * ~2 KB per show                                                      |
|  * Total: 6 GB                                                         |
|                                                                         |
|  SEAT INVENTORY (Hot Data):                                            |
|  * 3M shows × 300 seats average = 900M seat records                   |
|  * ~100 bytes per seat (status, lock, price)                          |
|  * Total: 90 GB (must be fast — Redis candidate)                      |
|                                                                         |
|  BOOKINGS:                                                             |
|  * 5M bookings/day × 365 days × 3 years = 5.5B bookings              |
|  * ~1 KB per booking                                                   |
|  * Total: 5.5 TB                                                       |
|                                                                         |
|  TOTAL: ~6 TB (manageable with sharding)                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 1.4 CORE DESIGN CHALLENGES

### CHALLENGE 1: THE DOUBLE-BOOKING PROBLEM

```
+-------------------------------------------------------------------------+
|  THE PROBLEM:                                                          |
|                                                                         |
|  User A                              User B                            |
|  ---------                           ---------                         |
|  T1: Check seat F-12 available? Y                                     |
|                                      T2: Check seat F-12 available? Y |
|  T3: Lock seat F-12                                                   |
|                                      T4: Lock seat F-12               |
|  T5: Complete payment                                                 |
|                                      T6: Complete payment             |
|  T7: Book seat F-12 Y                                                 |
|                                      T8: Book seat F-12 Y < PROBLEM!  |
|                                                                         |
|  Both users paid, both got confirmation — but only ONE seat exists!   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WHY IS THIS HARD?                                                     |
|  * Check and lock are separate operations (race window)               |
|  * Multiple servers handling concurrent requests                      |
|  * Database can't atomically check+lock across services               |
|                                                                         |
|  SOLUTION: Distributed locking with atomic operations                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CHALLENGE 2: TEMPORARY SEAT HOLDS (LOCK EXPIRY)

```
+-------------------------------------------------------------------------+
|  THE PROBLEM:                                                          |
|                                                                         |
|  User A selects seat F-12                                             |
|  System locks seat for 10 minutes                                     |
|  User A gets distracted, never pays                                   |
|  Seat is blocked for 10 minutes — lost revenue!                       |
|                                                                         |
|  Meanwhile, User B wanted that seat but couldn't book it.             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  TRADE-OFF:                                                            |
|  * Lock too short: User doesn't have time to pay                      |
|  * Lock too long: Seats blocked unnecessarily                         |
|                                                                         |
|  SOLUTION:                                                             |
|  * Typical lock duration: 8-10 minutes                                |
|  * Show countdown timer to user                                       |
|  * Auto-release on expiry (TTL-based)                                 |
|  * Allow lock extension if user is on payment page                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CHALLENGE 3: THUNDERING HERD (RELEASE DAY)

```
+-------------------------------------------------------------------------+
|  THE PROBLEM:                                                          |
|                                                                         |
|  Blockbuster movie release (e.g., Avengers)                           |
|  Advance booking opens at 12:00:00 AM                                 |
|                                                                         |
|  At 12:00:00 AM:                                                       |
|  * 500,000 users hit the system simultaneously                        |
|  * All want the same theater, same show                               |
|  * 300 seats, 500,000 requests                                        |
|                                                                         |
|  Normal load: 1,000 req/sec                                           |
|  Spike load: 100,000 req/sec (100x!)                                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTIONS:                                                            |
|  * Virtual waiting room / queue                                       |
|  * Rate limiting per user                                             |
|  * Pre-scaled infrastructure                                          |
|  * CDN for static assets                                              |
|  * Redis cluster for seat locks                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CHALLENGE 4: REAL-TIME SEAT AVAILABILITY

```
+-------------------------------------------------------------------------+
|  THE PROBLEM:                                                          |
|                                                                         |
|  User A is viewing seat map                                           |
|  User B books seat F-12                                               |
|  User A's screen still shows F-12 as available                        |
|  User A clicks F-12 > Error!                                          |
|                                                                         |
|  BAD USER EXPERIENCE                                                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTIONS:                                                            |
|  * WebSocket push for real-time updates                               |
|  * Polling every 5 seconds (simpler)                                  |
|  * Optimistic UI with server validation                               |
|  * Show "Someone else is viewing this seat" indicator                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CHALLENGE 5: PAYMENT FAILURES

```
+-------------------------------------------------------------------------+
|  THE PROBLEM:                                                          |
|                                                                         |
|  1. User selects seats (locked)                                       |
|  2. User initiates payment                                            |
|  3. Payment gateway times out                                         |
|  4. Did the payment succeed or fail?                                  |
|                                                                         |
|  SCENARIOS:                                                            |
|  * Money deducted but booking not confirmed > User angry              |
|  * Booking confirmed but money not deducted > Revenue loss            |
|  * User retries, double payment > Refund nightmare                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTIONS:                                                            |
|  * Idempotency keys for payment requests                              |
|  * Two-phase: Reserve seats > Charge > Confirm                        |
|  * Payment status polling                                             |
|  * Compensation (Saga pattern) for failures                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 1B: DATA MODEL & API CONTRACTS

### 1B.1 ENTITY RELATIONSHIP OVERVIEW

```
+-------------------------------------------------------------------------+
|                                                                         |
|   +--------+         +----------+         +---------+                  |
|   |  CITY  |--------<|  THEATER |--------<|  SCREEN |                  |
|   +--------+  has    +----------+  has    +----+----+                  |
|                            |                   |                        |
|                            | partner           | has                    |
|                            v                   v                        |
|                      +----------+        +-----------+                 |
|                      |  OWNER   |        | SEAT_TYPE |                 |
|                      +----------+        |  CONFIG   |                 |
|                                          +-----------+                 |
|                                                                         |
|   +--------+         +----------+         +---------+                  |
|   | MOVIE  |--------<|   SHOW   |--------<|  SEAT   |                  |
|   +--------+ screens +----+-----+  has    |INVENTORY|                  |
|       |                   |               +----+----+                  |
|       |                   |                    |                        |
|       | has               | for show          | booked in              |
|       v                   v                    v                        |
|   +--------+         +----------+         +---------+                  |
|   | CAST   |         |  USER    |-------->| BOOKING |                  |
|   | CREW   |         +----------+  makes  +----+----+                  |
|   +--------+                                   |                        |
|                                                | paid via              |
|                                                v                        |
|                                          +----------+                  |
|                                          | PAYMENT  |                  |
|                                          +----------+                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 1B.2 DATABASE SCHEMA (PostgreSQL)

**CITIES:**
```
+------------------------------------------------------------------------+
|  CREATE TABLE cities (                                                 |
|      id              UUID PRIMARY KEY,                                 |
|      name            VARCHAR(100) NOT NULL,                           |
|      state           VARCHAR(100),                                    |
|      country         VARCHAR(100) DEFAULT 'India',                    |
|      latitude        DECIMAL(10, 8),                                  |
|      longitude       DECIMAL(11, 8),                                  |
|      timezone        VARCHAR(50) DEFAULT 'Asia/Kolkata',              |
|      is_active       BOOLEAN DEFAULT true,                            |
|      created_at      TIMESTAMP DEFAULT NOW()                          |
|  );                                                                    |
+------------------------------------------------------------------------+
```

**MOVIES:**
```
+------------------------------------------------------------------------+
|  CREATE TABLE movies (                                                 |
|      id              UUID PRIMARY KEY,                                 |
|      title           VARCHAR(255) NOT NULL,                           |
|      description     TEXT,                                            |
|      duration_mins   INTEGER NOT NULL,                                |
|      language        VARCHAR(50),                                     |
|      genre           VARCHAR(100)[],           -- Array of genres     |
|      release_date    DATE,                                            |
|      certificate     VARCHAR(10),              -- U, UA, A, S         |
|      poster_url      VARCHAR(500),                                    |
|      trailer_url     VARCHAR(500),                                    |
|      avg_rating      DECIMAL(2,1) DEFAULT 0,                          |
|      total_ratings   INTEGER DEFAULT 0,                               |
|      is_active       BOOLEAN DEFAULT true,                            |
|      created_at      TIMESTAMP DEFAULT NOW(),                         |
|      updated_at      TIMESTAMP DEFAULT NOW()                          |
|  );                                                                    |
|                                                                        |
|  CREATE INDEX idx_movies_release ON movies(release_date);             |
|  CREATE INDEX idx_movies_language ON movies(language);                |
|  CREATE INDEX idx_movies_genre ON movies USING GIN(genre);            |
+------------------------------------------------------------------------+
```

**THEATERS:**
```
+------------------------------------------------------------------------+
|  CREATE TABLE theaters (                                               |
|      id              UUID PRIMARY KEY,                                 |
|      name            VARCHAR(255) NOT NULL,                           |
|      city_id         UUID REFERENCES cities(id),                      |
|      address         TEXT,                                            |
|      latitude        DECIMAL(10, 8),                                  |
|      longitude       DECIMAL(11, 8),                                  |
|      geohash         VARCHAR(12),              -- For geo queries     |
|      contact_phone   VARCHAR(20),                                     |
|      amenities       VARCHAR(100)[],           -- Parking, Food, etc  |
|      is_active       BOOLEAN DEFAULT true,                            |
|      created_at      TIMESTAMP DEFAULT NOW()                          |
|  );                                                                    |
|                                                                        |
|  CREATE INDEX idx_theaters_city ON theaters(city_id);                 |
|  CREATE INDEX idx_theaters_geohash ON theaters(geohash);              |
+------------------------------------------------------------------------+
```

**SCREENS:**
```
+------------------------------------------------------------------------+
|  CREATE TABLE screens (                                                |
|      id              UUID PRIMARY KEY,                                 |
|      theater_id      UUID REFERENCES theaters(id),                    |
|      name            VARCHAR(50) NOT NULL,     -- "Screen 1", "IMAX"  |
|      screen_type     VARCHAR(50),              -- Regular, IMAX, 4DX  |
|      total_seats     INTEGER NOT NULL,                                |
|      seat_layout     JSONB NOT NULL,           -- Row/column config   |
|      is_active       BOOLEAN DEFAULT true,                            |
|      created_at      TIMESTAMP DEFAULT NOW()                          |
|  );                                                                    |
|                                                                        |
|  -- seat_layout example:                                               |
|  -- {                                                                  |
|  --   "rows": ["A","B","C","D","E","F","G","H","I","J"],              |
|  --   "seatsPerRow": {"A":10,"B":12,"C":12,...},                      |
|  --   "categories": {                                                  |
|  --     "PLATINUM": ["A","B"],                                        |
|  --     "GOLD": ["C","D","E","F"],                                    |
|  --     "SILVER": ["G","H","I","J"]                                   |
|  --   },                                                               |
|  --   "aisles": [5, 12],  -- Gaps between seats                       |
|  --   "blocked": ["A-1", "J-12"]  -- Permanently unavailable          |
|  -- }                                                                  |
+------------------------------------------------------------------------+
```

**SHOWS:**
```
+------------------------------------------------------------------------+
|  CREATE TABLE shows (                                                  |
|      id              UUID PRIMARY KEY,                                 |
|      movie_id        UUID REFERENCES movies(id),                      |
|      screen_id       UUID REFERENCES screens(id),                     |
|      show_date       DATE NOT NULL,                                   |
|      start_time      TIME NOT NULL,                                   |
|      end_time        TIME NOT NULL,                                   |
|      language        VARCHAR(50),              -- Dubbed version      |
|      format          VARCHAR(20),              -- 2D, 3D, IMAX        |
|      pricing         JSONB NOT NULL,           -- By seat category    |
|      available_seats INTEGER NOT NULL,                                |
|      status          VARCHAR(20) DEFAULT 'ACTIVE',                    |
|      created_at      TIMESTAMP DEFAULT NOW()                          |
|  );                                                                    |
|                                                                        |
|  -- pricing example:                                                   |
|  -- {"PLATINUM": 500, "GOLD": 350, "SILVER": 200}                     |
|                                                                        |
|  CREATE INDEX idx_shows_movie ON shows(movie_id);                     |
|  CREATE INDEX idx_shows_screen ON shows(screen_id);                   |
|  CREATE INDEX idx_shows_date ON shows(show_date);                     |
|  CREATE UNIQUE INDEX idx_shows_screen_time                            |
|      ON shows(screen_id, show_date, start_time);                      |
+------------------------------------------------------------------------+
```

SEAT_INVENTORY (Per Show):
```
+------------------------------------------------------------------------+
|  CREATE TABLE seat_inventory (                                         |
|      id              UUID PRIMARY KEY,                                 |
|      show_id         UUID REFERENCES shows(id),                       |
|      seat_number     VARCHAR(10) NOT NULL,     -- "A-1", "F-12"       |
|      seat_category   VARCHAR(20) NOT NULL,     -- PLATINUM, GOLD, etc |
|      price           DECIMAL(10, 2) NOT NULL,                         |
|      status          VARCHAR(20) DEFAULT 'AVAILABLE',                 |
|                      -- AVAILABLE, LOCKED, BOOKED, BLOCKED            |
|      locked_by       UUID,                     -- User who locked     |
|      locked_until    TIMESTAMP,                -- Lock expiry         |
|      booking_id      UUID,                     -- If booked           |
|      version         INTEGER DEFAULT 0,        -- Optimistic lock     |
|      created_at      TIMESTAMP DEFAULT NOW(),                         |
|      updated_at      TIMESTAMP DEFAULT NOW()                          |
|  );                                                                    |
|                                                                        |
|  CREATE UNIQUE INDEX idx_seat_show_number                             |
|      ON seat_inventory(show_id, seat_number);                         |
|  CREATE INDEX idx_seat_status ON seat_inventory(show_id, status);     |
|  CREATE INDEX idx_seat_locked_until ON seat_inventory(locked_until)   |
|      WHERE status = 'LOCKED';                                         |
+------------------------------------------------------------------------+
```

**USERS:**
```
+------------------------------------------------------------------------+
|  CREATE TABLE users (                                                  |
|      id              UUID PRIMARY KEY,                                 |
|      email           VARCHAR(255) UNIQUE,                             |
|      phone           VARCHAR(20) UNIQUE,                              |
|      name            VARCHAR(255),                                    |
|      password_hash   VARCHAR(255),                                    |
|      city_id         UUID REFERENCES cities(id),                      |
|      preferences     JSONB,                    -- Language, genres    |
|      is_verified     BOOLEAN DEFAULT false,                           |
|      created_at      TIMESTAMP DEFAULT NOW(),                         |
|      last_login      TIMESTAMP                                        |
|  );                                                                    |
+------------------------------------------------------------------------+
```

**BOOKINGS:**
```
+------------------------------------------------------------------------+
|  CREATE TABLE bookings (                                               |
|      id              UUID PRIMARY KEY,                                 |
|      user_id         UUID REFERENCES users(id),                       |
|      show_id         UUID REFERENCES shows(id),                       |
|      seats           VARCHAR(10)[] NOT NULL,   -- ["A-1", "A-2"]      |
|      seat_count      INTEGER NOT NULL,                                |
|      total_amount    DECIMAL(10, 2) NOT NULL,                         |
|      convenience_fee DECIMAL(10, 2) DEFAULT 0,                        |
|      discount        DECIMAL(10, 2) DEFAULT 0,                        |
|      final_amount    DECIMAL(10, 2) NOT NULL,                         |
|      status          VARCHAR(20) DEFAULT 'PENDING',                   |
|                      -- PENDING, CONFIRMED, CANCELLED, EXPIRED        |
|      booking_code    VARCHAR(20) UNIQUE,       -- QR code content     |
|      booked_at       TIMESTAMP,                                       |
|      cancelled_at    TIMESTAMP,                                       |
|      cancel_reason   VARCHAR(255),                                    |
|      created_at      TIMESTAMP DEFAULT NOW()                          |
|  );                                                                    |
|                                                                        |
|  CREATE INDEX idx_bookings_user ON bookings(user_id);                 |
|  CREATE INDEX idx_bookings_show ON bookings(show_id);                 |
|  CREATE INDEX idx_bookings_code ON bookings(booking_code);            |
+------------------------------------------------------------------------+
```

**PAYMENTS:**
```
+------------------------------------------------------------------------+
|  CREATE TABLE payments (                                               |
|      id              UUID PRIMARY KEY,                                 |
|      booking_id      UUID REFERENCES bookings(id),                    |
|      user_id         UUID REFERENCES users(id),                       |
|      amount          DECIMAL(10, 2) NOT NULL,                         |
|      payment_method  VARCHAR(50),              -- UPI, Card, Wallet   |
|      payment_gateway VARCHAR(50),              -- Razorpay, Paytm     |
|      gateway_txn_id  VARCHAR(255),                                    |
|      idempotency_key VARCHAR(255) UNIQUE,      -- Prevent duplicates  |
|      status          VARCHAR(20) DEFAULT 'INITIATED',                 |
|                      -- INITIATED, SUCCESS, FAILED, REFUNDED          |
|      failure_reason  VARCHAR(255),                                    |
|      created_at      TIMESTAMP DEFAULT NOW(),                         |
|      completed_at    TIMESTAMP                                        |
|  );                                                                    |
|                                                                        |
|  CREATE INDEX idx_payments_booking ON payments(booking_id);           |
|  CREATE INDEX idx_payments_user ON payments(user_id);                 |
|  CREATE INDEX idx_payments_idempotency ON payments(idempotency_key);  |
+------------------------------------------------------------------------+
```

### 1B.3 REDIS DATA STRUCTURES (Hot Data)

```
+-------------------------------------------------------------------------+
|                    REDIS KEY PATTERNS                                   |
|                                                                         |
|  SEAT LOCKS (Distributed Lock):                                        |
|  ---------------------------------                                     |
|  Key:    seat_lock:{show_id}:{seat_number}                            |
|  Value:  {user_id}:{lock_token}                                       |
|  TTL:    600 seconds (10 minutes)                                     |
|                                                                         |
|  Example:                                                              |
|  SET seat_lock:show_abc:F-12 "user_123:token_xyz" NX EX 600          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SEAT AVAILABILITY (Bitmap for fast check):                           |
|  -------------------------------------------                           |
|  Key:    seats_available:{show_id}                                    |
|  Type:   Hash                                                          |
|  Fields: seat_number > status (0=available, 1=locked, 2=booked)       |
|                                                                         |
|  Example:                                                              |
|  HSET seats_available:show_abc A-1 0 A-2 1 A-3 2                      |
|  HGET seats_available:show_abc F-12                                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SHOW METADATA CACHE:                                                  |
|  --------------------                                                  |
|  Key:    show:{show_id}                                               |
|  Type:   Hash                                                          |
|  TTL:    3600 seconds (1 hour)                                        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  USER SESSION:                                                         |
|  ------------                                                          |
|  Key:    session:{session_id}                                         |
|  Value:  JSON (user_id, city, preferences)                            |
|  TTL:    86400 seconds (24 hours)                                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  RATE LIMITING:                                                        |
|  --------------                                                        |
|  Key:    rate_limit:{user_id}:{action}                                |
|  Type:   Counter with TTL                                             |
|                                                                         |
|  Example:                                                              |
|  INCR rate_limit:user_123:seat_lock                                   |
|  EXPIRE rate_limit:user_123:seat_lock 60                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 1B.4 REST API CONTRACTS

**MOVIE DISCOVERY:**
```
+-------------------------------------------------------------------------+
|  GET /api/v1/movies                                                    |
|  ---------------------                                                 |
|  Query Params:                                                         |
|    city_id       (required)  - User's city                            |
|    language      (optional)  - Filter by language                     |
|    genre         (optional)  - Filter by genre                        |
|    date          (optional)  - Show date (default: today)             |
|    page          (optional)  - Pagination                             |
|    limit         (optional)  - Items per page (default: 20)           |
|                                                                         |
|  Response:                                                             |
|  {                                                                     |
|    "movies": [                                                         |
|      {                                                                 |
|        "id": "movie_abc",                                             |
|        "title": "Avengers: Endgame",                                  |
|        "duration_mins": 181,                                          |
|        "language": "English",                                         |
|        "genre": ["Action", "Sci-Fi"],                                 |
|        "certificate": "UA",                                           |
|        "poster_url": "https://cdn.../poster.jpg",                     |
|        "avg_rating": 4.5,                                             |
|        "formats": ["2D", "3D", "IMAX"]                                |
|      }                                                                 |
|    ],                                                                  |
|    "pagination": { "page": 1, "total_pages": 5 }                      |
|  }                                                                     |
+-------------------------------------------------------------------------+
```

**SHOW LISTINGS:**
```
+-------------------------------------------------------------------------+
|  GET /api/v1/movies/{movie_id}/shows                                   |
|  ------------------------------------                                  |
|  Query Params:                                                         |
|    city_id       (required)  - User's city                            |
|    date          (required)  - Show date                              |
|    format        (optional)  - 2D, 3D, IMAX                           |
|    language      (optional)  - Filter dubbed versions                 |
|                                                                         |
|  Response:                                                             |
|  {                                                                     |
|    "theaters": [                                                       |
|      {                                                                 |
|        "id": "theater_xyz",                                           |
|        "name": "PVR Cinemas, Phoenix Mall",                           |
|        "address": "123 MG Road...",                                   |
|        "distance_km": 2.5,                                            |
|        "shows": [                                                      |
|          {                                                             |
|            "id": "show_123",                                          |
|            "start_time": "14:30",                                     |
|            "end_time": "17:31",                                       |
|            "format": "IMAX 3D",                                       |
|            "screen": "Screen 3",                                      |
|            "available_seats": 45,                                     |
|            "price_range": {"min": 200, "max": 500},                   |
|            "filling_fast": true                                       |
|          }                                                             |
|        ]                                                               |
|      }                                                                 |
|    ]                                                                   |
|  }                                                                     |
+-------------------------------------------------------------------------+
```

**SEAT MAP:**
```
+-------------------------------------------------------------------------+
|  GET /api/v1/shows/{show_id}/seats                                     |
|  ---------------------------------                                     |
|                                                                         |
|  Response:                                                             |
|  {                                                                     |
|    "show_id": "show_123",                                             |
|    "screen": {                                                         |
|      "name": "Screen 3",                                              |
|      "type": "IMAX"                                                   |
|    },                                                                  |
|    "layout": {                                                         |
|      "rows": ["A", "B", "C", "D", "E", "F"],                          |
|      "aisles": [5]                                                    |
|    },                                                                  |
|    "categories": [                                                     |
|      {                                                                 |
|        "name": "PLATINUM",                                            |
|        "price": 500,                                                  |
|        "rows": ["A", "B"]                                             |
|      },                                                                |
|      {                                                                 |
|        "name": "GOLD",                                                |
|        "price": 350,                                                  |
|        "rows": ["C", "D", "E", "F"]                                   |
|      }                                                                 |
|    ],                                                                  |
|    "seats": [                                                          |
|      {"id": "A-1", "row": "A", "number": 1, "status": "AVAILABLE"},  |
|      {"id": "A-2", "row": "A", "number": 2, "status": "LOCKED"},     |
|      {"id": "A-3", "row": "A", "number": 3, "status": "BOOKED"},     |
|      ...                                                               |
|    ],                                                                  |
|    "timestamp": "2024-01-15T10:30:00Z"                                |
|  }                                                                     |
+-------------------------------------------------------------------------+
```

**LOCK SEATS:**
```
+-------------------------------------------------------------------------+
|  POST /api/v1/shows/{show_id}/seats/lock                               |
|  ------------------------------------                                  |
|  Headers:                                                              |
|    Authorization: Bearer {token}                                      |
|    Idempotency-Key: {unique_key}                                      |
|                                                                         |
|  Request:                                                              |
|  {                                                                     |
|    "seats": ["A-1", "A-2", "A-3"]                                     |
|  }                                                                     |
|                                                                         |
|  Success Response (200):                                               |
|  {                                                                     |
|    "lock_id": "lock_abc123",                                          |
|    "seats": ["A-1", "A-2", "A-3"],                                    |
|    "locked_until": "2024-01-15T10:40:00Z",                            |
|    "expires_in_seconds": 600,                                         |
|    "total_amount": 1500,                                              |
|    "breakdown": {                                                      |
|      "seat_charges": 1400,                                            |
|      "convenience_fee": 100                                           |
|    }                                                                   |
|  }                                                                     |
|                                                                         |
|  Failure Response (409 Conflict):                                      |
|  {                                                                     |
|    "error": "SEATS_UNAVAILABLE",                                      |
|    "message": "Some seats are no longer available",                   |
|    "unavailable_seats": ["A-2"]                                       |
|  }                                                                     |
+-------------------------------------------------------------------------+
```

**CONFIRM BOOKING:**
```
+-------------------------------------------------------------------------+
|  POST /api/v1/bookings                                                 |
|  ---------------------                                                 |
|  Headers:                                                              |
|    Authorization: Bearer {token}                                      |
|    Idempotency-Key: {unique_key}                                      |
|                                                                         |
|  Request:                                                              |
|  {                                                                     |
|    "lock_id": "lock_abc123",                                          |
|    "payment_method": "UPI",                                           |
|    "payment_details": {                                               |
|      "upi_id": "user@paytm"                                           |
|    },                                                                  |
|    "apply_offers": ["FIRST50"]                                        |
|  }                                                                     |
|                                                                         |
|  Success Response (201):                                               |
|  {                                                                     |
|    "booking_id": "BMS12345678",                                       |
|    "status": "CONFIRMED",                                             |
|    "movie": "Avengers: Endgame",                                      |
|    "theater": "PVR Phoenix",                                          |
|    "screen": "Screen 3",                                              |
|    "show_time": "2024-01-15 14:30",                                   |
|    "seats": ["A-1", "A-2", "A-3"],                                    |
|    "amount_paid": 1350,                                               |
|    "booking_code": "QR_DATA_HERE",                                    |
|    "ticket_url": "https://bms.com/ticket/BMS12345678"                 |
|  }                                                                     |
|                                                                         |
|  Failure Response (402 Payment Required):                              |
|  {                                                                     |
|    "error": "PAYMENT_FAILED",                                         |
|    "message": "Payment declined by bank",                             |
|    "retry_allowed": true                                              |
|  }                                                                     |
+-------------------------------------------------------------------------+
```

**CANCEL BOOKING:**
```
+-------------------------------------------------------------------------+
|  POST /api/v1/bookings/{booking_id}/cancel                             |
|  --------------------------------------                                |
|  Headers:                                                              |
|    Authorization: Bearer {token}                                      |
|                                                                         |
|  Request:                                                              |
|  {                                                                     |
|    "reason": "Change of plans"                                        |
|  }                                                                     |
|                                                                         |
|  Response:                                                             |
|  {                                                                     |
|    "booking_id": "BMS12345678",                                       |
|    "status": "CANCELLED",                                             |
|    "refund_amount": 1200,                                             |
|    "cancellation_fee": 150,                                           |
|    "refund_status": "INITIATED",                                      |
|    "refund_eta": "3-5 business days"                                  |
|  }                                                                     |
+-------------------------------------------------------------------------+
```

### 1B.5 ERROR CODES

```
+-------------------------------------------------------------------------+
|  CODE                    | HTTP | DESCRIPTION                          |
|  ------------------------+------+--------------------------------------|
|  SEATS_UNAVAILABLE       | 409  | Requested seats already taken       |
|  LOCK_EXPIRED            | 410  | Seat lock has expired               |
|  LOCK_NOT_FOUND          | 404  | Invalid lock ID                     |
|  SHOW_FULL               | 409  | No seats available for show         |
|  SHOW_NOT_FOUND          | 404  | Invalid show ID                     |
|  SHOW_EXPIRED            | 410  | Show has already started            |
|  PAYMENT_FAILED          | 402  | Payment processing failed           |
|  PAYMENT_TIMEOUT         | 408  | Payment gateway timeout             |
|  BOOKING_NOT_FOUND       | 404  | Invalid booking ID                  |
|  CANCELLATION_NOT_ALLOWED| 403  | Too late to cancel                  |
|  RATE_LIMITED            | 429  | Too many requests                   |
|  INVALID_SEATS           | 400  | Invalid seat numbers                |
|  MAX_SEATS_EXCEEDED      | 400  | Cannot book more than 10 seats      |
+-------------------------------------------------------------------------+
```

## PART 2: HIGH-LEVEL ARCHITECTURE

### 2.1 SYSTEM OVERVIEW

```
+-------------------------------------------------------------------------+
|                                                                         |
|   +----------+    +----------+    +----------+                         |
|   |  Mobile  |    |   Web    |    | Partner  |                         |
|   |   App    |    |  Browser |    |   Apps   |                         |
|   +----+-----+    +----+-----+    +----+-----+                         |
|        |               |               |                                |
|        +---------------+---------------+                                |
|                        |                                                |
|                        v                                                |
|              +-----------------+                                       |
|              |       CDN       |  Static assets, images                |
|              |   (CloudFront)  |                                       |
|              +--------+--------+                                       |
|                       |                                                 |
|                       v                                                 |
|              +-----------------+                                       |
|              |  Load Balancer  |  L7 (Application)                     |
|              |     (ALB/Nginx) |                                       |
|              +--------+--------+                                       |
|                       |                                                 |
|                       v                                                 |
|              +-----------------+                                       |
|              |   API Gateway   |  Auth, Rate Limit, Routing            |
|              |                 |                                       |
|              +--------+--------+                                       |
|                       |                                                 |
|        +--------------+--------------+--------------+                  |
|        v              v              v              v                  |
|   +---------+   +----------+   +----------+   +----------+            |
|   | Movie   |   | Booking  |   | Payment  |   |  Search  |            |
|   | Service |   | Service  |   | Service  |   | Service  |            |
|   +----+----+   +----+-----+   +----+-----+   +----+-----+            |
|        |             |              |              |                    |
|        +-------------+--------------+--------------+                   |
|                      |              |                                   |
|                      v              v                                   |
|   +-------------------------------------------------------------+      |
|   |                    MESSAGE QUEUE (Kafka)                     |      |
|   +-------------------------------------------------------------+      |
|                      |              |                                   |
|                      v              v                                   |
|   +----------+  +----------+  +----------+  +----------+              |
|   |Notifica- |  |Analytics |  |  Fraud   |  | Inventory|              |
|   |  tion    |  | Service  |  | Detection|  |  Sync    |              |
|   +----------+  +----------+  +----------+  +----------+              |
|                                                                         |
|   +-------------------------------------------------------------+      |
|   |                      DATA LAYER                              |      |
|   |  +------------+  +------------+  +------------+             |      |
|   |  | PostgreSQL |  |   Redis    |  |Elasticsearch|             |      |
|   |  |  (Primary) |  |  (Cache +  |  |  (Search)  |             |      |
|   |  |            |  |   Locks)   |  |            |             |      |
|   |  +------------+  +------------+  +------------+             |      |
|   +-------------------------------------------------------------+      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 2.2 MICROSERVICES BREAKDOWN

```
+-------------------------------------------------------------------------+
|                    SERVICE RESPONSIBILITIES                             |
|                                                                         |
|  MOVIE SERVICE                                                         |
|  -------------                                                         |
|  * Movie CRUD (admin)                                                  |
|  * Movie listings by city, date, filters                              |
|  * Cast/crew information                                              |
|  * Reviews and ratings                                                |
|  * Heavily cached (movies don't change often)                         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  THEATER SERVICE                                                       |
|  ---------------                                                       |
|  * Theater and screen management                                      |
|  * Seat layout configuration                                          |
|  * Show scheduling                                                    |
|  * Pricing rules per theater                                          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  BOOKING SERVICE (Critical Path)                                       |
|  ---------------------------------                                     |
|  * Seat availability queries                                          |
|  * Seat locking (distributed lock)                                    |
|  * Booking creation and confirmation                                  |
|  * Booking cancellation and refunds                                   |
|  * Inventory management                                               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PAYMENT SERVICE                                                       |
|  ---------------                                                       |
|  * Payment gateway integration (Razorpay, Paytm)                      |
|  * Payment initiation and verification                                |
|  * Refund processing                                                  |
|  * Idempotency handling                                               |
|  * Payment reconciliation                                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SEARCH SERVICE                                                        |
|  --------------                                                        |
|  * Full-text search (Elasticsearch)                                   |
|  * Autocomplete suggestions                                           |
|  * Filters and facets                                                 |
|  * Personalized recommendations                                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  NOTIFICATION SERVICE                                                  |
|  --------------------                                                  |
|  * Email (booking confirmation, reminders)                            |
|  * SMS (OTP, booking code)                                            |
|  * Push notifications (offers, reminders)                             |
|  * Async via Kafka                                                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  USER SERVICE                                                          |
|  ------------                                                          |
|  * Registration and authentication                                    |
|  * Profile management                                                 |
|  * Preferences and history                                            |
|  * Wallet/loyalty points                                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 2.3 TECHNOLOGY CHOICES & RATIONALE

```
+-------------------------------------------------------------------------+
|                    DATABASE SELECTION                                   |
|                                                                         |
|  +----------------+-----------------+--------------------------------+ |
|  | Data Type      | Choice          | Why                            | |
|  +----------------+-----------------+--------------------------------+ |
|  | Transactional  | PostgreSQL      | ACID for bookings, payments   | |
|  | (Bookings,     |                 | Strong consistency required   | |
|  |  Payments)     |                 | Complex queries, joins        | |
|  +----------------+-----------------+--------------------------------+ |
|  | Seat Locks     | Redis           | Sub-ms latency for locks      | |
|  | (Hot Data)     |                 | TTL for auto-expiry           | |
|  |                |                 | Atomic operations (SETNX)     | |
|  +----------------+-----------------+--------------------------------+ |
|  | Seat Avail-    | Redis           | Extremely high read rate      | |
|  | ability Cache  |                 | Eventual consistency OK       | |
|  |                |                 | In-memory speed               | |
|  +----------------+-----------------+--------------------------------+ |
|  | Search         | Elasticsearch   | Full-text search              | |
|  | (Movies,       |                 | Faceted filtering             | |
|  |  Theaters)     |                 | Autocomplete                  | |
|  +----------------+-----------------+--------------------------------+ |
|  | Analytics      | ClickHouse/     | Time-series aggregations      | |
|  |                | Druid           | Real-time dashboards          | |
|  +----------------+-----------------+--------------------------------+ |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    COMMUNICATION PROTOCOLS                              |
|                                                                         |
|  +----------------+-----------------+--------------------------------+ |
|  | Communication  | Protocol        | Why                            | |
|  +----------------+-----------------+--------------------------------+ |
|  | Client > API   | HTTPS/REST      | Browser/mobile compatibility  | |
|  |                |                 | Cacheable responses           | |
|  |                |                 | Widely understood             | |
|  +----------------+-----------------+--------------------------------+ |
|  | Real-time      | WebSocket       | Seat availability updates     | |
|  | updates        |                 | Lock countdown timer sync     | |
|  +----------------+-----------------+--------------------------------+ |
|  | Service-to-    | gRPC            | Low latency, binary           | |
|  | Service        |                 | Strong typing (protobuf)      | |
|  |                |                 | Streaming support             | |
|  +----------------+-----------------+--------------------------------+ |
|  | Async Events   | Kafka           | Durable, ordered              | |
|  |                |                 | Replay capability             | |
|  |                |                 | Decoupled services            | |
|  +----------------+-----------------+--------------------------------+ |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    WHY NOT ALTERNATIVES?                                |
|                                                                         |
|  WHY POSTGRESQL OVER MYSQL?                                            |
|  -----------------------------                                         |
|  * Better JSON support (JSONB for seat layouts)                       |
|  * Array types (for seat lists in bookings)                           |
|  * Better concurrent write performance                                |
|  * More advanced indexing options                                     |
|                                                                         |
|  WHY REDIS OVER MEMCACHED FOR LOCKS?                                   |
|  -------------------------------------                                 |
|  * Atomic SETNX operation (set if not exists)                         |
|  * Native TTL support                                                 |
|  * Lua scripting for complex atomic operations                        |
|  * Data structures (hashes for seat maps)                             |
|                                                                         |
|  WHY KAFKA OVER RABBITMQ?                                              |
|  -------------------------                                             |
|  * Durability — messages persisted to disk                            |
|  * Replay — can reprocess failed events                               |
|  * Higher throughput for event streaming                              |
|  * Better for analytics pipeline                                      |
|                                                                         |
|  WHY ELASTICSEARCH OVER SOLR?                                          |
|  -------------------------------                                       |
|  * Better JSON/REST API                                               |
|  * Easier horizontal scaling                                          |
|  * Better real-time indexing                                          |
|  * Richer analytics capabilities                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 2.4 SECURITY MODEL (AUTHENTICATION & AUTHORIZATION)

```
+-------------------------------------------------------------------------+
|                    ACCESS POLICY OVERVIEW                               |
|                                                                         |
|  NOT ALL APIs ARE EQUAL:                                               |
|  -----------------------                                               |
|  * Some endpoints are public (anyone can access)                      |
|  * Some require authentication (logged-in users)                      |
|  * Some require specific roles (admin only)                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  ACCESS MATRIX:                                                        |
|                                                                         |
|  +--------------------------------+------------+-------------------+   |
|  | Endpoint                       | Auth       | Notes             |   |
|  +--------------------------------+------------+-------------------+   |
|  | GET /api/search                | PUBLIC     | Browse events     |   |
|  | GET /api/events                | PUBLIC     | List events       |   |
|  | GET /api/events/{id}           | PUBLIC     | Event details     |   |
|  | GET /api/shows/{id}/seats      | PUBLIC     | Seat map view     |   |
|  | GET /api/theaters              | PUBLIC     | Theater list      |   |
|  +--------------------------------+------------+-------------------+   |
|  | POST /api/reservations         | USER       | Lock seats        |   |
|  | POST /api/bookings/confirm     | USER       | Complete booking  |   |
|  | GET /api/bookings/me           | USER       | My bookings       |   |
|  | DELETE /api/bookings/{id}      | USER       | Cancel booking    |   |
|  | GET /api/users/profile         | USER       | View profile      |   |
|  +--------------------------------+------------+-------------------+   |
|  | POST /api/events               | ADMIN      | Create event      |   |
|  | PUT /api/events/{id}           | ADMIN      | Update event      |   |
|  | POST /api/theaters             | PARTNER    | Add theater       |   |
|  | PUT /api/pricing               | ADMIN      | Pricing rules     |   |
|  | GET /api/admin/reports         | ADMIN      | Revenue reports   |   |
|  +--------------------------------+------------+-------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    JWT-BASED AUTHENTICATION                            |
|                                                                         |
|  WHY JWT?                                                              |
|  ---------                                                             |
|  * Stateless — No session storage needed on server                   |
|  * Scalable — Any server can validate token                          |
|  * Contains claims — User info embedded in token                     |
|  * Standard — Wide library support                                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  JWT STRUCTURE:                                                        |
|  ---------------                                                       |
|                                                                         |
|  Header.Payload.Signature                                              |
|                                                                         |
|  HEADER:                                                               |
|  {                                                                     |
|    "alg": "RS256",                                                    |
|    "typ": "JWT"                                                       |
|  }                                                                     |
|                                                                         |
|  PAYLOAD (Claims):                                                     |
|  {                                                                     |
|    "sub": "user_12345",                    // Subject (user ID)       |
|    "email": "sara@example.com",                                       |
|    "roles": ["USER"],                      // Authorization roles     |
|    "iat": 1703001600,                      // Issued at              |
|    "exp": 1703005200                       // Expires at (1 hour)    |
|  }                                                                     |
|                                                                         |
|  SIGNATURE:                                                            |
|  RS256(base64(header) + "." + base64(payload), privateKey)           |
|                                                                         |
+-------------------------------------------------------------------------+
```

**AUTHENTICATION FLOW:**

```
+-------------------------------------------------------------------------+
|                    LOGIN SEQUENCE                                       |
|                                                                         |
|  Client                Auth Service            User DB                  |
|    |                       |                      |                     |
|    |--POST /auth/login---->|                      |                     |
|    |  {email, password}    |                      |                     |
|    |                       |--Verify credentials-->|                     |
|    |                       |<-User record---------|                     |
|    |                       |                      |                     |
|    |                       | +------------------+ |                     |
|    |                       | |Generate JWT:     | |                     |
|    |                       | |* Set claims      | |                     |
|    |                       | |* Sign with key   | |                     |
|    |                       | |* Set expiry      | |                     |
|    |                       | +------------------+ |                     |
|    |                       |                      |                     |
|    |<-{accessToken, expiresIn}                   |                     |
|    |                       |                      |                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  API REQUEST EXAMPLE:                                                  |
|  ---------------------                                                 |
|                                                                         |
|  POST /api/auth/login                                                  |
|  Content-Type: application/json                                        |
|                                                                         |
|  {                                                                     |
|    "email": "sara@example.com",                                       |
|    "password": "securePassword123"                                    |
|  }                                                                     |
|                                                                         |
|  Response:                                                             |
|  {                                                                     |
|    "accessToken": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",         |
|    "refreshToken": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4...",             |
|    "expiresIn": 3600,                                                 |
|    "tokenType": "Bearer"                                              |
|  }                                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

**AUTHORIZATION FLOW:**

```
+-------------------------------------------------------------------------+
|                    PROTECTED REQUEST SEQUENCE                          |
|                                                                         |
|  Client             API Gateway          Booking Service               |
|    |                     |                      |                       |
|    |--POST /reservations->|                      |                       |
|    |  Authorization:     |                      |                       |
|    |  Bearer eyJhbG...   |                      |                       |
|    |                     |                      |                       |
|    |                     | +------------------+ |                       |
|    |                     | |1. Extract JWT    | |                       |
|    |                     | |2. Verify sig     | |                       |
|    |                     | |3. Check expiry   | |                       |
|    |                     | |4. Extract claims | |                       |
|    |                     | |5. Check roles    | |                       |
|    |                     | +------------------+ |                       |
|    |                     |                      |                       |
|    |                     |  (If valid)         |                       |
|    |                     |--Forward + userId--->|                       |
|    |                     |<-Reservation result--|                       |
|    |<-Response-----------|                      |                       |
|    |                     |                      |                       |
|    |                     |  (If invalid)       |                       |
|    |<-401 Unauthorized---|                      |                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

**IMPLEMENTATION (JAVA):**

```
+-------------------------------------------------------------------------+
|                                                                         |
|  @RestController                                                        |
|  @RequestMapping("/api/auth")                                           |
|  public class AuthController {                                          |
|                                                                         |
|      @Autowired                                                         |
|      private AuthService authService;                                   |
|                                                                         |
|      @PostMapping("/login")                                             |
|      public ResponseEntity<TokenResponse> login(                        |
|              @RequestBody LoginRequest request) {                       |
|          return ResponseEntity.ok(authService.login(request));         |
|      }                                                                  |
|                                                                         |
|      @PostMapping("/refresh")                                           |
|      public ResponseEntity<TokenResponse> refresh(                      |
|              @RequestBody RefreshTokenRequest request) {                |
|          return ResponseEntity.ok(authService.refresh(request));       |
|      }                                                                  |
|                                                                         |
|      @PostMapping("/logout")                                            |
|      public ResponseEntity<Void> logout(                                |
|              @RequestHeader("Authorization") String token) {            |
|          authService.logout(token);                                    |
|          return ResponseEntity.ok().build();                           |
|      }                                                                  |
|  }                                                                      |
|                                                                         |
|  // JWT Filter for protected endpoints                                  |
|  @Component                                                             |
|  public class JwtAuthenticationFilter extends OncePerRequestFilter {   |
|                                                                         |
|      @Autowired                                                         |
|      private JwtTokenProvider tokenProvider;                           |
|                                                                         |
|      @Override                                                          |
|      protected void doFilterInternal(HttpServletRequest request,       |
|              HttpServletResponse response, FilterChain chain) {        |
|                                                                         |
|          String token = extractToken(request);                         |
|                                                                         |
|          if (token != null && tokenProvider.validateToken(token)) {    |
|              Claims claims = tokenProvider.getClaims(token);           |
|              String userId = claims.getSubject();                      |
|              List<String> roles = claims.get("roles", List.class);     |
|                                                                         |
|              UsernamePasswordAuthenticationToken auth =                |
|                  new UsernamePasswordAuthenticationToken(              |
|                      userId, null,                                     |
|                      roles.stream()                                    |
|                          .map(SimpleGrantedAuthority::new)             |
|                          .toList()                                     |
|                  );                                                    |
|                                                                         |
|              SecurityContextHolder.getContext()                        |
|                  .setAuthentication(auth);                             |
|          }                                                              |
|                                                                         |
|          chain.doFilter(request, response);                            |
|      }                                                                  |
|                                                                         |
|      private String extractToken(HttpServletRequest request) {         |
|          String bearer = request.getHeader("Authorization");           |
|          if (bearer != null && bearer.startsWith("Bearer ")) {         |
|              return bearer.substring(7);                               |
|          }                                                              |
|          return null;                                                  |
|      }                                                                  |
|  }                                                                      |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    TOKEN REFRESH STRATEGY                              |
|                                                                         |
|  WHY REFRESH TOKENS?                                                   |
|  ---------------------                                                 |
|  * Access tokens expire quickly (1 hour) for security                 |
|  * Refresh tokens live longer (7-30 days)                             |
|  * If access token stolen, limited damage window                      |
|  * User doesn't need to re-login frequently                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  FLOW:                                                                 |
|  ------                                                                |
|  1. User logs in > Gets access + refresh tokens                       |
|  2. Access token expires after 1 hour                                 |
|  3. Client sends refresh token to /auth/refresh                       |
|  4. Server validates refresh token                                    |
|  5. Server issues new access token (+ optionally new refresh)         |
|  6. Repeat until refresh token expires or user logs out               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SECURITY CONSIDERATIONS:                                              |
|  -------------------------                                             |
|  * Store refresh tokens in HttpOnly cookies (not localStorage)        |
|  * Implement token rotation (new refresh token on each use)           |
|  * Maintain blocklist for revoked tokens (logout, password change)    |
|  * Use different signing keys for access vs refresh tokens            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 2.5 PUBLIC VS PRIVATE (INTERNAL) APIs

```
+-------------------------------------------------------------------------+
|                    API CLASSIFICATION                                  |
|                                                                         |
|  PUBLIC APIs (External-facing):                                        |
|  --------------------------------                                      |
|  * Exposed through API Gateway                                        |
|  * Rate limited per user/IP                                           |
|  * Versioned (v1, v2)                                                 |
|  * Documented (OpenAPI/Swagger)                                       |
|  * May require authentication                                         |
|                                                                         |
|  PRIVATE APIs (Internal service-to-service):                          |
|  --------------------------------------------                          |
|  * Not exposed externally                                             |
|  * Higher trust level                                                 |
|  * mTLS or service mesh authentication                                |
|  * No rate limiting (or different limits)                             |
|  * May bypass some validations                                        |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    API GATEWAY RESPONSIBILITIES                        |
|                                                                         |
|                          INTERNET                                      |
|                              |                                          |
|                              v                                          |
|           +--------------------------------------+                     |
|           |           API GATEWAY                |                     |
|           |                                      |                     |
|           |  +---------------------------------+|                     |
|           |  | 1. SSL Termination             ||                     |
|           |  | 2. Rate Limiting               ||                     |
|           |  |    * 100 req/min per user      ||                     |
|           |  |    * 1000 req/min per IP       ||                     |
|           |  | 3. Authentication              ||                     |
|           |  |    * Validate JWT              ||                     |
|           |  |    * Reject invalid tokens     ||                     |
|           |  | 4. Authorization               ||                     |
|           |  |    * Check roles for endpoint  ||                     |
|           |  | 5. Request Validation          ||                     |
|           |  |    * Schema validation         ||                     |
|           |  | 6. Routing                     ||                     |
|           |  |    * Route to correct service  ||                     |
|           |  | 7. Response Transformation     ||                     |
|           |  |    * Hide internal details     ||                     |
|           |  +---------------------------------+|                     |
|           +--------------------------------------+                     |
|                              |                                          |
|             +----------------+----------------+                        |
|             |                |                |                        |
|             v                v                v                        |
|      +----------+    +----------+    +----------+                     |
|      | Booking  |    |  Search  |    |  Event   |                     |
|      | Service  |    | Service  |    | Service  |                     |
|      +----------+    +----------+    +----------+                     |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    RATE LIMITING STRATEGIES                            |
|                                                                         |
|  BY USER (Authenticated):                                              |
|  -------------------------                                             |
|  * 100 requests/minute for regular users                              |
|  * 500 requests/minute for premium users                              |
|  * Reservation: 5 attempts/minute (prevent hoarding)                  |
|                                                                         |
|  BY IP (Unauthenticated):                                              |
|  -------------------------                                             |
|  * 50 requests/minute for search                                      |
|  * 10 login attempts/hour                                             |
|                                                                         |
|  BY ENDPOINT (Critical):                                               |
|  -------------------------                                             |
|  * /api/reservations: Global cap during flash sales                   |
|  * /api/bookings/confirm: Per-user cooldown                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  IMPLEMENTATION (Redis-based):                                         |
|  ------------------------------                                        |
|                                                                         |
|  // Sliding window rate limiter                                        |
|  public boolean isAllowed(String userId, String endpoint) {           |
|      String key = "ratelimit:" + userId + ":" + endpoint;             |
|      long now = System.currentTimeMillis();                           |
|      long windowStart = now - 60000; // 1 minute window              |
|                                                                         |
|      // Remove old entries, count current, add new                    |
|      redisTemplate.opsForZSet()                                       |
|          .removeRangeByScore(key, 0, windowStart);                    |
|      Long count = redisTemplate.opsForZSet().zCard(key);              |
|                                                                         |
|      if (count >= MAX_REQUESTS) {                                     |
|          return false; // Rate limited                                |
|      }                                                                 |
|                                                                         |
|      redisTemplate.opsForZSet().add(key, now + "", now);              |
|      redisTemplate.expire(key, Duration.ofMinutes(2));                |
|      return true;                                                     |
|  }                                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 2.6 DATABASE-TO-SERVICE OWNERSHIP MAPPING

```
+-------------------------------------------------------------------------+
|                    WHY SEPARATE DATABASES?                             |
|                                                                         |
|  PRINCIPLES:                                                           |
|  -----------                                                           |
|  1. Each microservice owns its data                                   |
|  2. No cross-database JOINs                                           |
|  3. Services communicate via APIs, not shared tables                  |
|  4. Reference data by IDs across service boundaries                   |
|                                                                         |
|  BENEFITS:                                                             |
|  ---------                                                             |
|  * Independent scaling (Booking DB != Search index)                   |
|  * Independent deployments                                            |
|  * Technology flexibility (SQL vs NoSQL per service)                  |
|  * Clear ownership and accountability                                 |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    SERVICE > DATABASE MAPPING                          |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |  AUTH SERVICE > Auth DB (PostgreSQL)                           |   |
|  |  ------------------------------------                          |   |
|  |  Tables:                                                       |   |
|  |    * users (user_id, email, password_hash, created_at)        |   |
|  |    * roles (role_id, role_name)                               |   |
|  |    * user_roles (user_id, role_id)                            |   |
|  |    * refresh_tokens (token_id, user_id, token, expires_at)    |   |
|  |    * sessions (optional, for session-based fallback)          |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |  EVENT SERVICE > Events DB (PostgreSQL)                        |   |
|  |  -------------------------------------                         |   |
|  |  Tables:                                                       |   |
|  |    * movies (movie_id, title, genre, language, duration)      |   |
|  |    * theaters (theater_id, name, city_id, location)           |   |
|  |    * screens (screen_id, theater_id, name, capacity)          |   |
|  |    * shows (show_id, movie_id, screen_id, start_time, status) |   |
|  |    * seat_templates (template_id, screen_id, layout_json)     |   |
|  |    * pricing_rules (rule_id, show_id, seat_type, price)       |   |
|  |    * outbox_events (for CDC to Search service)                |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |  INVENTORY SERVICE > Inventory DB (PostgreSQL)                 |   |
|  |  --------------------------------------------                  |   |
|  |  Tables:                                                       |   |
|  |    * seats (seat_id, show_id, seat_number, status, price,     |   |
|  |            version, reserved_by, reserved_until, booking_id)  |   |
|  |    * reservations (reservation_id, seat_id, user_id,          |   |
|  |                    expires_at, status)                        |   |
|  |    * seat_audit (audit_id, seat_id, old_status, new_status,   |   |
|  |                  changed_by, changed_at)                      |   |
|  |                                                                 |   |
|  |  NOTE: This is the HOT PATH - consider Redis for seat locks   |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |  BOOKING SERVICE > Bookings DB (PostgreSQL)                    |   |
|  |  -----------------------------------------                     |   |
|  |  Tables:                                                       |   |
|  |    * bookings (booking_id, user_id, show_id, total_amount,    |   |
|  |               status, booking_reference, created_at)          |   |
|  |    * booking_seats (booking_seat_id, booking_id, seat_id,     |   |
|  |                     price_at_purchase)                        |   |
|  |    * payments (payment_id, booking_id, amount, status,        |   |
|  |               gateway_ref, idempotency_key)                   |   |
|  |    * refunds (refund_id, booking_id, amount, status)          |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |  SEARCH SERVICE > Elasticsearch / OpenSearch                   |   |
|  |  -------------------------------------------                   |   |
|  |  Indexes:                                                      |   |
|  |    * movies_index (denormalized movie + show data)            |   |
|  |    * theaters_index (theater + geo-location)                  |   |
|  |    * events_index (combined search view)                      |   |
|  |                                                                 |   |
|  |  Data synced via CDC (Debezium) from Events DB                |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |  NOTIFICATION SERVICE > Notifications DB (PostgreSQL/NoSQL)    |   |
|  |  ---------------------------------------------------------     |   |
|  |  Tables:                                                       |   |
|  |    * notification_templates (template_id, type, content)      |   |
|  |    * notification_log (log_id, user_id, type, status, sent_at)|   |
|  |    * user_preferences (user_id, email_enabled, sms_enabled)   |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    CROSS-SERVICE DATA FLOW                             |
|                                                                         |
|                                                                         |
|    +--------------+                        +--------------+            |
|    | Events DB    |--CDC (Debezium)------->| Search Index |            |
|    | (PostgreSQL) |                        | (OpenSearch) |            |
|    +--------------+                        +--------------+            |
|           |                                                            |
|           | show_id reference                                         |
|           v                                                            |
|    +--------------+                        +--------------+            |
|    | Inventory DB |<- API call -----------|   Booking    |            |
|    |  (Seats)     |   (lock/release)      |   Service    |            |
|    +--------------+                        +--------------+            |
|           |                                       |                    |
|           | seat_ids                              |                    |
|           +---------------------------------------+                    |
|                              |                                         |
|                              v                                         |
|                       +--------------+                                |
|                       | Bookings DB  |                                |
|                       | (Orders)     |                                |
|                       +--------------+                                |
|                              |                                         |
|                              | Kafka event                            |
|                              v                                         |
|                       +--------------+                                |
|                       | Notification |                                |
|                       |   Service    |                                |
|                       +--------------+                                |
|                                                                         |
|  KEY PRINCIPLES:                                                       |
|  ---------------                                                       |
|  * NO cross-database foreign keys                                     |
|  * Reference by IDs, validate via API calls                          |
|  * Eventual consistency via events (Kafka/CDC)                       |
|  * Each service is source of truth for its data                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 3: THEATER & SHOW MANAGEMENT

### 3.1 THEATER ONBOARDING

```
+-------------------------------------------------------------------------+
|                    THEATER HIERARCHY                                    |
|                                                                         |
|   CITY                                                                 |
|     |                                                                   |
|     +-- THEATER (Physical Location)                                    |
|           |                                                             |
|           +-- SCREEN 1                                                 |
|           |     |                                                       |
|           |     +-- SEAT LAYOUT                                        |
|           |           +-- Rows (A-J)                                   |
|           |           +-- Seats per row                                |
|           |           +-- Categories (Platinum, Gold, Silver)          |
|           |           +-- Blocked seats (wheelchair, exit)             |
|           |                                                             |
|           +-- SCREEN 2 (IMAX)                                          |
|           |     +-- Different layout...                                |
|           |                                                             |
|           +-- SCREEN 3                                                 |
|                 +-- ...                                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 3.2 SEAT LAYOUT CONFIGURATION

```
+-------------------------------------------------------------------------+
|                    SEAT MAP VISUALIZATION                               |
|                                                                         |
|                         +===============+                              |
|                         |    SCREEN     |                              |
|                         +===============+                              |
|                                                                         |
|     PLATINUM ($500)                                                    |
|     +---+---+---+---+---+   +---+---+---+---+---+                     |
|   A | 1 | 2 | 3 | 4 | 5 |   | 6 | 7 | 8 | 9 |10 |                     |
|     +---+---+---+---+---+   +---+---+---+---+---+                     |
|     +---+---+---+---+---+   +---+---+---+---+---+                     |
|   B | 1 | 2 | 3 | 4 | 5 |   | 6 | 7 | 8 | 9 |10 |                     |
|     +---+---+---+---+---+   +---+---+---+---+---+                     |
|     ----------------------------------------------- (aisle)            |
|     GOLD ($350)                                                        |
|     +---+---+---+---+---+---+ +---+---+---+---+---+---+               |
|   C | 1 | 2 | 3 | 4 | 5 | 6 | | 7 | 8 | 9 |10 |11 |12 |               |
|     +---+---+---+---+---+---+ +---+---+---+---+---+---+               |
|     +---+---+---+---+---+---+ +---+---+---+---+---+---+               |
|   D | 1 | 2 | 3 | 4 | 5 | 6 | | 7 | 8 | 9 |10 |11 |12 |               |
|     +---+---+---+---+---+---+ +---+---+---+---+---+---+               |
|     ----------------------------------------------- (aisle)            |
|     SILVER ($200)                                                      |
|     +---+---+---+---+---+---+---+---+---+---+---+---+---+---+         |
|   E | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |10 |11 |12 |13 |14 |         |
|     +---+---+---+---+---+---+---+---+---+---+---+---+---+---+         |
|                                                                         |
|     Legend:  [ ] Available   [█] Booked   [░] Locked   [X] Blocked    |
|                                                                         |
+-------------------------------------------------------------------------+
```

**SEAT LAYOUT JSON STRUCTURE:**

```
{
  "screen_id": "screen_xyz",
  "total_rows": 5,
  "rows": [
    {
      "row_id": "A",
      "category": "PLATINUM",
      "seats": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
      "gaps_after": [5]    // Aisle after seat 5
    },
    {
      "row_id": "B",
      "category": "PLATINUM",
      "seats": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
      "gaps_after": [5]
    },
    // ... more rows
  ],
  "aisles_after_rows": ["B", "D"],   // Horizontal aisles
  "blocked_seats": ["E-14"],          // Wheelchair space
  "pricing": {
    "PLATINUM": 500,
    "GOLD": 350,
    "SILVER": 200
  }
}
```

### 3.3 SHOW SCHEDULING

```
+-------------------------------------------------------------------------+
|                    SHOW CREATION FLOW                                   |
|                                                                         |
|  INPUTS:                                                               |
|  * Movie (with duration)                                              |
|  * Screen                                                              |
|  * Start time                                                          |
|  * Format (2D, 3D, IMAX)                                              |
|  * Language (original or dubbed)                                      |
|  * Pricing overrides (optional)                                       |
|                                                                         |
|  VALIDATIONS:                                                          |
|  ------------                                                          |
|  1. No overlap with existing shows on same screen                     |
|     * End time = Start time + Movie duration + Buffer (30 min)        |
|     * Check: SELECT * FROM shows WHERE screen_id = ? AND              |
|              show_date = ? AND start_time < ? AND end_time > ?        |
|                                                                         |
|  2. Screen supports format (IMAX screen for IMAX movie)               |
|                                                                         |
|  3. Not in the past                                                   |
|                                                                         |
|  SEAT INVENTORY INITIALIZATION:                                        |
|  --------------------------------                                      |
|  When show is created, we DON'T pre-create 300 seat_inventory rows.  |
|                                                                         |
|  WHY?                                                                  |
|  * 100,000 shows/day × 300 seats = 30 million rows/day               |
|  * Most seats never get viewed or booked                              |
|  * Wasteful storage                                                   |
|                                                                         |
|  INSTEAD:                                                              |
|  * Seat layout is derived from screen configuration                   |
|  * seat_inventory rows created ON-DEMAND when locked or booked        |
|  * Default status = AVAILABLE (absence = available)                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

**LAZY SEAT INVENTORY PATTERN:**

```
+-------------------------------------------------------------------------+
|                                                                         |
|  When user requests seat map:                                          |
|  1. Get screen layout (cached)                                        |
|  2. Get seat_inventory rows for this show (only locked/booked exist)  |
|  3. Merge: All seats in layout - inventory rows = AVAILABLE           |
|                                                                         |
|  PSEUDO-LOGIC:                                                         |
|                                                                         |
|  allSeats = getScreenLayout(screenId).getAllSeats()                   |
|  // Returns: [A-1, A-2, A-3, ... E-14]                                |
|                                                                         |
|  takenSeats = SELECT seat_number, status FROM seat_inventory          |
|               WHERE show_id = ?                                        |
|  // Returns: {A-5: LOCKED, B-3: BOOKED, C-1: BOOKED}                  |
|                                                                         |
|  FOR EACH seat IN allSeats:                                           |
|      IF seat IN takenSeats:                                           |
|          seatStatus = takenSeats[seat].status                         |
|      ELSE:                                                             |
|          seatStatus = AVAILABLE                                       |
|                                                                         |
|  BENEFIT: Only store what's necessary (sparse representation)         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 4: SEAT SELECTION & BOOKING (THE HARD PROBLEM)

This is the CORE technical challenge of BookMyShow — handling concurrent seat
bookings without double-booking while maintaining good user experience.

### 4.1 THE BOOKING FLOW (USER JOURNEY)

```
+-------------------------------------------------------------------------+
|                    USER BOOKING JOURNEY                                 |
|                                                                         |
|   +---------+    +---------+    +---------+    +---------+            |
|   | Browse  |--->|  Select |--->|  Lock   |--->|   Pay   |            |
|   | Movies  |    |  Seats  |    |  Seats  |    |         |            |
|   +---------+    +---------+    +----+----+    +----+----+            |
|                                      |              |                   |
|                                      |              |                   |
|                                      v              v                   |
|                               +-----------+  +-----------+             |
|                               |  Timer    |  | Confirm   |             |
|                               |  10 min   |  | Booking   |             |
|                               +-----+-----+  +-----------+             |
|                                     |                                   |
|                            +--------+--------+                         |
|                            v                 v                         |
|                     +-----------+     +-----------+                    |
|                     |  Timeout  |     |  Payment  |                    |
|                     |  Release  |     |  Success  |                    |
|                     +-----------+     +-----------+                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

**DETAILED STEPS:**

Step 1: VIEW SEAT MAP
---------------------
- User selects a show
- System returns seat layout + current availability
- UI renders interactive seat map
- Seats shown as: Available / Locked / Booked

Step 2: SELECT SEATS
--------------------
- User clicks on seats (client-side only)
- No server call yet
- UI highlights selected seats
- Shows running total

Step 3: LOCK SEATS (Critical!)
------------------------------
- User clicks "Book Now"
- System attempts to LOCK all selected seats atomically
- If ANY seat unavailable > FAIL entire request
- If success > Start 10-minute countdown
- Seats now show as LOCKED to other users

Step 4: PAYMENT
---------------
- User enters payment details
- Payment initiated with gateway
- User has until lock expires to complete

Step 5A: PAYMENT SUCCESS
------------------------
- Seats marked as BOOKED (permanent)
- Booking record created
- Confirmation sent (email, SMS)
- Lock released (replaced by booking)

Step 5B: PAYMENT FAILURE / TIMEOUT
----------------------------------
- Lock expires (TTL-based auto-release)
- Seats become AVAILABLE again
- Other users can now book

### 4.2 WHY IS THIS HARD? — THE CONCURRENCY PROBLEM

```
+-------------------------------------------------------------------------+
|                    RACE CONDITION SCENARIO                              |
|                                                                         |
|  Two users (A and B) want seat F-12 at the exact same time.           |
|                                                                         |
|  NAIVE APPROACH (CHECK-THEN-LOCK):                                     |
|                                                                         |
|  User A                              User B                            |
|  ---------                           ---------                         |
|  T1: Is F-12 available?                                               |
|      > Query DB: status = AVAILABLE                                   |
|      > Yes!                                                           |
|                                      T2: Is F-12 available?           |
|                                          > Query DB: status = AVAILABLE|
|                                          > Yes!                       |
|  T3: Lock F-12                                                        |
|      > UPDATE status = LOCKED                                         |
|      > Success                                                        |
|                                      T4: Lock F-12                    |
|                                          > UPDATE status = LOCKED     |
|                                          > Success < PROBLEM!         |
|                                                                         |
|  Both users think they have the seat! When they pay, one will fail.  |
|  BAD USER EXPERIENCE.                                                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  THE PROBLEM:                                                          |
|  * Check and Lock are SEPARATE operations                             |
|  * Race window between check and lock                                 |
|  * Multiple servers, can't use simple mutex                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 4.3 SOLUTION APPROACHES

### APPROACH 1: DATABASE-LEVEL LOCKING (Pessimistic)

```
+-------------------------------------------------------------------------+
|                    SELECT FOR UPDATE                                    |
|                                                                         |
|  CONCEPT:                                                              |
|  Use database row-level locks to serialize access to seats.           |
|                                                                         |
|  HOW IT WORKS:                                                         |
|  ----------------                                                      |
|  BEGIN TRANSACTION;                                                    |
|                                                                         |
|  SELECT * FROM seat_inventory                                          |
|  WHERE show_id = 'xyz' AND seat_number IN ('A-1', 'A-2')              |
|  FOR UPDATE;          < Locks these rows!                             |
|                                                                         |
|  -- Other transactions trying to SELECT FOR UPDATE same rows          |
|  -- will WAIT until this transaction commits/rollbacks                |
|                                                                         |
|  IF all seats have status = 'AVAILABLE':                              |
|      UPDATE seat_inventory                                             |
|      SET status = 'LOCKED', locked_by = ?, locked_until = ?           |
|      WHERE show_id = 'xyz' AND seat_number IN ('A-1', 'A-2');         |
|                                                                         |
|  COMMIT;               < Releases locks                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PROS:                                                                 |
|  Y Database handles locking — simple to implement                     |
|  Y ACID guarantees                                                    |
|  Y No external dependencies (no Redis needed)                         |
|                                                                         |
|  CONS:                                                                 |
|  X Database becomes bottleneck under high load                        |
|  X Row locks held for entire transaction duration                     |
|  X Potential for deadlocks with multiple seats                        |
|  X Doesn't scale well horizontally                                    |
|                                                                         |
|  VERDICT: Works for moderate scale, not for 100K concurrent users     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### APPROACH 2: OPTIMISTIC LOCKING (Version Column)

```
+-------------------------------------------------------------------------+
|                    OPTIMISTIC LOCKING                                   |
|                                                                         |
|  CONCEPT:                                                              |
|  Don't lock during read. At write time, check if data changed.        |
|                                                                         |
|  HOW IT WORKS:                                                         |
|  ----------------                                                      |
|  1. Read seat with version number:                                    |
|     SELECT seat_number, status, version FROM seat_inventory           |
|     WHERE show_id = ? AND seat_number = 'A-1'                         |
|     > Returns: status = AVAILABLE, version = 5                        |
|                                                                         |
|  2. Attempt update with version check:                                |
|     UPDATE seat_inventory                                              |
|     SET status = 'LOCKED', version = 6                                |
|     WHERE show_id = ? AND seat_number = 'A-1'                         |
|       AND version = 5;    < Only if version unchanged!               |
|                                                                         |
|  3. Check rows affected:                                              |
|     - If 1 row affected > Success, we got the lock                    |
|     - If 0 rows affected > Someone else modified, RETRY or FAIL       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PROS:                                                                 |
|  Y No blocking — high concurrency                                     |
|  Y Simple implementation                                              |
|  Y No deadlock risk                                                   |
|                                                                         |
|  CONS:                                                                 |
|  X High retry rate under contention (popular shows)                   |
|  X Still hits database for every attempt                              |
|  X Multiple seats = multiple queries (or complex batch)               |
|                                                                         |
|  VERDICT: Good for low-medium contention, struggles with hot shows   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### APPROACH 3: REDIS DISTRIBUTED LOCKING (Recommended)

```
+-------------------------------------------------------------------------+
|                    REDIS SETNX FOR SEAT LOCKS                          |
|                                                                         |
|  CONCEPT:                                                              |
|  Use Redis as a fast, distributed lock manager.                       |
|  SETNX = SET if Not eXists (atomic operation)                         |
|                                                                         |
|  HOW IT WORKS:                                                         |
|  ----------------                                                      |
|                                                                         |
|  KEY DESIGN:                                                           |
|  Key:    seat_lock:{show_id}:{seat_number}                            |
|  Value:  {user_id}:{lock_token}                                       |
|  TTL:    600 seconds (10 minutes)                                     |
|                                                                         |
|  LOCKING A SINGLE SEAT:                                                |
|  -------------------------                                             |
|  SET seat_lock:show123:A-1 "user456:token789" NX EX 600               |
|                                                                         |
|  NX = Only set if key doesn't exist                                   |
|  EX 600 = Expire after 600 seconds                                    |
|                                                                         |
|  Response:                                                             |
|  * "OK" > Lock acquired!                                              |
|  * nil  > Seat already locked by someone else                         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  LOCKING MULTIPLE SEATS ATOMICALLY:                                    |
|  ------------------------------------                                  |
|  THE PROBLEM: User selects 3 seats. What if 2 succeed and 1 fails?   |
|                                                                         |
|  BAD: Lock A-1 Y, Lock A-2 Y, Lock A-3 X                              |
|       User has partial lock — confusing!                              |
|                                                                         |
|  SOLUTION: Use Redis Lua script for atomic multi-key operation        |
|                                                                         |
|  PRINCIPLE:                                                            |
|  Lua scripts in Redis execute atomically — no interleaving.          |
|  Either ALL seats get locked, or NONE do.                             |
|                                                                         |
|  ALGORITHM:                                                            |
|  1. For each seat, check if key exists                                |
|  2. If ANY key exists > Return failure (seats not available)          |
|  3. If ALL keys absent > Set all keys atomically                     |
|  4. Return success with lock token                                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PROS:                                                                 |
|  Y Sub-millisecond latency                                            |
|  Y Handles massive concurrency                                        |
|  Y Atomic multi-seat locking via Lua                                  |
|  Y Automatic expiry (TTL) — no cleanup needed                         |
|  Y Horizontally scalable (Redis Cluster)                              |
|                                                                         |
|  CONS:                                                                 |
|  X Redis is an additional component to manage                         |
|  X Need to sync with database eventually                              |
|  X Redis failure = booking failure (need HA setup)                    |
|                                                                         |
|  VERDICT: Best approach for high-scale systems like BookMyShow        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 4.4 LOCK EXPIRY AND AUTO-RELEASE

```
+-------------------------------------------------------------------------+
|                    WHY LOCKS MUST EXPIRE                                |
|                                                                         |
|  SCENARIO:                                                             |
|  1. User locks seats A-1, A-2, A-3                                    |
|  2. User's phone dies / user closes browser                           |
|  3. User never completes payment                                      |
|                                                                         |
|  WITHOUT EXPIRY:                                                       |
|  Seats locked FOREVER. Lost revenue. Angry other users.              |
|                                                                         |
|  WITH TTL-BASED EXPIRY:                                                |
|  After 10 minutes, Redis keys auto-delete.                            |
|  Seats automatically become available.                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CHOOSING LOCK DURATION:                                               |
|  ------------------------                                              |
|                                                                         |
|  TOO SHORT (2 minutes):                                               |
|  * User doesn't have time to enter payment details                    |
|  * Lock expires mid-payment > booking fails                           |
|  * Frustrating user experience                                        |
|                                                                         |
|  TOO LONG (30 minutes):                                               |
|  * Abandoned locks block seats for too long                           |
|  * Lost revenue opportunity                                           |
|  * Other users can't book                                             |
|                                                                         |
|  SWEET SPOT: 8-10 minutes                                             |
|  * Enough time for most payment flows                                 |
|  * Not too long for abandoned sessions                                |
|  * Show countdown timer to create urgency                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  LOCK EXTENSION:                                                       |
|  ----------------                                                      |
|  If user is actively on payment page (not idle):                      |
|  * Allow ONE extension of 5 more minutes                              |
|  * User must click "Need more time"                                   |
|  * Prevents abuse while helping genuine users                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 5: DISTRIBUTED LOCKING FOR SEATS (DEEP DIVE)

### 5.1 REDIS SETNX PRINCIPLE

```
+-------------------------------------------------------------------------+
|                    SETNX = SET IF NOT EXISTS                           |
|                                                                         |
|  ATOMIC OPERATION:                                                     |
|  The entire check-and-set happens as ONE indivisible operation.       |
|  No race condition possible.                                          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  COMMAND:                                                              |
|  SET key value NX EX seconds                                          |
|                                                                         |
|  NX = Only set if key does NOT exist                                  |
|  EX = Set expiry in seconds                                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  EXAMPLE:                                                              |
|                                                                         |
|  Thread A: SET seat:A-1 "userA" NX EX 600                             |
|            > Response: "OK" (key didn't exist, now set)               |
|                                                                         |
|  Thread B: SET seat:A-1 "userB" NX EX 600                             |
|            > Response: nil (key exists, NOT set)                      |
|                                                                         |
|  Even if both commands arrive at the "same time", Redis processes    |
|  them sequentially. ONE will succeed, ONE will fail.                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WHY THE VALUE MATTERS:                                                |
|  -------------------------                                             |
|  Value = user_id:lock_token                                           |
|                                                                         |
|  Purpose:                                                              |
|  1. Know WHO holds the lock (for debugging, support)                  |
|  2. Lock token ensures only owner can release                         |
|  3. Prevents accidental release by wrong user                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 5.2 ATOMIC MULTI-SEAT LOCKING

```
+-------------------------------------------------------------------------+
|                    THE PROBLEM WITH MULTIPLE SEATS                     |
|                                                                         |
|  User wants to book seats: A-1, A-2, A-3                              |
|                                                                         |
|  NAIVE APPROACH:                                                       |
|  Lock A-1 > Success Y                                                 |
|  Lock A-2 > Success Y                                                 |
|  Lock A-3 > FAIL X (someone else has it)                              |
|                                                                         |
|  PROBLEM:                                                              |
|  User now has partial lock (A-1, A-2 locked, A-3 not)                 |
|  Need to rollback A-1 and A-2 > Complex!                              |
|  Race condition during rollback!                                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTION: LUA SCRIPT                                                  |
|  ---------------------                                                 |
|  Lua scripts in Redis execute atomically.                             |
|  Either ALL seats lock, or NONE do. No partial state.                 |
|                                                                         |
|  ALGORITHM:                                                            |
|  ------------                                                          |
|  1. Input: List of seat keys to lock                                  |
|  2. For each key, check if EXISTS                                     |
|  3. If ANY key exists:                                                |
|     > Return which seats are unavailable                              |
|     > Lock NOTHING                                                    |
|  4. If ALL keys absent:                                               |
|     > SET all keys with same TTL                                      |
|     > Return success                                                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PSEUDO-LOGIC:                                                         |
|                                                                         |
|  FUNCTION lock_seats(seat_keys[], user_id, lock_token, ttl):          |
|      unavailable = []                                                 |
|                                                                         |
|      // Phase 1: Check all seats                                      |
|      FOR EACH key IN seat_keys:                                       |
|          IF EXISTS(key):                                              |
|              unavailable.add(key)                                     |
|                                                                         |
|      // If any unavailable, fail fast                                 |
|      IF unavailable.length > 0:                                       |
|          RETURN {success: false, unavailable: unavailable}            |
|                                                                         |
|      // Phase 2: Lock all seats (we know all are available)           |
|      FOR EACH key IN seat_keys:                                       |
|          SET key "{user_id}:{lock_token}" EX ttl                      |
|                                                                         |
|      RETURN {success: true}                                           |
|                                                                         |
|  ATOMICITY GUARANTEE:                                                  |
|  Entire script runs without any other command interleaving.           |
|  Between check and set, NO other client can modify keys.              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 5.3 SAFE LOCK RELEASE

```
+-------------------------------------------------------------------------+
|                    THE LOCK RELEASE PROBLEM                            |
|                                                                         |
|  SCENARIO:                                                             |
|  1. User A locks seat at T=0, TTL=600s                                |
|  2. User A's request is slow (network issues)                         |
|  3. Lock expires at T=600                                             |
|  4. User B locks same seat at T=601                                   |
|  5. User A's delayed release command arrives at T=602                 |
|  6. User A accidentally releases User B's lock!                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTION: CHECK-BEFORE-DELETE (ATOMIC)                                |
|  -----------------------------------------                             |
|                                                                         |
|  Only delete if the lock value matches our token.                     |
|                                                                         |
|  PRINCIPLE:                                                            |
|  1. Check if key value = our token                                    |
|  2. If yes, delete                                                    |
|  3. If no, someone else has the lock now — don't touch!              |
|                                                                         |
|  This must be ATOMIC (Lua script) to avoid race.                      |
|                                                                         |
|  PSEUDO-LOGIC:                                                         |
|                                                                         |
|  FUNCTION release_lock(key, expected_token):                          |
|      current_value = GET(key)                                         |
|      IF current_value == expected_token:                              |
|          DEL(key)                                                     |
|          RETURN 1   // Released                                       |
|      ELSE:                                                             |
|          RETURN 0   // Not our lock, or already expired              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WHY TOKENS?                                                           |
|  -------------                                                         |
|  Lock token is a random UUID generated when lock is acquired.        |
|  Example: "user123:a1b2c3d4-e5f6-7890-abcd-ef1234567890"             |
|                                                                         |
|  Even if same user locks twice, different tokens prevent confusion.  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 5.4 PESSIMISTIC VS OPTIMISTIC: WHICH FOR BOOKMYSHOW?

```
+-------------------------------------------------------------------------+
|                    LOCKING STRATEGY COMPARISON                         |
|                                                                         |
|  +----------------+----------------------+------------------------+    |
|  | Aspect         | Pessimistic          | Optimistic             |    |
|  |                | (Redis SETNX)        | (Version Column)       |    |
|  +----------------+----------------------+------------------------+    |
|  | Lock acquired  | BEFORE reading       | Not at all             |    |
|  +----------------+----------------------+------------------------+    |
|  | Conflict check | At lock time         | At write time          |    |
|  +----------------+----------------------+------------------------+    |
|  | On conflict    | Immediate rejection  | Retry required         |    |
|  +----------------+----------------------+------------------------+    |
|  | Contention     | Handles well         | High retry rate        |    |
|  +----------------+----------------------+------------------------+    |
|  | Latency        | Fast (Redis)         | Depends on retries     |    |
|  +----------------+----------------------+------------------------+    |
|  | Complexity     | Medium (Redis Lua)   | Low                    |    |
|  +----------------+----------------------+------------------------+    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WHY PESSIMISTIC FOR BOOKMYSHOW?                                       |
|  ---------------------------------                                     |
|                                                                         |
|  1. HIGH CONTENTION:                                                   |
|     Popular shows have many users competing for same seats.           |
|     Optimistic would have extremely high retry rates.                 |
|                                                                         |
|  2. CLEAR FEEDBACK:                                                    |
|     User knows IMMEDIATELY if seats are available.                    |
|     "Seat unavailable" appears instantly, not after payment attempt. |
|                                                                         |
|  3. RESERVATION SEMANTICS:                                             |
|     User needs to HOLD seats while they pay (10 minutes).            |
|     This is inherently a pessimistic/exclusive lock pattern.         |
|                                                                         |
|  4. WASTED WORK:                                                       |
|     With optimistic: User enters payment, THEN finds out conflict.   |
|     Terrible UX. Wasted payment gateway calls.                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  BOOKMYSHOW USES BOTH:                                                 |
|  -----------------------                                               |
|  Layer 1: Redis pessimistic lock (primary)                            |
|  Layer 2: Database optimistic lock (backup verification)              |
|                                                                         |
|  Why both? Defense in depth.                                          |
|  If Redis fails, database version check catches inconsistencies.     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 5.5 COMPLETE BOOKING SEQUENCE

```
+-------------------------------------------------------------------------+
|                    BOOKING SEQUENCE DIAGRAM                            |
|                                                                         |
|  User        API         Redis        Database       Payment           |
|   |           |            |             |             |                |
|   |--Select seats->       |             |             |                |
|   |           |--Lock seats (Lua)->    |             |                |
|   |           |           |             |             |                |
|   |           |  +--------+--------+   |             |                |
|   |           |  | For each seat:  |   |             |                |
|   |           |  | EXISTS? No      |   |             |                |
|   |           |  | SET with TTL    |   |             |                |
|   |           |  +--------+--------+   |             |                |
|   |           |           |             |             |                |
|   |           |<-Lock result (OK)--    |             |                |
|   |<-Seats locked, 10 min timer-       |             |                |
|   |           |            |            |             |                |
|   | (User enters payment details - takes 2-3 minutes)                  |
|   |           |            |            |             |                |
|   |--Submit payment->     |            |             |                |
|   |           |--Verify lock->        |             |                |
|   |           |<-Still locked, valid--|             |                |
|   |           |            |            |             |                |
|   |           |----------Create pending booking-->   |                |
|   |           |            |            |<(booking_id)|                |
|   |           |            |            |             |                |
|   |           |------------Initiate payment--------->|                |
|   |           |            |            |             |                |
|   |           |<-----------Payment success-----------|                |
|   |           |            |            |             |                |
|   |           |--Update booking CONFIRMED-->        |                |
|   |           |--Update seats BOOKED-->            |                |
|   |           |--Release Redis locks->             |                |
|   |           |            |            |             |                |
|   |<-Booking confirmed + ticket-       |             |                |
|   |           |            |            |             |                |
|                                                                         |
+-------------------------------------------------------------------------+
```

**KEY POINTS IN SEQUENCE:**

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. LOCK FIRST, PAY LATER                                              |
|     Redis lock acquired BEFORE payment attempt.                       |
|     User has guaranteed seats while paying.                           |
|                                                                         |
|  2. VERIFY BEFORE PAYMENT                                              |
|     Before sending to payment gateway, verify lock still valid.       |
|     Prevents edge case of expired lock + successful payment.          |
|                                                                         |
|  3. DATABASE UPDATE AFTER PAYMENT                                      |
|     Only create permanent booking AFTER payment confirmed.            |
|     Atomic: payment + booking = single logical transaction.           |
|                                                                         |
|  4. RELEASE REDIS AFTER DATABASE                                       |
|     Database is source of truth.                                      |
|     Redis lock released only after DB confirms booking.               |
|     Order matters for consistency.                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 5.6 REDLOCK ALGORITHM (ADVANCED DISTRIBUTED LOCKING)

```
+-------------------------------------------------------------------------+
|                    WHY REDLOCK?                                         |
|                                                                         |
|  PROBLEM WITH SINGLE REDIS:                                            |
|  -----------------------------                                         |
|  * Single Redis instance = Single Point of Failure                    |
|  * Redis Sentinel provides HA, but during failover:                   |
|    - Master dies, replica promoted                                    |
|    - Lock on old master may not be replicated yet                     |
|    - Two clients can hold the "same" lock!                            |
|                                                                         |
|  REDLOCK SOLUTION:                                                     |
|  -----------------                                                     |
|  Use N independent Redis masters (typically N=5)                      |
|  Acquire lock on majority (N/2+1 = 3) for it to be valid             |
|  Even if 2 masters fail, lock is still valid                         |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    REDLOCK ALGORITHM STEPS                              |
|                                                                         |
|  STEP 1: Get current time T1                                           |
|                                                                         |
|  STEP 2: Try to acquire lock on ALL N Redis instances                  |
|          * Use same key, same random value, same TTL                  |
|          * Short timeout per instance (5-50ms)                        |
|          * Don't wait too long on unresponsive instances              |
|                                                                         |
|  STEP 3: Calculate elapsed time: elapsed = T2 - T1                     |
|                                                                         |
|  STEP 4: Lock is VALID if:                                             |
|          * Acquired on majority: count >= N/2 + 1                     |
|          * Validity time positive: TTL - elapsed - clock_drift > 0   |
|                                                                         |
|  STEP 5: If lock INVALID, release on ALL instances                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  VISUAL EXAMPLE (N=5):                                                 |
|  ---------------------                                                 |
|                                                                         |
|  Client attempts to lock "seat:A-1" on 5 Redis masters:               |
|                                                                         |
|    Redis-1: SET seat:A-1 "uuid123" NX EX 30 > OK Y                    |
|    Redis-2: SET seat:A-1 "uuid123" NX EX 30 > OK Y                    |
|    Redis-3: SET seat:A-1 "uuid123" NX EX 30 > TIMEOUT X              |
|    Redis-4: SET seat:A-1 "uuid123" NX EX 30 > OK Y                    |
|    Redis-5: SET seat:A-1 "uuid123" NX EX 30 > FAIL X                 |
|                                                                         |
|  Acquired: 3 out of 5 (majority = 3)                                  |
|  Elapsed: 50ms                                                        |
|  Validity: 30000ms - 50ms - 100ms(drift) = 29850ms                   |
|                                                                         |
|  Result: LOCK ACQUIRED Y                                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

**REDLOCK IMPLEMENTATION (JAVA):**

```
+-------------------------------------------------------------------------+
|                                                                         |
|  @Component                                                             |
|  public class RedlockDistributedLock {                                  |
|                                                                         |
|      private List<RedisTemplate<String, String>> redisInstances;       |
|      private static final int N = 5;                                   |
|      private static final int QUORUM = N / 2 + 1;  // 3               |
|      private static final int CLOCK_DRIFT_MS = 100;                    |
|      private static final int RETRY_DELAY_MS = 50;                     |
|      private static final int MAX_RETRIES = 3;                         |
|                                                                         |
|      /**                                                                |
|       * Acquire distributed lock using Redlock algorithm               |
|       */                                                                |
|      public LockResult tryLock(String resource, int ttlMs) {           |
|          String lockValue = UUID.randomUUID().toString();              |
|                                                                         |
|          for (int retry = 0; retry < MAX_RETRIES; retry++) {          |
|              long startTime = System.currentTimeMillis();              |
|              int acquiredCount = 0;                                    |
|                                                                         |
|              // Try to acquire lock on ALL Redis instances             |
|              for (RedisTemplate<String, String> redis : redisInstances) {
|                  try {                                                 |
|                      Boolean acquired = redis.opsForValue()            |
|                          .setIfAbsent(resource, lockValue,             |
|                              Duration.ofMillis(ttlMs));                |
|                      if (Boolean.TRUE.equals(acquired)) {              |
|                          acquiredCount++;                              |
|                      }                                                 |
|                  } catch (Exception e) {                               |
|                      // Instance unavailable, continue                 |
|                      log.warn("Redis instance unavailable", e);        |
|                  }                                                     |
|              }                                                          |
|                                                                         |
|              long elapsed = System.currentTimeMillis() - startTime;    |
|              long validityTime = ttlMs - elapsed - CLOCK_DRIFT_MS;     |
|                                                                         |
|              // Check if lock is valid                                 |
|              if (acquiredCount >= QUORUM && validityTime > 0) {        |
|                  return new LockResult(true, lockValue, validityTime); |
|              }                                                          |
|                                                                         |
|              // Lock not acquired, release any partial locks           |
|              releaseLock(resource, lockValue);                         |
|                                                                         |
|              // Random delay before retry (prevent thundering herd)    |
|              Thread.sleep(ThreadLocalRandom.current()                  |
|                  .nextInt(RETRY_DELAY_MS));                            |
|          }                                                              |
|                                                                         |
|          return new LockResult(false, null, 0);                        |
|      }                                                                  |
|                                                                         |
|      /**                                                                |
|       * Release lock on ALL Redis instances                            |
|       */                                                                |
|      public void releaseLock(String resource, String lockValue) {      |
|          String luaScript =                                            |
|              "if redis.call('get', KEYS[1]) == ARGV[1] then " +       |
|              "    return redis.call('del', KEYS[1]) " +                |
|              "else " +                                                  |
|              "    return 0 " +                                          |
|              "end";                                                     |
|                                                                         |
|          for (RedisTemplate<String, String> redis : redisInstances) {  |
|              try {                                                     |
|                  redis.execute(                                        |
|                      new DefaultRedisScript<>(luaScript, Long.class),  |
|                      Collections.singletonList(resource),              |
|                      lockValue                                         |
|                  );                                                    |
|              } catch (Exception e) {                                   |
|                  log.warn("Failed to release lock on instance", e);    |
|              }                                                          |
|          }                                                              |
|      }                                                                  |
|  }                                                                      |
|                                                                         |
|  // Lock result holder                                                  |
|  public record LockResult(                                              |
|      boolean acquired,                                                 |
|      String lockValue,                                                 |
|      long validityTimeMs                                               |
|  ) {}                                                                   |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    WHEN TO USE REDLOCK VS SIMPLE REDIS LOCK            |
|                                                                         |
|  +------------------+---------------------+------------------------+   |
|  | Aspect           | Simple Redis Lock   | Redlock                |   |
|  +------------------+---------------------+------------------------+   |
|  | Infrastructure   | Single Redis or     | N independent Redis   |   |
|  |                  | Redis Sentinel      | masters (N=5 typical) |   |
|  +------------------+---------------------+------------------------+   |
|  | Complexity       | Low                 | High                   |   |
|  +------------------+---------------------+------------------------+   |
|  | Latency          | ~1ms                | ~5-50ms (N calls)      |   |
|  +------------------+---------------------+------------------------+   |
|  | Failure          | Redis down = no     | Tolerates N/2-1        |   |
|  | tolerance        | locks               | failures               |   |
|  +------------------+---------------------+------------------------+   |
|  | Consistency      | May lose locks on   | Stronger guarantees    |   |
|  |                  | failover            |                        |   |
|  +------------------+---------------------+------------------------+   |
|  | Cost             | Low                 | 5x Redis instances     |   |
|  +------------------+---------------------+------------------------+   |
|  | Use case         | 99% of applications | Mission-critical       |   |
|  |                  |                     | (banking, tickets)     |   |
|  +------------------+---------------------+------------------------+   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  BOOKMYSHOW RECOMMENDATION:                                            |
|  ---------------------------                                           |
|                                                                         |
|  FOR MOST DEPLOYMENTS: Simple Redis with Sentinel                     |
|  * Lower complexity, lower latency                                    |
|  * Sentinel handles failover                                          |
|  * Rare edge case of lost lock during failover is acceptable         |
|    (user retries, no real harm)                                      |
|                                                                         |
|  FOR HIGH-VALUE EVENTS (Taylor Swift, IPL Finals):                    |
|  * Consider Redlock for extra safety                                  |
|  * Cost of double-booking is very high (PR disaster, refunds)        |
|  * Extra latency is acceptable for premium events                    |
|                                                                         |
|  HYBRID APPROACH:                                                      |
|  * Feature flag to enable Redlock for specific events                |
|  * Default to simple lock for regular shows                          |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    REDLOCK CRITICISMS & MITIGATIONS                    |
|                                                                         |
|  CRITICISM 1: Clock skew between servers                               |
|  -----------------------------------------                             |
|  If server clocks are not synchronized, validity calculations         |
|  can be wrong.                                                         |
|                                                                         |
|  Mitigation:                                                           |
|  * Use NTP for clock synchronization                                  |
|  * Add generous clock drift factor (100-500ms)                        |
|  * Monitor clock skew alerts                                          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CRITICISM 2: Process pause during GC                                  |
|  --------------------------------------                                |
|  Client acquires lock, then JVM GC pauses for 30 seconds.            |
|  Lock expires, another client gets it.                                |
|  GC ends, first client thinks it still has lock!                     |
|                                                                         |
|  Mitigation:                                                           |
|  * Fencing tokens (increment counter on each lock)                   |
|  * Revalidate lock before critical operations                        |
|  * Use low-pause GC (ZGC, Shenandoah)                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CRITICISM 3: Network partitions                                       |
|  --------------------------------                                      |
|  Client A locks on Redis 1,2,3                                        |
|  Network partition isolates Redis 1,2,3 from Redis 4,5               |
|  Client B locks on Redis 4,5,3 (3 switched sides)                    |
|  Two clients have locks!                                              |
|                                                                         |
|  Mitigation:                                                           |
|  * This is extremely rare                                             |
|  * Database-level check as backup                                     |
|  * Accept that distributed systems have edge cases                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 6: PAYMENT PROCESSING & IDEMPOTENCY

### 6.1 PAYMENT FLOW OVERVIEW

```
+-------------------------------------------------------------------------+
|                    PAYMENT INTEGRATION                                  |
|                                                                         |
|  BookMyShow integrates with payment gateways like:                     |
|  * Razorpay                                                            |
|  * Paytm                                                               |
|  * PayU                                                                |
|  * Credit/Debit cards (via gateway)                                   |
|  * UPI                                                                 |
|  * Net Banking                                                         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PAYMENT STAGES:                                                       |
|                                                                         |
|  Stage 1: INITIATE                                                     |
|  -----------------                                                     |
|  * Create payment record in our DB (status = INITIATED)               |
|  * Generate idempotency key                                           |
|  * Call payment gateway to create order                               |
|                                                                         |
|  Stage 2: AUTHORIZE                                                    |
|  -----------------                                                     |
|  * User enters payment details on gateway page                        |
|  * Gateway verifies card/UPI                                          |
|  * Amount is HELD (not yet transferred)                               |
|                                                                         |
|  Stage 3: CAPTURE                                                      |
|  ----------------                                                      |
|  * We confirm to gateway: "Complete the payment"                      |
|  * Money actually moves                                               |
|  * Gateway sends webhook confirmation                                 |
|                                                                         |
|  Stage 4: CONFIRM BOOKING                                              |
|  -----------------------                                               |
|  * Update payment status = SUCCESS                                    |
|  * Update booking status = CONFIRMED                                  |
|  * Update seats status = BOOKED                                       |
|  * Send confirmation notification                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 6.2 IDEMPOTENCY — PREVENTING DOUBLE CHARGES

```
+-------------------------------------------------------------------------+
|                    THE DOUBLE-CHARGE PROBLEM                           |
|                                                                         |
|  SCENARIO:                                                             |
|  1. User clicks "Pay Now"                                             |
|  2. Request sent to server                                            |
|  3. Server initiates payment with gateway                             |
|  4. Gateway processes payment                                         |
|  5. Gateway sends response                                            |
|  6. Network timeout — response never reaches our server               |
|  7. User's app shows "Something went wrong. Try again?"               |
|  8. User clicks "Pay Now" again                                       |
|  9. SECOND payment initiated!                                         |
|                                                                         |
|  RESULT: User charged TWICE for same booking.                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

WHAT IS IDEMPOTENCY?

```
+-------------------------------------------------------------------------+
|                    IDEMPOTENCY PRINCIPLE                               |
|                                                                         |
|  DEFINITION:                                                           |
|  An operation is idempotent if executing it multiple times            |
|  produces the SAME RESULT as executing it once.                       |
|                                                                         |
|  EXAMPLE:                                                              |
|  Idempotent:     SET x = 5      (do it 10 times, x is still 5)       |
|  Not Idempotent: x = x + 1      (do it 10 times, x increases by 10)  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  FOR PAYMENTS:                                                         |
|  * First "Pay" request > Charge the user                              |
|  * Second "Pay" request (retry) > Return previous result              |
|  * Third "Pay" request (retry) > Return previous result               |
|                                                                         |
|  User is only charged ONCE, no matter how many retries.               |
|                                                                         |
+-------------------------------------------------------------------------+
```

**HOW IDEMPOTENCY WORKS:**

```
+-------------------------------------------------------------------------+
|                    IDEMPOTENCY KEY MECHANISM                           |
|                                                                         |
|  STEP 1: GENERATE IDEMPOTENCY KEY                                      |
|  ---------------------------------                                     |
|  When user clicks "Book Now" (lock seats):                            |
|  * Generate unique key: booking:{booking_id}:payment:{timestamp}      |
|  * Or simpler: UUID                                                   |
|  * Store in client and send with all payment requests                 |
|                                                                         |
|  STEP 2: CHECK BEFORE PROCESSING                                       |
|  --------------------------------                                      |
|  When payment request arrives:                                        |
|  1. Look up idempotency_key in payments table                         |
|  2. If EXISTS:                                                        |
|     * Return cached result (don't charge again)                       |
|  3. If NOT EXISTS:                                                    |
|     * Process payment                                                 |
|     * Store result with idempotency_key                               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  EXAMPLE FLOW:                                                         |
|                                                                         |
|  Request 1 (Original):                                                |
|  POST /api/payments                                                   |
|  Idempotency-Key: pay_abc123                                          |
|  > Check DB: No record with key pay_abc123                            |
|  > Process payment with gateway                                       |
|  > Store: {key: pay_abc123, status: SUCCESS, txn_id: txn_456}        |
|  > Return: {status: SUCCESS, txn_id: txn_456}                         |
|                                                                         |
|  Request 2 (Retry):                                                   |
|  POST /api/payments                                                   |
|  Idempotency-Key: pay_abc123  (same key!)                             |
|  > Check DB: Found record with key pay_abc123                         |
|  > DO NOT call payment gateway                                        |
|  > Return cached: {status: SUCCESS, txn_id: txn_456}                  |
|                                                                         |
|  User sees success, charged only once!                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

**DATABASE ENFORCEMENT:**

```
+-------------------------------------------------------------------------+
|                    UNIQUE CONSTRAINT AS BACKUP                         |
|                                                                         |
|  Even with application-level checks, add database constraint:         |
|                                                                         |
|  CREATE TABLE payments (                                               |
|      id                UUID PRIMARY KEY,                               |
|      booking_id        UUID NOT NULL,                                  |
|      idempotency_key   VARCHAR(255) UNIQUE,  < Database enforced!     |
|      amount            DECIMAL(10,2),                                  |
|      status            VARCHAR(20),                                    |
|      ...                                                               |
|  );                                                                    |
|                                                                         |
|  If two concurrent requests try to insert same idempotency_key:       |
|  > One succeeds, one fails with UNIQUE VIOLATION                      |
|  > Application catches error, queries existing record                 |
|  > Returns cached result                                              |
|                                                                         |
|  DEFENSE IN DEPTH:                                                     |
|  Application check + Database constraint = No double charges          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 6.3 HANDLING PAYMENT FAILURES

```
+-------------------------------------------------------------------------+
|                    FAILURE SCENARIOS                                   |
|                                                                         |
|  SCENARIO 1: GATEWAY RETURNS FAILURE                                   |
|  ------------------------------------                                  |
|  Payment declined (insufficient funds, wrong OTP, etc.)               |
|                                                                         |
|  Action:                                                               |
|  * Update payment status = FAILED                                     |
|  * Keep seat lock active (user might retry)                          |
|  * Show "Payment failed. Try again?"                                 |
|  * User can retry until lock expires                                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SCENARIO 2: GATEWAY TIMEOUT                                           |
|  -----------------------------                                         |
|  We sent request, no response (network issue)                         |
|                                                                         |
|  PROBLEM: Did payment succeed or fail? We don't know!                 |
|                                                                         |
|  Action:                                                               |
|  * Mark payment status = PENDING                                      |
|  * Poll gateway for status (GET /payments/{id})                       |
|  * Retry with SAME idempotency key (safe!)                           |
|  * Show "Verifying payment..." to user                               |
|  * Background job checks pending payments                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SCENARIO 3: SUCCESS BUT DB UPDATE FAILS                               |
|  -----------------------------------------                             |
|  Payment succeeded, but booking confirmation failed                   |
|                                                                         |
|  Action:                                                               |
|  * Retry DB update (transient failure)                               |
|  * If persistent failure: Queue for manual review                    |
|  * NEVER leave payment SUCCESS with booking PENDING                  |
|  * Reconciliation job matches payments to bookings                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SCENARIO 4: LOCK EXPIRED BEFORE PAYMENT COMPLETED                     |
|  ---------------------------------------------------                   |
|  User took too long, lock expired, someone else booked seats         |
|                                                                         |
|  PROBLEM: Payment might already be in progress!                       |
|                                                                         |
|  Prevention:                                                          |
|  * Check lock validity BEFORE initiating payment                     |
|  * If lock < 2 minutes remaining, reject payment attempt             |
|  * "Lock expiring soon. Please restart booking."                     |
|                                                                         |
|  If payment succeeds but seats gone:                                  |
|  * Auto-refund                                                        |
|  * Apologize and offer alternatives                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 6.4 SAGA PATTERN FOR BOOKING

```
+-------------------------------------------------------------------------+
|                    BOOKING AS A DISTRIBUTED TRANSACTION                |
|                                                                         |
|  A booking involves multiple services:                                 |
|  1. Seat Service: Lock > Book seats                                   |
|  2. Payment Service: Charge user                                      |
|  3. Notification Service: Send confirmation                           |
|  4. Analytics Service: Record booking                                 |
|                                                                         |
|  Traditional DB transaction can't span services.                      |
|  Solution: SAGA pattern.                                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

**ORCHESTRATION-BASED SAGA:**

```
+-------------------------------------------------------------------------+
|                    BOOKING SAGA (ORCHESTRATION)                        |
|                                                                         |
|  A central ORCHESTRATOR coordinates all steps.                        |
|                                                                         |
|                                                                         |
|        +----------------------------------------------+                |
|        |           BOOKING ORCHESTRATOR               |                |
|        |         (e.g., Temporal/Cadence)             |                |
|        +----------------------------------------------+                |
|                         |                                              |
|     +-------------------+-------------------+                         |
|     |                   |                   |                          |
|     v                   v                   v                          |
|  +-------+         +---------+        +-----------+                   |
|  | Seat  |         | Payment |        |Notification|                  |
|  |Service|         | Service |        |  Service  |                   |
|  +-------+         +---------+        +-----------+                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  HAPPY PATH:                                                           |
|  ------------                                                          |
|  1. Orchestrator: "Reserve seats"                                     |
|     Seat Service: Seats reserved Y                                    |
|                                                                         |
|  2. Orchestrator: "Charge payment"                                    |
|     Payment Service: Payment successful Y                             |
|                                                                         |
|  3. Orchestrator: "Confirm seats"                                     |
|     Seat Service: Seats booked Y                                      |
|                                                                         |
|  4. Orchestrator: "Send notification"                                 |
|     Notification Service: Email/SMS sent Y                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  COMPENSATION (Payment Fails):                                         |
|  ------------------------------                                        |
|  1. Orchestrator: "Reserve seats" > Y                                 |
|  2. Orchestrator: "Charge payment" > X FAILED                         |
|                                                                         |
|  Now we need to UNDO step 1:                                          |
|  3. Orchestrator: "Release seats" (compensating action)               |
|     Seat Service: Seats released Y                                    |
|                                                                         |
|  Every action has a compensating action.                              |
|  Orchestrator tracks state and triggers compensations on failure.    |
|                                                                         |
+-------------------------------------------------------------------------+
```

**WHY ORCHESTRATION OVER CHOREOGRAPHY FOR BOOKMYSHOW:**

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CHOREOGRAPHY:                                                         |
|  Each service emits events, others react.                             |
|  No central coordinator.                                              |
|                                                                         |
|  Problems for BookMyShow:                                              |
|  * Hard to track booking state across services                        |
|  * Compensation logic scattered everywhere                            |
|  * Debugging distributed failures is nightmare                        |
|  * "Where is my booking stuck?" — hard to answer                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  ORCHESTRATION:                                                        |
|  Central orchestrator knows full state.                               |
|                                                                         |
|  Benefits for BookMyShow:                                              |
|  * Clear visibility: "Step 2 of 4 failed"                            |
|  * Automatic retries with backoff                                    |
|  * Compensation is coordinated                                        |
|  * Easier debugging and monitoring                                    |
|  * Can resume from failures                                           |
|                                                                         |
|  Tools: Temporal, Cadence, AWS Step Functions                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 7: SEARCH & DISCOVERY

### 7.1 SEARCH REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                    SEARCH USE CASES                                    |
|                                                                         |
|  1. MOVIE SEARCH                                                       |
|     * "Avengers" > Avengers: Endgame, Avengers: Infinity War          |
|     * Typo tolerance: "Avangers" > Avengers                           |
|     * By actor: "Shah Rukh Khan movies"                               |
|     * By genre: "Action movies this week"                             |
|                                                                         |
|  2. THEATER SEARCH                                                     |
|     * "PVR near me"                                                   |
|     * "IMAX theaters in Mumbai"                                       |
|     * Geolocation-based sorting                                       |
|                                                                         |
|  3. AUTOCOMPLETE                                                       |
|     * User types "Av" > Suggest "Avatar", "Avengers"                  |
|     * Fast (< 100ms)                                                  |
|     * Prefix matching                                                 |
|                                                                         |
|  4. FILTERS                                                            |
|     * Language: Hindi, English, Tamil                                 |
|     * Format: 2D, 3D, IMAX                                            |
|     * Genre: Action, Comedy, Drama                                    |
|     * Time: Morning, Afternoon, Evening                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 7.2 ELASTICSEARCH ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                    WHY ELASTICSEARCH?                                  |
|                                                                         |
|  PostgreSQL has full-text search, but Elasticsearch is better for:    |
|                                                                         |
|  Y Fuzzy matching (typo tolerance)                                    |
|  Y Relevance scoring                                                  |
|  Y Faceted search (filters + counts)                                  |
|  Y Autocomplete / suggestions                                         |
|  Y Geospatial queries (nearby theaters)                               |
|  Y Horizontal scaling for search load                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

**INDEX DESIGN:**

```
+-------------------------------------------------------------------------+
|                    MOVIES INDEX                                        |
|                                                                         |
|  {                                                                     |
|    "mappings": {                                                       |
|      "properties": {                                                   |
|        "title": {                                                      |
|          "type": "text",                                              |
|          "analyzer": "standard",                                      |
|          "fields": {                                                   |
|            "suggest": {                                               |
|              "type": "completion"   // For autocomplete              |
|            }                                                           |
|          }                                                             |
|        },                                                              |
|        "genre": { "type": "keyword" },    // Exact match filter      |
|        "language": { "type": "keyword" },                             |
|        "cast": { "type": "text" },        // Searchable              |
|        "release_date": { "type": "date" },                            |
|        "avg_rating": { "type": "float" },                             |
|        "city_ids": { "type": "keyword" }  // Which cities showing    |
|      }                                                                 |
|    }                                                                   |
|  }                                                                     |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    THEATERS INDEX                                      |
|                                                                         |
|  {                                                                     |
|    "mappings": {                                                       |
|      "properties": {                                                   |
|        "name": { "type": "text" },                                    |
|        "city_id": { "type": "keyword" },                              |
|        "location": { "type": "geo_point" },  // For "near me"        |
|        "amenities": { "type": "keyword" },                            |
|        "screen_types": { "type": "keyword" } // IMAX, 4DX, etc      |
|      }                                                                 |
|    }                                                                   |
|  }                                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 7.3 SYNCING DATA TO ELASTICSEARCH

```
+-------------------------------------------------------------------------+
|                    DATA SYNC STRATEGIES                                |
|                                                                         |
|  PostgreSQL (Source of Truth) > Elasticsearch (Search Index)          |
|                                                                         |
|  APPROACH 1: DUAL WRITE (Not Recommended)                              |
|  -----------------------------------------                             |
|  Write to both DB and ES in same request.                             |
|  Problem: Inconsistency if one fails.                                 |
|                                                                         |
|  APPROACH 2: CDC (Change Data Capture) — Recommended                   |
|  ----------------------------------------------------                  |
|  Use Debezium to stream changes from PostgreSQL WAL.                  |
|  Changes flow through Kafka to Elasticsearch.                         |
|                                                                         |
|  PostgreSQL > Debezium > Kafka > ES Connector > Elasticsearch         |
|                                                                         |
|  Benefits:                                                             |
|  * Decoupled (main write path not affected)                          |
|  * Reliable (Kafka durability)                                       |
|  * Eventual consistency (seconds of delay is OK for search)          |
|                                                                         |
|  APPROACH 3: APPLICATION EVENTS                                        |
|  ------------------------------                                        |
|  After DB write, publish event to Kafka.                              |
|  Consumer updates Elasticsearch.                                      |
|                                                                         |
|  Simpler than CDC, but requires discipline to emit events.           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 8: CACHING STRATEGY

### 8.1 WHAT TO CACHE

```
+-------------------------------------------------------------------------+
|                    CACHING TIERS                                       |
|                                                                         |
|  +--------------------+-------------+--------------+-----------------+ |
|  | Data               | Cache       | TTL          | Invalidation    | |
|  +--------------------+-------------+--------------+-----------------+ |
|  | Movie list         | Redis       | 1 hour       | On movie update | |
|  | (by city/date)     |             |              |                 | |
|  +--------------------+-------------+--------------+-----------------+ |
|  | Movie details      | Redis       | 24 hours     | On movie update | |
|  +--------------------+-------------+--------------+-----------------+ |
|  | Theater list       | Redis       | 6 hours      | On theater edit | |
|  +--------------------+-------------+--------------+-----------------+ |
|  | Show listings      | Redis       | 15 minutes   | On show change  | |
|  +--------------------+-------------+--------------+-----------------+ |
|  | Seat availability  | Redis       | 5 seconds    | On lock/book    | |
|  | (summary)          |             |              |                 | |
|  +--------------------+-------------+--------------+-----------------+ |
|  | Seat locks         | Redis       | 10 minutes   | TTL-based       | |
|  | (distributed lock) |             |              |                 | |
|  +--------------------+-------------+--------------+-----------------+ |
|  | Static assets      | CDN         | 1 year       | URL versioning  | |
|  | (images, CSS, JS)  |             |              |                 | |
|  +--------------------+-------------+--------------+-----------------+ |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 8.2 CACHE-ASIDE PATTERN

```
+-------------------------------------------------------------------------+
|                    READ PATH                                           |
|                                                                         |
|  1. Application receives request for movie details                    |
|  2. Check Redis cache:                                                |
|     - Cache HIT > Return cached data                                  |
|     - Cache MISS > Continue to step 3                                 |
|  3. Query PostgreSQL                                                  |
|  4. Store result in Redis with TTL                                    |
|  5. Return data                                                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WRITE PATH                                                            |
|                                                                         |
|  1. Update PostgreSQL                                                 |
|  2. Invalidate (delete) cache key                                     |
|     - Next read will repopulate cache                                 |
|                                                                         |
|  WHY NOT UPDATE CACHE?                                                  |
|  * Race condition: Old data might overwrite new                         |
|  * Delete is simpler and safer                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 8.3 SEAT AVAILABILITY: SPECIAL CASE

```
+-------------------------------------------------------------------------+
|                    REAL-TIME AVAILABILITY                              |
|                                                                         |
|  Seat availability changes frequently (locks, bookings).              |
|  Traditional caching with TTL causes stale data.                      |
|                                                                         |
|  APPROACH: REDIS AS PRIMARY FOR HOT DATA                               |
|  ------------------------------------------                            |
|  * Seat locks stored ONLY in Redis (TTL-based)                        |
|  * Seat bookings written to BOTH Redis and PostgreSQL                 |
|  * Seat map reads from Redis first                                    |
|                                                                         |
|  REDIS HASH FOR SEAT STATUS:                                           |
|                                                                         |
|  Key: seats:{show_id}                                                 |
|  Fields:                                                               |
|    A-1 > "available"                                                  |
|    A-2 > "locked:user123:expire1705312345"                           |
|    A-3 > "booked:booking456"                                         |
|    ...                                                                 |
|                                                                         |
|  Single HGETALL returns entire seat map.                              |
|  Very fast (<1ms for 300 seats).                                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CONSISTENCY:                                                          |
|  * On booking: Update Redis THEN PostgreSQL                           |
|  * On startup/recovery: Rebuild Redis from PostgreSQL                |
|  * PostgreSQL is source of truth for bookings                        |
|  * Redis is source of truth for locks (ephemeral)                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 8.4 CACHE STAMPEDE (THUNDERING HERD PROBLEM)

```
+-------------------------------------------------------------------------+
|                    WHAT IS CACHE STAMPEDE?                             |
|                                                                         |
|  SCENARIO:                                                             |
|  * Movie list cache expires at exactly 10:00:00 AM                    |
|  * 10,000 users request movie list at 10:00:01 AM                     |
|  * All 10,000 requests find cache MISS                                |
|  * All 10,000 requests hit DATABASE simultaneously                    |
|  * Database overwhelmed > slow/crash                                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  TIMELINE:                                                             |
|                                                                         |
|       9:59:59              10:00:00              10:00:01              |
|          |                    |                    |                   |
|     Cache valid          Cache expires      10,000 requests           |
|     All from cache       TTL reached        ALL hit database!         |
|                                                                         |
|                                                                         |
|  +-------------+     +-------------+                                   |
|  |   Cache     |---->|  DATABASE   |                                   |
|  |   MISS!     |     |  10,000     |                                   |
|  |   x 10,000  |     |  queries!   |                                   |
|  +-------------+     +-------------+                                   |
|                            |                                           |
|                            v                                           |
|                      +-----------+                                     |
|                      |  CRASH!   |                                     |
|                      +-----------+                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

WHY DOES THIS HAPPEN?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CAUSE 1: FIXED TTL                                                    |
|  ---------------------                                                 |
|  All cache entries set with same TTL (e.g., 1 hour)                   |
|  If set at same time > expire at same time                            |
|                                                                         |
|  CAUSE 2: MASS INVALIDATION                                            |
|  --------------------------                                            |
|  Admin updates movie data > invalidates all movie caches              |
|  All users' next requests hit database                                |
|                                                                         |
|  CAUSE 3: CACHE RESTART                                                |
|  ---------------------                                                 |
|  Redis restarts (maintenance, crash)                                  |
|  All cached data lost > everything hits database                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SOLUTION 1: JITTERED TTL (RANDOMIZED EXPIRY)

```
+-------------------------------------------------------------------------+
|                    ADD RANDOMNESS TO TTL                               |
|                                                                         |
|  INSTEAD OF:                                                           |
|  TTL = 3600 seconds (exactly 1 hour)                                  |
|                                                                         |
|  USE:                                                                  |
|  TTL = 3600 + random(0, 600)  // 1 hour + 0-10 minutes random         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  EFFECT:                                                               |
|  * 10,000 cache entries set at same time                              |
|  * Each has slightly different expiry                                 |
|  * Entries expire GRADUALLY over 10 minutes                           |
|  * Database sees steady load, not spike                               |
|                                                                         |
|  EXAMPLE:                                                              |
|  Entry 1: expires at 10:00:00                                         |
|  Entry 2: expires at 10:03:45                                         |
|  Entry 3: expires at 10:07:22                                         |
|  Entry 4: expires at 10:01:15                                         |
|  ... spread over 10 minutes                                           |
|                                                                         |
|  PSEUDO-CODE:                                                          |
|  baseTTL = 3600                                                       |
|  jitter = random.nextInt(600)  // 0 to 600 seconds                    |
|  finalTTL = baseTTL + jitter                                          |
|  cache.set(key, value, finalTTL)                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SOLUTION 2: LOCKING / SINGLE-FLIGHT

```
+-------------------------------------------------------------------------+
|                    ONLY ONE REQUEST REBUILDS CACHE                     |
|                                                                         |
|  PRINCIPLE:                                                            |
|  When cache miss occurs, only ONE request should hit database.        |
|  Other requests WAIT for that one to populate cache.                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  FLOW:                                                                 |
|                                                                         |
|  Request 1: Cache miss                                                |
|             > Try to acquire rebuild lock                             |
|             > Lock acquired! Y                                        |
|             > Query database                                          |
|             > Store in cache                                          |
|             > Release lock                                            |
|             > Return data                                             |
|                                                                         |
|  Request 2-10,000: Cache miss                                         |
|             > Try to acquire rebuild lock                             |
|             > Lock NOT available (Request 1 holds it)                 |
|             > WAIT (sleep 50ms, retry)                                |
|             > Eventually cache is populated                           |
|             > Return cached data                                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PSEUDO-CODE:                                                          |
|                                                                         |
|  FUNCTION getData(key):                                               |
|      value = cache.get(key)                                           |
|      IF value != null:                                                |
|          RETURN value                                                 |
|                                                                         |
|      // Cache miss — try to acquire rebuild lock                      |
|      lockKey = "rebuild_lock:" + key                                  |
|      lockAcquired = redis.SET(lockKey, "1", NX, EX, 30)              |
|                                                                         |
|      IF lockAcquired:                                                 |
|          // I'm the one rebuilding                                    |
|          value = database.query(key)                                  |
|          cache.set(key, value, TTL_WITH_JITTER)                       |
|          redis.DEL(lockKey)                                           |
|          RETURN value                                                 |
|      ELSE:                                                             |
|          // Someone else is rebuilding, wait                          |
|          FOR i = 1 to 10:                                             |
|              sleep(50ms)                                              |
|              value = cache.get(key)                                   |
|              IF value != null:                                        |
|                  RETURN value                                         |
|                                                                         |
|          // Timeout — fall back to database                           |
|          RETURN database.query(key)                                   |
|                                                                         |
|  RESULT: Only 1 database query instead of 10,000!                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SOLUTION 3: BACKGROUND REFRESH (PROACTIVE)

```
+-------------------------------------------------------------------------+
|                    REFRESH BEFORE EXPIRY                               |
|                                                                         |
|  PRINCIPLE:                                                            |
|  Don't wait for cache to expire. Refresh it BEFORE expiry.           |
|  Cache is always warm. Users never see cache miss.                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  APPROACH A: EARLY EXPIRATION CHECK                                    |
|  ------------------------------------                                  |
|  Store: {value, expires_at, refresh_at}                               |
|                                                                         |
|  refresh_at = expires_at - 5 minutes                                  |
|                                                                         |
|  On read:                                                              |
|  * If current_time > refresh_at AND < expires_at:                    |
|    > Return stale value to user (fast!)                              |
|    > Trigger async background refresh                                |
|  * Next request gets fresh data                                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  APPROACH B: SCHEDULED REFRESH JOB                                     |
|  ---------------------------------                                     |
|  Background job runs every 10 minutes:                                |
|  * Find cache entries expiring in next 5 minutes                     |
|  * Proactively refresh them                                          |
|  * Cache never actually expires for popular keys                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  BEST FOR:                                                             |
|  * Expensive queries (aggregations, complex joins)                   |
|  * High-traffic keys (movie list, homepage)                          |
|  * Data that changes predictably (show schedules)                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SOLUTION 4: STALE-WHILE-REVALIDATE

```
+-------------------------------------------------------------------------+
|                    SERVE STALE, REFRESH IN BACKGROUND                  |
|                                                                         |
|  PRINCIPLE:                                                            |
|  Even after TTL expires, serve stale data immediately.               |
|  Meanwhile, refresh cache in background.                             |
|  User gets fast response (stale but acceptable).                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  STORE TWO TTLS:                                                       |
|  * soft_ttl: Time after which data is "stale" (refresh preferred)    |
|  * hard_ttl: Time after which data is deleted                        |
|                                                                         |
|  Example:                                                              |
|  soft_ttl = 1 hour                                                    |
|  hard_ttl = 2 hours                                                   |
|                                                                         |
|  FLOW:                                                                 |
|  * 0-1 hour: Return cached value (fresh)                             |
|  * 1-2 hours: Return cached value (stale) + trigger refresh          |
|  * >2 hours: Cache miss, must hit database                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  VALUE STRUCTURE:                                                      |
|  {                                                                     |
|    "data": {...},                                                     |
|    "created_at": 1705312345,                                          |
|    "soft_ttl": 3600,                                                  |
|    "hard_ttl": 7200                                                   |
|  }                                                                     |
|                                                                         |
|  PSEUDO-CODE:                                                          |
|                                                                         |
|  FUNCTION getData(key):                                               |
|      cached = cache.get(key)                                          |
|      IF cached == null:                                               |
|          RETURN fetchAndCache(key)  // Hard miss                     |
|                                                                         |
|      age = now() - cached.created_at                                  |
|                                                                         |
|      IF age < cached.soft_ttl:                                        |
|          RETURN cached.data         // Fresh                          |
|                                                                         |
|      IF age < cached.hard_ttl:                                        |
|          async { fetchAndCache(key) }  // Background refresh         |
|          RETURN cached.data         // Stale but fast                |
|                                                                         |
|      RETURN fetchAndCache(key)      // Expired, must refresh         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SOLUTION 5: CACHE WARMING ON STARTUP

```
+-------------------------------------------------------------------------+
|                    PRE-POPULATE CACHE                                  |
|                                                                         |
|  WHEN CACHE (REDIS) RESTARTS:                                          |
|  * All data lost                                                      |
|  * First requests all hit database                                   |
|  * Stampede!                                                          |
|                                                                         |
|  SOLUTION:                                                             |
|  Before accepting traffic, pre-load critical data into cache.        |
|                                                                         |
|  STARTUP SEQUENCE:                                                     |
|  1. Redis starts                                                      |
|  2. Warm-up job runs:                                                 |
|     - Load top 100 movies                                             |
|     - Load all cities                                                 |
|     - Load today's shows for major cities                            |
|  3. Only then: Accept traffic                                        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  KUBERNETES READINESS PROBE:                                           |
|  ----------------------------                                          |
|  Don't mark pod "ready" until cache is warmed.                       |
|  Traffic only routed to pods with warm caches.                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SUMMARY: DEFENSE AGAINST CACHE STAMPEDE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  +--------------------------+---------------------------------------+  |
|  | Technique                | When to Use                           |  |
|  +--------------------------+---------------------------------------+  |
|  | Jittered TTL             | Always (simple, effective)            |  |
|  +--------------------------+---------------------------------------+  |
|  | Locking/Single-flight    | Expensive queries, high traffic keys  |  |
|  +--------------------------+---------------------------------------+  |
|  | Background refresh       | Predictable, critical data            |  |
|  +--------------------------+---------------------------------------+  |
|  | Stale-while-revalidate   | When slight staleness is acceptable   |  |
|  +--------------------------+---------------------------------------+  |
|  | Cache warming            | After restarts, deployments           |  |
|  +--------------------------+---------------------------------------+  |
|                                                                         |
|  BOOKMYSHOW RECOMMENDATION:                                            |
|  ---------------------------                                           |
|  * Movie list: Jitter + Background refresh (critical, expensive)     |
|  * Show timings: Jitter + Stale-while-revalidate                     |
|  * Seat availability: No traditional cache (Redis is primary)        |
|  * On Redis restart: Cache warming before accepting traffic          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 9: NOTIFICATION SYSTEM

### 9.1 NOTIFICATION TYPES

```
+-------------------------------------------------------------------------+
|                    NOTIFICATION CHANNELS                               |
|                                                                         |
|  +--------------+-----------------------------------------------------+|
|  | Channel      | Use Cases                                          ||
|  +--------------+-----------------------------------------------------+|
|  | Email        | Booking confirmation (with ticket PDF)             ||
|  |              | Refund confirmation                                ||
|  |              | Marketing (new releases, offers)                   ||
|  +--------------+-----------------------------------------------------+|
|  | SMS          | Booking code (for entry)                           ||
|  |              | OTP for login/payment                              ||
|  |              | Show reminder (2 hours before)                     ||
|  +--------------+-----------------------------------------------------+|
|  | Push         | Seat available (if waitlisted)                     ||
|  |              | Offers and discounts                               ||
|  |              | New movie releases                                 ||
|  +--------------+-----------------------------------------------------+|
|  | In-App       | Lock expiring warning (2 min left)                 ||
|  |              | Real-time seat updates (WebSocket)                 ||
|  +--------------+-----------------------------------------------------+|
|                                                                         |
+-------------------------------------------------------------------------+
```

### 9.2 ASYNC NOTIFICATION ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                    EVENT-DRIVEN NOTIFICATIONS                          |
|                                                                         |
|  Booking                                                               |
|  Service                                                               |
|     |                                                                   |
|     | Publish Event                                                    |
|     v                                                                   |
|  +---------------------------------------------------------------+     |
|  |                         KAFKA                                  |     |
|  |  Topic: booking.events                                        |     |
|  |  {type: BOOKING_CONFIRMED, booking_id: xyz, user_id: abc}    |     |
|  +---------------------------------------------------------------+     |
|            |              |              |                              |
|            v              v              v                              |
|     +-----------+  +-----------+  +-----------+                       |
|     |   Email   |  |    SMS    |  |   Push    |                       |
|     |  Consumer |  |  Consumer |  |  Consumer |                       |
|     +-----+-----+  +-----+-----+  +-----+-----+                       |
|           |              |              |                              |
|           v              v              v                              |
|     +-----------+  +-----------+  +-----------+                       |
|     | SendGrid  |  |  Twilio   |  | Firebase  |                       |
|     |           |  |           |  |    FCM    |                       |
|     +-----------+  +-----------+  +-----------+                       |
|                                                                         |
|  WHY ASYNC?                                                            |
|  * Booking confirmation shouldn't wait for email to send             |
|  * Retry logic for failed deliveries                                 |
|  * Rate limiting for external providers                              |
|  * Different SLAs (email can be slower than SMS)                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 10: DATABASE ARCHITECTURE

### 10.1 SHARDING STRATEGY

```
+-------------------------------------------------------------------------+
|                    SHARDING BOOKMYSHOW                                 |
|                                                                         |
|  WHAT TO SHARD:                                                        |
|  * Bookings (5M/day × 365 × 3 years = 5.5 billion rows)              |
|  * Payments                                                           |
|  * Seat Inventory (per show)                                         |
|                                                                         |
|  WHAT NOT TO SHARD:                                                    |
|  * Movies (50K rows — fits in single instance)                       |
|  * Theaters (10K rows)                                               |
|  * Users (50M rows — shard if needed later)                          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SHARDING KEY OPTIONS:                                                 |
|  ---------------------                                                 |
|                                                                         |
|  OPTION 1: Shard by CITY_ID                                           |
|  ---------------------------                                           |
|  Each city's data on separate shard.                                  |
|                                                                         |
|  Pros:                                                                 |
|  * Locality — most queries are within a city                         |
|  * Can scale hot cities independently                                |
|                                                                         |
|  Cons:                                                                 |
|  * Uneven distribution (Mumbai >> small cities)                      |
|  * Cross-city queries need scatter-gather                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  OPTION 2: Shard by SHOW_ID (for seat_inventory)                      |
|  -----------------------------------------------                       |
|  Each show's seats on one shard.                                      |
|                                                                         |
|  Pros:                                                                 |
|  * All seat operations for a show hit one shard                      |
|  * Good for booking flow                                             |
|                                                                         |
|  Cons:                                                                 |
|  * Hot shows might overload a shard                                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  RECOMMENDED: HYBRID                                                   |
|  ---------------------                                                 |
|  * Seat inventory: Shard by show_id (all seats together)             |
|  * Bookings: Shard by user_id (user sees all their bookings)        |
|  * Use consistent hashing for even distribution                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 10.2 READ REPLICAS

```
+-------------------------------------------------------------------------+
|                    READ/WRITE SPLITTING                                |
|                                                                         |
|           +-------------------------------------------+                |
|           |                                           |                |
|           |              APPLICATION                  |                |
|           |                                           |                |
|           +---------------+---------------------------+                |
|                           |                                            |
|            +--------------+--------------+                             |
|            |                             |                              |
|            v                             v                              |
|     +-------------+            +---------------------+                 |
|     |   PRIMARY   |            |      REPLICAS       |                 |
|     |   (Write)   |----------->|       (Read)        |                 |
|     |             |  Async     |                     |                 |
|     |             |  Repl.     |   +---+ +---+ +---+|                 |
|     +-------------+            |   | R1| | R2| | R3||                 |
|                                |   +---+ +---+ +---+|                 |
|                                +---------------------+                 |
|                                                                         |
|  WRITE OPERATIONS (go to Primary):                                     |
|  * Create booking                                                     |
|  * Update seat status                                                 |
|  * Process payment                                                    |
|                                                                         |
|  READ OPERATIONS (go to Replicas):                                     |
|  * Browse movies                                                      |
|  * View show listings                                                 |
|  * Check booking history                                              |
|                                                                         |
|  CAUTION: Replication lag                                             |
|  * For seat availability, read from PRIMARY (must be fresh)          |
|  * For movie browsing, replica is fine (slight delay OK)             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 11: FAILURE SCENARIOS & RECOVERY

### 11.1 REDIS FAILURE

```
+-------------------------------------------------------------------------+
|                    REDIS DOWN — WHAT HAPPENS?                          |
|                                                                         |
|  IMPACT:                                                               |
|  * Can't acquire seat locks                                           |
|  * Can't check lock status                                            |
|  * Booking flow completely blocked                                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  MITIGATION: REDIS CLUSTER + SENTINEL                                  |
|  -------------------------------------                                 |
|  * Multiple Redis nodes (master + replicas)                           |
|  * Sentinel monitors health                                           |
|  * Automatic failover to replica if master dies                      |
|  * Typically < 30 seconds failover                                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  FALLBACK: DATABASE LOCKING                                            |
|  -------------------------------                                       |
|  If Redis cluster fails completely:                                   |
|  * Fall back to SELECT FOR UPDATE on database                        |
|  * Slower, less scalable, but WORKS                                  |
|  * Feature flag to switch between modes                              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  GRACEFUL DEGRADATION:                                                 |
|  -----------------------                                               |
|  * Disable seat selection temporarily                                 |
|  * Show "High demand. Try again in few minutes"                      |
|  * Continue serving read-only operations (browse, search)            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 11.2 DATABASE FAILURE

```
+-------------------------------------------------------------------------+
|                    DATABASE FAILURE HANDLING                           |
|                                                                         |
|  PRIMARY FAILURE:                                                      |
|  -----------------                                                     |
|  * All writes fail                                                    |
|  * Replica promoted to primary (automatic with tools like Patroni)   |
|  * Application reconnects to new primary                             |
|  * Downtime: 30-60 seconds typically                                 |
|                                                                         |
|  REPLICA FAILURE:                                                      |
|  ----------------                                                      |
|  * Read load redistributed to other replicas                         |
|  * Less impact — system continues                                    |
|  * Failed replica rebuilt from primary                               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  DATA DURABILITY:                                                      |
|  -----------------                                                     |
|  * Synchronous replication for critical data (bookings, payments)    |
|  * At least one replica confirms before commit                       |
|  * No data loss on primary failure                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 11.3 PAYMENT GATEWAY FAILURE

```
+-------------------------------------------------------------------------+
|                    HANDLING GATEWAY ISSUES                             |
|                                                                         |
|  GATEWAY TIMEOUT:                                                      |
|  -----------------                                                     |
|  * Retry with exponential backoff                                    |
|  * Same idempotency key (safe to retry)                              |
|  * After N retries, mark as PENDING for manual check                 |
|                                                                         |
|  GATEWAY COMPLETELY DOWN:                                              |
|  -------------------------                                             |
|  * Circuit breaker pattern                                           |
|  * After X failures, stop trying for Y seconds                       |
|  * Show "Payment service unavailable. Try later"                     |
|  * Offer alternative gateway if available                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  MULTI-GATEWAY STRATEGY:                                               |
|  -------------------------                                             |
|  Integrate multiple gateways (Razorpay + Paytm).                     |
|  If primary fails, route to secondary.                               |
|  Increases availability at cost of complexity.                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 11.4 RECONCILIATION

```
+-------------------------------------------------------------------------+
|                    DATA RECONCILIATION JOBS                            |
|                                                                         |
|  JOB 1: PAYMENT-BOOKING RECONCILIATION                                 |
|  -------------------------------------                                 |
|  Find mismatches:                                                     |
|  * Payment SUCCESS but Booking PENDING > Complete booking            |
|  * Payment PENDING for > 1 hour > Query gateway, update status       |
|  * Booking CONFIRMED but no Payment > Flag for review                |
|                                                                         |
|  JOB 2: REDIS-DB SYNC                                                  |
|  ---------------------                                                 |
|  * Compare Redis seat status with DB                                 |
|  * If Redis shows BOOKED but DB doesn't > Something wrong            |
|  * Rebuild Redis from DB if significant drift                        |
|                                                                         |
|  JOB 3: EXPIRED LOCK CLEANUP                                           |
|  -----------------------------                                         |
|  * Redis TTL handles this automatically                              |
|  * But verify: If DB shows LOCKED with old timestamp > Release       |
|                                                                         |
|  JOB 4: ORPHAN BOOKING CLEANUP                                         |
|  -------------------------------                                       |
|  * Bookings PENDING for > 30 minutes                                 |
|  * User never completed payment                                      |
|  * Mark as EXPIRED, release seats                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 12: SCALING & PERFORMANCE

### 12.1 HANDLING TRAFFIC SPIKES (BLOCKBUSTER RELEASE)

```
+-------------------------------------------------------------------------+
|                    VIRTUAL WAITING ROOM                                |
|                                                                         |
|  PROBLEM:                                                              |
|  500,000 users hit site at exactly 12:00 AM for advance booking.     |
|  System can handle 10,000 concurrent.                                 |
|  490,000 will get errors. BAD UX.                                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTION: VIRTUAL QUEUE                                               |
|  -------------------------                                             |
|                                                                         |
|  1. User arrives at 12:00 AM                                          |
|  2. Instead of seat page, user sees: "You're in queue"               |
|     Position: 45,231 of 500,000                                       |
|     Estimated wait: 15 minutes                                        |
|  3. Queue drains at controlled rate (1000 users/minute)              |
|  4. When user's turn: "Click to enter booking page"                  |
|     Has 2 minutes to click, else loses spot                          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  IMPLEMENTATION:                                                       |
|  ----------------                                                      |
|  * Redis sorted set: queue:{event_id}                                |
|  * Score = timestamp of arrival                                      |
|  * Worker pops from queue, issues "access token"                     |
|  * Token valid for 2 minutes                                         |
|  * Actual booking page validates token                               |
|                                                                         |
|  FAIRNESS: First come, first served.                                  |
|  CONTROLLED: System never overloaded.                                 |
|  TRANSPARENT: User knows their position.                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 12.2 AUTO-SCALING

```
+-------------------------------------------------------------------------+
|                    HORIZONTAL SCALING                                  |
|                                                                         |
|  STATELESS SERVICES:                                                   |
|  * API servers: Scale based on CPU/request rate                       |
|  * Search service: Scale based on query rate                          |
|  * Notification consumers: Scale based on queue depth                 |
|                                                                         |
|  SCALING TRIGGERS:                                                     |
|  +--------------------+--------------------+-------------------------+|
|  | Metric             | Scale Up           | Scale Down              ||
|  +--------------------+--------------------+-------------------------+|
|  | CPU Utilization    | > 70% for 2 min    | < 30% for 10 min       ||
|  | Request Latency    | p99 > 500ms        | p99 < 100ms            ||
|  | Queue Depth        | > 10,000 messages  | < 100 messages         ||
|  | Active Connections | > 80% capacity     | < 30% capacity         ||
|  +--------------------+--------------------+-------------------------+|
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PRE-SCALING FOR KNOWN EVENTS:                                         |
|  -------------------------------                                       |
|  For known blockbuster releases:                                      |
|  * Scale up 2 hours before booking opens                             |
|  * 10x normal capacity                                               |
|  * Pre-warm caches with movie/theater data                          |
|  * Scale down after peak passes                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 12.3 CDN FOR STATIC CONTENT

```
+-------------------------------------------------------------------------+
|                    CDN USAGE                                           |
|                                                                         |
|  WHAT TO SERVE FROM CDN:                                               |
|  * Movie posters, banners                                             |
|  * Theater images                                                     |
|  * CSS, JavaScript bundles                                            |
|  * Fonts, icons                                                       |
|  * Static HTML (landing page)                                         |
|                                                                         |
|  BENEFITS:                                                             |
|  * Reduce load on origin servers                                     |
|  * Lower latency (edge locations near users)                         |
|  * Handle traffic spikes (CDN absorbs load)                          |
|                                                                         |
|  CACHE HEADERS:                                                        |
|  * Immutable assets: Cache-Control: max-age=31536000, immutable      |
|  * Use content hash in filename: app.a1b2c3d4.js                     |
|  * API responses: No caching (dynamic)                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 13: TRADE-OFFS & DECISIONS

### 13.1 KEY DESIGN DECISIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DECISION 1: REDIS FOR LOCKS VS DATABASE LOCKS                         |
|  ---------------------------------------------                         |
|                                                                         |
|  Chose: Redis                                                          |
|                                                                         |
|  Trade-off:                                                            |
|  + Sub-millisecond lock operations                                    |
|  + Handles extreme concurrency                                        |
|  + TTL for automatic expiry                                           |
|  - Additional infrastructure component                                |
|  - Redis failure = booking failure                                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  DECISION 2: LAZY VS EAGER SEAT INVENTORY                              |
|  -----------------------------------------                             |
|                                                                         |
|  Chose: Lazy (create on demand)                                       |
|                                                                         |
|  Trade-off:                                                            |
|  + Much less storage (only locked/booked seats)                      |
|  + Faster show creation                                               |
|  - Slightly more complex read logic                                   |
|  - First lock creates row (INSERT vs UPDATE)                         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  DECISION 3: ORCHESTRATION VS CHOREOGRAPHY (SAGA)                      |
|  -------------------------------------------------                     |
|                                                                         |
|  Chose: Orchestration                                                  |
|                                                                         |
|  Trade-off:                                                            |
|  + Clear state visibility                                             |
|  + Easier debugging                                                   |
|  + Centralized compensation                                           |
|  - Single point of coordination                                       |
|  - Orchestrator becomes critical path                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  DECISION 4: STRONG VS EVENTUAL CONSISTENCY FOR SEATS                  |
|  ---------------------------------------------------                   |
|                                                                         |
|  Chose: Strong for locks, Eventual for display                        |
|                                                                         |
|  Trade-off:                                                            |
|  + Seat map can be slightly stale (OK for browsing)                  |
|  + Lock acquisition is always strongly consistent                    |
|  + Best of both worlds                                               |
|  - Complexity of two consistency models                              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  DECISION 5: LOCK DURATION (10 MINUTES)                                |
|  ----------------------------------------                              |
|                                                                         |
|  Trade-off:                                                            |
|  + Enough time for most payment flows                                |
|  + Not too long to block seats                                       |
|  - Some slow users might timeout                                     |
|  - Some fast users might waste 8 minutes                             |
|                                                                         |
|  Mitigation: Timer countdown, lock extension option                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 14: INTERVIEW FOLLOW-UP QUESTIONS

### 14.1 COMMON INTERVIEW QUESTIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q1: How do you prevent double booking?                                |
|  ---------------------------------------                               |
|  A: Redis distributed lock with SETNX for atomic lock acquisition.    |
|     Lua script for atomic multi-seat locking.                         |
|     Database optimistic lock as backup verification.                  |
|     Unique constraint on (show_id, seat_number, booking_id).         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q2: What happens if Redis fails?                                      |
|  -----------------------------------                                   |
|  A: Redis Cluster with Sentinel for high availability.                |
|     Fallback to database pessimistic locking (SELECT FOR UPDATE).    |
|     Circuit breaker pattern to fail fast.                             |
|     Graceful degradation: disable booking, allow browsing.           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q3: How do you handle 500K users at midnight release?                 |
|  ----------------------------------------------------                  |
|  A: Virtual waiting room with Redis sorted set queue.                 |
|     Controlled drain rate (1000 users/minute).                        |
|     Pre-scaled infrastructure (10x capacity).                         |
|     CDN for static assets.                                            |
|     Rate limiting per user.                                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q4: How do you ensure payment idempotency?                            |
|  -----------------------------------------                             |
|  A: Unique idempotency key generated at lock time.                    |
|     Store in payments table with UNIQUE constraint.                   |
|     On retry, check if key exists > return cached result.            |
|     Never call payment gateway twice for same idempotency key.       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q5: How would you design real-time seat updates?                      |
|  -------------------------------------------------                     |
|  A: WebSocket connection from client to server.                       |
|     Redis Pub/Sub for broadcasting seat changes.                      |
|     Client subscribes to channel: seats:{show_id}.                   |
|     On lock/book, publish event > all viewers see update.            |
|     Fallback: polling every 5 seconds.                               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q6: How do you shard the database?                                    |
|  ---------------------------------                                     |
|  A: Seat inventory: shard by show_id (all seats together).           |
|     Bookings: shard by user_id (user sees all their bookings).       |
|     Movies, theaters: no sharding needed (small datasets).           |
|     Consistent hashing for even distribution.                        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q7: Why not use Kafka for seat locks?                                 |
|  ------------------------------------                                  |
|  A: Kafka is for async, durable message passing.                     |
|     Seat locking needs synchronous, low-latency response.            |
|     User can't wait for Kafka consumer to process lock request.      |
|     Redis is purpose-built for low-latency atomic operations.        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q8: How do you handle seat selection timeout during payment?          |
|  ---------------------------------------------------------             |
|  A: Check lock validity BEFORE initiating payment.                    |
|     If < 2 minutes remaining, reject: "Lock expiring, restart".      |
|     If payment in progress and lock expires:                         |
|       - Complete payment, check if seats still ours                  |
|       - If seats gone: auto-refund + apology                         |
|       - Race is rare due to 2-minute buffer                          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q9: When would you use Redlock vs simple Redis lock?                  |
|  -----------------------------------------------------                 |
|  A: SIMPLE REDIS LOCK (with Sentinel):                               |
|     * 99% of use cases                                               |
|     * Lower latency (~1ms vs ~50ms)                                  |
|     * Simpler infrastructure                                         |
|     * Rare edge case of lost lock on failover is acceptable         |
|                                                                         |
|     REDLOCK:                                                          |
|     * Mission-critical events (Taylor Swift, IPL Finals)             |
|     * When double-booking cost is extremely high                     |
|     * Requires N independent Redis masters (typically 5)             |
|     * Higher latency acceptable for premium events                   |
|                                                                         |
|     HYBRID APPROACH:                                                  |
|     * Feature flag: enable Redlock for high-value events             |
|     * Default to simple lock for regular shows                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q10: What's your authentication strategy?                             |
|  -----------------------------------------                             |
|  A: JWT-based authentication:                                         |
|     * Access token: Short-lived (1 hour), contains user claims       |
|     * Refresh token: Long-lived (7-30 days), stored securely         |
|                                                                         |
|     PUBLIC APIs (no auth):                                            |
|     * GET /search, GET /events, GET /shows/{id}/seats                |
|                                                                         |
|     AUTHENTICATED APIs:                                               |
|     * POST /reservations, POST /bookings/confirm                     |
|                                                                         |
|     ADMIN APIs:                                                       |
|     * POST /events, PUT /pricing (role-based access)                 |
|                                                                         |
|     IMPLEMENTATION:                                                   |
|     * API Gateway validates JWT, extracts userId                     |
|     * Passes userId in header to downstream services                 |
|     * Services trust gateway (internal network)                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q11: How do you handle rate limiting?                                 |
|  -------------------------------------                                 |
|  A: MULTI-LAYER RATE LIMITING:                                        |
|                                                                         |
|     Per-User (authenticated):                                         |
|     * 100 requests/minute for regular APIs                           |
|     * 5 reservation attempts/minute (prevent hoarding)               |
|                                                                         |
|     Per-IP (unauthenticated):                                         |
|     * 50 requests/minute for search                                  |
|     * 10 login attempts/hour                                         |
|                                                                         |
|     Global (flash sales):                                             |
|     * Virtual waiting room for high-demand events                    |
|     * Controlled admission rate (1000 users/minute)                  |
|                                                                         |
|     IMPLEMENTATION:                                                   |
|     * Redis sorted set with sliding window                           |
|     * Key: "ratelimit:{userId}:{endpoint}"                          |
|     * Returns 429 Too Many Requests when exceeded                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q12: How do you split databases across microservices?                 |
|  ------------------------------------------------------                |
|  A: Each service owns its database (no shared tables):               |
|                                                                         |
|     AUTH SERVICE > Auth DB:                                           |
|     * users, roles, refresh_tokens                                   |
|                                                                         |
|     EVENT SERVICE > Events DB:                                        |
|     * movies, theaters, shows, pricing_rules                         |
|                                                                         |
|     INVENTORY SERVICE > Inventory DB:                                 |
|     * seats, reservations (HOT PATH)                                 |
|                                                                         |
|     BOOKING SERVICE > Bookings DB:                                    |
|     * bookings, booking_seats, payments                              |
|                                                                         |
|     SEARCH SERVICE > Elasticsearch:                                   |
|     * Denormalized indexes (synced via CDC)                          |
|                                                                         |
|     KEY PRINCIPLES:                                                   |
|     * NO cross-database foreign keys                                 |
|     * Reference by IDs, validate via API calls                       |
|     * Eventual consistency via events (Kafka/CDC)                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q13: What if payment succeeds but booking confirmation fails?         |
|  --------------------------------------------------------------        |
|  A: SAGA PATTERN with compensating transactions:                      |
|                                                                         |
|     1. Payment succeeds > Record payment_id                          |
|     2. Attempt booking confirmation                                  |
|     3. If confirmation fails:                                        |
|        a. Log the failure                                            |
|        b. Trigger auto-refund (compensating action)                  |
|        c. Release seat reservation                                   |
|        d. Notify user: "Sorry, booking failed. Refund initiated."   |
|                                                                         |
|     IDEMPOTENCY PROTECTION:                                           |
|     * Idempotency key generated at reservation time                  |
|     * Stored with booking attempt                                    |
|     * On retry, check if booking already exists > return cached     |
|                                                                         |
|     RECONCILIATION JOB:                                               |
|     * Runs every 5 minutes                                           |
|     * Finds: Payment SUCCESS but Booking PENDING                     |
|     * Either completes booking or triggers refund                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q14: How would you handle a Redis cluster failure mid-booking?        |
|  ---------------------------------------------------------------       |
|  A: GRACEFUL DEGRADATION strategy:                                    |
|                                                                         |
|     DETECTION:                                                        |
|     * Health checks fail > Circuit breaker opens                     |
|     * Stop sending requests to Redis                                 |
|                                                                         |
|     FALLBACK OPTIONS:                                                 |
|     1. Database pessimistic lock (SELECT FOR UPDATE)                 |
|        * Slower but works                                            |
|        * Feature flag to switch modes                                |
|                                                                         |
|     2. Graceful degradation                                          |
|        * Disable new reservations temporarily                        |
|        * Show "High demand. Try again in few minutes"               |
|        * Continue serving read-only (browse, search)                 |
|                                                                         |
|     RECOVERY:                                                         |
|     * When Redis recovers, warm cache from database                  |
|     * Resume normal operations                                       |
|     * Reconcile any in-flight transactions                          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q15: How do you prevent bot attacks during flash sales?               |
|  --------------------------------------------------------              |
|  A: MULTI-LAYER DEFENSE:                                              |
|                                                                         |
|     LAYER 1 - Rate Limiting:                                          |
|     * Per-user, per-IP limits                                        |
|     * Aggressive limits on /reservations endpoint                    |
|                                                                         |
|     LAYER 2 - CAPTCHA:                                                |
|     * reCAPTCHA on reservation for high-demand events                |
|     * Invisible CAPTCHA for legitimate users                         |
|                                                                         |
|     LAYER 3 - Virtual Waiting Room:                                   |
|     * Queue-based admission during flash sales                       |
|     * Random delays to deter bots                                    |
|                                                                         |
|     LAYER 4 - Device Fingerprinting:                                  |
|     * Detect multiple accounts from same device                      |
|     * Flag suspicious patterns                                       |
|                                                                         |
|     LAYER 5 - Purchase Limits:                                        |
|     * Max 6 tickets per user per event                               |
|     * Phone verification for accounts                                |
|                                                                         |
|     LAYER 6 - Post-Purchase Review:                                   |
|     * ML model to detect suspicious patterns                         |
|     * Cancel bulk orders from same IP/payment method                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q16: How do you ensure zero data loss for bookings?                   |
|  ----------------------------------------------------                  |
|  A: MULTI-LAYER DATA PROTECTION:                                      |
|                                                                         |
|     DATABASE LEVEL:                                                   |
|     * Synchronous replication for bookings table                     |
|     * At least 1 replica confirms before commit                      |
|     * WAL (Write-Ahead Logging) for durability                       |
|                                                                         |
|     APPLICATION LEVEL:                                                |
|     * Outbox pattern for event publishing                            |
|     * Idempotency keys prevent duplicate processing                  |
|                                                                         |
|     INFRASTRUCTURE LEVEL:                                             |
|     * Multi-AZ database deployment                                   |
|     * Automated backups every hour                                   |
|     * Point-in-time recovery capability                              |
|                                                                         |
|     RECONCILIATION:                                                   |
|     * Hourly reconciliation jobs                                     |
|     * Payment gateway > Our DB comparison                            |
|     * Alert on any mismatches                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 14.2 DEEP DIVE INTERVIEW QUESTIONS (ADVANCED)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q17: Walk me through what happens from click to confirmation          |
|  ---------------------------------------------------------------       |
|                                                                         |
|  A: COMPLETE BOOKING FLOW:                                             |
|                                                                         |
|  STEP 1: USER SELECTS SEATS                                            |
|  ---------------------------                                           |
|  * Client: POST /api/reservations {showId, seats: ["A1", "A2"]}       |
|  * API Gateway: Validate JWT, extract userId                          |
|  * Rate limiter: Check user hasn't exceeded reservation limit         |
|                                                                         |
|  STEP 2: ACQUIRE DISTRIBUTED LOCKS (Booking Service > Redis)          |
|  ---------------------------------------------------------             |
|  * Generate lockValue = UUID                                          |
|  * Sort seats alphabetically (deadlock prevention)                    |
|  * For each seat:                                                     |
|      SETNX "lock:show123:A1" {userId}:{lockValue} EX 600             |
|  * If ANY fails: Release acquired locks, return 409 Conflict          |
|  * If ALL succeed: Continue                                           |
|                                                                         |
|  STEP 3: CREATE RESERVATION (Booking Service > Inventory DB)          |
|  --------------------------------------------------------              |
|  * Insert reservation record (expires_at = now + 10 min)              |
|  * Update seat status: AVAILABLE > RESERVED                           |
|  * Return: reservationId, expiresAt, totalAmount                      |
|                                                                         |
|  STEP 4: USER COMPLETES PAYMENT (Client > Payment Gateway)            |
|  ---------------------------------------------------------             |
|  * Client receives reservationId, shows payment form                  |
|  * Timer counting down: "Complete in 9:45..."                        |
|  * User enters payment details                                        |
|                                                                         |
|  STEP 5: CONFIRM BOOKING (Client > Booking Service)                   |
|  ----------------------------------------------------                  |
|  * Client: POST /api/bookings/confirm {reservationId, paymentToken}  |
|  * Verify reservation not expired                                     |
|  * Verify lock still held (GET lock key, check value matches)        |
|  * Create idempotency key                                             |
|                                                                         |
|  STEP 6: PROCESS PAYMENT (Booking Service > Payment Gateway)          |
|  ---------------------------------------------------------             |
|  * Call payment gateway with idempotency key                          |
|  * Wait for response (timeout: 30 seconds)                            |
|  * If timeout: Log, mark PENDING for reconciliation                   |
|  * If success: Continue                                               |
|  * If failure: Return error, keep reservation (user can retry)        |
|                                                                         |
|  STEP 7: FINALIZE BOOKING (Booking Service > Bookings DB)             |
|  ------------------------------------------------------                |
|  * Create booking record (status: CONFIRMED)                          |
|  * Create booking_seats records                                       |
|  * Update seat status: RESERVED > BOOKED                              |
|  * Update event available_seats count (optimistic lock)               |
|                                                                         |
|  STEP 8: RELEASE LOCKS (Booking Service > Redis)                      |
|  -------------------------------------------------                     |
|  * For each seat: DEL lock if value matches (Lua script)              |
|  * Locks released AFTER database commit                               |
|                                                                         |
|  STEP 9: PUBLISH EVENT (Booking Service > Kafka)                      |
|  -------------------------------------------------                     |
|  * Event: BOOKING_CONFIRMED {bookingId, userId, seats, amount}       |
|                                                                         |
|  STEP 10: SEND NOTIFICATIONS (Notification Service)                   |
|  ----------------------------------------------------                  |
|  * Email: Booking confirmation with ticket PDF                        |
|  * SMS: Booking code for entry                                        |
|  * Push: "Booking confirmed!"                                        |
|                                                                         |
|  TOTAL LATENCY: ~2-3 seconds (mostly payment gateway)                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q18: How would you design Redlock for BookMyShow?                     |
|  --------------------------------------------------                    |
|                                                                         |
|  A: REDLOCK IMPLEMENTATION FOR HIGH-VALUE EVENTS:                     |
|                                                                         |
|  INFRASTRUCTURE:                                                       |
|  * 5 independent Redis masters (not replicas!)                        |
|  * Different availability zones                                       |
|  * Each master: 16GB RAM, SSD                                         |
|                                                                         |
|  ALGORITHM:                                                            |
|  1. Get current timestamp T1                                          |
|  2. Try SET lock NX EX 30 on all 5 Redis instances                   |
|  3. Calculate elapsed = T2 - T1                                       |
|  4. Lock valid if:                                                    |
|     * Acquired on >= 3 instances (N/2+1)                             |
|     * validity = TTL - elapsed - clock_drift > 0                     |
|  5. If invalid: Release on ALL instances                             |
|                                                                         |
|  CODE SNIPPET:                                                         |
|  --------------                                                        |
|  public boolean tryRedlock(String seatKey, String value) {            |
|      int acquired = 0;                                                |
|      long start = System.currentTimeMillis();                         |
|                                                                         |
|      for (Redis redis : redisInstances) {                             |
|          if (redis.setNx(seatKey, value, 30_000)) {                   |
|              acquired++;                                              |
|          }                                                             |
|      }                                                                 |
|                                                                         |
|      long validity = 30_000 - (now() - start) - 100; // drift        |
|      return acquired >= 3 && validity > 0;                            |
|  }                                                                     |
|                                                                         |
|  WHEN TO USE:                                                          |
|  * High-demand events (flag per event)                                |
|  * IPL finals, concert premieres                                      |
|  * NOT for regular movie bookings (overkill)                          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q19: Design the seat status state machine                             |
|  -----------------------------------------                             |
|                                                                         |
|  A: SEAT STATUS TRANSITIONS:                                           |
|                                                                         |
|                    +--------------+                                    |
|                    |  AVAILABLE   |                                    |
|                    +------+-------+                                    |
|                           |                                            |
|              User selects | (Redis lock + DB update)                  |
|                           v                                            |
|                    +--------------+                                    |
|           +--------|  RESERVED    |--------+                          |
|           |        +------+-------+        |                          |
|           |               |                |                          |
|    10 min |   Payment     | Payment       | 10 min                   |
|    timeout|   succeeds    | fails         | timeout                  |
|           |               |                |                          |
|           v               v                v                          |
|    +----------+    +----------+    +--------------+                  |
|    |AVAILABLE |    |  BOOKED  |    |  AVAILABLE   |                  |
|    |(released)|    +----------+    |  (released)  |                  |
|    +----------+          |         +--------------+                  |
|                          |                                            |
|                   Cancel | (with refund)                             |
|                          v                                            |
|                   +--------------+                                    |
|                   |  AVAILABLE   |                                    |
|                   | (after grace |                                    |
|                   |   period)    |                                    |
|                   +--------------+                                    |
|                                                                         |
|  VALID TRANSITIONS:                                                   |
|  * AVAILABLE > RESERVED (user locks)                                 |
|  * RESERVED > BOOKED (payment success)                               |
|  * RESERVED > AVAILABLE (timeout/failure)                            |
|  * BOOKED > AVAILABLE (cancellation after grace)                     |
|                                                                         |
|  INVALID TRANSITIONS (must reject):                                   |
|  * BOOKED > RESERVED (can't re-reserve booked seat)                  |
|  * AVAILABLE > BOOKED (must go through RESERVED)                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q20: How do you handle partial failures in multi-seat booking?        |
|  ---------------------------------------------------------------       |
|                                                                         |
|  A: ALL-OR-NOTHING SEMANTICS with Lua script:                         |
|                                                                         |
|  PROBLEM:                                                              |
|  User wants seats A1, A2, A3                                          |
|  A1: Lock success Y                                                   |
|  A2: Lock success Y                                                   |
|  A3: Lock FAIL X (someone else has it)                               |
|  Now A1, A2 are locked but user can't book. Bad UX.                  |
|                                                                         |
|  SOLUTION: Lua Script (atomic)                                        |
|  ------------------------------                                        |
|  -- Phase 1: Check all seats                                          |
|  for i, key in ipairs(KEYS) do                                        |
|      if redis.call('EXISTS', key) == 1 then                          |
|          return {err='SEAT_TAKEN', seat=key}                         |
|      end                                                              |
|  end                                                                   |
|  -- Phase 2: Lock all seats (only if Phase 1 passed)                 |
|  for i, key in ipairs(KEYS) do                                        |
|      redis.call('SET', key, ARGV[1], 'EX', ARGV[2])                  |
|  end                                                                   |
|  return {ok=true}                                                     |
|                                                                         |
|  GUARANTEE:                                                            |
|  * Either ALL seats locked, or NONE locked                           |
|  * No partial state possible                                         |
|  * Lua scripts are atomic in Redis                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 14.3 HOMEWORK ASSIGNMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. Design the waitlist feature                                        |
|     When a show is sold out, users can join waitlist.                 |
|     If someone cancels, notify waitlist users.                        |
|                                                                         |
|  2. Design dynamic pricing                                             |
|     Like airline tickets — price changes based on demand.            |
|     Higher price for popular shows/times.                             |
|                                                                         |
|  3. Design the refund system                                           |
|     Different refund policies based on cancellation time.            |
|     Integration with payment gateway for refunds.                    |
|                                                                         |
|  4. Design the recommendation engine                                   |
|     "Because you watched X, you might like Y"                        |
|     Collaborative filtering vs content-based.                        |
|                                                                         |
|  5. Design multi-region deployment                                     |
|     Users in Mumbai should hit Mumbai servers.                       |
|     How to handle cross-region bookings?                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 15: THEORETICAL FOUNDATIONS

### 15.1 CAP THEOREM

```
+-------------------------------------------------------------------------+
|                    CAP THEOREM FOR BOOKING SYSTEMS                      |
|                                                                         |
|  In a distributed system, you can only guarantee TWO of THREE:         |
|                                                                         |
|  CONSISTENCY (C):     All nodes see same data at same time             |
|  AVAILABILITY (A):    System always responds (no errors)               |
|  PARTITION (P):       System works despite network failures            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  BOOKMYSHOW CHOICES:                                                    |
|                                                                         |
|  SEAT INVENTORY (CP - Choose Consistency):                              |
|  -------------------------------------------                            |
|  * Can't have two people book same seat                                |
|  * Brief unavailability acceptable                                     |
|  * "Please try again" is better than double-booking                   |
|                                                                         |
|  SHOW CATALOG (AP - Choose Availability):                               |
|  -----------------------------------------                              |
|  * Users should always see movie listings                              |
|  * Slightly stale data is OK (show still available)                   |
|  * Cache heavily, sync eventually                                      |
|                                                                         |
|  USER SESSIONS (AP - Choose Availability):                              |
|  ------------------------------------------                             |
|  * Users must stay logged in                                           |
|  * Session data can be eventually consistent                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 15.2 ACID vs BASE

```
+-------------------------------------------------------------------------+
|                    ACID (Traditional Databases)                         |
|                                                                         |
|  ATOMICITY:    All or nothing transactions                             |
|  CONSISTENCY:  Data always valid (constraints respected)               |
|  ISOLATION:    Concurrent transactions don't interfere                 |
|  DURABILITY:   Committed data survives crashes                         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  BOOKING TRANSACTION (ACID Required):                                   |
|                                                                         |
|  BEGIN TRANSACTION;                                                     |
|    -- Lock seats                                                       |
|    UPDATE seats SET status = 'BOOKED', user_id = 123                  |
|    WHERE seat_id IN (1, 2, 3) AND status = 'AVAILABLE';               |
|                                                                         |
|    -- Create booking                                                   |
|    INSERT INTO bookings (...);                                        |
|                                                                         |
|    -- Record payment                                                   |
|    INSERT INTO payments (...);                                        |
|  COMMIT;  -- All succeed or all fail                                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  ISOLATION LEVELS FOR BOOKING:                                          |
|                                                                         |
|  SERIALIZABLE:  Safest but slowest (use for seat locking)             |
|  READ COMMITTED: Good default (use for reads)                          |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    BASE (NoSQL / Distributed)                           |
|                                                                         |
|  BASICALLY AVAILABLE:  System always responds                          |
|  SOFT STATE:           State may change over time                      |
|  EVENTUAL CONSISTENCY: All replicas converge eventually                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WHERE WE USE BASE:                                                     |
|  * Show browsing / search results                                     |
|  * User reviews and ratings                                           |
|  * Analytics and reporting                                            |
|  * Notification delivery                                              |
|                                                                         |
|  WHERE WE NEED ACID:                                                    |
|  * Seat reservation                                                   |
|  * Payment processing                                                 |
|  * Booking confirmation                                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 15.3 CONSISTENCY MODELS

```
+-------------------------------------------------------------------------+
|                    CONSISTENCY SPECTRUM                                 |
|                                                                         |
|  STRONGEST <---------------------------------------------> WEAKEST    |
|                                                                         |
|  Linearizable > Sequential > Causal > Eventual > None                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  LINEARIZABILITY:                                                       |
|  -----------------                                                      |
|  * Reads always return most recent write                               |
|  * As if single copy of data                                           |
|  * USE FOR: Seat availability checks                                   |
|                                                                         |
|  EVENTUAL CONSISTENCY:                                                  |
|  ---------------------                                                  |
|  * Given time, all replicas converge                                   |
|  * May read stale data temporarily                                    |
|  * USE FOR: Movie catalog, theater listings                           |
|                                                                         |
|  READ-YOUR-WRITES:                                                      |
|  -------------------                                                    |
|  * User always sees their own updates                                  |
|  * May not see others' updates immediately                            |
|  * USE FOR: User's booking history                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 15.4 DATABASE SCALING CONCEPTS

```
+-------------------------------------------------------------------------+
|                    REPLICATION                                          |
|                                                                         |
|  SINGLE-LEADER (Master-Slave):                                          |
|                                                                         |
|       Writes ----> +--------+                                          |
|                    | LEADER |                                          |
|       Reads  ----> |        |                                          |
|                    +---+----+                                          |
|              +---------+---------+                                     |
|              v         v         v                                     |
|         +--------++--------++--------+                                |
|  Reads> |Follower||Follower||Follower| <Reads                         |
|         +--------++--------++--------+                                |
|                                                                         |
|  BOOKING SYSTEM:                                                        |
|  * All bookings write to leader                                        |
|  * Seat availability reads from leader (for accuracy)                 |
|  * Movie listings can read from followers                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  REPLICATION LAG:                                                       |
|  -----------------                                                      |
|  * Followers may be milliseconds behind leader                        |
|  * For seat booking: ALWAYS read from leader                          |
|  * For show listings: Followers OK (eventual consistency)             |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    SHARDING                                             |
|                                                                         |
|  BOOKING SYSTEM SHARDING STRATEGY:                                      |
|                                                                         |
|  OPTION 1: Shard by Event/Show ID                                      |
|  ---------------------------------                                      |
|  * All seats for one show on same shard                               |
|  * Simple seat locking (no cross-shard)                               |
|  * Hot shows = hot shards                                              |
|                                                                         |
|  OPTION 2: Shard by City/Region                                        |
|  ----------------------------------                                     |
|  * Mumbai users > Mumbai shard                                        |
|  * Lower latency                                                       |
|  * Some cities much busier                                            |
|                                                                         |
|  OPTION 3: Shard by Theater ID                                         |
|  ----------------------------------                                     |
|  * Each theater on its own shard                                      |
|  * Balanced distribution                                               |
|  * Cross-theater queries need scatter-gather                          |
|                                                                         |
|  RECOMMENDATION: Shard by Event ID                                     |
|  * Booking is always for specific event                               |
|  * All seat operations stay on one shard                              |
|  * Use consistent hashing for flexibility                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 15.5 CACHING PATTERNS

```
+-------------------------------------------------------------------------+
|                    CACHE PATTERNS FOR BOOKING                           |
|                                                                         |
|  CACHE-ASIDE (Lazy Loading):                                            |
|  -----------------------------                                          |
|  1. Check cache                                                        |
|  2. Cache miss > query DB                                              |
|  3. Store in cache                                                     |
|  4. Return                                                             |
|                                                                         |
|  USE FOR: Movie details, theater info                                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WRITE-THROUGH:                                                         |
|  ---------------                                                        |
|  1. Write to cache                                                     |
|  2. Cache writes to DB                                                 |
|  3. Return                                                             |
|                                                                         |
|  USE FOR: User sessions, seat locks (Redis)                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WHAT TO CACHE:                                                         |
|  +-----------------+-----------+------------------------------------+  |
|  | Data            | TTL       | Notes                              |  |
|  +-----------------+-----------+------------------------------------+  |
|  | Movie catalog   | 1 hour    | Invalidate on admin update         |  |
|  | Theater list    | 6 hours   | Rarely changes                     |  |
|  | Show schedule   | 30 min    | More dynamic                       |  |
|  | Seat map layout | 24 hours  | Theater-specific, static           |  |
|  | Seat status     | NO CACHE  | Must be real-time                  |  |
|  | User session    | 24 hours  | Redis                              |  |
|  | Seat locks      | 10 min    | Redis with TTL                     |  |
|  +-----------------+-----------+------------------------------------+  |
|                                                                         |
|  CRITICAL: Never cache seat availability for booking flow!             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 15.6 LOAD BALANCING

```
+-------------------------------------------------------------------------+
|                    LOAD BALANCING ALGORITHMS                            |
|                                                                         |
|  ROUND ROBIN:                                                           |
|  Request 1 > Server A                                                  |
|  Request 2 > Server B                                                  |
|  Request 3 > Server A (repeat)                                         |
|                                                                         |
|  LEAST CONNECTIONS:                                                     |
|  Route to server with fewest active connections                        |
|  Good for long booking transactions                                    |
|                                                                         |
|  IP HASH:                                                               |
|  Same user always goes to same server                                  |
|  Good for session affinity                                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  BOOKING SYSTEM RECOMMENDATION:                                         |
|                                                                         |
|  * API Gateway: Round Robin with health checks                         |
|  * Payment Service: Least Connections (long requests)                  |
|  * Search Service: Round Robin (stateless)                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  LAYER 4 vs LAYER 7:                                                    |
|                                                                         |
|  Layer 4 (TCP):    Fast, no content inspection                         |
|  Layer 7 (HTTP):   Content-based routing, SSL termination             |
|                                                                         |
|  BOOKING SYSTEM:                                                        |
|  * NLB (L4): High throughput, flash sale traffic                      |
|  * ALB (L7): Path routing (/api/*, /admin/*)                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 15.7 RATE LIMITING ALGORITHMS

```
+-------------------------------------------------------------------------+
|                    RATE LIMITING FOR BOOKING                            |
|                                                                         |
|  TOKEN BUCKET:                                                          |
|  --------------                                                         |
|  * Bucket holds tokens (max = burst size)                              |
|  * Tokens added at fixed rate                                          |
|  * Request consumes token                                              |
|  * No token = rejected (429)                                           |
|                                                                         |
|  ALLOWS BURSTS: User can make 10 quick requests if bucket full        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SLIDING WINDOW:                                                        |
|  ----------------                                                       |
|  * Count requests in last N seconds                                    |
|  * Smooth rate limiting                                                |
|  * No edge bursts                                                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  BOOKING SYSTEM LIMITS:                                                 |
|  +-----------------------+----------------------------------------+    |
|  | Endpoint              | Limit                                  |    |
|  +-----------------------+----------------------------------------+    |
|  | Search / Browse       | 100 req/min per user                   |    |
|  | Seat Selection        | 20 req/min per user                    |    |
|  | Payment               | 5 req/min per user                     |    |
|  | OTP Requests          | 3 req/min per phone                    |    |
|  | Booking (global)      | 10,000 req/sec (circuit breaker)       |    |
|  +-----------------------+----------------------------------------+    |
|                                                                         |
|  IMPLEMENTATION (Redis):                                                |
|  -------------------------                                              |
|  Key: rate_limit:{user_id}:{endpoint}                                  |
|  INCR key                                                              |
|  EXPIRE key 60  (1 minute window)                                      |
|  If count > limit: return 429                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 15.8 MESSAGE QUEUE SEMANTICS

```
+-------------------------------------------------------------------------+
|                    DELIVERY GUARANTEES                                  |
|                                                                         |
|  AT-MOST-ONCE:                                                          |
|  * Delivered 0 or 1 times                                              |
|  * No retries, may lose messages                                       |
|  * USE: Metrics, logs                                                  |
|                                                                         |
|  AT-LEAST-ONCE:                                                         |
|  * Delivered 1 or more times                                           |
|  * Retries until ACK                                                   |
|  * May have duplicates                                                 |
|  * USE: Most events (with idempotent consumers)                        |
|                                                                         |
|  EXACTLY-ONCE:                                                          |
|  * Delivered exactly 1 time                                            |
|  * Hardest to achieve                                                  |
|  * USE: Payment confirmations                                          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  BOOKING SYSTEM EVENTS:                                                 |
|                                                                         |
|  Event: SeatReserved                                                   |
|  Delivery: At-least-once                                               |
|  Consumer: Notification service (idempotent - check if sent)          |
|                                                                         |
|  Event: PaymentCompleted                                               |
|  Delivery: Exactly-once (idempotency key)                             |
|  Consumer: Booking service                                             |
|                                                                         |
|  Event: BookingConfirmed                                               |
|  Delivery: At-least-once                                               |
|  Consumer: Email/SMS service                                           |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    ORDERING GUARANTEES                                  |
|                                                                         |
|  KAFKA PARTITIONS:                                                      |
|  ------------------                                                     |
|  * Messages with same key > same partition > ordered                  |
|  * Different keys > different partitions > no order guarantee         |
|                                                                         |
|  BOOKING SYSTEM:                                                        |
|  * Partition key = event_id                                           |
|  * All events for same show > same partition > ordered               |
|                                                                         |
|  Event flow (ordered within partition):                                |
|  1. SeatReserved (event_123)                                          |
|  2. PaymentInitiated (event_123)                                      |
|  3. PaymentCompleted (event_123)                                      |
|  4. BookingConfirmed (event_123)                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 15.9 DISTRIBUTED LOCKING THEORY

```
+-------------------------------------------------------------------------+
|                    LOCKING STRATEGIES                                   |
|                                                                         |
|  PESSIMISTIC LOCKING:                                                   |
|  ---------------------                                                  |
|  * Lock resource BEFORE operation                                      |
|  * Others wait or fail                                                 |
|  * Safe but can cause contention                                      |
|                                                                         |
|  SELECT * FROM seats WHERE id = 1 FOR UPDATE;                         |
|  -- Other transactions blocked until commit                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  OPTIMISTIC LOCKING:                                                    |
|  ---------------------                                                  |
|  * Read with version number                                            |
|  * Update only if version matches                                      |
|  * Retry on version mismatch                                          |
|                                                                         |
|  UPDATE seats                                                          |
|  SET status = 'RESERVED', version = version + 1                       |
|  WHERE id = 1 AND version = 5;                                        |
|  -- If affected_rows = 0, version changed > retry                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  DISTRIBUTED LOCK (Redis):                                              |
|  ---------------------------                                            |
|  * SET key value NX EX 30                                             |
|  * NX = only if not exists                                            |
|  * EX = expire in 30 seconds                                          |
|  * Release with Lua script (check ownership)                          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  REDLOCK (Multi-node):                                                  |
|  -----------------------                                                |
|  * Acquire lock on N/2 + 1 Redis nodes                                |
|  * Must acquire within time limit                                     |
|  * Handles single Redis failure                                       |
|                                                                         |
|  BOOKING SYSTEM APPROACH:                                               |
|  * Redis lock for seat reservation (fast)                             |
|  * DB optimistic lock for final confirmation (safe)                   |
|  * Lua scripts for atomic multi-seat locking                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 15.10 API DESIGN PRINCIPLES

```
+-------------------------------------------------------------------------+
|                    REST API BEST PRACTICES                              |
|                                                                         |
|  RESOURCE NAMING:                                                       |
|  -----------------                                                      |
|  * Use nouns: /shows, /bookings, /seats                               |
|  * Hierarchical: /shows/{id}/seats                                    |
|  * Plural: /movies not /movie                                         |
|                                                                         |
|  HTTP METHODS:                                                          |
|  --------------                                                         |
|  GET    /shows              List shows                                 |
|  GET    /shows/123          Get single show                            |
|  POST   /bookings           Create booking                             |
|  DELETE /reservations/456   Cancel reservation                         |
|                                                                         |
|  STATUS CODES:                                                          |
|  --------------                                                         |
|  200 OK           Success                                              |
|  201 Created      Booking created                                      |
|  400 Bad Request  Invalid input                                        |
|  404 Not Found    Show not found                                       |
|  409 Conflict     Seat already booked                                  |
|  429 Too Many     Rate limited                                         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  IDEMPOTENCY:                                                           |
|  -------------                                                          |
|  POST /bookings                                                        |
|  Idempotency-Key: abc-123-def                                         |
|                                                                         |
|  * Client generates unique key                                         |
|  * Server returns cached response on retry                            |
|  * Safe to retry on timeout                                           |
|                                                                         |
|  CRITICAL FOR:                                                          |
|  * Payment processing                                                 |
|  * Booking confirmation                                               |
|  * Seat reservation                                                   |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    PAGINATION                                           |
|                                                                         |
|  CURSOR-BASED (Recommended):                                            |
|  -----------------------------                                          |
|  GET /shows?limit=20&cursor=eyJpZCI6MTIzfQ==                           |
|                                                                         |
|  Response:                                                              |
|  {                                                                      |
|    "data": [...],                                                      |
|    "next_cursor": "eyJpZCI6MTQzfQ==",                                  |
|    "has_more": true                                                    |
|  }                                                                      |
|                                                                         |
|  * Efficient (index scan)                                              |
|  * Consistent with real-time data                                     |
|  * Better than OFFSET for large datasets                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF DOCUMENT

