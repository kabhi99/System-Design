# FOOD DELIVERY PLATFORM SYSTEM DESIGN (ZOMATO/SWIGGY/DOORDASH-LIKE)

PART 1: REQUIREMENTS AND SCALE ESTIMATION

## SECTION 1: UNDERSTANDING THE PROBLEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS A FOOD DELIVERY PLATFORM?                                      |
|                                                                         |
|  A three-sided marketplace connecting:                                  |
|  * CUSTOMERS - People ordering food                                     |
|  * RESTAURANTS - Places preparing food                                  |
|  * DELIVERY PARTNERS - People delivering food                           |
|                                                                         |
|  Examples: Zomato, Swiggy, DoorDash, Uber Eats, Grubhub                 |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  THREE-SIDED MARKETPLACE                                                |
|                                                                         |
|  +--------------------------------------------------------------------+ |
|  |                                                                    | |
|  |         +--------------+                                           | |
|  |         |   CUSTOMER   |                                           | |
|  |         |              |                                           | |
|  |         | * Browse     |                                           | |
|  |         | * Order      |                                           | |
|  |         | * Track      |                                           | |
|  |         | * Pay        |                                           | |
|  |         +------+-------+                                           | |
|  |                |                                                   | |
|  |                v                                                   | |
|  |        +---------------+                                           | |
|  |        |   PLATFORM    |                                           | |
|  |        |   (Zomato)    |                                           | |
|  |        |               |                                           | |
|  |        | * Matching    |                                           | |
|  |        | * Pricing     |                                           | |
|  |        | * Payments    |                                           | |
|  |        | * Support     |                                           | |
|  |        +-------+-------+                                           | |
|  |                |                                                   | |
|  |     +----------+----------+                                        | |
|  |     v                     v                                        | |
|  |  +--------------+   +--------------+                               | |
|  |  |  RESTAURANT  |   |   DELIVERY   |                               | |
|  |  |              |   |   PARTNER    |                               | |
|  |  | * Menu mgmt  |   |              |                               | |
|  |  | * Accept     |   | * Accept     |                               | |
|  |  | * Prepare    |   | * Pickup     |                               | |
|  |  | * Package    |   | * Deliver    |                               | |
|  |  +--------------+   +--------------+                               | |
|  |                                                                    | |
|  +--------------------------------------------------------------------+ |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  KEY CHALLENGES                                                         |
|                                                                         |
|  1. REAL-TIME LOCATION TRACKING                                         |
|     * Track delivery partner location continuously                      |
|     * Update every 3-5 seconds                                          |
|     * Show live tracking to customer                                    |
|                                                                         |
|  2. DELIVERY PARTNER ASSIGNMENT                                         |
|     * Find optimal partner for each order                               |
|     * Balance distance, load, partner preferences                       |
|     * Handle surge hours efficiently                                    |
|                                                                         |
|  3. ETA PREDICTION                                                      |
|     * Predict food preparation time                                     |
|     * Predict delivery time accurately                                  |
|     * Account for traffic, weather, restaurant load                     |
|                                                                         |
|  4. RESTAURANT AVAILABILITY                                             |
|     * Real-time menu availability                                       |
|     * Restaurant open/close status                                      |
|     * Busy restaurant handling                                          |
|                                                                         |
|  5. PAYMENT & SETTLEMENTS                                               |
|     * Customer payments                                                 |
|     * Restaurant payouts                                                |
|     * Delivery partner earnings                                         |
|     * Refunds and disputes                                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2: FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CUSTOMER APP FEATURES                                                  |
|                                                                         |
|  1. DISCOVERY & BROWSING                                                |
|     * Browse restaurants by location                                    |
|     * Search by cuisine, dish, restaurant name                          |
|     * Filter (rating, price, delivery time, offers)                     |
|     * View restaurant menus and prices                                  |
|     * See reviews and ratings                                           |
|                                                                         |
|  2. CART & ORDERING                                                     |
|     * Add items to cart                                                 |
|     * Customize items (add-ons, special instructions)                   |
|     * Apply coupons/offers                                              |
|     * Choose delivery/pickup                                            |
|     * Schedule orders for later                                         |
|                                                                         |
|  3. PAYMENTS                                                            |
|     * Multiple payment options (card, UPI, wallet, COD)                 |
|     * Save payment methods                                              |
|     * Split bills                                                       |
|                                                                         |
|  4. ORDER TRACKING                                                      |
|     * Real-time order status                                            |
|     * Live delivery partner location                                    |
|     * ETA updates                                                       |
|     * Contact delivery partner                                          |
|                                                                         |
|  5. POST-ORDER                                                          |
|     * Rate order, restaurant, delivery                                  |
|     * View order history                                                |
|     * Reorder previous orders                                           |
|     * Raise issues/complaints                                           |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  RESTAURANT APP/DASHBOARD FEATURES                                      |
|                                                                         |
|  1. ONBOARDING                                                          |
|     * Register restaurant                                               |
|     * Upload documents (FSSAI, GST)                                     |
|     * Set up bank account                                               |
|                                                                         |
|  2. MENU MANAGEMENT                                                     |
|     * Add/edit menu items                                               |
|     * Set prices and variants                                           |
|     * Upload food images                                                |
|     * Mark items available/unavailable                                  |
|     * Set preparation time                                              |
|                                                                         |
|  3. ORDER MANAGEMENT                                                    |
|     * Receive new orders (with alert)                                   |
|     * Accept/reject orders                                              |
|     * Mark order ready for pickup                                       |
|     * View order history                                                |
|                                                                         |
|  4. BUSINESS INSIGHTS                                                   |
|     * Sales analytics                                                   |
|     * Popular items                                                     |
|     * Customer reviews                                                  |
|     * Earnings and payouts                                              |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  DELIVERY PARTNER APP FEATURES                                          |
|                                                                         |
|  1. ONBOARDING                                                          |
|     * Register as delivery partner                                      |
|     * Upload documents (ID, license, vehicle)                           |
|     * Background verification                                           |
|     * Training completion                                               |
|                                                                         |
|  2. AVAILABILITY                                                        |
|     * Go online/offline                                                 |
|     * Set preferred areas                                               |
|     * Accept/reject delivery requests                                   |
|                                                                         |
|  3. DELIVERY FLOW                                                       |
|     * Receive delivery requests                                         |
|     * Navigate to restaurant                                            |
|     * Mark picked up                                                    |
|     * Navigate to customer                                              |
|     * Mark delivered                                                    |
|     * Collect COD if applicable                                         |
|                                                                         |
|  4. EARNINGS                                                            |
|     * View daily/weekly earnings                                        |
|     * Incentive tracking                                                |
|     * Instant withdrawal                                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3: NON-FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PERFORMANCE                                                            |
|                                                                         |
|  * Restaurant search: < 200ms                                           |
|  * Order placement: < 500ms                                             |
|  * Location update: every 3-5 seconds                                   |
|  * ETA update: every 30 seconds                                         |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  AVAILABILITY                                                           |
|                                                                         |
|  * 99.99% uptime (52 minutes downtime/year)                             |
|  * Core ordering flow must never go down                                |
|  * Graceful degradation for non-critical features                       |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  SCALABILITY                                                            |
|                                                                         |
|  * Handle 10x traffic during peak hours                                 |
|  * Peak: Lunch (12-2 PM), Dinner (7-10 PM)                              |
|  * Festival days: 20x normal traffic                                    |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  RELIABILITY                                                            |
|                                                                         |
|  * Orders must never be lost                                            |
|  * Payment transactions must be atomic                                  |
|  * Location data can be eventually consistent                           |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  CONSISTENCY                                                            |
|                                                                         |
|  * Strong: Order state, payments, inventory                             |
|  * Eventual: Ratings, reviews, analytics                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4: SCALE ESTIMATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  USER BASE (Zomato-like scale)                                          |
|                                                                         |
|  * 50 million monthly active customers                                  |
|  * 15 million daily active customers                                    |
|  * 500,000 restaurant partners                                          |
|  * 500,000 active delivery partners                                     |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ORDER VOLUME                                                           |
|                                                                         |
|  Orders per day:                                                        |
|  * Average: 3 million orders/day                                        |
|  * Peak hour: 500,000 orders/hour                                       |
|                                                                         |
|  Orders per second:                                                     |
|  * Average: 3M / 86400 ~ 35 orders/second                               |
|  * Peak: 500K / 3600 ~ 140 orders/second                                |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  SEARCH & BROWSE                                                        |
|                                                                         |
|  * 15M DAU x 10 searches/day = 150M searches/day                        |
|  * 150M / 86400 ~ 1,750 searches/second                                 |
|  * Peak (3x): 5,000 searches/second                                     |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  LOCATION UPDATES (The Heavy Part!)                                     |
|                                                                         |
|  Active delivery partners during peak:                                  |
|  * 300,000 partners online simultaneously                               |
|                                                                         |
|  Location update frequency:                                             |
|  * Every 4 seconds while on delivery                                    |
|                                                                         |
|  Location updates per second:                                           |
|  * 300,000 / 4 = 75,000 location updates/second                         |
|                                                                         |
|  This is the HIGHEST throughput requirement!                            |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  STORAGE ESTIMATION                                                     |
|                                                                         |
|  Orders:                                                                |
|  * 3M orders/day x 5 KB per order = 15 GB/day                           |
|  * Per year: 15 GB x 365 = 5.5 TB/year                                  |
|                                                                         |
|  Location data (if stored):                                             |
|  * 75K updates/second x 100 bytes = 7.5 MB/second                       |
|  * Per day: 7.5 MB x 86400 = 650 GB/day                                 |
|  * Usually stored only for active deliveries, purged after              |
|                                                                         |
|  Restaurant/Menu data:                                                  |
|  * 500K restaurants x 100 menu items x 1 KB = 50 GB                     |
|  * Relatively static, easily cacheable                                  |
|                                                                         |
|  Images:                                                                |
|  * 500K restaurants x 100 items x 500 KB avg = 25 TB                    |
|  * Stored on CDN/Object storage                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5: ORDER LIFECYCLE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ORDER STATE MACHINE                                                    |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |                      ORDER LIFECYCLE                              |  |
|  |                                                                   |  |
|  |   +---------+                                                     |  |
|  |   |  CART   | <-- Customer adds items                             |  |
|  |   +----+----+                                                     |  |
|  |        | Place Order                                              |  |
|  |        v                                                          |  |
|  |   +---------+                                                     |  |
|  |   | PLACED  | <-- Payment captured                                |  |
|  |   +----+----+                                                     |  |
|  |        | Restaurant receives                                      |  |
|  |        v                                                          |  |
|  |   +---------+     +---------+                                     |  |
|  |   |CONFIRMED|---->|REJECTED | (Restaurant rejects)                |  |
|  |   +----+----+     +---------+                                     |  |
|  |        | Start preparing                                          |  |
|  |        v                                                          |  |
|  |   +----------+                                                    |  |
|  |   |PREPARING | <-- Kitchen working                                |  |
|  |   +----+-----+                                                    |  |
|  |        | Mark ready                                               |  |
|  |        v                                                          |  |
|  |   +-------------+                                                 |  |
|  |   |READY_PICKUP | <-- Waiting for delivery partner                |  |
|  |   +------+------+                                                 |  |
|  |          | Partner picks up                                       |  |
|  |          v                                                        |  |
|  |   +-------------+                                                 |  |
|  |   |  PICKED_UP  | <-- Food collected by partner                   |  |
|  |   +------+------+                                                 |  |
|  |          | Partner delivers                                       |  |
|  |          v                                                        |  |
|  |   +-------------+                                                 |  |
|  |   |  DELIVERED  | <-- Order complete!                             |  |
|  |   +-------------+                                                 |  |
|  |                                                                   |  |
|  |   Alternate paths:                                                |  |
|  |   * CANCELLED (customer/restaurant/system)                        |  |
|  |   * REFUNDED                                                      |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  TYPICAL TIMELINE                                                       |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  T+0        Order placed                                          |  |
|  |  T+30s      Restaurant confirms                                   |  |
|  |  T+1min     Delivery partner assigned                             |  |
|  |  T+5min     Partner reaches restaurant                            |  |
|  |  T+15min    Food ready, picked up                                 |  |
|  |  T+30min    Delivered to customer                                 |  |
|  |                                                                   |  |
|  |  Total: 25-40 minutes (varies by distance/restaurant)             |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

END OF PART 1
