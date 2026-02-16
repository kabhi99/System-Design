# BOOKMYSHOW SYSTEM DESIGN
*Chapter 1: Requirements and Scale Estimation*

BookMyShow is India's leading entertainment booking platform. Designing
such a system requires handling concurrent bookings, preventing double-booking,
managing inventory in real-time, and processing payments securely.

## SECTION 1.1: UNDERSTANDING THE BUSINESS

### WHAT IS BOOKMYSHOW?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BookMyShow is an online ticket booking platform for:                   |
|                                                                         |
|  * Movies                                                               |
|  * Live concerts and events                                             |
|  * Sports matches                                                       |
|  * Theatre and plays                                                    |
|  * Comedy shows                                                         |
|                                                                         |
|  CORE FUNCTIONALITY:                                                    |
|                                                                         |
|  1. BROWSING                                                            |
|     Users browse movies, events by location, date, genre                |
|                                                                         |
|  2. SEAT SELECTION                                                      |
|     Users see venue layout, select specific seats                       |
|     Real-time availability updates                                      |
|                                                                         |
|  3. BOOKING                                                             |
|     Temporary hold on seats during checkout                             |
|     Payment processing                                                  |
|     Ticket generation                                                   |
|                                                                         |
|  4. TICKET DELIVERY                                                     |
|     E-ticket via email/SMS                                              |
|     QR code for venue entry                                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### THE UNIQUE CHALLENGE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY IS TICKET BOOKING HARD?                                            |
|                                                                         |
|  FINITE INVENTORY                                                       |
|  -----------------                                                      |
|  Unlike e-commerce (can restock), a movie show has exactly N seats.     |
|  Once sold, they're gone. Overselling is catastrophic.                  |
|                                                                         |
|  CONCURRENT ACCESS                                                      |
|  -----------------                                                      |
|  Popular shows: Thousands of users trying to book same seats            |
|  simultaneously. First-day-first-show of blockbusters!                  |
|                                                                         |
|  RACE CONDITIONS                                                        |
|  ----------------                                                       |
|  User A and User B both see Seat A5 available                           |
|  Both click "Book" at same time                                         |
|  > Only ONE can get the seat!                                           |
|                                                                         |
|  TEMPORARY HOLDS                                                        |
|  ----------------                                                       |
|  User selects seats but takes time to pay                               |
|  Seats must be locked temporarily                                       |
|  But not forever (abandoned carts)                                      |
|                                                                         |
|  FLASH SALES                                                            |
|  -----------                                                            |
|  Concert ticket drops at specific time                                  |
|  Millions of requests in seconds                                        |
|  System must not crash                                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.2: FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FUNCTIONAL REQUIREMENTS                                                |
|                                                                         |
|  1. CONTENT MANAGEMENT (Admin)                                          |
|  -----------------------------                                          |
|  * Add/edit movies, events, venues                                      |
|  * Configure showtimes, pricing                                         |
|  * Define seat layouts for venues                                       |
|  * Manage promotions and offers                                         |
|                                                                         |
|  2. SEARCH & DISCOVERY (User)                                           |
|  -------------------------------                                        |
|  * Search movies by title, genre, language                              |
|  * Filter by date, time, location                                       |
|  * View movie details (cast, synopsis, ratings)                         |
|  * See nearby theaters                                                  |
|                                                                         |
|  3. SEAT SELECTION (User)                                               |
|  -------------------------                                              |
|  * View venue/theater seat layout                                       |
|  * See real-time seat availability                                      |
|  * Select multiple seats                                                |
|  * See price breakdown by seat category                                 |
|                                                                         |
|  4. BOOKING FLOW (User)                                                 |
|  -----------------------                                                |
|  * Temporary hold on selected seats (e.g., 10 minutes)                  |
|  * Apply coupons/offers                                                 |
|  * Multiple payment options (cards, UPI, wallets)                       |
|  * Handle payment failures gracefully                                   |
|  * Generate confirmation and e-ticket                                   |
|                                                                         |
|  5. TICKET MANAGEMENT (User)                                            |
|  ------------------------------                                         |
|  * View booking history                                                 |
|  * Download/resend tickets                                              |
|  * Cancel bookings (with refund policy)                                 |
|                                                                         |
|  6. NOTIFICATIONS                                                       |
|  -----------------                                                      |
|  * Booking confirmation (email, SMS)                                    |
|  * Reminders before show                                                |
|  * Cancellation alerts                                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.3: NON-FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NON-FUNCTIONAL REQUIREMENTS                                            |
|                                                                         |
|  1. CONSISTENCY                                                         |
|  ---------------                                                        |
|  * NO double-booking (same seat sold twice)                             |
|  * Seat status must be accurate                                         |
|  * Payment must be atomic (charge once)                                 |
|  This is NON-NEGOTIABLE for a booking system!                           |
|                                                                         |
|  2. AVAILABILITY                                                        |
|  --------------                                                         |
|  * 99.99% uptime target                                                 |
|  * Graceful degradation (search works even if booking slow)             |
|  * Must handle traffic spikes                                           |
|                                                                         |
|  3. LATENCY                                                             |
|  ---------                                                              |
|  * Search results: < 200ms                                              |
|  * Seat map loading: < 500ms                                            |
|  * Seat lock: < 100ms                                                   |
|  * Payment processing: < 5s (includes external gateway)                 |
|                                                                         |
|  4. SCALABILITY                                                         |
|  -------------                                                          |
|  * Handle 10x normal traffic during blockbuster releases                |
|  * Support millions of concurrent users                                 |
|  * Scale horizontally                                                   |
|                                                                         |
|  5. DURABILITY                                                          |
|  -----------                                                            |
|  * Never lose a confirmed booking                                       |
|  * Survive datacenter failures                                          |
|  * Regular backups                                                      |
|                                                                         |
|  6. SECURITY                                                            |
|  ----------                                                             |
|  * PCI-DSS compliance for payments                                      |
|  * User data privacy                                                    |
|  * Fraud prevention                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.4: SCALE ESTIMATION

