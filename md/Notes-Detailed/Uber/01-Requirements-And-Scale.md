# UBER SYSTEM DESIGN
*Chapter 1: Requirements and Scale Estimation*

Uber is a ride-hailing platform that connects riders with drivers in real-time.
The system must handle millions of location updates per second, match riders
with nearby drivers, and provide accurate ETAs.

## SECTION 1.1: UNDERSTANDING UBER

### WHAT IS UBER?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Uber connects riders with drivers in real-time:                       |
|                                                                         |
|  RIDER FLOW:                                                           |
|  1. Open app, see nearby drivers on map                               |
|  2. Enter destination                                                  |
|  3. See fare estimate and ETA                                         |
|  4. Request ride                                                       |
|  5. Matched with driver                                               |
|  6. Track driver arrival in real-time                                 |
|  7. Take ride, track progress                                         |
|  8. Pay automatically, rate driver                                    |
|                                                                         |
|  DRIVER FLOW:                                                          |
|  1. Go online (available for rides)                                   |
|  2. Location continuously updated to server                           |
|  3. Receive ride request                                              |
|  4. Accept/decline within time limit                                  |
|  5. Navigate to pickup location                                       |
|  6. Start ride, navigate to destination                               |
|  7. Complete ride, receive payment                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### THE UNIQUE CHALLENGES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY IS UBER HARD TO BUILD?                                           |
|                                                                         |
|  1. REAL-TIME LOCATION TRACKING                                       |
|  --------------------------------                                       |
|  Millions of drivers sending GPS coordinates every 4 seconds.        |
|  Must process and store this efficiently.                            |
|                                                                         |
|  2. GEOSPATIAL QUERIES                                                |
|  ----------------------                                                 |
|  "Find all drivers within 3km of this location"                      |
|  Must be fast (<100ms) despite millions of drivers.                  |
|                                                                         |
|  3. MATCHING ALGORITHM                                                |
|  ------------------------                                               |
|  Match rider with best driver considering:                           |
|  - Distance                                                           |
|  - ETA                                                                |
|  - Driver rating                                                      |
|  - Driver preferences                                                 |
|  All in real-time!                                                    |
|                                                                         |
|  4. DYNAMIC PRICING                                                    |
|  ---------------------                                                  |
|  Surge pricing when demand > supply.                                 |
|  Must calculate in real-time based on area demand.                   |
|                                                                         |
|  5. ETA PREDICTION                                                     |
|  ------------------                                                     |
|  Accurate arrival time predictions considering:                      |
|  - Current traffic                                                    |
|  - Time of day                                                        |
|  - Weather                                                            |
|  - Historical patterns                                                |
|                                                                         |
|  6. GLOBAL SCALE                                                       |
|  --------------                                                         |
|  Operating in 10,000+ cities worldwide.                              |
|  Different regulations per city/country.                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.2: FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FUNCTIONAL REQUIREMENTS                                               |
|                                                                         |
|  RIDER APP                                                             |
|  ---------                                                              |
|  * View nearby available drivers on map                               |
|  * Enter pickup and destination                                       |
|  * Get fare estimate before booking                                   |
|  * Request ride                                                       |
|  * Track driver location in real-time                                |
|  * Track ride progress                                                |
|  * Payment processing                                                 |
|  * Rate driver after ride                                             |
|  * View ride history                                                  |
|                                                                         |
|  DRIVER APP                                                            |
|  ----------                                                             |
|  * Go online/offline                                                  |
|  * Continuously send location                                         |
|  * Receive ride requests                                              |
|  * Accept/decline rides                                               |
|  * Navigation to pickup and destination                              |
|  * Start/end ride                                                     |
|  * View earnings                                                      |
|  * Rate riders                                                        |
|                                                                         |
|  MATCHING SYSTEM                                                       |
|  ---------------                                                        |
|  * Find nearby available drivers                                      |
|  * Match rider with optimal driver                                    |
|  * Handle driver acceptance/rejection                                |
|  * Re-match if driver cancels                                        |
|                                                                         |
|  PRICING                                                               |
|  -------                                                                |
|  * Base fare + distance + time                                       |
|  * Surge pricing during high demand                                  |
|  * Promo codes and discounts                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.3: NON-FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NON-FUNCTIONAL REQUIREMENTS                                           |
|                                                                         |
|  1. LOW LATENCY                                                        |
|  ---------------                                                        |
|  * Driver location update: < 200ms                                    |
|  * Find nearby drivers: < 100ms                                       |
|  * Match and notify: < 1 second                                       |
|  * ETA calculation: < 500ms                                           |
|                                                                         |
|  2. HIGH AVAILABILITY                                                  |
|  ---------------------                                                  |
|  * 99.99% uptime                                                      |
|  * Degraded mode: If matching fails, show drivers on map             |
|                                                                         |
|  3. CONSISTENCY                                                        |
|  -------------                                                          |
|  * Strong: Ride assignment (no double-booking drivers)               |
|  * Eventual: Location updates, ETA displays                          |
|                                                                         |
|  4. SCALABILITY                                                        |
|  -------------                                                          |
|  * Support millions of concurrent drivers                            |
|  * Handle 10x surge during events                                    |
|  * Scale to new cities easily                                        |
|                                                                         |
|  5. REAL-TIME                                                          |
|  ------------                                                           |
|  * Location updates visible within seconds                           |
|  * Push notifications for ride requests                              |
|  * Live tracking during ride                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.4: SCALE ESTIMATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ASSUMPTIONS (Uber-scale platform)                                    |
|                                                                         |
|  USERS:                                                                |
|  * 100 million monthly active riders                                  |
|  * 5 million active drivers                                           |
|  * 1 million concurrent drivers online (peak)                        |
|                                                                         |
|  RIDES:                                                                |
|  * 20 million rides per day                                           |
|  * Peak: 1,000 ride requests per second                              |
|                                                                         |
|  LOCATION UPDATES:                                                     |
|  * Drivers send location every 4 seconds                             |
|  * 1 million drivers × (1 update / 4 seconds) = 250,000 updates/sec |
|                                                                         |
|  GEOSPATIAL QUERIES:                                                   |
|  * "Show nearby drivers" on app open                                 |
|  * "Find driver" on ride request                                     |
|  * ~500,000 queries/second during peak                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### TRAFFIC CALCULATIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LOCATION UPDATES                                                      |
|                                                                         |
|  Drivers online: 1,000,000                                            |
|  Update frequency: Every 4 seconds                                    |
|  Updates per second: 1,000,000 / 4 = 250,000 writes/sec              |
|                                                                         |
|  Each update: ~100 bytes (lat, lng, timestamp, driver_id, status)    |
|  Write bandwidth: 250,000 × 100 = 25 MB/sec                          |
|                                                                         |
|  GEOSPATIAL QUERIES                                                    |
|                                                                         |
|  App opens per second: 100,000                                        |
|  Each shows nearby drivers: 100,000 reads/sec                        |
|                                                                         |
|  Ride requests: 1,000/sec                                             |
|  Each queries nearby drivers: 1,000 reads/sec                        |
|                                                                         |
|  Total geospatial reads: ~100,000/sec                                |
|                                                                         |
|  RIDES                                                                 |
|                                                                         |
|  Rides per day: 20 million                                            |
|  Rides per second (average): 20M / 86,400 = ~230/sec                 |
|  Peak rides per second: ~1,000/sec                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### STORAGE CALCULATIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LOCATION HISTORY                                                      |
|                                                                         |
|  Updates per day: 250,000/sec × 86,400 = 21.6 billion                |
|  Data per update: 100 bytes                                           |
|  Daily storage: 21.6B × 100 = 2.16 TB/day                            |
|                                                                         |
|  Retention: 30 days > 65 TB                                           |
|  (Can use time-series DB with auto-expiry)                           |
|                                                                         |
|  RIDE DATA                                                             |
|                                                                         |
|  Rides per day: 20 million                                            |
|  Data per ride: 2 KB (route, fare, details)                          |
|  Daily: 20M × 2KB = 40 GB/day                                        |
|  Yearly: 40 × 365 = 14.6 TB/year                                     |
|                                                                         |
|  USER DATA                                                             |
|                                                                         |
|  100M riders × 1KB = 100 GB                                           |
|  5M drivers × 2KB = 10 GB                                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.5: SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  UBER SCALE SUMMARY                                                    |
|                                                                         |
|  +----------------------------------------------------------------+   |
|  |                                                                |   |
|  |  USERS                                                        |   |
|  |  -----                                                        |   |
|  |  Active drivers: 1 million (peak concurrent)                 |   |
|  |  Active riders: 100 million MAU                              |   |
|  |                                                                |   |
|  |  LOCATION UPDATES                                             |   |
|  |  ----------------                                             |   |
|  |  250,000 writes/second                                       |   |
|  |  25 MB/sec write bandwidth                                   |   |
|  |                                                                |   |
|  |  GEOSPATIAL QUERIES                                           |   |
|  |  ------------------                                           |   |
|  |  100,000 reads/second                                        |   |
|  |  Must complete in <100ms                                     |   |
|  |                                                                |   |
|  |  RIDES                                                        |   |
|  |  -----                                                        |   |
|  |  20 million/day                                               |   |
|  |  1,000/second peak                                           |   |
|  |                                                                |   |
|  |  KEY CHALLENGES                                               |   |
|  |  --------------                                               |   |
|  |  1. High-throughput location ingestion                       |   |
|  |  2. Fast geospatial queries                                  |   |
|  |  3. Real-time matching                                       |   |
|  |  4. Accurate ETA prediction                                  |   |
|  |                                                                |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 1

