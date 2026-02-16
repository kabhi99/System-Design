# FOOD DELIVERY PLATFORM SYSTEM DESIGN

PART 4: ORDER FLOW, PAYMENT & SEARCH
SECTION 1: DETAILED ORDER FLOW
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  COMPLETE ORDER PLACEMENT FLOW                                         |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Customer App: Checkout                                        |  |*
*|  |         |                                                       |  |*
*|  |         | POST /api/orders                                     |  |*
*|  |         | { cart_id, address_id, payment_method, coupon }     |  |*
*|  |         |                                                       |  |*
*|  |         v                                                       |  |*
*|  |  +----------------------------------------------------------+ |  |*
*|  |  |                    ORDER SERVICE                         | |  |*
*|  |  |                                                          | |  |*
*|  |  |  1. VALIDATE                                            | |  |*
*|  |  |     * Cart not empty                                    | |  |*
*|  |  |     * Restaurant is open                                | |  |*
*|  |  |     * All items still available                        | |  |*
*|  |  |     * Delivery address in service area                 | |  |*
*|  |  |     * Minimum order value met                          | |  |*
*|  |  |                                                          | |  |*
*|  |  |  2. CALCULATE PRICING                                   | |  |*
*|  |  |     +-- Item subtotal                                  | |  |*
*|  |  |     +-- Apply coupon discount                          | |  |*
*|  |  |     +-- Calculate delivery fee                         | |  |*
*|  |  |     +-- Apply surge pricing (if applicable)           | |  |*
*|  |  |     +-- Calculate taxes (GST)                          | |  |*
*|  |  |     +-- Final total                                    | |  |*
*|  |  |                                                          | |  |*
*|  |  |  3. RESERVE INVENTORY (Soft lock)                      | |  |*
*|  |  |     * Decrement available count temporarily            | |  |*
*|  |  |     * Release after 10 mins if payment fails           | |  |*
*|  |  |                                                          | |  |*
*|  |  |  4. CREATE ORDER (Status: PENDING_PAYMENT)             | |  |*
*|  |  |     * Generate order_id                                | |  |*
*|  |  |     * Store order details                              | |  |*
*|  |  |                                                          | |  |*
*|  |  +------------------------+---------------------------------+ |  |*
*|  |                           |                                   |  |*
*|  |                           v                                   |  |*
*|  |  +----------------------------------------------------------+ |  |*
*|  |  |                   PAYMENT SERVICE                        | |  |*
*|  |  |                                                          | |  |*
*|  |  |  If PREPAID (Card/UPI/Wallet):                         | |  |*
*|  |  |  1. Initiate payment with gateway (Razorpay)           | |  |*
*|  |  |  2. Return payment link/intent to customer             | |  |*
*|  |  |  3. Customer completes payment                         | |  |*
*|  |  |  4. Receive webhook from gateway                       | |  |*
*|  |  |  5. Verify signature, update status                    | |  |*
*|  |  |                                                          | |  |*
*|  |  |  If COD:                                                | |  |*
*|  |  |  1. Skip payment gateway                               | |  |*
*|  |  |  2. Mark payment_status = COD_PENDING                  | |  |*
*|  |  |                                                          | |  |*
*|  |  +------------------------+---------------------------------+ |  |*
*|  |                           |                                   |  |*
*|  |                           v                                   |  |*
*|  |  +----------------------------------------------------------+ |  |*
*|  |  |              ORDER CONFIRMED (Status: PLACED)            | |  |*
*|  |  |                                                          | |  |*
*|  |  |  1. Update order status = PLACED                       | |  |*
*|  |  |  2. Publish event to Kafka: order-placed               | |  |*
*|  |  |  3. Return order confirmation to customer              | |  |*
*|  |  |                                                          | |  |*
*|  |  +----------------------------------------------------------+ |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  ASYNC PROCESSING (After Order Placed)                                |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Kafka: order-placed event                                     |  |*
*|  |         |                                                       |  |*
*|  |         +--> Restaurant Service                                |  |*
*|  |         |    * Send push notification to restaurant app       |  |*
*|  |         |    * Play alert sound                                |  |*
*|  |         |    * Show order on tablet                           |  |*
*|  |         |                                                       |  |*
*|  |         +--> Notification Service                              |  |*
*|  |         |    * Send confirmation SMS to customer              |  |*
*|  |         |    * Send push notification                         |  |*
*|  |         |                                                       |  |*
*|  |         +--> Analytics Service                                 |  |*
*|  |              * Record order metrics                           |  |*
*|  |              * Update restaurant stats                        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  RESTAURANT CONFIRMATION FLOW                                         |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Restaurant receives order notification                        |  |*
*|  |         |                                                       |  |*
*|  |         | Has 3 minutes to accept/reject                      |  |*
*|  |         |                                                       |  |*
*|  |         +--> ACCEPT                                            |  |*
*|  |         |    |                                                 |  |*
*|  |         |    v                                                 |  |*
*|  |         |    Update order status = CONFIRMED                   |  |*
*|  |         |    Publish: order-confirmed                         |  |*
*|  |         |         |                                            |  |*
*|  |         |         +--> Delivery Service                       |  |*
*|  |         |              Start partner assignment               |  |*
*|  |         |                                                       |  |*
*|  |         +--> REJECT                                            |  |*
*|  |         |    |                                                 |  |*
*|  |         |    v                                                 |  |*
*|  |         |    Update order status = RESTAURANT_REJECTED        |  |*
*|  |         |    Trigger refund process                           |  |*
*|  |         |    Notify customer with alternatives                |  |*
*|  |         |                                                       |  |*
*|  |         +--> TIMEOUT (3 mins)                                  |  |*
*|  |              |                                                 |  |*
*|  |              v                                                 |  |*
*|  |              Auto-confirm OR auto-reject based on settings    |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 2: PAYMENT ARCHITECTURE
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  PAYMENT FLOW                                                          |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Customer                                                       |  |*
*|  |     |                                                           |  |*
*|  |     | 1. POST /api/orders                                      |  |*
*|  |     |    { payment_method: "upi" }                             |  |*
*|  |     |                                                           |  |*
*|  |     v                                                           |  |*
*|  |  Order Service                                                  |  |*
*|  |     |                                                           |  |*
*|  |     | 2. Create order (PENDING_PAYMENT)                        |  |*
*|  |     | 3. Request payment link                                  |  |*
*|  |     |                                                           |  |*
*|  |     v                                                           |  |*
*|  |  Payment Service                                                |  |*
*|  |     |                                                           |  |*
*|  |     | 4. Create payment intent                                 |  |*
*|  |     |    POST https://api.razorpay.com/v1/orders              |  |*
*|  |     |    { amount, currency, receipt }                        |  |*
*|  |     |                                                           |  |*
*|  |     v                                                           |  |*
*|  |  Razorpay (Payment Gateway)                                    |  |*
*|  |     |                                                           |  |*
*|  |     | 5. Returns: { order_id, key_id }                        |  |*
*|  |     |                                                           |  |*
*|  |     v                                                           |  |*
*|  |  Customer App                                                   |  |*
*|  |     |                                                           |  |*
*|  |     | 6. Opens payment UI (UPI/Card)                          |  |*
*|  |     | 7. Completes payment                                     |  |*
*|  |     |                                                           |  |*
*|  |     v                                                           |  |*
*|  |  Razorpay -> Webhook                                            |  |*
*|  |     |                                                           |  |*
*|  |     | 8. POST /webhooks/razorpay                              |  |*
*|  |     |    { event: "payment.captured", ... }                   |  |*
*|  |     |                                                           |  |*
*|  |     v                                                           |  |*
*|  |  Payment Service                                                |  |*
*|  |     |                                                           |  |*
*|  |     | 9. Verify webhook signature                             |  |*
*|  |     | 10. Update payment status                               |  |*
*|  |     | 11. Publish: payment-success event                      |  |*
*|  |     |                                                           |  |*
*|  |     v                                                           |  |*
*|  |  Order Service                                                  |  |*
*|  |     |                                                           |  |*
*|  |     | 12. Update order status = PLACED                        |  |*
*|  |     |                                                           |  |*
*|  |     v                                                           |  |*
*|  |  Continue order flow...                                        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  PAYMENT DATABASE SCHEMA                                               |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TABLE: transactions                                           |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | txn_id          | VARCHAR (PK)  | Unique transaction ID  | |  |*
*|  |  | order_id        | BIGINT (FK)   | Related order          | |  |*
*|  |  | user_id         | BIGINT (FK)   | Customer               | |  |*
*|  |  | amount          | DECIMAL(10,2) | Payment amount         | |  |*
*|  |  | currency        | VARCHAR(3)    | INR, USD               | |  |*
*|  |  | payment_method  | ENUM          | CARD, UPI, WALLET, COD | |  |*
*|  |  | status          | ENUM          | PENDING, SUCCESS, FAIL | |  |*
*|  |  | gateway_txn_id  | VARCHAR       | Razorpay payment_id    | |  |*
*|  |  | gateway_order_id| VARCHAR       | Razorpay order_id      | |  |*
*|  |  | created_at      | TIMESTAMP     | Initiation time        | |  |*
*|  |  | completed_at    | TIMESTAMP     | Completion time        | |  |*
*|  |  | error_code      | VARCHAR       | If failed              | |  |*
*|  |  | error_message   | VARCHAR       | If failed              | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |                                                                 |  |*
*|  |  TABLE: wallets                                                |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | wallet_id       | BIGINT (PK)   | Unique ID              | |  |*
*|  |  | user_id         | BIGINT (FK)   | Owner                  | |  |*
*|  |  | balance         | DECIMAL(10,2) | Current balance        | |  |*
*|  |  | updated_at      | TIMESTAMP     | Last update            | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  REFUND HANDLING                                                       |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Refund Triggers:                                              |  |*
*|  |  * Restaurant rejected order                                   |  |*
*|  |  * Customer cancelled (if allowed)                            |  |*
*|  |  * Order not delivered (partner issue)                        |  |*
*|  |  * Customer complaint approved                                 |  |*
*|  |                                                                 |  |*
*|  |  Refund Flow:                                                  |  |*
*|  |  1. Calculate refund amount                                    |  |*
*|  |     * Full refund: before restaurant confirms                 |  |*
*|  |     * Partial refund: after food prepared                     |  |*
*|  |                                                                 |  |*
*|  |  2. Choose refund method                                       |  |*
*|  |     * Source refund (back to card/UPI)                        |  |*
*|  |     * Wallet credit (instant, preferred)                      |  |*
*|  |                                                                 |  |*
*|  |  3. Process refund                                             |  |*
*|  |     POST https://api.razorpay.com/v1/payments/{id}/refund    |  |*
*|  |                                                                 |  |*
*|  |  4. Update records                                             |  |*
*|  |     * Create refund transaction                               |  |*
*|  |     * Update order status                                     |  |*
*|  |     * Notify customer                                         |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 3: SEARCH SERVICE
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  SEARCH ARCHITECTURE                                                   |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Customer Search Query                                         |  |*
*|  |  "pizza near me"                                               |  |*
*|  |         |                                                       |  |*
*|  |         v                                                       |  |*
*|  |  +----------------------------------------------------------+ |  |*
*|  |  |                   SEARCH SERVICE                         | |  |*
*|  |  |                                                          | |  |*
*|  |  |  1. Parse query                                         | |  |*
*|  |  |     * Keywords: "pizza"                                 | |  |*
*|  |  |     * Intent: find restaurants                          | |  |*
*|  |  |                                                          | |  |*
*|  |  |  2. Enrich with context                                 | |  |*
*|  |  |     * User location: (12.97, 77.59)                    | |  |*
*|  |  |     * Time: 8 PM (dinner)                              | |  |*
*|  |  |     * User preferences (veg, past orders)              | |  |*
*|  |  |                                                          | |  |*
*|  |  +------------------------+---------------------------------+ |  |*
*|  |                           |                                   |  |*
*|  |                           v                                   |  |*
*|  |  +----------------------------------------------------------+ |  |*
*|  |  |                   ELASTICSEARCH                          | |  |*
*|  |  |                                                          | |  |*
*|  |  |  Query:                                                 | |  |*
*|  |  |  {                                                       | |  |*
*|  |  |    "bool": {                                            | |  |*
*|  |  |      "must": [                                          | |  |*
*|  |  |        {                                                 | |  |*
*|  |  |          "multi_match": {                               | |  |*
*|  |  |            "query": "pizza",                            | |  |*
*|  |  |            "fields": ["name", "cuisine", "items.name"] | |  |*
*|  |  |          }                                               | |  |*
*|  |  |        },                                                | |  |*
*|  |  |        {                                                 | |  |*
*|  |  |          "geo_distance": {                              | |  |*
*|  |  |            "distance": "5km",                           | |  |*
*|  |  |            "location": { "lat": 12.97, "lon": 77.59 }  | |  |*
*|  |  |          }                                               | |  |*
*|  |  |        },                                                | |  |*
*|  |  |        { "term": { "is_active": true } },               | |  |*
*|  |  |        { "term": { "is_open": true } }                  | |  |*
*|  |  |      ]                                                   | |  |*
*|  |  |    },                                                    | |  |*
*|  |  |    "sort": [                                             | |  |*
*|  |  |      { "_score": "desc" },                              | |  |*
*|  |  |      { "rating": "desc" }                               | |  |*
*|  |  |    ]                                                     | |  |*
*|  |  |  }                                                       | |  |*
*|  |  |                                                          | |  |*
*|  |  +------------------------+---------------------------------+ |  |*
*|  |                           |                                   |  |*
*|  |                           v                                   |  |*
*|  |  +----------------------------------------------------------+ |  |*
*|  |  |                   POST PROCESSING                        | |  |*
*|  |  |                                                          | |  |*
*|  |  |  * Calculate delivery ETA for each restaurant          | |  |*
*|  |  |  * Get current offers/discounts                        | |  |*
*|  |  |  * Add "Promoted" restaurants (paid placement)         | |  |*
*|  |  |  * Personalize ranking based on user history           | |  |*
*|  |  |                                                          | |  |*
*|  |  +------------------------------------------------------------+ |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  ELASTICSEARCH INDEX SCHEMA                                           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Index: restaurants                                            |  |*
*|  |                                                                 |  |*
*|  |  {                                                              |  |*
*|  |    "restaurant_id": 123,                                       |  |*
*|  |    "name": "Pizza Palace",                                     |  |*
*|  |    "description": "Best pizzas in town",                       |  |*
*|  |    "cuisine_types": ["italian", "pizza", "fast-food"],        |  |*
*|  |    "location": {                                               |  |*
*|  |      "lat": 12.9716,                                          |  |*
*|  |      "lon": 77.5946                                           |  |*
*|  |    },                                                           |  |*
*|  |    "address": "123 MG Road, Bangalore",                        |  |*
*|  |    "rating": 4.2,                                               |  |*
*|  |    "rating_count": 1500,                                       |  |*
*|  |    "price_range": 2,  // 1-4 ($ to $$$$)                      |  |*
*|  |    "avg_delivery_time": 30,                                    |  |*
*|  |    "is_active": true,                                          |  |*
*|  |    "is_open": true,                                            |  |*
*|  |    "is_veg_only": false,                                       |  |*
*|  |    "tags": ["bestseller", "trending"],                        |  |*
*|  |    "items": [                                                   |  |*
*|  |      {                                                          |  |*
*|  |        "name": "Margherita Pizza",                            |  |*
*|  |        "description": "Classic cheese pizza",                 |  |*
*|  |        "price": 299,                                           |  |*
*|  |        "is_veg": true,                                         |  |*
*|  |        "is_bestseller": true                                  |  |*
*|  |      },                                                         |  |*
*|  |      // ... more items                                        |  |*
*|  |    ]                                                            |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  |  Mappings:                                                     |  |*
*|  |  * location: geo_point                                        |  |*
*|  |  * name: text + keyword                                       |  |*
*|  |  * cuisine_types: keyword[]                                   |  |*
*|  |  * items.name: text (nested)                                 |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  KEEPING SEARCH INDEX IN SYNC                                         |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Restaurant Service                                            |  |*
*|  |         |                                                       |  |*
*|  |         | Updates restaurant/menu                              |  |*
*|  |         |                                                       |  |*
*|  |         v                                                       |  |*
*|  |  +--------------+                                              |  |*
*|  |  |    MySQL     | (Source of truth)                           |  |*
*|  |  +------+-------+                                              |  |*
*|  |         |                                                       |  |*
*|  |         | CDC (Debezium) or Event                             |  |*
*|  |         |                                                       |  |*
*|  |         v                                                       |  |*
*|  |  +--------------+                                              |  |*
*|  |  |    Kafka     | restaurant-updates topic                    |  |*
*|  |  +------+-------+                                              |  |*
*|  |         |                                                       |  |*
*|  |         v                                                       |  |*
*|  |  +--------------+                                              |  |*
*|  |  |   Indexer    |                                              |  |*
*|  |  |   Service    |                                              |  |*
*|  |  +------+-------+                                              |  |*
*|  |         |                                                       |  |*
*|  |         v                                                       |  |*
*|  |  +--------------+                                              |  |*
*|  |  |Elasticsearch | (Search index)                              |  |*
*|  |  +--------------+                                              |  |*
*|  |                                                                 |  |*
*|  |  Latency: 1-5 seconds (acceptable for menu updates)           |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SEARCH RANKING FACTORS                                               |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Base Score:                                                   |  |*
*|  |  * Text relevance (TF-IDF)                                    |  |*
*|  |  * Proximity to user                                          |  |*
*|  |                                                                 |  |*
*|  |  Quality Signals:                                              |  |*
*|  |  * Restaurant rating (4.5 > 3.5)                              |  |*
*|  |  * Number of reviews                                          |  |*
*|  |  * Order volume (popular restaurants)                        |  |*
*|  |                                                                 |  |*
*|  |  Performance Signals:                                          |  |*
*|  |  * On-time delivery rate                                      |  |*
*|  |  * Cancellation rate                                          |  |*
*|  |  * Customer complaints                                        |  |*
*|  |                                                                 |  |*
*|  |  Personalization:                                              |  |*
*|  |  * User's past orders                                         |  |*
*|  |  * Cuisine preferences                                        |  |*
*|  |  * Price range preference                                     |  |*
*|  |                                                                 |  |*
*|  |  Business Factors:                                             |  |*
*|  |  * Paid promotions (ads)                                      |  |*
*|  |  * New restaurant boost                                       |  |*
*|  |  * Partner tier (exclusive partners)                         |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 4: CART SERVICE
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  CART ARCHITECTURE                                                     |*
*|                                                                         |*
*|  Cart is ephemeral - stored in Redis, not MySQL                       |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Key: cart:{user_id}                                          |  |*
*|  |  TTL: 7 days (auto-expire abandoned carts)                    |  |*
*|  |                                                                 |  |*
*|  |  Value (Hash):                                                 |  |*
*|  |  {                                                              |  |*
*|  |    "restaurant_id": "123",                                     |  |*
*|  |    "items": [                                                   |  |*
*|  |      {                                                          |  |*
*|  |        "item_id": "456",                                       |  |*
*|  |        "name": "Margherita Pizza",                            |  |*
*|  |        "quantity": 2,                                          |  |*
*|  |        "unit_price": 299,                                      |  |*
*|  |        "variant_id": "large",                                 |  |*
*|  |        "addons": ["extra_cheese"],                            |  |*
*|  |        "total_price": 698                                     |  |*
*|  |      },                                                         |  |*
*|  |      // more items                                             |  |*
*|  |    ],                                                           |  |*
*|  |    "subtotal": 898,                                            |  |*
*|  |    "created_at": "2024-01-15T20:00:00Z",                       |  |*
*|  |    "updated_at": "2024-01-15T20:05:00Z"                        |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  CART RULES                                                            |*
*|                                                                         |*
*|  1. Single Restaurant: Cart can only have items from ONE restaurant  |*
*|     * If user adds item from different restaurant:                    |*
*|       -> Prompt: "Clear cart and add this item?"                      |*
*|                                                                         |*
*|  2. Availability Check: Validate item availability on:               |*
*|     * Every add/update                                                |*
*|     * Checkout                                                        |*
*|     * If item unavailable -> remove from cart, notify user           |*
*|                                                                         |*
*|  3. Price Sync: Prices can change between add and checkout           |*
*|     * Store price at add time                                        |*
*|     * Re-validate at checkout                                        |*
*|     * If price changed -> notify user before proceeding              |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 5: PRICING & OFFERS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  PRICING COMPONENTS                                                    |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Order Summary:                                                |  |*
*|  |  -------------------------------------------------------------|  |*
*|  |  Item total                               ₹ 498.00             |  |*
*|  |  Delivery fee                             ₹  35.00             |  |*
*|  |  Platform fee                             ₹   5.00             |  |*
*|  |  Packing charges                          ₹  20.00             |  |*
*|  |  Surge (High demand)                      ₹  15.00             |  |*
*|  |  -------------------------------------------------------------|  |*
*|  |  Subtotal                                 ₹ 573.00             |  |*
*|  |  -------------------------------------------------------------|  |*
*|  |  Coupon (FLAT50)                          - ₹ 50.00            |  |*
*|  |  -------------------------------------------------------------|  |*
*|  |  GST (5%)                                  ₹  26.15            |  |*
*|  |  -------------------------------------------------------------|  |*
*|  |  TOTAL                                    ₹ 549.15             |  |*
*|  |  -------------------------------------------------------------|  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  DELIVERY FEE CALCULATION                                             |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Base formula:                                                 |  |*
*|  |                                                                 |  |*
*|  |  delivery_fee = base_fee + (distance * per_km_rate)           |  |*
*|  |                                                                 |  |*
*|  |  Example:                                                       |  |*
*|  |  * Base fee: ₹15 (first 2 km included)                        |  |*
*|  |  * Per km: ₹10                                                 |  |*
*|  |  * Distance: 5 km                                              |  |*
*|  |  * Fee: 15 + (5-2) * 10 = ₹45                                 |  |*
*|  |                                                                 |  |*
*|  |  Adjustments:                                                  |  |*
*|  |  * Rain surge: +20%                                           |  |*
*|  |  * Peak hours: +₹10-30                                        |  |*
*|  |  * Free delivery: Order > ₹199 (restaurant promo)            |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SURGE PRICING                                                         |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Factors:                                                      |  |*
*|  |  * High demand: More orders than available partners           |  |*
*|  |  * Weather: Rain increases demand, reduces supply             |  |*
*|  |  * Time: Lunch (12-2 PM), Dinner (7-10 PM)                   |  |*
*|  |  * Events: Cricket match, festival                            |  |*
*|  |                                                                 |  |*
*|  |  Calculation:                                                  |  |*
*|  |                                                                 |  |*
*|  |  demand_supply_ratio = active_orders / available_partners     |  |*
*|  |                                                                 |  |*
*|  |  if ratio > 1.5: surge = 1.2x                                 |  |*
*|  |  if ratio > 2.0: surge = 1.5x                                 |  |*
*|  |  if ratio > 3.0: surge = 2.0x                                 |  |*
*|  |                                                                 |  |*
*|  |  Applied to: Delivery fee only (not food price)               |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  COUPON SYSTEM                                                         |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TABLE: coupons                                                |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | coupon_code     | VARCHAR (PK)  | FLAT50, NEWUSER        | |  |*
*|  |  | discount_type   | ENUM          | FLAT, PERCENTAGE       | |  |*
*|  |  | discount_value  | DECIMAL       | 50 or 20 (%)           | |  |*
*|  |  | max_discount    | DECIMAL       | Cap for %              | |  |*
*|  |  | min_order_value | DECIMAL       | Minimum cart           | |  |*
*|  |  | valid_from      | TIMESTAMP     | Start date             | |  |*
*|  |  | valid_until     | TIMESTAMP     | End date               | |  |*
*|  |  | max_uses        | INT           | Total uses allowed     | |  |*
*|  |  | current_uses    | INT           | Used so far            | |  |*
*|  |  | per_user_limit  | INT           | 1 use per user         | |  |*
*|  |  | restaurant_ids  | JSON          | Null = all             | |  |*
*|  |  | user_ids        | JSON          | Targeted users         | |  |*
*|  |  | payment_methods | JSON          | [UPI, CARD]            | |  |*
*|  |  | is_active       | BOOLEAN       | Enabled/disabled       | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |                                                                 |  |*
*|  |  Validation Flow:                                              |  |*
*|  |  1. Check coupon exists and is_active                         |  |*
*|  |  2. Check validity dates                                      |  |*
*|  |  3. Check max_uses not exceeded                               |  |*
*|  |  4. Check per_user_limit for this user                        |  |*
*|  |  5. Check min_order_value                                     |  |*
*|  |  6. Check restaurant_ids includes this restaurant            |  |*
*|  |  7. Check payment_method if specified                         |  |*
*|  |  8. Calculate discount                                        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

END OF PART 4
