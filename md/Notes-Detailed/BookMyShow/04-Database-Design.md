# BOOKMYSHOW SYSTEM DESIGN
*Chapter 4: Database Design*

A well-designed database schema is the foundation of a reliable booking system.
This chapter covers table design, indexing strategies, and scaling approaches.

## SECTION 4.1: ENTITY RELATIONSHIP DIAGRAM

```
+-------------------------------------------------------------------------+
|                                                                         |
|                    CORE ENTITY RELATIONSHIPS                           |
|                                                                         |
|  +---------+         +---------+         +---------+                  |
|  |  USER   |         |  CITY   |         |  MOVIE  |                  |
|  |---------|         |---------|         |---------|                  |
|  | id (PK) |         | id (PK) |         | id (PK) |                  |
|  | name    |         | name    |         | title   |                  |
|  | email   |         | state   |         | genre   |                  |
|  | phone   |         |         |         | duration|                  |
|  +----+----+         +----+----+         +----+----+                  |
|       |                   |                   |                        |
|       |                   |                   |                        |
|       |              +----+----+              |                        |
|       |              |  VENUE  |<-------------+                        |
|       |              |---------|  (Movies shown at venues)            |
|       |              | id (PK) |                                       |
|       |              | name    |                                       |
|       |              | city_id | (FK)                                  |
|       |              | address |                                       |
|       |              +----+----+                                       |
|       |                   |                                            |
|       |              +----+----+                                       |
|       |              | SCREEN  |                                       |
|       |              |---------|                                       |
|       |              | id (PK) |                                       |
|       |              |venue_id | (FK)                                  |
|       |              | name    |                                       |
|       |              |capacity |                                       |
|       |              +----+----+                                       |
|       |                   |                                            |
|       |              +----+----+         +------------+               |
|       |              |  SHOW   |---------| SHOW_SEAT  |               |
|       |              |---------|         |------------|               |
|       |              | id (PK) |         | show_id(FK)|               |
|       |              |screen_id|         | seat_id    |               |
|       |              |movie_id |         | status     |               |
|       |              |datetime |         | price      |               |
|       |              +----+----+         | booking_id |               |
|       |                   |              +------------+               |
|       |                   |                                            |
|       |              +----+----+                                       |
|       +--------------|BOOKING  |                                       |
|                      |---------|                                       |
|                      | id (PK) |                                       |
|                      | user_id | (FK)                                  |
|                      | show_id | (FK)                                  |
|                      | status  |                                       |
|                      | total   |                                       |
|                      +---------+                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.2: TABLE SCHEMAS

### USERS TABLE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CREATE TABLE users (                                                  |
|      id              BIGSERIAL PRIMARY KEY,                           |
|      email           VARCHAR(255) NOT NULL UNIQUE,                    |
|      phone           VARCHAR(20),                                      |
|      password_hash   VARCHAR(255) NOT NULL,                           |
|      name            VARCHAR(255),                                     |
|      city_id         BIGINT REFERENCES cities(id),                    |
|      created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,             |
|      updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,             |
|      is_active       BOOLEAN DEFAULT TRUE                             |
|  );                                                                    |
|                                                                         |
|  CREATE INDEX idx_users_email ON users(email);                        |
|  CREATE INDEX idx_users_phone ON users(phone);                        |
|  CREATE INDEX idx_users_city ON users(city_id);                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### VENUES AND SCREENS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CREATE TABLE cities (                                                 |
|      id              BIGSERIAL PRIMARY KEY,                           |
|      name            VARCHAR(100) NOT NULL,                           |
|      state           VARCHAR(100),                                     |
|      country         VARCHAR(100) DEFAULT 'India',                    |
|      timezone        VARCHAR(50) DEFAULT 'Asia/Kolkata'               |
|  );                                                                    |
|                                                                         |
|  CREATE TABLE venues (                                                 |
|      id              BIGSERIAL PRIMARY KEY,                           |
|      city_id         BIGINT NOT NULL REFERENCES cities(id),           |
|      name            VARCHAR(255) NOT NULL,                           |
|      address         TEXT,                                             |
|      latitude        DECIMAL(10, 8),                                  |
|      longitude       DECIMAL(11, 8),                                  |
|      total_screens   INTEGER DEFAULT 0,                               |
|      facilities      JSONB,  -- parking, food court, etc.            |
|      is_active       BOOLEAN DEFAULT TRUE,                            |
|      created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP              |
|  );                                                                    |
|                                                                         |
|  CREATE INDEX idx_venues_city ON venues(city_id);                     |
|  CREATE INDEX idx_venues_location ON venues                           |
|      USING GIST (point(latitude, longitude));                        |
|                                                                         |
|  CREATE TABLE screens (                                                |
|      id              BIGSERIAL PRIMARY KEY,                           |
|      venue_id        BIGINT NOT NULL REFERENCES venues(id),           |
|      name            VARCHAR(50) NOT NULL,  -- "Screen 1", "IMAX"    |
|      screen_type     VARCHAR(50),  -- STANDARD, IMAX, 4DX, DOLBY     |
|      total_seats     INTEGER NOT NULL,                                |
|      row_count       INTEGER,                                          |
|      column_count    INTEGER,                                          |
|      is_active       BOOLEAN DEFAULT TRUE                             |
|  );                                                                    |
|                                                                         |
|  CREATE INDEX idx_screens_venue ON screens(venue_id);                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SEAT TEMPLATE (Fixed Layout Per Screen)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  -- Seat template defines the physical layout of a screen              |
|  -- This doesn't change per show                                       |
|                                                                         |
|  CREATE TABLE seat_templates (                                         |
|      id              BIGSERIAL PRIMARY KEY,                           |
|      screen_id       BIGINT NOT NULL REFERENCES screens(id),          |
|      seat_number     VARCHAR(10) NOT NULL,  -- "A1", "A2", "B1"       |
|      row_name        CHAR(2) NOT NULL,      -- "A", "B", "C"          |
|      column_number   INTEGER NOT NULL,      -- 1, 2, 3                |
|      category        VARCHAR(50) NOT NULL,  -- SILVER, GOLD, PLATINUM|
|      seat_type       VARCHAR(50),           -- REGULAR, RECLINER, COUPLE|
|      is_available    BOOLEAN DEFAULT TRUE,  -- Some seats might be blocked|
|                                                                         |
|      UNIQUE(screen_id, seat_number)                                   |
|  );                                                                    |
|                                                                         |
|  CREATE INDEX idx_seat_template_screen ON seat_templates(screen_id);  |
|                                                                         |
|  EXAMPLE DATA:                                                         |
|  +----------------------------------------------------------------+   |
|  | screen_id | seat_number | row | col | category   | type      |   |
|  |---------------------------------------------------------------|   |
|  | 1         | A1          | A   | 1   | SILVER     | REGULAR   |   |
|  | 1         | A2          | A   | 2   | SILVER     | REGULAR   |   |
|  | 1         | G1          | G   | 1   | GOLD       | RECLINER  |   |
|  | 1         | P1          | P   | 1   | PLATINUM   | RECLINER  |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### MOVIES AND SHOWS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CREATE TABLE movies (                                                 |
|      id              BIGSERIAL PRIMARY KEY,                           |
|      title           VARCHAR(255) NOT NULL,                           |
|      description     TEXT,                                             |
|      duration_mins   INTEGER NOT NULL,                                |
|      language        VARCHAR(50),                                      |
|      genre           VARCHAR(100)[],  -- Array of genres              |
|      release_date    DATE,                                             |
|      rating          DECIMAL(3, 1),   -- 8.5                          |
|      certificate     VARCHAR(10),     -- U, UA, A                     |
|      poster_url      TEXT,                                             |
|      trailer_url     TEXT,                                             |
|      cast_crew       JSONB,                                            |
|      is_active       BOOLEAN DEFAULT TRUE,                            |
|      created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP              |
|  );                                                                    |
|                                                                         |
|  CREATE INDEX idx_movies_title ON movies USING GIN(title gin_trgm_ops);|
|  CREATE INDEX idx_movies_release ON movies(release_date);             |
|  CREATE INDEX idx_movies_genre ON movies USING GIN(genre);            |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  CREATE TABLE shows (                                                  |
|      id              BIGSERIAL PRIMARY KEY,                           |
|      movie_id        BIGINT NOT NULL REFERENCES movies(id),           |
|      screen_id       BIGINT NOT NULL REFERENCES screens(id),          |
|      show_date       DATE NOT NULL,                                    |
|      start_time      TIME NOT NULL,                                   |
|      end_time        TIME NOT NULL,                                   |
|      language        VARCHAR(50),  -- Can differ from movie default   |
|      format          VARCHAR(50),  -- 2D, 3D, IMAX                    |
|      status          VARCHAR(20) DEFAULT 'ACTIVE',                    |
|      created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,             |
|                                                                         |
|      UNIQUE(screen_id, show_date, start_time)                        |
|  );                                                                    |
|                                                                         |
|  CREATE INDEX idx_shows_movie ON shows(movie_id);                     |
|  CREATE INDEX idx_shows_screen ON shows(screen_id);                   |
|  CREATE INDEX idx_shows_datetime ON shows(show_date, start_time);    |
|  CREATE INDEX idx_shows_lookup ON shows(movie_id, show_date);        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SHOW SEATS (Per-Show Seat Status) - THE CRITICAL TABLE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  -- This is where seat availability is tracked for each show           |
|  -- Created when a show is scheduled                                   |
|                                                                         |
|  CREATE TABLE show_seats (                                             |
|      id              BIGSERIAL PRIMARY KEY,                           |
|      show_id         BIGINT NOT NULL REFERENCES shows(id),            |
|      seat_template_id BIGINT NOT NULL REFERENCES seat_templates(id),  |
|      seat_number     VARCHAR(10) NOT NULL,  -- Denormalized for speed |
|      category        VARCHAR(50) NOT NULL,  -- Denormalized           |
|      price           DECIMAL(10, 2) NOT NULL,                         |
|      status          VARCHAR(20) NOT NULL DEFAULT 'AVAILABLE',        |
|                      -- AVAILABLE, LOCKED, BOOKED, BLOCKED            |
|      locked_at       TIMESTAMP,             -- When lock was acquired |
|      locked_until    TIMESTAMP,             -- Lock expiry            |
|      booking_id      BIGINT,                -- Set after confirmation |
|      version         INTEGER DEFAULT 1,     -- For optimistic locking |
|                                                                         |
|      UNIQUE(show_id, seat_number)                                     |
|  );                                                                    |
|                                                                         |
|  -- CRITICAL INDEXES for booking performance                          |
|  CREATE INDEX idx_show_seats_show ON show_seats(show_id);            |
|  CREATE INDEX idx_show_seats_status ON show_seats(show_id, status);  |
|  CREATE INDEX idx_show_seats_booking ON show_seats(booking_id);      |
|  CREATE INDEX idx_show_seats_lock_expiry                             |
|      ON show_seats(locked_until) WHERE status = 'LOCKED';            |
|                                                                         |
|  EXAMPLE DATA:                                                         |
|  +------------------------------------------------------------------+ |
|  |show_id|seat |category|price |status   |locked_until|booking_id | |
|  |----------------------------------------------------------------- | |
|  | 1001  | A1  |SILVER  |150.00|AVAILABLE| NULL       | NULL      | |
|  | 1001  | A2  |SILVER  |150.00|LOCKED   | 10:15:00   | NULL      | |
|  | 1001  | G1  |GOLD    |300.00|BOOKED   | NULL       | 5001      | |
|  +------------------------------------------------------------------+ |
|                                                                         |
+-------------------------------------------------------------------------+
```

