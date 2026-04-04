# HOTEL / AIRLINE RESERVATION SYSTEM (BOOKING.COM STYLE)
*Complete Design: Requirements, Architecture, and Interview Guide*

A hotel reservation system allows users to search for hotels by location and dates,
view room availability, and book rooms with payment - all while preventing double-booking.
At scale, it must handle millions of concurrent searchers, thousands of simultaneous
bookings, and flash-sale traffic spikes with strong consistency for the booking path.

## SECTION 1: SCOPING THE PROBLEM WITH THE INTERVIEWER

```
+-------------------------------------------------------------------------+
|                                                                         |
|  INTERVIEWER-CANDIDATE DIALOGUE                                         |
|  (establishing scope before diving into design)                         |
|                                                                         |
|  CANDIDATE: What kind of reservation system are we designing?           |
|    A hotel-only platform like Booking.com, or multi-vertical            |
|    (hotels + flights + car rentals)?                                    |
|                                                                         |
|  INTERVIEWER: Hotel-only. Focus on the room booking flow.               |
|    Ignore flights and car rentals.                                      |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: Who are the users? Just guests, or also hotel               |
|    managers uploading inventory?                                        |
|                                                                         |
|  INTERVIEWER: Both. Guests search and book. Hotels manage               |
|    their own rooms and pricing via a portal.                            |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: For the booking flow, should I handle the full              |
|    payment integration, or can I treat payment as an external           |
|    service we call?                                                     |
|                                                                         |
|  INTERVIEWER: Treat payment as an external service. Focus on            |
|    the booking orchestration and inventory management.                  |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: What scale should I target? How many hotels                 |
|    and how much booking traffic?                                        |
|                                                                         |
|  INTERVIEWER: 500K hotels, 10M rooms. About 100K bookings/day           |
|    normally, but we should handle flash-sale spikes.                    |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: Do guests book a specific room number, or just              |
|    a room type (e.g., "double") with fungible inventory?                |
|                                                                         |
|  INTERVIEWER: Room type with fungible inventory. The guest              |
|    gets assigned a specific room at check-in, not at booking.           |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: For availability, should search results show                |
|    real-time exact availability, or is approximate OK for               |
|    search with exact check at booking time?                             |
|                                                                         |
|  INTERVIEWER: Approximate for search is fine. Exact check               |
|    must happen at booking time. Good instinct.                          |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: Should I design for overbooking? Airlines                   |
|    intentionally overbook by ~15%.                                      |
|                                                                         |
|  INTERVIEWER: Hotels generally don't overbook. Design for               |
|    zero overbooking as the default. We can discuss an optional          |
|    overbooking mode later.                                              |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: What about cancellation and refunds?                        |
|                                                                         |
|  INTERVIEWER: Yes, support cancellation with configurable               |
|    policies (free, moderate, non-refundable). Inventory must            |
|    be released back on cancellation.                                    |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  AGREED SCOPE:                                                          |
|                                                                         |
|  * Hotel-only, room-type-based (fungible) inventory                     |
|  * Guest booking flow + hotel management portal                         |
|  * Search with approximate availability, exact at booking               |
|  * Payment as external service                                          |
|  * 500K hotels, 10M rooms, 100K bookings/day + flash sales              |
|  * No overbooking (zero double-booking tolerance)                       |
|  * Cancellation with configurable refund policies                       |
|  * Idempotent booking API for retry safety                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2: UNDERSTANDING THE PROBLEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS A HOTEL RESERVATION SYSTEM?                                    |
|                                                                         |
|  User Journey:                                                          |
|  1. Search: "Hotels in Paris, Dec 20-25, 2 guests"                      |
|  2. Browse results: filter by price, rating, amenities                  |
|  3. Select hotel, view room types and availability                      |
|  4. Choose room > system places temporary hold                          |
|  5. Enter payment details > system charges card                         |
|  6. Confirm booking > receive confirmation email/SMS                    |
|  7. (Optional) Cancel booking within cancellation window                |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  WHY IS THIS HARD?                                                      |
|                                                                         |
|  1. DOUBLE-BOOKING PREVENTION (THE core challenge)                      |
|     Two users try to book the last room simultaneously.                 |
|     Only one must succeed. Zero tolerance for overbooking hotels.       |
|     (Airlines intentionally overbook ~15%; hotels generally don't.)     |
|                                                                         |
|  2. SEARCH vs BOOKING MISMATCH                                          |
|     Search is read-heavy: 100:1 search-to-book ratio.                   |
|     Booking is write-heavy with strong consistency needs.               |
|     Different patterns need different optimization strategies.          |
|                                                                         |
|  3. FLASH SALE / SURGE TRAFFIC                                          |
|     A luxury hotel posts a 90% discount > 100K users try to book.       |
|     System must handle spike without downtime or data corruption.       |
|                                                                         |
|  4. DISTRIBUTED TRANSACTIONS                                            |
|     A booking spans: inventory check, payment, confirmation, email.     |
|     If payment fails after inventory reserved, must roll back.          |
|     Saga pattern needed for distributed coordination.                   |
|                                                                         |
|  5. INVENTORY IS DATE-BASED                                             |
|     Room availability changes per date. Booking Dec 20-25 must          |
|     check and reserve inventory for EACH of the 5 nights.               |
|     Partial availability (3 of 5 nights) = no booking.                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3: REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FUNCTIONAL REQUIREMENTS:                                               |
|                                                                         |
|  1. HOTEL SEARCH                                                        |
|     * Search by location, check-in/check-out dates, number of guests    |
|     * Filter by price range, star rating, amenities, review score       |
|     * Sort by price, rating, distance, relevance                        |
|     * View hotel details: photos, descriptions, policies                |
|                                                                         |
|  2. ROOM AVAILABILITY                                                   |
|     * Check real-time room availability for a date range                |
|     * Show room types: single, double, suite, etc.                      |
|     * Display pricing per night (dynamic pricing)                       |
|     * Show cancellation policy per room type                            |
|                                                                         |
|  3. BOOKING                                                             |
|     * Reserve a room with guest details                                 |
|     * Process payment (credit card, etc.)                               |
|     * Generate booking confirmation with unique ID                      |
|     * Send confirmation via email and SMS                               |
|                                                                         |
|  4. CANCELLATION                                                        |
|     * Cancel booking within policy window                               |
|     * Full/partial refund based on cancellation policy                  |
|     * Release inventory back to available pool                          |
|     * Notify hotel of cancellation                                      |
|                                                                         |
|  5. HOTEL MANAGEMENT (Admin)                                            |
|     * Hotels manage room inventory and pricing                          |
|     * Set availability, blackout dates                                  |
|     * View bookings and revenue reports                                 |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  NON-FUNCTIONAL REQUIREMENTS:                                           |
|                                                                         |
|  * Strong consistency for bookings (no double-booking)                  |
|  * High availability for search (eventual consistency OK)               |
|  * Search latency: < 500ms p99                                          |
|  * Booking latency: < 2 seconds end-to-end                              |
|  * Handle 10K+ concurrent bookings/sec during flash sales               |
|  * 99.99% availability for search, 99.9% for booking                    |
|  * Support 500K+ hotels, 10M+ rooms globally                            |
|  * Idempotent booking API (retry-safe)                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4: KEY TERMINOLOGY

```
+-------------------------------------------------------------------------+
||                                                                        |
||  INVENTORY                                                             |
||  The pool of available rooms per type per hotel per night.             |
||  Tracked as (total, booked) for each (hotel, room_type, date).         |
||                                                                        |
||  OVERBOOKING                                                           |
||  Selling more reservations than physical rooms, betting on             |
||  no-shows. Airlines do ~15%; hotels generally avoid it.                |
||                                                                        |
||  RESERVATION                                                           |
||  A confirmed booking tying a guest to a room type for a date           |
||  range. States: HELD > CONFIRMED > CHECKED_IN > COMPLETED.             |
||                                                                        |
||  ROOM TYPE                                                             |
||  A category of rooms (single, double, suite) with fungible             |
||  inventory. Guests book a type, not a specific room number.            |
||                                                                        |
||  RATE PLAN                                                             |
||  Pricing rules for a room type: per-night cost, discounts,             |
||  minimum stay, and cancellation terms. Can vary dynamically.           |
||                                                                        |
||  CHECK-IN / CHECK-OUT                                                  |
||  Start and end dates of a stay. Booking Dec 20-25 must                 |
||  reserve inventory for each of the 5 individual nights.                |
||                                                                        |
||  BOOKING WINDOW                                                        |
||  The time range during which a hotel accepts reservations.             |
||  Typically 1-365 days ahead; pricing adjusts by lead time.             |
||                                                                        |
||  CANCELLATION POLICY                                                   |
||  Rules governing refund amounts based on cancellation timing.          |
||  Types: free, moderate, or non-refundable (discounted rate).           |
||                                                                        |
||  AVAILABILITY CALENDAR                                                 |
||  A date-indexed view of remaining rooms per type per hotel.            |
||  Checked in real-time at booking; approximate in search.               |
||                                                                        |
||  CONCURRENCY CONTROL                                                   |
||  Mechanisms (pessimistic locking, optimistic locking, queues)          |
||  to prevent double-booking when users compete for a room.              |
||                                                                        |
||  IDEMPOTENCY KEY                                                       |
||  A client-generated unique token sent with each booking                |
||  request. Prevents duplicate charges on retries or double-clicks.      |
||                                                                        |
+-------------------------------------------------------------------------+
```

## SECTION 5: BACK-OF-ENVELOPE ESTIMATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCALE ESTIMATES:                                                       |
|                                                                         |
|  Hotels: 500,000 hotels on the platform                                 |
|  Rooms per hotel: ~20 avg > 10,000,000 rooms total                      |
|  Room types per hotel: ~5 avg                                           |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  SEARCH TRAFFIC (QPS funnel):                                           |
|                                                                         |
|  DAU: 5M users searching                                                |
|  Searches per user per session: ~10                                     |
|  Total searches/day: 50M                                                |
|                                                                         |
|  Average search QPS:                                                    |
|    50,000,000 / 86,400 = ~580 QPS                                       |
|                                                                         |
|  Peak QPS (3x average):                                                 |
|    580 * 3 = ~1,800 QPS                                                 |
|                                                                         |
|  Hotel detail page views:                                               |
|    ~20% of searches click a hotel = 10M views/day                       |
|    10,000,000 / 86,400 = ~115 QPS avg, ~350 QPS peak                    |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  BOOKING TRAFFIC (QPS funnel):                                          |
|                                                                         |
|  View-to-book conversion: ~1% of detail page views book                 |
|  Bookings/day: 10M * 0.01 = 100,000 bookings/day                        |
|                                                                         |
|  Average booking QPS:                                                   |
|    100,000 / 86,400 = ~1.2 QPS                                          |
|                                                                         |
|  Peak booking QPS (flash sale, 100x):                                   |
|    1.2 * 100 = ~120 QPS                                                 |
|                                                                         |
|  Read-to-write ratio:                                                   |
|    1,800 (search peak) / 120 (booking peak) ~ 15:1                      |
|    Overall including detail views: ~100:1                               |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  STORAGE:                                                               |
|                                                                         |
|  Hotel metadata:                                                        |
|    500K hotels * 10 KB each = ~5 GB                                     |
|    (easily fits in memory/cache)                                        |
|                                                                         |
|  Room inventory rows:                                                   |
|    500K hotels * 5 room_types * 365 days = 912.5M rows                  |
|    Each row ~ 50 bytes (hotel_id, room_type, date, total, booked)       |
|    912.5M * 50 B = ~45 GB/year                                          |
|                                                                         |
|  Booking records:                                                       |
|    100K/day * 1 KB * 365 = ~36 GB/year                                  |
|                                                                         |
|  Total active data: ~90 GB                                              |
|  With indexes + replicas (3x): ~270 GB                                  |
|  (manageable on a sharded PostgreSQL cluster)                           |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  NODE COUNT DERIVATION:                                                 |
|                                                                         |
|  Booking write path:                                                    |
|    Peak 120 TPS; PostgreSQL handles 5K-10K TPS per node                 |
|    1-2 DB nodes handle booking writes (+ replicas)                      |
|                                                                         |
|  Search read path:                                                      |
|    Peak 1,800 QPS; single ES node handles ~500 QPS                      |
|    Need ~4 ES data nodes (+ replicas for HA)                            |
|                                                                         |
|  Application servers:                                                   |
|    Assume 200 req/sec per app server                                    |
|    1,800 (search) + 350 (detail) + 120 (booking) ~ 2,300 peak           |
|    2,300 / 200 = ~12 app servers (+ headroom = 16)                      |
|                                                                         |
|  KEY INSIGHT:                                                           |
|  The data volume is not extreme. The challenge is CONCURRENCY           |
|  and CONSISTENCY, not raw storage or throughput.                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6: API DESIGN

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REST API ENDPOINTS                                                     |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  1. SEARCH APIs                                                         |
|                                                                         |
|  +--------+---------------------------+----------------------------+    |
|  | Method | Path                      | Description                |    |
|  +--------+---------------------------+----------------------------+    |
|  | GET    | /v1/hotels/search         | Search hotels by location, |    |
|  |        |   ?lat=48.85&lng=2.35     |   dates, filters.          |    |
|  |        |   &check_in=2024-12-20    |   Returns paginated list.  |    |
|  |        |   &check_out=2024-12-25   |                            |    |
|  |        |   &guests=2               |                            |    |
|  |        |   &min_price=100          |                            |    |
|  |        |   &max_price=500          |                            |    |
|  |        |   &cursor=abc123          |                            |    |
|  +--------+---------------------------+----------------------------+    |
|  | GET    | /v1/hotels/{hotel_id}     | Hotel detail page: photos, |    |
|  |        |                           |   room types, reviews.     |    |
|  +--------+---------------------------+----------------------------+    |
|  | GET    | /v1/hotels/{hotel_id}     | Room availability + prices |    |
|  |        |   /rooms                  |   for a date range.        |    |
|  |        |   ?check_in=2024-12-20    |                            |    |
|  |        |   &check_out=2024-12-25   |                            |    |
|  +--------+---------------------------+----------------------------+    |
|                                                                         |
|  Search response example:                                               |
|  {                                                                      |
|    "hotels": [                                                          |
|      {                                                                  |
|        "hotel_id": "h_12345",                                           |
|        "name": "Grand Hyatt Paris",                                     |
|        "star_rating": 4,                                                |
|        "avg_review": 8.7,                                               |
|        "price_per_night": 320,                                          |
|        "thumbnail_url": "https://cdn.../thumb.jpg",                     |
|        "distance_km": 1.2,                                              |
|        "available_rooms": 3                                             |
|      }                                                                  |
|    ],                                                                   |
|    "next_cursor": "def456",                                             |
|    "total_results": 142                                                 |
|  }                                                                      |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  2. BOOKING APIs                                                        |
|                                                                         |
|  +--------+---------------------------+----------------------------+    |
|  | Method | Path                      | Description                |    |
|  +--------+---------------------------+----------------------------+    |
|  | POST   | /v1/reservations/hold     | Place a 10-min hold on a   |    |
|  |        |                           |   room. Returns hold_id.   |    |
|  +--------+---------------------------+----------------------------+    |
|  | POST   | /v1/reservations/confirm  | Confirm booking after      |    |
|  |        |                           |   payment. Finalizes hold. |    |
|  +--------+---------------------------+----------------------------+    |
|  | DELETE | /v1/reservations/{id}     | Cancel a confirmed booking |    |
|  |        |                           |   (subject to policy).     |    |
|  +--------+---------------------------+----------------------------+    |
|  | GET    | /v1/reservations/{id}     | Get booking details.       |    |
|  +--------+---------------------------+----------------------------+    |
|  | GET    | /v1/users/{user_id}       | User's booking history.    |    |
|  |        |   /reservations           |                            |    |
|  +--------+---------------------------+----------------------------+    |
|                                                                         |
|  Hold request body:                                                     |
|  {                                                                      |
|    "hotel_id": "h_12345",                                               |
|    "room_type": "double",                                               |
|    "check_in": "2024-12-20",                                            |
|    "check_out": "2024-12-25",                                           |
|    "guest_count": 2,                                                    |
|    "idempotency_key": "cli_uuid_abc123"                                 |
|  }                                                                      |
|                                                                         |
|  Hold response:                                                         |
|  {                                                                      |
|    "hold_id": "hold_789xyz",                                            |
|    "status": "HELD",                                                    |
|    "expires_at": "2024-12-19T14:30:00Z",                                |
|    "price_per_night": 320,                                              |
|    "total_price": 1600,                                                 |
|    "cancellation_policy": "free_cancel_24h"                             |
|  }                                                                      |
|                                                                         |
|  Confirm request body:                                                  |
|  {                                                                      |
|    "hold_id": "hold_789xyz",                                            |
|    "payment_token": "tok_stripe_abc",                                   |
|    "guest_name": "Jane Doe",                                            |
|    "guest_email": "jane@example.com",                                   |
|    "idempotency_key": "cli_uuid_def456"                                 |
|  }                                                                      |
|                                                                         |
|  IDEMPOTENCY NOTE: Both /hold and /confirm accept an                    |
|  idempotency_key. If the same key is sent again, the server             |
|  returns the original response without re-processing.                   |
|  Prevents double-booking on retries or network timeouts.                |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  3. HOTEL MANAGEMENT APIs                                               |
|                                                                         |
|  +--------+---------------------------+----------------------------+    |
|  | Method | Path                      | Description                |    |
|  +--------+---------------------------+----------------------------+    |
|  | PUT    | /v1/hotels/{hotel_id}     | Update room availability   |    |
|  |        |   /inventory              |   and pricing.             |    |
|  +--------+---------------------------+----------------------------+    |
|  | GET    | /v1/hotels/{hotel_id}     | Hotel's booking dashboard. |    |
|  |        |   /bookings               |                            |    |
|  +--------+---------------------------+----------------------------+    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7: DATABASE SCHEMA WITH SAMPLE DATA

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TABLE: hotels                                                          |
|                                                                         |
|  +---------------+--------------+----------------------------------+    |
|  | Column        | Type         | Description                      |    |
|  +---------------+--------------+----------------------------------+    |
|  | hotel_id      | VARCHAR (PK) | Unique hotel identifier          |    |
|  | name          | VARCHAR(255) | Hotel display name               |    |
|  | city          | VARCHAR(100) | City for search filtering        |    |
|  | latitude      | DECIMAL(9,6) | GPS latitude                     |    |
|  | longitude     | DECIMAL(9,6) | GPS longitude                    |    |
|  | star_rating   | SMALLINT     | 1-5 star rating                  |    |
|  | description   | TEXT         | Hotel description                |    |
|  | created_at    | TIMESTAMP    | Row creation time                |    |
|  +---------------+--------------+----------------------------------+    |
|                                                                         |
|  Sample rows:                                                           |
|  +--------+-------------------+-------+----------+-----------+-----+    |
|  | id     | name              | city  | lat      | lng       | star|    |
|  +--------+-------------------+-------+----------+-----------+-----+    |
|  | h_001  | Grand Hyatt Paris | Paris | 48.8720  | 2.3280    | 4   |    |
|  | h_002  | Hilton NYC        | NYC   | 40.7614  | -73.9776  | 4   |    |
|  | h_003  | Budget Inn Tokyo  | Tokyo | 35.6762  | 139.6503  | 2   |    |
|  +--------+-------------------+-------+----------+-----------+-----+    |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  TABLE: room_types                                                      |
|                                                                         |
|  +---------------+--------------+----------------------------------+    |
|  | Column        | Type         | Description                      |    |
|  +---------------+--------------+----------------------------------+    |
|  | room_type_id  | VARCHAR (PK) | Unique room type ID              |    |
|  | hotel_id      | VARCHAR (FK) | Parent hotel                     |    |
|  | name          | VARCHAR(50)  | "single", "double", "suite"      |    |
|  | max_occupancy | SMALLINT     | Max guests for this room type    |    |
|  | base_price    | INT          | Price in cents (avoids floats)   |    |
|  | amenities     | TEXT[]       | ["wifi", "pool", "minibar"]      |    |
|  | cancel_policy | VARCHAR(30)  | "free_24h", "moderate", "strict" |    |
|  +---------------+--------------+----------------------------------+    |
|                                                                         |
|  Sample rows:                                                           |
|  +--------+-------+----------+-----+---------+--------------------+     |
|  | rt_id  | hotel | name     | max | base_$  | cancel_policy      |     |
|  +--------+-------+----------+-----+---------+--------------------+     |
|  | rt_101 | h_001 | single   | 1   | 18000   | free_24h           |     |
|  | rt_102 | h_001 | double   | 2   | 32000   | free_24h           |     |
|  | rt_103 | h_001 | suite    | 4   | 80000   | moderate           |     |
|  | rt_201 | h_002 | double   | 2   | 25000   | strict             |     |
|  +--------+-------+----------+-----+---------+--------------------+     |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  TABLE: room_inventory (THE CRITICAL TABLE)                             |
|                                                                         |
|  +---------------+--------------+----------------------------------+    |
|  | Column        | Type         | Description                      |    |
|  +---------------+--------------+----------------------------------+    |
|  | hotel_id      | VARCHAR (PK) | Composite PK part 1              |    |
|  | room_type_id  | VARCHAR (PK) | Composite PK part 2              |    |
|  | date          | DATE (PK)    | Composite PK part 3              |    |
|  | total_rooms   | SMALLINT     | Total rooms of this type         |    |
|  | booked        | SMALLINT     | Currently booked count           |    |
|  | price_cents   | INT          | Price for this specific night    |    |
|  | version       | INT          | Optimistic lock version          |    |
|  +---------------+--------------+----------------------------------+    |
|                                                                         |
|  PK: (hotel_id, room_type_id, date)                                     |
|  CHECK: booked <= total_rooms                                           |
|  CHECK: booked >= 0                                                     |
|                                                                         |
|  Sample rows:                                                           |
|  +-------+--------+------------+-------+--------+---------+-----+       |
|  | hotel | rt_id  | date       | total | booked | price_$ | ver |       |
|  +-------+--------+------------+-------+--------+---------+-----+       |
|  | h_001 | rt_102 | 2024-12-20 |  50   |   48   |  32000  |  12 |       |
|  | h_001 | rt_102 | 2024-12-21 |  50   |   49   |  35000  |   8 |       |
|  | h_001 | rt_102 | 2024-12-22 |  50   |   50   |  38000  |  15 |       |
|  | h_001 | rt_102 | 2024-12-23 |  50   |   47   |  32000  |   6 |       |
|  | h_001 | rt_102 | 2024-12-24 |  50   |   45   |  40000  |   9 |       |
|  | h_001 | rt_103 | 2024-12-20 |  10   |   10   |  80000  |   3 |       |
|  +-------+--------+------------+-------+--------+---------+-----+       |
|                                                                         |
|  Available rooms = total_rooms - booked                                 |
|  Dec 22: 50 - 50 = 0 (SOLD OUT)                                         |
|  Dec 20: 50 - 48 = 2 rooms left                                         |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  TABLE: reservations                                                    |
|                                                                         |
|  +------------------+--------------+-------------------------------+    |
|  | Column           | Type         | Description                   |    |
|  +------------------+--------------+-------------------------------+    |
|  | reservation_id   | VARCHAR (PK) | Unique booking ID             |    |
|  | hotel_id         | VARCHAR (FK) | Hotel reference                |   |
|  | room_type_id     | VARCHAR (FK) | Room type reference            |   |
|  | guest_id         | VARCHAR (FK) | Guest user reference           |   |
|  | check_in         | DATE         | Check-in date                 |    |
|  | check_out        | DATE         | Check-out date                |    |
|  | status           | VARCHAR(20)  | HELD/CONFIRMED/CANCELLED/etc  |    |
|  | total_price      | INT          | Total price in cents          |    |
|  | idempotency_key  | VARCHAR (UQ) | Client dedup key              |    |
|  | hold_expires_at  | TIMESTAMP    | When hold auto-expires        |    |
|  | created_at       | TIMESTAMP    | Booking creation time         |    |
|  | updated_at       | TIMESTAMP    | Last status change            |    |
|  +------------------+--------------+-------------------------------+    |
|                                                                         |
|  UNIQUE INDEX on idempotency_key (dedup safety net)                     |
|  INDEX on (guest_id, created_at) for "my bookings"                      |
|  INDEX on (hotel_id, check_in) for hotel dashboard                      |
|  INDEX on (status, hold_expires_at) for expired-hold cleanup            |
|                                                                         |
|  WHY THESE INDEXES?                                                     |
|  * idempotency_key UNIQUE: prevents duplicate bookings on retry.        |
|    Without it, a network timeout + retry could double-book.             |
|  * (guest_id, created_at): powers "My Reservations" page.               |
|    Covering index avoids table scan for user history.                   |
|  * (status, hold_expires_at): the cleanup job that releases             |
|    expired holds queries WHERE status='HELD' AND                        |
|    hold_expires_at < NOW(). This index makes it fast.                   |
|                                                                         |
|  Sample rows:                                                           |
|  +----------+-------+--------+------+------------+------------+         |
|  | res_id   | hotel | rt_id  | guest| check_in   | status     |         |
|  +----------+-------+--------+------+------------+------------+         |
|  | res_5001 | h_001 | rt_102 | u_42 | 2024-12-20 | CONFIRMED  |         |
|  | res_5002 | h_002 | rt_201 | u_77 | 2024-12-22 | HELD       |         |
|  | res_5003 | h_001 | rt_103 | u_15 | 2024-12-20 | CANCELLED  |         |
|  +----------+-------+--------+------+------------+------------+         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8: HIGH-LEVEL ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HOTEL RESERVATION ARCHITECTURE                                         |
|                                                                         |
|  +--------+    +-----------+                                            |
|  | Mobile  | -> | API       |                                           |
|  | Web App |    | Gateway   |                                           |
|  +--------+    | (Auth,    |                                            |
|                | Rate Limit|                                            |
|                +-----+-----+                                            |
|                      |                                                  |
|        +-------------+------------------+------------------+            |
|        |             |                  |                  |            |
|        v             v                  v                  v            |
|  +-----------+ +-----------+   +-------------+   +-----------+          |
|  | Search    | | Hotel     |   | Availability|   | Booking   |          |
|  | Service   | | Service   |   | Service     |   | Service   |          |
|  | (ES +     | | (details, |   | (inventory, |   | (reserve, |          |
|  |  geo)     | |  photos,  |   |  check,     |   |  confirm, |          |
|  |           | |  reviews) |   |  hold)      |   |  cancel)  |          |
|  +-----+-----+ +-----+-----+   +------+------+   +-----+-----+          |
|        |             |                |                  |              |
|        v             v                v                  v              |
|  +-----------+ +-----------+   +-------------+   +-----------+          |
|  | Elastic-  | | Hotel DB  |   | Inventory   |   | Booking   |          |
|  | search    | | (Postgres)|   | DB          |   | DB        |          |
|  | Cluster   | +-----------+   | (Postgres)  |   | (Postgres)|          |
|  +-----------+                 +-------------+   +-----------+          |
|                                                        |                |
|                                        +---------------+-------+        |
|                                        |               |       |        |
|                                        v               v       v        |
|                                  +-----------+  +--------+ +---------+  |
|                                  | Payment   |  | Notif. | | Hotel   |  |
|                                  | Service   |  | Service| | Mgmt    |  |
|                                  | (Stripe)  |  | (email,| | Service |  |
|                                  +-----------+  |  SMS)  | +---------+  |
|                                                 +--------+              |
|                                                                         |
|  WHY SEPARATE AVAILABILITY + BOOKING DATABASES?                         |
|  Inventory DB is the hottest table (checked on every booking            |
|  attempt). Isolating it prevents booking metadata queries from          |
|  competing for the same DB connections and locks. Both can be           |
|  on the same PostgreSQL cluster sharded by hotel_id so that             |
|  single-hotel transactions remain single-shard.                         |
|                                                                         |
|  WHY ELASTICSEARCH FOR SEARCH?                                          |
|  Combines geo_distance + full-text + faceted filters (price,            |
|  rating, amenities) in a single query. SQL cannot do geo +              |
|  text + range + sort efficiently at this scale. ES also                 |
|  supports search_after cursor-based pagination natively.                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 9: HOTEL SEARCH - GEO + FULL-TEXT + RANKING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  GEO-BASED SEARCH:                                                      |
|                                                                         |
|  User searches: "Hotels near Times Square, NYC"                         |
|  We need: all hotels within N km of a point / within a bounding box     |
|                                                                         |
|  OPTION 1: GEOHASH                                                      |
|  * Encode (lat, lng) into a string: "dr5ru7" (precision level)          |
|  * Nearby locations share a common geohash prefix                       |
|  * Query: WHERE geohash LIKE 'dr5ru%'                                   |
|  * Fast prefix-based index lookup                                       |
|  * Edge case: neighbors at geohash boundary may not share prefix        |
|    > query current cell + 8 neighboring cells                           |
|                                                                         |
|  +------+------+------+                                                 |
|  | dr5rt| dr5ru| dr5rv|                                                 |
|  +------+------+------+                                                 |
|  | dr5rq| dr5rr| dr5rs|  < user is in dr5rr                             |
|  +------+------+------+    query dr5rr + all 8 neighbors                |
|  | dr5rm| dr5rn| dr5rp|                                                 |
|  +------+------+------+                                                 |
|                                                                         |
|  OPTION 2: QUADTREE                                                     |
|  * Recursively divide map into 4 quadrants                              |
|  * Split until each cell has < N hotels                                 |
|  * Dense areas (NYC) have deeper tree, sparse areas are coarse          |
|  * Good for in-memory spatial index                                     |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  ELASTICSEARCH FOR FULL-TEXT + FILTERS:                                 |
|                                                                         |
|  Hotel document indexed in Elasticsearch:                               |
|  {                                                                      |
|    "hotel_id": "h_12345",                                               |
|    "name": "Grand Hyatt NYC",                                           |
|    "location": { "lat": 40.7549, "lon": -73.9764 },                     |
|    "city": "New York",                                                  |
|    "star_rating": 4,                                                    |
|    "amenities": ["pool", "wifi", "gym", "spa"],                         |
|    "avg_review_score": 8.7,                                             |
|    "price_range": { "min": 250, "max": 800 },                           |
|    "room_types": ["single", "double", "suite"]                          |
|  }                                                                      |
|                                                                         |
|  ES query combines:                                                     |
|  * geo_distance filter (within 5km of point)                            |
|  * range filter (price, star rating)                                    |
|  * term filter (amenities, room type)                                   |
|  * full-text match (hotel name, description)                            |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  SEARCH RANKING:                                                        |
|                                                                         |
|  +-------------------+------+-----------------------------------------+ |
|  | Factor            |Weight| Notes                                   | |
|  +-------------------+------+-----------------------------------------+ |
|  | Price match       | 25%  | Closer to user's budget = higher        | |
|  | Review score      | 20%  | Average guest rating                    | |
|  | Distance          | 15%  | Proximity to searched location          | |
|  | Relevance         | 15%  | Text match on name/description          | |
|  | Promoted/Ads      | 10%  | Hotels paying for placement             | |
|  | Conversion rate   | 10%  | Historical booking rate for listing     | |
|  | Recency           | 5%   | Recently updated listings               | |
|  +-------------------+------+-----------------------------------------+ |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CACHING SEARCH RESULTS:                                                |
|                                                                         |
|  +----------+    +-----------+    +---------------+                     |
|  | Search   | -> | Redis     | -> | Elasticsearch |                     |
|  | Request  |    | Cache     |    | (cache miss)  |                     |
|  +----------+    | TTL: 60s  |    +---------------+                     |
|                  +-----------+                                          |
|                                                                         |
|  WHY REDIS CACHE? Same search (city + dates) repeated by thousands      |
|  of users. 60s TTL avoids hitting ES for every request. Sub-ms reads.   |
|  WHY ELASTICSEARCH? Full-text (hotel names) + geo (location radius)     |
|  + facets (price range, amenities, rating) in one query. Combined       |
|  text+geo+filter queries impossible at scale with SQL alone.            |
|                                                                         |
|  Cache key: hash(location, dates, filters, sort, page)                  |
|  TTL: 60 seconds (availability can change, but search results are       |
|        approximate - real availability checked at booking time)         |
|                                                                         |
|  Pagination: use search_after (cursor-based) instead of offset          |
|  for consistent deep pagination results.                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 10: DEEP DIVE - DOUBLE-BOOKING PREVENTION (3 APPROACHES COMPARED)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THIS IS THE CORE INTERVIEW TOPIC.                                      |
|                                                                         |
|  The "hard problem" in hotel reservation is preventing two users        |
|  from booking the last room simultaneously. We compare three            |
|  approaches, showing how the interviewer might push back on each.       |
|                                                                         |
|  =================================================================      |
|                                                                         |
|  THE RACE CONDITION:                                                    |
|                                                                         |
|  Last room available for Dec 20. Two users book simultaneously:         |
|                                                                         |
|  Time    User A                    User B                               |
|  ----    ------                    ------                               |
|  T1      Read: booked=49, total=50                                      |
|  T2                                Read: booked=49, total=50            |
|  T3      49 < 50? Yes > book!                                           |
|  T4                                49 < 50? Yes > book!                 |
|  T5      UPDATE SET booked=50      UPDATE SET booked=50                 |
|  T6      Confirmed                 Confirmed  < DOUBLE BOOKED!          |
|                                                                         |
|  Both users see availability, both succeed > OVERBOOKING.               |
|                                                                         |
|  =================================================================      |
|                                                                         |
|  APPROACH 1: PESSIMISTIC LOCKING (SELECT ... FOR UPDATE)                |
|                                                                         |
|  BEGIN TRANSACTION;                                                     |
|    SELECT booked, total_rooms FROM room_inventory                       |
|    WHERE hotel_id = 'h_001'                                             |
|      AND room_type_id = 'rt_102'                                        |
|      AND date BETWEEN '2024-12-20' AND '2024-12-24'                     |
|    FOR UPDATE;  -- LOCKS these rows                                     |
|                                                                         |
|    -- Check: all dates have (total_rooms - booked) >= 1                 |
|    -- If yes:                                                           |
|    UPDATE room_inventory SET booked = booked + 1                        |
|    WHERE hotel_id = 'h_001'                                             |
|      AND room_type_id = 'rt_102'                                        |
|      AND date BETWEEN '2024-12-20' AND '2024-12-24';                    |
|  COMMIT;                                                                |
|                                                                         |
|  Timeline with pessimistic locking:                                     |
|                                                                         |
|  Time    User A                    User B                               |
|  ----    ------                    ------                               |
|  T1      SELECT ... FOR UPDATE                                          |
|          (acquires row lock)                                            |
|  T2                                SELECT ... FOR UPDATE                |
|                                    (BLOCKED - waiting for lock)         |
|  T3      booked=49 < 50 > UPDATE                                        |
|  T4      COMMIT (releases lock)                                         |
|  T5                                (lock acquired)                      |
|  T6                                booked=50, total=50                  |
|  T7                                50 < 50? NO > REJECT                 |
|                                                                         |
|  +------------------+-----------------------------------------+         |
|  | Pros             | Cons                                    |         |
|  +------------------+-----------------------------------------+         |
|  | Simple to code   | Locks held for entire transaction       |         |
|  | Guaranteed safe  | High contention on popular hotels       |         |
|  | Easy to reason   | Deadlock risk if lock order varies      |         |
|  | No retry logic   | Throughput drops under concurrency      |         |
|  +------------------+-----------------------------------------+         |
|                                                                         |
|  INTERVIEWER PUSHBACK: "What happens during a flash sale when           |
|  1000 users try to book the same hotel? Won't they all queue            |
|  up waiting for locks?"                                                 |
|                                                                         |
|  YES. Pessimistic locking serializes all requests for the same          |
|  rows. Under high contention, most requests are blocked waiting.        |
|  P99 latency spikes. This is why we need a better approach for          |
|  high-concurrency scenarios.                                            |
|                                                                         |
|  BEST FOR: Low-to-moderate concurrency, simple implementation.          |
|                                                                         |
|  =================================================================      |
|                                                                         |
|  APPROACH 2: OPTIMISTIC LOCKING (version column)                        |
|                                                                         |
|  Table adds: version INT (incremented on every update)                  |
|                                                                         |
|  Step 1: Read (no lock)                                                 |
|    SELECT booked, total_rooms, version FROM room_inventory              |
|    WHERE hotel_id = 'h_001'                                             |
|      AND room_type_id = 'rt_102'                                        |
|      AND date = '2024-12-20';                                           |
|    -- booked=48, total=50, version=12                                   |
|                                                                         |
|  Step 2: Update with version check                                      |
|    UPDATE room_inventory                                                |
|    SET booked = 49, version = 13                                        |
|    WHERE hotel_id = 'h_001'                                             |
|      AND room_type_id = 'rt_102'                                        |
|      AND date = '2024-12-20'                                            |
|      AND version = 12;                                                  |
|    -- Rows affected = 1? Success!                                       |
|    -- Rows affected = 0? Someone else updated > RETRY                   |
|                                                                         |
|  Timeline with optimistic locking:                                      |
|                                                                         |
|  Time    User A                    User B                               |
|  ----    ------                    ------                               |
|  T1      Read: booked=49, ver=12                                        |
|  T2                                Read: booked=49, ver=12              |
|  T3      UPDATE ... WHERE ver=12                                        |
|          (1 row affected > success)                                     |
|  T4                                UPDATE ... WHERE ver=12              |
|                                    (0 rows > CONFLICT > retry)          |
|  T5                                Re-read: booked=50, ver=13           |
|  T6                                50 < 50? NO > REJECT                 |
|                                                                         |
|  +------------------+-----------------------------------------+         |
|  | Pros             | Cons                                    |         |
|  +------------------+-----------------------------------------+         |
|  | No locks held    | Retry storms under high contention      |         |
|  | Higher throughput| Multi-date bookings need ALL dates      |         |
|  | No deadlock risk |   to succeed (any conflict = retry all) |         |
|  | Simple reads     | App must implement retry logic          |         |
|  +------------------+-----------------------------------------+         |
|                                                                         |
|  INTERVIEWER PUSHBACK: "During a flash sale, won't optimistic           |
|  locking cause a retry storm? 1000 users, 1 room - 999 fail             |
|  on first try, retry, fail again, cascading retries..."                 |
|                                                                         |
|  YES. This is the "thundering herd" problem. Retries amplify            |
|  load under extreme contention. Mitigations:                            |
|  * Exponential backoff + jitter on retries                              |
|  * Max retry limit (3 attempts, then reject)                            |
|  * For flash-sale scenarios, switch to queue serialization              |
|                                                                         |
|  BEST FOR: Moderate concurrency, most hotel booking scenarios.          |
|                                                                         |
|  =================================================================      |
|                                                                         |
|  APPROACH 3: ATOMIC DB CONSTRAINT (CHECK + single statement)            |
|                                                                         |
|  UPDATE room_inventory                                                  |
|  SET booked = booked + 1                                                |
|  WHERE hotel_id = 'h_001'                                               |
|    AND room_type_id = 'rt_102'                                          |
|    AND date BETWEEN '2024-12-20' AND '2024-12-24'                       |
|    AND booked < total_rooms;                                            |
|                                                                         |
|  -- If rows_updated = 5 (all 5 nights) > success!                       |
|  -- If rows_updated < 5 > at least one night full > ROLLBACK            |
|                                                                         |
|  The database itself enforces the constraint. No application-           |
|  level read-then-check needed. Combined with a CHECK constraint:        |
|    ALTER TABLE room_inventory                                           |
|      ADD CONSTRAINT no_overbook CHECK (booked <= total_rooms);          |
|                                                                         |
|  Even if the WHERE clause somehow fails, the CHECK constraint           |
|  acts as a database-level safety net preventing booked > total.         |
|                                                                         |
|  +------------------+-----------------------------------------+         |
|  | Pros             | Cons                                    |         |
|  +------------------+-----------------------------------------+         |
|  | Single SQL stmt  | Must ROLLBACK partial updates if not    |         |
|  | No app retry     |   all dates succeed (wrap in txn)       |         |
|  | DB enforces rule | Slightly less flexible than version     |         |
|  | Very fast        |   checks for complex business logic     |         |
|  +------------------+-----------------------------------------+         |
|                                                                         |
|  INTERVIEWER PUSHBACK: "What if only 3 of 5 nights succeed?             |
|  You've now incremented booked for 3 dates but not the other 2."        |
|                                                                         |
|  Wrap in a transaction. Check rows_updated = expected_nights.           |
|  If not, ROLLBACK. The CHECK constraint also prevents booked            |
|  from ever exceeding total_rooms even without the WHERE clause.         |
|                                                                         |
|  BEGIN;                                                                 |
|    UPDATE room_inventory SET booked = booked + 1                        |
|    WHERE hotel_id = 'h_001' AND room_type_id = 'rt_102'                 |
|      AND date BETWEEN '2024-12-20' AND '2024-12-24'                     |
|      AND booked < total_rooms;                                          |
|    -- Check: rows_updated = 5?                                          |
|    -- If yes: COMMIT                                                    |
|    -- If no:  ROLLBACK (all-or-nothing)                                 |
|  END;                                                                   |
|                                                                         |
|  BEST FOR: The recommended default approach. Simple, fast,              |
|  leverages DB-level guarantees.                                         |
|                                                                         |
|  =================================================================      |
|                                                                         |
|  COMPARISON SUMMARY:                                                    |
|                                                                         |
|  +------------------+----------+-----------+--------+---------+         |
|  | Approach         | Safety   | Throughput| Retry? | Complex |         |
|  +------------------+----------+-----------+--------+---------+         |
|  | Pessimistic Lock | Strong   | Low       | No     | Low     |         |
|  | Optimistic Lock  | Strong   | Medium    | Yes    | Medium  |         |
|  | Atomic + CHECK   | Strong   | High      | No*    | Low     |         |
|  +------------------+----------+-----------+--------+---------+         |
|  * No app-level retry needed; DB handles atomically.                    |
|                                                                         |
|  RECOMMENDED STRATEGY:                                                  |
|  * Normal flow: Atomic DB constraint (Approach 3)                       |
|  * Flash sale: Add queue serialization in front                         |
|    (Kafka partition per hotel > single consumer > DB write)             |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  OPTIONAL: REDIS FAST-PATH FOR FLASH SALES                              |
|                                                                         |
|  Key: availability:{hotel_id}:{room_type}:{date}                        |
|  Value: remaining room count                                            |
|                                                                         |
|  MULTI                                                                  |
|    DECR availability:h_001:rt_102:2024-12-20                            |
|    DECR availability:h_001:rt_102:2024-12-21                            |
|    ... (all dates)                                                      |
|  EXEC                                                                   |
|                                                                         |
|  If any result < 0: INCR them all back (rollback in Redis).             |
|  If all >= 0: proceed to DB write for durable confirmation.             |
|                                                                         |
|  WHY REDIS FAST-PATH? During a flash sale, 10K requests hit             |
|  simultaneously. Redis DECR at ~100K ops/sec pre-filters most           |
|  requests before they touch the DB. Only successful Redis holds         |
|  proceed to the slower DB write. Acts as a fast admission gate.         |
|                                                                         |
|  RISK: Redis is not durable. If Redis crashes after DECR but            |
|  before DB write, we've lost a room's availability count.               |
|  Mitigation: periodic reconciliation Redis vs DB (every 60s).           |
|  DB is always the source of truth.                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 11: BOOKING FLOW - HOLD > PAY > CONFIRM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BOOKING STATE MACHINE:                                                 |
|                                                                         |
|  +----------+    +---------+    +-----------+    +-----------+          |
|  | AVAILABLE| -> | HELD    | -> | PAYMENT   | -> | CONFIRMED |          |
|  |          |    | (temp,  |    | PROCESSING|    |           |          |
|  +----------+    | 10 min  |    +-----------+    +-----------+          |
|       ^          | TTL)    |         |                 |                |
|       |          +----+----+         |                 v                |
|       |               |              |           +-----------+          |
|       |               v              v           | CANCELLED |          |
|       |          +---------+    +---------+      +-----------+          |
|       +--------- | EXPIRED |    | PAYMENT |                             |
|       (release)  | (TTL    |    | FAILED  |                             |
|                  |  hit)   |    +---------+                             |
|                  +---------+         |                                  |
|                                      v                                  |
|                                 (release inventory)                     |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  DETAILED FLOW:                                                         |
|                                                                         |
|  Step 1: User selects room                                              |
|  +--------+                    +------------------+                     |
|  | User   | -- POST /hold --> | Availability     |                      |
|  | clicks |    {hotel, room,  | Service          |                      |
|  | "Book" |     dates,        | - Check avail    |                      |
|  +--------+     idempotency_  | - Decrement      |                      |
|                 key}          |   inventory       |                     |
|                               | - Create hold     |                     |
|                               |   with TTL=10min  |                     |
|                               +------------------+                      |
|                                                                         |
|  Step 2: User enters payment details (within 10 min hold)               |
|  +--------+                    +------------------+                     |
|  | User   | -- POST /confirm->| Booking Service  |                      |
|  | submits|    {hold_id,      | - Verify hold    |                      |
|  | payment|     payment_info, |   still active   |                      |
|  +--------+     idempotency_  | - Call Payment   |                      |
|                 key}          |   Service         |                     |
|                               +--------+---------+                      |
|                                        |                                |
|  Step 3: Payment processing            |                                |
|                                        v                                |
|                               +------------------+                      |
|                               | Payment Service  |                      |
|                               | - Charge card    |                      |
|                               | - Return success |                      |
|                               |   or failure     |                      |
|                               +--------+---------+                      |
|                                        |                                |
|  Step 4: Confirm or rollback           |                                |
|                                        v                                |
|                               +------------------+                      |
|                               | If payment OK:   |                      |
|                               | - Mark CONFIRMED |                      |
|                               | - Persist booking|                      |
|                               | - Send confirm   |                      |
|                               |   notification   |                      |
|                               |                  |                      |
|                               | If payment FAIL: |                      |
|                               | - Release hold   |                      |
|                               | - Restore avail  |                      |
|                               | - Notify user    |                      |
|                               +------------------+                      |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  IDEMPOTENCY KEY:                                                       |
|                                                                         |
|  Every booking request carries a client-generated idempotency_key.      |
|                                                                         |
|  +----------+    +------------------+    +-----------+                  |
|  | Request  | -> | Check:           | -> | Key exists|                  |
|  | with key |    | idempotency_keys |    | in DB?    |                  |
|  | "abc-123"|    | table            |    +-----+-----+                  |
|  +----------+    +------------------+          |                        |
|                                          +-----+-----+                  |
|                                          |           |                  |
|                                         YES          NO                 |
|                                          |           |                  |
|                                          v           v                  |
|                                   +-----------+ +-----------+           |
|                                   | Return    | | Process   |           |
|                                   | previous  | | booking,  |           |
|                                   | result    | | store key |           |
|                                   +-----------+ | + result  |           |
|                                                 +-----------+           |
|                                                                         |
|  Prevents double-booking on network retries or user double-click.       |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  SAGA PATTERN FOR DISTRIBUTED TRANSACTION:                              |
|                                                                         |
|  A booking is NOT a single DB transaction. It spans services:           |
|                                                                         |
|  FORWARD FLOW (happy path):                                             |
|  +------------------+    +------------------+    +-----------------+    |
|  | 1. Reserve       | -> | 2. Charge        | -> | 3. Confirm      |    |
|  |    Inventory     |    |    Payment       |    |    Booking      |    |
|  | (availability    |    | (payment service)|    | (booking svc)   |    |
|  |  service)        |    |                  |    | + notification  |    |
|  +------------------+    +------------------+    +-----------------+    |
|                                                                         |
|  COMPENSATION (on failure at any step):                                 |
|  +------------------+    +------------------+    +-----------------+    |
|  | 3. FAIL?         | -> | Refund Payment   | -> | Release         |    |
|  | Booking can't    |    | (reverse charge) |    | Inventory       |    |
|  | be created       |    |                  |    | (increment back)|    |
|  +------------------+    +------------------+    +-----------------+    |
|                                                                         |
|  Orchestrator-based saga: a central BookingSaga service                 |
|  coordinates the steps and triggers compensations on failure.           |
|                                                                         |
|  Each step is idempotent (can be retried safely).                       |
|  Each step has a corresponding compensation action.                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 12: CANCELLATION FLOW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CANCELLATION STATE MACHINE:                                            |
|                                                                         |
|  +-----------+    +-------------------+    +-----------+                |
|  | CONFIRMED | -> | CANCELLATION      | -> | CANCELLED |                |
|  |           |    | PROCESSING        |    |           |                |
|  +-----------+    | - check policy    |    +-----------+                |
|                   | - calculate refund|                                 |
|                   | - release rooms   |                                 |
|                   +-------------------+                                 |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANCELLATION POLICIES:                                                 |
|                                                                         |
|  +----------------------------+------------------------------------+    |
|  | Policy                     | Refund                             |    |
|  +----------------------------+------------------------------------+    |
|  | Free cancellation          | Full refund if cancelled > 24h     |    |
|  | (most common)              | before check-in                    |    |
|  +----------------------------+------------------------------------+    |
|  | Moderate                   | Full refund > 5 days before        |    |
|  |                            | 50% refund 1-5 days before         |    |
|  |                            | No refund < 24 hours               |    |
|  +----------------------------+------------------------------------+    |
|  | Non-refundable             | No refund at any time              |    |
|  | (discounted rate)          | (cheaper price as trade-off)       |    |
|  +----------------------------+------------------------------------+    |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  REFUND + INVENTORY RELEASE FLOW:                                       |
|                                                                         |
|  +------------------+                                                   |
|  | User requests    |                                                   |
|  | cancellation     |                                                   |
|  +--------+---------+                                                   |
|           |                                                             |
|           v                                                             |
|  +------------------+                                                   |
|  | Booking Service  |                                                   |
|  | 1. Validate      |                                                   |
|  |    booking exists|                                                   |
|  | 2. Check cancel  |                                                   |
|  |    policy + time |                                                   |
|  | 3. Calculate     |                                                   |
|  |    refund amount |                                                   |
|  +--------+---------+                                                   |
|           |                                                             |
|     +-----+-----+                                                       |
|     |           |                                                       |
|     v           v                                                       |
|  +----------+  +------------------+                                     |
|  | Payment  |  | Availability     |                                     |
|  | Service  |  | Service          |                                     |
|  | - refund |  | - decrement      |                                     |
|  |   card   |  |   booked count   |                                     |
|  +----------+  |   (release rooms)|                                     |
|                +------------------+                                     |
|     |           |                                                       |
|     v           v                                                       |
|  +------------------+                                                   |
|  | Notification     |                                                   |
|  | - Confirm cancel |                                                   |
|  |   to user        |                                                   |
|  | - Notify hotel   |                                                   |
|  +------------------+                                                   |
|                                                                         |
|  COMPENSATION SAGA FOR CANCELLATION:                                    |
|                                                                         |
|  Step 1: Mark booking as CANCELLING (prevent double-cancel)             |
|  Step 2: Process refund via Payment Service                             |
|  Step 3: Release inventory via Availability Service                     |
|  Step 4: Mark booking as CANCELLED                                      |
|  Step 5: Send notifications                                             |
|                                                                         |
|  If refund fails > retry with exponential backoff.                      |
|  If inventory release fails > retry (idempotent: decrementing           |
|  booked count for an already-released booking is a no-op).              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 13: SCALING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCALING BY ACCESS PATTERN:                                             |
|                                                                         |
|  SEARCH (read-heavy, 100x more than booking):                           |
|  -----------------------------------------------------------------      |
|                                                                         |
|  +------------------+    +-------------------+                          |
|  | Elasticsearch    |    | Redis Cache       |                          |
|  | Cluster          |    | - search results  |                          |
|  | - 3+ data nodes  |    | - hotel details   |                          |
|  | - read replicas  |    | - TTL: 60s        |                          |
|  | - shard per      |    +-------------------+                          |
|  |   region/city    |                                                   |
|  +------------------+                                                   |
|                                                                         |
|  Strategy:                                                              |
|  * Elasticsearch sharded by geography (city/region)                     |
|  * Read replicas: scale reads independently                             |
|  * Redis caches hot search queries + hotel detail pages                 |
|  * CDN for hotel images/static content                                  |
|  * Eventual consistency OK: availability shown in search is             |
|    approximate - real check happens at booking time                     |
|                                                                         |
|  BOOKING (write-heavy, strong consistency required):                    |
|  -----------------------------------------------------------------      |
|                                                                         |
|  +------------------+    +-------------------+                          |
|  | Booking DB       |    | Inventory DB      |                          |
|  | (PostgreSQL)     |    | (PostgreSQL)      |                          |
|  | - shard by       |    | - shard by        |                          |
|  |   hotel_id       |    |   hotel_id        |                          |
|  | - 2 replicas     |    | - same shard key  |                          |
|  |   per shard      |    |   as booking DB   |                          |
|  +------------------+    +-------------------+                          |
|                                                                         |
|  WHY SHARD BY HOTEL_ID (NOT USER_ID)?                                   |
|  The critical transaction is: "check availability + decrement           |
|  inventory + create reservation" - all for the SAME hotel.              |
|  Sharding by hotel_id keeps all these operations on a single            |
|  shard, enabling single-shard ACID transactions. No distributed         |
|  2PC needed. User-level queries ("my bookings") are less frequent       |
|  and can use a secondary index or read model.                           |
|                                                                         |
|  Strategy:                                                              |
|  * Shard by hotel_id: all data for one hotel on one shard               |
|  * Booking + inventory for same hotel on same shard                     |
|    > enables single-shard transactions (no distributed txn)             |
|  * Replicas for read queries (booking history, reports)                 |
|  * Connection pooling (PgBouncer) to handle connection spikes           |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  EVENT-DRIVEN ARCHITECTURE:                                             |
|                                                                         |
|  +------------------+                                                   |
|  | Booking Service  |                                                   |
|  | emits events:    |                                                   |
|  | - BookingCreated |                                                   |
|  | - BookingCancel  |                                                   |
|  +--------+---------+                                                   |
|           |                                                             |
|           v                                                             |
|  +------------------+                                                   |
|  | Event Bus        |                                                   |
|  | (Kafka)          |                                                   |
|  +--+------+------+-+                                                   |
|     |      |      |                                                     |
|     v      v      v                                                     |
|  +------+ +------+ +------+                                             |
|  |Notif | |Search| |Analyt|                                             |
|  |Svc   | |Index | |ics   |                                             |
|  |(email| |Update| |(rev  |                                             |
|  | SMS) | |(ES)  | |report|                                             |
|  +------+ +------+ |s)   |                                              |
|                     +------+                                            |
|                                                                         |
|  WHY KAFKA? Booking events fan out to 3+ downstream systems             |
|  (notifications, ES index, analytics). Kafka's durable log              |
|  ensures no event is lost if a consumer is temporarily down.            |
|  Partitioned by hotel_id so events for one hotel are ordered.           |
|  Consumer groups let each downstream scale independently.               |
|                                                                         |
|  TRANSACTIONAL OUTBOX PATTERN:                                          |
|  Write booking row + event to outbox table in SAME DB                   |
|  transaction. A relay process reads outbox, publishes to                |
|  Kafka, marks rows as published. Guarantees at-least-once               |
|  event delivery even if Kafka is momentarily unreachable.               |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  MULTI-REGION DEPLOYMENT:                                               |
|                                                                         |
|  +------------------+           +------------------+                    |
|  | US Region        |           | EU Region        |                    |
|  | - Search (local  |           | - Search (local  |                    |
|  |   ES + cache)    |           |   ES + cache)    |                    |
|  | - Read replicas  |           | - Read replicas  |                    |
|  +--------+---------+           +--------+---------+                    |
|           |                              |                              |
|           +----------+  +----------------+                              |
|                      |  |                                               |
|                      v  v                                               |
|               +------------------+                                      |
|               | Central Region   |                                      |
|               | - Booking writes |                                      |
|               | - Inventory DB   |                                      |
|               |   (source of     |                                      |
|               |    truth)        |                                      |
|               +------------------+                                      |
|                                                                         |
|  Search: fully regional for low latency (replicated ES + cache).        |
|  Booking: centralized for strong consistency.                           |
|  Trade-off: booking latency is higher for non-central regions           |
|  (~100-200ms cross-region), but correctness is guaranteed.              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 14: DETAILED WRITE/READ PATHS AND STATE MANAGEMENT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. ENTITY STATE MACHINE (Reservation)                                  |
|                                                                         |
|  PENDING --> HELD --> CONFIRMED --> CHECKED_IN --> CHECKED_OUT          |
|    |           |          |                                             |
|    |           |          +---> CANCELLED (by guest, refund triggered)  |
|    |           |                                                        |
|    |           +---> EXPIRED (TTL hit, inventory released)              |
|    |                                                                    |
|    +---> PAYMENT_FAILED (inventory released)                            |
|                                                                         |
|  CANCELLED --> REFUND_PROCESSING --> REFUND_COMPLETED                   |
|                                                                         |
|  Transition rules:                                                      |
|  * HELD has a 10-minute TTL; auto-transitions to EXPIRED                |
|  * Only CONFIRMED can transition to CHECKED_IN (at hotel)               |
|  * CANCELLED only from CONFIRMED (within cancellation policy)           |
|  * CHECKED_OUT is a terminal state                                      |
|                                                                         |
|  =================================================================      |
|                                                                         |
|  2. CRITICAL WRITE PATH (Room Booking with Atomic Constraint)           |
|                                                                         |
|  Client                API GW        Avail Svc       Booking Svc        |
|    |                     |               |               |              |
|    |-- POST /hold ------>|               |               |              |
|    |                     |-- reserve --->|               |              |
|    |                     |               |               |              |
|    |                     |  BEGIN;                                      |
|    |                     |  UPDATE room_inventory                       |
|    |                     |    SET booked = booked + 1                   |
|    |                     |    WHERE hotel_id = 'h_001'                  |
|    |                     |      AND room_type_id = 'rt_102'             |
|    |                     |      AND date BETWEEN '2024-12-20'           |
|    |                     |                  AND '2024-12-24'            |
|    |                     |      AND booked < total_rooms;               |
|    |                     |  -- rows_updated = 5? all nights avail       |
|    |                     |  -- rows_updated < 5? ROLLBACK               |
|    |                     |                                              |
|    |                     |  INSERT INTO reservations                    |
|    |                     |    (id, hotel_id, room_type_id, guest_id,    |
|    |                     |     check_in, check_out, status,             |
|    |                     |     idempotency_key, created_at)             |
|    |                     |    VALUES (..., 'HELD', :idem_key, now());   |
|    |                     |  COMMIT;                                     |
|    |                     |               |               |              |
|    |                     |  SET hold:{reservation_id} EX 600 (Redis TTL)|
|    |                     |               |               |              |
|    |<-- hold_id, TTL ----|               |               |              |
|    |                     |               |               |              |
|    |-- POST /confirm --->|               |-- confirm --->|              |
|    |   {hold_id, pay}    |               |               |              |
|    |                     |               |  Payment Svc  |              |
|    |                     |               |   charge()    |              |
|    |                     |               |               |              |
|    |                     |  UPDATE reservations SET status = 'CONFIRMED'|
|    |                     |    WHERE id = :hold_id AND status = 'HELD';  |
|    |                     |               |               |              |
|    |                     |  Kafka: emit BookingConfirmed event          |
|    |                     |   -> Notification Svc (email + SMS)          |
|    |                     |   -> ES index update (availability refresh)  |
|    |                     |               |               |              |
|    |<-- booking confirmed|               |               |              |
|                                                                         |
|  =================================================================      |
|                                                                         |
|  3. READ PATH                                                           |
|                                                                         |
|  SEARCH (hotel list):                                                   |
|    Client --> Redis (cache key: hash(location,dates,filters))           |
|      HIT  --> return cached results (TTL 60s)                           |
|      MISS --> Elasticsearch (geo + text + filter query)                 |
|           --> populate Redis, return results                            |
|                                                                         |
|  AVAILABILITY CHECK (at booking time):                                  |
|    Client --> Inventory DB (PostgreSQL, source of truth)                |
|    SELECT (total_rooms - booked) AS available                           |
|      FROM room_inventory                                                |
|      WHERE hotel_id = :h AND room_type_id = :rt                         |
|        AND date BETWEEN :check_in AND :check_out;                       |
|    * Always reads from primary (strong consistency)                     |
|    * Search shows approximate; booking checks real-time                 |
|                                                                         |
|  BOOKING HISTORY (user's reservations):                                 |
|    Client --> Booking DB read replica                                   |
|    * Eventual consistency OK for display purposes                       |
|                                                                         |
|  =================================================================      |
|                                                                         |
|  4. FAILURE SCENARIOS                                                   |
|                                                                         |
|  +-----------------------------+-------------------------------------+  |
|  | What Fails                  | Impact & Recovery                   |  |
|  +-----------------------------+-------------------------------------+  |
|  | Payment succeeds, confirm   | Saga compensation: refund payment, |   |
|  | write fails                 | release inventory hold.             |  |
|  |                             | Orchestrator retries on restart.    |  |
|  +-----------------------------+-------------------------------------+  |
|  | Redis hold key expires      | Background job scans HELD rows     |   |
|  | before guest pays           | older than 10 min, sets EXPIRED,   |   |
|  |                             | decrements booked count in         |   |
|  |                             | room_inventory.                    |   |
|  +-----------------------------+-------------------------------------+  |
|  | Optimistic lock conflict    | Application retries the UPDATE;    |   |
|  | (version mismatch)          | on re-read if booked = total,      |   |
|  |                             | reject with "room unavailable."    |   |
|  +-----------------------------+-------------------------------------+  |
|  | Kafka event lost after      | Transactional outbox pattern:      |   |
|  | booking confirmed           | write event to outbox table in     |   |
|  |                             | same DB txn, relay to Kafka async. |   |
|  +-----------------------------+-------------------------------------+  |
|                                                                         |
|  =================================================================      |
|                                                                         |
|  5. CLEANUP / EXPIRY                                                    |
|                                                                         |
|  EXPIRED HOLDS:                                                         |
|  * Redis key hold:{reservation_id} TTL 600s (10 min)                    |
|  * On key expiry callback OR sweep job every 60s:                       |
|    UPDATE room_inventory SET booked = booked - 1                        |
|      WHERE hotel_id = :h AND room_type_id = :rt                         |
|      AND date BETWEEN :ci AND :co;                                      |
|    UPDATE reservations SET status = 'EXPIRED'                           |
|      WHERE id = :id AND status = 'HELD';                                |
|                                                                         |
|  STALE SEARCH CACHE:                                                    |
|  * Redis search cache TTL: 60 seconds                                   |
|  * Kafka BookingCreated / BookingCancelled events trigger               |
|    ES index refresh for affected hotel availability                     |
|                                                                         |
|  OLD BOOKING DATA:                                                      |
|  * Bookings > 2 years: archived to cold storage (S3 + Athena)           |
|  * room_inventory rows for past dates: purged monthly                   |
|  * ES index: only future + 30-day past dates kept hot                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 15: OVERBOOKING STRATEGY (AIRLINES VS HOTELS)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Airlines: intentionally overbook by ~15%                               |
|    * Historical no-show rate: 10-15%                                    |
|    * total = 200 seats, sell 230 tickets                                |
|    * If everyone shows up > offer compensation + rebooking              |
|    * Revenue optimization: empty seats = lost revenue                   |
|                                                                         |
|  Hotels: generally do NOT overbook                                      |
|    * Guest expectation is guaranteed room                               |
|    * "Walking" a guest (sending to another hotel) is expensive          |
|    * Some hotels overbook by 5% for no-shows + cancellations            |
|    * Overbooking threshold = historical (no_show + late_cancel) rate    |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  KEY DESIGN DIFFERENCE:                                                 |
|                                                                         |
|  +--------------------+-----------------------+----------------------+  |
|  | Dimension          | Airlines              | Hotels               |  |
|  +--------------------+-----------------------+----------------------+  |
|  | Overbooking        | ~15% intentional      | 0-5% at most         |  |
|  | Inventory          | Specific seats (graph) | Room types (counter) | |
|  | Pricing dynamics   | Highly dynamic (yield) | Moderately dynamic   | |
|  | Multi-leg          | A>B>C connections      | Single location,     | |
|  |                    |                        | multi-night (5 legs) | |
|  | Check-in           | Online + boarding pass | Front desk           | |
|  +--------------------+-----------------------+----------------------+  |
|                                                                         |
|  The core booking/concurrency patterns are very similar.                |
|  Both need strong consistency on inventory writes and                   |
|  idempotent booking APIs.                                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 16: WRAP-UP

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SUMMARY OF KEY DESIGN DECISIONS:                                       |
|                                                                         |
|  1. DOUBLE-BOOKING PREVENTION                                           |
|     Atomic DB constraint (booked < total_rooms in WHERE clause)         |
|     with CHECK constraint as safety net. Queue serialization            |
|     added for flash-sale scenarios.                                     |
|                                                                         |
|  2. TWO-PHASE BOOKING (HOLD > CONFIRM)                                  |
|     10-minute hold prevents inventory lockup. Auto-expiry via           |
|     Redis TTL + background sweep releases abandoned holds.              |
|                                                                         |
|  3. SEARCH vs BOOKING CONSISTENCY SPLIT                                 |
|     Search uses eventually-consistent ES + Redis cache.                 |
|     Booking always checks source-of-truth PostgreSQL.                   |
|     Different consistency guarantees for different access paths.        |
|                                                                         |
|  4. SHARD BY HOTEL_ID                                                   |
|     Keeps inventory check + booking creation on a single shard.         |
|     Avoids distributed transactions for the critical path.              |
|                                                                         |
|  5. SAGA FOR CROSS-SERVICE ORCHESTRATION                                |
|     Booking spans inventory, payment, notification services.            |
|     Saga with compensation handles partial failures.                    |
|     Transactional outbox ensures event delivery.                        |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  KEY TRADE-OFFS:                                                        |
|                                                                         |
|  * Search availability is approximate (eventual consistency)            |
|    vs booking availability is exact (strong consistency).               |
|    TRADE-OFF: lower search latency at the cost of occasional            |
|    "room no longer available" at booking time.                          |
|                                                                         |
|  * Centralized booking writes for consistency vs regional               |
|    search for latency. Cross-region booking adds ~100-200ms             |
|    but guarantees no double-booking.                                    |
|                                                                         |
|  * 10-minute hold TTL balances user experience (time to enter           |
|    payment) vs inventory lockup (holding rooms others could book).      |
|                                                                         |
|  * Atomic DB constraint is simpler than optimistic locking but          |
|    slightly less flexible for complex business rules. The trade-off     |
|    favors simplicity given hotel booking's moderate contention.         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 17: INTERVIEW Q&A

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q1: How do you prevent double-booking the last room?                   |
|  -----------------------------------------------------------------      |
|  A: Use an atomic conditional UPDATE with a DB CHECK constraint.        |
|  UPDATE room_inventory SET booked = booked + 1 WHERE booked <           |
|  total_rooms. If rows_updated < expected nights, ROLLBACK the           |
|  transaction. The CHECK constraint (booked <= total_rooms) is a         |
|  database-level safety net. For moderate contention, this single        |
|  statement avoids locks entirely. For flash-sale extremes, add          |
|  queue serialization (Kafka partition per hotel) so requests            |
|  are processed one at a time.                                           |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  Q2: Why not use a distributed lock for every booking?                  |
|  -----------------------------------------------------------------      |
|  A: Distributed locks (Redis SETNX) add complexity: lock expiry,        |
|  fencing tokens, clock skew, and an external dependency. For most       |
|  hotel bookings, contention is low (many room types, many dates),       |
|  so the atomic DB constraint is simpler and sufficient. Reserve         |
|  distributed locks for extreme contention scenarios where DB-level      |
|  approaches become insufficient.                                        |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  Q3: What if payment succeeds but the confirmation write fails?         |
|  -----------------------------------------------------------------      |
|  A: The saga pattern handles this. The BookingSaga orchestrator         |
|  detects the confirmation failure and triggers compensation:            |
|  1. Refund the payment (payment service idempotent refund API)          |
|  2. Release the inventory hold                                          |
|  3. Notify the user of the failure                                      |
|  Each compensation step is idempotent and retried until success.        |
|  The saga's state is persisted, so even if the orchestrator crashes,    |
|  it resumes compensation on restart.                                    |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  Q4: How does the temporary hold work? What if the user abandons?       |
|  -----------------------------------------------------------------      |
|  A: When a user selects a room, we decrement available inventory        |
|  and create a hold record with a 10-15 minute TTL. A background         |
|  job (or Redis key expiry callback) checks for expired holds and        |
|  releases them back to inventory. The hold prevents others from         |
|  booking while the user enters payment details, but auto-expires        |
|  to prevent permanent inventory lockup from abandoned sessions.         |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  Q5: How would you handle a flash sale (50% off a luxury hotel)?        |
|  -----------------------------------------------------------------      |
|  A: Multi-layer defense:                                                |
|  1. Rate limiting at API gateway (per-user, per-IP)                     |
|  2. Redis fast-path: DECR availability keys to pre-filter before DB     |
|  3. Queue serialization: route booking requests for that hotel          |
|     through a Kafka partition > single consumer processes in order      |
|  4. Waiting room / virtual queue: frontend shows "You are #347 in       |
|     line" to manage expectations and reduce server load                 |
|  5. Pre-validate availability before entering queue to reject           |
|     obviously impossible requests early                                 |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  Q6: Why shard by hotel_id and not by user_id?                          |
|  -----------------------------------------------------------------      |
|  A: The critical transaction is: "check availability + decrement        |
|  inventory + create booking" - all for the SAME hotel. Sharding         |
|  by hotel_id keeps all these operations on a single shard, avoiding     |
|  distributed transactions. User-level queries (my bookings) are         |
|  less frequent and can use a secondary index or a separate read         |
|  model (event-sourced from booking events).                             |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  Q7: How do you keep Elasticsearch in sync with the booking DB?         |
|  -----------------------------------------------------------------      |
|  A: Event-driven sync via Kafka with transactional outbox. When a       |
|  booking is created or cancelled, an event row is written to the        |
|  outbox table in the same DB transaction. A relay process publishes     |
|  it to Kafka. An ES updater consumer updates the hotel's availability   |
|  in the ES index. This is eventually consistent (seconds delay),        |
|  which is acceptable for search results. The real availability check    |
|  happens at booking time against the source-of-truth PostgreSQL DB.     |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  Q8: How do you handle the case where search shows "available"          |
|      but booking fails because it was just booked?                      |
|  -----------------------------------------------------------------      |
|  A: This is expected and by design. Search uses cached/eventually       |
|  consistent data for performance. When the user clicks "Book", the      |
|  availability service does a real-time check against the DB. If         |
|  the room was just booked, we return a clear error: "This room is       |
|  no longer available" and suggest alternative rooms or dates. The       |
|  UX should gracefully handle this common scenario.                      |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  Q9: How would you add dynamic pricing?                                 |
|  -----------------------------------------------------------------      |
|  A: A pricing service that adjusts rates based on:                      |
|  * Demand (occupancy rate approaching capacity > price up)              |
|  * Seasonality (holidays, events in the city)                           |
|  * Competitor pricing (scrape or API)                                   |
|  * Lead time (last-minute deals vs far-out bookings)                    |
|  Prices computed periodically (every 15 min) and cached. The search     |
|  index stores current prices. At booking time, the confirmed price      |
|  is locked in (the price shown at selection time, not a stale cache).   |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  Q10: How is this different from designing an airline reservation?      |
|  -----------------------------------------------------------------      |
|  A: Key differences:                                                    |
|  1. Overbooking: airlines overbook (~15%), hotels generally don't       |
|  2. Seat selection: airlines have specific seats (assigned graph),      |
|     hotels have room TYPES (fungible inventory count)                   |
|  3. Pricing: airline pricing is far more dynamic (yield management),    |
|     hotel pricing changes less frequently                               |
|  4. Multi-leg: flights have connections (A>B>C), hotels are single      |
|     location but multi-night (each night is like a "leg")               |
|  5. Check-in: airlines have online check-in + boarding pass,            |
|     hotels have front-desk check-in                                     |
|  The core booking/concurrency patterns are very similar.                |
|                                                                         |
+-------------------------------------------------------------------------+
```
