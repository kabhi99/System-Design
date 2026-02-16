================================================================================
         E-COMMERCE SYSTEM DESIGN
         Chapter 2: High-Level Architecture
================================================================================

This chapter presents the complete architecture of an e-commerce platform,
explaining microservices, data flow, and technology choices.


================================================================================
SECTION 2.1: ARCHITECTURE OVERVIEW
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │                    E-COMMERCE ARCHITECTURE                             │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                         CLIENTS                                 │  │
    │  │    [Web App]    [Mobile Apps]    [Partner APIs]                │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                              │                                         │
    │                              ▼                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │              CDN (Static assets, images, product pages)        │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                              │                                         │
    │                              ▼                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                      API GATEWAY                                │  │
    │  │    [Auth] [Rate Limit] [Routing] [Load Balance]                │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                              │                                         │
    │  ┌───────────────────────────┼───────────────────────────┐            │
    │  │                           │                           │            │
    │  ▼                           ▼                           ▼            │
    │  ┌────────────┐      ┌────────────┐      ┌────────────┐              │
    │  │   User     │      │  Product   │      │   Search   │              │
    │  │  Service   │      │  Catalog   │      │  Service   │              │
    │  └────────────┘      └────────────┘      └────────────┘              │
    │                                                                         │
    │  ┌────────────┐      ┌────────────┐      ┌────────────┐              │
    │  │   Cart     │      │  Inventory │      │   Order    │              │
    │  │  Service   │      │  Service   │      │  Service   │              │
    │  └────────────┘      └────────────┘      └────────────┘              │
    │                                                                         │
    │  ┌────────────┐      ┌────────────┐      ┌────────────┐              │
    │  │  Payment   │      │  Shipping  │      │ Notification│              │
    │  │  Service   │      │  Service   │      │  Service   │              │
    │  └────────────┘      └────────────┘      └────────────┘              │
    │                              │                                         │
    │  ┌───────────────────────────┴───────────────────────────┐            │
    │  │                      DATA LAYER                       │            │
    │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐ │            │
    │  │  │PostgreSQL│  │ MongoDB │  │  Redis  │  │  Elastic│ │            │
    │  │  │ (Orders) │  │(Catalog)│  │ (Cache) │  │ (Search)│ │            │
    │  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘ │            │
    │  └───────────────────────────────────────────────────────┘            │
    │                              │                                         │
    │  ┌───────────────────────────┴───────────────────────────┐            │
    │  │                    KAFKA (Event Bus)                  │            │
    │  │  [Order Events] [Inventory] [Payments] [Analytics]   │            │
    │  └───────────────────────────────────────────────────────┘            │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 2.2: MICROSERVICES DEEP DIVE
================================================================================

USER SERVICE
────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  USER SERVICE                                                          │
    │                                                                         │
    │  RESPONSIBILITIES:                                                     │
    │  • User registration and authentication                               │
    │  • Profile management                                                 │
    │  • Address book management                                            │
    │  • Wishlist                                                           │
    │                                                                         │
    │  ENDPOINTS:                                                            │
    │  POST /users/register                                                 │
    │  POST /users/login                                                    │
    │  GET  /users/profile                                                  │
    │  POST /users/addresses                                                │
    │  GET  /users/wishlist                                                 │
    │                                                                         │
    │  DATABASE: PostgreSQL (users, addresses)                              │
    │  CACHE: Redis (sessions, profile cache)                               │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


PRODUCT CATALOG SERVICE
───────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  PRODUCT CATALOG SERVICE                                              │
    │                                                                         │
    │  RESPONSIBILITIES:                                                     │
    │  • Product listing and details                                        │
    │  • Categories and attributes                                          │
    │  • Pricing (can be separate service at scale)                        │
    │  • Reviews and ratings                                                │
    │                                                                         │
    │  ENDPOINTS:                                                            │
    │  GET  /products                                                       │
    │  GET  /products/{id}                                                  │
    │  GET  /products/{id}/reviews                                         │
    │  GET  /categories                                                     │
    │  POST /products (seller)                                              │
    │                                                                         │
    │  WHY MONGODB?                                                          │
    │  Products have varying attributes:                                    │
    │  - Laptop: RAM, processor, screen size                               │
    │  - Shirt: size, color, material                                      │
    │  - Book: author, pages, ISBN                                         │
    │                                                                         │
    │  Document model handles this flexibility well.                        │
    │                                                                         │
    │  DATABASE: MongoDB                                                     │
    │  • Products collection (flexible schema)                              │
    │  • Categories collection                                              │
    │  • Reviews collection                                                 │
    │                                                                         │
    │  CACHE: Redis                                                          │
    │  • Popular products (top 10K products = 90% of traffic)             │
    │  • Category listings                                                  │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