### RESERVATIONS AND BOOKINGS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  -- Reservation: Temporary hold before payment                         |
|                                                                         |
|  CREATE TABLE reservations (                                           |
|      id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),      |
|      user_id         BIGINT NOT NULL REFERENCES users(id),            |
|      show_id         BIGINT NOT NULL REFERENCES shows(id),            |
|      seat_numbers    VARCHAR(10)[] NOT NULL,  -- ['A1', 'A2']        |
|      total_amount    DECIMAL(10, 2) NOT NULL,                         |
|      status          VARCHAR(20) DEFAULT 'PENDING',                   |
|                      -- PENDING, CONFIRMED, EXPIRED, CANCELLED        |
|      created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,             |
|      expires_at      TIMESTAMP NOT NULL,                              |
|      confirmed_at    TIMESTAMP,                                        |
|                                                                         |
|      -- Idempotency for retries                                       |
|      idempotency_key VARCHAR(255) UNIQUE                              |
|  );                                                                    |
|                                                                         |
|  CREATE INDEX idx_reservations_user ON reservations(user_id);        |
|  CREATE INDEX idx_reservations_status ON reservations(status);       |
|  CREATE INDEX idx_reservations_expiry                                |
|      ON reservations(expires_at) WHERE status = 'PENDING';           |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  -- Booking: Confirmed purchase                                        |
|                                                                         |
|  CREATE TABLE bookings (                                               |
|      id              BIGSERIAL PRIMARY KEY,                           |
|      booking_number  VARCHAR(20) UNIQUE NOT NULL,  -- BMS20240115001 |
|      reservation_id  UUID REFERENCES reservations(id),                |
|      user_id         BIGINT NOT NULL REFERENCES users(id),            |
|      show_id         BIGINT NOT NULL REFERENCES shows(id),            |
|      seat_count      INTEGER NOT NULL,                                |
|      subtotal        DECIMAL(10, 2) NOT NULL,                         |
|      convenience_fee DECIMAL(10, 2) DEFAULT 0,                        |
|      taxes           DECIMAL(10, 2) DEFAULT 0,                        |
|      discount        DECIMAL(10, 2) DEFAULT 0,                        |
|      total_amount    DECIMAL(10, 2) NOT NULL,                         |
|      status          VARCHAR(20) DEFAULT 'CONFIRMED',                 |
|                      -- CONFIRMED, CANCELLED, REFUNDED                |
|      created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,             |
|      cancelled_at    TIMESTAMP,                                        |
|      cancellation_reason TEXT                                         |
|  );                                                                    |
|                                                                         |
|  CREATE INDEX idx_bookings_user ON bookings(user_id);                |
|  CREATE INDEX idx_bookings_show ON bookings(show_id);                |
|  CREATE INDEX idx_bookings_number ON bookings(booking_number);       |
|  CREATE INDEX idx_bookings_created ON bookings(created_at);          |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  -- Booking items (seats in a booking)                                 |
|                                                                         |
|  CREATE TABLE booking_items (                                          |
|      id              BIGSERIAL PRIMARY KEY,                           |
|      booking_id      BIGINT NOT NULL REFERENCES bookings(id),         |
|      show_seat_id    BIGINT NOT NULL REFERENCES show_seats(id),       |
|      seat_number     VARCHAR(10) NOT NULL,                            |
|      category        VARCHAR(50) NOT NULL,                            |
|      price           DECIMAL(10, 2) NOT NULL                          |
|  );                                                                    |
|                                                                         |
|  CREATE INDEX idx_booking_items_booking ON booking_items(booking_id);|
|                                                                         |
+-------------------------------------------------------------------------+
```

PAYMENTS
--------

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CREATE TABLE payments (                                               |
|      id              BIGSERIAL PRIMARY KEY,                           |
|      booking_id      BIGINT REFERENCES bookings(id),                  |
|      reservation_id  UUID REFERENCES reservations(id),                |
|      user_id         BIGINT NOT NULL REFERENCES users(id),            |
|      amount          DECIMAL(10, 2) NOT NULL,                         |
|      currency        CHAR(3) DEFAULT 'INR',                           |
|      payment_method  VARCHAR(50),  -- CREDIT_CARD, UPI, WALLET       |
|      gateway         VARCHAR(50),  -- RAZORPAY, PAYU                  |
|      gateway_payment_id VARCHAR(255),                                  |
|      gateway_order_id VARCHAR(255),                                    |
|      status          VARCHAR(20) DEFAULT 'PENDING',                   |
|                      -- PENDING, SUCCESS, FAILED, REFUNDED           |
|      failure_reason  TEXT,                                             |
|      idempotency_key VARCHAR(255) UNIQUE,                             |
|      created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,             |
|      completed_at    TIMESTAMP                                        |
|  );                                                                    |
|                                                                         |
|  CREATE INDEX idx_payments_booking ON payments(booking_id);          |
|  CREATE INDEX idx_payments_reservation ON payments(reservation_id);  |
|  CREATE INDEX idx_payments_gateway_id                                |
|      ON payments(gateway_payment_id);                                 |
|  CREATE INDEX idx_payments_status ON payments(status);               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.3: INDEXING STRATEGY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CRITICAL QUERIES AND THEIR INDEXES                                   |
|                                                                         |
|  1. GET SHOWS FOR A MOVIE IN A CITY                                   |
|  ===================================                                    |
|                                                                         |
|  Query:                                                                |
|  SELECT s.*, v.name as venue_name                                     |
|  FROM shows s                                                          |
|  JOIN screens sc ON s.screen_id = sc.id                               |
|  JOIN venues v ON sc.venue_id = v.id                                  |
|  WHERE s.movie_id = ?                                                 |
|    AND v.city_id = ?                                                  |
|    AND s.show_date = ?;                                               |
|                                                                         |
|  Indexes:                                                              |
|  - idx_shows_movie (movie_id)                                         |
|  - idx_venues_city (city_id)                                          |
|  - Composite: idx_shows_movie_date (movie_id, show_date)             |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. GET SEAT AVAILABILITY FOR A SHOW                                  |
|  ====================================                                   |
|                                                                         |
|  Query:                                                                |
|  SELECT seat_number, category, price, status                         |
|  FROM show_seats                                                       |
|  WHERE show_id = ?;                                                    |
|                                                                         |
|  Index:                                                                |
|  - idx_show_seats_show (show_id) -- Covers this query                |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. CHECK SPECIFIC SEATS AVAILABILITY                                 |
|  =======================================                                |
|                                                                         |
|  Query:                                                                |
|  SELECT * FROM show_seats                                             |
|  WHERE show_id = ?                                                     |
|    AND seat_number IN ('A1', 'A2', 'A3')                             |
|    AND status = 'AVAILABLE'                                          |
|  FOR UPDATE;                                                           |
|                                                                         |
|  Index:                                                                |
|  - UNIQUE(show_id, seat_number) -- Primary lookup                    |
|  - idx_show_seats_status (show_id, status) -- Filter by status       |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  4. CLEANUP EXPIRED LOCKS                                             |
|  =========================                                              |
|                                                                         |
|  Query:                                                                |
|  UPDATE show_seats                                                     |
|  SET status = 'AVAILABLE', locked_at = NULL, locked_until = NULL     |
|  WHERE status = 'LOCKED'                                              |
|    AND locked_until < NOW();                                          |
|                                                                         |
|  Index:                                                                |
|  - Partial: idx_show_seats_lock_expiry ON (locked_until)             |
|             WHERE status = 'LOCKED'                                   |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  5. USER'S BOOKING HISTORY                                            |
|  ==========================                                             |
|                                                                         |
|  Query:                                                                |
|  SELECT b.*, m.title, s.show_date, s.start_time                      |
|  FROM bookings b                                                       |
|  JOIN shows s ON b.show_id = s.id                                    |
|  JOIN movies m ON s.movie_id = m.id                                  |
|  WHERE b.user_id = ?                                                  |
|  ORDER BY b.created_at DESC;                                         |
|                                                                         |
|  Index:                                                                |
|  - idx_bookings_user (user_id)                                       |
|  - Composite: idx_bookings_user_created (user_id, created_at DESC)  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.4: DATABASE SCALING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCALING STRATEGY                                                      |
|                                                                         |
|  1. READ REPLICAS                                                      |
|  =================                                                      |
|                                                                         |
|  Most queries are reads (browse movies, check availability).          |
|  Use read replicas for these:                                         |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Writes ---> Primary DB (Leader)                               |  |
|  |                   |                                             |  |
|  |                   | Replication                                 |  |
|  |                   v                                             |  |
|  |  Reads ---> Read Replica 1                                     |  |
|  |        ---> Read Replica 2                                     |  |
|  |        ---> Read Replica 3                                     |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  ROUTE TO PRIMARY:                                                    |
|  - Booking flow (SELECT FOR UPDATE, INSERT, UPDATE)                  |
|  - Payment processing                                                 |
|  - Anything requiring immediate consistency                          |
|                                                                         |
|  ROUTE TO REPLICA:                                                    |
|  - Movie listings                                                     |
|  - Show schedules                                                     |
|  - User profile reads                                                 |
|  - Booking history                                                    |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. SHARDING BY CITY                                                  |
|  ======================                                                 |
|                                                                         |
|  When single DB can't handle load, shard by city.                    |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  +----------+  +----------+  +----------+  +----------+      |  |
|  |  | Shard 1  |  | Shard 2  |  | Shard 3  |  | Shard 4  |      |  |
|  |  | Mumbai   |  | Delhi    |  | Bengaluru|  | Others   |      |  |
|  |  |          |  | NCR      |  |          |  |          |      |  |
|  |  +----------+  +----------+  +----------+  +----------+      |  |
|  |                                                                 |  |
|  |  Each shard contains: venues, screens, shows, bookings        |  |
|  |  for that city                                                  |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  WHY CITY?                                                             |
|  - Users typically book in one city                                  |
|  - Cross-city queries are rare                                       |
|  - Natural data locality                                             |
|                                                                         |
|  CROSS-SHARD DATA:                                                     |
|  - Users table: Replicated or in separate DB                         |
|  - Movies table: Replicated to all shards                            |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. TABLE PARTITIONING                                                |
|  ======================                                                 |
|                                                                         |
|  show_seats table grows huge. Partition by show_date:                |
|                                                                         |
|  CREATE TABLE show_seats (                                            |
|      ...                                                               |
|  ) PARTITION BY RANGE (show_date);                                    |
|                                                                         |
|  CREATE TABLE show_seats_2024_01                                      |
|      PARTITION OF show_seats                                          |
|      FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');               |
|                                                                         |
|  CREATE TABLE show_seats_2024_02                                      |
|      PARTITION OF show_seats                                          |
|      FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');               |
|                                                                         |
|  BENEFITS:                                                             |
|  - Queries for today's shows only scan today's partition            |
|  - Old partitions can be archived/dropped easily                    |
|  - Better index performance (smaller indexes per partition)         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DATABASE DESIGN - KEY TAKEAWAYS                                      |
|                                                                         |
|  CORE TABLES                                                           |
|  -----------                                                           |
|  * show_seats: The critical table for availability                   |
|  * reservations: Temporary holds with TTL                            |
|  * bookings: Confirmed purchases                                      |
|  * payments: With idempotency keys                                    |
|                                                                         |
|  INDEXING                                                              |
|  --------                                                              |
|  * Index on show_id for seat queries                                 |
|  * Partial index on locked_until for cleanup                         |
|  * Composite indexes for common queries                              |
|                                                                         |
|  SCALING                                                               |
|  -------                                                               |
|  * Read replicas for browse queries                                  |
|  * City-based sharding for large scale                               |
|  * Date partitioning for show_seats                                  |
|                                                                         |
|  INTERVIEW TIP                                                         |
|  -------------                                                         |
|  Explain the show_seats table in detail.                             |
|  Show how status transitions: AVAILABLE > LOCKED > BOOKED           |
|  Discuss version column for optimistic locking.                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 4

