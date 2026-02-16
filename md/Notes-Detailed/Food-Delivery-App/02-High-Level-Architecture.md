# FOOD DELIVERY PLATFORM SYSTEM DESIGN

PART 2: HIGH-LEVEL ARCHITECTURE
SECTION 1: SYSTEM OVERVIEW
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  HIGH-LEVEL ARCHITECTURE                                               |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |   +----------+   +----------+   +--------------+              |  |*
*|  |   | Customer |   |Restaurant|   |   Delivery   |              |  |*
*|  |   |   App    |   |   App    |   | Partner App  |              |  |*
*|  |   +----+-----+   +----+-----+   +------+-------+              |  |*
*|  |        |              |                |                       |  |*
*|  |        +--------------+----------------+                       |  |*
*|  |                       |                                         |  |*
*|  |                       v                                         |  |*
*|  |               +---------------+                                |  |*
*|  |               |      CDN      | <-- Images, Static Assets    |  |*
*|  |               +-------+-------+                                |  |*
*|  |                       |                                         |  |*
*|  |                       v                                         |  |*
*|  |               +---------------+                                |  |*
*|  |               | API GATEWAY   |                                |  |*
*|  |               |               |                                |  |*
*|  |               | * Auth        |                                |  |*
*|  |               | * Rate Limit  |                                |  |*
*|  |               | * Routing     |                                |  |*
*|  |               +-------+-------+                                |  |*
*|  |                       |                                         |  |*
*|  |    +------------------+------------------+                    |  |*
*|  |    |                  |                  |                    |  |*
*|  |    v                  v                  v                    |  |*
*|  |  +--------+     +----------+      +----------+               |  |*
*|  |  | User   |     | Order    |      | Location |               |  |*
*|  |  |Service |     | Service  |      | Service  |               |  |*
*|  |  +--------+     +----------+      +----------+               |  |*
*|  |                                                                 |  |*
*|  |  +--------+     +----------+      +----------+               |  |*
*|  |  |Restaur.|     | Search   |      | Delivery |               |  |*
*|  |  |Service |     | Service  |      | Service  |               |  |*
*|  |  +--------+     +----------+      +----------+               |  |*
*|  |                                                                 |  |*
*|  |  +--------+     +----------+      +----------+               |  |*
*|  |  |Payment |     |  Rating  |      |  Notif.  |               |  |*
*|  |  |Service |     | Service  |      | Service  |               |  |*
*|  |  +--------+     +----------+      +----------+               |  |*
*|  |                       |                                         |  |*
*|  |    +------------------+------------------+                    |  |*
*|  |    |                  |                  |                    |  |*
*|  |    v                  v                  v                    |  |*
*|  |  +--------+     +----------+      +----------+               |  |*
*|  |  | MySQL  |     |  Redis   |      |   Kafka  |               |  |*
*|  |  |Cluster |     | Cluster  |      |          |               |  |*
*|  |  +--------+     +----------+      +----------+               |  |*
*|  |                                                                 |  |*
*|  |  +--------+     +----------+      +----------+               |  |*
*|  |  |Elastic |     |  Mongo   |      | InfluxDB |               |  |*
*|  |  |search  |     |   DB     |      |(Metrics) |               |  |*
*|  |  +--------+     +----------+      +----------+               |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 2: CORE MICROSERVICES
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  SERVICE RESPONSIBILITIES                                              |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  1. USER SERVICE                                               |  |*
*|  |     -----------------                                           |  |*
*|  |     * Customer registration/login                              |  |*
*|  |     * Profile management                                       |  |*
*|  |     * Address management (saved locations)                    |  |*
*|  |     * Authentication (JWT tokens)                             |  |*
*|  |     * User preferences                                        |  |*
*|  |                                                                 |  |*
*|  |     Database: MySQL (users, addresses tables)                 |  |*
*|  |     Cache: Redis (session, user profile)                      |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  2. RESTAURANT SERVICE                                         |  |*
*|  |     -----------------------                                     |  |*
*|  |     * Restaurant onboarding                                    |  |*
*|  |     * Menu management (CRUD)                                   |  |*
*|  |     * Item availability toggle                                |  |*
*|  |     * Restaurant timings/status                               |  |*
*|  |     * Category management                                      |  |*
*|  |                                                                 |  |*
*|  |     Database: MySQL (restaurants, menus, items)               |  |*
*|  |     Cache: Redis (menu cache per restaurant)                  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  3. SEARCH SERVICE                                             |  |*
*|  |     ------------------                                          |  |*
*|  |     * Restaurant search by location                           |  |*
*|  |     * Full-text search (dish, cuisine, restaurant)           |  |*
*|  |     * Filtering (rating, price, time)                        |  |*
*|  |     * Sorting (relevance, distance, rating)                  |  |*
*|  |     * Personalized recommendations                            |  |*
*|  |                                                                 |  |*
*|  |     Database: Elasticsearch                                    |  |*
*|  |     Geospatial: Elasticsearch geo_point                       |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  4. ORDER SERVICE (Most Complex!)                             |  |*
*|  |     ---------------------------------                           |  |*
*|  |     * Cart management                                          |  |*
*|  |     * Order creation                                           |  |*
*|  |     * Order state management                                   |  |*
*|  |     * Price calculation                                        |  |*
*|  |     * Coupon/offer application                                |  |*
*|  |     * Order history                                            |  |*
*|  |                                                                 |  |*
*|  |     Database: MySQL (orders, order_items)                     |  |*
*|  |     Cache: Redis (cart, active orders)                        |  |*
*|  |     Events: Kafka (order state changes)                       |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  5. DELIVERY SERVICE                                           |  |*
*|  |     --------------------                                        |  |*
*|  |     * Delivery partner management                             |  |*
*|  |     * Partner assignment algorithm                            |  |*
*|  |     * Delivery tracking                                        |  |*
*|  |     * Route optimization                                       |  |*
*|  |     * Partner earnings calculation                            |  |*
*|  |                                                                 |  |*
*|  |     Database: MySQL (delivery_partners, deliveries)          |  |*
*|  |     Cache: Redis (online partners, assignments)              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  6. LOCATION SERVICE (Highest Throughput!)                    |  |*
*|  |     --------------------------------------                      |  |*
*|  |     * Receive location updates (75K/second)                   |  |*
*|  |     * Store current location                                   |  |*
*|  |     * Find nearby partners for assignment                     |  |*
*|  |     * Calculate ETA                                            |  |*
*|  |     * Stream location to customers                            |  |*
*|  |                                                                 |  |*
*|  |     Database: Redis (current location only)                   |  |*
*|  |     Geospatial: Redis GEO commands                            |  |*
*|  |     Alternative: Custom quadtree/geohash                      |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  7. PAYMENT SERVICE                                            |  |*
*|  |     ---------------------                                       |  |*
*|  |     * Payment processing                                       |  |*
*|  |     * Wallet management                                        |  |*
*|  |     * Refunds                                                   |  |*
*|  |     * Invoice generation                                       |  |*
*|  |     * Restaurant/Partner payouts                              |  |*
*|  |                                                                 |  |*
*|  |     Database: MySQL (transactions, wallets)                   |  |*
*|  |     External: Payment gateway (Razorpay, Stripe)             |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  8. NOTIFICATION SERVICE                                       |  |*
*|  |     ------------------------                                    |  |*
*|  |     * Push notifications (FCM/APNs)                           |  |*
*|  |     * SMS notifications                                        |  |*
*|  |     * Email notifications                                      |  |*
*|  |     * In-app notifications                                    |  |*
*|  |     * Real-time updates (WebSocket)                          |  |*
*|  |                                                                 |  |*
*|  |     Queue: Kafka (notification events)                        |  |*
*|  |     External: Twilio (SMS), Firebase (Push)                  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  9. RATING SERVICE                                             |  |*
*|  |     ------------------                                          |  |*
*|  |     * Restaurant ratings/reviews                              |  |*
*|  |     * Delivery partner ratings                                |  |*
*|  |     * Dish ratings                                             |  |*
*|  |     * Aggregate rating calculation                            |  |*
*|  |                                                                 |  |*
*|  |     Database: MongoDB (flexible schema for reviews)          |  |*
*|  |     Cache: Redis (aggregate ratings)                          |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  10. PRICING SERVICE                                           |  |*
*|  |      -----------------                                          |  |*
*|  |      * Surge pricing during peak hours                        |  |*
*|  |      * Delivery fee calculation                               |  |*
*|  |      * Coupon management                                       |  |*
*|  |      * Restaurant commission                                   |  |*
*|  |      * Dynamic pricing rules                                   |  |*
*|  |                                                                 |  |*
*|  |      Database: MySQL (pricing_rules, coupons)                 |  |*
*|  |      Cache: Redis (active coupons, surge zones)              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 3: DATABASE DESIGN
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  CORE TABLES                                                           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TABLE: users                                                  |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | Column          | Type          | Description            | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | user_id         | BIGINT (PK)   | Unique identifier      | |  |*
*|  |  | phone           | VARCHAR(15)   | Primary login          | |  |*
*|  |  | email           | VARCHAR(255)  | Optional               | |  |*
*|  |  | name            | VARCHAR(100)  | Display name           | |  |*
*|  |  | created_at      | TIMESTAMP     | Registration time      | |  |*
*|  |  | last_login      | TIMESTAMP     | Last activity          | |  |*
*|  |  | status          | ENUM          | ACTIVE, BLOCKED        | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TABLE: addresses                                              |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | address_id      | BIGINT (PK)   | Unique identifier      | |  |*
*|  |  | user_id         | BIGINT (FK)   | Owner                  | |  |*
*|  |  | label           | VARCHAR(50)   | Home, Work, Other      | |  |*
*|  |  | address_line    | VARCHAR(500)  | Full address           | |  |*
*|  |  | latitude        | DECIMAL(10,8) | Geo coordinate         | |  |*
*|  |  | longitude       | DECIMAL(11,8) | Geo coordinate         | |  |*
*|  |  | landmark        | VARCHAR(200)  | Delivery instructions  | |  |*
*|  |  | is_default      | BOOLEAN       | Primary address        | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TABLE: restaurants                                            |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | restaurant_id   | BIGINT (PK)   | Unique identifier      | |  |*
*|  |  | name            | VARCHAR(200)  | Restaurant name        | |  |*
*|  |  | description     | TEXT          | About                  | |  |*
*|  |  | latitude        | DECIMAL(10,8) | Location               | |  |*
*|  |  | longitude       | DECIMAL(11,8) | Location               | |  |*
*|  |  | address         | VARCHAR(500)  | Full address           | |  |*
*|  |  | phone           | VARCHAR(15)   | Contact                | |  |*
*|  |  | cuisine_type    | VARCHAR(100)  | Indian, Chinese, etc.  | |  |*
*|  |  | avg_rating      | DECIMAL(2,1)  | 1.0 - 5.0              | |  |*
*|  |  | total_ratings   | INT           | Review count           | |  |*
*|  |  | avg_prep_time   | INT           | Minutes                | |  |*
*|  |  | is_veg_only     | BOOLEAN       | Veg restaurant         | |  |*
*|  |  | is_active       | BOOLEAN       | Accepting orders       | |  |*
*|  |  | commission_pct  | DECIMAL(4,2)  | Platform commission    | |  |*
*|  |  | opening_time    | TIME          | Daily open time        | |  |*
*|  |  | closing_time    | TIME          | Daily close time       | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |                                                                 |  |*
*|  |  INDEXES:                                                      |  |*
*|  |  * (latitude, longitude) - Geospatial lookup                  |  |*
*|  |  * (cuisine_type) - Filter by cuisine                         |  |*
*|  |  * (is_active, avg_rating DESC) - Sort by rating             |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TABLE: menu_items                                             |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | item_id         | BIGINT (PK)   | Unique identifier      | |  |*
*|  |  | restaurant_id   | BIGINT (FK)   | Parent restaurant      | |  |*
*|  |  | category_id     | BIGINT (FK)   | Menu category          | |  |*
*|  |  | name            | VARCHAR(200)  | Item name              | |  |*
*|  |  | description     | TEXT          | Item description       | |  |*
*|  |  | price           | DECIMAL(10,2) | Base price             | |  |*
*|  |  | image_url       | VARCHAR(500)  | CDN URL                | |  |*
*|  |  | is_veg          | BOOLEAN       | Veg/Non-veg            | |  |*
*|  |  | is_available    | BOOLEAN       | In stock               | |  |*
*|  |  | is_bestseller   | BOOLEAN       | Popular item           | |  |*
*|  |  | prep_time_mins  | INT           | Preparation time       | |  |*
*|  |  | calories        | INT           | Nutritional info       | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |                                                                 |  |*
*|  |  TABLE: item_variants (Size: Small/Medium/Large)              |  |*
*|  |  TABLE: item_addons (Extra cheese, toppings)                  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TABLE: orders                                                 |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | order_id        | BIGINT (PK)   | Unique identifier      | |  |*
*|  |  | user_id         | BIGINT (FK)   | Customer               | |  |*
*|  |  | restaurant_id   | BIGINT (FK)   | Restaurant             | |  |*
*|  |  | delivery_partner| BIGINT (FK)   | Assigned partner       | |  |*
*|  |  | address_id      | BIGINT (FK)   | Delivery location      | |  |*
*|  |  | status          | ENUM          | Order state            | |  |*
*|  |  | subtotal        | DECIMAL(10,2) | Item total             | |  |*
*|  |  | delivery_fee    | DECIMAL(10,2) | Delivery charge        | |  |*
*|  |  | discount        | DECIMAL(10,2) | Coupon discount        | |  |*
*|  |  | taxes           | DECIMAL(10,2) | GST etc.               | |  |*
*|  |  | total           | DECIMAL(10,2) | Final amount           | |  |*
*|  |  | payment_method  | ENUM          | CARD, UPI, WALLET, COD | |  |*
*|  |  | payment_status  | ENUM          | PENDING, PAID, FAILED  | |  |*
*|  |  | special_instr   | TEXT          | Customer notes         | |  |*
*|  |  | created_at      | TIMESTAMP     | Order placed time      | |  |*
*|  |  | confirmed_at    | TIMESTAMP     | Restaurant confirmed   | |  |*
*|  |  | picked_up_at    | TIMESTAMP     | Partner picked up      | |  |*
*|  |  | delivered_at    | TIMESTAMP     | Order delivered        | |  |*
*|  |  | estimated_time  | TIMESTAMP     | Expected delivery      | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |                                                                 |  |*
*|  |  INDEXES:                                                      |  |*
*|  |  * (user_id, created_at DESC) - User order history            |  |*
*|  |  * (restaurant_id, status) - Restaurant active orders         |  |*
*|  |  * (delivery_partner, status) - Partner active orders        |  |*
*|  |  * (status, created_at) - Processing queue                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TABLE: order_items                                            |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | order_item_id   | BIGINT (PK)   | Unique identifier      | |  |*
*|  |  | order_id        | BIGINT (FK)   | Parent order           | |  |*
*|  |  | item_id         | BIGINT (FK)   | Menu item              | |  |*
*|  |  | quantity        | INT           | Number ordered         | |  |*
*|  |  | unit_price      | DECIMAL(10,2) | Price at order time    | |  |*
*|  |  | total_price     | DECIMAL(10,2) | quantity × unit_price  | |  |*
*|  |  | variant_id      | BIGINT (FK)   | Size selection         | |  |*
*|  |  | addons          | JSON          | Selected add-ons       | |  |*
*|  |  | special_instr   | VARCHAR(500)  | Item-level notes       | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TABLE: delivery_partners                                      |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | partner_id      | BIGINT (PK)   | Unique identifier      | |  |*
*|  |  | name            | VARCHAR(100)  | Partner name           | |  |*
*|  |  | phone           | VARCHAR(15)   | Contact number         | |  |*
*|  |  | email           | VARCHAR(255)  | Email                  | |  |*
*|  |  | vehicle_type    | ENUM          | BIKE, SCOOTER, CAR     | |  |*
*|  |  | vehicle_number  | VARCHAR(20)   | License plate          | |  |*
*|  |  | license_number  | VARCHAR(50)   | Driving license        | |  |*
*|  |  | rating          | DECIMAL(2,1)  | Average rating         | |  |*
*|  |  | total_deliveries| INT           | Completed orders       | |  |*
*|  |  | status          | ENUM          | ONLINE, OFFLINE, BUSY  | |  |*
*|  |  | current_lat     | DECIMAL(10,8) | Current location       | |  |*
*|  |  | current_lng     | DECIMAL(11,8) | Current location       | |  |*
*|  |  | created_at      | TIMESTAMP     | Onboarding date        | |  |*
*|  |  | is_verified     | BOOLEAN       | Documents verified     | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 4: API DESIGN
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  CUSTOMER APIs                                                         |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  SEARCH & BROWSE                                               |  |*
*|  |  ------------------                                             |  |*
*|  |                                                                 |  |*
*|  |  GET /api/restaurants                                          |  |*
*|  |  Query: lat, lng, radius, cuisine, sort, rating_min           |  |*
*|  |  Response: { restaurants: [...], total, page_info }           |  |*
*|  |                                                                 |  |*
*|  |  GET /api/restaurants/{id}                                    |  |*
*|  |  Response: { restaurant details, menu, offers }               |  |*
*|  |                                                                 |  |*
*|  |  GET /api/restaurants/{id}/menu                               |  |*
*|  |  Response: { categories: [{ items: [...] }] }                 |  |*
*|  |                                                                 |  |*
*|  |  GET /api/search                                              |  |*
*|  |  Query: q (search term), lat, lng                             |  |*
*|  |  Response: { restaurants: [...], dishes: [...] }              |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  CART                                                          |  |*
*|  |  -----                                                          |  |*
*|  |                                                                 |  |*
*|  |  GET /api/cart                                                 |  |*
*|  |  Response: { items: [...], subtotal, restaurant_id }          |  |*
*|  |                                                                 |  |*
*|  |  POST /api/cart/items                                          |  |*
*|  |  Body: { item_id, quantity, variant_id, addons }              |  |*
*|  |                                                                 |  |*
*|  |  PUT /api/cart/items/{item_id}                                |  |*
*|  |  Body: { quantity }                                            |  |*
*|  |                                                                 |  |*
*|  |  DELETE /api/cart/items/{item_id}                             |  |*
*|  |                                                                 |  |*
*|  |  DELETE /api/cart (clear cart)                                |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  ORDERS                                                        |  |*
*|  |  -------                                                        |  |*
*|  |                                                                 |  |*
*|  |  POST /api/orders                                              |  |*
*|  |  Body: {                                                       |  |*
*|  |    address_id,                                                 |  |*
*|  |    payment_method,                                             |  |*
*|  |    coupon_code,                                                |  |*
*|  |    special_instructions                                        |  |*
*|  |  }                                                              |  |*
*|  |  Response: { order_id, payment_info, estimated_time }         |  |*
*|  |                                                                 |  |*
*|  |  GET /api/orders/{id}                                          |  |*
*|  |  Response: { order details, status, tracking_info }           |  |*
*|  |                                                                 |  |*
*|  |  GET /api/orders                                               |  |*
*|  |  Response: { orders: [...], pagination }                      |  |*
*|  |                                                                 |  |*
*|  |  POST /api/orders/{id}/cancel                                 |  |*
*|  |  Body: { reason }                                              |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  TRACKING (WebSocket)                                         |  |*
*|  |  ---------------------                                         |  |*
*|  |                                                                 |  |*
*|  |  WS /ws/orders/{id}/track                                     |  |*
*|  |  Events:                                                       |  |*
*|  |    * status_update (status changed)                          |  |*
*|  |    * location_update (partner location)                      |  |*
*|  |    * eta_update (new ETA)                                    |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  RESTAURANT APIs                                               |  |*
*|  |  --------------------                                           |  |*
*|  |                                                                 |  |*
*|  |  GET /api/restaurant/orders (pending orders)                  |  |*
*|  |  POST /api/restaurant/orders/{id}/accept                      |  |*
*|  |  POST /api/restaurant/orders/{id}/reject                      |  |*
*|  |  POST /api/restaurant/orders/{id}/ready                       |  |*
*|  |                                                                 |  |*
*|  |  PUT /api/restaurant/menu/items/{id}/availability            |  |*
*|  |  Body: { is_available: true/false }                          |  |*
*|  |                                                                 |  |*
*|  |  PUT /api/restaurant/status                                   |  |*
*|  |  Body: { is_accepting_orders: true/false }                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  DELIVERY PARTNER APIs                                         |  |*
*|  |  -------------------------                                      |  |*
*|  |                                                                 |  |*
*|  |  PUT /api/partner/status                                      |  |*
*|  |  Body: { status: ONLINE/OFFLINE }                            |  |*
*|  |                                                                 |  |*
*|  |  PUT /api/partner/location                                    |  |*
*|  |  Body: { latitude, longitude, timestamp }                    |  |*
*|  |  (Called every 3-5 seconds)                                   |  |*
*|  |                                                                 |  |*
*|  |  GET /api/partner/delivery-requests                          |  |*
*|  |  Response: { pending delivery requests }                      |  |*
*|  |                                                                 |  |*
*|  |  POST /api/partner/deliveries/{id}/accept                    |  |*
*|  |  POST /api/partner/deliveries/{id}/reject                    |  |*
*|  |  POST /api/partner/deliveries/{id}/picked-up                 |  |*
*|  |  POST /api/partner/deliveries/{id}/delivered                 |  |*
*|  |                                                                 |  |*
*|  |  GET /api/partner/earnings                                    |  |*
*|  |  Response: { today, week, month, withdrawable }              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

END OF PART 2