SEARCH SERVICE
──────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  SEARCH SERVICE                                                        │
    │                                                                         │
    │  RESPONSIBILITIES:                                                     │
    │  • Full-text search                                                   │
    │  • Faceted search (filters)                                          │
    │  • Autocomplete                                                       │
    │  • Search ranking                                                     │
    │                                                                         │
    │  ENDPOINTS:                                                            │
    │  GET /search?q=laptop&brand=dell&price=50000-100000                  │
    │  GET /search/suggest?q=lapt                                          │
    │                                                                         │
    │  BACKEND: Elasticsearch                                               │
    │                                                                         │
    │  FEATURES:                                                             │
    │  • Fuzzy matching for typos                                          │
    │  • Synonyms (laptop = notebook)                                      │
    │  • Boosting (promoted products)                                      │
    │  • Aggregations for filters                                          │
    │                                                                         │
    │  DATA SYNC:                                                            │
    │  MongoDB → Change Data Capture → Kafka → Elasticsearch               │
    │                                                                         │
    │  PERSONALIZATION:                                                      │
    │  Search results can be personalized based on:                        │
    │  • User's past purchases                                             │
    │  • Browsing history                                                  │
    │  • Location                                                          │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


CART SERVICE
────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  CART SERVICE                                                          │
    │                                                                         │
    │  RESPONSIBILITIES:                                                     │
    │  • Manage shopping cart                                               │
    │  • Persist cart across sessions                                       │
    │  • Handle cart merging (guest → logged in)                           │
    │  • Price updates                                                      │
    │                                                                         │
    │  ENDPOINTS:                                                            │
    │  GET    /cart                                                         │
    │  POST   /cart/items                                                   │
    │  PUT    /cart/items/{id}                                             │
    │  DELETE /cart/items/{id}                                             │
    │  POST   /cart/apply-coupon                                           │
    │                                                                         │
    │  STORAGE: Redis (primary) + PostgreSQL (backup)                       │
    │                                                                         │
    │  CART STRUCTURE IN REDIS:                                             │
    │  ┌────────────────────────────────────────────────────────────────┐   │
    │  │ Key: cart:{user_id}                                           │   │
    │  │ Value: {                                                       │   │
    │  │   "items": [                                                   │   │
    │  │     {                                                          │   │
    │  │       "product_id": "prod_123",                               │   │
    │  │       "quantity": 2,                                          │   │
    │  │       "price": 999.00,                                        │   │
    │  │       "added_at": "2024-01-15T10:00:00Z"                     │   │
    │  │     }                                                          │   │
    │  │   ],                                                           │   │
    │  │   "coupon": "SAVE10",                                         │   │
    │  │   "updated_at": "2024-01-15T10:30:00Z"                       │   │
    │  │ }                                                              │   │
    │  │ TTL: 30 days                                                   │   │
    │  └────────────────────────────────────────────────────────────────┘   │
    │                                                                         │
    │  CART CHALLENGES:                                                      │
    │  • Price changes: Recalculate on checkout                            │
    │  • Out of stock: Notify user on checkout                             │
    │  • Guest carts: Merge when user logs in                              │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