Let's estimate the scale for a BookMyShow-like platform.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ASSUMPTIONS (India-scale platform)                                     |
|                                                                         |
|  USERS:                                                                 |
|  * 75 million registered users                                          |
|  * 15 million monthly active users (MAU)                                |
|  * 5 million daily active users (DAU)                                   |
|                                                                         |
|  CONTENT:                                                               |
|  * 10,000 theaters/venues                                               |
|  * Average 5 screens per theater = 50,000 screens                       |
|  * Average 5 shows per screen per day = 250,000 shows/day               |
|  * Average 200 seats per screen = 50 million seats/day                  |
|                                                                         |
|  BOOKINGS:                                                              |
|  * 2 million bookings per day                                           |
|  * Average 2.5 tickets per booking = 5 million tickets/day              |
|  * 10% seat occupancy rate (normal day)                                 |
|                                                                         |
|  TRAFFIC:                                                               |
|  * 50 million page views per day                                        |
|  * 10 million search queries per day                                    |
|  * 5 million seat map views per day                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### TRAFFIC CALCULATIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REQUESTS PER SECOND (RPS)                                              |
|                                                                         |
|  PAGE VIEWS:                                                            |
|  * 50 million / 86,400 seconds = ~580 RPS average                       |
|  * Peak (evening, 7-10 PM): 3x average = ~1,750 RPS                     |
|                                                                         |
|  SEARCH QUERIES:                                                        |
|  * 10 million / 86,400 = ~116 RPS average                               |
|  * Peak: ~350 RPS                                                       |
|                                                                         |
|  SEAT MAP VIEWS:                                                        |
|  * 5 million / 86,400 = ~58 RPS average                                 |
|  * Peak: ~175 RPS                                                       |
|                                                                         |
|  BOOKING TRANSACTIONS:                                                  |
|  * 2 million / 86,400 = ~23 RPS average                                 |
|  * Peak: ~70 RPS                                                        |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  FLASH SALE SCENARIO (Blockbuster release / Concert tickets)            |
|                                                                         |
|  * 1 million users trying to access in first 5 minutes                  |
|  * 1,000,000 / 300 seconds = 3,333 RPS sustained                        |
|  * Initial spike: 10,000+ RPS in first seconds                          |
|                                                                         |
|  This requires special handling (virtual waiting room, rate limiting)   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### STORAGE CALCULATIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DATA STORAGE ESTIMATES                                                 |
|                                                                         |
|  USERS TABLE:                                                           |
|  * 75 million users                                                     |
|  * ~500 bytes per user (profile, preferences)                           |
|  * Total: 75M x 500 = 37.5 GB                                           |
|                                                                         |
|  MOVIES/EVENTS:                                                         |
|  * 50,000 movies/events (including historical)                          |
|  * ~10 KB per item (metadata, descriptions)                             |
|  * Total: 50K x 10KB = 500 MB                                           |
|                                                                         |
|  SHOWS:                                                                 |
|  * 250,000 shows/day x 365 days x 2 years = 182 million shows           |
|  * ~1 KB per show                                                       |
|  * Total: 182M x 1KB = 182 GB                                           |
|                                                                         |
|  SEATS:                                                                 |
|  * 50 million seats/day x 365 x 2 = 36.5 billion seat records           |
|  * ~200 bytes per seat record                                           |
|  * Total: 36.5B x 200 = 7.3 TB                                          |
|  (This is the largest table - needs partitioning/archival)              |
|                                                                         |
|  BOOKINGS:                                                              |
|  * 2 million bookings/day x 365 x 2 = 1.46 billion bookings             |
|  * ~500 bytes per booking                                               |
|  * Total: 1.46B x 500 = 730 GB                                          |
|                                                                         |
|  TOTAL STRUCTURED DATA: ~10 TB                                          |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  MEDIA STORAGE:                                                         |
|  * Movie posters, banners: 50K x 5MB = 250 GB                           |
|  * Venue photos: 10K x 10MB = 100 GB                                    |
|  * Total media: ~500 GB (served via CDN)                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### BANDWIDTH CALCULATIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BANDWIDTH ESTIMATES                                                    |
|                                                                         |
|  AVERAGE PAGE SIZE: 2 MB (including images, cached via CDN)             |
|  API RESPONSE: 5 KB average                                             |
|                                                                         |
|  OUTBOUND BANDWIDTH:                                                    |
|  * Page views: 50M x 2MB / 86,400 = 1.16 GB/s average                   |
|  * API calls: 100M x 5KB / 86,400 = 5.8 MB/s                            |
|                                                                         |
|  With CDN serving static content:                                       |
|  * Origin servers: ~100 MB/s                                            |
|  * CDN handles the rest                                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.5: SUMMARY OF SCALE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCALE SUMMARY FOR SYSTEM DESIGN                                        |
|                                                                         |
|  +----------------------------------------------------------------+     |
|  |                                                                |     |
|  |  USERS                                                        |      |
|  |  -----                                                        |      |
|  |  MAU: 15 million                                              |      |
|  |  DAU: 5 million                                               |      |
|  |  Peak concurrent: 500K                                        |      |
|  |                                                                |     |
|  |  TRAFFIC                                                      |      |
|  |  -------                                                      |      |
|  |  Normal: ~600 RPS                                            |       |
|  |  Peak: ~2,000 RPS                                            |       |
|  |  Flash sale: ~10,000 RPS (spike)                             |       |
|  |                                                                |     |
|  |  BOOKINGS                                                     |      |
|  |  --------                                                     |      |
|  |  Daily: 2 million                                             |      |
|  |  Peak: ~70 bookings/second                                   |       |
|  |                                                                |     |
|  |  STORAGE                                                      |      |
|  |  -------                                                      |      |
|  |  Structured data: ~10 TB                                     |       |
|  |  Media: ~500 GB (CDN)                                        |       |
|  |  Growth: ~5 TB/year                                          |       |
|  |                                                                |     |
|  |  KEY CHALLENGES                                               |      |
|  |  --------------                                               |      |
|  |  1. Prevent double-booking (consistency)                     |       |
|  |  2. Handle flash sales (scalability)                         |       |
|  |  3. Real-time seat availability (low latency)                |       |
|  |  4. Payment processing (reliability)                         |       |
|  |                                                                |     |
|  +----------------------------------------------------------------+     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REQUIREMENTS - KEY TAKEAWAYS                                           |
|                                                                         |
|  FUNCTIONAL                                                             |
|  ----------                                                             |
|  * Browse movies/events                                                 |
|  * View seat maps with real-time availability                           |
|  * Book with temporary seat hold                                        |
|  * Process payments                                                     |
|  * Generate tickets                                                     |
|                                                                         |
|  NON-FUNCTIONAL                                                         |
|  --------------                                                         |
|  * Consistency: NO double-booking (critical!)                           |
|  * Availability: 99.99% uptime                                          |
|  * Latency: Sub-second for most operations                              |
|  * Scalability: Handle flash sales                                      |
|                                                                         |
|  SCALE                                                                  |
|  -----                                                                  |
|  * 5M DAU, 2M bookings/day                                              |
|  * 600 RPS normal, 10K RPS flash sale                                   |
|  * 10 TB data                                                           |
|                                                                         |
|  INTERVIEW TIP                                                          |
|  -------------                                                          |
|  Start with requirements clarification. Ask about:                      |
|  * Scale (users, bookings)                                              |
|  * Features to focus on                                                 |
|  * Consistency vs availability trade-offs                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 1