INVENTORY SERVICE ⭐
───────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  INVENTORY SERVICE (Critical!)                                        │
    │                                                                         │
    │  RESPONSIBILITIES:                                                     │
    │  • Track stock levels per product per warehouse                      │
    │  • Reserve inventory during checkout                                  │
    │  • Release inventory if order cancelled                              │
    │  • Prevent overselling                                                │
    │                                                                         │
    │  ENDPOINTS:                                                            │
    │  GET  /inventory/{product_id}                                        │
    │  POST /inventory/reserve                                              │
    │  POST /inventory/release                                              │
    │  POST /inventory/deduct (on shipment)                                │
    │                                                                         │
    │  DATABASE: PostgreSQL (ACID for inventory transactions)              │
    │                                                                         │
    │  INVENTORY STATES:                                                     │
    │  ┌────────────────────────────────────────────────────────────────┐   │
    │  │                                                                │   │
    │  │  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐  │   │
    │  │  │  AVAILABLE   │────►│   RESERVED   │────►│   SOLD       │  │   │
    │  │  │   (100)      │     │    (10)      │     │    (5)       │  │   │
    │  │  └──────────────┘     └──────────────┘     └──────────────┘  │   │
    │  │         ▲                    │                               │   │
    │  │         │                    │ Order cancelled               │   │
    │  │         └────────────────────┘ (Release)                    │   │
    │  │                                                                │   │
    │  └────────────────────────────────────────────────────────────────┘   │
    │                                                                         │
    │  Total Stock = Available + Reserved + Sold                           │
    │                                                                         │
    │  MULTI-WAREHOUSE:                                                      │
    │  ┌────────────────────────────────────────────────────────────────┐   │
    │  │ product_id │ warehouse_id │ available │ reserved │ sold       │   │
    │  │──────────────────────────────────────────────────────────────── │   │
    │  │ PROD_123   │ WH_MUMBAI    │    50     │    5     │  100       │   │
    │  │ PROD_123   │ WH_DELHI     │    30     │    2     │   75       │   │
    │  │ PROD_123   │ WH_BANGALORE │    20     │    0     │   50       │   │
    │  └────────────────────────────────────────────────────────────────┘   │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


ORDER SERVICE ⭐
───────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  ORDER SERVICE (Critical!)                                            │
    │                                                                         │
    │  RESPONSIBILITIES:                                                     │
    │  • Create orders from cart                                            │
    │  • Order lifecycle management                                         │
    │  • Order history                                                      │
    │  • Cancellation and returns                                           │
    │                                                                         │
    │  ENDPOINTS:                                                            │
    │  POST /orders (create order)                                          │
    │  GET  /orders/{id}                                                    │
    │  GET  /orders (user's orders)                                        │
    │  POST /orders/{id}/cancel                                            │
    │  POST /orders/{id}/return                                            │
    │                                                                         │
    │  ORDER STATES:                                                         │
    │  ┌────────────────────────────────────────────────────────────────┐   │
    │  │                                                                │   │
    │  │  CREATED → PAYMENT_PENDING → CONFIRMED → PROCESSING           │   │
    │  │                                              ↓                 │   │
    │  │                                          SHIPPED               │   │
    │  │                                              ↓                 │   │
    │  │                                          DELIVERED             │   │
    │  │                                              ↓                 │   │
    │  │                                          COMPLETED             │   │
    │  │                                                                │   │
    │  │  At any point: → CANCELLED or RETURNED                        │   │
    │  │                                                                │   │
    │  └────────────────────────────────────────────────────────────────┘   │
    │                                                                         │
    │  DATABASE: PostgreSQL                                                  │
    │  • orders (main order info)                                          │
    │  • order_items (line items)                                          │
    │  • order_status_history (audit trail)                                │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


PAYMENT SERVICE
───────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  PAYMENT SERVICE                                                       │
    │                                                                         │
    │  RESPONSIBILITIES:                                                     │
    │  • Payment processing                                                 │
    │  • Multiple payment methods                                           │
    │  • Refunds                                                            │
    │  • Payment reconciliation                                             │
    │                                                                         │
    │  INTEGRATIONS:                                                         │
    │  • Stripe, Razorpay, PayU (payment gateways)                         │
    │  • UPI (India)                                                        │
    │  • Wallets (PayPal, Paytm)                                           │
    │                                                                         │
    │  CRITICAL FEATURES:                                                    │
    │  • Idempotency keys for retries                                      │
    │  • PCI-DSS compliance                                                 │
    │  • Fraud detection integration                                        │
    │                                                                         │
    │  DATABASE: PostgreSQL                                                  │
    │  • payments (with idempotency_key)                                   │
    │  • refunds                                                            │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 2.3: CHECKOUT FLOW
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  CHECKOUT SEQUENCE DIAGRAM                                            │
    │                                                                         │
    │  User        API GW      Cart     Inventory    Payment     Order      │
    │   │            │          │          │           │          │         │
    │   │ Checkout   │          │          │           │          │         │
    │   │───────────►│          │          │           │          │         │
    │   │            │ Get Cart │          │           │          │         │
    │   │            │─────────►│          │           │          │         │
    │   │            │◄─────────│          │           │          │         │
    │   │            │          │          │           │          │         │
    │   │            │ Reserve Inventory   │           │          │         │
    │   │            │─────────────────────►           │          │         │
    │   │            │◄─────────────────────           │          │         │
    │   │            │     (success/fail)  │           │          │         │
    │   │            │          │          │           │          │         │
    │   │            │ Create Order (PENDING)          │          │         │
    │   │            │─────────────────────────────────────────────►        │
    │   │            │◄──────────────────────────────────────────────       │
    │   │            │          │          │           │          │         │
    │   │            │ Process Payment     │           │          │         │
    │   │            │─────────────────────────────────►          │         │
    │   │ Payment UI │          │          │           │          │         │
    │   │◄───────────│          │          │           │          │         │
    │   │ Complete   │          │          │           │          │         │
    │   │───────────►│          │          │           │          │         │
    │   │            │          │          │ Callback  │          │         │
    │   │            │◄─────────────────────────────────          │         │
    │   │            │          │          │           │          │         │
    │   │            │ Update Order (CONFIRMED)        │          │         │
    │   │            │─────────────────────────────────────────────►        │
    │   │            │          │          │           │          │         │
    │   │ Confirmation│         │          │           │          │         │
    │   │◄───────────│          │          │           │          │         │
    │   │            │          │          │           │          │         │
    │                                                                         │
    │  IF PAYMENT FAILS:                                                     │
    │  - Order marked as PAYMENT_FAILED                                     │
    │  - Inventory released                                                 │
    │  - User notified                                                       │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 2.4: TECHNOLOGY CHOICES
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  TECHNOLOGY STACK                                                      │
    │                                                                         │
    │  COMPONENT              │ TECHNOLOGY        │ REASONING                │
    │  ═══════════════════════════════════════════════════════════════════   │
    │  API Gateway            │ Kong / Envoy      │ Rate limiting, routing   │
    │  Backend Services       │ Java/Go           │ Performance, ecosystem   │
    │  Product Catalog        │ MongoDB           │ Flexible schema          │
    │  Orders/Payments        │ PostgreSQL        │ ACID transactions        │
    │  Cart/Sessions          │ Redis             │ Speed, TTL               │
    │  Search                 │ Elasticsearch     │ Full-text, facets        │
    │  Message Queue          │ Kafka             │ Event-driven, replay     │
    │  CDN                    │ CloudFront        │ Global edge              │
    │  Object Storage         │ S3                │ Product images           │
    │  Container              │ Kubernetes        │ Scaling, orchestration   │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
CHAPTER SUMMARY
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  ARCHITECTURE - KEY TAKEAWAYS                                         │
    │                                                                         │
    │  CORE SERVICES                                                         │
    │  ─────────────                                                         │
    │  • Catalog: MongoDB for flexible product schema                       │
    │  • Inventory: PostgreSQL for ACID guarantees                          │
    │  • Orders: PostgreSQL with event sourcing                             │
    │  • Cart: Redis for speed                                              │
    │  • Search: Elasticsearch for performance                              │
    │                                                                         │
    │  DATA FLOW                                                             │
    │  ─────────                                                             │
    │  • Checkout: Cart → Inventory → Order → Payment                       │
    │  • Search: MongoDB → CDC → Kafka → Elasticsearch                     │
    │  • Events: All services → Kafka → Consumers                          │
    │                                                                         │
    │  CRITICAL POINTS                                                       │
    │  ───────────────                                                       │
    │  • Inventory reservation prevents overselling                        │
    │  • Event-driven for loose coupling                                   │
    │  • Multiple payment gateway fallback                                 │
    │                                                                         │
    │  INTERVIEW TIP                                                         │
    │  ─────────────                                                         │
    │  Draw the checkout flow sequence diagram.                            │
    │  Explain what happens if payment fails.                              │
    │  Discuss inventory reservation vs deduction.                         │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
                              END OF CHAPTER 2
================================================================================

